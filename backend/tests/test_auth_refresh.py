from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User


def _login(client: TestClient, phone: str, password: str) -> dict:
    response = client.post(
        "/api/auth/login", data={"username": phone, "password": password}
    )
    assert response.status_code == 200, response.text
    return response.json()


def _register(client: TestClient, phone: str, password: str = "pass1234") -> None:
    response = client.post(
        "/api/auth/register",
        json={"phone": phone, "password": password, "grade": 3},
    )
    assert response.status_code == 201, response.text


def test_login_returns_access_and_refresh(client: TestClient) -> None:
    _register(client, "13700000010")
    body = _login(client, "13700000010", "pass1234")
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"
    assert body["expires_in"] > 0

    me = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert me.status_code == 200


def test_refresh_rotates_and_old_token_invalid(client: TestClient) -> None:
    _register(client, "13700000011")
    tokens = _login(client, "13700000011", "pass1234")
    first_refresh = tokens["refresh_token"]

    refreshed = client.post(
        "/api/auth/refresh", json={"refresh_token": first_refresh}
    )
    assert refreshed.status_code == 200, refreshed.text
    body = refreshed.json()
    assert body["refresh_token"] != first_refresh
    assert body["access_token"]

    # 旧 refresh 已被轮换作废，再次使用返回 401。
    reuse = client.post("/api/auth/refresh", json={"refresh_token": first_refresh})
    assert reuse.status_code == 401
    assert reuse.json()["detail"]["code"] == "REFRESH_TOKEN_INVALID"


def test_refresh_reuse_revokes_whole_family(client: TestClient) -> None:
    _register(client, "13700000012")
    tokens = _login(client, "13700000012", "pass1234")
    first_refresh = tokens["refresh_token"]

    second = client.post(
        "/api/auth/refresh", json={"refresh_token": first_refresh}
    ).json()["refresh_token"]

    # 重用检测：用已作废的 first_refresh 再次刷新
    assert (
        client.post(
            "/api/auth/refresh", json={"refresh_token": first_refresh}
        ).status_code
        == 401
    )
    # 整族撤销后，最新的 second 也失效。
    assert (
        client.post(
            "/api/auth/refresh", json={"refresh_token": second}
        ).status_code
        == 401
    )


def test_logout_revokes_refresh(client: TestClient) -> None:
    _register(client, "13700000013")
    tokens = _login(client, "13700000013", "pass1234")
    response = client.post(
        "/api/auth/logout", json={"refresh_token": tokens["refresh_token"]}
    )
    assert response.status_code == 204
    assert (
        client.post(
            "/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
        ).status_code
        == 401
    )
    # 幂等：重复登出不报错。
    assert (
        client.post(
            "/api/auth/logout", json={"refresh_token": tokens["refresh_token"]}
        ).status_code
        == 204
    )


def test_token_version_change_invalidates_refresh(
    client: TestClient, db: Session
) -> None:
    _register(client, "13700000014")
    tokens = _login(client, "13700000014", "pass1234")
    user = db.query(User).filter(User.phone == "13700000014").one()
    user.token_version = (user.token_version or 0) + 1
    db.commit()

    assert (
        client.post(
            "/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
        ).status_code
        == 401
    )


def test_unknown_refresh_token_rejected(client: TestClient) -> None:
    assert (
        client.post(
            "/api/auth/refresh", json={"refresh_token": "not-a-real-token"}
        ).status_code
        == 401
    )
