"""内容举报受理与 24 小时下架（R-07）。"""

from datetime import datetime
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.content import Question
from app.models.content_report import ContentReport
from app.models.user import User
from app.schemas.content_report import ContentReportIn
from app.services.audit import record_audit


def _not_found(code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": code, "message": message},
    )


def create_report(
    db: Session,
    *,
    user: User,
    payload: ContentReportIn,
    ip: Optional[str] = None,
) -> ContentReport:
    """创建举报；题目类举报校验题目存在，避免脏数据。"""
    if payload.target_type == "question":
        if payload.target_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "TARGET_REQUIRED", "message": "请提供题目 ID"},
            )
        if db.get(Question, payload.target_id) is None:
            raise _not_found("CONTENT_NOT_FOUND", "举报的题目不存在")
    report = ContentReport(
        reporter_id=user.id,
        target_type=payload.target_type,
        target_id=payload.target_id,
        reason=payload.reason,
        description=payload.description,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    record_audit(
        db,
        user_id=user.id,
        action="content.report.created",
        message=f"report={report.id}, type={report.target_type}",
        after={
            "report_id": report.id,
            "target_type": report.target_type,
            "target_id": report.target_id,
            "reason": report.reason,
        },
        ip=ip,
    )
    return report


def list_reports(
    db: Session, *, status_filter: Optional[str] = None
) -> list[ContentReport]:
    stmt = select(ContentReport).order_by(ContentReport.id.desc())
    if status_filter:
        stmt = stmt.where(ContentReport.status == status_filter)
    return list(db.scalars(stmt))


def handle_report(
    db: Session,
    *,
    report: ContentReport,
    action: str,
    note: Optional[str],
    user: User,
    ip: Optional[str] = None,
) -> ContentReport:
    """处理举报：下架题目（status=offline）或驳回，并写审计。"""
    if report.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "REPORT_ALREADY_HANDLED", "message": "该举报已处理"},
        )
    before_status: Optional[str] = None
    if action == "takedown" and report.target_type == "question" and report.target_id:
        question = db.get(Question, report.target_id)
        if question is not None:
            before_status = question.status
            question.status = "offline"
    report.status = "takedown" if action == "takedown" else "dismissed"
    report.handled_by = user.id
    report.handled_at = datetime.utcnow()
    report.handle_note = note
    db.commit()
    db.refresh(report)
    record_audit(
        db,
        user_id=user.id,
        action=f"content.report.{report.status}",
        message=f"report={report.id}, target={report.target_type}:{report.target_id}",
        before={"status": before_status} if before_status else None,
        after={
            "report_id": report.id,
            "status": report.status,
            "target_type": report.target_type,
            "target_id": report.target_id,
        },
        ip=ip,
    )
    return report
