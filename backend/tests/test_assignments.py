"""P2-03 班级作业：教师布置统一卷、学生作答、教师批改主观题。"""

from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.content import Question
from app.models.exam import ExamAttempt
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


def _add_answer_questions(db: Session, chapter_id: int, count: int = 2) -> list[int]:
    ids: list[int] = []
    for index in range(count):
        question = Question(
            chapter_id=chapter_id,
            subject="math",
            q_type="answer",
            content={"stem": f"请写出第 {index + 1} 题的解题过程"},
            answer={"value": f"参考解答 {index + 1}", "scoring_points": ["步骤完整", "结果正确"]},
            analysis="分步作答",
            difficulty=2,
        )
        db.add(question)
        db.flush()
        ids.append(question.id)
    db.commit()
    return ids


def _class_context(
    db: Session, *, grade: int = 1
) -> tuple[int, int, list[int], int]:
    """建学校/班级/数学教师/班内学生/班外学生，返回 (class_id, teacher_id, members, outsider)。"""
    school = School(name="作业测试学校")
    db.add(school)
    db.flush()
    teacher_id = _add_user(
        db,
        "13500000001",
        "teacher",
        school_id=school.id,
        grade=grade,
    )
    school_class = SchoolClass(
        school_id=school.id,
        grade=grade,
        name="作业测试班",
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
        [
            ClassMember(class_id=school_class.id, student_id=student_id)
            for student_id in members
        ]
    )
    db.commit()
    return school_class.id, teacher_id, members, outsider


