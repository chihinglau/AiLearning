from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import bump_token_version, create_access_token, decode_access_token
from app.models.user import User


def _register_and_login(client: TestClient, phone: str, grade: int = 3) -> dict[str, str]:
    response = client.post(
        "/api/auth/register", json={"phone": phone, "password": "pass1234", "grade": grade}
    )
    assert response.status_code == 201, response.text
    login = client.post("/api/auth/login", data={"username": phone, "password": "pass1234"})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_login_token_carries_token_version(client: TestClient, db: Session) -> None:
    headers = _register_and_login(client, "13500000001")
    token = headers["Authorization"].removeprefix("Bearer ")

    data = decode_access_token(token)
    assert data is not None
    assert data.subject.isdigit()
    assert data.version == 0

    student = db.scalar(select(User).where(User.phone == "13500000001"))
    assert data.subject == str(student.id)


def test_bump_invalidates_old_token(client: TestClient, db: Session) -> None:
    headers = _register_and_login(client, "13500000002")
    assert client.get("/api/auth/me", headers=headers).status_code == 200

    student = db.scalar(select(User).where(User.phone == "13500000002"))
    bump_token_version(student)
    db.commit()

    assert client.get("/api/auth/me", headers=headers).status_code == 401

    relogin = client.post(
        "/api/auth/login", data={"username": "13500000002", "password": "pass1234"}
    )
    assert relogin.status_code == 200
    new_headers = {"Authorization": f"Bearer {relogin.json()['access_token']}"}
    assert client.get("/api/auth/me", headers=new_headers).status_code == 200


def test_stale_token_version_rejected(client: TestClient, db: Session) -> None:
    student = User(
        phone="13500000003", password_hash="x", nickname="student", role="student", grade=4
    )
    db.add(student)
    db.commit()

    token = create_access_token(str(student.id), token_version=3)
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_bump_token_version_increments() -> None:
    user = User(phone="13500000004", password_hash="x", nickname="s", role="student", grade=1)
    user.token_version = 0
    assert bump_token_version(user) == 1
    assert bump_token_version(user) == 2


def test_invalid_token_rejected(client: TestClient) -> None:
    response = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-token"})
    assert response.status_code == 401
