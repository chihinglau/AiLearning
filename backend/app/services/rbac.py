"""RBAC 数据表双写、权限读取与对账，见 D-03 §9.2 阶段 A/B。

当前处于 **阶段 B**：
- 写入：`users.role` 仍是主角色缓存，注册/角色变更时同步写 `user_roles`；
- 读取：优先 `user_roles`，无记录时回退 `users.role` 与常量表；
- 对账：`reconcile()` 比对常量目录与数据库、`users.role` 与 `user_roles`，可一键修复。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.permissions import (
    ALL_PERMISSIONS,
    PERMISSIONS,
    ROLE_INFO,
    ROLE_PERMISSIONS,
    normalize_role,
    permissions_for_role,
    scope_for_role,
)
from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.user import User

WILDCARD_DOMAIN = "system"
WILDCARD_DESCRIPTION = "全部权限（通配）"


def permission_catalog() -> Dict[str, Tuple[str, Optional[str]]]:
    """权限点常量目录：code → (domain, description)，额外包含超管通配 `*`。"""
    catalog: Dict[str, Tuple[str, Optional[str]]] = {
        code: (code.split(":")[0], None) for code in PERMISSIONS
    }
    catalog[ALL_PERMISSIONS] = (WILDCARD_DOMAIN, WILDCARD_DESCRIPTION)
    return catalog


def sync_catalog(db: Session, prune: bool = False) -> Dict[str, int]:
    """把常量角色/权限/授权关系同步到数据表（幂等）。

    `prune=True` 时删除数据库中多余的角色授权关系（用于对账修复）；
    默认只补齐、不删除，避免覆盖后续权限配置后台的调整。
    """
    stats = {
        "roles_created": 0,
        "roles_updated": 0,
        "permissions_created": 0,
        "permissions_updated": 0,
        "links_created": 0,
        "links_removed": 0,
    }

    roles = {role.code: role for role in db.scalars(select(Role))}
    for code, (name, level) in ROLE_INFO.items():
        role = roles.get(code)
        if role is None:
            role = Role(code=code, name=name, level=level, is_system=True)
            db.add(role)
            db.flush()
            roles[code] = role
            stats["roles_created"] += 1
        elif role.name != name or role.level != level or not role.is_system:
            role.name = name
            role.level = level
            role.is_system = True
            stats["roles_updated"] += 1

    permissions = {permission.code: permission for permission in db.scalars(select(Permission))}
    for code, (domain, description) in permission_catalog().items():
        permission = permissions.get(code)
        if permission is None:
            permission = Permission(code=code, domain=domain, description=description)
            db.add(permission)
            db.flush()
            permissions[code] = permission
            stats["permissions_created"] += 1
        elif permission.domain != domain or permission.description != description:
            permission.domain = domain
            permission.description = description
            stats["permissions_updated"] += 1

    desired = {
        (roles[role_code].id, permissions[permission_code].id)
        for role_code, permission_codes in ROLE_PERMISSIONS.items()
        for permission_code in permission_codes
        if permission_code in permissions
    }
    existing = {
        (int(role_id), int(permission_id))
        for role_id, permission_id in db.execute(
            select(RolePermission.role_id, RolePermission.permission_id)
        ).all()
    }
    for role_id, permission_id in desired - existing:
        db.add(RolePermission(role_id=role_id, permission_id=permission_id))
        stats["links_created"] += 1
    if prune:
        for role_id, permission_id in existing - desired:
            db.execute(
                delete(RolePermission).where(
                    RolePermission.role_id == role_id,
                    RolePermission.permission_id == permission_id,
                )
            )
            stats["links_removed"] += 1

    db.flush()
    return stats


def role_codes_for_user(db: Session, user: User) -> Set[str]:
    """当前用户角色集合：优先 `user_roles`，无记录回退 `users.role`。"""
    codes = set(
        db.scalars(
            select(Role.code)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user.id)
        )
    )
    if codes:
        return codes
    return {normalize_role(user.role)}


def effective_role(db: Session, user: User) -> str:
    """主角色：优先 `user_roles.is_primary`，其次任意已授予角色，最后回退 `users.role`。"""
    primary = db.scalar(
        select(Role.code)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user.id, UserRole.is_primary.is_(True))
        .limit(1)
    )
    if primary:
        return primary
    any_role = db.scalar(
        select(Role.code)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user.id)
        .order_by(Role.id)
        .limit(1)
    )
    return any_role or normalize_role(user.role)


def effective_permissions(db: Session, user: User) -> List[str]:
    """有效权限点集合：并集读取 `role_permissions`，数据表为空时回退常量表。"""
    codes = role_codes_for_user(db, user)
    if ALL_PERMISSIONS in codes:
        return [ALL_PERMISSIONS]
    role_ids = list(
        db.scalars(select(Role.id).where(Role.code.in_(codes)))
    )
    permission_codes = list(
        db.scalars(
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id.in_(role_ids))
        )
    )
    if ALL_PERMISSIONS in permission_codes:
        return [ALL_PERMISSIONS]
    if permission_codes:
        return sorted(permission_codes)
    merged: Set[str] = set()
    for code in codes:
        merged |= permissions_for_role(code)
    if ALL_PERMISSIONS in merged:
        return [ALL_PERMISSIONS]
    return sorted(merged)


def effective_scope(db: Session, user: User) -> str:
    return scope_for_role(effective_role(db, user))


def sync_user_role(
    db: Session, user: User, role: Optional[str] = None, granted_by: Optional[int] = None
) -> Optional[str]:
    """双写单主角色：先清空该用户授予关系，再写入主角色（`users.role` 由调用方维护）。

    角色目录尚未初始化（如测试库未执行 seed）时返回 None，不做写入。
    """
    code = normalize_role(role or user.role)
    role_row = db.scalar(select(Role).where(Role.code == code))
    if role_row is None:
        return None
    db.execute(delete(UserRole).where(UserRole.user_id == user.id))
    db.add(
        UserRole(
            user_id=user.id,
            role_id=role_row.id,
            is_primary=True,
            granted_by=granted_by,
            granted_at=datetime.utcnow(),
        )
    )
    db.flush()
    return code


def backfill_user_roles(db: Session) -> int:
    """为缺少 `user_roles` 记录的存量用户按 `users.role` 补齐，返回补齐数量。"""
    existing_ids = set(db.scalars(select(UserRole.user_id)))
    count = 0
    for user in db.scalars(select(User).order_by(User.id)):
        if user.id in existing_ids:
            continue
        if sync_user_role(db, user) is not None:
            count += 1
    return count


def _catalog_report(db: Session) -> Dict[str, Any]:
    roles = {role.code: role for role in db.scalars(select(Role))}
    permissions = {permission.code: permission for permission in db.scalars(select(Permission))}
    desired_links = {
        (role_code, permission_code)
        for role_code, permission_codes in ROLE_PERMISSIONS.items()
        for permission_code in permission_codes
    }
    role_code_by_id = {role.id: role.code for role in roles.values()}
    permission_code_by_id = {permission.id: permission.code for permission in permissions.values()}
    existing_links = {
        (role_code_by_id.get(int(role_id)), permission_code_by_id.get(int(permission_id)))
        for role_id, permission_id in db.execute(
            select(RolePermission.role_id, RolePermission.permission_id)
        ).all()
    }
    return {
        "roles_missing": sorted(set(ROLE_INFO) - set(roles)),
        "roles_extra": sorted(set(roles) - set(ROLE_INFO)),
        "permissions_missing": sorted(set(permission_catalog()) - set(permissions)),
        "permissions_extra": sorted(set(permissions) - set(permission_catalog())),
        "links_missing": len(desired_links - existing_links),
        "links_extra": len(existing_links - desired_links),
    }


def _user_role_report(db: Session) -> Dict[str, Any]:
    user_ids_with_roles = set(db.scalars(select(UserRole.user_id)))
    missing: List[int] = []
    mismatched: List[Dict[str, Any]] = []
    for user in db.scalars(select(User).order_by(User.id)):
        if user.id not in user_ids_with_roles:
            missing.append(user.id)
            continue
        expected = normalize_role(user.role)
        current = effective_role(db, user)
        if current != expected:
            mismatched.append(
                {
                    "user_id": user.id,
                    "users_role": user.role,
                    "user_roles_role": current,
                }
            )
    return {"missing": missing, "mismatched": mismatched}


def reconcile(db: Session, fix: bool = False) -> Dict[str, Any]:
    """对账：比对常量目录与数据库、`users.role` 与 `user_roles`。

    `fix=True` 时先把常量目录同步到数据表（含删除多余授权关系），
    再补齐缺失 `user_roles`，并把与 `users.role` 不一致的授予关系对齐到 `users.role`
    （阶段 B 以 `users.role` 为写入事实源，阶段 C 切换后再反转）。
    """
    if fix:
        sync_catalog(db, prune=True)
        backfill_user_roles(db)
        for user in db.scalars(select(User).order_by(User.id)):
            current = effective_role(db, user)
            expected = normalize_role(user.role)
            if current != expected:
                sync_user_role(db, user, user.role)
        db.flush()

    return {"catalog": _catalog_report(db), "user_roles": _user_role_report(db)}


def has_drift(report: Dict[str, Any]) -> bool:
    catalog = report["catalog"]
    user_roles = report["user_roles"]
    return bool(
        catalog["roles_missing"]
        or catalog["roles_extra"]
        or catalog["permissions_missing"]
        or catalog["permissions_extra"]
        or catalog["links_missing"]
        or catalog["links_extra"]
        or user_roles["missing"]
        or user_roles["mismatched"]
    )
