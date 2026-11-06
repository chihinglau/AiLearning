from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TextbookBinding(Base):
    """学生-教材绑定（D-04 §9.3）：按学科+学期保留，历史学期归档。"""

    __tablename__ = "textbook_bindings"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "subject", "semester", "textbook_id", name="uq_textbook_binding"
        ),
        Index("ix_binding_user_subject", "user_id", "subject", "status"),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    subject: Mapped[str] = mapped_column(String(20))
    textbook_id: Mapped[int] = mapped_column(ForeignKey("textbooks.id"))
    semester: Mapped[str] = mapped_column(String(10), default="first")
    source: Mapped[str] = mapped_column(String(20), default="auto")
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    bound_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
