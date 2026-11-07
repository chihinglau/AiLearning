from datetime import datetime

from app.models.user import AuditLog, ParentChildBinding, User
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

STUDENT_PHONE = "13900000000"


def test_delete_account_requires_confirm(
    client: TestClient, student_headers: dict[str, str]
) -> None:
    response = client.request(
        "DELETE",
        "/api/users/me",
        headers=student_headers,
        json={"confirm": False},
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "CONFIRM_REQUIRED"


def test_delete_account_anonymizes_and_revokes_bindings(
    client: TestClient, student_headers: dict[str, str], db: Session
) -> None:
    student = db.scalar(select(User).where(User.phone == STUDENT_PHONE))
    assert student is not None
    parent = User(
        phone="13600000031", password_hash="x", nickname="parent", role="parent"
    )
    db.add(parent)
    db.flush()
    db.add(
        ParentChildBinding(
            parent_id=parent.id,
            child_id=student.id,
            status="active",
            consent_at=datetime.utcnow(),
        )
    )
    db.commit()
    student_id = student.id

    response = client.request(
        "DELETE",
        "/api/users/me",
        headers=student_headers,
        json={"confirm": True, "reason": "不再使用"},
    )
    assert response.status_code == 202, response.text
    body = response.json()
    assert body["due_at"] > body["requested_at"]
    assert "15 个工作日" in body["message"]

    db.expire_all()
    anonymized = db.get(User, student_id)
    assert anonymized is not None
    assert anonymized.is_active is False
    assert anonymized.phone.startswith(f"deleted-{student_id}-")
    assert anonymized.nickname == "已注销用户"
    assert anonymized.deletion_requested_at is not None

    binding = db.scalar(
        select(ParentChildBinding).where(ParentChildBinding.child_id == student_id)
    )
    assert binding is not None
    assert binding.status == "revoked"
    assert binding.consent_at is None

    audit = db.scalar(
        select(AuditLog).where(AuditLog.action == "account.deletion.requested")
    )
    assert audit is not None
    assert "due_at=" in audit.detail

    # 注销后旧 Token 立即失效
    me = client.get("/api/auth/me", headers=student_headers)
    assert me.status_code == 401
