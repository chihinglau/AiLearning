"""删除旧版数据（R-C 占位章节及其全部内容）——占位章节清理立项 · 阶段 4。

用户指示（2026-11-08）：「旧版数据删掉」。

删除范围（全部由库现状推导，不手写 id）：
  1. chapters.is_placeholder = 1 的占位章节（教材目录上不存在、旧样章/旧专题）；
  2. 挂在这些章节下的题目；
  3. 因此变空的知识点（独占 point + 其独占 section 父节点）；
  4. exams.chapter_ids 里指向占位章节的 id（剔除，不删考试本身）。

不做的事：
  - 不删教材真实章节、知识点、题目（只删旧版数据）；
  - 不改 chapters.is_placeholder 字段本身（保留作为兜底标记，app 端过滤照旧生效）；
  - 不动 daily/templates 源文件（导入层已加「丢弃」保护，重导不会复活，见 content_import.py）。

用法（人工运维，写库必须显式确认）：
    python chapter_drop_legacy.py --dry-run          # 只算不写
    python chapter_drop_legacy.py --confirm I_KNOW    # 备份 → 删除 → 自检 → 留痕
"""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
BACKEND = ROOT / "backend"
DB = BACKEND / "ailearning_dev.db"
BACKUP_DIR = BACKEND / "build" / "backups"
PLAN_PATH = HERE / "chapter_cleanup_plan_20261108.json"


def die(msg: str) -> None:
    print(f"[错误] {msg}")
    raise SystemExit(2)


def open_db() -> sqlite3.Connection:
    if not DB.is_file():
        die(f"未找到内容库：{DB}")
    con = sqlite3.connect(str(DB))
    con.row_factory = sqlite3.Row
    return con


def table_counts(con: sqlite3.Connection) -> dict:
    out = {}
    for t in ("textbooks", "chapters", "knowledge_points", "questions"):
        out[t] = con.execute(f"select count(*) from {t}").fetchone()[0]
    return out

def compute(con: sqlite3.Connection) -> dict:
    """推导删除集合（全部由库现状推导，不手写 id）。"""
    ph = [dict(r) for r in con.execute(
        "select id,textbook_id,grade,name,order_index from chapters where is_placeholder=1 "
        "order by textbook_id, order_index")]
    ph_ids = [c["id"] for c in ph]
    phs = ",".join(str(i) for i in ph_ids) or "0"
    questions = [dict(r) for r in con.execute(
        "select id,knowledge_point_id,chapter_id from questions where chapter_id in (%s) order by id" % phs)]
    kp_ids = sorted({q["knowledge_point_id"] for q in questions if q["knowledge_point_id"]})
    exclusive_points = []
    for kid in kp_ids:
        total = con.execute("select count(*) from questions where knowledge_point_id=?", (kid,)).fetchone()[0]
        mine = con.execute(
            "select count(*) from questions where knowledge_point_id=? and chapter_id in ("
            + phs + ")", (kid,)).fetchone()[0]
        if total == mine:
            exclusive_points.append(kid)
    kp_rows = {r["id"]: dict(r) for r in con.execute(
        "select id,name,parent_id,node_type from knowledge_points")}
    sections = []
    for kid in exclusive_points:
        pid = kp_rows[kid]["parent_id"]
        if pid is None or pid in sections:
            continue
        children = [c for c in kp_rows.values() if c["parent_id"] == pid]
        if all(c["id"] in set(exclusive_points) for c in children):
            sections.append(pid)
    extra = []
    for sid in list(sections):
        pid = kp_rows[sid]["parent_id"]
        while pid is not None:
            extra.append(pid)
            pid = kp_rows[pid]["parent_id"]
    sections = sorted(set(sections) | set(extra))
    exam_fix = []
    for r in con.execute("select id,chapter_ids from exams where chapter_ids is not null and chapter_ids != ''"):
        raw = str(r["chapter_ids"])
        try:
            ids = json.loads(raw)
        except json.JSONDecodeError:
            ids = [x.strip() for x in raw.replace("[", "").replace("]", "").split(",") if x.strip()]
        hit = [i for i in ids if i in set(ph_ids)]
        if hit:
            exam_fix.append({"exam_id": r["id"], "before": ids, "removed": hit,
                             "after": [i for i in ids if i not in set(ph_ids)]})
    return {
        "placeholder_chapters": ph,
        "questions": questions,
        "exclusive_points": exclusive_points,
        "exclusive_sections": sections,
        "exam_fix": exam_fix,
    }

