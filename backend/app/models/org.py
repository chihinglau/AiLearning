"""学校/班级/成员/授课分配模型，见 D-03 §9.1/§7.3。"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class School(Base):
    """学校（机构），校级管理员与班级均以 school_id 归属。"""

    __tablename__ = "schools"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    region: Mapped[str] = mapped_column(
        String(20), nullable=False, default="shenzhen", server_default="shenzhen"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SchoolClass(Base):
    """行政班；班主任通过 head_teacher_id 显式指定。"""

    __tablename__ = "classes"
    __table_args__ = (UniqueConstraint("school_id", "grade", "name", name="uq_class"),)

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False, index=True)
    grade: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    head_teacher_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    school_year: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ClassMember(Base):
    """班级学生名册；(class_id, student_id) 复合主键保证不重复入班。"""

    __tablename__ = "class_members"

    class_id: Mapped[int] = mapped_column(
        ForeignKey("classes.id"), primary_key=True, index=True
    )
    student_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), primary_key=True, index=True
    )
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TeacherClassAssignment(Base):
    """教师-班级-学科授课关系；班主任用 role_in_class=head_teacher 标识。"""

    __tablename__ = "teacher_class_assignments"
    __table_args__ = (
        UniqueConstraint("teacher_id", "class_id", "subject", name="uq_teacher_class_subject"),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(20), nullable=False)
    role_in_class: Mapped[str] = mapped_column(
        String(20), nullable=False, default="subject_teacher", server_default="subject_teacher"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
