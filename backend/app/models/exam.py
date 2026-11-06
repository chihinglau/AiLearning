from datetime import datetime
from typing import Any, Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String
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
    """模考卷：深圳一模/二模、历年真题等。"""

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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ExamSubmission(Base):
    __tablename__ = "exam_submissions"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id"), index=True)
    answers: Mapped[dict[str, Any]] = mapped_column(JSONType)
    score: Mapped[float] = mapped_column(default=0.0)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
