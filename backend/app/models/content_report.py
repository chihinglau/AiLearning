"""内容举报与下架处理（R-07，D-08 缺口 6）。"""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ContentReport(Base):
    """用户举报：待处理 → 下架 / 驳回，处理动作写入审计。"""

    __tablename__ = "content_reports"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True
    )
    reporter_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    target_type: Mapped[str] = mapped_column(String(20), index=True)
    target_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, index=True
    )
    reason: Mapped[str] = mapped_column(String(30))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    handled_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    handled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    handle_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
