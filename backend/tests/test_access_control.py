"""P0-40 越权专项：跨学生/跨班级/跨学校、pending 绑定、旧 Token 与角色越权。"""

from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.exam import Exam
from app.models.user import ParentChildBinding, User


def _student(client: TestClient, phone: str, grade: int = 3) -> dict[str, str]:
    registered = client.post(
        "/api/auth/register", json={"phone": phone, "password": "pass1234", "grade": grade}
    )
    assert registered.status_code == 201, registered.text
    login = client.post("/api/auth/login", data={"username": phone, "password": "pass1234"})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _parent(client: TestClient, phone: str) -> dict[str, str]:
    registered = client.post(
        "/api/auth/register", json={"phone": phone, "password": "pass1234", "role": "parent"}
    )
    assert registered.status_code == 201, registered.text
    login = client.post("/api/auth/login", data={"username": phone, "password": "pass1234"})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _user(db: Session, phone: str) -> User:
    user = db.scalar(select(User).where(User.phone == phone))
    assert user is not None
    return user


def _token_headers(user: User) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {create_access_token(str(user.id), user.token_version or 0)}"
    }


def _bind(db: Session, parent_id: int, child_id: int, status: str = "active") -> None:
    db.add(
        ParentChildBinding(
            parent_id=parent_id,
            child_id=child_id,
            status=status,
            consent_at=datetime.utcnow() if status == "active" else None,
        )
    )
    db.commit()


def _published_exam(db: Session, title: str = "越权测试试卷") -> Exam:
    exam = Exam(
        title=title,
        subject="math",
        grade=3,
        exam_type="unit",
        total_score=100,
        time_limit_min=45,
        questions=[],
        status="published",
    )
    db.add(exam)
    db.commit()
    return exam


def test_cross_student_stats_and_wrong_book_denied(client: TestClient, db: Session) -> None:
    headers = _student(client, "13200000030")
    _student(client, "13200000031")
    other_id = _user(db, "13200000031").id

    stats = client.get(f"/api/learn/stats?student_id={other_id}", headers=headers)
    assert stats.status_code == 403
    assert stats.json()["detail"]["code"] == "SCOPE_DENIED"

    wrong = client.get(
        f"/api/learn/wrong-questions?student_id={other_id}", headers=headers
    )
    assert wrong.status_code == 403
    assert wrong.json()["detail"]["code"] == "SCOPE_DENIED"


def test_cross_class_teacher_cannot_read_student_or_take_exam(
    client: TestClient, db: Session
) -> None:
    _student(client, "13200000032")
    child_id = _user(db, "13200000032").id
    teacher = User(
        phone="13200000033", password_hash="x", nickname="teacher", role="teacher"
    )
    db.add(teacher)
    db.commit()
    teacher_headers = _token_headers(teacher)

    # 班级/授课关系未接入前 CLASS 安全默认空集
    stats = client.get(f"/api/learn/stats?student_id={child_id}", headers=teacher_headers)
    assert stats.status_code == 403
    assert stats.json()["detail"]["code"] == "SCOPE_DENIED"

    exam = _published_exam(db)
    started = client.post(f"/api/exams/{exam.id}/attempts", headers=teacher_headers)
    assert started.status_code == 403
    assert started.json()["detail"]["code"] == "PERMISSION_DENIED"


def test_cross_school_scope_and_api_denial(client: TestClient, db: Session) -> None:
    from app.core.scope import resolve_student_ids

    admin = User(
        phone="13200000034",
        password_hash="x",
        nickname="school_admin",
        role="school_admin",
        school_id=10,
    )
    db.add(admin)
    db.commit()

    _student(client, "13200000035")
    _student(client, "13200000036")
    same_school = _user(db, "13200000035")
    other_school = _user(db, "13200000036")
    same_school.school_id = 10
    other_school.school_id = 11
    db.commit()

    allowed = resolve_student_ids(db, admin, "SCHOOL")
    assert allowed is not None
    assert same_school.id in allowed
    assert other_school.id not in allowed

    response = client.get(
        f"/api/learn/stats?student_id={other_school.id}",
        headers=_token_headers(admin),
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "SCOPE_DENIED"


def test_parent_pending_binding_denied_on_wrong_book(
    client: TestClient, db: Session
) -> None:
    parent_headers = _parent(client, "13200000037")
    _student(client, "13200000038")
    parent_id = _user(db, "13200000037").id
    child_id = _user(db, "13200000038").id
    _bind(db, parent_id, child_id, status="pending")

    response = client.get(
        f"/api/learn/wrong-questions?student_id={child_id}", headers=parent_headers
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "SCOPE_DENIED"


def test_parent_cannot_take_exam_or_read_unbound_child(
    client: TestClient, db: Session
) -> None:
    parent_headers = _parent(client, "13200000039")
    _student(client, "13200000040")
    unrelated_id = _user(db, "13200000040").id

    exam = _published_exam(db, title="家长不可参加")
    started = client.post(f"/api/exams/{exam.id}/attempts", headers=parent_headers)
    assert started.status_code == 403
    assert started.json()["detail"]["code"] == "PERMISSION_DENIED"

    report = client.get(
        f"/api/learn/wrong-questions?student_id={unrelated_id}", headers=parent_headers
    )
    assert report.status_code == 403


def test_parent_cannot_read_bound_child_exam_report(
    client: TestClient, db: Session
) -> None:
    parent_headers = _parent(client, "13200000041")
    child_headers = _student(client, "13200000042")
    parent_id = _user(db, "13200000041").id
    child_id = _user(db, "13200000042").id
    _bind(db, parent_id, child_id)

    exam = _published_exam(db, title="家长不可见报告")
    attempt = client.post(f"/api/exams/{exam.id}/attempts", headers=child_headers)
    assert attempt.status_code == 200, attempt.text
    attempt_id = attempt.json()["id"]
    assert client.post(
        f"/api/exams/attempts/{attempt_id}/submit",
        headers=child_headers,
        json={"submit_token": "parent-report"},
    ).status_code == 200

    response = client.get(
        f"/api/exams/attempts/{attempt_id}/report", headers=parent_headers
    )
    assert response.status_code == 404


def test_old_token_revoked_across_protected_endpoints(
    client: TestClient, db: Session
) -> None:
    headers = _student(client, "13200000043", grade=3)
    confirm = client.put("/api/users/me/grade", json={"grade": 4}, headers=headers)
    assert confirm.status_code == 428, confirm.text
    token = confirm.json()["confirm_token"]

    applied = client.put(
        "/api/users/me/grade",
        json={"grade": 4, "confirm_token": token},
        headers=headers,
    )
    assert applied.status_code == 200, applied.text
    assert applied.json()["token_version"] == 1

    for path in ("/api/auth/me", "/api/learn/home", "/api/exams"):
        stale = client.get(path, headers=headers)
        assert stale.status_code == 401, path
        assert stale.json()["detail"]["code"] == "TOKEN_REVOKED"
