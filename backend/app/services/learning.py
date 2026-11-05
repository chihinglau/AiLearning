"""学情引擎：掌握度 EMA 更新、SM-2 Lite 错题复习调度、自适应难度配比。

全部函数保持纯函数 / 显式传 db，确定性可单测。
"""

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


def grade_answer(question: Question, user_answer: dict[str, Any]) -> bool:
    expected = question.answer.get("value")
    actual = user_answer.get("value")
    if expected is None or actual is None:
        return False
    # answer.value 支持「可接受答案列表」（填空题多答案）
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
) -> Optional[MasteryScore]:
    """按 EMA 更新某学生在某知识点上的掌握度；题目未挂知识点时跳过。"""
    if knowledge_point_id is None:
        return None
    row = db.scalar(
        select(MasteryScore).where(
            MasteryScore.user_id == user_id,
            MasteryScore.knowledge_point_id == knowledge_point_id,
        )
    )
    p = 1.0 if is_correct else 0.0
    if row is None:
        row = MasteryScore(
            user_id=user_id,
            knowledge_point_id=knowledge_point_id,
            score=EMA_ALPHA * p * 100,
            confidence=1,
        )
        db.add(row)
        db.flush()
    else:
        row.score = EMA_ALPHA * p * 100 + (1 - EMA_ALPHA) * row.score
        row.confidence = min(row.confidence + 1, MAX_CONFIDENCE)
        row.updated_at = datetime.utcnow()
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
