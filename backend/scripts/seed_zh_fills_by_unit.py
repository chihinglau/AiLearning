"""按单元章节铺语文「积累与运用」填空（幂等，source_ref 为键）。

产物：每册每个章节 4 条（2 章=1 单元 → 单元卷可凑 8 条 fill），
题目均为原创、答案确定的语文基础练法（量词/近反义/成语/诗句/标点/关联词）。

用法：
    python scripts/seed_zh_fills_by_unit.py --dry-run
    python scripts/seed_zh_fills_by_unit.py --apply
"""

from __future__ import annotations

import argparse

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.content import Chapter, Question, Textbook
from scripts.zh_fills_by_unit_data import build_items_for_chapter

SOURCE_NAME = "自建题型题库（原创）"
LICENSE_NOTE = "原创自建内容，不含第三方版权素材"
PER_CHAPTER = 4
MAX_STEM_USES = 2  # 全库同一题干最多出现 2 次（680 条需求 → 需要 ≥340 条词条池）

# 按学段挑选可用题型（避免低年级出现文言关联词、高年级只练量词）
BAND_KINDS = {
    (1, 3): {"liangci", "biaodian", "fanyi", "jinyi"},
    (4, 6): {"chengyu", "gushi", "jinyi", "biaodian"},
    (7, 9): {"jinyi", "fanyi", "chengyu", "guanlian"},
}


def kinds_for(grade: int) -> set[str]:
    for (lo, hi), kinds in BAND_KINDS.items():
        if lo <= grade <= hi:
            return kinds
    return {"jinyi", "fanyi"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--grades", nargs="+", type=int, default=list(range(1, 10)))
    args = parser.parse_args()

    planned: list[dict] = []
    with SessionLocal() as db:
        # 全局账本：跨册共享游标与题干占用计数，避免每册从同一位置起取导致跨册复用。
        counters: dict[str, int] = {}
        stem_uses: dict[str, int] = {}
        for book in db.scalars(
            select(Textbook).where(
                Textbook.subject == "chinese",
                Textbook.grade.in_(args.grades),
            ).order_by(Textbook.grade, Textbook.semester)
        ):
            chapters = list(db.scalars(
                select(Chapter).where(Chapter.textbook_id == book.id)
                .order_by(Chapter.order_index, Chapter.id)
            ))
            if not chapters:
                continue
            allowed = kinds_for(book.grade)
            for chapter_index, chapter in enumerate(chapters, start=1):
                got = 0
                # 生成量放大到 per_chapter*3，跳过已被占用满 MAX_STEM_USES 次的题干
                for stem, answer, analysis, kind in build_items_for_chapter(
                    allowed, PER_CHAPTER * 3, counters
                ):
                    if got >= PER_CHAPTER:
                        break
                    if stem_uses.get(stem, 0) >= MAX_STEM_USES:
                        continue
                    stem_uses[stem] = stem_uses.get(stem, 0) + 1
                    got += 1
                    planned.append({
                        "book": book, "chapter": chapter, "index": got,
                        "stem": stem, "answer": answer, "analysis": analysis,
                        "kind": kind,
                    })

        print(f"计划写入 {len(planned)} 题（覆盖 {len({p['book'].id for p in planned})} 册）")
        if not args.apply:
            print("干跑模式：未写库")
            return 0

        created = updated = skipped = 0
        for item in planned:
            ref = f"selfbank:zh_fillu:{item['book'].id}:{item['chapter'].id}:{item['index']}"
            row = db.scalar(select(Question).where(Question.source_ref == ref))
            payload = dict(
                chapter_id=item["chapter"].id,
                subject="chinese",
                q_type="fill",
                content={"stem": item["stem"]},
                options=None,
                answer={"value": item["answer"]},
                analysis=item["analysis"],
                difficulty=2,
                tags=["fill", "积累与运用", "by_unit", item["kind"], f"g{item['book'].grade}"],
                status="published",
                source_type="original",
                source_name=SOURCE_NAME,
                source_ref=ref,
                license_note=LICENSE_NOTE,
            )
            if row is not None:
                # 题干重排：原地替换内容，避免留下旧的高重复题干
                if (row.content or {}).get("stem") == item["stem"]:
                    skipped += 1
                    continue
                for k, v in payload.items():
                    setattr(row, k, v)
                row.knowledge_point_id = None  # 题型可能变化，等待重新挂 KP
                updated += 1
                continue
            db.add(Question(knowledge_point_id=None, **payload))
            created += 1
        db.commit()
        print(f"新建 {created} 题，题干改写 {updated} 题，无变化 {skipped} 题")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
