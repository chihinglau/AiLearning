"""CR-008 第 1 批答案泄漏修复：只改「改法无歧义」的机制性硬泄漏。

选取标准（不碰需要教研语义判断的题）：
  A. 成语补充题：给出的字里已经含答案字（兴致勃__ 填「勃」），把给出的字缩到
     挖空位之前，答案改为剩余两字——题型不变、答案仍唯一；
  B. 政治两条被复制 12 次的源题干：题干叙述里含答案词（「法治体系」含「法治」、
     「判断题」含「判断」），把答案词一并挖空，考点不变；
其余 block 条目交教研逐条改写（清单见 exports/answer_leak_gate_*/answer_leak_gate.csv）。

用法（在 backend 目录执行）：
    .venv\\Scripts\\python.exe -m scripts.fix_answer_leak_cr008 --dry-run
    .venv\\Scripts\\python.exe -m scripts.fix_answer_leak_cr008 --apply
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.models.content import Question  # noqa: E402

# (匹配子串, 新题干, 新答案, 说明)
FIXES: list[tuple[str, str, str, str]] = [
    (
        "把成语补充完整：兴致勃",
        "把成语补充完整：兴致（　）（　）。",
        "勃勃",
        "成语：给出的字「兴致勃」已含答案「勃」，改为挖两空填「勃勃」",
    ),
    (
        "把成语补充完整：喜气洋",
        "把成语补充完整：喜气（　）（　）。",
        "洋洋",
        "成语：给出的字「喜气洋」已含答案「洋」，改为挖两空填「洋洋」",
    ),
    (
        "把成语补充完整：精益求",
        "把成语补充完整：精益（　）（　）。",
        "求精",
        "成语：给出的字「精益求」已含答案「精」，改为挖两空填「求精」",
    ),
    (
        "把成语补充完整：理所当然",
        "把成语补充完整：理所当（　）。",
        "然",
        "成语：题干「理所当然」已含答案「然」，改为挖第 4 字",
    ),
    (
        "全面依法治国的总目标",
        "国家治理方式要从人治转向（　），并建设社会主义（　）国家。",
        "法治",
        "政治：题干「依法治国」「法治体系」都含答案「法治」，改写为不含答案字的叙述，考点不变",
    ),
    (
        "价值判断题一般要先",
        "这类题目作答时，第一步应先（　）观点的对错，再说明理由。（2字）",
        "判断",
        "政治：题干「判断题」已含答案「判断」，改写叙述避免泄题",
    ),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="CR-008 第 1 批答案泄漏修复")
    parser.add_argument("--apply", action="store_true", help="写库（默认只演练）")
    args = parser.parse_args()

    session = SessionLocal()
    changed = 0
    missing = {fix[0]: 0 for fix in FIXES}
    try:
        for question in session.scalars(select(Question)):
            content = question.content or {}
            stem = str(content.get("stem") or "")
            for needle, new_stem, new_answer, note in FIXES:
                if not needle or needle not in stem:
                    continue
                missing[needle] += 1
                print(f"q{question.id} [{question.subject}/{question.q_type}] {note}")
                print(f"    旧：{stem[:80]}")
                print(f"    新：{new_stem[:80]}  answer={new_answer}")
                if args.apply:
                    content = dict(content)
                    content["stem"] = new_stem
                    question.content = content
                    answer = dict(question.answer or {})
                    answer["value"] = new_answer
                    question.answer = answer
                changed += 1
                break
        if args.apply:
            session.commit()
            print(f"\n已写库：{changed} 条")
        else:
            print(f"\n演练：将修改 {changed} 条（加 --apply 落库）")
        for needle, count in missing.items():
            if count == 0:
                print(f"未匹配：{needle}")
    finally:
        session.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
