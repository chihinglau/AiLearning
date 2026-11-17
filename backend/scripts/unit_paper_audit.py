"""单元级全量体检：对每册**每一个单元**出一次卷，弥补 grade_paper_audit 只取第一单元的盲区。

用法：
    python scripts/unit_paper_audit.py --grades 1 2 3
    python scripts/unit_paper_audit.py --subject chinese
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
from pathlib import Path

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.content import Textbook
from app.models.exam import ExamBlueprint
from app.models.user import User
from app.services.core_kp_list import core_kps_for_chapters
from app.services.exam_paper import generate_paper, resolve_scope_chapters

SUBJECT_NAMES = {"chinese": "语文", "math": "数学", "english": "英语"}
SEMESTER_NAMES = {"first": "上册", "second": "下册"}
OUT_ROOT = Path(__file__).resolve().parents[2] / "docs" / "content-templates" / "exports" / "paper_blueprint_20261116"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--grades", nargs="+", type=int, default=list(range(1, 10)))
    parser.add_argument("--subject", default=None)
    parser.add_argument("--seed", type=int, default=30000)
    args = parser.parse_args()

    rows = []
    with SessionLocal() as db:
        admin = db.scalar(select(User).order_by(User.id).limit(1))
        subjects = [args.subject] if args.subject else ["chinese", "math", "english"]
        for subject in subjects:
            for book in db.scalars(
                select(Textbook).where(
                    Textbook.subject == subject,
                    Textbook.grade.in_(args.grades),
                ).order_by(Textbook.grade, Textbook.semester)
            ):
                code = f"g{book.grade}_{subject}_unit"
                blueprint = db.scalar(select(ExamBlueprint).where(ExamBlueprint.code == code))
                if blueprint is None:
                    rows.append({"grade": book.grade, "subject": subject,
                                 "semester": book.semester, "unit_index": 0,
                                 "result": "NO_BLUEPRINT", "items": 0, "reason": "蓝图未写库"})
                    continue
                unit_index = 1
                while unit_index <= 12:
                    try:
                        chapters = resolve_scope_chapters(
                            db, textbook_id=book.id, scope="unit", unit_index=unit_index
                        )
                    except (IndexError, ValueError):
                        break
                    if not chapters:
                        break
                    # 单元卷同样按「本单元必考核心考点清单」考核：一个单元常有
                    # 19-26 个知识点，而卷面只有 12-15 题，全量覆盖是算术上不可达的。
                    core_ids = core_kps_for_chapters(
                        db, textbook_id=book.id, chapter_ids=chapters
                    )
                    paper = generate_paper(
                        db, user=admin, blueprint=blueprint,
                        chapter_ids=chapters, seed=args.seed,
                        core_kps=core_ids or None,
                    )
                    hit_core = 0
                    if core_ids:
                        covered_ids = {
                            int(item.question.knowledge_point_id)
                            for item in paper.items
                            if item.question.knowledge_point_id
                        }
                        hit_core = len(core_ids & covered_ids)
                    rows.append({
                        "grade": book.grade, "subject": subject,
                        "semester": book.semester, "unit_index": unit_index,
                        "chapters": len(chapters),
                        "result": "REFUSED" if paper.refused else "OK",
                        "items": len(paper.items),
                        "score": round(paper.total_score, 2),
                        "coverage": paper.kp_coverage,
                        "core_total": len(core_ids),
                        "core_hit": hit_core,
                        "core_coverage": (
                            round(hit_core / len(core_ids), 4) if core_ids else 0.0
                        ),
                        "chapter_coverage": paper.chapter_coverage,
                        "reason": paper.refuse_reason or "",
                        "shortage": (
                            f"{paper.shortages[0].section_name}:{paper.shortages[0].q_type}"
                            f" {paper.shortages[0].got}/{paper.shortages[0].wanted}"
                            if paper.shortages else ""
                        ),
                    })
                    unit_index += 1

    stamp = datetime.now().strftime("%Y%m%d")
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    csv_path = OUT_ROOT / f"unit_scope_audit_{stamp}.csv"
    fields = ["grade", "subject", "semester", "unit_index", "chapters", "result",
              "items", "score", "coverage", "core_total", "core_hit", "core_coverage",
              "chapter_coverage", "reason", "shortage"]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    ok = sum(1 for r in rows if r["result"] == "OK")
    refused = [r for r in rows if r["result"] == "REFUSED"]
    print(f"单元卷：共 {len(rows)} 卷，OK {ok}，拒绝 {len(refused)}")
    for r in refused[:30]:
        print(f'  g{r["grade"]} {SUBJECT_NAMES.get(r["subject"], r["subject"])}'
              f'{SEMESTER_NAMES.get(r["semester"], r["semester"])} 第{r["unit_index"]}单元 '
              f'{r["items"]}题 {r["reason"]} {r["shortage"]}')
    print(f"CSV -> {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
