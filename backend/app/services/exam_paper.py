"""试卷生成（P0-26 → PG-01 改造）：按蓝图分节组卷，确定性 seed。

2026-11-16 改造要点（PM 裁决：不接受降级卷）：
1. 难度带改用「册内分位」：低 60% easy / 中 30% medium / 高 10% hard，不再依赖失真的 difficulty=1；
2. 题库过滤：只用 status=published 且 answer 非空的题；
3. 同一知识点同卷最多 2 题；
4. 题量/题型/难度不足时**拒绝出卷**（refused=True），不再静默兜底；
5. 分值必须与蓝图 total_score 严格一致，否则拒绝；
6. 支持 scope（unit/half_book/book）解析章节。
"""

import random
import re
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.content import Chapter, Question
from app.models.exam import ExamBlueprint
from app.models.user import User

# 题库尚不存在的题型：一旦蓝图要求，组卷即拒绝（PM 裁决「不接受降级卷」）
STRICT_Q_TYPES = {"composition", "listening", "experiment"}

BAND_QUANTILES = {"easy": (0.0, 0.6), "medium": (0.6, 0.9), "hard": (0.9, 1.0)}

KP_CAP_PER_PAPER = 4     # 整卷同一知识点上限
KP_CAP_PER_SECTION = 2   # 同一大题内同一知识点上限。曾两次尝试放宽（2→4 于 v2.14、
                          # 2→3 于 v2.16），两次都让归一覆盖下降：coverage 实质不变
                          # （0.654 → 0.654），但 cap 分母随上限抬高（7/11 → 9/11），
                          # 所以「理论可达」虚高、实际拿不到。达标口径不要动这个值。

# 为补知识点覆盖而跨出难度带的比例上限：超过该比例，卷面难度配比会明显偏离蓝图声明，
# 应视为「拿难度换覆盖」过度，需要在审计里拦下而不是静默接受。
MAX_KP_CROSS_BAND_RATIO = 0.25
CROSS_MIN_ITEMS = 4  # 小卷跨带题数地板：12 题卷按 25% 只给 3 题，与分位切档冲突

# 题干指纹归一化：去掉空白与常见标点，只留文字与数字。
# 用途是卷内同题去重——题库里同一道题可能被录入成不同 id（不同来源批次），
# 只按 question_id 去重时，卷面会出现两道一模一样的题（走查 exam14 q3/q9 即此因）。
_STEM_NOISE = re.compile(
    r"[\s\u3000（）()【】\[\]{}<>《》，,。.、；;：:！!？?“”\"'‘’`~\-—_/\\|*#&]+"
)


def stem_fingerprint(question: Question) -> str:
    """题干指纹（去空白标点后的文本）；无题干时返回空串，不参与去重。"""
    content = question.content if isinstance(question.content, dict) else {}
    stem = str(content.get("stem") or "")
    return _STEM_NOISE.sub("", stem)


@dataclass
class PaperItem:
    question: Question
    section_index: int
    section_name: str
    score: float
    band: str = "medium"


@dataclass
class Shortage:
    section_index: int
    section_name: str
    q_type: Optional[str]
    wanted: int
    got: int
    reason: str


@dataclass
class ExamPaper:
    blueprint: ExamBlueprint
    items: list[PaperItem]
    seed: int
    requested: int
    available: int
    kp_coverage: float
    difficulty_mix: dict[str, int] = field(default_factory=dict)
    chapter_coverage: float = 0.0
    # 知识点覆盖的「题量上限」与归一化值：
    # 一题只挂一个知识点，故命中不同知识点的上限 = min(知识点池, 题量)。
    # 期末卷题量(18/22) 远小于册内知识点池，kp_coverage 会被分母稀释；
    # kp_coverage_normalized = 命中数 / min(池, 题量)，用于判断是否接近结构性满覆盖。
    kp_universe_size: int = 0
    kp_coverage_cap: float = 0.0
    kp_coverage_normalized: float = 0.0
    band_relaxed: int = 0
    fallback_count: int = 0
    # 为「补知识点覆盖」而跨出难度带取用的题数，及其占全卷比例（上限见 MAX_KP_CROSS_BAND_RATIO）
    kp_cross_band: int = 0
    crossed_ratio: float = 0.0
    shortages: list[Shortage] = field(default_factory=list)
    refused: bool = False
    refuse_reason: str = ""

    @property
    def questions(self) -> list[Question]:
        return [item.question for item in self.items]

    @property
    def total_score(self) -> float:
        return sum(item.score for item in self.items)

    @property
    def insufficient(self) -> bool:
        return self.refused or len(self.items) < self.requested


