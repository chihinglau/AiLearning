"""P2-09 内容审核双人复核测试。"""

import json

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.content import Question
from app.models.content_review import ContentReview
from app.models.exam import Exam
from app.models.user import AuditLog, User


def _add_user(db: Session, phone: str, role: str) -> User:
    user = User(
        phone=phone,
        password_hash=hash_password("pass1234"),
        nickname=role,
        role=role,
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


def _draft_exam(db: Session, question_id: int) -> Exam:
    exam = Exam(
        title="待复核单元测",
        subject="math",
        grade=1,
        year=2026,
        source="manual",
        exam_type="unit",
        total_score=10,
        time_limit_min=30,
        status="draft",
        questions=[{"question_id": question_id, "score": 10}],
    )
    db.add(exam)
    db.commit()
    db.refresh(exam)
    return exam


def _audit(db: Session, action: str) -> AuditLog | None:
    return db.scalar(
        select(AuditLog).where(AuditLog.action == action).order_by(AuditLog.id.desc())
    )


def test_full_review_flow_publishes_exam(
    client: TestClient, db: Session, sample_question: int
) -> None:
    exam = _draft_exam(db, sample_question)
    operator = _add_user(db, "13600000051", "content_operator")
    auditor = _add_user(db, "13600000052", "auditor")
    operator_headers = _login(client, operator.phone)
    auditor_headers = _login(client, auditor.phone)

    submitted = client.post(
        "/api/content/reviews",
        json={"content_type": "exam", "content_id": exam.id, "note": "新单元测待复核"},
        headers=operator_headers,
    )
    assert submitted.status_code == 201, submitted.text
    review_id = submitted.json()["id"]
    assert submitted.json()["status"] == "pending"
    assert submitted.json()["submitted_by"] == operator.id
    assert submitted.json()["title"] == exam.title

    approved = client.post(
        f"/api/content/reviews/{review_id}/decision",
        json={"decision": "approve", "comment": "题目与答案一致"},
        headers=auditor_headers,
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"
    assert approved.json()["reviewed_by"] == auditor.id

    published = client.post(
        f"/api/content/reviews/{review_id}/publish", headers=operator_headers
    )
    assert published.status_code == 200, published.text
    assert published.json()["status"] == "published"
    assert published.json()["published_by"] == operator.id

    db.expire_all()
    exam_row = db.get(Exam, exam.id)
    assert exam_row is not None
    assert exam_row.status == "published"

    for action in ("content.review.submit", "content.review.decide", "content.publish"):
        record = _audit(db, action)
        assert record is not None, action
        assert json.loads(record.detail or "{}")["after"]


def test_operator_cannot_decide(client: TestClient, db: Session, sample_question: int) -> None:
    exam = _draft_exam(db, sample_question)
    operator = _add_user(db, "13600000053", "content_operator")
    headers = _login(client, operator.phone)
    submitted = client.post(
        "/api/content/reviews",
        json={"content_type": "exam", "content_id": exam.id},
        headers=headers,
    )
    assert submitted.status_code == 201, submitted.text
    review_id = submitted.json()["id"]

    denied = client.post(
        f"/api/content/reviews/{review_id}/decision",
        json={"decision": "approve"},
        headers=headers,
    )
    assert denied.status_code == 403, denied.text
    assert denied.json()["detail"]["code"] == "PERMISSION_DENIED"


def test_submitter_cannot_review_own_content(
    client: TestClient, db: Session, sample_question: int
) -> None:
    exam = _draft_exam(db, sample_question)
    super_admin = _add_user(db, "13600000054", "super_admin")
    headers = _login(client, super_admin.phone)
    submitted = client.post(
        "/api/content/reviews",
        json={"content_type": "exam", "content_id": exam.id},
        headers=headers,
    )
    assert submitted.status_code == 201, submitted.text
    review_id = submitted.json()["id"]

    denied = client.post(
        f"/api/content/reviews/{review_id}/decision",
        json={"decision": "approve"},
        headers=headers,
    )
    assert denied.status_code == 403, denied.text
    assert denied.json()["detail"]["code"] == "REVIEW_SELF_DENIED"


def test_rejection_requires_comment_and_blocks_publish(
    client: TestClient, db: Session, sample_question: int
) -> None:
    exam = _draft_exam(db, sample_question)
    operator = _add_user(db, "13600000055", "content_operator")
    auditor = _add_user(db, "13600000056", "auditor")
    operator_headers = _login(client, operator.phone)
    auditor_headers = _login(client, auditor.phone)

    review_id = client.post(
        "/api/content/reviews",
        json={"content_type": "exam", "content_id": exam.id},
        headers=operator_headers,
    ).json()["id"]

    invalid = client.post(
        f"/api/content/reviews/{review_id}/decision",
        json={"decision": "reject"},
        headers=auditor_headers,
    )
    assert invalid.status_code == 422, invalid.text
    assert invalid.json()["detail"]["code"] == "REVIEW_COMMENT_REQUIRED"

    rejected = client.post(
        f"/api/content/reviews/{review_id}/decision",
        json={"decision": "reject", "comment": "题干表述不清"},
        headers=auditor_headers,
    )
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["status"] == "rejected"

    blocked = client.post(
        f"/api/content/reviews/{review_id}/publish", headers=operator_headers
    )
    assert blocked.status_code == 409, blocked.text
    assert blocked.json()["detail"]["code"] == "REVIEW_NOT_APPROVED"


def test_pending_review_is_not_publishable(
    client: TestClient, db: Session, sample_question: int
) -> None:
    exam = _draft_exam(db, sample_question)
    operator = _add_user(db, "13600000057", "content_operator")
    headers = _login(client, operator.phone)
    review_id = client.post(
        "/api/content/reviews",
        json={"content_type": "exam", "content_id": exam.id},
        headers=headers,
    ).json()["id"]

    blocked = client.post(f"/api/content/reviews/{review_id}/publish", headers=headers)
    assert blocked.status_code == 409, blocked.text
    assert blocked.json()["detail"]["code"] == "REVIEW_NOT_APPROVED"


def test_duplicate_pending_review_rejected(
    client: TestClient, db: Session, sample_question: int
) -> None:
    exam = _draft_exam(db, sample_question)
    operator = _add_user(db, "13600000058", "content_operator")
    headers = _login(client, operator.phone)
    first = client.post(
        "/api/content/reviews",
        json={"content_type": "exam", "content_id": exam.id},
        headers=headers,
    )
    assert first.status_code == 201, first.text

    duplicate = client.post(
        "/api/content/reviews",
        json={"content_type": "exam", "content_id": exam.id},
        headers=headers,
    )
    assert duplicate.status_code == 409, duplicate.text
    assert duplicate.json()["detail"]["code"] == "REVIEW_PENDING_EXISTS"


def test_reviewer_cannot_publish(client: TestClient, db: Session, sample_question: int) -> None:
    exam = _draft_exam(db, sample_question)
    operator = _add_user(db, "13600000059", "content_operator")
    auditor = _add_user(db, "13600000060", "auditor")
    operator_headers = _login(client, operator.phone)
    auditor_headers = _login(client, auditor.phone)

    review_id = client.post(
        "/api/content/reviews",
        json={"content_type": "exam", "content_id": exam.id},
        headers=operator_headers,
    ).json()["id"]
    client.post(
        f"/api/content/reviews/{review_id}/decision",
        json={"decision": "approve"},
        headers=auditor_headers,
    )

    denied = client.post(
        f"/api/content/reviews/{review_id}/publish", headers=auditor_headers
    )
    assert denied.status_code == 403, denied.text
    assert denied.json()["detail"]["code"] == "PERMISSION_DENIED"


def test_super_admin_cannot_publish_self_reviewed(
    client: TestClient, db: Session, sample_question: int
) -> None:
    exam = _draft_exam(db, sample_question)
    operator = _add_user(db, "13600000061", "content_operator")
    super_admin = _add_user(db, "13600000062", "super_admin")
    operator_headers = _login(client, operator.phone)
    admin_headers = _login(client, super_admin.phone)

    review_id = client.post(
        "/api/content/reviews",
        json={"content_type": "exam", "content_id": exam.id},
        headers=operator_headers,
    ).json()["id"]
    decided = client.post(
        f"/api/content/reviews/{review_id}/decision",
        json={"decision": "approve"},
        headers=admin_headers,
    )
    assert decided.status_code == 200, decided.text

    denied = client.post(f"/api/content/reviews/{review_id}/publish", headers=admin_headers)
    assert denied.status_code == 403, denied.text
    assert denied.json()["detail"]["code"] == "PUBLISH_SELF_DENIED"


def test_question_review_publish_updates_status(
    client: TestClient, db: Session, sample_question: int
) -> None:
    question = db.get(Question, sample_question)
    assert question is not None
    question.status = "draft"
    db.commit()

    operator = _add_user(db, "13600000063", "content_operator")
    auditor = _add_user(db, "13600000064", "auditor")
    operator_headers = _login(client, operator.phone)
    auditor_headers = _login(client, auditor.phone)

    review_id = client.post(
        "/api/content/reviews",
        json={"content_type": "question", "content_id": sample_question},
        headers=operator_headers,
    ).json()["id"]
    client.post(
        f"/api/content/reviews/{review_id}/decision",
        json={"decision": "approve"},
        headers=auditor_headers,
    )
    published = client.post(f"/api/content/reviews/{review_id}/publish", headers=operator_headers)
    assert published.status_code == 200, published.text

    db.expire_all()
    refreshed = db.get(Question, sample_question)
    assert refreshed is not None
    assert refreshed.status == "published"


def test_review_list_visibility_and_filter(
    client: TestClient, db: Session, sample_question: int
) -> None:
    exam = _draft_exam(db, sample_question)
    operator_one = _add_user(db, "13600000065", "content_operator")
    operator_two = _add_user(db, "13600000066", "content_operator")
    auditor = _add_user(db, "13600000067", "auditor")
    headers_one = _login(client, operator_one.phone)
    headers_two = _login(client, operator_two.phone)
    auditor_headers = _login(client, auditor.phone)

    mine = client.post(
        "/api/content/reviews",
        json={"content_type": "exam", "content_id": exam.id},
        headers=headers_one,
    ).json()["id"]
    pooled = client.get("/api/content/reviews", headers=headers_two)
    assert pooled.status_code == 200, pooled.text
    assert pooled.json() == []

    all_rows = client.get(
        "/api/content/reviews", params={"status": "pending"}, headers=auditor_headers
    )
    assert all_rows.status_code == 200, all_rows.text
    assert [row["id"] for row in all_rows.json()] == [mine]

    assert db.scalar(select(ContentReview).where(ContentReview.id == mine)) is not None


def test_student_cannot_access_reviews(client: TestClient, db: Session) -> None:
    student = _add_user(db, "13600000069", "student")
    headers = _login(client, student.phone)

    denied = client.get("/api/content/reviews", headers=headers)
    assert denied.status_code == 403, denied.text
    assert denied.json()["detail"]["code"] == "PERMISSION_DENIED"
