from datetime import datetime

from fastapi.testclient import TestClient

from app.services import telemetry


def _report(client: TestClient, headers=None, **overrides) -> dict:
    payload = {
        "message": "StateError: Bad state: no element",
        "stack": "#0      main (package:ai_learning/main.dart:12)\n#1 ...",
        "error_type": "StateError",
        "platform": "android",
        "app_version": "1.0.0",
        "os_version": "Android 12",
        "device_model": "OXF AN10",
        "route": "/exam/1",
        "occurred_at": "2026-11-07T02:00:00Z",
    }
    payload.update(overrides)
    return client.post("/api/monitor/crash", json=payload, headers=headers or {})


def test_anonymous_crash_report_is_sanitized(client: TestClient, db) -> None:
    response = _report(
        client,
        message="家长 13800001111 邮箱 parent@example.com 崩溃异常",
        stack="Exception: boom\n" + "x" * 5000,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert len(body["fingerprint"]) == 64

    from app.models.telemetry import CrashReport

    row = db.query(CrashReport).one()
    assert row.user_id is None
    assert row.source == "app"
    assert "13800001111" not in row.message
    assert "parent@example.com" not in row.message
    assert "1**********" in row.message
    assert "***@***" in row.message
    assert row.stack_trace is not None and len(row.stack_trace) <= 4000
    assert row.occurred_at == datetime(2026, 11, 7, 2, 0, 0)


def test_crash_report_links_logged_in_user(
    client: TestClient, db, student_headers: dict[str, str]
) -> None:
    response = _report(client, headers=student_headers)
    assert response.status_code == 201, response.text

    from app.models.telemetry import CrashReport

    row = db.query(CrashReport).one()
    assert row.user_id is not None
    assert row.platform == "android"
    assert row.route == "/exam/1"


def test_same_error_aggregates_by_fingerprint(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    first = _report(client, message="TypeError: 13800001111 崩溃")
    second = _report(client, message="TypeError: 13900002222 崩溃")
    other = _report(client, message="RangeError: index out of range")
    assert first.status_code == second.status_code == other.status_code == 201
    assert first.json()["fingerprint"] == second.json()["fingerprint"]

    summary = client.get(
        "/api/monitor/crashes/summary", params={"days": 7}, headers=admin_headers
    )
    assert summary.status_code == 200, summary.text
    data = summary.json()
    assert data["total"] == 3
    assert data["unique_fingerprints"] == 2
    assert data["top"][0]["count"] == 2
    assert data["by_platform"] == {"android": 3}
    assert data["by_version"] == {"1.0.0": 3}


def test_monitor_endpoints_require_admin(
    client: TestClient, student_headers: dict[str, str]
) -> None:
    _report(client)
    assert (
        client.get("/api/monitor/crashes/summary", headers=student_headers)
    ).status_code == 403
    assert (
        client.get("/api/monitor/crashes", headers=student_headers)
    ).status_code == 403
    assert client.get("/api/monitor/crashes/summary").status_code == 401


def test_crash_list_filters_and_limit(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    _report(client, platform="android")
    _report(client, platform="ohos", message="OhosError: hdc timeout")
    response = client.get(
        "/api/monitor/crashes",
        params={"limit": 1, "platform": "ohos"},
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text
    items = response.json()
    assert len(items) == 1
    assert items[0]["platform"] == "ohos"
    assert items[0]["message"].startswith("OhosError")


def test_backend_error_is_recorded(monkeypatch) -> None:
    from tests.conftest import TestingSessionLocal

    monkeypatch.setattr(
        telemetry, "_session_factory", lambda: TestingSessionLocal()
    )
    telemetry.record_server_error(
        method="GET",
        path="/api/learn/home",
        request_id="req-123",
        error=RuntimeError("db connection lost"),
    )

    session = TestingSessionLocal()
    try:
        from app.models.telemetry import CrashReport

        row = session.query(CrashReport).one()
        assert row.source == "backend"
        assert row.platform == "backend"
        assert row.request_id == "req-123"
        assert "db connection lost" in row.message
        assert row.stack_trace is not None and "RuntimeError" in row.stack_trace
    finally:
        session.close()
