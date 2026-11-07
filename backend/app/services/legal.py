"""法务同意服务（R-03）：当前版本、同意状态与留痕。"""

from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.legal import PRIVACY_VERSION, TERMS_VERSION
from app.models.legal import ConsentRecord
from app.services.audit import record_audit


def accepted_version(db: Session, user_id: int, doc_type: str) -> Optional[str]:
    """返回该用户已同意的最新版本（无记录返回 None）。"""
    return db.scalar(
        select(ConsentRecord.version)
        .where(ConsentRecord.user_id == user_id, ConsentRecord.doc_type == doc_type)
        .order_by(ConsentRecord.created_at.desc(), ConsentRecord.id.desc())
        .limit(1)
    )


def needs_reconsent(db: Session, user_id: int) -> bool:
    """任一法务文档未同意当前版本时，需要重新征求同意。"""
    return any(
        accepted_version(db, user_id, doc_type) != current_version(doc_type)
        for doc_type in ("privacy", "terms")
    )


def current_version(doc_type: str) -> str:
    return PRIVACY_VERSION if doc_type == "privacy" else TERMS_VERSION


def record_consents(
    db: Session,
    *,
    user_id: int,
    privacy_version: str,
    terms_version: str,
    guardian_confirmed: bool = False,
    ip: Optional[str] = None,
    commit: bool = True,
) -> datetime:
    """幂等写入隐私政策/用户协议同意记录，并写审计 `legal.consent.accepted`。"""
    accepted_at = datetime.utcnow()
    for doc_type, version in (("privacy", privacy_version), ("terms", terms_version)):
        exists = db.scalar(
            select(ConsentRecord.id).where(
                ConsentRecord.user_id == user_id,
                ConsentRecord.doc_type == doc_type,
                ConsentRecord.version == version,
            )
        )
        if exists is None:
            db.add(
                ConsentRecord(
                    user_id=user_id,
                    doc_type=doc_type,
                    version=version,
                    guardian_confirmed=guardian_confirmed,
                    ip=ip,
                    created_at=accepted_at,
                )
            )
    record_audit(
        db,
        user_id=user_id,
        action="legal.consent.accepted",
        message=(
            f"privacy={privacy_version}, terms={terms_version}, "
            f"guardian_confirmed={guardian_confirmed}"
        ),
        ip=ip,
        commit=False,
    )
    if commit:
        db.commit()
    return accepted_at
