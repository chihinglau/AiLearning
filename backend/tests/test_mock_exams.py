"""P2-07 真题库与班级同卷模考测试。"""

from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.exam import Exam
from app.models.org import ClassMember, School, SchoolClass, TeacherClassAssignment
from app.models.user import AuditLog, User

PASSWORD = "pass1234"


def _add_user(
    db: Session,
    phone: str,
    role: str,
    *,
    school_id: int | None = None,
    grade: int | None = None,
) -> int:
    user = User(
        phone=phone,
        password_hash=hash_password(PASSWORD),
        nickname=f"{role}-{phone[-4:]}",
        role=role,
        school_id=school_id,
        grade=grade,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user.id


def _login(client: TestClient, phone: str) -> dict[str, str]:
    response = client.post(
        "/api/auth/login", data={"username": phone, "password": PASSWORD}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _add_exam(
    db: Session,
    *,
    title: str,
    grade: int,
    year: int,
    question_id: int,
    is_past_paper: bool = True,
    region: str | None = "深圳",
    class_id: int | None = None,
    source: str = "past_paper",
) -> int:
    exam = Exam(
        title=title,
        subject="math",
        grade=grade,
        year=year,
        source=source,
        exam_type="mock",
        total_score=5,
        time_limit_min=20,
        questions=[
            {
                "question_id": question_id,
                "score": 5,
                "section_index": 0,
                "section_name": "一、选择题",
            }
        ],
        status="published",
        region=region,
        is_past_paper=is_past_paper,
        class_id=class_id,
    )
    db.add(exam)
    db.commit()
    db.refresh(exam)
    return exam.id


def _class_context(db: Session, *, grade: int = 1) -> tuple[int, int, list[int], int]:
    school = School(name="模考测试学校")
    db.add(school)
    db.flush()
    teacher_id = _add_user(db, "13500000001", "teacher", school_id=school.id, grade=grade)
    school_class = SchoolClass(
        school_id=school.id,
        grade=grade,
        name="模考测试班",
        school_year="2026-2027",
    )
    db.add(school_class)
    db.flush()
    db.add(
        TeacherClassAssignment(
            teacher_id=teacher_id,
            class_id=school_class.id,
            subject="math",
            role_in_class="subject_teacher",
        )
    )
    members = [
        _add_user(db, phone, "student", school_id=school.id, grade=grade)
        for phone in ("13500000002", "13500000003")
    ]
    outsider = _add_user(db, "13500000004", "student", school_id=school.id, grade=grade)
    db.add_all(
        [ClassMember(class_id=school_class.id, student_id=member) for member in members]
    )
    db.commit()
    return school_class.id, teacher_id, members, outsider


def test_past_papers_filtered_by_grade_and_fields(
    client: TestClient, db: Session, sample_question: int
) -> None:
    grade1_id = _add_user(db, "13600000001", "student", grade=1)
    grade3_id = _add_user(db, "13600000002", "student", grade=3)
    assert grade1_id != grade3_id
    past_grade1 = _add_exam(
        db, title="一年级真题", grade=1, year=2025, question_id=sample_question
    )
    past_grade3 = _add_exam(
        db, title="三年级真题", grade=3, year=2024, question_id=sample_question
    )
    regular = _add_exam(
        db,
        title="普通单元测",
        grade=1,
        year=2025,
        question_id=sample_question,
        is_past_paper=False,
        region=None,
        source="system",
    )

    grade1 = _login(client, "13600000001")
    listed = client.get("/api/exams/past-papers", headers=grade1)
    assert listed.status_code == 200, listed.text
    rows = listed.json()
    assert [row["id"] for row in rows] == [past_grade1]
    row = rows[0]
    assert row["region"] == "深圳"
    assert row["year"] == 2025
    assert row["question_count"] == 1
    assert row["window_state"] == "unscheduled"
    assert regular not in [item["id"] for item in rows]
    assert past_grade3 not in [item["id"] for item in rows]

    filtered = client.get(
        "/api/exams/past-papers?subject=english", headers=grade1
    )
    assert filtered.status_code == 200
    assert filtered.json() == []

    grade3 = _login(client, "13600000002")
    rows3 = client.get("/api/exams/past-papers", headers=grade3).json()
    assert [row["id"] for row in rows3] == [past_grade3]


def test_class_mock_same_paper_and_membership(
    client: TestClient, db: Session, sample_question: int
) -> None:
    class_id, _, _, outsider = _class_context(db)
    template_id = _add_exam(
        db, title="一年级数学真题", grade=1, year=2025, question_id=sample_question
    )
    teacher = _login(client, "13500000001")
    student_one = _login(client, "13500000002")
    student_two = _login(client, "13500000003")
    outsider_headers = _login(client, "13500000004")

    now = datetime.utcnow()
    assigned = client.post(
        "/api/exams/mock",
        headers=teacher,
        json={
            "class_id": class_id,
            "exam_id": template_id,
            "window_start": (now - timedelta(minutes=5)).isoformat(),
            "window_end": (now + timedelta(hours=2)).isoformat(),
        },
    )
    assert assigned.status_code == 200, assigned.text
    body = assigned.json()
    assert body["student_count"] == 2
    assert body["question_count"] == 1
    assert body["class_id"] == class_id
    mock_id = body["exam_id"]

    # 本班学生可见班级模考，班外学生不可见
    member_list = client.get("/api/exams", headers=student_one)
    assert member_list.status_code == 200
    assert mock_id in [item["id"] for item in member_list.json()]
    row = next(item for item in member_list.json() if item["id"] == mock_id)
    assert row["class_id"] == class_id
    assert row["window_state"] == "open"
    outsider_list = client.get("/api/exams", headers=outsider_headers)
    assert mock_id not in [item["id"] for item in outsider_list.json()]

    # 同班同卷：两名学生拿到的题目完全一致
    started_one = client.post(f"/api/exams/{mock_id}/attempts", headers=student_one, json={})
    assert started_one.status_code == 200, started_one.text
    started_two = client.post(f"/api/exams/{mock_id}/attempts", headers=student_two, json={})
    assert started_two.status_code == 200, started_two.text
    ids_one = [item["id"] for item in started_one.json()["exam"]["questions"]]
    ids_two = [item["id"] for item in started_two.json()["exam"]["questions"]]
    assert ids_one == ids_two == [sample_question]

    denied = client.post(
        f"/api/exams/{mock_id}/attempts", headers=outsider_headers, json={}
    )
    assert denied.status_code == 403
    assert denied.json()["detail"]["code"] == "EXAM_NOT_MEMBER"

    actions = list(db.scalars(select(AuditLog.action)))
    assert "exam.mock.assign" in actions


def test_class_mock_guards(
    client: TestClient, db: Session, sample_question: int
) -> None:
    class_id, _, _, _ = _class_context(db)
    template_id = _add_exam(
        db, title="三年级真题", grade=3, year=2025, question_id=sample_question
    )
    teacher = _login(client, "13500000001")

    _add_user(
        db,
        "13500000011",
        "teacher",
        school_id=db.get(SchoolClass, class_id).school_id,
        grade=1,
    )
    outsider_teacher = _login(client, "13500000011")
    denied = client.post(
        "/api/exams/mock",
        headers=outsider_teacher,
        json={"class_id": class_id, "exam_id": template_id},
    )
    assert denied.status_code == 403
    assert denied.json()["detail"]["code"] == "CLASS_FORBIDDEN"

    mismatch = client.post(
        "/api/exams/mock",
        headers=teacher,
        json={"class_id": class_id, "exam_id": template_id},
    )
    assert mismatch.status_code == 422
    assert mismatch.json()["detail"]["code"] == "CLASS_GRADE_MISMATCH"

    template_ok = _add_exam(
        db, title="一年级真题", grade=1, year=2025, question_id=sample_question
    )
    now = datetime.utcnow()
    bad_window = client.post(
        "/api/exams/mock",
        headers=teacher,
        json={
            "class_id": class_id,
            "exam_id": template_ok,
            "window_start": (now + timedelta(hours=1)).isoformat(),
            "window_end": now.isoformat(),
        },
    )
    assert bad_window.status_code == 422
    assert bad_window.json()["detail"]["code"] == "EXAM_WINDOW_INVALID"

    missing = client.post(
        "/api/exams/mock",
        headers=teacher,
        json={"class_id": class_id, "exam_id": 99999},
    )
    assert missing.status_code == 404
