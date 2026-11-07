"""生产库恢复/演练 CLI（R-02）。

Usage:
    python -m scripts.db_restore \
        --backup build/backups/ailearning-backup-xxx.db \
        --target-url sqlite:///./restore_drill.db --force

恢复前会校验备份完整性；目标库已存在时必须显式 --force（避免误覆盖生产库）。
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from app.services.backup import restore_sqlite, sqlite_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="从备份恢复 AiLearning 数据库")
    parser.add_argument("--backup", required=True, help="备份文件路径")
    parser.add_argument("--target-url", required=True, help="恢复目标数据库连接串")
    parser.add_argument("--force", action="store_true", help="允许覆盖已存在的目标库")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    backup = Path(args.backup).expanduser().resolve()
    if args.target_url.startswith("sqlite:///"):
        target = sqlite_path(args.target_url)
        restore_sqlite(backup, target, overwrite=args.force)
    elif args.target_url.startswith("postgresql"):
        if not args.force:
            raise SystemExit("覆盖 PostgreSQL 目标库需要显式 --force")
        dsn = args.target_url.replace("postgresql+psycopg://", "postgresql://", 1)
        subprocess.run(
            ["pg_restore", "--clean", "--if-exists", "--dbname", dsn, str(backup)],
            check=True,
        )
    else:
        raise SystemExit(f"不支持的目标连接串：{args.target_url}")
    print(f"[restore] restored {backup} -> {args.target_url}")


if __name__ == "__main__":
    main()
