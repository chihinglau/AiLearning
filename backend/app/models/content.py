from datetime import datetime
from typing import Any, List, Optional

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import JSONType


class Textbook(Base):
    """教材版本，如「人教版 / 牛津深圳版」；深圳本地化教材在此登记。"""

    __tablename__ = "textbooks"
    __table_args__ = (
        UniqueConstraint("subject", "grade", "version", "semester", name="uq_textbook"),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    subject: Mapped[str] = mapped_column(String(20), index=True)
    grade: Mapped[int] = mapped_column(index=True)
    version: Mapped[str] = mapped_column(String(50))
    semester: Mapped[str] = mapped_column(String(10), default="first")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


class Chapter(Base):
    __tablename__ = "chapters"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    textbook_id: Mapped[int] = mapped_column(ForeignKey("textbooks.id"), index=True)
    grade: Mapped[int] = mapped_column(index=True)
    name: Mapped[str] = mapped_column(String(100))
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    chapter_id: Mapped[int] = mapped_column(ForeignKey("chapters.id"), index=True)
    knowledge_point_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("knowledge_points.id"), nullable=True, index=True
    )
    subject: Mapped[str] = mapped_column(String(20), index=True)
    q_type: Mapped[str] = mapped_column(String(20), default="choice")
    content: Mapped[dict[str, Any]] = mapped_column(JSONType)
    options: Mapped[Optional[List[Any]]] = mapped_column(JSONType, nullable=True)
    answer: Mapped[dict[str, Any]] = mapped_column(JSONType)
    analysis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    difficulty: Mapped[int] = mapped_column(Integer, default=3)
    tags: Mapped[Optional[List[str]]] = mapped_column(JSONType, nullable=True)
    # P2-09 内容复核：draft（待审核）/published（已发布）/offline（已下架）
    status: Mapped[str] = mapped_column(
        String(20), default="published", server_default="published", index=True
    )
    # CT-02 内容来源与版权登记：original/adapted/licensed/public/external
    source_type: Mapped[str] = mapped_column(
        String(20), default="original", server_default="original"
    )
    source_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    source_ref: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    copyright_owner: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    license_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    adapted_from: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


class KnowledgePoint(Base):
    """知识点图谱，parent_id 自关联构建层级树。

    node_type：`section` 为单元下的节（L2，parent_id 为空），`point` 为最小学习单位（L3）。
    """

    __tablename__ = "knowledge_points"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    subject: Mapped[str] = mapped_column(String(20), index=True)
    name: Mapped[str] = mapped_column(String(100))
    parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("knowledge_points.id"), nullable=True, index=True
    )
    grade: Mapped[Optional[int]] = mapped_column(index=True, nullable=True)
    node_type: Mapped[str] = mapped_column(
        String(20), default="point", server_default="point", index=True
    )
    order_index: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    weight: Mapped[float] = mapped_column(default=1.0, server_default="1.0")
    prerequisites: Mapped[Optional[List[int]]] = mapped_column(JSONType, nullable=True)
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # CT-02 讲解来源登记（教材原文引用需标注版权方与授权说明）
    source_type: Mapped[str] = mapped_column(
        String(20), default="original", server_default="original"
    )
    source_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    source_ref: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    copyright_owner: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    license_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
