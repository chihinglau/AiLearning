from typing import Optional

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.permissions import (
    ALL_PERMISSIONS,
    SCOPE_SELF,
    permissions_for_role,
    scope_for_role,
)
from app.core.scope import (
    StudentAccess,
    ensure_student_access,
    resolve_student_ids,
    scope_for_permission,
)
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_prefix}/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    subject = decode_access_token(token)
    if subject is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录状态已失效，请重新登录",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user: Optional[User] = db.get(User, int(subject)) if subject.isdigit() else None
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号不存在或已停用")
    return user


def has_permission(user: User, permission: str) -> bool:
    perms = permissions_for_role(user.role)
    return ALL_PERMISSIONS in perms or permission in perms


def current_user_permissions(user: User) -> list[str]:
    perms = permissions_for_role(user.role)
    if ALL_PERMISSIONS in perms:
        return [ALL_PERMISSIONS]
    return sorted(perms)


def require_permission(*required: str):
    """声明式权限依赖：要求当前用户具备全部指定权限点。"""

    def dependency(current: User = Depends(get_current_user)) -> User:
        perms = permissions_for_role(current.role)
        if ALL_PERMISSIONS not in perms and not all(p in perms for p in required):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "PERMISSION_DENIED", "message": "权限不足"},
            )
        return current

    return dependency


def require_admin(current: User = Depends(get_current_user)) -> User:
    """兼容改造：历史 admin 映射 super_admin；保持"全量权限"语义。"""
    if not has_permission(current, ALL_PERMISSIONS):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
    return current


def current_user_scope(user: User) -> str:
    return scope_for_role(user.role)


def require_student_access(permission: str):
    """声明式数据范围依赖：校验权限点并按角色范围解析目标学生。"""

    def dependency(
        student_id: Optional[int] = Query(default=None, ge=1),
        current: User = Depends(require_permission(permission)),
        db: Session = Depends(get_db),
    ) -> StudentAccess:
        scope = scope_for_permission(current.role, permission)
        if scope is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "SCOPE_DENIED", "message": "无权访问该学生数据"},
            )
        allowed = resolve_student_ids(db, current, scope)
        # 直接调用（单测）时 Query 默认值是标记对象，统一归一化为 None
        requested = student_id if isinstance(student_id, int) else None
        target = requested
        if target is None and scope == SCOPE_SELF:
            target = current.id
        if requested is not None:
            ensure_student_access(db, current, scope, requested)
        return StudentAccess(scope=scope, student_id=target, allowed_ids=allowed)

    return dependency
