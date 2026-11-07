from datetime import datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user import AuditLog
from app.services.audit import MIN_RETENTION_MONTHS, prune_audit_logs


def test_prune_audit_logs_removes_old_records(db: Session) -> None:
    now = datetime(2026, 11, 7, 12, 0, 0)
    db.add_all(
        [
            AuditLog(action="old.event", created_at=now - timedelta(days=800)),
            AuditLog(action="recent.event", created_at=now - timedelta(days=30)),
        ]
    )
    db.commit()

    deleted = prune_audit_logs(db, months=24, now=now)

    assert deleted == 1
    remaining = db.scalar(select(func.count()).select_from(AuditLog))
    assert remaining == 1


def test_prune_audit_logs_dry_run_keeps_records(db: Session) -> None:
    now = datetime(2026, 11, 7, 12, 0, 0)
    db.add(AuditLog(action="old.event", created_at=now - timedelta(days=800)))
    db.commit()

    assert prune_audit_logs(db, months=24, now=now, dry_run=True) == 1
    assert db.scalar(select(func.count()).select_from(AuditLog)) == 1


def test_prune_audit_logs_rejects_short_retention(db: Session) -> None:
    with pytest.raises(ValueError):
        prune_audit_logs(db, months=MIN_RETENTION_MONTHS - 1)
