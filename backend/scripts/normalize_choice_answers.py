"""选择题答案口径归一：把 answer 统一成选项 key，并打乱选项位置消除「答案全在 A」的偏差。

背景（2026-11-17 体检）：
- 全库 5,908 道 choice 题里 3,418 道（57.8%）正确答案落在 A 位；语文 96%、生物 97%、
  化学 98%、历史 98%、政治 91%、数学 68%。学生蒙 A 即可拿到远高于随机的分数。
- 英语另有约 900 道 choice 的 answer 存的是答案原文（goes / is / Coco …）而不是选项 key，
  判分时无法与作答的 key 对齐。

本脚本做两件事：
1. 口径归一：answer 若是文本，按 options[].text 精确匹配回对应 key；匹配不到记为 unresolved。
2. 位置打乱：按 (question.id, seed) 确定性打乱 options，重排 key 为 A/B/C/D，answer 同步换成新 key。
   确定性保证可重复执行且结果稳定，不会每次跑都变。

用法（backend 目录下）：
    .venv\\Scripts\\python.exe scripts\\normalize_choice_answers.py            # 干跑
    .venv\\Scripts\\python.exe scripts\\normalize_choice_answers.py --apply    # 写库
"""

from __future__ import annotations

import argparse
import os
import random
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.models.content import Question  # noqa: E402

KEYS = ("A", "B", "C", "D", "E", "F")
SEED = 20261117


def _norm_text(value: object) -> str:
    return str("" if value is None else value).strip()


def fix_one(row: Question) -> tuple[bool, str]:
    """返回 (是否需要改写, 处理结论)。就地修改 row.options / row.answer。"""
    options = row.options or []
    if not options:
        return False, "no_options"

    keys = [_norm_text(o.get("key")) for o in options]
    texts = [_norm_text(o.get("text")) for o in options]
    answer = _norm_text((row.answer or {}).get("value"))

    # 1) 口径归一：answer 不是合法 key 时，按文本匹配回 key
    if answer not in keys:
        if answer in texts:
            answer = keys[texts.index(answer)]
        else:
            return False, "unresolved"

    # 2) 位置打乱：确定性 shuffle，保证同一题目每次得到同一顺序
    order = list(range(len(options)))
    random.Random(f"{SEED}-{row.id}").shuffle(order)

    new_options = []
    old_key_to_new: dict[str, str] = {}
    for position, index in enumerate(order):
        new_key = KEYS[position]
        new_options.append({"key": new_key, "text": options[index].get("text")})
        old_key_to_new[keys[index]] = new_key

    new_answer = old_key_to_new[answer]
    changed = new_options != options or new_answer != _norm_text((row.answer or {}).get("value"))
    row.options = new_options
    row.answer = {"value": new_answer}
    return changed, "ok"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="真正写库")
    args = parser.parse_args()

    stats = Counter()
    by_subject: dict[str, Counter] = {}
    samples: list[str] = []

    with SessionLocal() as db:
        rows = db.scalars(select(Question).where(Question.q_type == "choice")).all()
        for row in rows:
            changed, verdict = fix_one(row)
            stats[verdict] += 1
            if changed:
                stats["changed"] += 1
            by_subject.setdefault(row.subject, Counter())[verdict] += 1
            if len(samples) < 5 and verdict == "unresolved":
                samples.append(f"id={row.id} subject={row.subject} answer={(row.answer or {}).get('value')!r} "
                               f"options={[o.get('text') for o in (row.options or [])]}")

        # 打乱后重新统计答案分布，验证偏差是否消除
        after = Counter()
        for row in rows:
            after[_norm_text((row.answer or {}).get("value"))] += 1

        print(f"[choice] 共 {len(rows)} 道")
        for verdict, count in stats.items():
            print(f"  {verdict:12s} {count}")
        print("[choice] 分科：")
        for subject, counter in sorted(by_subject.items()):
            detail = ", ".join(f"{k}={v}" for k, v in counter.items())
            print(f"  {subject:10s} {detail}")
        if samples:
            print("[choice] unresolved 样例：")
            for line in samples:
                print("  ", line)
        top = after.most_common(5)
        print(f"[choice] 打乱后答案分布 top5: {top}")

        if not args.apply:
            db.rollback()
            print("[choice] 干跑结束，未写库（加 --apply 生效）")
            return 0

        db.commit()
        print("[choice] 已提交")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
