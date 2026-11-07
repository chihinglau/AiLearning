from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CrashReport(Base):
    """崩溃与错误监控记录（R-09）。

    App 侧异常与后端未捕获异常统一落到本表；`fingerprint` 用于同因聚合，
    `message/stack_trace` 入库前已脱敏截断（见 `services/telemetry.py`）。
    """

    __tablename__ = "crash_reports"
    __table_args__ = (
        Index("ix_crash_reports_fingerprint_created", "fingerprint", "created_at"),
        Index("ix_crash_reports_source_created", "source", "created_at"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True
    )
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    source: Mapped[str] = mapped_column(
        String(20), nullable=False, default="app", server_default="app"
    )
    platform: Mapped[str] = mapped_column(
        String(30), nullable=False, default="unknown", server_default="unknown"
    )
    app_version: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    os_version: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    device_model: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    route: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    error_type: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    stack_trace: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    fingerprint: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    request_id: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    ip: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, index=True
    )
