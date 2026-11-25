"""学情引擎：掌握度 EMA 更新、SM-2 Lite 错题复习调度、自适应难度配比。

全部函数保持纯函数 / 显式传 db，确定性可单测。
"""

import re
from datetime import datetime, timedelta
from typing import Any, Iterable, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.content import Question
from app.models.practice import MasteryScore, WrongQuestion

# ---------------------------------------------------------------------------
# 判题（与 practice.route.grade_answer 同一规范，集中到引擎以便复用）
# ---------------------------------------------------------------------------


def normalize(value: Any) -> str:
    if isinstance(value, list):
        return "|".join(sorted(normalize(item) for item in value))
    text = str(value).strip().lower()
    # 填空题容错：压缩全部空白、统一中英文标点
    for ch in " \t\u3000":
        text = text.replace(ch, "")
    return text.replace("，", ",").replace("（", "(").replace("）", ")")


# ---------------------------------------------------------------------------
# 主观题（解答/计算/习作）关键词覆盖判分
#
# 主观题参考答案多是「示例：…」式的完整表述，学生几乎不可能逐字相同，
# 全等判分等于永远判错。这里改为「关键内容覆盖」：把参考答案切成
# 汉字二元组 + 字母数字词，学生作答覆盖到阈值即算答对。
# 只做字符串层面的关键词匹配（不引入分词/NLP 依赖），并保留：
#   - 数学写法归一：平方/立方 → 幂指数，² ³ → 数字，使「a²+b²=c²」与
#     「a 的平方加 b 的平方等于 c 的平方」等价；
#   - 短答案（如「是/否」「25」）仍走全等，避免宽松判分把是非题判错。
# ---------------------------------------------------------------------------

SUBJECTIVE_Q_TYPES = {"answer", "calc", "composition", "essay", "writing"}

# 参考答案前缀引导语（「示例：」「参考答案：」「评分要点：」等）不参与匹配
_ANSWER_PREFIXES = (
    "参考答案",
    "正确答案",
    "评分要点",
    "评分标准",
    "参考",
    "示例",
    "例如",
    "答案",
)

# 虚词：既不能作为关键词，也不该拼进汉字二元组
_STOP_CHARS = set("的了是在和与及或也就都而又把被对从向这那其之并且则于等吗呢吧啊很更最将已")

_POWER_WORDS = (("四次方", "4"), ("三次方", "3"), ("平方", "2"), ("立方", "3"))
_SUPERSCRIPTS = {
    "⁰": "0",
    "¹": "1",
    "²": "2",
    "³": "3",
    "⁴": "4",
    "⁵": "5",
}

_LATIN_RUN = re.compile(r"[0-9a-z]+")
_CJK_RUN = re.compile(r"[\u4e00-\u9fff]+")
_NON_WORD = re.compile(r"[^0-9a-z\u4e00-\u9fff]+")

# 参考答案少于该关键词数时不做宽松判分（是非题、单值填空等）
SUBJECTIVE_MIN_UNITS = 5
# 关键词覆盖率阈值：命中 50% 即视为答对（主观题二元对错，取偏宽松口径）
SUBJECTIVE_HIT_RATIO = 0.5
# 作答长度下限（相对参考答案），避免只写一两个关键词就判对
SUBJECTIVE_MIN_LENGTH_RATIO = 0.3


def _clean_subjective(text: str) -> str:
    s = str(text).strip().lower()
    for ch in " \t\u3000":
        s = s.replace(ch, "")
    for word, power in _POWER_WORDS:
        s = s.replace(word, power)
    for sup, digit in _SUPERSCRIPTS.items():
        s = s.replace(sup, digit)
    s = _NON_WORD.sub("", s)
    changed = True
    while changed:
        changed = False
        for prefix in _ANSWER_PREFIXES:
            if s.startswith(prefix) and len(s) > len(prefix) + 1:
                s = s[len(prefix):]
                changed = True
    return s


