"""练习组卷：范围解析 + 题型配比 + 知识点覆盖 + 确定性选题（与预览共用同一 seed）。"""

import math
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.grade import derive_stage
from app.models.content import Chapter, KnowledgePoint, Question
from app.models.practice import MasteryScore, StudentQuestionRecord, WrongQuestion
from app.models.user import User

# 预估单题耗时（秒），用于练习配置页展示
SECONDS_PER_TYPE = {"choice": 30, "fill": 45, "judge": 25, "answer": 120}

# 题型配比：按学段默认（D-04 §15.2）；unit/pre_exam 模式按单元测蓝图覆盖
TYPE_RATIO_BY_STAGE: dict[str, dict[str, float]] = {
    "primary": {"choice": 0.40, "judge": 0.20, "fill": 0.25, "answer": 0.15},
    "junior": {"choice": 0.40, "multiple": 0.10, "judge": 0.05, "fill": 0.20, "answer": 0.25},
    "senior": {"choice": 0.35, "multiple": 0.15, "fill": 0.15, "answer": 0.35},
}
TYPE_RATIO_BY_MODE: dict[str, dict[str, float]] = {
    "unit": {"choice": 0.35, "judge": 0.15, "fill": 0.25, "answer": 0.25},
    "pre_exam": {"choice": 0.30, "multiple": 0.15, "fill": 0.15, "answer": 0.40},
}

MIN_COVERAGE_RATIO = 0.8      # KP 覆盖率下限（D-04 §7.3）
COVERAGE_FULL_KP = 3          # 范围 KP ≤ 3 时要求 100% 覆盖
DUE_QUOTA_CAP = 5             # 到期错题绝对上限
RECENT_EXCLUDE_DAYS = 7       # 去重窗口：7 天内做过的题不再出（D-04 §7.3）
WEAK_MASTERY_THRESHOLD = 60   # 掌握度低于此值视为薄弱知识点


@dataclass(frozen=True)
class ModePolicy:
    """一种练习模式的组卷策略（前端配置页展示同一份语义）。"""

    label: str
    summary: str
    due_quota_ratio: float = 0.25
    exclude_recent: bool = True
    weak_first: bool = False
    cover_all_kps: bool = False
    textbook_order: bool = False
    difficulty_order: bool = False
    type_ratio: Optional[dict[str, float]] = None


MODE_POLICIES: dict[str, ModePolicy] = {
    "special": ModePolicy(
        label="专项突破",
        summary="优先攻克薄弱知识点与到期错题，题目集中在尚未掌握的内容",
        due_quota_ratio=0.25,
        weak_first=True,
    ),
    "sync": ModePolicy(
        label="同步巩固",
        summary="按教材章节顺序由易到难推进，均衡覆盖范围内的知识点",
        due_quota_ratio=0.15,
        textbook_order=True,
        difficulty_order=True,
    ),
    "pre_exam": ModePolicy(
        label="考前速练",
        summary="全范围模拟卷：考试题型配比、知识点全覆盖、难度递进，不排重近期做过的题",
        due_quota_ratio=0.10,
        exclude_recent=False,
        cover_all_kps=True,
        difficulty_order=True,
        type_ratio=TYPE_RATIO_BY_MODE["pre_exam"],
    ),
    "unit": ModePolicy(
        label="单元测",
        summary="按单元测蓝图配比组卷",
        type_ratio=TYPE_RATIO_BY_MODE["unit"],
    ),
}


def get_mode_policy(mode: str) -> ModePolicy:
    """未知模式回退到专项突破，保证旧会话仍可组卷。"""
    return MODE_POLICIES.get(mode, MODE_POLICIES["special"])


def ratio_for(stage: str, mode: str) -> dict[str, float]:
    """题型配比：unit/pre_exam 用练习蓝图表，其余按学段默认。"""
    policy = get_mode_policy(mode)
    if policy.type_ratio:
        return policy.type_ratio
    if mode in TYPE_RATIO_BY_MODE:
        return TYPE_RATIO_BY_MODE[mode]
    return TYPE_RATIO_BY_STAGE.get(stage, TYPE_RATIO_BY_STAGE["primary"])


def coverage_target(kp_count: int) -> int:
    """覆盖率目标：KP≤3 要求全覆盖，否则 ≥80%。"""
    if kp_count <= 0:
        return 0
    if kp_count <= COVERAGE_FULL_KP:
        return kp_count
    return math.ceil(kp_count * MIN_COVERAGE_RATIO)


