# -*- coding: utf-8 -*-
"""只读：导出 34 册重跑目标册的教材骨架章名，作为内容包编写依据与评审材料。"""
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CT = Path(__file__).resolve().parent.parent
SKEL = CT / "baseline" / "_skeleton_first"
TASKS = CT / "exports" / "automation_20261108_codebuddy" / "tasks.json"
OUT = CT / "exports" / "review_20261110" / "rerun_skeleton_index_20261110.json"

pairs = json.loads(TASKS.read_text(encoding="utf-8"))["policy"]["quarantine_books"]["pairs"]
books = []
for pair in pairs:
    sub, g = pair.split(":")
    path = SKEL / f"chapters_{sub}_g{g}_first_20261107.json"
    if not path.is_file():
        print(f"[缺骨架] {sub}/g{g}: {path.name}")
        books.append({"subject": sub, "grade": int(g), "chapters": [], "skeleton_missing": True})
        continue
    raw = json.loads(path.read_text(encoding="utf-8"))
    chapters = [c["name"] for c in raw.get("chapters", []) if isinstance(c, dict)]
    books.append({"subject": sub, "grade": int(g), "version": raw.get("version"),
                  "chapters": chapters})
    print(f"{sub}/g{g} ({len(chapters)} 章): " + " | ".join(chapters))

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps({"schema_version": 1, "source": "_skeleton_first",
                           "books": books}, ensure_ascii=False, indent=2) + "\n",
               encoding="utf-8")
print(f"[留痕] {OUT}")
print(f"合计 {len(books)} 册，章数合计 {sum(len(b['chapters']) for b in books)}")