def _keyword_units(text: str) -> dict[str, int]:
    """「主谓宾」近似载体：汉字二元组（权重 2）+ 字母数字词（权重 1）。

    汉字承载语义，权重更高；字母/数字（变量名、数值、单位）只是辅助。
    """
    units: dict[str, int] = {}
    for run in _CJK_RUN.findall(text):
        kept = "".join(ch for ch in run if ch not in _STOP_CHARS)
        if len(kept) <= 1:
            if kept:
                units[kept] = 2
        else:
            for i in range(len(kept) - 1):
                units[kept[i : i + 2]] = 2
    for token in _LATIN_RUN.findall(text):
        units[token] = 1
    return units


def _char_units(text: str) -> dict[str, int]:
    """单字级关键词（去掉虚词），用于覆盖「学生只写要点名词」的作答。"""
    units: dict[str, int] = {}
    for run in _CJK_RUN.findall(text):
        for ch in run:
            if ch not in _STOP_CHARS:
                units[ch] = 2
    for token in _LATIN_RUN.findall(text):
        units[token] = 1
    return units


def _symbol_signature(text: str) -> str:
    """去掉汉字后的符号/数字串，用于识别等价数学式。"""
    return "".join(ch for ch in text if not ("\u4e00" <= ch <= "\u9fff"))


def _coverage(expected: dict[str, int], actual: dict[str, int]) -> float:
    total = sum(expected.values())
    if not total or not actual:
        return 0.0
    hit = sum(weight for unit, weight in expected.items() if unit in actual)
    return hit / total


def subjective_score(expected: str, actual: str) -> float:
    """返回 0~1 的关键内容覆盖率（1 = 完全覆盖）。

    取两个维度的较高值：
      - 二元组覆盖：区分度好，适合短答案与公式类；
      - 单字覆盖：学生只写要点名词、不写完整句时也能判对（「主谓宾」口径）。
    """
    e = _clean_subjective(expected)
    a = _clean_subjective(actual)
    if not e or not a:
        return 0.0
    if e == a:
        return 1.0
    # 数学式等价：a²+b²=c² ↔ a的平方加b的平方等于c的平方
    e_symbols = _symbol_signature(e)
    if len(e_symbols) >= 2 and e_symbols == _symbol_signature(a):
        return 1.0
    bigram = _coverage(_keyword_units(e), _keyword_units(a))
    unigram = _coverage(_char_units(e), _char_units(a))
    return max(bigram, unigram)


def _grade_subjective(expected: Any, actual: Any) -> bool:
    if isinstance(expected, list):
        return any(_grade_subjective(item, actual) for item in expected)
    e = _clean_subjective(expected)
    a = _clean_subjective(actual)
    if not e or not a:
        return False
    if len(_keyword_units(e)) < SUBJECTIVE_MIN_UNITS:
        # 参考答案太短（是/否、单个数值）→ 保持全等，宽松会把是非题放水。
        return normalize(expected) == normalize(actual)
    if a == e or (
        len(_symbol_signature(e)) >= 2
        and _symbol_signature(e) == _symbol_signature(a)
    ):
        return True
    if len(a) < max(2, int(len(e) * SUBJECTIVE_MIN_LENGTH_RATIO)):
        return False
    return subjective_score(expected, actual) >= SUBJECTIVE_HIT_RATIO


def grade_answer(question: Question, user_answer: dict[str, Any]) -> bool:
    expected = question.answer.get("value")
    actual = user_answer.get("value")
    if expected is None or actual is None:
        return False
    # 多选题：标准答案可能是列表或 "A|C" 形式，做整体等价比较。
    if isinstance(expected, list) and isinstance(actual, list):
        return normalize(actual) == normalize(expected)
    if isinstance(actual, list):
        return normalize(expected) == normalize(actual)
    # 主观题：按关键内容覆盖判分，避免「必须逐字相同」。
    if question.q_type in SUBJECTIVE_Q_TYPES:
        return _grade_subjective(expected, actual)
    # 填空题：answer.value 支持「可接受答案列表」（多答案任意匹配）。
    if isinstance(expected, list):
        return any(normalize(actual) == normalize(ans) for ans in expected)
    return normalize(expected) == normalize(actual)


