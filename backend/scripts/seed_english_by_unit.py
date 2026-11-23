"""英语按单元入库（幂等）：补齐单元卷所需 listening8 / choice12（单选 8 + 阅读 4）/ fill8。

取题方式为「全局游标 + 索引解码」：同一 index 永远解码出同一组槽值，
游标按册顺序逐章推进，因此不同单元拿到的是池里不同位置的内容，跨单元不再复用同题。
source_ref = selfbank:en_u:{chapter_id}:{bucket}:{idx}
"""

from __future__ import annotations

import argparse

from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.models.content import Chapter, Question, Textbook
from scripts.english_by_unit_data import (
    FILL_FRAMES, GRAM_FRAMES, LICENSE_NOTE, SOURCE_NAME, band_for_grade,
    fill_item_at, grammar_item_at, listening_item, listening_items_for_unit,
    reading_passage,
)

NEED = {"listening": 8, "grammar": 8, "reading": 6, "fill": 10}
# fill 由 8 提到 10：单元卷要 8 题填空，原库常只有 5–7 条，留 2 条余量才能
# 支撑 KP_CAP_PER_SECTION 提到 4 后「每节同知识点上限放宽」而不被题量卡住。
# 每篇短文取 3 问：6 条阅读 = 2 篇短文 × 3 问
READ_Q_PER_PASSAGE = 3


