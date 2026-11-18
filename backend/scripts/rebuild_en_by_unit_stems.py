"""重排英语 by_unit 单选与填空的题干内容：保证同一模板槽位不重复。

背景：seed_english_by_unit 每章固定生成 NEED 条、却只写已有行数，游标空转，
导致部分模板落不到题上、题干出现 6 次重复。本脚本按每章**实际行数**生成内容，
模板跨章轮转、模板内槽位用独立游标递增，因此总行数小于池容量即可做到两两不同。
只改内容，不新增、不删除任何行。
"""

from __future__ import annotations

import argparse

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.content import Question
from scripts.english_by_unit_data import FILL_FRAMES, GRAM_FRAMES, fill_item_at, grammar_item_at


def _load(db, bucket: str) -> dict[int, list[int]]:
    rows = db.execute(
        select(Question.id, Question.chapter_id, Question.source_ref).where(
            Question.source_ref.like(f"selfbank:en_u:%:{bucket}:%")
        )
    )
    out: dict[int, list[int]] = {}
    for qid, ch, _ref in rows:
        out.setdefault(ch, []).append(qid)
    for k in out:
        out[k].sort()
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    changed = 0
    with SessionLocal() as db:
        gram = _load(db, "grammar")
        fill = _load(db, "fill")
        g_tpl = 0
        f_tpl = 0
        g_pos: dict[int, int] = {}
        f_pos: dict[int, int] = {}

        for ch in sorted(set(gram) | set(fill)):
            for bucket, rows in (("grammar", gram.get(ch, [])), ("fill", fill.get(ch, []))):
                for qid in rows:
                    if bucket == "grammar":
                        t = g_tpl % len(GRAM_FRAMES)
                        pos = g_pos.get(t, 0)
                        g_pos[t] = pos + 1
                        payload = grammar_item_at(t, pos)
                        g_tpl += 1
                    else:
                        t = f_tpl % len(FILL_FRAMES)
                        pos = f_pos.get(t, 0)
                        f_pos[t] = pos + 1
                        payload = fill_item_at(t, pos)
                        f_tpl += 1
                    row = db.get(Question, qid)
                    row.content = payload["content"]
                    row.options = payload["options"]
                    row.answer = {"value": payload["answer"]}
                    row.analysis = payload["analysis"]
                    row.knowledge_point_id = None
                    changed += 1

        print(("已写入 " if args.apply else "干跑 ") + f"重排 {changed} 条")
        if args.apply:
            db.commit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
