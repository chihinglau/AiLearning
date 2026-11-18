"""EX-04~EX-08：考试中心与真题库设计落地验收（D-09 §9，L21~L26）。

覆盖 D-04 §8.7.1 口径契约不变前提下的筛选下推、状态矩阵数据、
真题库服务端年份过滤与溯源、详情/报告历史接口、分页与兼容回归。
"""

from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.exam import Exam, ExamAttempt, ExamBlueprint
from app.models.user import User


def _student(
    client: TestClient, db: Session, phone: str = "13211110001", grade: int = 1
):
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


def _paper(db: Session, **overrides) -> Exam:
    data = {
        "title": "历年真题卷",
        "is_past_paper": True,
        "source": "mock",
        "exam_type": "mock",
        "year": 2020,
        "region": "深圳",
        "source_name": "深圳市教育考试院公开真题",
    }
    data.update(overrides)
    return _exam(db, **data)


# ---------------------------------------------------------------- L21


def test_exam_center_filters_never_widen_visibility(
    client: TestClient, db: Session
) -> None:
    """筛选只能收窄 §8.7.1 谓词：真题/作业卷/其它年级/草稿不得被筛回来。"""
    headers, _ = _student(client, db, phone="13211111001")
    normal = _exam(db, title="一年级数学单元测", subject="math", exam_type="unit")
    _exam(db, title="一年级语文单元测", subject="chinese", exam_type="unit")
    _exam(db, title="一年级数学期末", subject="math", exam_type="final")
    _exam(db, title="一年级真题", is_past_paper=True, subject="math")
    _exam(db, title="班级作业卷", source="assignment", subject="math")
    _exam(db, title="二年级数学单元测", grade=2, subject="math")
    _exam(db, title="草稿卷", status="draft", subject="math")

    response = client.get(
        "/api/exams",
        params={"type": "unit", "subject": "math", "status": "available"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    assert [item["id"] for item in response.json()] == [normal.id]
    assert response.headers["X-Total-Count"] == "1"

    # 搜索与窗口状态同样是 AND 收窄
    assert [item["id"] for item in client.get(
        "/api/exams", params={"q": "数学单元"}, headers=headers
    ).json()] == [normal.id]
    assert client.get(
        "/api/exams", params={"q": "不存在的试卷"}, headers=headers
    ).json() == []

    scheduled = _exam(
        db,
        title="下周开考",
        window_start=datetime.utcnow() + timedelta(days=2),
        window_end=datetime.utcnow() + timedelta(days=3),
    )
    sched = client.get(
        "/api/exams", params={"window_state": "scheduled"}, headers=headers
    )
    assert [item["id"] for item in sched.json()] == [scheduled.id]
    assert sched.json()[0]["window_state"] == "scheduled"


def test_exam_center_attempt_states_pagination_and_compat(
    client: TestClient, db: Session
) -> None:
    """状态矩阵数据源、分页总数头、不带参数时与 CR-003 行为一致。"""
    headers, user = _student(client, db, phone="13211111002")
    doing = _exam(db, title="进行中卷")
    done = _exam(db, title="已完成卷")
    _exam(db, title="未考卷")
    db.add(ExamAttempt(user_id=user.id, exam_id=doing.id, seed=1, status="in_progress"))
    db.add(ExamAttempt(user_id=user.id, exam_id=done.id, seed=1, status="submitted"))
    db.commit()

    in_progress = client.get(
        "/api/exams", params={"status": "in_progress"}, headers=headers
    ).json()
    assert [item["id"] for item in in_progress] == [doing.id]
    assert in_progress[0]["attempt"]["status"] == "in_progress"
    assert in_progress[0]["attempt_count"] == 1

    completed = client.get(
        "/api/exams", params={"status": "completed"}, headers=headers
    ).json()
    assert [item["id"] for item in completed] == [done.id]

    paged = client.get(
        "/api/exams", params={"page": 1, "page_size": 2}, headers=headers
    )
    assert len(paged.json()) == 2
    assert paged.headers["X-Total-Count"] == "3"

    # 兼容：不带新参数时仍是原来的列表行为
    plain = client.get("/api/exams", headers=headers)
    assert plain.status_code == 200
    assert len(plain.json()) == 3
    assert "X-Total-Count" in plain.headers


# ---------------------------------------------------------------- L23 / L25


def test_past_paper_filters_server_side_and_old_years(
    client: TestClient, db: Session
) -> None:
    """年份/学科/地区由服务端过滤，历史年份不会被 limit(60) 截断。"""
    headers, _ = _student(client, db, phone="13211111003")
    old = _paper(
        db, title="2018 全国数学真题", year=2018, region="全国", subject="math"
    )
    _paper(db, title="2020 广东语文真题", year=2020, region="广东", subject="chinese")
    _paper(db, title="2026 深圳数学真题", year=2026, region="深圳", subject="math")
    _paper(db, title="二年级真题", year=2019, grade=2)  # 学生锁定一年级

    by_year = client.get(
        "/api/exams/past-papers", params={"year": 2018}, headers=headers
    )
    assert [item["id"] for item in by_year.json()] == [old.id]
    assert by_year.headers["X-Total-Count"] == "1"

    assert len(client.get(
        "/api/exams/past-papers", params={"subject": "chinese"}, headers=headers
    ).json()) == 1
    assert len(client.get(
        "/api/exams/past-papers", params={"region": "广东"}, headers=headers
    ).json()) == 1

    filters = client.get("/api/exams/past-papers/filters", headers=headers)
    assert filters.status_code == 200, filters.text
    body = filters.json()
    assert 2018 in body["years"] and 2026 in body["years"]
    assert "chinese" in body["subjects"]
    assert "广东" in body["regions"]
    assert body["grades"] == [1]  # 学生视角不含二年级

    # 口径不变：真题仍不进通用考试列表
    assert client.get("/api/exams", headers=headers).json() == []


def test_past_paper_action_states_source_and_detail(
    client: TestClient, db: Session
) -> None:
    """真题库动作闭环数据、来源展示、详情溯源与报告历史。"""
    headers, user = _student(client, db, phone="13211111004")
    doing = _paper(db, title="进行中真题", year=2021)
    fresh = _paper(db, title="未考真题", year=2022, source_name=None)
    db.add(ExamAttempt(user_id=user.id, exam_id=doing.id, seed=1, status="in_progress"))
    db.commit()

    listed = client.get("/api/exams/past-papers", headers=headers)
    assert listed.status_code == 200, listed.text
    items = {item["id"]: item for item in listed.json()}
    assert items[doing.id]["category"] == "in_progress"
    assert items[doing.id]["attempt"]["id"] is not None
    assert items[fresh.id]["category"] == "available"
    # L24：缺来源明确展示为可判定的空值，不伪造来源
    assert items[fresh.id]["source_name"] is None
    assert items[doing.id]["source_name"] == "深圳市教育考试院公开真题"

    none_state = client.get(
        "/api/exams/past-papers", params={"attempt_status": "none"}, headers=headers
    ).json()
    assert [item["id"] for item in none_state] == [fresh.id]

    detail = client.get(f"/api/exams/past-papers/{doing.id}", headers=headers)
    assert detail.status_code == 200, detail.text
    assert detail.json()["source"] == "mock"
    assert detail.json()["attempt_count"] == 1
    assert "questions" not in detail.json() and "answers" not in detail.json()

    history = client.get("/api/exams/attempts", headers=headers)
    assert history.status_code == 200, history.text
    assert [item["exam_id"] for item in history.json()] == [doing.id]
    assert client.get(
        "/api/exams/attempts", params={"exam_id": fresh.id}, headers=headers
    ).json() == []


# ---------------------------------------------------------------- §9.5 收尾


def test_attempt_and_review_queues_are_paginated(
    client: TestClient, db: Session, admin_headers: dict[str, str]
) -> None:
    """§9.5-1：/attempts 与 /reviews 分页，X-Total-Count 为分页前真实总数。"""
    headers, user = _student(client, db, phone="13211111007")
    for index in range(3):
        exam = _exam(db, title=f"历史上卷 {index}")
        db.add(ExamAttempt(user_id=user.id, exam_id=exam.id, seed=index, status="submitted"))
    db.commit()

    paged = client.get(
        "/api/exams/attempts", params={"page": 1, "page_size": 2}, headers=headers
    )
    assert paged.status_code == 200, paged.text
    assert len(paged.json()) == 2
    assert paged.headers["X-Total-Count"] == "3"
    second = client.get(
        "/api/exams/attempts", params={"page": 2, "page_size": 2}, headers=headers
    )
    assert len(second.json()) == 1
    # 兼容：不带 page 仍是数组
    assert isinstance(client.get("/api/exams/attempts", headers=headers).json(), list)

    pending = [_paper(db, status="pending_review", title=f"待复核 {i}") for i in range(3)]
    queue = client.get(
        "/api/exams/reviews", params={"page": 1, "page_size": 2}, headers=admin_headers
    )
    assert queue.status_code == 200, queue.text
    assert len(queue.json()) == 2
    assert queue.headers["X-Total-Count"] == "3"
    assert all(item["status"] == "pending_review" for item in queue.json())
    assert pending is not None


def test_license_note_hidden_from_students(
    client: TestClient, db: Session, admin_headers: dict[str, str]
) -> None:
    """§9.5-3：授权说明属 R-07 台账内部信息，学生端不下发，管理位保留。"""
    headers, _ = _student(client, db, phone="13211111008")
    paper = _paper(
        db, title="带授权说明真题", license_note="内部台账：授权编号 SZ-2020-001"
    )

    student_list = client.get("/api/exams/past-papers", headers=headers).json()
    row = next(item for item in student_list if item["id"] == paper.id)
    assert row["license_note"] is None
    assert row["source_name"] == "深圳市教育考试院公开真题"

    student_detail = client.get(
        f"/api/exams/past-papers/{paper.id}", headers=headers
    ).json()
    assert student_detail["license_note"] is None
    assert student_detail["adapted_from"] is None

    db.expire_all()
    assert db.get(Exam, paper.id).license_note == "内部台账：授权编号 SZ-2020-001"


# ---------------------------------------------------------------- L24 / L26


def test_generate_past_paper_requires_source(
    client: TestClient, db: Session, admin_headers: dict[str, str]
) -> None:
    """组卷发布为真题时缺来源返回 EXAM_SOURCE_REQUIRED（普通卷不受影响）。"""
    db.add(
        ExamBlueprint(
            code="math_g1_unit_d09",
            name="一年级数学单元测",
            subject="math",
            grade=1,
            exam_type="unit",
            total_score=100,
            time_limit_min=60,
            sections=[],
            difficulty_mix={},
            is_active=True,
        )
    )
    db.commit()
    payload = {
        "blueprint_code": "math_g1_unit_d09",
        "chapter_ids": [1],
        "is_past_paper": True,
    }

    denied = client.post("/api/exams/generate", json=payload, headers=admin_headers)
    assert denied.status_code == 422, denied.text
    assert denied.json()["detail"]["code"] == "EXAM_SOURCE_REQUIRED"

    allowed = client.post(
        "/api/exams/generate",
        json={**payload, "source_name": "2020 深圳中考公开真题", "year": 2020},
        headers=admin_headers,
    )
    detail = allowed.json().get("detail")
    code = detail.get("code") if isinstance(detail, dict) else None
    assert code != "EXAM_SOURCE_REQUIRED", allowed.text


def test_exam_center_route_order_and_compat(
    client: TestClient, db: Session
) -> None:
    """静态路由 /past-papers/filters 与 /attempts 不得被 /{exam_id} 吞掉。"""
    headers, _ = _student(client, db, phone="13211111005")
    assert (
        client.get("/api/exams/past-papers/filters", headers=headers).status_code
        == 200
    )
    assert client.get("/api/exams/attempts", headers=headers).status_code == 200
    # 兼容：不带分页参数时响应体仍是数组，且旧参数别名不变
    assert isinstance(client.get("/api/exams", headers=headers).json(), list)
    assert isinstance(
        client.get("/api/exams/past-papers", headers=headers).json(), list
    )


def test_exam_center_filters_are_sql_side_not_truncated(
    client: TestClient, db: Session
) -> None:
    """评审 R2-06：状态/窗口筛选必须在取数前生效，不能被 hard_limit 截断。

    构造 101 张卷（超过不带 page 时的 100 条上限），仅给最早一张挂进行中记录：
    旧实现先 limit(100) 再内存过滤会把这卷丢掉，新实现应能查到。
    """
    headers, user = _student(client, db, phone="13211111006")
    first = _exam(db, title="第 1 张卷")
    for index in range(2, 102):
        _exam(db, title=f"第 {index} 张卷")
    db.add(ExamAttempt(user_id=user.id, exam_id=first.id, seed=1, status="in_progress"))
    db.commit()

    found = client.get(
        "/api/exams", params={"status": "in_progress"}, headers=headers
    )
    assert found.status_code == 200, found.text
    assert [item["id"] for item in found.json()] == [first.id]
    assert found.headers["X-Total-Count"] == "1"

    # 未考状态同样按 SQL 条件过滤，总数与返回体一致（不是截断后的长度）
    available = client.get(
        "/api/exams",
        params={"status": "available", "page": 1, "page_size": 5},
        headers=headers,
    )
    assert len(available.json()) == 5
    assert available.headers["X-Total-Count"] == "100"
