"""P1-04 管理端用户列表与角色授予/回收（D-03 §10.3）。"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import has_permission, require_permission
from app.core.permissions import ALL_PERMISSIONS, ROLE_PERMISSIONS, normalize_role
from app.core.scope import mask_phone
from app.core.security import bump_token_version
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import (
    AdminUserListOut,
    AdminUserOut,
    RoleChangeIn,
    RoleChangeOut,
)
from app.services.audit import record_audit
from app.services.rbac import sync_user_role

router = APIRouter(prefix="/admin", tags=["管理端"])

SCHOOL_MANAGED_ROLES = frozenset({"student", "teacher", "head_teacher"})
PRIVILEGED_ROLES = frozenset({"super_admin", "admin", "school_admin"})


def _forbidden(code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"code": code, "message": message},
    )


def _is_super(user: User, db: Optional[Session] = None) -> bool:
    return has_permission(user, ALL_PERMISSIONS, db)


def _to_out(user: User) -> AdminUserOut:
    return AdminUserOut(
        id=user.id,
        phone_masked=mask_phone(user.phone) or "",
        nickname=user.nickname,
        role=user.role,
        school_id=user.school_id,
        grade=user.grade,
        grade_group=user.grade_group,
        teacher_subjects=user.teacher_subjects,
        grade_start=user.grade_start,
        grade_end=user.grade_end,
        is_active=user.is_active,
    )


@router.get("/users", response_model=AdminUserListOut)
def list_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    role: Optional[str] = Query(default=None, max_length=20),
    school_id: Optional[int] = Query(default=None),
    grade: Optional[int] = Query(default=None, ge=1, le=12),
    keyword: Optional[str] = Query(default=None, max_length=40),
    current: User = Depends(require_permission("admin:user:manage")),
    db: Session = Depends(get_db),
) -> AdminUserListOut:
    filters = []
    if not _is_super(current, db):
        if current.school_id is None:
            raise _forbidden("SCHOOL_UNBOUND", "账号未绑定学校")
        filters.append(User.school_id == current.school_id)
    elif school_id is not None:
        filters.append(User.school_id == school_id)
    if role:
        filters.append(User.role == role)
    if grade is not None:
        filters.append(User.grade == grade)
    if keyword:
        pattern = f"%{keyword.strip()}%"
        filters.append(or_(User.phone.like(pattern), User.nickname.like(pattern)))

    total = int(db.scalar(select(func.count()).select_from(User).where(*filters)) or 0)
    users = list(
        db.scalars(
            select(User)
            .where(*filters)
            .order_by(User.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return AdminUserListOut(
        total=total,
        page=page,
        page_size=page_size,
        items=[_to_out(user) for user in users],
    )


@router.post("/users/{user_id}/roles", response_model=RoleChangeOut)
def change_user_roles(
    user_id: int,
    payload: RoleChangeIn,
    current: User = Depends(require_permission("admin:role:assign")),
    db: Session = Depends(get_db),
) -> RoleChangeOut:
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    if target.id == current.id:
        raise _forbidden("SELF_ROLE_DENIED", "不能修改自己的角色")
    if not _is_super(current, db):
        if target.school_id != current.school_id:
            raise _forbidden("CROSS_SCHOOL", "无权操作其他学校用户")
        if normalize_role(target.role) in PRIVILEGED_ROLES:
            raise _forbidden("ROLE_NOT_ALLOWED", "无权管理该角色账号")

    if payload.grant and payload.revoke:
        raise HTTPException(
            status_code=422,
            detail={"code": "ROLE_CONFLICT", "message": "grant 与 revoke 不能同时提交"},
        )
    if not payload.grant and not payload.revoke:
        raise HTTPException(
            status_code=422,
            detail={"code": "ROLE_REQUIRED", "message": "请指定 grant 或 revoke"},
        )

    before = {"role": target.role}
    if payload.grant:
        if len(payload.grant) != 1:
            raise HTTPException(
                status_code=422,
                detail={"code": "MULTIPLE_GRANT", "message": "一次只能授予一个角色"},
            )
        role = normalize_role(payload.grant[0])
        if role not in ROLE_PERMISSIONS:
            raise HTTPException(
                status_code=422,
                detail={"code": "ROLE_INVALID", "message": "角色不存在"},
            )
        if not _is_super(current, db) and role not in SCHOOL_MANAGED_ROLES:
            raise _forbidden("ROLE_NOT_ALLOWED", "校管只能授予学生/教师/班主任")
        if role == "super_admin" and not _is_super(current, db):
            raise _forbidden("ROLE_NOT_ALLOWED", "无权授予超管")
        new_role = role
    else:
        if len(payload.revoke) != 1:
            raise HTTPException(
                status_code=422,
                detail={"code": "MULTIPLE_REVOKE", "message": "一次只能回收一个角色"},
            )
        revoke_role = normalize_role(payload.revoke[0])
        if revoke_role != normalize_role(target.role):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "ROLE_MISMATCH", "message": "该用户未持有待回收角色"},
            )
        if revoke_role in PRIVILEGED_ROLES and not _is_super(current, db):
            raise _forbidden("ROLE_NOT_ALLOWED", "无权回收该角色")
        new_role = "student"

    if normalize_role(target.role) == new_role:
        return RoleChangeOut(
            id=target.id, role=target.role, token_version=target.token_version
        )

    target.role = new_role
    sync_user_role(db, target, new_role, granted_by=current.id)
    token_version = bump_token_version(target)
    db.commit()
    db.refresh(target)
    record_audit(
        db,
        user_id=current.id,
        action="admin.role.assign",
        before=before,
        after={"role": target.role},
    )
    return RoleChangeOut(
        id=target.id, role=target.role, token_version=token_version
    )
