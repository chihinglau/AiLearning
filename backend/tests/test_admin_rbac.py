"""P2-02 权限配置后台：角色/权限读取、授权调整、审计与越权用例。"""

from sqlalchemy import select

from app.core.permissions import PERMISSIONS, ROLE_INFO, ROLE_PERMISSIONS
from app.core.security import hash_password
from app.models.user import AuditLog, User
from app.services.rbac import effective_permissions


def _create_user(db, phone: str, role: str) -> User:
    user = User(phone=phone, password_hash=hash_password("pass1234"), nickname=role, role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _login(client, phone: str) -> dict[str, str]:
    response = client.post("/api/auth/login", data={"username": phone, "password": "pass1234"})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_list_roles_initializes_catalog(client, admin_headers) -> None:
    response = client.get("/api/admin/rbac/roles", headers=admin_headers)
    assert response.status_code == 200, response.text
    items = {item["code"]: item for item in response.json()["items"]}

    assert set(items) == set(ROLE_INFO)
    assert items["super_admin"]["permissions"] == ["*"]
    assert items["super_admin"]["is_editable"] is False
    assert items["student"]["is_editable"] is True
    assert sorted(items["student"]["permissions"]) == sorted(ROLE_PERMISSIONS["student"])
    assert items["teacher"]["name"] == "教师"
    assert items["teacher"]["level"] == "L2"


def test_list_permissions_contains_all_codes(client, admin_headers) -> None:
    response = client.get("/api/admin/rbac/permissions", headers=admin_headers)
    assert response.status_code == 200, response.text
    payload = response.json()
    codes = {item["code"] for item in payload["items"]}

    assert "*" in codes
    assert codes - {"*"} == set(PERMISSIONS)
    assert "system" in payload["domains"]


def test_update_role_permissions_and_audit(client, admin_headers, db) -> None:
    teacher = _create_user(db, "13700000011", "teacher")
    desired = set(ROLE_PERMISSIONS["teacher"]) - {"learn:exam:grade"}
    desired.add("learn:wrong:self")

    response = client.put(
        "/api/admin/rbac/roles/teacher/permissions",
        json={"permissions": sorted(desired)},
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["code"] == "teacher"
    assert payload["permissions"] == sorted(desired)
    assert payload["removed"] == ["learn:exam:grade"]
    assert payload["added"] == ["learn:wrong:self"]

    roles = {
        item["code"]: item
        for item in client.get("/api/admin/rbac/roles", headers=admin_headers).json()["items"]
    }
    assert roles["teacher"]["permissions"] == sorted(desired)

    db.expire_all()
    assert effective_permissions(db, db.get(User, teacher.id)) == sorted(desired)

    audit = db.scalar(select(AuditLog).where(AuditLog.action == "rbac.role.permissions"))
    assert audit is not None
    assert "learn:exam:grade" in audit.detail
    assert "learn:wrong:self" in audit.detail


def test_update_super_admin_is_immutable(client, admin_headers) -> None:
    response = client.put(
        "/api/admin/rbac/roles/super_admin/permissions",
        json={"permissions": ["learn:content:read"]},
        headers=admin_headers,
    )
    assert response.status_code == 403, response.text
    assert response.json()["detail"]["code"] == "ROLE_IMMUTABLE"


def test_update_unknown_permission_rejected(client, admin_headers) -> None:
    response = client.put(
        "/api/admin/rbac/roles/teacher/permissions",
        json={"permissions": ["learn:not-exist"]},
        headers=admin_headers,
    )
    assert response.status_code == 422, response.text
    assert response.json()["detail"]["code"] == "PERMISSION_UNKNOWN"


def test_non_super_admin_denied(client, db) -> None:
    _create_user(db, "13600000011", "school_admin")
    _create_user(db, "13500000011", "teacher")

    for phone in ("13600000011", "13500000011"):
        headers = _login(client, phone)
        assert client.get("/api/admin/rbac/roles", headers=headers).status_code == 403
        assert (
            client.get("/api/admin/rbac/permissions", headers=headers).status_code
            == 403
        )
        assert (
            client.put(
                "/api/admin/rbac/roles/teacher/permissions",
                json={"permissions": []},
                headers=headers,
            ).status_code
            == 403
        )
