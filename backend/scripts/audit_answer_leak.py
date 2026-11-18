"""全库答案泄漏巡检（2026-11-18 · CR-008）。

与 `app.services.question_quality.check_answer_leak` 共用同一套判定口径，
用于：
  1. 一次性摸清全库还有多少题「答案写在题干里」；
  2. 追溯 `exports/answer_leak_review.csv` 里 99 条「需复核」在门禁下的定级；
  3. 交付给教研的整改清单（只列 block，warn 单列备查）。

用法（在 backend 目录执行）：
    .venv\\Scripts\\python.exe -m scripts.audit_answer_leak
    .venv\\Scripts\\python.exe -m scripts.audit_answer_leak --subject chinese
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.models.content import Chapter, Question  # noqa: E402
from app.services import question_quality as qq  # noqa: E402

EXPORT_ROOT = Path(__file__).resolve().parents[2] / "docs" / "content-templates" / "exports"


def stem_of(question: Question) -> str:
    content = question.content or {}
    return str(content.get("stem") or "")


def main() -> int:
    parser = argparse.ArgumentParser(description="全库答案泄漏巡检")
    parser.add_argument("--subject", help="只查某个学科")
    parser.add_argument("--grade", type=int, help="只查某个年级")
    parser.add_argument("--out", help="输出目录，默认 exports/answer_leak_gate_<date>")
    args = parser.parse_args()

    session = SessionLocal()
    stats: Counter[str] = Counter()
    by_subject: dict[str, Counter[str]] = defaultdict(Counter)
    rows: list[list[str]] = []
    try:
        stmt = (
            select(Question, Chapter.grade)
            .join(Chapter, Question.chapter_id == Chapter.id)
            .where(Question.status == "published", Chapter.is_placeholder == 0)
            .order_by(Chapter.grade, Question.subject, Question.id)
        )
        if args.subject:
            stmt = stmt.where(Question.subject == args.subject)
        if args.grade:
            stmt = stmt.where(Chapter.grade == args.grade)

        for question, grade in session.execute(stmt):
            stem = stem_of(question)
            verdict = qq.check_answer_leak(stem, question.answer, question.q_type)
            if qq.is_arithmetic_stem(stem) and verdict and verdict[0] == qq.BLOCK:
                verdict = (qq.WARN, "算式/条件题：题干须给出操作数，非缺陷")
            level = verdict[0] if verdict else "ok"
            stats[level] += 1
            by_subject[question.subject][level] += 1
            if level == "ok":
                continue
            rows.append([
                level,
                str(question.id),
                question.subject,
                f"g{grade}",
                question.q_type,
                " / ".join(qq.answer_values(question.answer)),
                stem[:160],
                verdict[1],
            ])
    finally:
        session.close()

    out_dir = Path(args.out) if args.out else EXPORT_ROOT / f"answer_leak_gate_{date.today():%Y%m%d}"
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "answer_leak_gate.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["level", "question_id", "subject", "grade", "q_type", "answer", "stem_head", "reason"])
        writer.writerows(rows)

    print(f"扫描完成：ok={stats['ok']}  block={stats['block']}  warn={stats['warn']}")
    print("\n分学科：")
    for subject, counter in sorted(by_subject.items()):
        print(f"  {subject:<10} ok={counter['ok']:<6} block={counter['block']:<5} warn={counter['warn']}")
    blocks = [row for row in rows if row[0] == "block"]
    print(f"\nBLOCK 清单（{len(blocks)} 条，需改题干）：")
    seen: set[str] = set()
    for row in blocks:
        key = row[6][:36]
        if key in seen:
            continue
        seen.add(key)
        print(f"  {row[1]:<7} {row[2]:<9} {row[3]:<4} ans={row[5]:<10} {row[6][:60]}")
    print(f"\n导出：{csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
