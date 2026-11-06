from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.permissions import (
    ALL_PERMISSIONS,
    permissions_for_role,
    scope_for_role,
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
