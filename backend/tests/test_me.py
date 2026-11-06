from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.user import User


def _register(client: TestClient, phone: str, grade: int) -> None:
    response = client.post(
        "/api/auth/register", json={"phone": phone, "password": "pass1234", "grade": grade}
    )
    assert response.status_code == 201, response.text


def _auth_headers(client: TestClient, phone: str) -> dict[str, str]:
    response = client.post(
        "/api/auth/login", data={"username": phone, "password": "pass1234"}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_me_returns_grade_group_and_permissions(client: TestClient) -> None:
    _register(client, "13600000001", 3)
    headers = _auth_headers(client, "13600000001")

    me = client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200, me.text
    body = me.json()
    assert body["stage"] == "primary"
    assert body["grade_group"] == "primary_mid"
    assert body["scope"] == "SELF"
    assert "learn:practice:submit" in body["permissions"]
    assert "learn:stats:child:read" not in body["permissions"]


def test_permissions_endpoint(client: TestClient) -> None:
    _register(client, "13600000002", 8)
    headers = _auth_headers(client, "13600000002")

    response = client.get("/api/auth/permissions", headers=headers)
    assert response.status_code == 200
    assert response.json()["scope"] == "SELF"
    assert "learn:exam:take" in response.json()["permissions"]


def test_legacy_admin_permissions(client: TestClient, db: Session) -> None:
    admin = User(phone="13600000003", password_hash="x", nickname="admin", role="admin")
    db.add(admin)
    db.commit()
    token = create_access_token(str(admin.id))

    response = client.get(
        "/api/auth/permissions", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json() == {"permissions": ["*"], "scope": "ALL"}
