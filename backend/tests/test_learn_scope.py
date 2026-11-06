from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.user import AuditLog, ParentChildBinding, User


def _register(client: TestClient, payload: dict) -> None:
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201, response.text


def _login(client: TestClient, phone: str) -> dict[str, str]:
    response = client.post(
        "/api/auth/login", data={"username": phone, "password": "pass1234"}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _student(client: TestClient, phone: str, grade: int = 3, is_child: bool = False) -> dict[str, str]:
    _register(
        client,
        {
            "phone": phone,
            "password": "pass1234",
            "grade": grade,
            "is_child": is_child,
        },
    )
    return _login(client, phone)


def _parent(client: TestClient, phone: str) -> dict[str, str]:
    _register(client, {"phone": phone, "password": "pass1234", "role": "parent"})
    return _login(client, phone)


def _bind(
    db: Session, parent_phone: str, child_phone: str, status: str = "active"
) -> ParentChildBinding:
    parent = db.scalar(select(User).where(User.phone == parent_phone))
    child = db.scalar(select(User).where(User.phone == child_phone))
    binding = ParentChildBinding(
        parent_id=parent.id,
        child_id=child.id,
        status=status,
        consent_at=datetime.utcnow() if status == "active" else None,
    )
    db.add(binding)
    db.commit()
    return binding


def _user_id(db: Session, phone: str) -> int:
    return db.scalar(select(User.id).where(User.phone == phone))


def test_student_stats_defaults_to_self(client: TestClient) -> None:
    headers = _student(client, "13200000001")
    response = client.get("/api/learn/stats", headers=headers)
    assert response.status_code == 200
    assert response.json()["total_answered"] == 0


def test_student_cannot_view_other_student(client: TestClient, db: Session) -> None:
    headers = _student(client, "13200000002")
    _student(client, "13200000003")
    other_id = _user_id(db, "13200000003")

    stats = client.get(f"/api/learn/stats?student_id={other_id}", headers=headers)
    assert stats.status_code == 403
    assert stats.json()["detail"]["code"] == "SCOPE_DENIED"

    wrong = client.get(f"/api/learn/wrong-questions?student_id={other_id}", headers=headers)
    assert wrong.status_code == 403


def test_parent_must_choose_child(client: TestClient, db: Session) -> None:
    parent_headers = _parent(client, "13200000004")
    _student(client, "13200000005", grade=2)
    _bind(db, "13200000004", "13200000005")

    response = client.get("/api/learn/stats", headers=parent_headers)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "STUDENT_ID_REQUIRED"


def test_parent_reads_bound_child_data(client: TestClient, db: Session) -> None:
    parent_headers = _parent(client, "13200000006")
    _student(client, "13200000007", grade=2)
    _bind(db, "13200000006", "13200000007")
    child_id = _user_id(db, "13200000007")

    stats = client.get(f"/api/learn/stats?student_id={child_id}", headers=parent_headers)
    assert stats.status_code == 200, stats.text
    assert stats.json()["total_answered"] == 0

    wrong = client.get(
        f"/api/learn/wrong-questions?student_id={child_id}", headers=parent_headers
    )
    assert wrong.status_code == 200
    assert wrong.json() == []

    log = db.scalar(select(AuditLog).where(AuditLog.action == "data.cross_user_read"))
    assert log is not None
    assert f"target={child_id}" in log.detail


def test_parent_cannot_read_unbound_child(client: TestClient, db: Session) -> None:
    parent_headers = _parent(client, "13200000008")
    _student(client, "13200000009", grade=1)
    unrelated_id = _user_id(db, "13200000009")

    response = client.get(
        f"/api/learn/stats?student_id={unrelated_id}", headers=parent_headers
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "SCOPE_DENIED"


def test_pending_binding_denied(client: TestClient, db: Session) -> None:
    parent_headers = _parent(client, "13200000010")
    _student(client, "13200000011", grade=1)
    _bind(db, "13200000010", "13200000011", status="pending")
    child_id = _user_id(db, "13200000011")

    response = client.get(
        f"/api/learn/stats?student_id={child_id}", headers=parent_headers
    )
    assert response.status_code == 403


def test_teacher_cannot_read_wrong_book(client: TestClient, db: Session) -> None:
    teacher = User(
        phone="13200000012", password_hash="x", nickname="teacher", role="teacher"
    )
    db.add(teacher)
    db.commit()

    response = client.get(
        "/api/learn/wrong-questions",
        headers={"Authorization": f"Bearer {create_access_token(str(teacher.id))}"},
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "PERMISSION_DENIED"
