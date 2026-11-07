"""生产库每日备份 CLI（R-02）。

Usage:
    python -m scripts.db_backup
    python -m scripts.db_backup --database-url sqlite:///./ailearning_dev.db \
        --keep-days 30

SQLite 使用在线备份 API（无需停服）；PostgreSQL 调用 pg_dump（需安装客户端）。
"""

from __future__ import annotations

import argparse
import os
import subprocess
from datetime import datetime
from pathlib import Path

from app.core.config import settings
from app.services.backup import BACKUP_PREFIX, backup_sqlite, prune_backups, sqlite_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="备份 AiLearning 数据库")
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL", settings.database_url),
        help="数据库连接串，默认取 DATABASE_URL",
    )
    parser.add_argument(
        "--out-dir",
        default=os.environ.get("BACKUP_DIR", "build/backups"),
        help="备份输出目录（默认 build/backups）",
    )
    parser.add_argument("--keep-days", type=int, default=30, help="本地备份保留天数")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    if args.database_url.startswith("sqlite:///"):
        source = sqlite_path(args.database_url)
        destination = out_dir / f"{BACKUP_PREFIX}{stamp}.db"
        backup_sqlite(source, destination)
    elif args.database_url.startswith("postgresql"):
        destination = out_dir / f"{BACKUP_PREFIX}{stamp}.dump"
        dsn = args.database_url.replace("postgresql+psycopg://", "postgresql://", 1)
        subprocess.run(
            ["pg_dump", "--format=custom", "--file", str(destination), dsn],
            check=True,
        )
    else:
        raise SystemExit(f"不支持的 DATABASE_URL：{args.database_url}")

    removed = prune_backups(out_dir, args.keep_days)
    print(f"[backup] wrote {destination}")
    for path in removed:
        print(f"[backup] pruned {path}")


if __name__ == "__main__":
    main()
