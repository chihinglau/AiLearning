from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.rate_limit import rate_limiter


def _login(client: TestClient) -> int:
    response = client.post(
        "/api/auth/login", data={"username": "13800000000", "password": "wrong-pass"}
    )
    return response.status_code


def test_login_rate_limited(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "login_rate_limit_per_minute", 2)
    rate_limiter.reset()

    assert _login(client) == 401
    assert _login(client) == 401

    blocked = client.post(
        "/api/auth/login", data={"username": "13800000000", "password": "wrong-pass"}
    )
    assert blocked.status_code == 429
    assert blocked.json()["detail"] == "RATE_LIMITED"
    assert int(blocked.headers["Retry-After"]) >= 1


def test_register_rate_limited(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "register_rate_limit_per_minute", 1)
    rate_limiter.reset()

    first = client.post(
        "/api/auth/register",
        json={"phone": "13700000001", "password": "pass1234", "grade": 3},
    )
    assert first.status_code == 201

    blocked = client.post(
        "/api/auth/register",
        json={"phone": "13700000002", "password": "pass1234", "grade": 3},
    )
    assert blocked.status_code == 429
    assert blocked.json()["detail"] == "RATE_LIMITED"


def test_other_paths_not_rate_limited(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "login_rate_limit_per_minute", 1)
    rate_limiter.reset()

    for _ in range(5):
        assert client.get("/health").status_code == 200


def test_rate_limit_can_be_disabled(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "rate_limit_enabled", False)
    monkeypatch.setattr(settings, "login_rate_limit_per_minute", 1)
    rate_limiter.reset()

    assert _login(client) == 401
    assert _login(client) == 401
