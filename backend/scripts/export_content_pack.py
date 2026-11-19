"""导出「生产内容数据包」——只含内容，不含任何用户/作答数据。

用途（P0-A 内容交付）：把开发库里已经验收过的题库与试卷，打成可复现的数据包，
在生产实例上通过 scripts.import_content_pack 导入，避免依赖重跑生成脚本
（生成脚本带随机性，且生产上跑满 18746 题不现实）。

导出白名单（按 FK 顺序）：
    textbooks → chapters → knowledge_points → questions → exam_blueprints → exams

刻意不导出：
    users / user_roles / refresh_tokens / consent_records
    exam_attempts / exam_answers / listening_plays / practice_sessions
    wrong_questions / student_question_records / mastery_scores / audit_logs / crash_reports
    assignments / classes / class_members（班级同卷副本属于运行时数据）

用法（在 backend 目录）：
    python -m scripts.export_content_pack                        # 默认 build/content_pack/
    python -m scripts.export_content_pack --out build/pack.json.gz
    python -m scripts.export_content_pack --include-draft        # 连草稿卷一起导
"""

from __future__ import annotations

import argparse
import gzip
import json
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import func, select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.content import Chapter, KnowledgePoint, Question, Textbook
from app.models.exam import Exam, ExamBlueprint

# (表名, 模型, 导出时的过滤说明)
EXPORT_TABLES: list[tuple[str, type, str]] = [
    ("textbooks", Textbook, "全部教材"),
    ("chapters", Chapter, "全部章节"),
    ("knowledge_points", KnowledgePoint, "全部知识点"),
    ("questions", Question, "全部题目（含 draft，保留审核状态）"),
    ("exam_blueprints", ExamBlueprint, "全部蓝图"),
    ("exams", Exam, "已发布且非班级副本"),
]

DEFAULT_OUT = Path("build/content_pack")


def _encode(value):
    if isinstance(value, (datetime, date)):
        return {"__dt__": value.isoformat()}
    return value


def _row_to_dict(obj) -> dict:
    data = {}
    for column in obj.__table__.columns:
        value = getattr(obj, column.name)
        data[column.name] = _encode(value)
    return data


def _count(session, model) -> int:
    return int(session.scalar(select(func.count()).select_from(model)) or 0)


def main() -> int:
    parser = argparse.ArgumentParser(description="导出生产内容数据包")
    parser.add_argument("--out", default=None, help="输出路径（.json.gz）")
    parser.add_argument(
        "--include-draft",
        action="store_true",
        help="连 draft / offline 卷一起导出（默认只导 published）",
    )
    parser.add_argument(
        "--include-class-copies",
        action="store_true",
        help="连班级同卷副本（class_id 非空）一起导出，默认排除",
    )
    args = parser.parse_args()

    out = Path(args.out) if args.out else DEFAULT_OUT / f"ailearning-content-{datetime.now():%Y%m%d}.json.gz"
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.suffix != ".gz":
        out = out.with_suffix(out.suffix + ".gz")

    session = SessionLocal()
    counts: dict[str, int] = {}
    try:
        with gzip.open(out, "wt", encoding="utf-8") as fh:
            for table, model, note in EXPORT_TABLES:
                stmt = select(model).order_by(model.id)
                if table == "exams":
                    if not args.include_draft:
                        stmt = stmt.where(Exam.status == "published")
                    if not args.include_class_copies:
                        stmt = stmt.where(Exam.class_id.is_(None))
                rows = session.scalars(stmt).all()
                counts[table] = len(rows)
                for obj in rows:
                    fh.write(
                        json.dumps(
                            {"table": table, "data": _row_to_dict(obj)},
                            ensure_ascii=False,
                            separators=(",", ":"),
                        )
                        + "\n"
                    )
                print(f"{table:<18} 导出 {len(rows)}")

            # manifest 放在文件末尾，导入时读不到也无妨（--dry-run 只读头）
            manifest = {
                "table": "__manifest__",
                "data": {
                    "version": 1,
                    "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                    "source_database": settings.database_url.split("@")[-1] if "@" in settings.database_url else settings.database_url,
                    "tables": counts,
                    "filters": {
                        "exams_published_only": not args.include_draft,
                        "exclude_class_copies": not args.include_class_copies,
                    },
                    "excluded": [
                        "users", "user_roles", "refresh_tokens", "consent_records",
                        "exam_attempts", "exam_answers", "listening_plays", "practice_sessions",
                        "wrong_questions", "student_question_records", "mastery_scores",
                        "audit_logs", "crash_reports", "assignments", "classes", "class_members",
                    ],
                },
            }
            fh.write(json.dumps(manifest, ensure_ascii=False) + "\n")
    finally:
        session.close()

    size_mb = out.stat().st_size / (1024 * 1024)
    print(f"\n数据包：{out}  ({size_mb:.1f} MB)")
    print("表行数：" + "，".join(f"{k}={v}" for k, v in counts.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
