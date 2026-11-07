"""审计日志留存清理 CLI（R-02）。

Usage:
    python -m scripts.prune_audit --dry-run
    python -m scripts.prune_audit --months 24
"""

from __future__ import annotations

import argparse

from app.core.config import settings
from app.db.session import SessionLocal
from app.services.audit import MIN_RETENTION_MONTHS, prune_audit_logs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="清理超过留存期的审计日志")
    parser.add_argument(
        "--months",
        type=int,
        default=settings.audit_retention_months,
        help=f"留存月数（>= {MIN_RETENTION_MONTHS}，默认取配置）",
    )
    parser.add_argument("--dry-run", action="store_true", help="只统计不删除")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with SessionLocal() as db:
        count = prune_audit_logs(db, months=args.months, dry_run=args.dry_run)
    action = "would prune" if args.dry_run else "pruned"
    print(f"[audit] {action} {count} records older than {args.months} months")


if __name__ == "__main__":
    main()
