"""崩溃与错误监控（R-09）。

- App 上报：清洗/截断 -> 指纹聚合 -> 落 `crash_reports`。
- 后端异常：`ErrorMaskingMiddleware` 捕获后写入同表（`source=backend`）。
- 管理端汇总：按指纹聚合最近 N 天数量与 Top 榜。
"""

import hashlib
import logging
import re
import traceback
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.telemetry import CrashReport

logger = logging.getLogger("ailearning.monitor")

MAX_MESSAGE_CHARS = 500
MAX_STACK_CHARS = 4000
MAX_META_CHARS = 80
TOP_GROUPS = 10

_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_PHONE_RE = re.compile(r"(?<!\d)(1[3-9]\d{9})(?!\d)")
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")

_session_factory: Callable[[], Session] = SessionLocal


def set_session_factory(factory: Callable[[], Session]) -> None:
    """测试钩子：让后端异常落库走测试会话，避免污染开发库。"""
    global _session_factory
    _session_factory = factory


def sanitize(value: Optional[str], limit: int) -> Optional[str]:
    """去控制字符、掩码手机号/邮箱并截断，避免把隐私原样写进监控表。"""
    if value is None:
        return None
    text = _CONTROL_RE.sub("", str(value))
    text = _PHONE_RE.sub("1**********", text)
    text = _EMAIL_RE.sub("***@***", text)
    text = text.strip()
    if not text:
        return None
    return text[:limit]


def build_fingerprint(
    error_type: Optional[str], message: str, stack: Optional[str]
) -> str:
    """同错误类型 + 首行消息 + 栈首行生成稳定指纹，用于同因聚合。"""
    stack_head = (stack or "").splitlines()[0] if stack else ""
    raw = f"{error_type or ''}|{message.splitlines()[0]}|{stack_head}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _normalize_time(value: Optional[datetime]) -> datetime:
    if value is None:
        return datetime.utcnow()
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def record_crash(
    db: Session,
    *,
    message: str,
    stack: Optional[str] = None,
    error_type: Optional[str] = None,
    platform: Optional[str] = None,
    app_version: Optional[str] = None,
    os_version: Optional[str] = None,
    device_model: Optional[str] = None,
    route: Optional[str] = None,
    occurred_at: Optional[datetime] = None,
    source: str = "app",
    user_id: Optional[int] = None,
    request_id: Optional[str] = None,
    ip: Optional[str] = None,
) -> CrashReport:
    safe_message = sanitize(message, MAX_MESSAGE_CHARS) or "unknown error"
    safe_stack = sanitize(stack, MAX_STACK_CHARS)
    safe_type = sanitize(error_type, MAX_META_CHARS)
    report = CrashReport(
        user_id=user_id,
        source=source,
        platform=sanitize(platform, 30) or "unknown",
        app_version=sanitize(app_version, 30),
        os_version=sanitize(os_version, MAX_META_CHARS),
        device_model=sanitize(device_model, MAX_META_CHARS),
        route=sanitize(route, 120),
        error_type=safe_type,
        message=safe_message,
        stack_trace=safe_stack,
        fingerprint=build_fingerprint(safe_type, safe_message, safe_stack),
        request_id=sanitize(request_id, 40),
        ip=sanitize(ip, 64),
        occurred_at=_normalize_time(occurred_at),
        created_at=datetime.utcnow(),
    )
    db.add(report)
    return report


def record_server_error(
    *,
    method: str,
    path: str,
    request_id: str,
    error: Exception,
) -> None:
    """后端未捕获异常落监控表；任何失败都只记日志，绝不影响主响应。"""
    try:
        session = _session_factory()
        try:
            stack = "".join(
                traceback.format_exception(type(error), error, error.__traceback__)
            )
            record_crash(
                session,
                message=f"{method} {path} failed: {error}",
                stack=stack,
                error_type=type(error).__name__,
                platform="backend",
                app_version=None,
                route=path,
                source="backend",
                request_id=request_id,
            )
            session.commit()
        finally:
            session.close()
    except Exception:  # noqa: BLE001 - 监控写入不得影响请求处理
        logger.exception("monitor_write_failed request_id=%s", request_id)


def summarize(db: Session, days: int = 7, limit: int = TOP_GROUPS) -> dict:
    """按指纹聚合最近 N 天记录：总数、同因 Top N、平台/版本分布。"""
    since = datetime.utcnow() - timedelta(days=max(1, days))
    base = db.query(CrashReport).filter(CrashReport.created_at >= since)
    total = base.count()
    grouped = (
        db.query(
            CrashReport.fingerprint,
            func.count(CrashReport.id),
            func.max(CrashReport.created_at),
        )
        .filter(CrashReport.created_at >= since)
        .group_by(CrashReport.fingerprint)
        .order_by(func.count(CrashReport.id).desc())
        .limit(max(1, limit))
        .all()
    )
    top = []
    for fingerprint, count, last_seen in grouped:
        sample = (
            db.query(CrashReport)
            .filter(CrashReport.fingerprint == fingerprint)
            .order_by(CrashReport.created_at.desc())
            .first()
        )
        if sample is None:
            continue
        top.append(
            {
                "fingerprint": fingerprint,
                "error_type": sample.error_type,
                "message": sample.message,
                "platform": sample.platform,
                "count": int(count),
                "last_seen": last_seen,
            }
        )
    by_platform: dict[str, int] = {}
    for platform, count in (
        db.query(CrashReport.platform, func.count(CrashReport.id))
        .filter(CrashReport.created_at >= since)
        .group_by(CrashReport.platform)
        .all()
    ):
        by_platform[platform] = int(count)
    by_version: dict[str, int] = {}
    for version, count in (
        db.query(CrashReport.app_version, func.count(CrashReport.id))
        .filter(CrashReport.created_at >= since)
        .group_by(CrashReport.app_version)
        .all()
    ):
        by_version[version or "unknown"] = int(count)
    return {
        "days": days,
        "total": total,
        "unique_fingerprints": int(
            db.query(func.count(func.distinct(CrashReport.fingerprint)))
            .filter(CrashReport.created_at >= since)
            .scalar()
            or 0
        ),
        "top": top,
        "by_platform": by_platform,
        "by_version": by_version,
    }
