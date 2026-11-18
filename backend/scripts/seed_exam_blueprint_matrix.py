"""PG-02：写入试卷蓝图矩阵（g1–g9 × 语文/数学/英语 × 单元/期中/期末 = 81 条）。

用法（backend 目录下）：
    .venv\\Scripts\\python.exe scripts\\seed_exam_blueprint_matrix.py            # 干跑，只打印
    .venv\\Scripts\\python.exe scripts\\seed_exam_blueprint_matrix.py --apply    # 写库（并停用 9 条旧蓝图）

干跑会顺带打印每个年级-学科的题库题型供给，标出哪些卷型当前会被拒绝（缺 composition / listening）。
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import func, select  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.models.content import Chapter, Question, Textbook  # noqa: E402
from app.services.exam_blueprint_matrix import (  # noqa: E402
    LEGACY_CODES,
    apply_matrix,
    build_specs,
)


def _supply(db) -> dict[tuple[int, str], dict[str, int]]:
    rows = db.execute(
        select(Textbook.grade, Question.subject, Question.q_type, func.count(Question.id))
        .join(Chapter, Chapter.textbook_id == Textbook.id)
        .join(Question, Question.chapter_id == Chapter.id)
        .group_by(Textbook.grade, Question.subject, Question.q_type)
    ).all()
    supply: dict[tuple[int, str], dict[str, int]] = {}
    for grade, subject, q_type, count in rows:
        supply.setdefault((grade, subject), {})[q_type] = count
    return supply


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="真正写库")
    args = parser.parse_args()

    specs = build_specs()
    print(f"[matrix] 蓝图 {len(specs)} 条")
    for spec in specs[:4]:
        total = sum(s["count"] * s["score_each"] for s in spec["sections"])
        print(f"  {spec['code']}  {spec['name']}  {total}分 / {spec['time_limit_min']}min")

    with SessionLocal() as db:
        supply = _supply(db)
        blocked: list[str] = []
        for spec in specs:
            need = {
                s["q_type"]: s["count"]
                for s in spec["sections"]
                if s["q_type"] in ("composition", "listening", "experiment")
            }
            have = supply.get((spec["grade"], spec["subject"]), {})
            for q_type in need:
                if have.get(q_type, 0) < need[q_type]:
                    blocked.append(spec["code"])
                    break
        print(f"[matrix] 当前题库可直接组卷 {len(specs) - len(blocked)} 条，"
              f"因缺题型被拒 {len(blocked)} 条")
        if blocked:
            subjects = sorted({code.split("_")[1] for code in blocked})
            print(f"  被拒卷型涉及学科: {subjects}")
            print(f"  示例: {blocked[:6]}")

        if not args.apply:
            print("[matrix] 干跑结束，未写库（加 --apply 生效）")
            return 0

        result = apply_matrix(db)
        print(f"[matrix] 已写库: {result}")
        print(f"[matrix] 旧蓝图已停用: {', '.join(LEGACY_CODES)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
