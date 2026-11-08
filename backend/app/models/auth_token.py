from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RefreshToken(Base):
    """刷新令牌：支持轮换、重用检测与按登录族整族撤销。

    token 本体不落库，仅保存 sha256 摘要；同一次登录的轮换链共享 family_id。
    """

    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    family_id: Mapped[str] = mapped_column(String(64), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    token_version: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    replaced_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("refresh_tokens.id"), nullable=True
    )
    ip: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