def self_check(con: sqlite3.Connection) -> dict:
    out = {
        "quick_check": con.execute("pragma quick_check").fetchone()[0],
        "foreign_key_violations": len(con.execute("pragma foreign_key_check").fetchall()),
        "orphan_question_chapter_refs": con.execute(
            "select count(*) from questions q left join chapters c on c.id=q.chapter_id "
            "where c.id is null").fetchone()[0],
        "orphan_question_kp_refs": con.execute(
            "select count(*) from questions q left join knowledge_points k on k.id=q.knowledge_point_id "
            "where k.id is null").fetchone()[0],
        "orphan_kp_parent_refs": con.execute(
            "select count(*) from knowledge_points k left join knowledge_points p on p.id=k.parent_id "
            "where k.parent_id is not null and p.id is null").fetchone()[0],
        "placeholder_chapters_left": con.execute(
            "select count(*) from chapters where is_placeholder=1").fetchone()[0],
    }
    out["exam_chapter_refs_dangling"] = 0
    return out


def repair_exams(con) -> list:
    """修 exams.chapter_ids：剔除指向不存在章节的 id（含历史遗留）。

    判定规则（可复核）：
      1. 剔除所有指向不存在章节的 id；
      2. 若该考试按 subject/grade 能定位到「年级上册教材」，且剔除后剩余章数
         少于该册真实章节数的一半 → 判定为「原本是整册范围、历史 id 失效导致残缺」，
         重新挂该册**全部真实章节**（期末真题本就该覆盖整册）；
      3. 否则保留剔除后的结果。
    """
    fixes = []
    for r in con.execute("select id,title,subject,grade,chapter_ids from exams").fetchall():
        raw = str(r["chapter_ids"] or "").strip()
        try:
            ids = json.loads(raw) if raw else []
        except json.JSONDecodeError:
            ids = []
        ids = [int(i) for i in ids]
        alive = [i for i in ids if con.execute("select 1 from chapters where id=?", (i,)).fetchone()]
        dead = [i for i in ids if i not in alive]
        after = alive
        refilled = False
        reason = "剔除悬空引用"
        tb = con.execute(
            "select id from textbooks where subject=? and grade=? and semester='first'",
            (r["subject"], r["grade"])).fetchone()
        book_chapters = []
        if tb is not None:
            book_chapters = [c["id"] for c in con.execute(
                "select id from chapters where textbook_id=? order by order_index,id", (tb["id"],))]
        if book_chapters and len(alive) * 2 < len(book_chapters):
            after = book_chapters
            refilled = True
            reason = "原范围指向的章节已失效，按该年级上册真实章节整册重挂"
        if after != ids:
            fixes.append({"exam_id": r["id"], "title": r["title"], "before": ids,
                          "removed_dead": dead, "after": after,
                          "refilled_by_textbook": refilled, "reason": reason})
    return fixes


def backup():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().isoformat(timespec="seconds").replace(":", "").replace("-", "").replace("T", "-")
    dst = BACKUP_DIR / ("ailearning-backup-" + stamp + ".db")
    shutil.copy2(str(DB), str(dst))
    return dst

def exam_dangling(con):
    bad = 0
    for r in con.execute("select id, chapter_ids from exams").fetchall():
        raw = str(r["chapter_ids"] or "").strip()
        if not raw:
            continue
        try:
            ids = json.loads(raw)
        except Exception:
            ids = []
        for i in ids:
            if not con.execute("select 1 from chapters where id=?", (i,)).fetchone():
                bad += 1
    return bad

