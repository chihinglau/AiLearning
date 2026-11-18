"""PG-02 验证：用真实题库对蓝图矩阵做一次组卷干跑（不落库）。

用法：
    .venv\\Scripts\\python.exe scripts\\dry_run_paper_matrix.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.models.exam import ExamBlueprint  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.content import Textbook  # noqa: E402
from app.services.exam_blueprint_matrix import apply_matrix, build_specs  # noqa: E402
from app.services.exam_paper import generate_paper, resolve_scope_chapters  # noqa: E402


def main() -> int:
    with SessionLocal() as db:
        specs = {spec["code"]: spec for spec in build_specs()}
        admin = db.scalar(select(User).order_by(User.id).limit(1))

        ok = refused = 0
        for code, spec in specs.items():
            blueprint = db.scalar(select(ExamBlueprint).where(ExamBlueprint.code == code))
            if blueprint is None:
                # 未写库时用内存对象实例化，仅用于干跑
                blueprint = ExamBlueprint(**{k: v for k, v in spec.items()})
            book = db.scalar(
                select(Textbook).where(
                    Textbook.subject == spec["subject"],
                    Textbook.grade == spec["grade"],
                ).order_by(Textbook.semester)
            )
            if book is None:
                print(f"{code}: 无教材")
                continue
            if spec["exam_type"] == "unit":
                chapters = resolve_scope_chapters(db, textbook_id=book.id, scope="unit", unit_index=1)
            elif spec["exam_type"] == "midterm":
                chapters = resolve_scope_chapters(db, textbook_id=book.id, scope="half_book")
            else:
                chapters = resolve_scope_chapters(db, textbook_id=book.id, scope="book")
            paper = generate_paper(
                db, user=admin, blueprint=blueprint, chapter_ids=chapters, seed=1000 + spec["grade"],
            )
            flag = "REFUSED" if paper.refused else "OK"
            if paper.refused:
                refused += 1
                reason = paper.refuse_reason
                short = paper.shortages[0].reason if paper.shortages else ""
                print(f"{code:26s} {flag:7s} items={len(paper.items):3d}/{paper.requested:3d} "
                      f"cov={paper.kp_coverage:.2f} reason={reason} {short}")
            else:
                ok += 1
                print(f"{code:26s} {flag:7s} items={len(paper.items):3d}/{paper.requested:3d} "
                      f"cov={paper.kp_coverage:.2f} mix={paper.difficulty_mix}")

        print(f"\n小结: 可出卷 {ok} / 拒绝 {refused} / 合计 {len(specs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
