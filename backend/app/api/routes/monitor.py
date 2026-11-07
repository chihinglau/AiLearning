from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import get_optional_user, require_admin
from app.db.session import get_db
from app.models.telemetry import CrashReport
from app.models.user import User
from app.schemas.telemetry import (
    CrashItemOut,
    CrashReportIn,
    CrashReportOut,
    CrashSummaryOut,
)
from app.services import telemetry

router = APIRouter(tags=["监控"])


@router.post("/monitor/crash", status_code=201, response_model=CrashReportOut)
def report_crash(
    payload: CrashReportIn,
    request: Request,
    current: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> CrashReportOut:
    """App 崩溃/错误上报（匿名可用；带有效 Token 时关联账号）。"""
    report = telemetry.record_crash(
        db,
        message=payload.message,
        stack=payload.stack,
        error_type=payload.error_type,
        platform=payload.platform,
        app_version=payload.app_version,
        os_version=payload.os_version,
        device_model=payload.device_model,
        route=payload.route,
        occurred_at=payload.occurred_at,
        user_id=current.id if current else None,
        ip=request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(report)
    return CrashReportOut(
        id=report.id,
        fingerprint=report.fingerprint,
        occurred_at=report.occurred_at,
    )


@router.get("/monitor/crashes/summary", response_model=CrashSummaryOut)
def crash_summary(
    days: int = Query(default=7, ge=1, le=90),
    limit: int = Query(default=10, ge=1, le=50),
    current: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> CrashSummaryOut:
    """按指纹聚合最近 N 天的崩溃/错误（仅超管）。"""
    return CrashSummaryOut(**telemetry.summarize(db, days=days, limit=limit))


@router.get("/monitor/crashes", response_model=list[CrashItemOut])
def list_crashes(
    limit: int = Query(default=20, ge=1, le=100),
    source: Optional[str] = Query(default=None),
    platform: Optional[str] = Query(default=None),
    current: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[CrashItemOut]:
    """最近崩溃明细（仅超管），按时间倒序。"""
    query = db.query(CrashReport)
    if source:
        query = query.filter(CrashReport.source == source)
    if platform:
        query = query.filter(CrashReport.platform == platform)
    rows = query.order_by(CrashReport.created_at.desc()).limit(limit).all()
    return [CrashItemOut.model_validate(row, from_attributes=True) for row in rows]
