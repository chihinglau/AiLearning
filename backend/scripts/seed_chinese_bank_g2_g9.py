"""g2–g9 语文习作入库脚本（幂等，source_ref 为键）。

用法：
    python scripts/seed_chinese_bank_g2_g9.py --grades 2 3 --dry-run
    python scripts/seed_chinese_bank_g2_g9.py --grades 2 3 --apply
"""

from __future__ import annotations

import argparse

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.content import Chapter, Question, Textbook
from scripts.zh_compositions_g2_g9 import ZH_COMPOSITIONS
from scripts.zh_unit_fills_g2_g9 import ZH_UNIT_ANSWERS, ZH_UNIT_FILLS

SOURCE_NAME = "自建题型题库（原创）"
LICENSE_NOTE = "原创自建内容，不含第三方版权素材"


def first_chapter(db, book_id: int) -> Chapter | None:
    return db.scalars(
        select(Chapter).where(Chapter.textbook_id == book_id)
        .order_by(Chapter.order_index, Chapter.id)
    ).first()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--grades", nargs="+", type=int, required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    plan: list[Question] = []
    with SessionLocal() as db:
        for book in db.scalars(
            select(Textbook).where(
                Textbook.subject == "chinese", Textbook.grade.in_(args.grades)
            )
        ):
            comps = ZH_COMPOSITIONS.get(book.id) or []
            fills = ZH_UNIT_FILLS.get(book.id) or []
            answers = ZH_UNIT_ANSWERS.get(book.id) or []
            if not (comps or fills or answers):
                continue
            anchor = first_chapter(db, book.id)
            if anchor is None:
                continue
            for index, (stem, value, analysis) in enumerate(fills, start=1):
                plan.append(Question(
                    chapter_id=anchor.id, knowledge_point_id=None,
                    subject="chinese", q_type="fill",
                    content={"stem": stem},
                    options=None, answer={"value": value},
                    analysis=analysis, difficulty=2,
                    tags=["fill", "积累与运用", f"g{book.grade}"],
                    status="published", source_type="original", source_name=SOURCE_NAME,
                    source_ref=f"selfbank:zh_fill:{book.id}:{index}",
                    license_note=LICENSE_NOTE,
                ))
            for index, (stem, value, analysis) in enumerate(answers, start=1):
                plan.append(Question(
                    chapter_id=anchor.id, knowledge_point_id=None,
                    subject="chinese", q_type="answer",
                    content={"stem": stem},
                    options=None, answer={"value": value},
                    analysis=analysis, difficulty=3,
                    tags=["answer", "阅读理解", f"g{book.grade}"],
                    status="published", source_type="original", source_name=SOURCE_NAME,
                    source_ref=f"selfbank:zh_answer:{book.id}:{index}",
                    license_note=LICENSE_NOTE,
                ))
            for index, (title, prompt, min_words, points, sample) in enumerate(comps, start=1):
                plan.append(Question(
                    chapter_id=anchor.id, knowledge_point_id=None,
                    subject="chinese", q_type="composition",
                    content={"stem": prompt, "title": title, "min_words": min_words,
                             "scoring_points": points, "sample": sample},
                    options=None,
                    answer={"value": sample, "scoring_points": points, "open_ended": True},
                    analysis="参考范文：" + sample,
                    difficulty=4,
                    tags=["composition", "selfbank", title],
                    status="published", source_type="original", source_name=SOURCE_NAME,
                    source_ref=f"selfbank:zh_comp:{book.id}:{index}",
                    license_note=LICENSE_NOTE,
                ))

    print(f"计划写入 {len(plan)} 题（习作/填空/简答）")
    if not args.apply:
        print("干跑模式：未写库")
        return 0

    created = skipped = 0
    with SessionLocal() as db:
        for question in plan:
            if db.scalar(select(Question.id).where(Question.source_ref == question.source_ref)):
                skipped += 1
                continue
            db.add(question)
            created += 1
        db.commit()
    print(f"入库完成：created={created} skipped={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