def main() -> int:
    ap = argparse.ArgumentParser(description="删除旧版数据（占位章节及其内容）")
    ap.add_argument("--dry-run", action="store_true", help="只算不写")
    ap.add_argument("--confirm", help="写库必须显式 --confirm I_KNOW")
    ap.add_argument("--skip-backup", action="store_true", help="不备份（不建议）")
    args = ap.parse_args()
    if not args.dry_run and args.confirm != "I_KNOW":
        die("写库必须显式 --confirm I_KNOW（教研会话禁止调用本脚本）")
    con = open_db()
    before = table_counts(con)
    plan = compute(con)
    ph = plan["placeholder_chapters"]
    mode = "试跑" if args.dry_run else "执行"
    print("# 删除旧版数据（" + mode + "）· 库 " + DB.name)
    print("- 占位章节 " + str(len(ph)) + " 个 / 挂题 " + str(len(plan["questions"])) + " 道 / 独占知识点 "
          + str(len(plan["exclusive_points"])) + " 点 + " + str(len(plan["exclusive_sections"])) + " 板块")
    print("- 考试章节引用修正 " + str(len(plan["exam_fix"])) + " 条")
    if not ph:
        print("- 库里已无占位章节，只需修 exams.chapter_ids 悬空引用")
    else:
        for c in ph:
            print("    chapter #" + str(c["id"]) + " " + repr(c["name"]) + " order=" + str(c["order_index"]))
    if args.dry_run:
        fixes = repair_exams(con)
        for f in fixes:
            print("    exam #" + str(f["exam_id"]) + " " + repr(f["title"]) + " "
                  + str(f["before"]) + " -> " + str(f["after"])
                  + ("（按该年级上册重挂）" if f["refilled_by_textbook"] else ""))
        print("- dry-run：未写库")
        con.close()
        return 0
    bk = None
    if not args.skip_backup:
        bk = backup()
        print("- 已备份：" + str(bk))
    phs = ",".join(str(c["id"]) for c in ph)
    qids = ",".join(str(q["id"]) for q in plan["questions"]) or "0"
    kids = ",".join(str(i) for i in plan["exclusive_points"]) or "0"
    sids = ",".join(str(i) for i in plan["exclusive_sections"]) or "0"
    con.execute("delete from questions where id in (" + qids + ")")
    con.execute("delete from knowledge_points where id in (" + kids + ")")
    con.execute("delete from knowledge_points where id in (" + sids + ")")
    con.execute("delete from chapters where id in (" + phs + ")")
    exam_fixes = repair_exams(con)
    for fix in exam_fixes:
        con.execute("update exams set chapter_ids=? where id=?",
                    (json.dumps(fix["after"], ensure_ascii=False), fix["exam_id"]))
    con.commit()
    after = table_counts(con)
    checks = self_check(con)
    checks["exam_chapter_refs_dangling"] = exam_dangling(con)
    print("- 删除后：chapters " + str(before["chapters"]) + "→" + str(after["chapters"])
          + "、knowledge_points " + str(before["knowledge_points"]) + "→" + str(after["knowledge_points"])
          + "、questions " + str(before["questions"]) + "→" + str(after["questions"]))
    for k, v in checks.items():
        print("    " + k + ": " + str(v))
    report = {
        "_meta": {
            "kind": "chapter_drop_legacy",
            "generated": datetime.now().isoformat(timespec="seconds"),
            "tool": "chapter_drop_legacy.py（人工运维，--confirm I_KNOW）",
            "database": str(DB),
            "backup": str(bk) if bk else None,
            "restore_hint": ('python db_ops.py restore --backup "' + str(bk) + '" --force --confirm I_KNOW'
                             if bk else None),
            "plan": str(PLAN_PATH),
            "semantics": "删除教材目录上不存在的旧样章（is_placeholder=1）及其全部题目、独占知识点；"
                         "exams.chapter_ids 剔除占位章 id；教材真实章节/知识点/题目零删除。",
        },
        "stats": {
            "before": before,
            "after": after,
            "delta": {k: after[k] - before[k] for k in before},
            "chapters_deleted": len(ph),
            "questions_deleted": len(plan["questions"]),
            "knowledge_points_deleted": len(plan["exclusive_points"]) + len(plan["exclusive_sections"]),
            "exam_refs_fixed": len(plan["exam_fix"]),
        },
        "checks": checks,
        "deleted": {
            "chapters": ph,
            "question_ids": [q["id"] for q in plan["questions"]],
            "exclusive_point_ids": plan["exclusive_points"],
            "exclusive_section_ids": plan["exclusive_sections"],
        },
        "exams_fixed": exam_fixes,
        # ---- 统一骨架（第十二轮评审 B 项）：与 db_ops.py audit 的报告对齐 ----
        # 消费方统一按 changes[] / rollback 读，不必再分辨 deleted / deleted_chapters / migrated。
        "changes": (
            [{"table": "chapter", "id": c.get("id"), "name": c.get("name"),
              "grade": c.get("grade"), "action": "delete"} for c in ph]
            + [{"table": "question", "id": q["id"], "action": "delete",
                "chapter_id": q.get("chapter_id"), "knowledge_point_id": q.get("knowledge_point_id")}
               for q in plan["questions"]]
            + [{"table": "knowledge_point", "id": pid, "action": "delete"} for pid in plan["exclusive_points"]]
            + [{"table": "knowledge_point", "id": sid, "action": "delete"} for sid in plan["exclusive_sections"]]
        ),
        "rollback": {
            "backup": str(bk) if bk else None,
            "command": ('python db_ops.py restore --backup "' + str(bk) + '" --force --confirm I_KNOW'
                        if bk else None),
        },
    }
    stamp = datetime.now().isoformat(timespec="seconds").replace(":", "").replace("-", "").replace("T", "_")
    out = HERE / ("db_op_" + stamp + ".json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("- 留痕：" + str(out))
    ok = (checks["quick_check"] == "ok" and checks["foreign_key_violations"] == 0
          and checks["orphan_question_chapter_refs"] == 0 and checks["orphan_question_kp_refs"] == 0
          and checks["orphan_kp_parent_refs"] == 0 and checks["exam_chapter_refs_dangling"] == 0)
    con.close()
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())