import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from app.services.backup import backup_sqlite, prune_backups, restore_sqlite


def _create_db(path: Path) -> None:
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT)")
        conn.execute("INSERT INTO items (name) VALUES ('alpha')")
        conn.commit()


def test_sqlite_backup_and_restore_roundtrip(tmp_path: Path) -> None:
    source = tmp_path / "source.db"
    backup = tmp_path / "backups" / "ailearning-backup-test.db"
    restored = tmp_path / "restored.db"
    _create_db(source)

    backup_sqlite(source, backup)
    restore_sqlite(backup, restored)

    with sqlite3.connect(restored) as conn:
        rows = conn.execute("SELECT name FROM items").fetchall()
    assert rows == [("alpha",)]


def test_restore_requires_overwrite_for_existing_target(tmp_path: Path) -> None:
    source = tmp_path / "source.db"
    backup = tmp_path / "backups" / "ailearning-backup-test.db"
    target = tmp_path / "existing.db"
    _create_db(source)
    backup_sqlite(source, backup)
    _create_db(target)

    with pytest.raises(FileExistsError):
        restore_sqlite(backup, target)


def test_restore_rejects_corrupt_backup(tmp_path: Path) -> None:
    backup = tmp_path / "corrupt.db"
    backup.write_text("not a sqlite database")
    with pytest.raises(RuntimeError):
        restore_sqlite(backup, tmp_path / "restored.db")


def test_prune_backups_keeps_recent_files(tmp_path: Path) -> None:
    old = tmp_path / "ailearning-backup-old.db"
    recent = tmp_path / "ailearning-backup-recent.db"
    old.write_text("old")
    recent.write_text("recent")
    timestamp = (datetime.now() - timedelta(days=40)).timestamp()
    import os

    os.utime(old, (timestamp, timestamp))

    removed = prune_backups(tmp_path, keep_days=30)

    assert removed == [old]
    assert recent.exists()
