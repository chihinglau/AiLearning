"""合规审计日志写入（D-03 §8、D-05 合规要求）。"""

import json
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.user import AuditLog

DETAIL_MAX_LENGTH = 1000


def record_audit(
    db: Session,
    *,
    user_id: Optional[int],
    action: str,
    message: Optional[str] = None,
    before: Optional[Any] = None,
    after: Optional[Any] = None,
    ip: Optional[str] = None,
    commit: bool = True,
) -> AuditLog:
    """写入审计日志；detail 统一序列化 JSON（含 before/after 变更快照）。"""
    payload: dict[str, Any] = {}
    if message:
        payload["message"] = message
    if before is not None:
        payload["before"] = before
    if after is not None:
        payload["after"] = after
    detail = (
        json.dumps(payload, ensure_ascii=False, default=str)[:DETAIL_MAX_LENGTH]
        if payload
        else None
    )
    log = AuditLog(user_id=user_id, action=action, detail=detail, ip=ip)
    db.add(log)
    if commit:
        db.commit()
    return log
