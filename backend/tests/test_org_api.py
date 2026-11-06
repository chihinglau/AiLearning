"""P1-02 班级/成员/授课分配 API 与教师范围校验。"""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import AuditLog, User

PASSWORD = "pass1234"


def _add_user(
    db: Session,
    phone: str,
    role: str,
    *,
    school_id: int | None = None,
    grade: int | None = None,
    **extra: object,
) -> int:
    user = User(
        phone=phone,
        password_hash=hash_password(PASSWORD),
        nickname=role,
        role=role,
        school_id=school_id,
        grade=grade,
        **extra,
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


def _create_school(client: TestClient, headers: dict[str, str], name: str) -> int:
    response = client.post("/api/org/schools", headers=headers, json={"name": name})
    assert response.status_code == 201, response.text
    return int(response.json()["id"])


def _create_class(
    client: TestClient, headers: dict[str, str], **overrides: object
) -> int:
    payload = {
        "grade": 4,
        "name": "四年级1班",
        "school_year": "2026-2027",
        **overrides,
    }
    response = client.post("/api/org/classes", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return int(response.json()["id"])


def test_school_admin_manages_class_members_and_teacher_sees_class(
    client: TestClient, db: Session, admin_headers: dict[str, str]
) -> None:
    school_id = _create_school(client, admin_headers, "南山实验学校")
    _add_user(db, "13600000001", "school_admin", school_id=school_id)
    teacher_id = _add_user(
        db,
        "13600000002",
        "teacher",
        school_id=school_id,
        teacher_subjects=["math"],
        grade_start=1,
        grade_end=6,
    )
    student_id = _add_user(db, "13600000003", "student", school_id=school_id, grade=4)
    school_admin = _login(client, "13600000001")
    teacher = _login(client, "13600000002")

    class_id = _create_class(client, school_admin)

    added = client.post(
        f"/api/org/classes/{class_id}/members",
        headers=school_admin,
        json={"student_ids": [student_id]},
    )
    assert added.status_code == 201, added.text
    assert added.json() == {"added": 1, "skipped": 0}

    again = client.post(
        f"/api/org/classes/{class_id}/members",
        headers=school_admin,
        json={"student_ids": [student_id]},
    )
    assert again.status_code == 201
    assert again.json() == {"added": 0, "skipped": 1}

    assignment = client.post(
        "/api/org/assignments",
        headers=school_admin,
        json={"teacher_id": teacher_id, "class_id": class_id, "subject": "math"},
    )
    assert assignment.status_code == 201, assignment.text

    classes = client.get("/api/org/classes", headers=teacher)
    assert classes.status_code == 200, classes.text
    assert [item["id"] for item in classes.json()] == [class_id]
    assert classes.json()[0]["member_count"] == 1

    members = client.get(f"/api/org/classes/{class_id}/members", headers=teacher)
    assert members.status_code == 200
    assert members.json() == [student_id]

    own_assignments = client.get("/api/org/assignments", headers=teacher)
    assert own_assignments.status_code == 200
    assert [item["teacher_id"] for item in own_assignments.json()] == [teacher_id]

    actions = set(db.scalars(select(AuditLog.action)))
    assert {"org.school.create", "org.class.create", "org.member.add", "org.teacher.assign"} <= actions


def test_cross_school_and_role_checks(
    client: TestClient, db: Session, admin_headers: dict[str, str]
) -> None:
    school_a = _create_school(client, admin_headers, "A 校")
    school_b = _create_school(client, admin_headers, "B 校")
    _add_user(db, "13600000011", "school_admin", school_id=school_a)
    _add_user(db, "13600000012", "school_admin", school_id=school_b)
    student_b = _add_user(db, "13600000013", "student", school_id=school_b, grade=4)
    _add_user(db, "13600000014", "student", school_id=school_a, grade=4)
    admin_a = _login(client, "13600000011")
    admin_b = _login(client, "13600000012")
    student = _login(client, "13600000014")

    class_a = _create_class(client, admin_a)

    cross_class = client.post(
        "/api/org/classes",
        headers=admin_b,
        json={"school_id": school_a, "grade": 4, "name": "越权班", "school_year": "2026-2027"},
    )
    assert cross_class.status_code == 403
    assert cross_class.json()["detail"]["code"] == "CROSS_SCHOOL"

    cross_member = client.post(
        f"/api/org/classes/{class_a}/members",
        headers=admin_b,
        json={"student_ids": [student_b]},
    )
    assert cross_member.status_code in (403, 422)
    assert cross_member.json()["detail"]["code"] in ("CROSS_SCHOOL", "CLASS_DENIED")

    denied = client.get("/api/org/classes", headers=student)
    assert denied.status_code == 403
    assert denied.json()["detail"]["code"] == "PERMISSION_DENIED"


def test_assignment_validation_rules(
    client: TestClient, db: Session, admin_headers: dict[str, str]
) -> None:
    school_id = _create_school(client, admin_headers, "规则小学")
    _add_user(db, "13600000021", "school_admin", school_id=school_id)
    teacher_id = _add_user(
        db,
        "13600000022",
        "teacher",
        school_id=school_id,
        teacher_subjects=["math"],
        grade_start=1,
        grade_end=6,
    )
    limited_teacher = _add_user(
        db,
        "13600000024",
        "teacher",
        school_id=school_id,
        teacher_subjects=["math"],
        grade_start=1,
        grade_end=3,
    )
    other_teacher = _add_user(
        db,
        "13600000023",
        "head_teacher",
        school_id=school_id,
        teacher_subjects=["math"],
    )
    admin = _login(client, "13600000021")
    class_id = _create_class(client, admin, grade=4)

    wrong_subject = client.post(
        "/api/org/assignments",
        headers=admin,
        json={"teacher_id": teacher_id, "class_id": class_id, "subject": "chinese"},
    )
    assert wrong_subject.status_code == 422
    assert wrong_subject.json()["detail"]["code"] == "SUBJECT_NOT_ALLOWED"

    out_of_range = client.post(
        "/api/org/assignments",
        headers=admin,
        json={"teacher_id": limited_teacher, "class_id": class_id, "subject": "math"},
    )
    assert out_of_range.status_code == 422
    assert out_of_range.json()["detail"]["code"] == "GRADE_OUT_OF_RANGE"

    head = client.post(
        "/api/org/assignments",
        headers=admin,
        json={
            "teacher_id": other_teacher,
            "class_id": class_id,
            "subject": "math",
            "role_in_class": "head_teacher",
        },
    )
    assert head.status_code == 201, head.text

    duplicate = client.post(
        "/api/org/assignments",
        headers=admin,
        json={"teacher_id": other_teacher, "class_id": class_id, "subject": "math"},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"]["code"] == "ASSIGNMENT_EXISTS"

    conflict = client.post(
        "/api/org/assignments",
        headers=admin,
        json={
            "teacher_id": teacher_id,
            "class_id": class_id,
            "subject": "math",
            "role_in_class": "head_teacher",
        },
    )
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["code"] == "HEAD_TEACHER_EXISTS"
