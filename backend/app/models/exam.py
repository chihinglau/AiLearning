from datetime import datetime
from typing import Any, Optional

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import JSONType


class ExamBlueprint(Base):
    """试卷蓝图：题型分节 + 分值 + 难度分布 + 覆盖约束（P0-25）。"""

    __tablename__ = "exam_blueprints"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    subject: Mapped[str] = mapped_column(String(20), index=True)
    grade: Mapped[Optional[int]] = mapped_column(nullable=True, index=True)
    exam_type: Mapped[str] = mapped_column(String(20), default="unit", index=True)
    total_score: Mapped[int] = mapped_column(Integer, default=100)
    time_limit_min: Mapped[int] = mapped_column(Integer, default=60)
    sections: Mapped[list[dict[str, Any]]] = mapped_column(JSONType, default=list)
    kp_coverage_min: Mapped[float] = mapped_column(default=0.8)
    difficulty_mix: Mapped[dict[str, float]] = mapped_column(JSONType, default=dict)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Exam(Base):
    """试卷：模考卷 / 单元测 / 期中期末（由蓝图生成或人工录入）。"""

    __tablename__ = "exams"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    subject: Mapped[str] = mapped_column(String(20), index=True)
    grade: Mapped[int] = mapped_column(index=True)
    year: Mapped[Optional[int]] = mapped_column(nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="mock")
    total_score: Mapped[int] = mapped_column(Integer, default=100)
    time_limit_min: Mapped[int] = mapped_column(Integer, default=90)
    questions: Mapped[list[Any]] = mapped_column(JSONType)
    # P0-27 考试闭环扩展
    blueprint_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("exam_blueprints.id"), nullable=True, index=True
    )
    exam_type: Mapped[str] = mapped_column(String(20), default="mock", index=True)
    chapter_ids: Mapped[Optional[list[int]]] = mapped_column(JSONType, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="published", index=True)
    # P1-08 考试窗口：为空表示不限时段
    window_start: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    window_end: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ExamAttempt(Base):
    """一次考试作答（支持断点续答、幂等交卷与批改状态）。"""

    __tablename__ = "exam_attempts"
    __table_args__ = (
        UniqueConstraint("user_id", "exam_id", "seed", name="uq_attempt_user_exam_seed"),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id"), index=True)
    seed: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(20), default="in_progress", index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    objective_score: Mapped[float] = mapped_column(default=0.0)
    subjective_score: Mapped[Optional[float]] = mapped_column(nullable=True)
    total_score: Mapped[Optional[float]] = mapped_column(nullable=True)
    submit_token: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)


class ExamAnswer(Base):
    """考试逐题作答与判分（主观题保留自评分）。"""

    __tablename__ = "exam_answers"
    __table_args__ = (
        UniqueConstraint("attempt_id", "question_id", name="uq_answer_attempt_question"),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    attempt_id: Mapped[int] = mapped_column(ForeignKey("exam_attempts.id"), index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), index=True)
    user_answer: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONType, nullable=True)
    is_correct: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    score: Mapped[Optional[float]] = mapped_column(nullable=True)
    self_score: Mapped[Optional[float]] = mapped_column(nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ExamSubmission(Base):
    __tablename__ = "exam_submissions"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id"), index=True)
    answers: Mapped[dict[str, Any]] = mapped_column(JSONType)
    score: Mapped[float] = mapped_column(default=0.0)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
