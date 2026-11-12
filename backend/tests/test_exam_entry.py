"""EX-01：考试入口口径一致性与蓝图列表接口（D-04 §8.7）。"""

from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.exam import Exam, ExamAttempt, ExamBlueprint
from app.models.user import User
from app.services.recommendation import build_pending_exams


def _student(client: TestClient, db: Session, phone: str = "13211110001", grade: int = 1):
    response = client.post(
        "/api/auth/register",
        json={"phone": phone, "password": "pass1234", "grade": grade},
    )
    assert response.status_code == 201, response.text
    login = client.post(
        "/api/auth/login", data={"username": phone, "password": "pass1234"}
    )
    assert login.status_code == 200, login.text
    user = db.scalar(select(User).where(User.phone == phone))
    assert user is not None
    return {"Authorization": f"Bearer {login.json()['access_token']}"}, user


def _exam(db: Session, **overrides) -> Exam:
    data = {
        "title": "一年级数学单元测",
        "subject": "math",
        "grade": 1,
        "source": "blueprint",
        "status": "published",
        "exam_type": "unit",
        "total_score": 100,
        "time_limit_min": 60,
        "questions": [],
        "is_past_paper": False,
    }
    data.update(overrides)
    row = Exam(**data)
    db.add(row)
    db.flush()
    db.commit()
    return row


def test_pending_exams_match_visible_exam_list(client: TestClient, db: Session) -> None:
    """首页待办与考试列表必须同一口径：真题/作业卷/其它年级不得虚标。"""
    headers, user = _student(client, db)
    normal = _exam(db, title="一年级数学单元测")
    _exam(db, title="一年级真题", is_past_paper=True)
    _exam(db, title="班级作业卷", source="assignment")
    _exam(db, title="二年级期中", grade=2)
    _exam(db, title="草稿卷", status="draft")

    pending = build_pending_exams(db, user=user, now=datetime.utcnow())
    assert [item["exam_id"] for item in pending] == [normal.id]
    assert pending[0]["entry"] == "exam"
    assert pending[0]["subject"] == "math"

    listed = client.get("/api/exams", headers=headers)
    assert listed.status_code == 200, listed.text
    assert [item["id"] for item in listed.json()] == [normal.id]


def test_pending_exams_skip_submitted_and_closed(client: TestClient, db: Session) -> None:
    headers, user = _student(client, db, phone="13211110002")
    submitted = _exam(db, title="已交卷")
    db.add(
        ExamAttempt(
            user_id=user.id,
            exam_id=submitted.id,
            seed=1,
            status="submitted",
        )
    )
    db.commit()
    _exam(
        db,
        title="已关闭窗口",
        window_start=datetime.utcnow().replace(year=2020),
        window_end=datetime.utcnow().replace(year=2021),
    )
    pending = build_pending_exams(db, user=user, now=datetime.utcnow())
    assert pending == []


def test_blueprints_require_write_permission(
    client: TestClient, db: Session, admin_headers: dict[str, str]
) -> None:
    db.add(
        ExamBlueprint(
            code="math_g1_unit",
            name="一年级数学单元测",
            subject="math",
            grade=1,
            exam_type="unit",
            total_score=100,
            time_limit_min=40,
            sections=[],
            difficulty_mix={},
            is_active=True,
        )
    )
    db.add(
        ExamBlueprint(
            code="disabled",
            name="停用蓝图",
            subject="math",
            is_active=False,
            sections=[],
            difficulty_mix={},
        )
    )
    db.commit()

    student, _ = _student(client, db, phone="13211110003")
    denied = client.get("/api/exams/blueprints", headers=student)
    assert denied.status_code == 403, denied.text

    ok = client.get("/api/exams/blueprints", headers=admin_headers)
    assert ok.status_code == 200, ok.text
    rows = ok.json()
    assert [row["code"] for row in rows] == ["math_g1_unit"]
    assert rows[0]["time_limit_min"] == 40


def test_generated_exam_is_visible_in_entry(client: TestClient, db: Session) -> None:
    """L20：组卷发布后的普通卷立即进入首页待办与考试列表。"""
    headers, user = _student(client, db, phone="13211110004")
    generated = _exam(db, title="新发布的一年级单元测", source="generated")

    pending = build_pending_exams(db, user=user, now=datetime.utcnow())
    assert [item["exam_id"] for item in pending] == [generated.id]

    listed = client.get("/api/exams", headers=headers)
    assert listed.status_code == 200, listed.text
    assert [item["id"] for item in listed.json()] == [generated.id]
