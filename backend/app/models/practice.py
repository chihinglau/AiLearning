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
    # P0-24 数据来源拆分：practice|review|exam；session_id 关联练习会话
    source: Mapped[str] = mapped_column(String(20), default="practice", index=True)
    session_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("practice_sessions.id"), nullable=True, index=True
    )
    kp_weight: Mapped[float] = mapped_column(default=1.0)
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
    # P0-24 来源拆分：{practice: {answered, correct}, review: {...}, exam: {...}}
    source_breakdown: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class KpStudyState(Base):
    """知识点学习状态（P0-20 状态机），一生一知识点一行。"""

    __tablename__ = "kp_study_states"
    __table_args__ = (
        UniqueConstraint("user_id", "knowledge_point_id", name="uq_kp_state_user_kp"),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    knowledge_point_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_points.id"), index=True
    )
    state: Mapped[str] = mapped_column(String(20), default="未学习", index=True)
    evidence_count: Mapped[int] = mapped_column(Integer, default=0)
    last_event: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    mastered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class WrongQuestion(Base):
    """错题本：一生一错题一行，聚合多次作答并承载 SM-2 间隔复习调度。"""

    __tablename__ = "wrong_questions"
    __table_args__ = (
        UniqueConstraint("user_id", "question_id", name="uq_wrong_user_question"),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), index=True)
    wrong_count: Mapped[int] = mapped_column(Integer, default=1)
    correct_streak: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    # SM-2 Lite 调度字段
    ease_factor: Mapped[float] = mapped_column(default=2.5)
    interval_days: Mapped[int] = mapped_column(Integer, default=1)
    reps: Mapped[int] = mapped_column(Integer, default=0)
    lapses: Mapped[int] = mapped_column(Integer, default=0)
    next_review_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    last_wrong_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    wrong_reason: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PracticeSession(Base):
    """练习会话：支撑断点续答与结算（D-04 §11）。"""

    __tablename__ = "practice_sessions"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    mode: Mapped[str] = mapped_column(String(20), default="special")
    scope_type: Mapped[str] = mapped_column(String(20), default="chapter")
    scope_ids: Mapped[Optional[list[int]]] = mapped_column(JSONType, nullable=True)
    question_ids: Mapped[list[int]] = mapped_column(JSONType, default=list)
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    answered_count: Mapped[int] = mapped_column(Integer, default=0)
    correct_count: Mapped[int] = mapped_column(Integer, default=0)
    seed: Mapped[int] = mapped_column(BigInteger)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