# ---------------------------------------------------------------------------
# 掌握度 EMA
# ---------------------------------------------------------------------------

EMA_ALPHA = 0.6  # 本次作答权重
MAX_CONFIDENCE = 20
MASTERED_STREAK = 3


def update_mastery(
    db: Session,
    *,
    user_id: int,
    knowledge_point_id: Optional[int],
    is_correct: bool,
    source: str = "practice",
    weight: float = 1.0,
) -> Optional[MasteryScore]:
    """按 EMA 更新某学生在某知识点上的掌握度；题目未挂知识点时跳过。

    source 区分练习/复习/考试，weight 为来源权重（练习 1.0、单元测 0.8 等）。
    """
    if knowledge_point_id is None:
        return None
    row = db.scalar(
        select(MasteryScore).where(
            MasteryScore.user_id == user_id,
            MasteryScore.knowledge_point_id == knowledge_point_id,
        )
    )
    p = weight if is_correct else 0.0
    if row is None:
        row = MasteryScore(
            user_id=user_id,
            knowledge_point_id=knowledge_point_id,
            score=EMA_ALPHA * p * 100,
            confidence=1,
            source_breakdown={},
        )
        db.add(row)
        db.flush()
    else:
        row.score = EMA_ALPHA * p * 100 + (1 - EMA_ALPHA) * row.score
        row.confidence = min(row.confidence + 1, MAX_CONFIDENCE)
        row.updated_at = datetime.utcnow()
    breakdown = dict(row.source_breakdown or {})
    bucket = dict(breakdown.get(source) or {"answered": 0, "correct": 0})
    bucket["answered"] = int(bucket.get("answered", 0)) + 1
    bucket["correct"] = int(bucket.get("correct", 0)) + (1 if is_correct else 0)
    breakdown[source] = bucket
    row.source_breakdown = breakdown
    db.flush()
    return row


def mastery_band(score: float) -> str:
    if score < 40:
        return "weak"      # 薄弱
    if score < 70:
        return "growing"   # 巩固
    if score < 85:
        return "skilled"   # 熟练
    return "mastered"      # 精通


def derive_study_state(
    *, mastery: float, attempted: bool, due_review: bool = False
) -> str:
    """由掌握度与作答记录推导知识点学习状态（P0-20 状态机会覆盖为持久化状态）。"""
    if due_review:
        return "复习中"
    if not attempted:
        return "未学习"
    if mastery >= 85:
        return "已掌握"
    return "待巩固"


# ---------------------------------------------------------------------------
# SM-2 Lite 错题调度
# ---------------------------------------------------------------------------

DEFAULT_EASE = 2.5
MIN_EASE = 1.3
EASE_PENALTY = 0.2


def schedule_on_wrong(item: WrongQuestion, *, now: Optional[datetime] = None) -> None:
    """首次 / 再次答错：1 天后到期，连续记录归零，ease 下探。"""
    now = now or datetime.utcnow()
    item.wrong_count += 1
    item.correct_streak = 0
    item.status = "active"
    item.lapses += 1
    item.ease_factor = max(MIN_EASE, item.ease_factor - EASE_PENALTY)
    item.interval_days = 1
    item.reps = 0
    item.next_review_at = now + timedelta(days=1)
    item.last_wrong_at = now


def schedule_on_review_correct(
    item: WrongQuestion, *, question_difficulty: int, now: Optional[datetime] = None
) -> None:
    """复习答对：间隔 × ease；连续 3 次且题目难度≥3 → 已掌握。"""
    now = now or datetime.utcnow()
    item.correct_streak += 1
    item.reps += 1
    if item.reps == 1:
        item.interval_days = 1
    elif item.reps == 2:
        item.interval_days = 3
    else:
        item.interval_days = max(1, round(item.interval_days * item.ease_factor))
    item.next_review_at = now + timedelta(days=item.interval_days)
    if item.correct_streak >= MASTERED_STREAK and question_difficulty >= 3:
        item.status = "mastered"
        item.next_review_at = None


