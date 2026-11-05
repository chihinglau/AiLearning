from fastapi.testclient import TestClient


def test_register_and_me(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register",
        json={"phone": "13700000000", "password": "pass1234", "nickname": "小明", "grade": 3},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["role"] == "student"
    assert body["grade"] == 3

    token = client.post(
        "/api/auth/login", data={"username": "13700000000", "password": "pass1234"}
    )
    assert token.status_code == 200
    headers = {"Authorization": f"Bearer {token.json()['access_token']}"}
    me = client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["phone"] == "13700000000"


def test_duplicate_phone_rejected(client: TestClient) -> None:
    payload = {"phone": "13700000001", "password": "pass1234"}
    assert client.post("/api/auth/register", json=payload).status_code == 201
    assert client.post("/api/auth/register", json=payload).status_code == 409


def test_admin_cannot_self_register(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register",
        json={"phone": "13700000002", "password": "pass1234", "role": "admin"},
    )
    assert response.status_code == 422


def test_wrong_password(client: TestClient) -> None:
    client.post("/api/auth/register", json={"phone": "13700000003", "password": "pass1234"})
    response = client.post(
        "/api/auth/login", data={"username": "13700000003", "password": "wrong-pass"}
    )
    assert response.status_code == 401


def test_me_requires_token(client: TestClient) -> None:
    assert client.get("/api/auth/me").status_code == 401
