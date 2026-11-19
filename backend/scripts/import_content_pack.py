"""导入「生产内容数据包」（与 scripts.export_content_pack 配套）。

用途（P0-A 内容交付）：把开发库验收过的题库/试卷灌入生产实例。

⚠️ 重要：数据包按**原 id** 导入（试卷 questions 快照里引用的是题目 id，
   重映射代价高且易错）。因此目标库必须是**空内容库**，或显式 --truncate。

推荐的生产首启顺序：
    RUN_SEED=false 启动（只跑 alembic upgrade）
    python -m scripts.import_content_pack --pack build/content_pack/<file>.json.gz --truncate --yes

用法（在 backend 目录）：
    python -m scripts.import_content_pack --pack <file> --dry-run
    python -m scripts.import_content_pack --pack <file> --truncate --yes
    python -m scripts.import_content_pack --pack <file>            # 仅补齐缺失行（按 id 跳过已存在）
"""

from __future__ import annotations

import argparse
import gzip
import json
from collections import Counter
from datetime import date, datetime

from sqlalchemy import delete, func, inspect, select

from app.db.session import SessionLocal
from app.models.content import Chapter, KnowledgePoint, Question, Textbook
from app.models.exam import Exam, ExamBlueprint

# 导入顺序＝导出顺序（满足 FK）
IMPORT_ORDER = ["textbooks", "chapters", "knowledge_points", "questions", "exam_blueprints", "exams"]
MODELS = {
    "textbooks": Textbook,
    "chapters": Chapter,
    "knowledge_points": KnowledgePoint,
    "questions": Question,
    "exam_blueprints": ExamBlueprint,
    "exams": Exam,
}


def _decode(value):
    if isinstance(value, dict) and "__dt__" in value:
        raw = value["__dt__"]
        try:
            return datetime.fromisoformat(raw)
        except ValueError:
            return date.fromisoformat(raw)
    return value


def _load_rows(path) -> tuple[dict[str, list[dict]], dict]:
    rows: dict[str, list[dict]] = {name: [] for name in IMPORT_ORDER}
    manifest: dict = {}
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            table = item.get("table")
            data = item.get("data") or {}
            if table == "__manifest__":
                manifest = data
                continue
            if table in rows:
                rows[table].append(data)
    return rows, manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="导入生产内容数据包")
    parser.add_argument("--pack", required=True, help="export_content_pack 生成的 .json.gz")
    parser.add_argument("--truncate", action="store_true", help="先清空 6 张内容表（危险，需配 --yes）")
    parser.add_argument("--yes", action="store_true", help="确认执行 --truncate")
    parser.add_argument("--dry-run", action="store_true", help="只解析并统计，不落库")
    args = parser.parse_args()

    if args.truncate and not args.yes:
        print("❌ --truncate 需要同时传 --yes 确认")
        return 2

    rows, manifest = _load_rows(args.pack)
    print(f"数据包版本 {manifest.get('version')}，生成于 {manifest.get('created_at')}")
    print("包内行数：" + "，".join(f"{k}={len(v)}" for k, v in rows.items() if v))

    session = SessionLocal()
    stats: Counter = Counter()
    try:
        if args.truncate and not args.dry_run:
            print("\n清空内容表（反向 FK 顺序）...")
            inspector = inspect(session.bind)
            for table in reversed(IMPORT_ORDER):
                if not inspector.has_table(table):
                    print(f"  跳过 {table}（目标库尚无此表，请先 alembic upgrade head）")
                    continue
                session.execute(delete(MODELS[table]))
                session.commit()
                print(f"  清空 {table}")

        for table in IMPORT_ORDER:
            items = rows[table]
            if not items:
                continue
            model = MODELS[table]

            if args.dry_run:
                stats[f"{table}_new"] += len(items)
                continue

            existing = set(session.scalars(select(model.id)).all())
            added = 0
            for data in items:
                if data.get("id") in existing:
                    stats[f"{table}_skip"] += 1
                    continue
                payload = {}
                for key, value in data.items():
                    value = _decode(value)
                    payload[key] = value
                session.add(model(**payload))
                added += 1
            session.commit()
            stats[f"{table}_new"] += added
            print(f"{table:<18} 新增 {added}，跳过已存在 {len(items) - added}")

        # PG 显式插入 id 不会推进 sequence，必须回填，否则后续新建会主键冲突
        dialect = session.bind.dialect.name if session.bind is not None else ""
        if dialect == "postgresql" and not args.dry_run:
            print("\n回填 sequence ...")
            for table in IMPORT_ORDER:
                session.execute(
                    select(func.setval(
                        func.pg_get_serial_sequence(table, "id"),
                        func.coalesce(select(func.max(MODELS[table].id)).scalar_subquery(), 1),
                    ))
                )
            session.commit()
            print("  已回填 6 张表")

        # 导入后自检
        if not args.dry_run:
            published = int(
                session.scalar(select(func.count()).select_from(Question).where(Question.status == "published"))
                or 0
            )
            exams = int(
                session.scalar(select(func.count()).select_from(Exam).where(Exam.status == "published"))
                or 0
            )
            listening = int(
                session.scalar(
                    select(func.count()).select_from(Question).where(Question.q_type == "listening")
                )
                or 0
            )
            print(f"\n自检：published 题 {published} / published 卷 {exams} / 听力题 {listening}")
    finally:
        session.close()

    print("\n汇总：" + "，".join(f"{k}={v}" for k, v in sorted(stats.items())))
    if args.dry_run:
        print("dry-run：未写入数据库")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
