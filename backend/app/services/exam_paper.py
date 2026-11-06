"""试卷生成（P0-26）：按蓝图分节组卷，确定性 seed，题型/难度/覆盖约束 + 题量兜底。"""

import random
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.content import Question
from app.models.exam import ExamBlueprint
from app.models.user import User


@dataclass
class PaperItem:
    question: Question
    section_index: int
    section_name: str
    score: float


@dataclass
class ExamPaper:
    blueprint: ExamBlueprint
    items: list[PaperItem]
    seed: int
    requested: int
    available: int
    kp_coverage: float
    difficulty_mix: dict[str, int] = field(default_factory=dict)
    fallback_count: int = 0

    @property
    def questions(self) -> list[Question]:
        return [item.question for item in self.items]

    @property
    def total_score(self) -> float:
        return sum(item.score for item in self.items)

    @property
    def insufficient(self) -> bool:
        return len(self.items) < self.requested


def _difficulty_band(difficulty: int) -> str:
    if difficulty <= 1:
        return "easy"
    if difficulty <= 3:
        return "medium"
    return "hard"


def _pick(
    candidates: list[Question], wanted: int, covered: set[int]
) -> list[Question]:
    """覆盖优先：先每个知识点取 1 题，再按顺序补齐。"""
    picked: list[Question] = []
    picked_ids: set[int] = set()
    for question in candidates:
        if len(picked) >= wanted:
            break
        kp_id = question.knowledge_point_id
        if kp_id and kp_id in covered:
            continue
        picked.append(question)
        picked_ids.add(question.id)
        if kp_id:
            covered.add(kp_id)
    for question in candidates:
        if len(picked) >= wanted:
            break
        if question.id in picked_ids:
            continue
        picked.append(question)
        picked_ids.add(question.id)
        if question.knowledge_point_id:
            covered.add(question.knowledge_point_id)
    return picked


def generate_paper(
    db: Session,
    *,
    user: User,
    blueprint: ExamBlueprint,
    chapter_ids: list[int],
    seed: Optional[int] = None,
) -> ExamPaper:
    """按蓝图生成试卷：分节题型配比 → 难度优先 → 知识点覆盖 → 题量兜底。"""
    actual_seed = int(seed) if seed is not None else random.randint(1, 2**31 - 1)
    rng = random.Random(actual_seed)

    stmt = select(Question).where(Question.chapter_id.in_(chapter_ids))
    pool = list(db.scalars(stmt))
    pool.sort(key=lambda q: q.id)
    rng.shuffle(pool)

    range_kps = {q.knowledge_point_id for q in pool if q.knowledge_point_id}
    sections = list(blueprint.sections or [])
    requested = sum(int(section.get("count", 0)) for section in sections)

    used: set[int] = set()
    covered: set[int] = set()
    items: list[PaperItem] = []
    fallback_count = 0

    for index, section in enumerate(sections):
        wanted = int(section.get("count", 0))
        q_type = section.get("q_type")
        allowed_diff = set(section.get("difficulty") or [])
        score_each = float(section.get("score_each", 0))

        remaining = [q for q in pool if q.id not in used]
        typed = [q for q in remaining if q_type is None or q.q_type == q_type]
        preferred = [q for q in typed if not allowed_diff or q.difficulty in allowed_diff]
        candidates = list(preferred or typed)
        picked = _pick(candidates, wanted, covered)

        # 题量兜底：该题型/难度不足时，从任意剩余题目补齐
        if len(picked) < wanted:
            before = len(picked)
            picked_ids = {q.id for q in picked}
            extras = [q for q in remaining if q.id not in picked_ids]
            picked.extend(_pick(extras, wanted - len(picked), covered))
            fallback_count += len(picked) - before

        for question in picked:
            used.add(question.id)
            items.append(
                PaperItem(
                    question=question,
                    section_index=index,
                    section_name=str(section.get("name", f"第 {index + 1} 部分")),
                    score=score_each,
                )
            )

    mix: dict[str, int] = {}
    for item in items:
        band = _difficulty_band(item.question.difficulty)
        mix[band] = mix.get(band, 0) + 1

    coverage = round(len(covered) / len(range_kps), 3) if range_kps else 0.0
    return ExamPaper(
        blueprint=blueprint,
        items=items,
        seed=actual_seed,
        requested=requested,
        available=len(pool),
        kp_coverage=coverage,
        difficulty_mix=mix,
        fallback_count=fallback_count,
    )
