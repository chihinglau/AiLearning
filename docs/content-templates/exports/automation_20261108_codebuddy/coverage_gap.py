"""只读巡检：**教材覆盖缺口**清单（库里哪些章还没题）。

背景（第九轮评审 B 项）：占位章节清理到 0、撞号到 0，只能说明「库干净」，
说明不了「教材覆盖齐了」。真实覆盖是「46 册上册各 1 节」，其余官方章全是空的。
本脚本把「干净」与「齐不齐」两件事分开量化：

- 每册教材：官方章数 / 有题章数 / 0 题章数 / 题目数 / 知识点数；
- `empty_textbooks`：整册 0 题（建议进「待重跑」队列，别在覆盖台账显示成已完成）；
- `empty_chapters`：逐个 0 题的教材真实章节（含 subject/grade/semester/chapter id/序）。

判定口径与 `chapter_audit.py` 一致：**官方章节骨架**
（`docs/content-templates/baseline/_skeleton_first|_skeleton`），占位/旧样章不计入。

用法（只读，不改库）：

    python coverage_gap.py --out coverage_gap_<date>.json
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
    """(subject, grade, semester) -> {章节名: 官方序}。"""
    out: dict = {}
    for folder in SKELETON_DIRS.values():
        if not folder.is_dir():
            continue
        for p in sorted(folder.glob("chapters_*_20261107.json")):
            data = json.loads(p.read_text(encoding="utf-8"))
            key = (data["subject"], int(data["grade"]), data["semester"])
            out.setdefault(key, {}).update(
                {c["name"]: int(c["order_index"]) for c in data["chapters"]}
            )
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="教材覆盖缺口巡检（只读）")
    ap.add_argument("--out", help="输出 JSON 路径")
    ap.add_argument("--semester", choices=["first", "second", "all"], default="first",
                    help="统计口径学期（默认 first 上册，即每日教研覆盖的口径）")
    args = ap.parse_args()

    skeletons = load_skeletons()
    con = connect_ro(db_path())
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    books = []
    for tb in list(cur.execute("select * from textbooks order by subject, grade, semester")):
        subject, grade, semester = tb["subject"], int(tb["grade"] or 0), tb["semester"]
        if args.semester != "all" and semester != args.semester:
            continue
        skel = skeletons.get((subject, grade, semester), {})
        rows = list(cur.execute(
            "select id,name,order_index,is_placeholder from chapters "
            "where textbook_id=? order by order_index,id", (tb["id"],)))
        if not skel:
            # 无官方章节骨架的教材（空册 / 未建目录）：不计入覆盖分母，但要报出来
            books.append({
                "textbook_id": tb["id"], "subject": subject, "grade": grade,
                "semester": semester, "version": tb["version"],
                "official_chapters": 0, "chapters_with_questions": 0,
                "empty_chapters": 0, "questions": 0, "knowledge_points": 0,
                "status": "no_skeleton", "empty_chapter_detail": [],
            })
            continue
        chapters, empty = [], []
        for ch in rows:
            if skel and ch["name"] not in skel:
                continue  # 非教材真实章节（占位/旧样章）不计入覆盖口径
            nq = cur.execute(
                "select count(*) from questions where chapter_id=?", (ch["id"],)).fetchone()[0]
            item = {"id": ch["id"], "name": ch["name"], "order_index": ch["order_index"],
                    "questions": nq}
            chapters.append(item)
            if nq == 0:
                empty.append(item)
        nkp = cur.execute(
            "select count(*) from knowledge_points k join chapters c on c.textbook_id=? "
            "where k.subject=? and k.grade=?", (tb["id"], subject, grade)).fetchone()[0]
        nq = sum(c["questions"] for c in chapters)
        books.append({
            "textbook_id": tb["id"], "subject": subject, "grade": grade,
            "semester": semester, "version": tb["version"],
            "official_chapters": len(chapters), "chapters_with_questions": len(chapters) - len(empty),
            "empty_chapters": len(empty), "questions": nq, "knowledge_points": nkp,
            "status": "empty" if (chapters and nq == 0) else "partial",
            "empty_chapter_detail": empty,
        })

    empty_books = [b for b in books if b["status"] == "empty"]
    partial_books = [b for b in books if b["status"] == "partial"]
    no_skeleton = [b for b in books if b["status"] == "no_skeleton"]

    # 与 tasks.json 的 policy.rerun_queue 对账：登记「待重跑」的册，实测是否真的 0 题
    rerun_queue = []
    tasks_path = HERE / "tasks.json"
    if tasks_path.is_file():
        tasks = json.loads(tasks_path.read_text(encoding="utf-8"))
        for item in tasks.get("policy", {}).get("rerun_queue") or []:
            hit = next((b for b in books
                        if b["subject"] == item["subject"]
                        and b["grade"] == item["grade"]
                        and b["semester"] == item["semester"]), None)
            rerun_queue.append({
                "subject": item["subject"], "grade": item["grade"],
                "semester": item["semester"],
                "registered_reason": item.get("reason"),
                "registered_questions": item.get("questions"),
                "actual_questions": hit["questions"] if hit else None,
                "actual_empty_chapters": hit["empty_chapters"] if hit else None,
                "consistent": bool(hit is not None and hit["questions"] == 0),
                "note": "登记待重跑" if (hit is not None and hit["questions"] == 0)
                        else "**已不成立：该册已有题，待重跑登记可撤**",
            })
    all_empty_chapters = [
        {"subject": b["subject"], "grade": b["grade"], "semester": b["semester"],
         "chapter_id": c["id"], "name": c["name"], "order_index": c["order_index"]}
        for b in books for c in b["empty_chapter_detail"]
    ]
    by_subject: dict = {}
    for b in books:
        s = by_subject.setdefault(b["subject"], {"books": 0, "empty_books": 0,
                                                  "chapters": 0, "empty_chapters": 0, "questions": 0})
        s["books"] += 1
        s["empty_books"] += 1 if b["status"] == "empty" else 0
        s["chapters"] += b["official_chapters"]
        s["empty_chapters"] += b["empty_chapters"]
        s["questions"] += b["questions"]

    report = {
        "_meta": {
            "kind": "coverage_gap",
            "generated": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "tool": "coverage_gap.py（只读）",
            "database": str(db_path()),
            "purpose": "教材覆盖缺口清单：库里哪些教材真实章节还没有题。"
                       "与 chapter_audit.py 分工——后者管「干不干净」（占位/撞号），本脚本管「齐不齐」（覆盖）",
            "criteria": "官方章节骨架口径（baseline/_skeleton_first|_skeleton）；"
                        f"学期口径 semester={args.semester}",
            "semantics": "empty_textbooks = 整册 0 题（建议进待重跑队列，"
                         "不要在覆盖台账里显示成已完成）；empty_chapters = 逐个 0 题的官方章",
            "note": "「占位 0 / 撞号 0」说明库干净，**不等于**教材覆盖齐了——两件事分开看",
        },
        "summary": {
            "textbooks": len(books),
            "empty_textbooks": len(empty_books),
            "partial_textbooks": len(partial_books),
            "textbooks_without_skeleton": len(no_skeleton),
            "official_chapters": sum(b["official_chapters"] for b in books),
            "chapters_with_questions": sum(b["chapters_with_questions"] for b in books),
            "empty_chapters": len(all_empty_chapters),
            "questions": sum(b["questions"] for b in books),
            "by_subject": by_subject,
        },
        "empty_textbooks": [
            {"textbook_id": b["textbook_id"], "subject": b["subject"], "grade": b["grade"],
             "semester": b["semester"], "version": b["version"],
             "official_chapters": b["official_chapters"], "questions": b["questions"],
             "action": "待重跑：旧版内容已按授权删除，需教研按新教材目录重新出题"}
            for b in empty_books
        ],
        "rerun_queue": rerun_queue,
        "empty_chapters": all_empty_chapters,
        "textbooks": books,
    }
    out = Path(args.out).expanduser() if args.out else (
        HERE / f"coverage_gap_{datetime.now():%Y%m%d_%H%M%S}.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"# 教材覆盖缺口巡检（只读，{args.semester} 学期口径）· {db_path().name}")
    print(f"- 教材 {len(books)} 册 / 官方章 {report['summary']['official_chapters']} 个 / "
          f"有题章 {report['summary']['chapters_with_questions']} 个 / 题目 {report['summary']['questions']} 道")
    print(f"- **0 题官方章 {report['summary']['empty_chapters']} 个**；**整册 0 题 {len(empty_books)} 册**；"
          f"无章节骨架（空册）{len(no_skeleton)} 册（不计入覆盖分母）")
    for sub, s in sorted(by_subject.items()):
        print(f"  {sub:<10} 册 {s['books']:>2} / 整册空 {s['empty_books']:>2} / 章 {s['chapters']:>3} / "
              f"0 题章 {s['empty_chapters']:>3} / 题 {s['questions']:>4}")
    if empty_books:
        print("- 整册 0 题（建议进待重跑队列）：")
        for b in empty_books:
            print(f"    {b['subject']} g{b['grade']} {b['semester']} {b['version']}"
                  f"（{b['official_chapters']} 章全空）")
    for r in rerun_queue:
        print(f"- 待重跑登记对账：{r['subject']} g{r['grade']} {r['semester']}"
              f" → {'一致（0 题）' if r['consistent'] else '**已不成立**'}")
    print(f"- 报告：{out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
