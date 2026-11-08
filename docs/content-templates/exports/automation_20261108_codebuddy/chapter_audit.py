"""只读巡检：库内章节 vs 官方章节骨架（占位/旧样章 + order_index 撞号 + 序一致性）。

判定口径（2026-11-08 起换成骨架口径）：
- 基准 = docs/content-templates/baseline/_skeleton_first|_skeleton/chapters_*.json
  （官方章节骨架，由教材目录生成）。不再用大纲允许名集合——大纲允许名里同时收录了
  简写名（认识更大的数 / 圆 / 勾股定理），会把旧样章误判为合法章节。
- 库内章节名不在骨架里 = 占位/旧样章；按 chapters.is_placeholder 分「已标记 / 未标记」。
- 教材真实章节的 order_index 应与骨架一致（骨架序 = 教材目录序）。

用法（只读，不改库）：python chapter_audit.py --out chapter_audit_<date>.json
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parents[1]
SKELETON_DIRS = {
    "first": CT / "baseline" / "_skeleton_first",
    "second": CT / "baseline" / "_skeleton",
}


def db_path() -> Path:
    root = HERE.parents[3]
    cand = root / "backend" / "ailearning_dev.db"
    return cand if cand.is_file() else root / "backend" / "ailearning_device.db"


def connect_ro(path: Path) -> sqlite3.Connection:
    """**只读**连接（mode=ro）：不建 journal/wal、不刷新库文件 mtime。

    巡检脚本必须是真只读——否则「库文件被动过却查不到 db_op 留痕」会被当成事故。
    验收标准：跑完巡检后 `ailearning_dev.db` 的 mtime 不变。
    """
    return sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)


def load_skeletons() -> dict:
    out: dict = {}
    for folder in SKELETON_DIRS.values():
        if not folder.is_dir():
            continue
        for p in sorted(folder.glob("chapters_*_20261107.json")):
            data = json.loads(p.read_text(encoding="utf-8"))
            key = (data["subject"], int(data["grade"]), data["semester"])
            out.setdefault(key, {}).update(
                {c["name"]: int(c["order_index"]) for c in data["chapters"]})
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="章节占位/旧样章巡检（只读，骨架口径）")
    ap.add_argument("--out", help="输出 JSON 路径")
    args = ap.parse_args()

    skeletons = load_skeletons()
    con = connect_ro(db_path())
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    out_textbooks = []
    tot_ch = tot_marked = tot_unmarked = tot_conf = tot_mismatch = tot_no_baseline = 0
    for tb in list(cur.execute("select * from textbooks order by subject, grade, semester")):
        subject, grade, semester = tb["subject"], int(tb["grade"] or 0), tb["semester"]
        skel = skeletons.get((subject, grade, semester), {})
        chs = list(cur.execute(
            "select id,name,order_index,is_placeholder,placeholder_note from chapters "
            "where textbook_id=? order by order_index,id", (tb["id"],)))
        rows, conflicts = [], {}
        for ch in chs:
            is_official = ch["name"] in skel
            nq = cur.execute(
                "select count(*) from questions where chapter_id=?", (ch["id"],)).fetchone()[0]
            rows.append({
                "id": ch["id"], "name": ch["name"], "order_index": ch["order_index"],
                "is_official": is_official, "is_placeholder": int(ch["is_placeholder"] or 0),
                "placeholder_note": ch["placeholder_note"], "questions": nq,
            })
            conflicts.setdefault(ch["order_index"], []).append(ch["name"])
        dup = {k: v for k, v in conflicts.items() if len(v) > 1}
        legacy = [r for r in rows if not r["is_official"]]
        marked = [r for r in legacy if r["is_placeholder"] == 1]
        # 无骨架基准的教材不做「占位」判定（判了也是假阳性），只报出来待补基线
        has_baseline = bool(skel)
        unmarked = [r for r in legacy if r["is_placeholder"] != 1] if has_baseline else []
        no_baseline = [] if has_baseline else legacy
        mismatch = [
            {"id": r["id"], "name": r["name"], "db_order": r["order_index"],
             "skeleton_order": skel[r["name"]]}
            for r in rows if r["is_official"] and r["order_index"] != skel[r["name"]]
        ]
        tot_ch += len(rows)
        tot_marked += len(marked)
        tot_unmarked += len(unmarked)
        tot_conf += sum(len(v) - 1 for v in dup.values())
        tot_mismatch += len(mismatch)
        tot_no_baseline += len(no_baseline)
        out_textbooks.append({
            "textbook_id": tb["id"], "subject": subject, "grade": grade,
            "semester": semester, "official_chapters": len(skel), "chapters": rows,
            "placeholder_marked": marked, "placeholder_unmarked": unmarked,
            "no_baseline": no_baseline,
            "order_index_conflicts": {str(k): v for k, v in dup.items()},
            "order_index_mismatch": mismatch,
        })

    by_subject: dict = {}
    for t in out_textbooks:
        b = by_subject.setdefault(t["subject"], {
            "textbooks": 0, "chapters": 0, "placeholder_marked": 0,
            "placeholder_unmarked": 0, "conflicts": 0, "order_mismatch": 0})
        b["textbooks"] += 1
        b["chapters"] += len(t["chapters"])
        b["placeholder_marked"] += len(t["placeholder_marked"])
        b["placeholder_unmarked"] += len(t["placeholder_unmarked"])
        b["conflicts"] += sum(len(v) - 1 for v in t["order_index_conflicts"].values())
        b["order_mismatch"] += len(t["order_index_mismatch"])

    report = {
        "_meta": {
            "kind": "chapter_placeholder_audit",
            "generated": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "tool": "chapter_audit.py（只读，骨架口径）",
            "database": str(db_path()),
            "purpose": "库内章节 vs 官方章节骨架：占位/旧样章清单 + order_index 撞号 + 序一致性，"
                       "供「教材占位章节清理」立项的回归巡检（本脚本不改库）",
            "criteria": "基准 = baseline/_skeleton_first|_skeleton 的官方章节骨架；"
                        "库内章节名不在骨架里 = 占位/旧样章（is_placeholder=1 为已清理标记）",
            "semantics": "placeholder_unmarked 应为 0；order_index_conflicts 应为 0；"
                         "order_index_mismatch 应为 0",
        },
        "summary": {
            "textbooks": len(out_textbooks), "chapters": tot_ch,
            "placeholder_marked": tot_marked, "placeholder_unmarked": tot_unmarked,
            "order_index_conflicts": tot_conf, "order_index_mismatch": tot_mismatch,
            "no_baseline_chapters": tot_no_baseline,
            "by_subject": by_subject,
        },
        "textbooks": out_textbooks,
    }
    out = Path(args.out).expanduser() if args.out else (
        HERE / f"chapter_audit_{datetime.now():%Y%m%d_%H%M%S}.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"# 章节占位巡检（只读，骨架口径）· {db_path().name}")
    print(f"- 教材 {len(out_textbooks)} 册 / 章节 {tot_ch} 个")
    print(f"- 占位章：已标记 {tot_marked} 个 / 未标记 {tot_unmarked} 个（未标记应为 0）")
    print(f"- order_index 撞号 {tot_conf} 处（应为 0）；官方章序与骨架不一致 {tot_mismatch} 处（应为 0）")
    if tot_no_baseline:
        print(f"- 无骨架基准、跳过判定的章节 {tot_no_baseline} 个（需补 baseline 骨架后才有判定依据）")
    for sub, b in sorted(by_subject.items()):
        if b["placeholder_marked"] or b["conflicts"] or b["order_mismatch"]:
            print(f"  {sub:<10} 教材 {b['textbooks']} 册 / 章节 {b['chapters']} / "
                  f"占位 {b['placeholder_marked']} / 未标记 {b['placeholder_unmarked']} / "
                  f"撞号 {b['conflicts']} / 序不一致 {b['order_mismatch']}")
    print(f"- 报告：{out}")
    return 0 if (tot_unmarked == 0 and tot_conf == 0 and tot_mismatch == 0) else 1


if __name__ == "__main__":
    raise SystemExit(main())
