"""P2-01 RBAC 数据表：目录同步、双写、优先读取与对账用例。"""

from sqlalchemy import delete, func, select

from app.core.permissions import (
    ALL_PERMISSIONS,
    PERMISSIONS,
    ROLE_INFO,
    ROLE_PERMISSIONS,
)
from app.core.security import hash_password
from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.user import User
from app.services.rbac import (
    backfill_user_roles,
    effective_permissions,
    effective_role,
    has_drift,
    reconcile,
    sync_catalog,
    sync_user_role,
)

EXPECTED_LINKS = sum(len(codes) for codes in ROLE_PERMISSIONS.values())


def _create_user(db, phone: str, role: str) -> User:
    user = User(phone=phone, password_hash=hash_password("pass1234"), role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _login(client, phone: str) -> dict[str, str]:
    response = client.post("/api/auth/login", data={"username": phone, "password": "pass1234"})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_sync_catalog_idempotent(db) -> None:
    first = sync_catalog(db)
    db.commit()
    second = sync_catalog(db)
    db.commit()

    assert first["roles_created"] == len(ROLE_INFO)
    assert first["permissions_created"] == len(PERMISSIONS) + 1
    assert first["links_created"] == EXPECTED_LINKS
    assert second["roles_created"] == 0
    assert second["permissions_created"] == 0
    assert second["links_created"] == 0

    assert {role.code for role in db.scalars(select(Role))} == set(ROLE_INFO)
    assert len(list(db.scalars(select(Permission)))) == len(PERMISSIONS) + 1
    assert int(db.scalar(select(func.count()).select_from(RolePermission))) == EXPECTED_LINKS


def test_register_writes_user_roles(client, db) -> None:
    sync_catalog(db)
    db.commit()

    response = client.post(
        "/api/auth/register",
        json={"phone": "13700000001", "password": "pass1234", "grade": 3},
    )
    assert response.status_code == 201, response.text

    user = db.scalar(select(User).where(User.phone == "13700000001"))
    link = db.scalar(select(UserRole).where(UserRole.user_id == user.id))
    assert user.role == "student"
    assert db.get(Role, link.role_id).code == "student"
    assert link.is_primary is True


def test_role_change_dual_writes(client, admin_headers, db) -> None:
    sync_catalog(db)
    target = _create_user(db, "13700000002", "student")

    granted = client.post(
        f"/api/admin/users/{target.id}/roles",
        json={"grant": ["teacher"]},
        headers=admin_headers,
    )
    assert granted.status_code == 200, granted.text
    db.expire_all()
    user = db.get(User, target.id)
    link = db.scalar(select(UserRole).where(UserRole.user_id == target.id))
    assert user.role == "teacher"
    assert db.get(Role, link.role_id).code == "teacher"

    revoked = client.post(
        f"/api/admin/users/{target.id}/roles",
        json={"revoke": ["teacher"]},
        headers=admin_headers,
    )
    assert revoked.status_code == 200, revoked.text
    db.expire_all()
    link = db.scalar(select(UserRole).where(UserRole.user_id == target.id))
    assert db.get(Role, link.role_id).code == "student"


def test_permissions_read_prefers_user_roles(client, db) -> None:
    sync_catalog(db)
    db.commit()
    response = client.post(
        "/api/auth/register",
        json={"phone": "13700000003", "password": "pass1234", "grade": 3},
    )
    assert response.status_code == 201, response.text
    user = db.scalar(select(User).where(User.phone == "13700000003"))

    teacher_role = db.scalar(select(Role).where(Role.code == "teacher"))
    db.execute(delete(UserRole).where(UserRole.user_id == user.id))
    db.add(UserRole(user_id=user.id, role_id=teacher_role.id, is_primary=True))
    db.commit()

    headers = _login(client, "13700000003")
    payload = client.get("/api/auth/permissions", headers=headers).json()
    assert payload["scope"] == "CLASS"
    assert "learn:stats:class:read" in payload["permissions"]
    assert "learn:practice:start" not in payload["permissions"]


def test_permissions_fallback_without_user_roles(client, db) -> None:
    _create_user(db, "13700000004", "student")

    headers = _login(client, "13700000004")
    payload = client.get("/api/auth/permissions", headers=headers).json()
    assert payload["scope"] == "SELF"
    assert "learn:practice:start" in payload["permissions"]
    assert "learn:stats:class:read" not in payload["permissions"]


def test_reconcile_backfills_and_fixes_mismatch(db) -> None:
    sync_catalog(db)
    student = _create_user(db, "13700000005", "student")
    admin = _create_user(db, "13700000006", "admin")
    db.commit()

    report = reconcile(db)
    assert report["catalog"]["links_missing"] == 0
    assert report["user_roles"]["missing"] == [student.id, admin.id]
    assert has_drift(report)

    fixed = reconcile(db, fix=True)
    db.commit()
    assert not has_drift(fixed)

    assert effective_role(db, db.get(User, student.id)) == "student"
    assert effective_role(db, db.get(User, admin.id)) == "super_admin"
    assert effective_permissions(db, db.get(User, admin.id)) == [ALL_PERMISSIONS]

    teacher_role = db.scalar(select(Role).where(Role.code == "teacher"))
    db.execute(delete(UserRole).where(UserRole.user_id == student.id))
    db.add(UserRole(user_id=student.id, role_id=teacher_role.id, is_primary=True))
    db.commit()

    drift = reconcile(db)
    assert drift["user_roles"]["mismatched"] == [
        {"user_id": student.id, "users_role": "student", "user_roles_role": "teacher"}
    ]

    reconcile(db, fix=True)
    db.commit()
    assert effective_role(db, db.get(User, student.id)) == "student"


def test_backfill_skips_unknown_role(db) -> None:
    sync_catalog(db)
    unknown = _create_user(db, "13700000007", "vip")
    db.commit()

    assert backfill_user_roles(db) == 0
    assert sync_user_role(db, unknown, "vip") is None