def _create_assignment(
    client: TestClient,
    headers: dict[str, str],
    *,
    class_id: int,
    chapter_id: int,
    count: int = 2,
) -> dict:
    response = client.post(
        "/api/assignments",
        headers=headers,
        json={
            "class_id": class_id,
            "title": "第 1 单元课后作业",
            "subject": "math",
            "chapter_ids": [chapter_id],
            "count": count,
            "q_types": ["answer"],
            "time_limit_min": 30,
            "due_at": (datetime.utcnow() + timedelta(days=3)).isoformat(),
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _take_and_submit(
    client: TestClient,
    headers: dict[str, str],
    *,
    exam_id: int,
) -> tuple[int, list[dict]]:
    started = client.post(f"/api/exams/{exam_id}/attempts", headers=headers, json={})
    assert started.status_code == 200, started.text
    attempt_id = int(started.json()["id"])
    questions = started.json()["exam"]["questions"]
    answers = [
        {
            "question_id": item["id"],
            "user_answer": {"value": f"作答-{item['id']}"},
        }
        for item in questions
    ]
    submitted = client.post(
        f"/api/exams/attempts/{attempt_id}/submit",
        headers=headers,
        json={"submit_token": f"submit-{attempt_id}", "answers": answers},
    )
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["status"] == "grading"
    return attempt_id, questions


def test_teacher_assigns_class_paper_student_submits_and_teacher_grades(
    client: TestClient, db: Session, sample_chapter: int
) -> None:
    class_id, teacher_id, members, outsider = _class_context(db)
    _add_answer_questions(db, sample_chapter, count=2)
    teacher = _login(client, "13500000001")
    student = _login(client, "13500000002")
    other_student = _login(client, "13500000003")
    outsider_headers = _login(client, "13500000004")

    created = _create_assignment(
        client, teacher, class_id=class_id, chapter_id=sample_chapter
    )
    assert created["student_count"] == 2
    assert created["pending_grading"] == 0
    assert {item["student_id"] for item in created["students"]} == set(members)
    assert all(item["status"] == "not_started" for item in created["students"])
    assignment_id = created["id"]
    exam_id = created["exam_id"]

    # 作业卷不进入通用考试列表
    listed_exams = client.get("/api/exams", headers=student)
    assert listed_exams.status_code == 200
    assert exam_id not in [item["id"] for item in listed_exams.json()]

    # 班内学生可见；班外学生不可见也不能作答
    in_list = client.get("/api/assignments", headers=student)
    assert in_list.status_code == 200, in_list.text
    assert [item["id"] for item in in_list.json()] == [assignment_id]

    out_list = client.get("/api/assignments", headers=outsider_headers)
    assert out_list.status_code == 200
    assert out_list.json() == []
    denied = client.post(f"/api/exams/{exam_id}/attempts", headers=outsider_headers, json={})
    assert denied.status_code == 403
    assert denied.json()["detail"]["code"] == "ASSIGNMENT_NOT_MEMBER"

    # 两名学生作答交卷
    attempt_one, questions = _take_and_submit(client, student, exam_id=exam_id)
    attempt_two, _ = _take_and_submit(client, other_student, exam_id=exam_id)

    detail = client.get(f"/api/assignments/{assignment_id}", headers=student)
    assert detail.status_code == 200, detail.text
    assert detail.json()["submitted_count"] == 2
    assert detail.json()["pending_grading"] == 2
    assert detail.json()["my_status"] == "grading"

    grading = client.get(f"/api/assignments/{assignment_id}/grading", headers=teacher)
    assert grading.status_code == 200, grading.text
    items = grading.json()["items"]
    assert len(items) == 4
    assert {item["attempt_id"] for item in items} == {attempt_one, attempt_two}
    assert all(item["q_type"] == "answer" for item in items)
    assert all(item["current_score"] is None for item in items)

    graded = client.post(
        f"/api/assignments/{assignment_id}/grade",
        headers=teacher,
        json={
            "items": [
                {
                    "attempt_id": item["attempt_id"],
                    "question_id": item["question_id"],
                    "score": 3 if index % 2 == 0 else 5,
                    "comment": "步骤完整",
                }
                for index, item in enumerate(items)
            ]
        },
    )
    assert graded.status_code == 200, graded.text
    assert graded.json() == {
        "graded": 4,
        "completed_attempts": 2,
        "pending_attempts": 0,
    }

    after = client.get(f"/api/assignments/{assignment_id}", headers=student)
    assert after.status_code == 200
    payload = after.json()
    assert payload["pending_grading"] == 0
    assert payload["my_status"] == "completed"
    assert payload["my_total_score"] == 8.0
    # 学生端不暴露同班名单与成绩
    assert payload["students"] == []

    teacher_detail = client.get(f"/api/assignments/{assignment_id}", headers=teacher)
    assert teacher_detail.status_code == 200
    row = next(
        item
        for item in teacher_detail.json()["students"]
        if item["student_id"] == members[0]
    )
    assert row["status"] == "completed"
    assert row["subjective_score"] == 8.0
    assert row["total_score"] == 8.0

    attempt = db.get(ExamAttempt, attempt_one)
    assert attempt is not None and attempt.status == "completed"
    assert attempt.total_score == 8.0
    actions = set(db.scalars(select(AuditLog.action)))
    assert {"assignment.create", "assignment.answer.grade", "assignment.grade"} <= actions

    # 学生报告可用，且作业卷来源正确
    report = client.get(f"/api/exams/attempts/{attempt_one}/report", headers=student)
    assert report.status_code == 200, report.text
    assert report.json()["total_score"] == 8.0


def test_assignment_permission_and_grading_guards(
    client: TestClient, db: Session, sample_chapter: int, sample_question: int
) -> None:
    class_id, teacher_id, _, _ = _class_context(db)
    _add_answer_questions(db, sample_chapter, count=2)
    teacher = _login(client, "13500000001")
    student = _login(client, "13500000002")

    # 未授课教师不能布置作业
    _add_user(
        db, "13500000011", "teacher", school_id=db.get(SchoolClass, class_id).school_id, grade=1
    )
    outsider_headers = _login(client, "13500000011")
    denied_create = client.post(
        "/api/assignments",
        headers=outsider_headers,
        json={
            "class_id": class_id,
            "title": "越权作业",
            "subject": "math",
            "chapter_ids": [sample_chapter],
            "count": 2,
            "q_types": ["answer"],
        },
    )
    assert denied_create.status_code == 403
    assert denied_create.json()["detail"]["code"] == "ASSIGNMENT_NOT_ALLOWED"

    created = _create_assignment(
        client, teacher, class_id=class_id, chapter_id=sample_chapter
    )
    assignment_id = created["id"]

    # 非创建者/非授课教师不能查看与批改
    denied_detail = client.get(f"/api/assignments/{assignment_id}", headers=outsider_headers)
    assert denied_detail.status_code == 403
    denied_grading = client.get(
        f"/api/assignments/{assignment_id}/grading", headers=outsider_headers
    )
    assert denied_grading.status_code == 403

    attempt_id, questions = _take_and_submit(
        client, student, exam_id=created["exam_id"]
    )

    # 客观题不支持教师批改
    rejected_objective = client.post(
        f"/api/assignments/{assignment_id}/grade",
        headers=teacher,
        json={
            "items": [
                {"attempt_id": attempt_id, "question_id": sample_question, "score": 1}
            ]
        },
    )
    assert rejected_objective.status_code == 422
    assert rejected_objective.json()["detail"]["code"] == "QUESTION_NOT_SUBJECTIVE"

    # 评分不得超过满分（每节 5 分）
    rejected_score = client.post(
        f"/api/assignments/{assignment_id}/grade",
        headers=teacher,
        json={
            "items": [
                {"attempt_id": attempt_id, "question_id": questions[0]["id"], "score": 6}
            ]
        },
    )
    assert rejected_score.status_code == 422
    assert rejected_score.json()["detail"]["code"] == "SCORE_EXCEEDED"

    # 班级无学生时不能布置
    empty_class = SchoolClass(
        school_id=db.get(SchoolClass, class_id).school_id,
        grade=1,
        name="空班",
        school_year="2026-2027",
    )
    db.add(empty_class)
    db.commit()
    db.add(
        TeacherClassAssignment(
            teacher_id=teacher_id,
            class_id=empty_class.id,
            subject="math",
        )
    )
    db.commit()
    empty = client.post(
        "/api/assignments",
        headers=teacher,
        json={
            "class_id": empty_class.id,
            "title": "空班作业",
            "subject": "math",
            "chapter_ids": [sample_chapter],
            "count": 2,
            "q_types": ["answer"],
        },
    )
    assert empty.status_code == 422
    assert empty.json()["detail"]["code"] == "CLASS_EMPTY"

    # 题目不属于试卷时拒绝评分
    unrelated = _add_answer_questions(db, sample_chapter, count=1)[0]
    unknown = client.post(
        f"/api/assignments/{assignment_id}/grade",
        headers=teacher,
        json={"items": [{"attempt_id": attempt_id, "question_id": unrelated, "score": 3}]},
    )
    assert unknown.status_code == 422
    assert unknown.json()["detail"]["code"] == "QUESTION_NOT_SUBJECTIVE"
