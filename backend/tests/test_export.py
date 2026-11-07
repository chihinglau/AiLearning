"""P2-08 数据导出与用途登记测试。"""

import json

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.org import School
from app.models.practice import StudentQuestionRecord, WrongQuestion
from app.models.user import AuditLog, User


def _add_user(
    db: Session,
    phone: str,
    role: str,
    *,
    school_id: int | None = None,
    grade: int | None = None,
) -> User:
    user = User(
        phone=phone,
        password_hash=hash_password("pass1234"),
        nickname=phone,
        role=role,
        school_id=school_id,
        grade=grade,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _login(client: TestClient, phone: str) -> dict[str, str]:
    response = client.post(
        "/api/auth/login", data={"username": phone, "password": "pass1234"}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_self_export_masks_phone_and_registers_purpose(
    client: TestClient,
    db: Session,
    sample_question: int,
    student_headers: dict[str, str],
) -> None:
    student = db.scalar(select(User).where(User.phone == "13900000000"))
    assert student is not None
    db.add(
        StudentQuestionRecord(
            user_id=student.id,
            question_id=sample_question,
            is_correct=False,
            user_answer={"value": "A"},
        )
    )
    db.add(WrongQuestion(user_id=student.id, question_id=sample_question, wrong_count=2))
    db.commit()

    response = client.get(
        "/api/data/export", params={"purpose": "self_copy"}, headers=student_headers
    )
    assert response.status_code == 200, response.text
    assert response.headers["X-Export-Purpose"] == "self_copy"
    assert "attachment" in response.headers["Content-Disposition"]

    body = response.json()
    assert body["meta"]["purpose"] == "self_copy"
    assert body["meta"]["purpose_label"] == "个人数据副本"
    assert body["meta"]["scope"] == "SELF"
    assert body["meta"]["masked_fields"] == ["phone"]
    assert body["profile"]["phone"] == "139****0000"
    assert body["learning_stats"]["answered_total"] >= 1
    assert body["question_records"][0]["question_id"] == sample_question
    assert body["wrong_questions"][0]["wrong_count"] == 2

    audit = db.scalar(
        select(AuditLog).where(AuditLog.action == "data.export").order_by(AuditLog.id.desc())
    )
    assert audit is not None
    detail = json.loads(audit.detail or "{}")
    assert detail["after"]["purpose"] == "self_copy"
    assert detail["after"]["target_user_id"] == student.id
    assert "139****0000" in audit.detail


def test_export_requires_purpose(client: TestClient, student_headers: dict[str, str]) -> None:
    response = client.get("/api/data/export", headers=student_headers)
    assert response.status_code == 422, response.text
    assert response.json()["detail"]["code"] == "PURPOSE_REQUIRED"


def test_export_rejects_unknown_purpose(
    client: TestClient, student_headers: dict[str, str]
) -> None:
    response = client.get(
        "/api/data/export", params={"purpose": "sell_data"}, headers=student_headers
    )
    assert response.status_code == 422, response.text
    assert response.json()["detail"]["code"] == "PURPOSE_INVALID"


def test_purpose_must_match_scope(client: TestClient, student_headers: dict[str, str]) -> None:
    response = client.get(
        "/api/data/export", params={"purpose": "school_management"}, headers=student_headers
    )
    assert response.status_code == 422, response.text
    assert response.json()["detail"]["code"] == "PURPOSE_NOT_ALLOWED"


def test_parent_exports_bound_child(client: TestClient, db: Session) -> None:
    child = _add_user(db, "13300000031", "student", grade=2)
    parent = _add_user(db, "13300000032", "parent")
    parent_headers = _login(client, "13300000032")

    created = client.post(
        "/api/family/bindings", json={"child_phone": child.phone}, headers=parent_headers
    )
    assert created.status_code == 201, created.text
    binding_id = created.json()["id"]
    child_headers = _login(client, "13300000031")
    confirmed = client.post(
        f"/api/family/bindings/{binding_id}/confirm", headers=child_headers
    )
    assert confirmed.status_code == 200, confirmed.text

    response = client.get(
        "/api/data/export",
        params={"student_id": child.id, "purpose": "guardian_review"},
        headers=parent_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["meta"]["scope"] == "CHILD"
    assert body["meta"]["purpose"] == "guardian_review"
    assert body["meta"]["requested_by"] == parent.id
    assert body["profile"]["phone"] == "133****0031"

    audit = db.scalar(
        select(AuditLog).where(AuditLog.action == "data.export").order_by(AuditLog.id.desc())
    )
    assert audit is not None
    assert f"target={child.id}" in (audit.detail or "")


def test_parent_cannot_export_unbound_child(client: TestClient, db: Session) -> None:
    _add_user(db, "13300000033", "student", grade=3)
    parent = _add_user(db, "13300000034", "parent")
    parent_headers = _login(client, "13300000034")

    response = client.get(
        "/api/data/export", params={"purpose": "self_copy"}, headers=parent_headers
    )
    assert response.status_code == 200
    assert response.json()["meta"]["student_id"] == parent.id

    target = db.scalar(select(User).where(User.phone == "13300000033"))
    assert target is not None
    denied = client.get(
        "/api/data/export",
        params={"student_id": target.id, "purpose": "guardian_review"},
        headers=parent_headers,
    )
    assert denied.status_code == 403, denied.text
    assert denied.json()["detail"]["code"] == "PERMISSION_DENIED"


def test_school_admin_exports_same_school_only(client: TestClient, db: Session) -> None:
    school_a = School(name="导出 A 校")
    school_b = School(name="导出 B 校")
    db.add_all([school_a, school_b])
    db.flush()
    db.commit()

    _add_user(db, "13720000041", "school_admin", school_id=school_a.id)
    own = _add_user(db, "13720000042", "student", school_id=school_a.id, grade=4)
    other = _add_user(db, "13720000043", "student", school_id=school_b.id, grade=4)
    headers = _login(client, "13720000041")

    allowed = client.get(
        "/api/data/export",
        params={"student_id": own.id, "purpose": "school_management"},
        headers=headers,
    )
    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["meta"]["scope"] == "SCHOOL"
    assert allowed.json()["profile"]["phone"] == "137****0042"

    denied = client.get(
        "/api/data/export",
        params={"student_id": other.id, "purpose": "school_management"},
        headers=headers,
    )
    assert denied.status_code == 403, denied.text
    assert denied.json()["detail"]["code"] == "SCOPE_DENIED"


def test_teacher_cannot_export_other_student(client: TestClient, db: Session) -> None:
    _add_user(db, "13720000044", "teacher")
    student = _add_user(db, "13720000045", "student", grade=5)
    headers = _login(client, "13720000044")

    response = client.get(
        "/api/data/export",
        params={"student_id": student.id, "purpose": "guardian_review"},
        headers=headers,
    )
    assert response.status_code == 403, response.text
    assert response.json()["detail"]["code"] == "PERMISSION_DENIED"


def test_export_purposes_catalog(client: TestClient, student_headers: dict[str, str]) -> None:
    response = client.get("/api/data/export/purposes", headers=student_headers)
    assert response.status_code == 200, response.text
    assert response.json()["self_copy"] == "个人数据副本"
    assert "guardian_review" in response.json()
