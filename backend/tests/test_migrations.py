"""P0-42 迁移/种子回归：

- 空库 upgrade → downgrade → upgrade 全链路可用，head 与模板一致
- 存量库（旧版本 + 真实数据）升级后数据保留、回填字段正确
- seed 连续运行两次幂等（行数不变、无重复账号）
"""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]

CORE_TABLES = {
    "users",
    "textbooks",
    "chapters",
    "knowledge_points",
    "questions",
    "textbook_bindings",
    "practice_sessions",
    "kp_study_states",
    "grade_histories",
    "parent_child_bindings",
    "audit_logs",
    "exam_blueprints",
    "exams",
    "exam_attempts",
    "exam_answers",
    "exam_submissions",
    "student_question_records",
    "mastery_scores",
    "wrong_questions",
}


def _env_for(db_file: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_file.as_posix()}"
    env["PYTHONIOENCODING"] = "utf-8"
    env.pop("AUTO_CREATE_TABLES", None)
    return env


def _run(module_args: list[str], db_file: Path) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, *module_args],
        check=False,
        cwd=BACKEND_DIR,
        env=_env_for(db_file),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 0, (
        f"{' '.join(module_args)} 失败:\nstdout={result.stdout}\nstderr={result.stderr}"
    )
    return result


def _alembic(db_file: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return _run(["-m", "alembic", "-c", "alembic.ini", *args], db_file)


def _head_revision() -> str:
    output = _alembic(Path("alembic_heads_probe.db"), "heads").stdout
    line = next(line for line in output.splitlines() if "(head)" in line)
    return line.split()[0]


def _tables(db_file: Path) -> set[str]:
    with sqlite3.connect(db_file) as conn:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return {row[0] for row in rows}


def _revision(db_file: Path) -> str | None:
    with sqlite3.connect(db_file) as conn:
        rows = conn.execute("SELECT version_num FROM alembic_version").fetchall()
    return rows[0][0] if rows else None


def _count(db_file: Path, table: str) -> int:
    with sqlite3.connect(db_file) as conn:
        return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def test_empty_database_upgrade_downgrade_upgrade(tmp_path: Path) -> None:
    db_file = tmp_path / "empty.db"
    head = _head_revision()

    _alembic(db_file, "upgrade", "head")
    assert _revision(db_file) == head
    assert CORE_TABLES <= _tables(db_file)

    _alembic(db_file, "downgrade", "base")
    assert _revision(db_file) is None
    assert _tables(db_file) - {"alembic_version"} == set()

    _alembic(db_file, "upgrade", "head")
    assert _revision(db_file) == head
    assert CORE_TABLES <= _tables(db_file)


def test_legacy_database_upgrade_keeps_data_and_backfills(tmp_path: Path) -> None:
    db_file = tmp_path / "legacy.db"
    head = _head_revision()

    # 停在 P0-01 之前的版本，模拟上线后的存量库
    _alembic(db_file, "upgrade", "b3f1a2c77d8e")
    with sqlite3.connect(db_file) as conn:
        conn.execute(
            "INSERT INTO users (phone, password_hash, nickname, role, stage, grade,"
            " is_child, daily_limit_minutes, is_active, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "13700000001",
                "hash",
                "存量学生",
                "student",
                None,
                4,
                0,
                120,
                1,
                "2026-01-01 00:00:00",
            ),
        )
        conn.commit()

    _alembic(db_file, "upgrade", "head")
    assert _revision(db_file) == head
    assert "grade_histories" in _tables(db_file)

    with sqlite3.connect(db_file) as conn:
        row = conn.execute(
            "SELECT phone, stage, grade, grade_group, token_version, region, semester"
            " FROM users WHERE phone = ?",
            ("13700000001",),
        ).fetchone()
    assert row is not None, "升级后存量用户丢失"
    phone, stage, grade, grade_group, token_version, region, semester = row
    assert phone == "13700000001"
    assert grade == 4
    assert stage == "primary"
    assert grade_group == "primary_mid"
    assert token_version == 0
    assert region == "shenzhen"
    assert semester == "first"


def test_seed_is_idempotent(tmp_path: Path) -> None:
    db_file = tmp_path / "seed.db"
    _alembic(db_file, "upgrade", "head")

    counts: list[dict[str, int]] = []
    for _ in range(2):
        _run(["-m", "scripts.seed"], db_file)
        counts.append(
            {
                "users": _count(db_file, "users"),
                "textbooks": _count(db_file, "textbooks"),
                "chapters": _count(db_file, "chapters"),
                "knowledge_points": _count(db_file, "knowledge_points"),
                "questions": _count(db_file, "questions"),
                "exam_blueprints": _count(db_file, "exam_blueprints"),
            }
        )

    assert counts[0] and all(counts[0].values()), f"首次 seed 未写入数据: {counts[0]}"
    assert counts[1] == counts[0], f"二次 seed 产生重复数据: {counts}"

    with sqlite3.connect(db_file) as conn:
        duplicates = conn.execute(
            "SELECT phone, COUNT(*) FROM users GROUP BY phone HAVING COUNT(*) > 1"
        ).fetchall()
    assert duplicates == [], f"存在重复账号: {duplicates}"
