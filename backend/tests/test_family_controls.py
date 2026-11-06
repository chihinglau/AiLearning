"""P1-05 家长控制（每日时长/青少年模式，D-03 §10.2）。"""

from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import AuditLog, ParentChildBinding, User

PASSWORD = "pass1234"


def _add_user(db: Session, phone: str, role: str, **extra: object) -> User:
    user = User(
        phone=phone,
        password_hash=hash_password(PASSWORD),
        nickname=phone,
        role=role,
        **extra,
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


def test_parent_updates_child_controls(client: TestClient, db: Session) -> None:
    parent = _add_user(db, "13730000001", "parent")
    child = _add_user(db, "13730000002", "student", grade=4)
    db.add(
        ParentChildBinding(
            parent_id=parent.id,
            child_id=child.id,
            relation="parent",
            status="active",
            consent_at=datetime.utcnow(),
        )
    )
    db.commit()

    headers = _login(client, "13730000001")
    children = client.get("/api/family/children", headers=headers)
    assert children.status_code == 200, children.text
    assert children.json()[0]["daily_limit_minutes"] == 120
    assert children.json()[0]["teen_mode"] is False

    updated = client.put(
        f"/api/family/children/{child.id}/controls",
        json={"daily_limit_minutes": 60, "teen_mode": True},
        headers=headers,
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["daily_limit_minutes"] == 60
    assert updated.json()["teen_mode"] is True

    refreshed = client.get("/api/family/children", headers=headers)
    assert refreshed.json()[0]["daily_limit_minutes"] == 60
    assert refreshed.json()[0]["teen_mode"] is True

    log = db.scalar(
        select(AuditLog).where(AuditLog.action == "family.controls.update")
    )
    assert log is not None
    assert "60" in (log.detail or "")


def test_controls_binding_and_permission(client: TestClient, db: Session) -> None:
    _add_user(db, "13730000011", "parent")
    stranger_child = _add_user(db, "13730000012", "student", grade=4)
    bound_parent = _add_user(db, "13730000013", "parent")
    bound_child = _add_user(db, "13730000014", "student", grade=4)
    db.add(
        ParentChildBinding(
            parent_id=bound_parent.id,
            child_id=bound_child.id,
            relation="parent",
            status="active",
            consent_at=datetime.utcnow(),
        )
    )
    db.commit()

    parent_headers = _login(client, "13730000011")
    no_binding = client.put(
        f"/api/family/children/{stranger_child.id}/controls",
        json={"daily_limit_minutes": 30},
        headers=parent_headers,
    )
    assert no_binding.status_code == 404
    assert no_binding.json()["detail"]["code"] == "BINDING_NOT_ACTIVE"

    bound_headers = _login(client, "13730000013")
    empty = client.put(
        f"/api/family/children/{bound_child.id}/controls",
        json={},
        headers=bound_headers,
    )
    assert empty.status_code == 422
    assert empty.json()["detail"]["code"] == "CONTROLS_REQUIRED"

    out_of_range = client.put(
        f"/api/family/children/{stranger_child.id}/controls",
        json={"daily_limit_minutes": 241},
        headers=parent_headers,
    )
    assert out_of_range.status_code == 422

    child_headers = _login(client, "13730000014")
    denied = client.put(
        f"/api/family/children/{bound_child.id}/controls",
        json={"teen_mode": True},
        headers=child_headers,
    )
    assert denied.status_code in (403, 404)
    assert denied.json()["detail"]["code"] in (
        "PERMISSION_DENIED",
        "BINDING_NOT_ACTIVE",
    )
