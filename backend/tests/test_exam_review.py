"""EX-09 / CR-005：真题审核发布流验收（L27/L30，D-09 §5.7 P2）。

覆盖：真题生成即草稿、普通卷仍生成即发布；草稿/待复核/下线不可见；
提交复核、审核队列、通过发布、退回、下线与非法流转；来源必填卡口与权限。
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.content import Chapter, KnowledgePoint, Question, Textbook
from app.models.exam import Exam, ExamBlueprint
from app.models.user import AuditLog


def _paper(
    db: Session,
    *,
    status: str = "draft",
    source_name: str | None = "深圳市教育考试院公开真题",
    **overrides,
) -> Exam:
    data = {
        "title": "历年真题卷",
        "subject": "math",
        "grade": 1,
        "source": "past_paper",
        "exam_type": "mock",
        "total_score": 100,
        "time_limit_min": 60,
        "questions": [],
        "is_past_paper": True,
        "year": 2020,
        "region": "深圳",
        "status": status,
        "source_name": source_name,
    }
    data.update(overrides)
    row = Exam(**data)
    db.add(row)
    db.flush()
    db.commit()
    return row


def _student(client: TestClient, phone: str = "13211112001") -> dict[str, str]:
    registered = client.post(
        "/api/auth/register",
        json={"phone": phone, "password": "pass1234", "grade": 1},
    )
    assert registered.status_code == 201, registered.text
    login = client.post(
        "/api/auth/login", data={"username": phone, "password": "pass1234"}
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_draft_paper_hidden_until_approved(
    client: TestClient, db: Session, admin_headers: dict[str, str]
) -> None:
    """L27：草稿真题不可见；提交复核 → 队列 → 通过发布后才进入真题库。"""
    student = _student(client)
    paper = _paper(db, status="draft")
    assert client.get("/api/exams/past-papers", headers=student).json() == []
    assert (
        client.get(
            f"/api/exams/past-papers/{paper.id}", headers=student
        ).status_code
        == 404
    )
    assert client.get("/api/exams", headers=student).json() == []

    submitted = client.post(
        f"/api/exams/{paper.id}/submit-review", json={}, headers=admin_headers
    )
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["status"] == "pending_review"

    # /reviews 是静态路径，不能被 /{exam_id} 吞掉；学生无审核权限
    queue = client.get("/api/exams/reviews", headers=admin_headers)
    assert queue.status_code == 200, queue.text
    assert [item["id"] for item in queue.json()] == [paper.id]
    assert client.get("/api/exams/reviews", headers=student).status_code == 403
    assert client.get("/api/exams/past-papers", headers=student).json() == []

    # 评审 R2-03 双人复核：approve 要求复核人与提交人不同，这里模拟“另一位账号提交”
    db.add(
        AuditLog(
            user_id=999001,
            action="exam.review.submit",
            detail=f'{{"message": "exam={paper.id}, from=draft, to=pending_review"}}',
        )
    )
    db.commit()

    approved = client.post(
        f"/api/exams/{paper.id}/review",
        json={"decision": "approve", "note": "来源凭证已核对"},
        headers=admin_headers,
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "published"
    assert approved.json()["reviewed_by"] is not None
    assert approved.json()["published_by"] is not None

    listed = client.get("/api/exams/past-papers", headers=student)
    assert [item["id"] for item in listed.json()] == [paper.id]
    detail = client.get(f"/api/exams/past-papers/{paper.id}", headers=student)
    assert detail.status_code == 200, detail.text
    assert detail.json()["reviewed_by"] is not None
    assert detail.json()["published_at"] is not None


def test_reject_offline_and_invalid_transitions(
    client: TestClient, db: Session, admin_headers: dict[str, str]
) -> None:
    """L27：退回回草稿、下线后不可见、非法流转 409，不绕过状态机。"""
    paper = _paper(db, status="pending_review", title="待复核卷")
    rejected = client.post(
        f"/api/exams/{paper.id}/review",
        json={"decision": "reject", "note": "授权凭证待补"},
        headers=admin_headers,
    )
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["status"] == "draft"

    invalid = client.post(
        f"/api/exams/{paper.id}/review",
        json={"decision": "approve"},
        headers=admin_headers,
    )
    assert invalid.status_code == 409, invalid.text
    assert invalid.json()["detail"]["code"] == "EXAM_INVALID_STATE"

    published = _paper(db, status="published", title="已发布真题")
    off = client.post(
        f"/api/exams/{published.id}/review",
        json={"decision": "offline"},
        headers=admin_headers,
    )
    assert off.status_code == 200, off.text
    assert off.json()["status"] == "offline"
    student = _student(client, phone="13211112002")
    assert client.get("/api/exams/past-papers", headers=student).json() == []


def test_review_requires_source_and_past_paper_only(
    client: TestClient, db: Session, admin_headers: dict[str, str]
) -> None:
    """L27/L29：缺来源不得提交或发布；普通卷不进入审核流；状态参数需合法。"""
    no_source = _paper(db, status="draft", source_name=None, title="缺来源草稿")
    denied = client.post(
        f"/api/exams/{no_source.id}/submit-review", json={}, headers=admin_headers
    )
    assert denied.status_code == 422, denied.text
    assert denied.json()["detail"]["code"] == "EXAM_SOURCE_REQUIRED"

    pending = _paper(
        db, status="pending_review", source_name=None, title="缺来源待复核"
    )
    approve = client.post(
        f"/api/exams/{pending.id}/review",
        json={"decision": "approve"},
        headers=admin_headers,
    )
    assert approve.status_code == 422, approve.text
    assert approve.json()["detail"]["code"] == "EXAM_SOURCE_REQUIRED"

    normal = _paper(
        db, status="draft", is_past_paper=False, title="普通卷（不审核）"
    )
    not_found = client.post(
        f"/api/exams/{normal.id}/submit-review", json={}, headers=admin_headers
    )
    assert not_found.status_code == 404, not_found.text

    bad = client.get(
        "/api/exams/reviews", params={"review_status": "bogus"}, headers=admin_headers
    )
    assert bad.status_code == 422, bad.text


def test_generate_past_paper_is_draft_normal_is_published(
    client: TestClient, db: Session, admin_headers: dict[str, str]
) -> None:
    """L20/L27：真题生成即草稿，普通卷生成即发布；L20 已验收行为不变。"""
    book = Textbook(subject="math", grade=1, version="人教版", semester="first")
    db.add(book)
    db.flush()
    chapter = Chapter(textbook_id=book.id, grade=1, name="第一单元", order_index=1)
    kp = KnowledgePoint(subject="math", name="加法", grade=1, node_type="point")
    db.add_all([chapter, kp])
    db.flush()
    for index in range(6):
        db.add(
            Question(
                chapter_id=chapter.id,
                knowledge_point_id=kp.id,
                subject="math",
                q_type="choice",
                difficulty=1 + index % 2,
                content={"stem": f"题 {index}"},
                answer={"value": "A"},
            )
        )
    db.add(
        ExamBlueprint(
            code="review_unit",
            name="一年级数学单元测",
            subject="math",
            grade=1,
            exam_type="unit",
            total_score=100,
            time_limit_min=45,
            sections=[
                {
                    "name": "一、选择",
                    "q_type": "choice",
                    "count": 5,
                    "score_each": 20,
                    "difficulty": [1, 2],
                }
            ],
            kp_coverage_min=0.8,
            difficulty_mix={"easy": 1},
            is_active=True,
        )
    )
    db.commit()

    normal = client.post(
        "/api/exams/generate",
        headers=admin_headers,
        json={"blueprint_code": "review_unit", "chapter_ids": [chapter.id], "seed": 9},
    )
    assert normal.status_code == 200, normal.text
    assert normal.json()["status"] == "published"

    past = client.post(
        "/api/exams/generate",
        headers=admin_headers,
        json={
            "blueprint_code": "review_unit",
            "chapter_ids": [chapter.id],
            "seed": 10,
            "is_past_paper": True,
            "source_name": "深圳市教育考试院公开真题",
            "year": 2020,
        },
    )
    assert past.status_code == 200, past.text
    assert past.json()["status"] == "draft"
    db.expire_all()
    row = db.get(Exam, past.json()["exam_id"])
    assert row is not None
    assert row.status == "draft" and row.is_past_paper is True

    student = _student(client, phone="13211112003")
    assert client.get("/api/exams", headers=student).json() != []
    assert client.get("/api/exams/past-papers", headers=student).json() == []


def test_self_approve_blocked_and_reject_requires_note(
    client: TestClient, db: Session, admin_headers: dict[str, str]
) -> None:
    """评审 R2-03/R2-04：同一账号不能自审自发；退回必须给意见。"""
    paper = _paper(db, status="draft", title="自审自发卷")
    submitted = client.post(
        f"/api/exams/{paper.id}/submit-review", json={}, headers=admin_headers
    )
    assert submitted.status_code == 200, submitted.text
    self_approve = client.post(
        f"/api/exams/{paper.id}/review",
        json={"decision": "approve", "note": "我自己批"},
        headers=admin_headers,
    )
    assert self_approve.status_code == 409, self_approve.text
    assert self_approve.json()["detail"]["code"] == "EXAM_REVIEW_SELF"

    no_note = _paper(db, status="pending_review", title="退回无意见卷")
    rejected = client.post(
        f"/api/exams/{no_note.id}/review",
        json={"decision": "reject"},
        headers=admin_headers,
    )
    assert rejected.status_code == 422, rejected.text
    assert rejected.json()["detail"]["code"] == "EXAM_REVIEW_NOTE_REQUIRED"


def test_class_copy_not_reviewable(
    client: TestClient, db: Session, admin_headers: dict[str, str]
) -> None:
    """§9.5-2：班级派发副本（class_id 非空）不进入审核队列，须操作模板卷。"""
    copy = _paper(db, status="draft", title="班级副本卷", class_id=1)
    denied = client.post(
        f"/api/exams/{copy.id}/submit-review", json={}, headers=admin_headers
    )
    assert denied.status_code == 409, denied.text
    assert denied.json()["detail"]["code"] == "EXAM_CLASS_COPY_NOT_REVIEWABLE"


def test_restore_offline_back_to_draft(
    client: TestClient, db: Session, admin_headers: dict[str, str]
) -> None:
    """评审 R2-05：误下线可 restore 回草稿，且不直接复原为 published。"""
    paper = _paper(db, status="offline", title="误下线卷")
    restored = client.post(
        f"/api/exams/{paper.id}/review",
        json={"decision": "restore", "note": "误操作下线，回草稿重走复核"},
        headers=admin_headers,
    )
    assert restored.status_code == 200, restored.text
    assert restored.json()["status"] == "draft"
    db.expire_all()
    row = db.get(Exam, paper.id)
    assert row is not None and row.status == "draft" and row.published_by is None
