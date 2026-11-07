"""R-07 内容举报入口与 24 小时下架流程演练。"""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.content import Question
from app.models.content_report import ContentReport
from app.models.user import AuditLog


def _audit(db: Session, action: str) -> AuditLog | None:
    return db.scalar(
        select(AuditLog).where(AuditLog.action == action).order_by(AuditLog.id.desc())
    )


def _report(
    client: TestClient,
    headers: dict[str, str],
    question_id: int,
    reason: str = "answer_error",
) -> dict[str, object]:
    response = client.post(
        "/api/content/reports",
        headers=headers,
        json={
            "target_type": "question",
            "target_id": question_id,
            "reason": reason,
            "description": "答案与解析不一致，请核对",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_student_can_report_question(
    client: TestClient,
    db: Session,
    student_headers: dict[str, str],
    sample_question: int,
) -> None:
    body = _report(client, student_headers, sample_question)
    assert body["status"] == "pending"
    assert body["target_type"] == "question"
    assert body["target_id"] == sample_question
    report = db.get(ContentReport, body["id"])
    assert report is not None
    log = _audit(db, "content.report.created")
    assert log is not None and f"report={body['id']}" in (log.detail or "")


def test_student_cannot_list_reports(
    client: TestClient,
    db: Session,
    student_headers: dict[str, str],
) -> None:
    db.add(
        ContentReport(
            reporter_id=1,
            target_type="other",
            reason="other",
            description="测试举报",
        )
    )
    db.commit()
    response = client.get("/api/content/reports", headers=student_headers)
    assert response.status_code == 403


def test_admin_takedown_within_24h(
    client: TestClient,
    db: Session,
    student_headers: dict[str, str],
    admin_headers: dict[str, str],
    sample_question: int,
) -> None:
    body = _report(client, student_headers, sample_question)
    pending = client.get(
        "/api/content/reports", params={"status": "pending"}, headers=admin_headers
    )
    assert pending.status_code == 200
    assert any(item["id"] == body["id"] for item in pending.json())

    handled = client.patch(
        f"/api/content/reports/{body['id']}",
        headers=admin_headers,
        json={"action": "takedown", "note": "内容不适宜，已下架"},
    )
    assert handled.status_code == 200, handled.text
    assert handled.json()["status"] == "takedown"

    db.expire_all()
    question = db.get(Question, sample_question)
    assert question is not None and question.status == "offline"
    log = _audit(db, "content.report.takedown")
    assert log is not None

    again = client.patch(
        f"/api/content/reports/{body['id']}",
        headers=admin_headers,
        json={"action": "dismiss"},
    )
    assert again.status_code == 409


def test_report_validation(
    client: TestClient,
    student_headers: dict[str, str],
) -> None:
    missing_id = client.post(
        "/api/content/reports",
        headers=student_headers,
        json={"target_type": "question", "reason": "answer_error"},
    )
    assert missing_id.status_code == 422
    assert missing_id.json()["detail"]["code"] == "TARGET_REQUIRED"

    unknown = client.post(
        "/api/content/reports",
        headers=student_headers,
        json={
            "target_type": "question",
            "target_id": 999999,
            "reason": "answer_error",
        },
    )
    assert unknown.status_code == 404
    assert unknown.json()["detail"]["code"] == "CONTENT_NOT_FOUND"