def recent_attempted_ids(
    db: Session, *, user_id: int, days: int = RECENT_EXCLUDE_DAYS
) -> set[int]:
    """最近 N 天已作答的题目 id（用于去重）。"""
    since = datetime.utcnow() - timedelta(days=days)
    rows = db.scalars(
        select(StudentQuestionRecord.question_id).where(
            StudentQuestionRecord.user_id == user_id,
            StudentQuestionRecord.attempted_at >= since,
        )
    )
    return set(rows)


def weak_kp_ids(db: Session, *, user_id: int, kp_ids: set[int]) -> Optional[set[int]]:
    """薄弱知识点（掌握度 < 60）。

    完全没有掌握度记录时返回 None，表示不倾斜——新用户/新教材不会因
    「全部未学」而让组卷退化为按 id 顺序，也不会改变既有的确定性结果。
    """
    if not kp_ids:
        return None
    rows = list(
        db.scalars(
            select(MasteryScore).where(
                MasteryScore.user_id == user_id,
                MasteryScore.knowledge_point_id.in_(kp_ids),
            )
        )
    )
    if not rows:
        return None
    weak = {
        row.knowledge_point_id
        for row in rows
        if row.score < WEAK_MASTERY_THRESHOLD
    }
    return weak or None


def order_by_textbook(db: Session, questions: list[Question]) -> list[Question]:
    """按教材顺序（章 → 知识点 order_index → 难度 → id）重排已选中的题。

    只改变呈现顺序，不改变题目集合，因此不影响覆盖率、题型配比与预览一致性。
    """
    kp_ids = {q.knowledge_point_id for q in questions if q.knowledge_point_id}
    chapter_ids = {q.chapter_id for q in questions if q.chapter_id}
    kp_order = {
        kp.id: kp.order_index
        for kp in db.scalars(
            select(KnowledgePoint).where(KnowledgePoint.id.in_(kp_ids))
        )
    } if kp_ids else {}
    chapter_order = {
        chapter.id: chapter.order_index
        for chapter in db.scalars(select(Chapter).where(Chapter.id.in_(chapter_ids)))
    } if chapter_ids else {}
    big = 10**9
    return sorted(
        questions,
        key=lambda q: (
            chapter_order.get(q.chapter_id, big),
            kp_order.get(q.knowledge_point_id, big),
            q.difficulty or 0,
            q.id,
        ),
    )


@dataclass
class PracticePlan:
    questions: list[Question]
    available: int
    range_kp_count: int
    due_review_count: int
    seed: int
    requested: int = 0
    q_type_mix: dict[str, int] = field(default_factory=dict)
    mode: str = "special"
    mode_label: str = "专项突破"
    strategy: str = ""

    @property
    def count(self) -> int:
        return len(self.questions)

    @property
    def insufficient(self) -> bool:
        return self.available < self.requested or self.count == 0

    @property
    def covered_kp_count(self) -> int:
        return len({q.knowledge_point_id for q in self.questions if q.knowledge_point_id})

    @property
    def kp_coverage(self) -> float:
        if not self.range_kp_count:
            return 0.0
        return round(self.covered_kp_count / self.range_kp_count, 3)

    @property
    def estimated_minutes(self) -> int:
        if not self.questions:
            return 0
        total = sum(SECONDS_PER_TYPE.get(q.q_type, 40) for q in self.questions)
        return max(1, math.ceil(total / 60))


def resolve_pool(
    db: Session,
    *,
    user: User,
    scope_type: str,
    scope_ids: list[int],
    q_types: Optional[list[str]] = None,
) -> list[Question]:
    """按范围取候选题目。scope_type: kp | chapter | textbook | wrong。"""
    if scope_type == "kp":
        if not scope_ids:
            return []
        stmt = select(Question).where(Question.knowledge_point_id.in_(scope_ids))
    elif scope_type == "chapter":
        if not scope_ids:
            return []
        stmt = select(Question).where(Question.chapter_id.in_(scope_ids))
    elif scope_type == "textbook":
        if not scope_ids:
            return []
        chapter_ids = select(Chapter.id).where(Chapter.textbook_id.in_(scope_ids))
        stmt = select(Question).where(Question.chapter_id.in_(chapter_ids))
    elif scope_type == "wrong":
        wrong = list(
            db.scalars(
                select(WrongQuestion).where(
                    WrongQuestion.user_id == user.id,
                    WrongQuestion.status == "active",
                )
            )
        )
        if not wrong:
            return []
        stmt = select(Question).where(Question.id.in_([row.question_id for row in wrong]))
    else:
        return []

    if q_types:
        stmt = stmt.where(Question.q_type.in_(q_types))
    questions = list(db.scalars(stmt.order_by(Question.id)))
    return questions


