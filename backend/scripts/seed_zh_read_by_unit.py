"""按单元补语文阅读理解（answer）：每单元 1 篇原创短文 + 2 道简答题。

用于补齐单元卷「三、阅读理解 answer 需要 2 题」的缺口；短文与题目均原创、可核对。
"""

from __future__ import annotations

import argparse

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.content import Chapter, Question, Textbook
from scripts.zh_read_by_unit_data import read_sets_for

SOURCE_NAME = "自建题型题库（原创）"
LICENSE_NOTE = "原创自建内容，不含第三方版权素材"
PER_UNIT = 1  # 每单元 1 篇短文，配 2 问
MAX_SET_USES = 2  # 全库同一短文最多出现 2 次（130 个单元 → 池需 ≥65 篇，现有 68 篇）


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--grades", nargs="+", type=int, default=list(range(1, 10)))
    args = parser.parse_args()

    planned = []
    set_uses: dict[str, int] = {}
    with SessionLocal() as db:
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
            unit_heads = [c for c in chapters if "单元" in (c.name or "")] or chapters
            sets = read_sets_for(book.grade)
            for i, chapter in enumerate(unit_heads, start=1):
                # 全库账本：优先取「已用次数最少」的短文，保证跨册分布均衡、
                # 不会因兜底而让某一篇被用第 3 次。
                cands = [sets[(book.id + i + offset) % len(sets)] for offset in range(len(sets))]
                chosen = min(cands, key=lambda s: (set_uses.get(s[0], 0),
                                                   cands.index(s)))
                passage, qas = chosen
                set_uses[passage] = set_uses.get(passage, 0) + 1
                for qi, (question, answer, analysis) in enumerate(qas, start=1):
                    planned.append({
                        "book": book, "chapter": chapter, "index": i, "qi": qi,
                        "passage": passage, "question": question,
                        "answer": answer, "analysis": analysis,
                    })

        print(f"计划写入阅读理解 {len(planned)} 题（覆盖 {len({p['book'].id for p in planned})} 册）")
        if not args.apply:
            print("干跑模式：未写库")
            return 0

        created = updated = 0
        for item in planned:
            ref = f"selfbank:zh_readu:{item['book'].id}:{item['chapter'].id}:{item['index']}:{item['qi']}"
            row = db.scalar(select(Question).where(Question.source_ref == ref))
            payload = dict(
                chapter_id=item["chapter"].id,
                subject="chinese",
                q_type="answer",
                content={
                    "stem": f"阅读短文，回答问题。\n{item['passage']}\n\n{item['question']}",
                    "passage": item["passage"],
                    "question": item["question"],
                },
                answer={"value": item["answer"]},
                analysis=item["analysis"],
                difficulty=3 if item["book"].grade <= 6 else 4,
                tags=["answer", "阅读理解", "by_unit", f"g{item['book'].grade}"],
                status="published",
                source_type="original",
                source_name=SOURCE_NAME,
                source_ref=ref,
                license_note=LICENSE_NOTE,
            )
            if row is not None:
                for k, v in payload.items():
                    setattr(row, k, v)
                row.knowledge_point_id = None  # 短文变动，等待重新挂 KP
                updated += 1
                continue
            db.add(Question(knowledge_point_id=None, **payload))
            created += 1
        db.commit()
        print(f"新建 {created} 题，改写 {updated} 题")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
