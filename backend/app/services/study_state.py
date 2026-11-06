"""知识点学习状态机（P0-20）。

未学习 → 学习中（阅读讲解）→ 待巩固（首次练习）→ 已掌握（自测达标）；
复习到期或完成复习时置为"复习中"。
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.practice import KpStudyState

NOT_STARTED = "未学习"
LEARNING = "学习中"
CONSOLIDATING = "待巩固"
MASTERED = "已掌握"
REVIEWING = "复习中"

SELFTEST_PASS_SCORE = 80.0


def get(db: Session, *, user_id: int, kp_id: int) -> Optional[KpStudyState]:
    return db.scalar(
        select(KpStudyState).where(
            KpStudyState.user_id == user_id,
            KpStudyState.knowledge_point_id == kp_id,
        )
    )


def states_for(
    db: Session, *, user_id: int, kp_ids: list[int]
) -> dict[int, KpStudyState]:
    if not kp_ids:
        return {}
    rows = db.scalars(
        select(KpStudyState).where(
            KpStudyState.user_id == user_id,
            KpStudyState.knowledge_point_id.in_(kp_ids),
        )
    )
    return {row.knowledge_point_id: row for row in rows}


def next_state(current: str, *, event: str, achieved: bool = False) -> str:
    """计算状态迁移；未知事件保持原状态。"""
    if event == "review":
        return REVIEWING
    if current == NOT_STARTED:
        if event == "read":
            return LEARNING
        if event == "practice":
            return CONSOLIDATING
        if event == "selftest":
            return MASTERED if achieved else CONSOLIDATING
        return current
    if event == "read":
        return current
    if event == "practice":
        if current == REVIEWING:
            return REVIEWING
        return MASTERED if current == MASTERED else CONSOLIDATING
    if event == "selftest":
        if achieved:
            return MASTERED
        return current if current == MASTERED else CONSOLIDATING
    return current


def mark(
    db: Session,
    *,
    user_id: int,
    kp_id: int,
    event: str,
    achieved: bool = False,
    now: Optional[datetime] = None,
) -> KpStudyState:
    """记录学习事件并推进状态（幂等：同一用户+知识点仅一行）。"""
    moment = now or datetime.utcnow()
    row = get(db, user_id=user_id, kp_id=kp_id)
    if row is None:
        row = KpStudyState(
            user_id=user_id,
            knowledge_point_id=kp_id,
            state=NOT_STARTED,
            evidence_count=0,
        )
        db.add(row)
    row.state = next_state(row.state, event=event, achieved=achieved)
    row.last_event = event
    row.evidence_count = (row.evidence_count or 0) + 1
    row.updated_at = moment
    if event == "read":
        row.read_at = moment
    if row.state == MASTERED and row.mastered_at is None:
        row.mastered_at = moment
    db.flush()
    return row