def due_review_ids(db: Session, *, user_id: int) -> set[int]:
    rows = db.scalars(
        select(WrongQuestion.question_id).where(
            WrongQuestion.user_id == user_id,
            WrongQuestion.status == "active",
            WrongQuestion.next_review_at.is_not(None),
            WrongQuestion.next_review_at <= datetime.utcnow(),
        )
    )
    return set(rows)


def select_questions(
    pool: list[Question],
    *,
    count: int,
    seed: int,
    due_ids: Optional[set[int]] = None,
    due_quota_ratio: float = 0.25,
    due_quota_cap: int = DUE_QUOTA_CAP,
    type_ratio: Optional[dict[str, float]] = None,
    duration_limit_min: Optional[int] = None,
    kp_ids: Optional[set[int]] = None,
    weak_kps: Optional[set[int]] = None,
    cover_all_kps: bool = False,
) -> list[Question]:
    """确定性选题（D-04 §7.3）：

    1) 到期错题优先，占比由模式策略给定且绝对上限 5 题；
    2) 知识点覆盖：先每 KP 取 1 题，直到达到覆盖目标（KP≤3 时 100%，否则 ≥80%；
       考前速练要求全覆盖）；薄弱知识点在专项突破模式下排在最前；
    3) 题型配比：按学段/模式蓝图分配剩余名额；
    4) 兜底：按 KP 轮转补齐，题量不足时自然收敛；
    5) 时长预算：超限时优先裁剪低难度非到期题。
    """
    if not pool or count <= 0:
        return []
    due_ids = due_ids or set()
    rng = random.Random(seed)

    # 到期错题配额（floor 保证占比不超 25%）
    due_pool = sorted([q for q in pool if q.id in due_ids], key=lambda q: q.id)
    rng.shuffle(due_pool)
    due_quota = min(len(due_pool), due_quota_cap, math.floor(count * due_quota_ratio))

    # 按知识点分桶，桶内洗牌；到期错题只走配额，不参与常规抽取（错题范围无其他题时才回退）
    normal_pool = [q for q in pool if q.id not in due_ids] or pool
    buckets: dict[int, list[Question]] = {}
    for question in normal_pool:
        buckets.setdefault(question.knowledge_point_id or 0, []).append(question)
    bucket_keys = sorted(buckets)
    rng.shuffle(bucket_keys)
    if weak_kps:
        # 稳定排序：弱项知识点整体前移，组内仍保持同一 seed 下的随机次序。
        bucket_keys.sort(key=lambda key: 0 if key in weak_kps else 1)
    for key in bucket_keys:
        buckets[key].sort(key=lambda q: q.id)
        rng.shuffle(buckets[key])

    selected: list[Question] = list(due_pool[:due_quota])
    seen = {q.id for q in selected}
    covered = {q.knowledge_point_id for q in selected if q.knowledge_point_id}

    range_kps = set(kp_ids) if kp_ids else {key for key in bucket_keys if key}
    target = len(range_kps) if cover_all_kps else coverage_target(len(range_kps))

    cursor = 0

    def take_any(q_type: Optional[str] = None) -> Optional[Question]:
        """按知识点轮转取 1 题；q_type 限定时跳过不匹配题但不丢弃。"""
        nonlocal cursor
        n = len(bucket_keys)
        if n == 0:
            return None
        for step in range(n):
            key = bucket_keys[(cursor + step) % n]
            bucket = buckets[key]
            for idx, question in enumerate(bucket):
                if question.id in seen:
                    continue
                if q_type is not None and question.q_type != q_type:
                    continue
                question = bucket.pop(idx)
                seen.add(question.id)
                selected.append(question)
                if question.knowledge_point_id:
                    covered.add(question.knowledge_point_id)
                cursor = (cursor + step + 1) % n
                return question
        return None

    # 覆盖率优先：每个 KP 至少 1 题
    for key in bucket_keys:
        if not key or len(selected) >= count or len(covered) >= target:
            continue
        bucket = buckets[key]
        while bucket and bucket[0].id in seen:
            bucket.pop(0)
        if not bucket:
            continue
        question = bucket.pop(0)
        seen.add(question.id)
        selected.append(question)
        covered.add(key)

    # 题型配比
    if type_ratio:
        existing = {q.q_type for q in pool}
        quotas = {
            q_type: int(round(count * ratio))
            for q_type, ratio in type_ratio.items()
            if q_type in existing and ratio > 0
        }
        actual = {q_type: sum(1 for q in selected if q.q_type == q_type) for q_type in quotas}
        for q_type in sorted(quotas, key=lambda t: (-quotas[t], t)):
            while actual.get(q_type, 0) < quotas[q_type] and len(selected) < count:
                if take_any(q_type) is None:
                    break
                actual[q_type] = actual.get(q_type, 0) + 1

    # 兜底补齐：按 KP 轮转
    while len(selected) < count:
        if take_any() is None:
            break

    # 时长预算：超限时优先裁剪低难度题（到期错题不裁）
    if duration_limit_min:
        limit_seconds = duration_limit_min * 60
        while selected and _estimate_seconds(selected) > limit_seconds:
            droppable = [q for q in selected if q.id not in due_ids]
            if not droppable:
                break
            drop = min(droppable, key=lambda q: (q.difficulty, -q.id))
            selected.remove(drop)
            seen.discard(drop.id)

    return selected[:count]