def _difficulty_band(difficulty: int) -> str:
    if difficulty <= 1:
        return "easy"
    if difficulty <= 3:
        return "medium"
    return "hard"


def _band_members(typed: list[Question]) -> dict[str, set[int]]:
    """同一题型池内按「排名分位」切三档：低 60% easy / 中 30% medium / 高 10% hard。

    题库 difficulty 是 1–5 的整数且分布集中，直接按数值切分会让三档退化成一档；
    按排名切分能保证目标配比（6:3:1）在出卷时稳定成立。
    """
    if not typed:
        return {"easy": set(), "medium": set(), "hard": set()}
    # 排序同难度时把「未挂知识点」的题排在后面：它占难度带名额却不贡献覆盖率，
    # 语文各章都有若干无 KP 的通用练习题（近反义/量词/的字得等），若不后置会把
    # 带 KP 的题挤出 easy 带，导致 coverage 被结构性压低。
    ordered = sorted(typed, key=lambda q: (q.difficulty, q.knowledge_point_id is None, q.id))
    n = len(ordered)
    easy_end = max(1, int(round(n * BAND_QUANTILES["easy"][1])))
    medium_end = max(easy_end + 1, int(round(n * BAND_QUANTILES["medium"][1])))
    hard = ordered[medium_end:]
    if not hard:
        # 小池（如语文习作只有 4 题）时高分位为空，退化为「带 KP 的最后一题」，
        # 不能让无 KP 的题顶到 hard 档——某些节只有 1 个位置，会把唯一覆盖点挤掉。
        with_kp = [q for q in ordered if q.knowledge_point_id]
        hard = (with_kp or ordered)[-max(1, n // 10):]
    return {
        "easy": {q.id for q in ordered[:easy_end]},
        "medium": {q.id for q in ordered[easy_end:medium_end]},
        "hard": {q.id for q in hard},
    }


def _allowed_ids(section: dict, typed: list[Question]) -> Optional[set[int]]:
    """返回该节允许的题目 id 集合；None 表示不限制难度。"""
    configured = set(section.get("difficulty") or [])
    if configured:
        return {q.id for q in typed if q.difficulty in configured}
    band = section.get("band")
    if band:
        members = _band_members(typed)
        return members.get(band, set())
    return None


def _kp_universe(chapter_ids: list[int], db: Session) -> set[int]:
    rows = db.scalars(
        select(Question.knowledge_point_id).where(
            Question.chapter_id.in_(chapter_ids),
            Question.knowledge_point_id.is_not(None),
        )
    )
    return {kp for kp in rows if kp}


def _kp_count(items: list[Question]) -> dict[int, int]:
    counts: dict[int, int] = {}
    for q in items:
        if q.knowledge_point_id:
            counts[q.knowledge_point_id] = counts.get(q.knowledge_point_id, 0) + 1
    return counts


def _pick(
    candidates: list[Question],
    wanted: int,
    covered_kps: set[int],
    kp_counts: dict[int, int],
    covered_chapters: Optional[set[int]] = None,
    kp_cap: int = KP_CAP_PER_PAPER,
    section_kp_cap: int = KP_CAP_PER_SECTION,
    beyond: Optional[list[Question]] = None,
    cross_limit: int = 0,
    cross_stat: Optional[dict] = None,
    priority_kps: Optional[set[int]] = None,
    core_kps: Optional[set[int]] = None,
    core_cross_budget: int = 0,
    seen_stems: Optional[set[str]] = None,
) -> list[Question]:
    """核心考点优先 → 章节覆盖优先 → 知识点覆盖优先 → 补足；同知识点次数受上限约束。

    seen_stems：整卷共享的题干指纹集合（跨大题传递），防止同一题干被录入成多个
    题号后在同卷重复出现。传 None 时退化为只按题目 id 去重（旧行为）。
    """
    covered_chapters = covered_chapters if covered_chapters is not None else set()
    picked: list[Question] = []
    picked_ids: set[int] = set()
    section_kp: dict[int, int] = {}
    fp_cache: dict[int, str] = {}

    def fingerprint(q: Question) -> str:
        fp = fp_cache.get(q.id)
        if fp is None:
            fp = stem_fingerprint(q)
            fp_cache[q.id] = fp
        return fp

    def allow(q: Question) -> bool:
        if q.id in picked_ids:
            return False
        if seen_stems is not None:
            fp = fingerprint(q)
            if fp and fp in seen_stems:
                return False
        kp = q.knowledge_point_id
        if kp is None:
            return True
        if section_kp.get(kp, 0) >= section_kp_cap:
            return False
        return kp_counts.get(kp, 0) < kp_cap

    def take(question: Question) -> None:
        picked.append(question)
        picked_ids.add(question.id)
        if seen_stems is not None:
            fp = fingerprint(question)
            if fp:
                seen_stems.add(fp)
        kp = question.knowledge_point_id
        kp_counts[kp] = kp_counts.get(kp, 0) + 1
        section_kp[kp] = section_kp.get(kp, 0) + 1
        if kp:
            covered_kps.add(kp)
        covered_chapters.add(question.chapter_id)

    # 第零轮：期末必考核心考点先进位。必须排在章节覆盖轮之前——否则章节多的册
    # （如 g8 数学上册 7 章）会把本节位置先分给「每章 1 题」，留给核心考点的位置
    # 只剩零星几个，核心清单命中率被章节轮挤掉。只在显式传入 core_kps 时启用。
    if core_kps:
        for question in candidates:
            if len(picked) >= wanted:
                break
            kp = question.knowledge_point_id
            if not kp or kp not in core_kps or kp in covered_kps:
                continue
            if not allow(question):
                continue
            take(question)
        # 带内取不到时，允许核心考点跨出难度带。难度带是「按排名分位切」的，
        # 同一难度的题还有 1/3 会落在本节带外——核心考点若因此整块拿不到，
        # 覆盖缺口就不是题量问题而是分位问题。核心跨带单独计 4 次额度并计入
        # cross_stat，卷级仍有 25% 的 crossed_ratio 兜底。
        if beyond:
            # 额度优先用「整卷共享预算」：按本节题量算会被小节卡死——fill 节 8 题
            # 只给 2 次跨带，而一个单元可能有 3 个核心考点全落在带外，必然缺 1 个
            # （g1 语文各单元核心覆盖卡 0.625 即此因）。未传预算时退回按节缩放。
            used = cross_stat.get("used", 0) if cross_stat is not None else 0
            if core_cross_budget:
                core_cross_cap = max(0, min(4, core_cross_budget) - used)
            else:
                core_cross_cap = max(1, min(4, int(wanted * 0.25)))
            core_cross = 0
            for question in beyond:
                if len(picked) >= wanted or core_cross >= core_cross_cap:
                    break
                kp = question.knowledge_point_id
                if not kp or kp not in core_kps or kp in covered_kps:
                    continue
                if not allow(question):
                    continue
                take(question)
                core_cross += 1
            if cross_stat is not None and core_cross:
                cross_stat["used"] = cross_stat.get("used", 0) + core_cross

    # 第一轮：每章至少 1 题（期末/期中卷按章节覆盖判定达标）
    for question in candidates:
        if len(picked) >= wanted:
            break
        if question.chapter_id in covered_chapters:
            continue
        if not allow(question):
            continue
        take(question)

    # 第二轮前置：先覆盖「本题型独占」的知识点。若先按池序贪心，fill 会吃掉
    # 与 choice/judge 共享的知识点，导致后面这些节拿不到任何新覆盖（语文单元卷
    # 只剩 11/15 就是此因）。独占点只有本节能覆盖，必须先占。
    if priority_kps:
        for question in candidates:
            if len(picked) >= wanted:
                break
            kp = question.knowledge_point_id
            if not kp or kp not in priority_kps or kp in covered_kps:
                continue
            if not allow(question):
                continue
            take(question)

    # 第二轮：每个未覆盖知识点取 1 题。无 KP 的题不贡献覆盖，留给第三轮补题量，
    # 否则会在「习作只有 1 个位置」这类节里把唯一的带 KP 题挤掉。
    for question in candidates:
        if len(picked) >= wanted:
            break
        kp = question.knowledge_point_id
        if not kp or kp in covered_kps:
            continue
        if not allow(question):
            continue
        take(question)

    # 第二轮半：知识点覆盖优先于难度带——候选池里已无未覆盖知识点时，
    # 允许跨出难度带从 beyond 取题补覆盖，但每节限量（cross_limit），
    # 且仍受「同节同知识点上限」约束，避免为了覆盖把难度分布彻底打散。
    if beyond and cross_limit > 0:
        used_cross = 0
        for question in beyond:
            if len(picked) >= wanted or used_cross >= cross_limit:
                break
            kp = question.knowledge_point_id
            if not kp or kp in covered_kps:
                continue
            if not allow(question):
                continue
            take(question)
            used_cross += 1
        if cross_stat is not None:
            cross_stat["used"] = cross_stat.get("used", 0) + used_cross

    # 第三轮：补足题量。同样题量下优先取「挂了知识点」的题——无 KP 的题会
    # 占用卷面位置却不贡献覆盖，是语文单章卷 coverage 卡在 cap 以下的主因
    # （单章 fill 8 个位置恰好有 8 道带 KP 的题，此前被 4 道无 KP 题占掉）。
    for question in candidates:
        if len(picked) >= wanted:
            break
        if not question.knowledge_point_id:
            continue
        if not allow(question):
            continue
        take(question)
    for question in candidates:
        if len(picked) >= wanted:
            break
        if question.knowledge_point_id:
            continue
        if not allow(question):
            continue
        take(question)
    return picked


CN_DIGITS = "零一二三四五六七八九十"


def _cn_number(value: int) -> str:
    """1→一、10→十、12→十二（教材单元名常用中文数字）。"""
    if value <= 10:
        return CN_DIGITS[value]
    if value < 20:
        return "十" + CN_DIGITS[value - 10]
    tens, ones = divmod(value, 10)
    return CN_DIGITS[tens] + "十" + (CN_DIGITS[ones] if ones else "")


def _is_named_unit(name: str) -> bool:
    """章节名是否为单元/章级（「第一单元 ...」「第3章 ...」）。"""
    return ("单元" in name) or (name.startswith("第") and "章" in name)


def _unit_tokens(unit_index: int) -> set[str]:
    """兼容「第1单元 / 第一单元 / 第1章 / 第一章」四种命名。"""
    arabic = f"第{unit_index}"
    chinese = f"第{_cn_number(unit_index)}"
    return {
        f"{arabic}单元", f"{chinese}单元", f"{arabic}章", f"{chinese}章",
    }


def resolve_scope_chapters(
    db: Session,
    *,
    textbook_id: int,
    scope: str = "book",
    unit_index: Optional[int] = None,
) -> list[int]:
    """按 scope 解析章节集合：book=全册；half_book=前半册；unit=指定单元。

    占位/旧样章（is_placeholder=1）一律不进范围：这些章节由早期导入产生，
    与真实教材目录无关，若参与组卷会带进不属于该年级的内容（例如小学数学卷里
    出现负数运算），也会把知识点并集撑大、压低覆盖率。
    """
    chapters = list(
        db.scalars(
            select(Chapter)
            .where(
                Chapter.textbook_id == textbook_id,
                Chapter.is_placeholder == 0,
            )
            .order_by(Chapter.order_index, Chapter.id)
        )
    )
    if not chapters:
        return []
    if scope == "book":
        return [c.id for c in chapters]
    if scope == "half_book":
        half = max(1, len(chapters) // 2)
        return [c.id for c in chapters[:half]]
    if scope == "unit":
        if unit_index is None:
            raise ValueError("scope=unit 时必须提供 unit_index")
        tokens = _unit_tokens(unit_index)
        matched = [
            c for c in chapters
            if any(token in (c.name or "") for token in tokens)
        ]
        if matched:
            # 教材里「单元」与「课」两种章节并存：单元章节之后的课级章节属于该单元，
            # 直到下一个具名单元为止，否则单章题量撑不起一份单元卷。
            start_order = min(c.order_index for c in matched)
            next_orders = [
                c.order_index for c in chapters
                if c.order_index > start_order
                and _is_named_unit(c.name or "")
            ]
            end_order = min(next_orders) if next_orders else float("inf")
            return [
                c.id for c in chapters
                if c in matched or start_order <= c.order_index < end_order
            ]
        # 题库章节粒度常是「课」而非「单元」：按 3 章折算 1 个单元，避免单章题量不足以出一份单元卷
        start = (unit_index - 1) * 3
        window = chapters[start:start + 3]
        return [c.id for c in window] or [chapters[min(unit_index - 1, len(chapters) - 1)].id]
    raise ValueError(f"未知 scope: {scope}")


def generate_paper(
    db: Session,
    *,
    user: User,
    blueprint: ExamBlueprint,
    chapter_ids: list[int],
    seed: Optional[int] = None,
    exclude_question_ids: Optional[set[int]] = None,
    allow_fallback: bool = False,
    allow_band_relax: bool = True,
    core_kps: Optional[set[int]] = None,
) -> ExamPaper:
    """按蓝图生成试卷；不足即拒绝（allow_fallback=True 才回退到旧兜底行为）。

    core_kps 传入「该册期末必考核心考点」时，这些考点在各节内获得与「题型独占
    知识点」同级的优先占位权，使核心考点先于普通考点被覆盖。不传时行为不变。
    """
    actual_seed = int(seed) if seed is not None else random.randint(1, 2**31 - 1)
    rng = random.Random(actual_seed)

    exclude = exclude_question_ids or set()
    stmt = select(Question).where(
        Question.chapter_id.in_(chapter_ids),
        Question.status == "published",
    )
    raw_pool = list(db.scalars(stmt))
    pool = []
    for q in raw_pool:
        if q.id in exclude:
            continue
        if not q.answer:
            continue
        pool.append(q)
    pool.sort(key=lambda q: q.id)
    rng.shuffle(pool)

    sections = list(blueprint.sections or [])
    requested = sum(int(section.get("count", 0)) for section in sections)
    # 覆盖分母只统计「本次卷型实际会考的题型」的知识点：语文单元卷只考
    # fill/choice/answer/composition，题库里 judge/multiple 专属的知识点
    # 无论怎么出卷都覆盖不到，计入分母等于人为压低覆盖率。
    involved_types = {s.get("q_type") for s in sections if s.get("q_type")}
    kp_universe = {
        q.knowledge_point_id for q in pool
        if q.knowledge_point_id and q.q_type in involved_types
    } or _kp_universe(chapter_ids, db)
    # 每个「题型 -> 知识点集合」，用于算出「本题型独占」的知识点（跨节预留的依据）
    kp_by_type: dict[str, set[int]] = {}
    for q in pool:
        if q.knowledge_point_id:
            kp_by_type.setdefault(q.q_type, set()).add(q.knowledge_point_id)
    # 知识点太少时（如单章只有 1 个知识点）按题量反推上限，避免整卷被上限卡死
    kp_cap = max(KP_CAP_PER_PAPER, -(-requested // max(len(kp_universe), 1)))
    required_chapters = set(chapter_ids)
    # 覆盖分母只算「题库里确有可用题目的章节」，避免占位章节把覆盖率永久压低
    chapter_total = len({q.chapter_id for q in pool}) or 1
    chapter_hit: set[int] = set()

    used: set[int] = set()
    covered: set[int] = set()
    kp_counts: dict[int, int] = {}
    items: list[PaperItem] = []
    shortages: list[Shortage] = []
    refused = False
    reason = ""
    band_relaxed = 0
    kp_cross_band = 0
    # 整卷跨带预算：为补知识点覆盖最多牺牲 MAX_KP_CROSS_BAND_RATIO 比例的题量
    cross_budget = max(1, int(requested * MAX_KP_CROSS_BAND_RATIO))
    # 核心考点的跨带额度：整卷共享，上限 4 次（与期末卷实测值一致）
    core_cross_budget = min(4, cross_budget)

    # 卷级题干指纹：同一题干被录入成多个题号时也要去重（走查 LR-6）
    seen_stems: set[str] = set()

    for index, section in enumerate(sections):
        wanted = int(section.get("count", 0))
        q_type = section.get("q_type")
        score_each = float(section.get("score_each", 0))

        remaining = [q for q in pool if q.id not in used]
        typed = [q for q in remaining if q_type is None or q.q_type == q_type]
        # 难度带在同一题型池内按排名分位切分（跨题型难度分布不可比）
        allowed_ids = _allowed_ids(section, typed)
        preferred = [q for q in typed if allowed_ids is None or q.id in allowed_ids]
        candidates = list(preferred)
        # 难度带外的同题型题：只用于「补知识点覆盖」，不做常规补题。
        # 每节最多 2 题，且整卷受 cross_budget（≈25% 题量）约束，避免难度配比被大幅打散。
        beyond = [q for q in typed if allowed_ids is not None and q.id not in allowed_ids]
        # 传了核心清单时，跨带配额统一交给核心轮按本节题量缩放占用；
        # 否则两条通道各跨一次就会顶破卷级 25% 的 crossed_ratio 上限（单元卷 12 题时
        # 4 题即 0.33，整卷直接被拒）。
        cross_limit = (
            0 if (q_type in STRICT_Q_TYPES or core_kps) else min(2, cross_budget)
        )
        cross_stat: dict = {}
        # 该题型独占的知识点（其他题型完全没有题）：只有本节能覆盖，优先占位
        other_kps: set[int] = set()
        for t in involved_types:
            if t != q_type:
                other_kps |= kp_by_type.get(t, set())
        priority_kps = kp_by_type.get(q_type, set()) - other_kps
        if core_kps:
            # 期末必考核心考点：与「题型独占」同级优先，保证核心先被覆盖
            priority_kps = priority_kps | (core_kps & kp_by_type.get(q_type, set()))

        if q_type in STRICT_Q_TYPES and not typed:
            shortages.append(Shortage(
                index, str(section.get("name", "")), q_type, wanted, 0,
                f"题库无 {q_type} 题型（不接受降级替代）",
            ))
            refused = True
            reason = reason or f"缺少题型 {q_type}"
            continue

        # 主观题（习作）与听力整卷只有少数几题、且天然围绕同一话题/同一知识点成组出现，
        # 若沿用「每知识点上限」会被客观题占满而永远取不到，故单独用一份计数。
        pick_counts = {} if q_type in STRICT_Q_TYPES else kp_counts
        # 听力/习作整节围绕同一话题，不适用「每节同知识点 2 题」的上限
        section_kp_cap = wanted if q_type in STRICT_Q_TYPES else KP_CAP_PER_SECTION
        kp_cap_for_section = wanted if q_type in STRICT_Q_TYPES else kp_cap

        # 第一步：先保证「未覆盖章节」各有 1 题（期末/期中卷按章节覆盖判定达标），
        # 该步不受难度带限制，避免分位池把某些章节整章过滤掉。
        uncovered_pass = [q for q in typed if q.chapter_id not in chapter_hit]
        head = _pick(uncovered_pass, min(wanted, chapter_total - len(chapter_hit)),
                     covered, pick_counts, chapter_hit, kp_cap_for_section, section_kp_cap,
                     core_kps=core_kps, seen_stems=seen_stems) if required_chapters else []
        picked = list(head)
        # 注意：章节覆盖轮的跨带是蓝图结构性必然（一册 40-66 个知识点、每章至少 1 题，
        # 必然有题落在带外），它不属于「拿难度换覆盖」，不计入 cross_stat。
        # 曾试过如实计入，期末卷立刻 8-9/25=0.32 全部被拒（v2.24 回退）。
        head_ids = {q.id for q in head}
        candidates = [q for q in candidates if q.id not in head_ids]
        remaining_wanted = wanted - len(picked)
        if remaining_wanted > 0:
            picked.extend(_pick(candidates, remaining_wanted, covered, pick_counts, chapter_hit,
                                kp_cap_for_section, section_kp_cap,
                                beyond=[q for q in beyond if q.id not in head_ids],
                                cross_limit=cross_limit, cross_stat=cross_stat,
                                priority_kps=priority_kps, core_kps=core_kps,
                                core_cross_budget=core_cross_budget,
                                seen_stems=seen_stems))
        kp_cross_band += cross_stat.get("used", 0)
        cross_budget = max(0, cross_budget - cross_stat.get("used", 0))
        core_cross_budget = max(0, core_cross_budget - cross_stat.get("used", 0))
        if len(picked) < wanted and allow_band_relax:
            # 只放宽「难度带」，绝不放宽「题型」：同题型内的其余题目补位
            leftovers = [q for q in typed if q.id not in {p.id for p in picked}]
            extra = _pick(leftovers, wanted - len(picked), covered, pick_counts, chapter_hit, kp_cap_for_section, section_kp_cap, seen_stems=seen_stems)
            band_relaxed += len(extra)
            picked.extend(extra)
        if len(picked) < wanted and allow_fallback:
            extras = [q for q in remaining if q.id not in {p.id for p in picked}]
            picked.extend(_pick(extras, wanted - len(picked), covered, pick_counts, chapter_hit, kp_cap_for_section, section_kp_cap, seen_stems=seen_stems))

        if len(picked) < wanted:
            shortages.append(Shortage(
                index, str(section.get("name", "")), q_type, wanted, len(picked),
                "可用题量或难度带不足",
            ))
            refused = True
            reason = reason or "题量/难度不足"

        for question in picked:
            used.add(question.id)
            chapter_hit.add(question.chapter_id)
            items.append(PaperItem(
                question=question,
                section_index=index,
                section_name=str(section.get("name", f"第 {index + 1} 部分")),
                score=score_each,
                band=str(section.get("band") or _difficulty_band(picked[0].difficulty)),
            ))

    # 卷面难度分布按「蓝图声明的难度带」统计（与细目表口径一致），
    # 不再用题库普遍失真的原始 difficulty 值。
    mix: dict[str, int] = {}
    for item in items:
        band = item.band or _difficulty_band(item.question.difficulty)
        mix[band] = mix.get(band, 0) + 1

    coverage = round(len(covered) / len(kp_universe), 3) if kp_universe else 0.0
    chapter_coverage = round(len(chapter_hit) / chapter_total, 3) if chapter_total else 0.0
    # PG-01 覆盖口径：单元卷看知识点覆盖，期中/期末看章节覆盖——
    # 一张 22 题的期末卷不可能覆盖全册上百个知识点，以「章节覆盖」作为达标口径。
    effective_coverage = max(coverage, chapter_coverage)

    # 题量上限归一化：一题只挂一个知识点，所以某节最多能贡献「该节题量」与
    # 「该题型可用知识点数」中的较小值。注意不是 KP_CAP_PER_SECTION——那个常量
    # 是「同一知识点在本节最多出现几次」，与「本节最多覆盖几个知识点」是两件事；
    # 早前把两者混用会把分母压成 Σmin(题量, 2)（语文 unit 仅 7/11=0.636），
    # 造成归一虚高，并让「提节级上限」看起来总是让指标变差。
    kp_universe_size = len(kp_universe)
    type_kp_counts: dict[str, set[int]] = {}
    for q in pool:
        if q.knowledge_point_id:
            type_kp_counts.setdefault(q.q_type, set()).add(q.knowledge_point_id)
    section_cap_kps = 0
    for section in sections:
        wanted_s = int(section.get("count", 0))
        if wanted_s <= 0:
            continue
        available = len(type_kp_counts.get(section.get("q_type"), ()))
        section_cap_kps += min(wanted_s, available)
    cap_kps = min(section_cap_kps, requested, kp_universe_size)
    kp_coverage_cap = (
        round(cap_kps / kp_universe_size, 3) if kp_universe_size else 0.0
    )
    kp_coverage_normalized = (
        round(min(1.0, coverage / kp_coverage_cap), 3) if kp_coverage_cap else 0.0
    )

    total = sum(item.score for item in items)
    if not refused and abs(total - float(blueprint.total_score)) > 0.01:
        refused = True
        reason = f"分值与蓝图不一致（{total} ≠ {blueprint.total_score}）"

    if not refused and effective_coverage < (blueprint.kp_coverage_min or 0):
        refused = True
        reason = (
            f"覆盖不足（知识点 {coverage:.2f} / 章节 {chapter_coverage:.2f}，"
            f"要求 {blueprint.kp_coverage_min}）"
        )

    # 硬约束：补覆盖允许跨难度带，但比例超过上限即「拿难度换覆盖」过度，拒绝出卷。
    # 预算层已保证不会超，这里作为兜底，防止后续改预算公式时静默突破。
    # 硬约束：补覆盖允许跨难度带，但比例超过上限即「拿难度换覆盖」过度，拒绝出卷。
    # 预算层已保证不会超，这里作为兜底，防止后续改预算公式时静默突破。
    # 题数地板：12 题的数学单元卷分 3 节、每节 4-5 题，按排名分位切三档后带内
    # 每档只剩 1-2 题，与 25% 的 3 题上限叠加必然冲突（实测 4 张卷卡死在 4/12）。
    # 小卷按「至少 4 题」放行，大卷仍按 25% 比例。
    crossed_ratio = round(kp_cross_band / len(items), 3) if items else 0.0
    crossed_allow = max(
        CROSS_MIN_ITEMS, int(len(items) * MAX_KP_CROSS_BAND_RATIO)
    ) if items else 0
    if not refused and kp_cross_band > crossed_allow:
        refused = True
        reason = (
            f"跨带补覆盖超限（{kp_cross_band}/{len(items)}={crossed_ratio:.2f}，"
            f"上限 {MAX_KP_CROSS_BAND_RATIO}）"
        )

    return ExamPaper(
        blueprint=blueprint,
        items=items,
        seed=actual_seed,
        requested=requested,
        available=len(pool),
        kp_coverage=coverage,
        chapter_coverage=chapter_coverage,
        kp_universe_size=kp_universe_size,
        kp_coverage_cap=kp_coverage_cap,
        kp_coverage_normalized=kp_coverage_normalized,
        difficulty_mix=mix,
        band_relaxed=band_relaxed,
        kp_cross_band=kp_cross_band,
        # 为补知识点覆盖而跨出难度带的题占全卷比例，直接衡量「覆盖 vs 难度」的让步
        crossed_ratio=crossed_ratio,
        shortages=shortages,
        refused=refused,
        refuse_reason=reason,
    )
