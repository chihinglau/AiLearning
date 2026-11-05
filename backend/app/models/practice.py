from datetime import datetime
from typing import Any, Optional

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import JSONType


class StudentQuestionRecord(Base):
    """答题记录，错题本与学情分析的原始数据来源。"""

    __tablename__ = "student_question_records"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), index=True)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)
    user_answer: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONType, nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    wrong_reason: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    mastered: Mapped[bool] = mapped_column(Boolean, default=False)
    attempted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class MasteryScore(Base):
    """知识点掌握度（0-100），由异步学情分析任务回写。"""

    __tablename__ = "mastery_scores"
    __table_args__ = (
        UniqueConstraint("user_id", "knowledge_point_id", name="uq_mastery_user_kp"),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    knowledge_point_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_points.id"), index=True
    )
    score: Mapped[float] = mapped_column(default=0.0)
    confidence: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
