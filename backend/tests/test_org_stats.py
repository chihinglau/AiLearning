"""P1-03 班级学情聚合（D-03 §6.5：仅聚合值，不返回逐题原文）。"""

from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.content import Chapter, KnowledgePoint, Question, Textbook
from app.models.org import ClassMember, School, SchoolClass, TeacherClassAssignment
from app.models.practice import MasteryScore, StudentQuestionRecord
from app.models.user import User

PASSWORD = "pass1234"


def _user(
    db: Session,
    phone: str,
    role: str,
    *,
    school_id: int | None = None,
    grade: int | None = None,
    teacher_subjects: list[str] | None = None,
) -> User:
    user = User(
        phone=phone,
        password_hash=hash_password(PASSWORD),
        nickname=role,
        role=role,
        school_id=school_id,
        grade=grade,
        teacher_subjects=teacher_subjects,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _login(client: TestClient, phone: str) -> dict[str, str]:
    response = client.post(
        "/api/auth/login", data={"username": phone, "password": PASSWORD}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _question(db: Session, chapter_id: int, subject: str, kp_id: int) -> Question:
    question = Question(
        chapter_id=chapter_id,
        knowledge_point_id=kp_id,
        subject=subject,
        q_type="choice",
        content={"stem": "示例题"},
        answer={"value": "A"},
    )
    db.add(question)
    db.flush()
    return question


def _answer(
    db: Session, user_id: int, question_id: int, *, correct: bool
) -> StudentQuestionRecord:
    record = StudentQuestionRecord(
        user_id=user_id,
        question_id=question_id,
        is_correct=correct,
        attempted_at=datetime.utcnow(),
    )
    db.add(record)
    return record


def _setup_class(db: Session) -> tuple[School, SchoolClass, User, User, User]:
    school = School(name="聚合小学")
    db.add(school)
    db.flush()
    room = SchoolClass(school_id=school.id, grade=4, name="四年级1班", school_year="2026-2027")
    db.add(room)
    db.flush()
    teacher = _user(
        db, "13610000001", "teacher", school_id=school.id, teacher_subjects=["math"]
    )
    db.add(TeacherClassAssignment(teacher_id=teacher.id, class_id=room.id, subject="math"))
    student_a = _user(db, "13610000002", "student", school_id=school.id, grade=4)
    student_b = _user(db, "13610000003", "student", school_id=school.id, grade=4)
    db.add_all(
        [
            ClassMember(class_id=room.id, student_id=student_a.id),
            ClassMember(class_id=room.id, student_id=student_b.id),
        ]
    )
    db.commit()
    return school, room, teacher, student_a, student_b


def test_class_stats_returns_aggregates_only(client: TestClient, db: Session) -> None:
    school, room, _, student_a, student_b = _setup_class(db)
    textbook = Textbook(subject="math", grade=4, version="人教版")
    db.add(textbook)
    db.flush()
    chapter = Chapter(textbook_id=textbook.id, grade=4, name="分数的认识")
    db.add(chapter)
    db.flush()
    kp_fraction = KnowledgePoint(subject="math", name="分数意义", grade=4)
    kp_compare = KnowledgePoint(subject="math", name="分数比较", grade=4)
    db.add_all([kp_fraction, kp_compare])
    db.flush()

    math_q1 = _question(db, chapter.id, "math", kp_fraction.id)
    math_q2 = _question(db, chapter.id, "math", kp_compare.id)
    db.add_all(
        [
            _answer(db, student_a.id, math_q1.id, correct=True),
            _answer(db, student_b.id, math_q2.id, correct=False),
            MasteryScore(user_id=student_a.id, knowledge_point_id=kp_fraction.id, score=40),
            MasteryScore(user_id=student_b.id, knowledge_point_id=kp_fraction.id, score=60),
            MasteryScore(user_id=student_a.id, knowledge_point_id=kp_compare.id, score=80),
            MasteryScore(user_id=student_b.id, knowledge_point_id=kp_compare.id, score=80),
        ]
    )
    db.commit()

    headers = _login(client, "13610000001")
    response = client.get(
        f"/api/org/classes/{room.id}/stats", params={"subject": "math"}, headers=headers
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert set(payload) == {
        "class_id",
        "class_name",
        "grade",
        "subject",
        "student_count",
        "active_student_count",
        "submission_rate",
        "total_answered",
        "accuracy",
        "avg_mastery",
        "weak_points",
    }
    assert payload["student_count"] == 2
    assert payload["active_student_count"] == 2
    assert payload["submission_rate"] == 1.0
    assert payload["total_answered"] == 2
    assert payload["accuracy"] == 0.5
    assert payload["avg_mastery"] == 65.0
    assert payload["weak_points"] == [
        {
            "knowledge_point_id": kp_fraction.id,
            "name": "分数意义",
            "subject": "math",
            "avg_mastery": 50.0,
        }
    ]
    assert "records" not in payload and "students" not in payload
    assert school.id == room.school_id


def test_class_stats_enforces_scope(client: TestClient, db: Session) -> None:
    school, room, teacher, _, _ = _setup_class(db)
    other_school = School(name="其他小学")
    db.add(other_school)
    db.flush()
    other_admin = _user(db, "13610000011", "school_admin", school_id=other_school.id)
    own_admin = _user(db, "13610000012", "school_admin", school_id=school.id)
    other_teacher = _user(
        db, "13610000013", "teacher", school_id=school.id, teacher_subjects=["math"]
    )
    student = _user(db, "13610000014", "student", school_id=school.id, grade=4)
    db.commit()

    teacher_headers = _login(client, teacher.phone)
    wrong_subject = client.get(
        f"/api/org/classes/{room.id}/stats",
        params={"subject": "chinese"},
        headers=teacher_headers,
    )
    assert wrong_subject.status_code == 403
    assert wrong_subject.json()["detail"]["code"] == "SCOPE_DENIED"

    other_teacher_headers = _login(client, other_teacher.phone)
    not_assigned = client.get(
        f"/api/org/classes/{room.id}/stats", headers=other_teacher_headers
    )
    assert not_assigned.status_code == 403
    assert not_assigned.json()["detail"]["code"] == "SCOPE_DENIED"

    own_admin_headers = _login(client, own_admin.phone)
    allowed = client.get(f"/api/org/classes/{room.id}/stats", headers=own_admin_headers)
    assert allowed.status_code == 200
    assert allowed.json()["student_count"] == 2

    other_admin_headers = _login(client, other_admin.phone)
    cross_school = client.get(
        f"/api/org/classes/{room.id}/stats", headers=other_admin_headers
    )
    assert cross_school.status_code == 403
    assert cross_school.json()["detail"]["code"] == "SCOPE_DENIED"

    student_headers = _login(client, student.phone)
    denied = client.get(f"/api/org/classes/{room.id}/stats", headers=student_headers)
    assert denied.status_code == 403
    assert denied.json()["detail"]["code"] == "PERMISSION_DENIED"
