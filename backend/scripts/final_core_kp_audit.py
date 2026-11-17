"""期末卷「必考核心考点清单」的达标核对（方案 C）。

清单的生成规则在 `app/services/core_kp_list.py`，本脚本只做核对与导出：

    基线（不传 core_kps）：按常规选序出期末卷，看清单能命中多少；
    注入（--inject）    ：核心考点在各节获得最优先占位权，并允许跨出难度带
                          （分位切档会让同难度的题有 1/3 落在本节带外）。

用法：
    python scripts/final_core_kp_audit.py
    python scripts/final_core_kp_audit.py --inject --export
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.content import Textbook
from app.models.exam import ExamBlueprint
from app.models.user import User
from app.services.core_kp_list import CORE_LIMIT, build_core_list
from app.services.exam_paper import generate_paper, resolve_scope_chapters

SUBJECTS = ("chinese", "math", "english")
SUBJECT_NAMES = {"chinese": "语文", "math": "数学", "english": "英语"}
SEMESTER_NAMES = {"first": "上册", "second": "下册"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--export", action="store_true")
    parser.add_argument(
        "--inject", action="store_true",
        help="把核心考点清单注入组卷优先级（卷面会优先覆盖核心考点）",
    )
    parser.add_argument("--limit", type=int, default=CORE_LIMIT)
    args = parser.parse_args()

    stamp = datetime.now().strftime("%Y%m%d")
    out_root = (
        Path(__file__).resolve().parents[2] / "docs" / "content-templates" / "exports"
        / "paper_blueprint_20261116"
    )

    all_core: list[dict] = []
    results: list[dict] = []

    with SessionLocal() as db:
        admin = db.scalar(select(User).order_by(User.id).limit(1))
        for grade in range(1, 10):
            for subject in SUBJECTS:
                books = db.scalars(
                    select(Textbook)
                    .where(Textbook.subject == subject, Textbook.grade == grade)
                    .order_by(Textbook.semester)
                ).all()
                for book in books:
                    core = build_core_list(db, book, limit=args.limit)
                    all_core.extend(core)
                    if not core:
                        continue

                    blueprint = db.scalar(
                        select(ExamBlueprint).where(
                            ExamBlueprint.code == f"g{grade}_{subject}_final"
                        )
                    )
                    if blueprint is None:
                        results.append({
                            "grade": grade, "subject": subject,
                            "semester": book.semester, "result": "NO_BLUEPRINT",
                            "core_total": len(core), "core_hit": 0,
                            "core_coverage": 0.0,
                        })
                        continue

                    chapters = resolve_scope_chapters(
                        db, textbook_id=book.id, scope="book"
                    )
                    core_ids = {row["kp_id"] for row in core}
                    paper = generate_paper(
                        db, user=admin, blueprint=blueprint,
                        chapter_ids=chapters, seed=20000 + grade * 10,
                        core_kps=core_ids if args.inject else None,
                    )
                    covered = {
                        int(item.question.knowledge_point_id)
                        for item in paper.items
                        if item.question.knowledge_point_id
                    }
                    hit = len(core_ids & covered)
                    results.append({
                        "grade": grade,
                        "subject": subject,
                        "semester": book.semester,
                        "textbook_id": book.id,
                        "chapters": len(chapters),
                        "result": "REFUSED" if paper.refused else "OK",
                        "items": len(paper.items),
                        "core_total": len(core_ids),
                        "core_hit": hit,
                        "core_coverage": round(hit / len(core_ids), 4) if core_ids else 0.0,
                        "kp_coverage": round(paper.kp_coverage, 4),
                        "crossed_ratio": round(paper.crossed_ratio, 4),
                        "missing_core": ",".join(
                            sorted(
                                row["kp_name"] for row in core
                                if row["kp_id"] not in covered
                            )[:6]
                        ),
                    })
                    print(
                        f"g{grade:1d} {subject:8s} {book.semester:6s} "
                        f"{len(paper.items):3d}题 核心{hit:2d}/{len(core_ids):2d} "
                        f"core={hit / len(core_ids):.2f} "
                        f"(全量cov={paper.kp_coverage:.2f} 跨带={paper.crossed_ratio:.2f})"
                    )

    if results:
        avg = sum(r["core_coverage"] for r in results) / len(results)
        below = [r for r in results if r["core_coverage"] < 0.8]
        print(
            f"\n期末卷 {len(results)} 张｜核心考点覆盖均值 {avg:.3f}｜"
            f"<0.8 {len(below)} 张｜"
            f"<0.6 {sum(1 for r in below if r['core_coverage'] < 0.6)} 张"
        )
        for r in below:
            print(
                f"  待补 g{r['grade']} {SUBJECT_NAMES.get(r['subject'], r['subject'])} "
                f"{SEMESTER_NAMES.get(r['semester'], r['semester'])} "
                f"core={r['core_coverage']:.2f}（{r['core_hit']}/{r['core_total']}）"
                f" | {r.get('missing_core', '')}"
            )

    if args.export:
        out_root.mkdir(parents=True, exist_ok=True)
        core_path = out_root / f"final_core_kp_list_{stamp}.csv"
        core_fields = [
            "grade", "subject", "semester", "textbook_id", "chapter_id",
            "chapter_name", "rank", "kp_id", "kp_name", "q_count",
        ]
        with core_path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=core_fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(all_core)

        result_path = out_root / f"final_core_audit_{stamp}.csv"
        with result_path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(
                handle, fieldnames=list(results[0].keys()), extrasaction="ignore"
            )
            writer.writeheader()
            writer.writerows(results)

        json_path = out_root / f"final_core_audit_{stamp}.json"
        json_path.write_text(
            json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\n核心考点清单 -> {core_path}")
        print(f"核对结果     -> {result_path}")
        print(f"核对结果JSON -> {json_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
