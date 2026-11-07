"""R-02 数据库备份/恢复：SQLite 在线备份，PostgreSQL 走 pg_dump/pg_restore。"""

import shutil
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

SQLITE_PREFIX = "sqlite:///"
BACKUP_PREFIX = "ailearning-backup-"


def sqlite_path(database_url: str) -> Path:
    if not database_url.startswith(SQLITE_PREFIX):
        raise ValueError("not a sqlite database url")
    raw = database_url[len(SQLITE_PREFIX) :]
    if raw == ":memory:" or raw.startswith("file:"):
        raise ValueError("内存数据库不支持备份")
    return Path(raw).expanduser().resolve()


def verify_sqlite(path: Path) -> None:
    try:
        with sqlite3.connect(path) as conn:
            result = conn.execute("PRAGMA quick_check").fetchone()
    except sqlite3.DatabaseError as exc:
        raise RuntimeError(f"SQLite 完整性校验失败：{path}") from exc
    if not result or result[0] != "ok":
        raise RuntimeError(f"SQLite 完整性校验失败：{path}")


def backup_sqlite(source: Path, destination: Path) -> Path:
    """使用 SQLite 在线备份 API 生成一致性快照，并校验完整性。"""
    if not source.exists():
        raise FileNotFoundError(f"数据库不存在：{source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    src = sqlite3.connect(f"file:{source.as_posix()}?mode=ro", uri=True)
    dst = sqlite3.connect(destination)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    verify_sqlite(destination)
    return destination


def restore_sqlite(backup: Path, target: Path, *, overwrite: bool = False) -> Path:
    """把备份恢复到目标库；恢复前校验备份完整性。"""
    if not backup.exists():
        raise FileNotFoundError(f"备份文件不存在：{backup}")
    if target.exists() and not overwrite:
        raise FileExistsError(
            f"目标数据库已存在：{target}（如需覆盖请显式开启 overwrite）"
        )
    verify_sqlite(backup)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(backup, target)
    verify_sqlite(target)
    return target


def prune_backups(
    out_dir: Path,
    keep_days: int,
    *,
    now: datetime | None = None,
) -> list[Path]:
    """删除超过保留天数的本工具生成的备份文件。"""
    cutoff = (now or datetime.now()) - timedelta(days=keep_days)
    removed: list[Path] = []
    if not out_dir.exists():
        return removed
    for path in out_dir.glob(f"{BACKUP_PREFIX}*"):
        if datetime.fromtimestamp(path.stat().st_mtime) < cutoff:
            path.unlink()
            removed.append(path)
    return removed
