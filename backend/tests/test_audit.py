from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_student_access
from app.models.user import AuditLog, ParentChildBinding, User
from app.services.audit import record_audit


def _register(client: TestClient, phone: str, grade: int) -> None:
    response = client.post(
        "/api/auth/register", json={"phone": phone, "password": "pass1234", "grade": grade}
    )
    assert response.status_code == 201, response.text


def test_login_failure_writes_audit_log(client: TestClient, db: Session) -> None:
    _register(client, "13600000004", 5)

    response = client.post(
        "/api/auth/login", data={"username": "13600000004", "password": "wrong-pass"}
    )
    assert response.status_code == 401

    log = db.scalar(select(AuditLog).where(AuditLog.action == "auth.login_failed"))
    assert log is not None
    assert "136****0004" in log.detail


def test_record_audit_keeps_before_after(db: Session) -> None:
    record_audit(
        db,
        user_id=None,
        action="user.grade_change",
        message="operator=school_admin",
        before={"grade": 6},
        after={"grade": 7},
    )
    log = db.scalar(select(AuditLog).where(AuditLog.action == "user.grade_change"))
    assert log is not None
    assert '"before": {"grade": 6}' in log.detail
    assert '"after": {"grade": 7}' in log.detail


def test_cross_user_read_writes_audit_log(db: Session) -> None:
    parent = User(phone="13600000005", password_hash="x", nickname="parent", role="parent")
    child = User(phone="13600000006", password_hash="x", nickname="child", role="student", grade=2)
    db.add_all([parent, child])
    db.flush()
    db.add(ParentChildBinding(parent_id=parent.id, child_id=child.id, status="active"))
    db.flush()

    dependency = require_student_access("learn:stats:child:read")
    dependency(student_id=child.id, current=parent, db=db)

    log = db.scalar(select(AuditLog).where(AuditLog.action == "data.cross_user_read"))
    assert log is not None
    assert f"target={child.id}" in log.detail