def _estimate_seconds(questions: list[Question]) -> int:
    return sum(SECONDS_PER_TYPE.get(q.q_type, 40) for q in questions)


def build_plan(
    db: Session,
    *,
    user: User,
    scope_type: str,
    scope_ids: list[int],
    count: int,
    q_types: Optional[list[str]] = None,
    seed: Optional[int] = None,
    mode: str = "special",
    duration_limit_min: Optional[int] = None,
    exclude_recent: bool = True,
) -> PracticePlan:
    policy = get_mode_policy(mode)
    pool = resolve_pool(
        db, user=user, scope_type=scope_type, scope_ids=scope_ids, q_types=q_types
    )
    actual_seed = int(seed) if seed is not None else random.randint(1, 2**31 - 1)

    # 去重：默认排除最近 7 天已做题；考前速练不排重（模拟卷允许再见做过的题）。
    # 过滤后为空则回退全量，避免无题可练。
    availablePool = pool
    if exclude_recent and policy.exclude_recent and pool:
        recent = recent_attempted_ids(db, user_id=user.id)
        filtered = [q for q in pool if q.id not in recent]
        availablePool = filtered or pool

    due = due_review_ids(db, user_id=user.id)
    try:
        stage = derive_stage(user.grade) if user.grade else "primary"
    except Exception:  # 非学生/异常年级兜底为小学配比
        stage = "primary"

    range_kp_ids = {q.knowledge_point_id for q in pool if q.knowledge_point_id}
    weak = (
        weak_kp_ids(db, user_id=user.id, kp_ids=range_kp_ids)
        if policy.weak_first
        else None
    )

    selected = select_questions(
        availablePool,
        count=count,
        seed=actual_seed,
        due_ids=due,
        due_quota_ratio=policy.due_quota_ratio,
        type_ratio=ratio_for(stage, mode),
        duration_limit_min=duration_limit_min,
        kp_ids=range_kp_ids,
        weak_kps=weak,
        cover_all_kps=policy.cover_all_kps,
    )
    # 呈现顺序也随模式变化：同步巩固按教材章节推进，考前速练按难度分层。
    # 只重排、不换题，预览与实际、覆盖率与题型配比均保持一致。
    if policy.textbook_order:
        selected = order_by_textbook(db, selected)
    elif policy.difficulty_order:
        selected = sorted(selected, key=lambda q: (q.difficulty or 0, q.id))

    mix: dict[str, int] = {}
    for question in selected:
        mix[question.q_type] = mix.get(question.q_type, 0) + 1
    return PracticePlan(
        questions=selected,
        available=len(availablePool),
        range_kp_count=len(range_kp_ids),
        due_review_count=len([q for q in pool if q.id in due]),
        seed=actual_seed,
        requested=count,
        q_type_mix=mix,
        mode=mode,
        mode_label=policy.label,
        strategy=policy.summary,
    )
