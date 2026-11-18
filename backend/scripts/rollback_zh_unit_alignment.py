"""回滚语文填空/简答的逐单元对齐：全部锚回该册第一章节。

原因：每册填空语料仅 6 条，按单元轮转后单元卷（2 章范围，需 8 条 fill）
出现「题量不足」拒绝（g2/g3/g4/g5 共 9 卷）。逐单元对齐必须以「先补语料」为前提。

用法：python scripts/rollback_zh_unit_alignment.py --apply
"""

from __future__ import annotations

import argparse

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.content import Chapter, Question, Textbook


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    changed = 0
    with SessionLocal() as db:
        for book in db.scalars(select(Textbook).where(Textbook.subject == "chinese")):
            anchor = db.scalars(
                select(Chapter).where(Chapter.textbook_id == book.id)
                .order_by(Chapter.order_index, Chapter.id)
            ).first()
            if anchor is None:
                continue
            for q in db.scalars(
                select(Question).where(
                    Question.source_ref.like(f"selfbank:zh_fill:{book.id}:%")
                )
            ):
                if q.chapter_id != anchor.id:
                    changed += 1
                    if args.apply:
                        q.chapter_id = anchor.id
            for q in db.scalars(
                select(Question).where(
                    Question.source_ref.like(f"selfbank:zh_answer:{book.id}:%")
                )
            ):
                if q.chapter_id != anchor.id:
                    changed += 1
                    if args.apply:
                        q.chapter_id = anchor.id
        if args.apply:
            db.commit()
    print(f"回滚章节锚定 {changed} 题")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
