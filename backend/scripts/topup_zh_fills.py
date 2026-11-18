"""补齐：单章即单元的册，章节 fill 不足 8 条时定向补题（幂等）。

背景：g8 下册的章节名是「第N单元」，一个单元就是一章，故单元卷要求本章内 8 条 fill。
本脚本使用与 seed_zh_fills_by_unit.py 共享的全局游标思路，避免补题与其他册撞题干。
"""

from __future__ import annotations

import argparse

from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.models.content import Chapter, Question, Textbook
from scripts.seed_zh_fills_by_unit import kinds_for, MAX_STEM_USES
from scripts.zh_fills_by_unit_data import build_items_for_chapter

SOURCE_NAME = "自建题型题库（原创）"
LICENSE_NOTE = "原创自建内容，不含第三方版权素材"
MIN_PER_CHAPTER = 8


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    created = updated = 0
    counters: dict[str, int] = {}
    # 先把全库现有题干占用计入账本，避免补的题与已写入的重合超过上限
    stem_uses: dict[str, int] = {}
    with SessionLocal() as db:
        for row in db.execute(select(Question.content, Question.source_ref).where(
            Question.subject == "chinese", Question.q_type == "fill",
            Question.source_ref.like("selfbank:zh_fillu:%"),
        )):
            # 补题行（ref 尾缀 t{n}）本轮会被重排，不预先计入账本，否则会占用名额
            if ":t" in (row[1] or "")[len("selfbank:zh_fillu:"):].rsplit(":", 1)[-1]:
                continue
            stem = (row[0] or {}).get("stem", "")
            stem_uses[stem] = stem_uses.get(stem, 0) + 1

        for book in db.scalars(
            select(Textbook).where(Textbook.subject == "chinese", Textbook.grade <= 9)
            .order_by(Textbook.grade, Textbook.semester)
        ):
            chapters = list(db.scalars(
                select(Chapter).where(Chapter.textbook_id == book.id)
                .order_by(Chapter.order_index, Chapter.id)
            ))
            allowed = kinds_for(book.grade)
            for idx, chapter in enumerate(chapters, start=1):
                # 该章的补题条目（ref 尾缀 t{n}）一律重排，纳入统一账本
                pad_rows = list(db.scalars(
                    select(Question).where(
                        Question.chapter_id == chapter.id,
                        Question.source_ref.like("selfbank:zh_fillu:%:t%"),
                    ).order_by(Question.source_ref)
                ))
                have = db.execute(
                    select(func.count(Question.id)).where(
                        Question.chapter_id == chapter.id,
                        Question.q_type == "fill",
                        Question.status == "published",
                    )
                ).scalar()
                need = max(MIN_PER_CHAPTER - have, len(pad_rows))
                if need <= 0:
                    continue
                pool_items = build_items_for_chapter(
                    allowed, per_chapter=60, counters=counters
                )
                added = 0
                for stem, answer, analysis, kind in pool_items:
                    if added >= need:
                        break
                    if stem_uses.get(stem, 0) >= MAX_STEM_USES:
                        continue
                    stem_uses[stem] = stem_uses.get(stem, 0) + 1
                    ref = f"selfbank:zh_fillu:{book.id}:{chapter.id}:t{added + 1}"
                    row = db.scalar(select(Question).where(Question.source_ref == ref))
                    if row is not None:
                        row.content = {"stem": stem}
                        row.answer = {"value": answer}
                        row.analysis = analysis
                        row.tags = ["fill", "积累与运用", "by_unit", kind, f"g{book.grade}"]
                        row.knowledge_point_id = None
                        updated += 1
                    else:
                        db.add(Question(
                            chapter_id=chapter.id,
                            subject="chinese",
                            q_type="fill",
                            content={"stem": stem},
                            answer={"value": answer},
                            analysis=analysis,
                            difficulty=2,
                            tags=["fill", "积累与运用", "by_unit", kind, f"g{book.grade}"],
                            status="published",
                            source_type="original",
                            source_name=SOURCE_NAME,
                            source_ref=ref,
                            license_note=LICENSE_NOTE,
                        ))
                        created += 1
                    added += 1
        if args.apply:
            db.commit()
        print(f"{'已写入' if args.apply else '干跑'}：补题 {created} 条，改写 {updated} 条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