def upsert_wrong_question(
    db: Session,
    *,
    user_id: int,
    question: Question,
    is_correct: bool,
    now: Optional[datetime] = None,
) -> Optional[WrongQuestion]:
    """作答后维护错题本。

    - 答错：无则建，有则调度；
    - 答对且错题本中存在（复习场景）：推进调度；
    - 答对且错题本不存在：不建行。
    """
    now = now or datetime.utcnow()
    item = db.scalar(
        select(WrongQuestion).where(
            WrongQuestion.user_id == user_id,
            WrongQuestion.question_id == question.id,
        )
    )
    if not is_correct:
        if item is None:
            item = WrongQuestion(
                user_id=user_id,
                question_id=question.id,
                wrong_count=0,
                correct_streak=0,
                status="active",
                ease_factor=DEFAULT_EASE,
                interval_days=1,
                reps=0,
                lapses=0,
                last_wrong_at=now,
            )
            db.add(item)
            db.flush()
            schedule_on_wrong(item, now=now)
        else:
            schedule_on_wrong(item, now=now)
        return item
    if item is not None and item.status == "active":
        schedule_on_review_correct(item, question_difficulty=question.difficulty, now=now)
    return item


# ---------------------------------------------------------------------------
# 自适应组卷
# ---------------------------------------------------------------------------

# 掌握度分段 → 难度（1-5）权重表
DIFFICULTY_MIX: dict[str, list[int]] = {
    "weak":    [1, 1, 1, 1, 2, 2, 2, 3, 3, 3],
    "growing": [2, 2, 3, 3, 3, 3, 3, 3, 4, 4],
    "skilled": [3, 3, 3, 4, 4, 4, 4, 4, 5, 5],
    "mastered": [4, 4, 4, 4, 5, 5, 5, 5, 5, 5],
}


def pick_difficulties(score: float, count: int) -> list[int]:
    """根据掌握度给出 count 个目标难度（循环取权重表，保证确定性与配比）。"""
    table = DIFFICULTY_MIX[mastery_band(score)]
    return [table[i % len(table)] for i in range(count)]


def due_review_question_ids(db: Session, *, user_id: int, now: datetime) -> list[int]:
    rows = db.scalars(
        select(WrongQuestion.question_id)
        .where(
            WrongQuestion.user_id == user_id,
            WrongQuestion.status == "active",
            WrongQuestion.next_review_at.is_not(None),
            WrongQuestion.next_review_at <= now,
        )
        .order_by(WrongQuestion.next_review_at)
    ).all()
    return list(rows)


def choose_questions(
    candidates: Iterable[Question],
    target_difficulties: list[int],
    *,
    review_ids: Optional[list[int]] = None,
    review_quota: int = 3,
) -> list[Question]:
    """从候选池按目标难度配比挑题；优先插入到期复习错题。

    candidates 应已限定章节/知识点范围。挑选不到精确难度时就近降级。
    """
    pool = list(candidates)
    by_id = {q.id: q for q in pool}
    chosen: list[Question] = []
    used: set[int] = set()

    # 1) 到期复习错题优先（候选池中存在的）
    for qid in (review_ids or []):
        if len(chosen) >= review_quota:
            break
        q = by_id.get(qid)
        if q is not None and q.id not in used:
            chosen.append(q)
            used.add(q.id)

    # 2) 按难度配比从池中补齐
    for diff in target_difficulties:
        if len(chosen) >= len(target_difficulties) + review_quota:
            break
        pick = _nearest_unused(pool, used, diff)
        if pick is not None:
            chosen.append(pick)
            used.add(pick.id)

    return chosen[: len(target_difficulties) + review_quota]


def _nearest_unused(
    pool: list[Question], used: set[int], target: int
) -> Optional[Question]:
    for delta in range(0, 5):
        for diff in (target - delta, target + delta):
            if diff < 1 or diff > 5:
                continue
            for q in pool:
                if q.id not in used and q.difficulty == diff:
                    return q
    return None
