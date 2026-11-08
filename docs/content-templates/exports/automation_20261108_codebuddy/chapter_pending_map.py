"""生成「需教材判断的旧主题归属清单」（占位章节清理立项 · 阶段 2 产出，只读）。

用法：
    python chapter_pending_map.py [--out chapter_pending_map_20261108.json]

清单内容 = 判定表 keep_marked 的 24 个 R-C 占位章：
每条给出章节 id / 当前状态 / 挂着的题目（含知识点父链与题干摘要）/
该册教材真实章节全表（供业务挑选）/ 原因 / 建议 / 风险。
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parents[1]
ROOT = CT.parents[1]
BACKEND = ROOT / "backend"
PLAN_PATH = HERE / "chapter_cleanup_plan_20261108.json"
SKELETON_DIRS = {
    "first": CT / "baseline" / "_skeleton_first",
    "second": CT / "baseline" / "_skeleton",
}

SUBJECT_CN = {
    "chinese": "语文", "math": "数学", "english": "英语", "physics": "物理",
    "chemistry": "化学", "biology": "生物", "geography": "地理",
    "history": "历史", "politics": "道德与法治",
}
RISK = {
    "语文": "旧专题与教材单元主题不对应；直接并入某单元会让该单元出现「主题外」题目。建议先保留为占位章，等教研出题替换后再挂载。",
    "英语": "旧单元与牛津深圳版单元主题不完全对应；并入后需教研重写题干，否则会与该单元考点重复或冲突。",
    "数学": "旧单元在新版教材目录里没有对应单元（多为下册或旧人教版口径）；强行并入会造成「教材里没有的知识点被算进该单元」。",
    "地理": "旧版第一章与新版第一章主题范围不同；并入前需逐题确认落在哪一节。",
    "政治": "旧版单元与新版单元序号相同但内容归属不同；并入哪一单元需业务判定。",
}
DEFAULT_RISK = "需教研确认归属后再迁移；迁移前该章内容对用户不可见，但库内完整保留、可随时回挂。"


def db_path() -> Path:
    for name in ("ailearning_dev.db", "ailearning_device.db"):
        p = BACKEND / name
        if p.is_file():
            return p
    raise SystemExit(f"未找到内容库：{BACKEND / 'ailearning_dev.db'}")


def connect_ro(path: Path) -> sqlite3.Connection:
    """**只读**连接（mode=ro）：不建 journal/wal、不刷新库文件 mtime。"""
    return sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="生成占位章节待确认清单（只读）")
    ap.add_argument("--out", default=str(HERE / "chapter_pending_map_20261108.json"))
    args = ap.parse_args()

    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    skeletons: dict[tuple[str, int, str], list[dict]] = {}
    for folder in SKELETON_DIRS.values():
        if not folder.is_dir():
            continue
        for p in sorted(folder.glob("chapters_*_20261107.json")):
            data = json.loads(p.read_text(encoding="utf-8"))
            skeletons.setdefault(
                (data["subject"], int(data["grade"]), data["semester"]), []
            ).extend(data["chapters"])

    con = connect_ro(db_path())
    con.row_factory = sqlite3.Row
    kp = {r["id"]: dict(r) for r in con.execute("select id,name,parent_id from knowledge_points")}

    def chain(kid):
        parts, cur, guard = [], kid, 0
        while cur and guard < 8:
            node = kp.get(cur)
            if not node:
                break
            parts.append(node["name"])
            cur = node["parent_id"]
            guard += 1
        return " > ".join(parts)

    items = []
    for entry in plan["keep_marked"]:
        subject, grade, semester = entry["subject"], entry["grade"], entry["semester"]
        tb = con.execute(
            "select id,version from textbooks where subject=? and grade=? and semester=?",
            (subject, grade, semester)).fetchone()
        row = con.execute(
            "select id,name,order_index,is_placeholder,placeholder_note from chapters "
            "where textbook_id=? and name=?", (tb["id"], entry["name"])).fetchone()
        official = [
            {"name": c["name"], "order_index": c["order_index"]}
            for c in skeletons.get((subject, grade, semester), [])
        ]
        questions = []
        if row is not None:
            for q in con.execute(
                "select id,knowledge_point_id,content,q_type from questions "
                "where chapter_id=? order by id", (row["id"],)):
                try:
                    stem = str((json.loads(q["content"]) or {}).get("stem") or "")
                except (TypeError, json.JSONDecodeError):
                    stem = str(q["content"])
                questions.append({
                    "id": q["id"],
                    "knowledge_point_chain": chain(q["knowledge_point_id"]),
                    "q_type": q["q_type"],
                    "stem": " ".join(stem.split())[:60],
                })
        items.append({
            "subject": subject,
            "subject_cn": SUBJECT_CN.get(subject, subject),
            "grade": grade,
            "semester": semester,
            "textbook_version": tb["version"] if tb else None,
            "chapter_id": row["id"] if row else None,
            "chapter_name": entry["name"],
            "current_state": {
                "is_placeholder": row["is_placeholder"] if row else None,
                "order_index": row["order_index"] if row else None,
                "placeholder_note": row["placeholder_note"] if row else None,
                "questions": len(questions),
            },
            "reason": entry["reason"],
            "suggestion": entry["suggestion"],
            "risk": RISK.get(SUBJECT_CN.get(subject, ""), DEFAULT_RISK),
            "candidate_official_chapters": official,
            "questions": questions,
        })

    out = {
        "_meta": {
            "kind": "chapter_pending_map",
            "generated": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "purpose": "占位章节清理立项 · 阶段 2：需教材判断的归属确认清单（只读产出，不改库）",
            "source_plan": "chapter_cleanup_plan_20261108.json（keep_marked 段）",
            "totals": {
                "pending_chapters": len(items),
                "pending_questions": sum(i["current_state"]["questions"] for i in items),
            },
            "how_to_use": [
                "1. 业务按 subject/grade/semester 挑出该归属的教材真实章节（candidate_official_chapters）；",
                "2. 把结论回填到 chapter_cleanup_plan_20261108.json 的 migrate 段（rule 记 R-B、evidence 写依据）；",
                "3. 重跑 chapter_cleanup.py --confirm I_KNOW，脚本按新判定表迁移并清掉该占位章。",
            ],
        },
        "items": items,
    }
    Path(args.out).write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"written {args.out} pending_chapters={len(items)} "
          f"pending_questions={out['_meta']['totals']['pending_questions']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
