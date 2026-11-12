# -*- coding: utf-8 -*-
"""只读：重跑队列进度表（34 册隔离名单 vs 已生成内容包 vs 待评审整册）。"""
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
REVIEW = CT / "exports" / "review_20261110"
TASKS = CT / "exports" / "automation_20261108_codebuddy" / "tasks.json"
OUT = REVIEW / "rerun_progress_20261110.json"

pairs = json.loads(TASKS.read_text(encoding="utf-8"))["policy"]["quarantine_books"]["pairs"]
index = json.loads((REVIEW / "rerun_skeleton_index_20261110.json").read_text(encoding="utf-8"))
chapters = {f"{b['subject']}:{b['grade']}": b["chapters"] for b in index["books"]}
rows = []
print("册 | 章数 | 内容包 | 待评审整册 | 状态")
for pair in pairs:
    sub, g = pair.split(":")
    pack = HERE / f"{sub}_g{g}.py"
    book = CT / "daily_rerun" / sub / f"g{g}" / f"{sub}_g{g}_first_20261110_book.json"
    count = len(chapters.get(pair, []))
    status = "done" if pack.is_file() and book.is_file() else ("pack_only" if pack.is_file() else "pending")
    rows.append({"book": pair, "chapters": count, "pack": pack.is_file(),
                 "review_book": book.is_file(), "status": status})
    print(f"{pair:16s} | {count:3d} | {'Y' if pack.is_file() else '-'} | {'Y' if book.is_file() else '-'} | {status}")

OUT.write_text(json.dumps({
    "schema_version": 1, "source": "rerun_packs/_pack_progress.py",
    "totals": {"quarantined": len(pairs),
               "done": sum(1 for r in rows if r["status"] == "done"),
               "pack_only": sum(1 for r in rows if r["status"] == "pack_only"),
               "pending": sum(1 for r in rows if r["status"] == "pending"),
               "chapters_pending": sum(r["chapters"] for r in rows if r["status"] == "pending")},
    "rows": rows,
}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"[留痕] {OUT}")
