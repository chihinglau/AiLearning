"""练习组卷：范围解析 + 确定性选题（与预览共用同一 seed，保证所见即所得）。"""

import math
import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.content import Chapter, Question
from app.models.practice import WrongQuestion
from app.models.user import User

# 预估单题耗时（秒），用于练习配置页展示
SECONDS_PER_TYPE = {"choice": 30, "fill": 45, "judge": 25, "answer": 120}


@dataclass
class PracticePlan:
    questions: list[Question]
    available: int
    range_kp_count: int
    due_review_count: int
    seed: int
    requested: int = 0
    q_type_mix: dict[str, int] = field(default_factory=dict)

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
    due_ids: set[int] = set()
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
        due_ids = {
            row.question_id
            for row in wrong
            if row.next_review_at is not None and row.next_review_at <= datetime.utcnow()
        }
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
) -> list[Question]:
    """确定性选题：到期错题优先（≤quota），其余按知识点轮流抽取以提升覆盖率。"""
    if not pool or count <= 0:
        return []
    due_ids = due_ids or set()
    rng = random.Random(seed)

    due_pool = sorted([q for q in pool if q.id in due_ids], key=lambda q: q.id)
    rng.shuffle(due_pool)
    due_quota = min(len(due_pool), max(0, int(count * due_quota_ratio)))

    # 按知识点分桶，桶内洗牌；按桶顺序轮流取题，避免同一知识点扎堆
    buckets: dict[int, list[Question]] = {}
    for question in pool:
        if question.id in due_ids:
            continue
        buckets.setdefault(question.knowledge_point_id or 0, []).append(question)
    bucket_keys = sorted(buckets)
    rng.shuffle(bucket_keys)
    for key in bucket_keys:
        buckets[key].sort(key=lambda q: q.id)
        rng.shuffle(buckets[key])

    selected: list[Question] = due_pool[:due_quota]
    seen = {q.id for q in selected}
    cursor = 0
    while len(selected) < count and bucket_keys:
        if not any(buckets[k] for k in bucket_keys):
            break
        key = bucket_keys[cursor % len(bucket_keys)]
        cursor += 1
        bucket = buckets[key]
        if not bucket:
            continue
        question = bucket.pop(0)
        if question.id not in seen:
            selected.append(question)
            seen.add(question.id)
    return selected[:count]


def build_plan(
    db: Session,
    *,
    user: User,
    scope_type: str,
    scope_ids: list[int],
    count: int,
    q_types: Optional[list[str]] = None,
    seed: Optional[int] = None,
) -> PracticePlan:
    pool = resolve_pool(
        db, user=user, scope_type=scope_type, scope_ids=scope_ids, q_types=q_types
    )
    actual_seed = int(seed) if seed is not None else random.randint(1, 2**31 - 1)
    due = due_review_ids(db, user_id=user.id)
    selected = select_questions(pool, count=count, seed=actual_seed, due_ids=due)
    mix: dict[str, int] = {}
    for question in selected:
        mix[question.q_type] = mix.get(question.q_type, 0) + 1
    return PracticePlan(
        questions=selected,
        available=len(pool),
        range_kp_count=len({q.knowledge_point_id for q in pool if q.knowledge_point_id}),
        due_review_count=len([q for q in pool if q.id in due]),
        seed=actual_seed,
        requested=count,
        q_type_mix=mix,
    )
