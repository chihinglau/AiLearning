"""数据访问范围解析与脱敏工具，见 D-03 §6。"""

from dataclasses import dataclass
from typing import Literal, Optional

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.permissions import (
    ALL_PERMISSIONS,
    PERMISSION_SCOPE,
    SCOPE_ALL,
    SCOPE_CHILD,
    SCOPE_CLASS,
    SCOPE_NONE,
    SCOPE_SCHOOL,
    SCOPE_SELF,
    permissions_for_role,
    scope_for_role,
)
from app.models.org import ClassMember, SchoolClass, TeacherClassAssignment
from app.models.user import ParentChildBinding, User

Scope = Literal["NONE", "SELF", "CHILD", "CLASS", "SCHOOL", "ALL"]


@dataclass(frozen=True)
class StudentAccess:
    """鉴权结果：目标学生（None 表示聚合查询）与允许集合（None 表示不限制）。"""

    scope: str
    student_id: Optional[int]
    allowed_ids: Optional[set[int]]


def scope_for_permission(role: str, permission: str) -> Optional[str]:
    """按"请求所需权限"选择角色对应的数据范围，不做跨权限并集提权。"""
    perms = permissions_for_role(role)
    if ALL_PERMISSIONS in perms:
        return SCOPE_ALL
    if permission not in perms:
        return None
    role_scope = scope_for_role(role)
    if role_scope in PERMISSION_SCOPE.get(permission, ()):
        return role_scope
    return None


def teacher_class_ids(db: Session, actor: User, subject: Optional[str] = None) -> set[int]:
    """教师可见班级：班主任所在班（全学科）+ 授课分配（按学科收窄）。"""
    if actor.school_id is None:
        return set()
    head_ids = set(
        db.scalars(
            select(SchoolClass.id).where(
                SchoolClass.head_teacher_id == actor.id,
                SchoolClass.school_id == actor.school_id,
            )
        )
    )
    stmt = (
        select(TeacherClassAssignment.class_id)
        .join(SchoolClass, SchoolClass.id == TeacherClassAssignment.class_id)
        .where(
            TeacherClassAssignment.teacher_id == actor.id,
            SchoolClass.school_id == actor.school_id,
        )
    )
    if subject:
        stmt = stmt.where(
            or_(
                TeacherClassAssignment.subject == subject,
                TeacherClassAssignment.role_in_class == "head_teacher",
            )
        )
    return head_ids | set(db.scalars(stmt))


def resolve_student_ids(
    db: Session, actor: User, scope: str, subject: Optional[str] = None
) -> Optional[set[int]]:
    """返回允许访问的 student_id 集合；None 表示不限制（ALL）。"""
    if scope == SCOPE_ALL:
        return None
    if scope == SCOPE_SELF:
        return {actor.id}
    if scope == SCOPE_CHILD:
        rows = db.scalars(
            select(ParentChildBinding.child_id).where(
                ParentChildBinding.parent_id == actor.id,
                ParentChildBinding.status == "active",
            )
        )
        return set(rows)
    if scope == SCOPE_CLASS:
        class_ids = teacher_class_ids(db, actor, subject)
        if not class_ids:
            return set()
        rows = db.scalars(
            select(ClassMember.student_id).where(ClassMember.class_id.in_(class_ids))
        )
        return set(rows)
    if scope == SCOPE_SCHOOL:
        if actor.school_id is None:
            return set()
        rows = db.scalars(
            select(User.id).where(
                User.school_id == actor.school_id,
                User.role == "student",
            )
        )
        return set(rows)
    if scope == SCOPE_NONE:
        return set()
    return set()


def ensure_student_access(
    db: Session, actor: User, scope: str, student_id: int, subject: Optional[str] = None
) -> None:
    allowed = resolve_student_ids(db, actor, scope, subject)
    if allowed is not None and student_id not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "SCOPE_DENIED", "message": "无权访问该学生数据"},
        )


def mask_phone(phone: Optional[str]) -> Optional[str]:
    """手机号脱敏：保留前 3 位与后 4 位。"""
    if not phone:
        return phone
    if len(phone) < 8:
        return "*" * len(phone)
    return f"{phone[:3]}****{phone[-4:]}"
