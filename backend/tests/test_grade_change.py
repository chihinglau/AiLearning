from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import AuditLog, GradeHistory, User


def _student(client: TestClient, phone: str, grade: int) -> dict[str, str]:
    response = client.post(
        "/api/auth/register", json={"phone": phone, "password": "pass1234", "grade": grade}
    )
    assert response.status_code == 201, response.text
    login = client.post("/api/auth/login", data={"username": phone, "password": "pass1234"})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _request_confirm(
    client: TestClient, headers: dict[str, str], grade: int
) -> dict:
    response = client.put("/api/users/me/grade", json={"grade": grade}, headers=headers)
    assert response.status_code == 428, response.text
    return response.json()


def test_change_requires_confirmation(client: TestClient) -> None:
    headers = _student(client, "13400000001", 3)

    body = _request_confirm(client, headers, 4)
    assert body["code"] == "CONFIRM_REQUIRED"
    assert body["impact"]["current_grade"] == 3
    assert body["impact"]["target_grade"] == 4
    assert body["impact"]["cross_stage"] is False
    assert body["impact"]["textbook_rebind_required"] is True
    assert body["confirm_token"]


def test_change_applies_and_revokes_token(client: TestClient, db: Session) -> None:
    headers = _student(client, "13400000002", 3)
    token = _request_confirm(client, headers, 4)["confirm_token"]

    response = client.put(
        "/api/users/me/grade",
        json={"grade": 4, "confirm_token": token},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["grade"] == 4
    assert body["stage"] == "primary"
    assert body["grade_group"] == "primary_mid"
    assert body["reauth_required"] is True
    assert body["token_version"] == 1

    student = db.scalar(select(User).where(User.phone == "13400000002"))
    assert student.grade == 4
    assert student.grade_updated_at is not None

    history = db.scalar(
        select(GradeHistory).where(
            GradeHistory.user_id == student.id, GradeHistory.source == "self"
        )
    )
    assert history is not None
    assert history.from_grade == 3
    assert history.to_grade == 4

    log = db.scalar(
        select(AuditLog).where(
            AuditLog.action == "user.grade.change", AuditLog.user_id == student.id
        )
    )
    assert log is not None
    assert '"before": {"grade": 3' in log.detail

    stale = client.get("/api/auth/me", headers=headers)
    assert stale.status_code == 401
    assert stale.json()["detail"]["code"] == "TOKEN_REVOKED"

    relogin = client.post(
        "/api/auth/login", data={"username": "13400000002", "password": "pass1234"}
    )
    me = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {relogin.json()['access_token']}"}
    )
    assert me.status_code == 200
    assert me.json()["grade"] == 4


def test_change_limited_per_semester(client: TestClient) -> None:
    headers = _student(client, "13400000003", 3)
    token = _request_confirm(client, headers, 4)["confirm_token"]
    applied = client.put(
        "/api/users/me/grade", json={"grade": 4, "confirm_token": token}, headers=headers
    )
    assert applied.status_code == 200
    relogin = client.post(
        "/api/auth/login", data={"username": "13400000003", "password": "pass1234"}
    )
    new_headers = {"Authorization": f"Bearer {relogin.json()['access_token']}"}

    limited = client.put(
        "/api/users/me/grade", json={"grade": 5}, headers=new_headers
    )
    assert limited.status_code == 409
    assert limited.json()["detail"]["code"] == "GRADE_CHANGE_LIMIT"


def test_invalid_confirm_token(client: TestClient) -> None:
    headers = _student(client, "13400000004", 4)
    response = client.put(
        "/api/users/me/grade",
        json={"grade": 5, "confirm_token": "bad-token"},
        headers=headers,
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "CONFIRM_INVALID"


def test_cross_stage_change_flagged(client: TestClient) -> None:
    headers = _student(client, "13400000005", 6)
    body = _request_confirm(client, headers, 7)
    assert body["impact"]["cross_stage"] is True


def test_same_grade_rejected(client: TestClient) -> None:
    headers = _student(client, "13400000006", 5)
    response = client.put("/api/users/me/grade", json={"grade": 5}, headers=headers)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "GRADE_UNCHANGED"


def test_parent_cannot_change_grade(client: TestClient) -> None:
    register = client.post(
        "/api/auth/register",
        json={"phone": "13400000007", "password": "pass1234", "role": "parent"},
    )
    assert register.status_code == 201
    login = client.post(
        "/api/auth/login", data={"username": "13400000007", "password": "pass1234"}
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = client.put("/api/users/me/grade", json={"grade": 4}, headers=headers)
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "PERMISSION_DENIED"
