from typing import Optional, Sequence, Union

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.permissions import (
    ALL_PERMISSIONS,
    PERMISSION_SCOPE,
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
from app.services.audit import record_audit
from app.services.rbac import effective_permissions, effective_role, effective_scope

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_prefix}/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    data = decode_access_token(token)
    if data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录状态已失效，请重新登录",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user: Optional[User] = db.get(User, int(data.subject)) if data.subject.isdigit() else None
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号不存在或已停用")
    if (user.token_version or 0) != data.version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "TOKEN_REVOKED", "message": "登录状态已失效，请重新登录"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def _db_or_none(db: object) -> Optional[Session]:
    """直接调用依赖函数（单测）时 db 可能是 Depends 标记，统一降级为常量回退。"""
    return db if isinstance(db, Session) else None


def has_permission(user: User, permission: str, db: Optional[Session] = None) -> bool:
    """权限判断：有会话时优先读 `user_roles/role_permissions`，否则回退常量表。"""
    session = _db_or_none(db)
    if session is not None:
        perms = effective_permissions(session, user)
    else:
        perms = permissions_for_role(user.role)
    return ALL_PERMISSIONS in perms or permission in perms


def current_user_permissions(user: User, db: Optional[Session] = None) -> list[str]:
    session = _db_or_none(db)
    if session is not None:
        return effective_permissions(session, user)
    perms = permissions_for_role(user.role)
    if ALL_PERMISSIONS in perms:
        return [ALL_PERMISSIONS]
    return sorted(perms)


def require_permission(*required: str):
    """声明式权限依赖：要求当前用户具备全部指定权限点。"""

    def dependency(
        current: User = Depends(get_current_user), db: Session = Depends(get_db)
    ) -> User:
        perms = current_user_permissions(current, db)
        if ALL_PERMISSIONS not in perms and not all(p in perms for p in required):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "PERMISSION_DENIED", "message": "权限不足"},
            )
        return current

    return dependency


def require_any_permission(*required: str):
    """声明式权限依赖：满足任一权限点即可（用于多角色共用接口）。"""

    def dependency(
        current: User = Depends(get_current_user), db: Session = Depends(get_db)
    ) -> User:
        perms = current_user_permissions(current, db)
        if ALL_PERMISSIONS not in perms and not any(p in perms for p in required):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "PERMISSION_DENIED", "message": "权限不足"},
            )
        return current

    return dependency


def require_admin(
    current: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> User:
    """兼容改造：历史 admin 映射 super_admin；保持"全量权限"语义。"""
    if not has_permission(current, ALL_PERMISSIONS, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
    return current


def current_user_scope(user: User, db: Optional[Session] = None) -> str:
    session = _db_or_none(db)
    if session is not None:
        return effective_scope(session, user)
    return scope_for_role(user.role)


def _select_permission(role: str, permission: Union[str, Sequence[str]]) -> Optional[str]:
    """多候选权限点中，选与角色默认数据范围匹配的那一个。"""
    candidates = (permission,) if isinstance(permission, str) else tuple(permission)
    perms = permissions_for_role(role)
    if ALL_PERMISSIONS in perms:
        return candidates[0]
    role_scope = scope_for_role(role)
    available = [p for p in candidates if p in perms]
    for candidate in available:
        if role_scope in PERMISSION_SCOPE.get(candidate, ()):
            return candidate
    return available[0] if available else None


def require_student_access(permission: Union[str, Sequence[str]]):
    """声明式数据范围依赖：校验权限点并按角色范围解析目标学生。"""

    def dependency(
        student_id: Optional[int] = Query(default=None, ge=1),
        current: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> StudentAccess:
        role = effective_role(db, current) if isinstance(db, Session) else current.role
        chosen = _select_permission(role, permission)
        if chosen is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "PERMISSION_DENIED", "message": "权限不足"},
            )
        scope = scope_for_permission(role, chosen)
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
            if requested != current.id:
                record_audit(
                    db,
                    user_id=current.id,
                    action="data.cross_user_read",
                    message=f"permission={chosen}, target={requested}, scope={scope}",
                )
        return StudentAccess(scope=scope, student_id=target, allowed_ids=allowed)

    return dependency
