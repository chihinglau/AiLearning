"""数学按单元入库（幂等）：补齐单元卷所需的 choice4 / fill5 / answer3。

source_ref = selfbank:math_u:{chapter_id}:{qtype}:{idx}
"""

from __future__ import annotations

import argparse

from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.models.content import Chapter, Question, Textbook
from scripts.math_by_unit_data import items_for_chapter

SOURCE_NAME = "自建题型题库（原创）"
LICENSE_NOTE = "原创自建内容，不含第三方版权素材"
NEED = {"choice": 4, "fill": 5, "answer": 3}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--grades", nargs="+", type=int, default=list(range(1, 10)))
    args = parser.parse_args()

    created = 0
    with SessionLocal() as db:
        for book in db.scalars(
            select(Textbook).where(Textbook.subject == "math", Textbook.grade.in_(args.grades))
            .order_by(Textbook.grade, Textbook.semester)
        ):
            chapters = list(db.scalars(
                select(Chapter).where(Chapter.textbook_id == book.id)
                .order_by(Chapter.order_index, Chapter.id)
            ))
            for chapter in chapters:
                key, items = items_for_chapter(chapter.id, chapter.name or "", book.grade)
                counters = {"choice": 0, "fill": 0, "answer": 0}
                for qtype, stem, options, answer, analysis, difficulty in items:
                    have = db.execute(
                        select(func.count(Question.id)).where(
                            Question.chapter_id == chapter.id,
                            Question.subject == "math",
                            Question.q_type == qtype,
                            Question.status == "published",
                        )
                    ).scalar()
                    counters[qtype] += 1
                    if have + counters[qtype] - 1 >= NEED[qtype]:
                        continue
                    ref = f"selfbank:math_u:{chapter.id}:{qtype}:{counters[qtype]}"
                    if db.scalar(select(Question.id).where(Question.source_ref == ref)):
                        continue
                    payload = {"stem": stem}
                    if qtype == "choice":
                        payload = stem if isinstance(stem, str) else stem
                    db.add(Question(
                        chapter_id=chapter.id,
                        subject="math",
                        q_type=qtype,
                        content={"stem": stem} if not isinstance(stem, dict) else stem,
                        options=options or [],
                        answer={"value": answer},
                        analysis=analysis,
                        difficulty=difficulty,
                        tags=[qtype, "by_unit", key, f"g{book.grade}"],
                        status="published",
                        source_type="original",
                        source_name=SOURCE_NAME,
                        source_ref=ref,
                        license_note=LICENSE_NOTE,
                    ))
                    created += 1
        if args.apply:
            db.commit()
        print(f"{'已写入' if args.apply else '干跑'}：数学补题 {created} 条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