def build_for_chapter(
    grade: int, cursors: dict, counts: dict | None = None, chapter_name: str = ""
) -> dict:
    band = band_for_grade(grade)
    need = dict(NEED)
    if counts:
        for k, v in counts.items():
            need[k] = max(need[k], v)  # 历史多余的 selfbank 行也要改写，避免残留旧内容

    listening = []
    # 7-9 上教版按单元主题词表出题（干扰项同主题、答案位置轮转）；
    # 1-6 或未登记单元沿用旧的全局词池。
    unit_items = listening_items_for_unit(chapter_name, need["listening"])
    if unit_items:
        listening.extend(unit_items)
        cursors["listening"] += need["listening"]
    else:
        for k in range(need["listening"]):
            listening.append(listening_item(cursors["listening"] + k))
        cursors["listening"] += need["listening"]

    # 语法：模板按章轮转（同章 8 题句式各异），模板内槽位用独立全局游标递增，
    # 保证同一模板的 (主语 × 槽位) 组合不被重复取用。
    grammar = []
    gpos = cursors.setdefault("gram_pos", {})
    gbase = cursors.get("gram_tpl", 0)
    for k in range(need["grammar"]):
        t = (gbase + k) % len(GRAM_FRAMES)
        pos = gpos.get(t, 0)
        gpos[t] = pos + 1
        grammar.append(grammar_item_at(t, pos))
    cursors["gram_tpl"] = gbase + need["grammar"]

    # 阅读：按游标取 2 篇短文，每篇取前 3 问，共 6 条
    readings = []
    rkey = ("reading", band)
    base = cursors.get(rkey, 0)
    n_pass = max(1, -(-need["reading"] // READ_Q_PER_PASSAGE))
    for p in range(n_pass):
        passage, qas = reading_passage(base + p, band)
        for j in range(READ_Q_PER_PASSAGE):
            question, opts, answer = qas[j]
            readings.append({
                "content": {"stem": f"Read the passage and answer.\n{passage}\n\n{question}",
                            "passage": passage, "question": question,
                            "section_hint": "reading"},
                "options": opts,
                "answer": answer,
                "analysis": f"答案依据短文内容：{answer}。",
                "difficulty": 3,
            })
    cursors[rkey] = base + n_pass

    fills = []
    fpos = cursors.setdefault("fill_pos", {})
    fbase = cursors.get("fill_tpl", 0)
    for k in range(need["fill"]):
        t = (fbase + k) % len(FILL_FRAMES)
        pos = fpos.get(t, 0)
        fpos[t] = pos + 1
        fills.append(fill_item_at(t, pos))
    cursors["fill_tpl"] = fbase + need["fill"]

    return {"listening": listening, "grammar": grammar, "reading": readings, "fill": fills}


def _norm_bucket(raw: str) -> str:
    """历史 ref 命名归一：单选曾记在 choice 桶，阅读/填空有 xN 后缀变体。"""
    if raw == "choice":
        return "grammar"
    return raw


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--grades", nargs="+", type=int, default=list(range(1, 10)))
    args = parser.parse_args()

    created = updated = 0
    cursors: dict = {"listening": 0, "grammar": 0, "fill": 0}
    with SessionLocal() as db:
        for book in db.scalars(
            select(Textbook).where(Textbook.subject == "english", Textbook.grade.in_(args.grades))
            .order_by(Textbook.grade, Textbook.semester)
        ):
            chapters = list(db.scalars(
                select(Chapter).where(
                    Chapter.textbook_id == book.id,
                    Chapter.is_placeholder == 0,  # 占位章节（教材目录未公布）不铺题
                )
                .order_by(Chapter.order_index, Chapter.id)
            ))
            for chapter in chapters:
                # 该章已有的 selfbank 行按桶归集，用于「原地改写」而不是另起新行
                existing: dict[str, list] = {}
                for row in db.execute(
                    select(Question.id, Question.source_ref).where(
                        Question.source_ref.like(f"selfbank:en_u:{chapter.id}:%")
                    )
                ):
                    parts = row[1].split(":")
                    bucket = _norm_bucket(parts[3])
                    existing.setdefault(bucket, []).append(row[0])
                for b in existing:
                    existing[b].sort()

                counts = {b: len(v) for b, v in existing.items() if b in NEED}
                batches = build_for_chapter(
                    book.grade, cursors, counts, chapter_name=chapter.name
                )
                for bucket, items in batches.items():
                    q_type = {"grammar": "choice", "reading": "choice"}.get(bucket, bucket)
                    rows = existing.get(bucket, [])
                    # 缺口口径与原逻辑一致：只统计已 published 的题，避免超量堆题
                    if bucket == "reading":
                        have = db.execute(select(func.count(Question.id)).where(
                            Question.chapter_id == chapter.id, Question.subject == "english",
                            Question.status == "published", Question.q_type == "choice",
                            Question.content["section_hint"].as_string() == "reading",
                        )).scalar()
                    elif bucket == "grammar":
                        have = db.execute(select(func.count(Question.id)).where(
                            Question.chapter_id == chapter.id, Question.subject == "english",
                            Question.status == "published", Question.q_type == "choice",
                            Question.content["section_hint"].as_string().is_(None),
                        )).scalar()
                    else:
                        have = db.execute(select(func.count(Question.id)).where(
                            Question.chapter_id == chapter.id, Question.subject == "english",
                            Question.q_type == q_type, Question.status == "published",
                        )).scalar()
                    room = max(0, NEED[bucket] - have)
                    for idx, item in enumerate(items, start=1):
                        payload = dict(
                            chapter_id=chapter.id,
                            subject="english",
                            q_type=q_type,
                            content=item["content"],
                            options=item["options"],
                            answer={"value": item["answer"]},
                            analysis=item["analysis"],
                            difficulty=item["difficulty"],
                            tags=[q_type, bucket, "by_unit", f"g{book.grade}"],
                            status="published",
                            source_type="original",
                            source_name=SOURCE_NAME,
                            source_ref=f"selfbank:en_u:{chapter.id}:{bucket}:{idx}",
                            license_note=LICENSE_NOTE,
                        )
                        if idx <= len(rows):
                            row = db.get(Question, rows[idx - 1])
                            for k, v in payload.items():
                                setattr(row, k, v)
                            row.knowledge_point_id = None  # 内容变动，等待重新挂 KP
                            updated += 1
                        elif room > 0:
                            db.add(Question(knowledge_point_id=None, **payload))
                            room -= 1
                            created += 1
        if args.apply:
            db.commit()
        print(f"{'已写入' if args.apply else '干跑'}：英语新建 {created} 条 / 改写 {updated} 条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
