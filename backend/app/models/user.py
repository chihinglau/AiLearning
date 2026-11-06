from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import settings
from app.db.base import Base
from app.db.types import JSONType


class User(Base):
    """学生 / 家长 / 管理员统一账号表。"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    nickname: Mapped[str] = mapped_column(String(50), default="")
    role: Mapped[str] = mapped_column(String(20), default="student", index=True)
    stage: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    grade: Mapped[Optional[int]] = mapped_column(nullable=True)
    school_id: Mapped[Optional[int]] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), nullable=True, index=True
    )
    grade_group: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    enrollment_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    region: Mapped[str] = mapped_column(
        String(20), nullable=False, default="shenzhen", server_default="shenzhen"
    )
    semester: Mapped[str] = mapped_column(
        String(10), nullable=False, default="first", server_default="first"
    )
    elective_subjects: Mapped[Optional[list]] = mapped_column(JSONType, nullable=True)
    grade_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    graduated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    token_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    teacher_subjects: Mapped[Optional[list]] = mapped_column(JSONType, nullable=True)
    grade_start: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    grade_end: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_child: Mapped[bool] = mapped_column(Boolean, default=False)
    daily_limit_minutes: Mapped[int] = mapped_column(
        Integer, default=settings.default_daily_limit_minutes
    )
    teen_mode: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="0", nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class GradeHistory(Base):
    """年级变更/升级历史；(user_id, to_grade, school_year) 唯一保证升级幂等。"""

    __tablename__ = "grade_histories"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "to_grade", "school_year", name="uq_grade_history_user_target_year"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    from_grade: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    to_grade: Mapped[int] = mapped_column(Integer, nullable=False)
    school_year: Mapped[str] = mapped_column(String(20), nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="self")
    reason: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    operator_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ParentChildBinding(Base):
    """家长-孩子绑定关系；儿童账号需家长确认后方可完整使用。"""

    __tablename__ = "parent_child_bindings"
    __table_args__ = (UniqueConstraint("parent_id", "child_id", name="uq_parent_child"),)

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    parent_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    relation: Mapped[str] = mapped_column(String(20), default="parent")
    status: Mapped[str] = mapped_column(String(20), default="pending")
    consent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    """合规审计日志：账号、内容、支付等敏感操作留痕。"""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(64), index=True)
    detail: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    ip: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
