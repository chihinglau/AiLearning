"""P1-04 管理端用户列表、角色授予/回收与 Token 失效。"""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.org import School
from app.models.user import AuditLog, User

PASSWORD = "pass1234"


def _add_user(
    db: Session,
    phone: str,
    role: str,
    *,
    school_id: int | None = None,
    grade: int | None = None,
    nickname: str = "",
) -> User:
    user = User(
        phone=phone,
        password_hash=hash_password(PASSWORD),
        nickname=nickname or role,
        role=role,
        school_id=school_id,
        grade=grade,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _login(client: TestClient, phone: str) -> dict[str, str]:
    response = client.post(
        "/api/auth/login", data={"username": phone, "password": PASSWORD}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_user_list_scope_masking_and_filters(
    client: TestClient, db: Session, admin_headers: dict[str, str]
) -> None:
    school_a = School(name="列表 A 校")
    school_b = School(name="列表 B 校")
    db.add_all([school_a, school_b])
    db.flush()
    _add_user(
        db, "13720000001", "school_admin", school_id=school_a.id, nickname="A 校管"
    )
    _add_user(db, "13720000002", "teacher", school_id=school_a.id, nickname="张老师")
    _add_user(
        db, "13720000003", "student", school_id=school_b.id, grade=4, nickname="B 学生"
    )
    school_admin = _login(client, "13720000001")

    all_users = client.get(
        "/api/admin/users", params={"page_size": 100}, headers=admin_headers
    )
    assert all_users.status_code == 200, all_users.text
    payload = all_users.json()
    assert payload["total"] >= 4
    assert all(
        item["phone_masked"].count("*") > 0 for item in payload["items"]
    )

    filtered = client.get(
        "/api/admin/users", params={"role": "teacher"}, headers=admin_headers
    )
    assert filtered.status_code == 200
    assert all(item["role"] == "teacher" for item in filtered.json()["items"])

    keyword = client.get(
        "/api/admin/users", params={"keyword": "张老师"}, headers=admin_headers
    )
    assert keyword.status_code == 200
    assert [item["nickname"] for item in keyword.json()["items"]] == ["张老师"]

    scoped = client.get(
        "/api/admin/users", params={"page_size": 100}, headers=school_admin
    )
    assert scoped.status_code == 200, scoped.text
    assert all(item["school_id"] == school_a.id for item in scoped.json()["items"])

    denied = client.get("/api/auth/me", headers=_login(client, "13720000003"))
    assert denied.status_code == 200  # 学生本人可访问 /me
    forbidden = client.get("/api/admin/users", headers=_login(client, "13720000003"))
    assert forbidden.status_code == 403
    assert forbidden.json()["detail"]["code"] == "PERMISSION_DENIED"


def test_school_admin_grant_and_revoke(
    client: TestClient, db: Session, admin_headers: dict[str, str]
) -> None:
    school = School(name="授予小学")
    db.add(school)
    db.flush()
    manager = _add_user(db, "13720000011", "school_admin", school_id=school.id)
    target = _add_user(db, "13720000012", "student", school_id=school.id, grade=4)
    _add_user(db, "13720000013", "school_admin", school_id=school.id)
    manager_headers = _login(client, "13720000011")
    old_target_token = _login(client, "13720000012")

    granted = client.post(
        f"/api/admin/users/{target.id}/roles",
        json={"grant": ["teacher"]},
        headers=manager_headers,
    )
    assert granted.status_code == 200, granted.text
    assert granted.json()["role"] == "teacher"
    assert granted.json()["token_version"] == 1

    revoked_token = client.get("/api/auth/me", headers=old_target_token)
    assert revoked_token.status_code == 401
    assert revoked_token.json()["detail"]["code"] == "TOKEN_REVOKED"

    revoked = client.post(
        f"/api/admin/users/{target.id}/roles",
        json={"revoke": ["teacher"]},
        headers=manager_headers,
    )
    assert revoked.status_code == 200, revoked.text
    assert revoked.json()["role"] == "student"

    mismatch = client.post(
        f"/api/admin/users/{target.id}/roles",
        json={"revoke": ["teacher"]},
        headers=manager_headers,
    )
    assert mismatch.status_code == 409
    assert mismatch.json()["detail"]["code"] == "ROLE_MISMATCH"

    privileged = client.post(
        f"/api/admin/users/{target.id}/roles",
        json={"grant": ["school_admin"]},
        headers=manager_headers,
    )
    assert privileged.status_code == 403
    assert privileged.json()["detail"]["code"] == "ROLE_NOT_ALLOWED"

    self_change = client.post(
        f"/api/admin/users/{manager.id}/roles",
        json={"grant": ["teacher"]},
        headers=manager_headers,
    )
    assert self_change.status_code == 403
    assert self_change.json()["detail"]["code"] == "SELF_ROLE_DENIED"

    logs = list(
        db.scalars(
            select(AuditLog)
            .where(AuditLog.action == "admin.role.assign")
            .order_by(AuditLog.id)
        )
    )
    assert logs, "角色变更未写审计"
    assert "teacher" in (logs[0].detail or "")


def test_cross_school_and_super_admin_rules(
    client: TestClient, db: Session, admin_headers: dict[str, str]
) -> None:
    school_a = School(name="跨校 A")
    school_b = School(name="跨校 B")
    db.add_all([school_a, school_b])
    db.flush()
    _add_user(db, "13720000021", "school_admin", school_id=school_a.id)
    other_school_user = _add_user(db, "13720000022", "teacher", school_id=school_b.id)
    candidate = _add_user(db, "13720000023", "student", school_id=school_a.id, grade=4)
    manager_a_headers = _login(client, "13720000021")

    cross = client.post(
        f"/api/admin/users/{other_school_user.id}/roles",
        json={"grant": ["student"]},
        headers=manager_a_headers,
    )
    assert cross.status_code == 403
    assert cross.json()["detail"]["code"] == "CROSS_SCHOOL"

    promoted = client.post(
        f"/api/admin/users/{candidate.id}/roles",
        json={"grant": ["super_admin"]},
        headers=admin_headers,
    )
    assert promoted.status_code == 200, promoted.text
    assert promoted.json()["role"] == "super_admin"

    admin_self = client.get("/api/auth/me", headers=admin_headers)
    assert admin_self.status_code == 200
    admin_id = admin_self.json()["id"]
    self_grant = client.post(
        f"/api/admin/users/{admin_id}/roles",
        json={"grant": ["super_admin"]},
        headers=admin_headers,
    )
    assert self_grant.status_code == 403
    assert self_grant.json()["detail"]["code"] == "SELF_ROLE_DENIED"


def test_role_payload_validation(
    client: TestClient, db: Session, admin_headers: dict[str, str]
) -> None:
    school = School(name="参数校验小学")
    db.add(school)
    db.flush()
    target = _add_user(db, "13720000031", "student", school_id=school.id, grade=4)

    both = client.post(
        f"/api/admin/users/{target.id}/roles",
        json={"grant": ["teacher"], "revoke": ["student"]},
        headers=admin_headers,
    )
    assert both.status_code == 422
    assert both.json()["detail"]["code"] == "ROLE_CONFLICT"

    empty = client.post(
        f"/api/admin/users/{target.id}/roles", json={}, headers=admin_headers
    )
    assert empty.status_code == 422
    assert empty.json()["detail"]["code"] == "ROLE_REQUIRED"

    invalid = client.post(
        f"/api/admin/users/{target.id}/roles",
        json={"grant": ["unknown_role"]},
        headers=admin_headers,
    )
    assert invalid.status_code == 422
    assert invalid.json()["detail"]["code"] == "ROLE_INVALID"

    missing = client.post(
        "/api/admin/users/999999/roles",
        json={"grant": ["teacher"]},
        headers=admin_headers,
    )
    assert missing.status_code == 404
