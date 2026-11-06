"""P2-02 权限配置后台：角色-权限可视化读取与调整（D-03 §9.1）。"""

from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.permissions import normalize_role
from app.db.session import get_db
from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.user import User
from app.schemas.rbac import (
    PermissionListOut,
    PermissionOut,
    RoleListOut,
    RolePermissionOut,
    RolePermissionsIn,
    RolePermissionsOut,
)
from app.services.audit import record_audit
from app.services.rbac import sync_catalog

router = APIRouter(prefix="/admin/rbac", tags=["管理端-RBAC"])

IMMUTABLE_ROLES = frozenset({"super_admin"})


def _ensure_catalog(db: Session) -> None:
    """数据表为空（未执行 seed/迁移回填）时按常量目录初始化，保证后台可用。"""
    if int(db.scalar(select(func.count()).select_from(Role)) or 0) == 0:
        sync_catalog(db)
        db.commit()


def _role_permission_codes(db: Session, role_id: int) -> List[str]:
    return sorted(
        db.scalars(
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id == role_id)
        )
    )


def _permission_role_codes(db: Session) -> Dict[int, List[str]]:
    mapping: Dict[int, List[str]] = {}
    rows = db.execute(
        select(RolePermission.permission_id, Role.code).join(
            Role, Role.id == RolePermission.role_id
        )
    ).all()
    for permission_id, role_code in rows:
        mapping.setdefault(int(permission_id), []).append(role_code)
    return mapping


@router.get("/roles", response_model=RoleListOut)
def list_roles(
    current: User = Depends(require_permission("system:config:write")),
    db: Session = Depends(get_db),
) -> RoleListOut:
    _ensure_catalog(db)
    counts = {
        int(role_id): int(total)
        for role_id, total in db.execute(
            select(UserRole.role_id, func.count()).group_by(UserRole.role_id)
        ).all()
    }
    roles = list(db.scalars(select(Role).order_by(Role.id)))
    return RoleListOut(
        items=[
            RolePermissionOut(
                code=role.code,
                name=role.name,
                level=role.level,
                is_system=role.is_system,
                is_editable=role.code not in IMMUTABLE_ROLES,
                user_count=counts.get(role.id, 0),
                permissions=_role_permission_codes(db, role.id),
            )
            for role in roles
        ]
    )


@router.get("/permissions", response_model=PermissionListOut)
def list_permissions(
    current: User = Depends(require_permission("system:config:write")),
    db: Session = Depends(get_db),
) -> PermissionListOut:
    _ensure_catalog(db)
    permission_roles = _permission_role_codes(db)
    permissions = list(db.scalars(select(Permission).order_by(Permission.id)))
    domains: List[str] = []
    for permission in permissions:
        if permission.domain not in domains:
            domains.append(permission.domain)
    return PermissionListOut(
        domains=domains,
        items=[
            PermissionOut(
                code=permission.code,
                domain=permission.domain,
                description=permission.description,
                roles=sorted(permission_roles.get(permission.id, [])),
            )
            for permission in permissions
        ]
    )


@router.put("/roles/{role_code}/permissions", response_model=RolePermissionsOut)
def update_role_permissions(
    role_code: str,
    payload: RolePermissionsIn,
    current: User = Depends(require_permission("system:config:write")),
    db: Session = Depends(get_db),
) -> RolePermissionsOut:
    _ensure_catalog(db)
    code = normalize_role(role_code)
    role = db.scalar(select(Role).where(Role.code == code))
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ROLE_NOT_FOUND", "message": "角色不存在"},
        )
    if code in IMMUTABLE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "ROLE_IMMUTABLE", "message": "超管角色固定拥有全部权限"},
        )

    permission_rows = {
        permission.code: permission for permission in db.scalars(select(Permission))
    }
    unknown = sorted({item for item in payload.permissions if item not in permission_rows})
    if unknown:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "PERMISSION_UNKNOWN",
                "message": f"未知权限点：{', '.join(unknown[:5])}",
            },
        )
    if "*" in payload.permissions:
        raise HTTPException(
            status_code=422,
            detail={"code": "PERMISSION_UNKNOWN", "message": "通配权限不可单独授予"},
        )

    current_codes = set(_role_permission_codes(db, role.id))
    desired_codes = set(payload.permissions)
    added = sorted(desired_codes - current_codes)
    removed = sorted(current_codes - desired_codes)

    for permission_code in removed:
        db.execute(
            delete(RolePermission).where(
                RolePermission.role_id == role.id,
                RolePermission.permission_id == permission_rows[permission_code].id,
            )
        )
    for permission_code in added:
        db.add(
            RolePermission(
                role_id=role.id,
                permission_id=permission_rows[permission_code].id,
            )
        )
    db.commit()

    if added or removed:
        record_audit(
            db,
            user_id=current.id,
            action="rbac.role.permissions",
            before={"role": code, "permissions": sorted(current_codes)},
            after={"role": code, "permissions": sorted(desired_codes)},
        )

    return RolePermissionsOut(
        code=code,
        permissions=sorted(desired_codes),
        added=added,
        removed=removed,
    )
