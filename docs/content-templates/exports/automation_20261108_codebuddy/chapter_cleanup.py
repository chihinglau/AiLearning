"""占位章节清理 · 阶段 1 执行脚本（人工运维，需显式 --confirm I_KNOW）。

背景见 `05-占位章节清理立项.md`：库里混着「教材真实章节」与「历史占位/旧样章」，
后者（39 个 / 297 题）与真实章节同级并列、order_index 撞号，app 端会看到教材上
不存在的章节。本脚本按判定表 `chapter_cleanup_plan_20261108.json` 做**确定性**清理：

    R-A/R-B 旧样章 → 题目迁移到教材真实章节 → 旧章删除
    R-C   旧样章 → 题目原地保留 + is_placeholder=1 + order_index 沉底
    教材真实章节   → order_index 回写官方章节骨架序（消除官方-官方撞号）

硬约束：
- 只改 `questions.chapter_id`、`chapters.order_index`、`chapters.is_placeholder`、
  `chapters.placeholder_note`，**不删题、不改题、不改知识点**；
- 写库前必须整库备份；每次执行产出一份 `db_op_<ts>.json` 机器可读留痕；
- 不删旧样章时，若该章仍有题目（迁移后非空），一律转 R-C 保留，不丢内容。

> **2026-11-08 20:4x 更新（阶段 4）**：用户指示「旧版数据删掉」，R-C 的 24 个旧章不再保留，
> 改由 **`chapter_drop_legacy.py`** 整章删除（含 130 题与 61 个独占知识点）。
> 因此本脚本的 R-C 分支**已被取代**，正常流程不要再重跑；`--alias-only` 仍可用
> （生成导入层别名/丢弃表 `chapter_aliases.json`）。

用法：

    python chapter_cleanup.py --dry-run                      # 只算不写
    python chapter_cleanup.py --confirm I_KNOW               # 真执行
    python chapter_cleanup.py --confirm I_KNOW --skip-alembic # 跳过迁移版本升级

回滚：

    python db_ops.py restore --backup backend/build/backups/<备份>.db --force --confirm I_KNOW
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parents[1]                       # docs/content-templates
ROOT = CT.parents[1]                       # 工作区根
BACKEND = ROOT / "backend"
PY = BACKEND / ".venv" / "Scripts" / "python.exe"
PLAN_PATH = HERE / "chapter_cleanup_plan_20261108.json"
SKELETON_DIRS = {
    "first": CT / "baseline" / "_skeleton_first",
    "second": CT / "baseline" / "_skeleton",
}
PREFIX_RE = re.compile(
    r"^(第[0-9一二三四五六七八九十]+[单元章节课篇部分]{1,2}\s*|Unit\s*\d+\s*|Module\s*\d+\s*)",
    re.I,
)
SINK_BASE = 9000          # 占位章沉底基准序（order_index 为 NOT NULL，不能置 NULL）


def die(msg: str, code: int = 2) -> None:
    print(f"[错误] {msg}", file=sys.stderr)
    raise SystemExit(code)


def db_path() -> Path:
    for name in ("ailearning_dev.db", "ailearning_device.db"):
        p = BACKEND / name
        if p.is_file():
            return p
    die(f"未找到内容库：{BACKEND / 'ailearning_dev.db'}")


def core_name(name: str) -> str:
    """剥掉「第N单元/第N章/Unit N」前缀后的核心名。"""
    prev = None
    cur = (name or "").strip()
    while prev != cur:
        prev = cur
        cur = PREFIX_RE.sub("", cur).strip()
    return re.sub(r"[\s*]+", "", cur)


def load_skeletons() -> dict[tuple[str, int, str], dict[str, int]]:
    """(subject, grade, semester) -> {章节名: 官方序}。"""
    out: dict[tuple[str, int, str], dict[str, int]] = {}
    for sem, folder in SKELETON_DIRS.items():
        if not folder.is_dir():
            continue
        for p in sorted(folder.glob("chapters_*_20261107.json")):
            data = json.loads(p.read_text(encoding="utf-8"))
            key = (data["subject"], int(data["grade"]), data["semester"])
            out.setdefault(key, {}).update(
                {c["name"]: int(c["order_index"]) for c in data["chapters"]}
            )
    return out


def run_alembic() -> tuple[int, str]:
    # PYTHONUTF8=1：alembic.ini 里带中文注释，Windows 默认 GBK 读配置文件会炸
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    res = subprocess.run(
        [str(PY), "-m", "alembic", "upgrade", "head"],
        cwd=str(BACKEND), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace",
    )
    return res.returncode, res.stdout.strip()


def backup_db() -> Path:
    res = subprocess.run(
        [str(PY), "-m", "scripts.db_backup"],
        cwd=str(BACKEND), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace",
    )
    m = re.search(r"\[backup\] wrote (.+)", res.stdout or "")
    if res.returncode != 0 or not m:
        die(f"备份失败（未做任何改动）：\n{(res.stdout or '')[-600:]}")
    path = Path(m.group(1).strip())
    if not path.is_file() or path.stat().st_size == 0:
        die(f"备份文件不存在或为空：{path}")
    print(f"[备份] {path}（{path.stat().st_size} 字节）")
    return path


def _discard_rows(plan: dict) -> list[dict]:
    """旧版数据丢弃表：章名 + 对应知识点板块名（板块名与章名可能不同）。"""
    rows = []
    for k in plan["keep_marked"]:
        base = {
            "subject": k["subject"], "grade": k["grade"], "semester": k["semester"],
            "rule": "R-C", "reason": k["reason"], "suggestion": k["suggestion"],
        }
        names = [k["name"]] + [n for n in (k.get("section_names") or []) if n != k["name"]]
        for n in names:
            rows.append(dict(base, name=n))
    return rows


def resolve_textbook(cur: sqlite3.Cursor, subject: str, grade: int, semester: str) -> int:
    rows = list(cur.execute(
        "select id,version from textbooks where subject=? and grade=? and semester=?",
        (subject, grade, semester)))
    if len(rows) != 1:
        die(f"教材定位不唯一：{subject} g{grade} {semester} → {rows}")
    return int(rows[0][0])


def main() -> int:
    ap = argparse.ArgumentParser(description="占位章节清理 · 阶段 1（人工运维）")
    ap.add_argument("--dry-run", action="store_true", help="只计算与校验，不写数据库")
    ap.add_argument("--confirm", choices=["I_KNOW"], help="显式确认会写数据库")
    ap.add_argument("--skip-alembic", action="store_true", help="跳过 alembic 版本升级")
    ap.add_argument("--alias-only", action="store_true",
                    help="只重新生成导入别名表 chapter_aliases.json，不碰数据库")
    ap.add_argument("--plan", default=str(PLAN_PATH), help="判定表路径")
    args = ap.parse_args()

    if not args.dry_run and not args.alias_only and args.confirm != "I_KNOW":
        die("写库必须显式 --confirm I_KNOW（教研会话禁止调用本脚本）")

    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))

    if args.alias_only:
        out = BACKEND / "app" / "services" / "chapter_aliases.json"
        out.write_text(
            json.dumps({
                "_meta": {
                    "kind": "chapter_import_alias",
                    "generated": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                    "purpose": "导入层旧章名 → 教材真实章节名映射；旧 JSON 重导时不再重建占位章",
                    "source": "docs/content-templates/exports/automation_20261108_codebuddy/chapter_cleanup_plan_20261108.json",
                    "note": "aliases：旧章名重定向到教材真实章节；discard：旧版数据章名，导入时整章丢弃（不建章、不挂题、不建知识点）",
                },
                "aliases": [
                    {"subject": m["subject"], "grade": m["grade"], "semester": m["semester"],
                     "legacy": m["legacy"], "canonical": m["target"], "rule": m["rule"]}
                    for m in plan["migrate"]
                ],
                "discard": _discard_rows(plan),
            }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[alias-only] 已写出 {out}")
        return 0

    skeletons = load_skeletons()
    db = db_path()
    con = sqlite3.connect(str(db))
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    # ---------- 预检：列是否存在 ----------
    cols = {r[1] for r in cur.execute("pragma table_info(chapters)")}
    need_alembic = not {"is_placeholder", "placeholder_note"} <= cols
    if need_alembic and args.skip_alembic:
        die("chapters 缺少 is_placeholder / placeholder_note 两列；请先跑 alembic upgrade head")

    # ---------- 解析判定表 ----------
    actions: list[dict] = []
    already: list[dict] = []
    errors: list[str] = []
    for item in plan["migrate"]:
        tb_id = resolve_textbook(cur, item["subject"], item["grade"], item["semester"])
        skel = skeletons.get((item["subject"], item["grade"], item["semester"]), {})
        legacy = cur.execute(
            "select id,name,order_index from chapters where textbook_id=? and name=?",
            (tb_id, item["legacy"])).fetchone()
        target = cur.execute(
            "select id,name from chapters where textbook_id=? and name=?",
            (tb_id, item["target"])).fetchone()
        if target is None:
            errors.append(f"目标官方章不存在：{item['subject']} g{item['grade']} 「{item['target']}」")
            continue
        if target["name"] not in skel:
            errors.append(f"目标不是官方章节（不在骨架里）：{item['target']}")
            continue
        if legacy is None:
            # 旧章已删、目标章在 → 上次已执行过，幂等跳过
            already.append({
                "legacy": item["legacy"], "target": item["target"],
                "subject": item["subject"], "grade": item["grade"],
                "semester": item["semester"], "rule": item["rule"],
            })
            continue
        if legacy["name"] in skel:
            errors.append(f"旧样章其实是官方章节，拒绝处理：{item['legacy']}")
            continue
        if target["id"] == legacy["id"]:
            errors.append(f"目标与旧样章相同：{item['legacy']}")
            continue
        qids = [int(r[0]) for r in cur.execute(
            "select id from questions where chapter_id=? order by id", (legacy["id"],))]
        overrides = {int(o["question_id"]): o for o in item.get("question_overrides") or []}
        for qid in overrides:
            if qid not in qids:
                errors.append(f"例外题 {qid} 不在旧样章「{item['legacy']}」里")
        targets = {}
        for qid in qids:
            ov = overrides.get(qid)
            if ov:
                t = cur.execute("select id from chapters where textbook_id=? and name=?",
                                (tb_id, ov["target"])).fetchone()
                if t is None:
                    errors.append(f"例外题目标章不存在：{ov['target']}")
                    continue
                targets[qid] = (int(t[0]), ov["target"])
            else:
                targets[qid] = (int(target["id"]), target["name"])
        actions.append({
            "kind": "migrate",
            "rule": item["rule"],
            "subject": item["subject"], "grade": item["grade"], "semester": item["semester"],
            "textbook_id": tb_id,
            "legacy_id": int(legacy["id"]), "legacy_name": legacy["name"],
            "legacy_order_before": legacy["order_index"],
            "target_id": int(target["id"]), "target_name": target["name"],
            "questions": len(qids),
            "overrides": {str(k): v[1] for k, v in targets.items()
                          if v[1] != target["name"]},
            "evidence": item["evidence"],
            "_targets": targets,
        })

    keeps: list[dict] = []
    for item in plan["keep_marked"]:
        tb_id = resolve_textbook(cur, item["subject"], item["grade"], item["semester"])
        skel = skeletons.get((item["subject"], item["grade"], item["semester"]), {})
        legacy = cur.execute(
            "select id,name,order_index from chapters where textbook_id=? and name=?",
            (tb_id, item["name"])).fetchone()
        if legacy is None:
            already.append({
                "legacy": item["name"], "target": None,
                "subject": item["subject"], "grade": item["grade"],
                "semester": item["semester"], "rule": "R-C",
            })
            continue
        if legacy["name"] in skel:
            errors.append(f"旧样章其实是官方章节，拒绝处理：{item['name']}")
            continue
        nq = cur.execute("select count(*) from questions where chapter_id=?",
                         (legacy["id"],)).fetchone()[0]
        keeps.append({
            "kind": "keep_marked",
            "rule": "R-C",
            "subject": item["subject"], "grade": item["grade"], "semester": item["semester"],
            "textbook_id": tb_id,
            "legacy_id": int(legacy["id"]), "legacy_name": legacy["name"],
            "legacy_order_before": legacy["order_index"],
            "questions": int(nq),
            "reason": item["reason"], "suggestion": item["suggestion"],
        })

    # ---------- order_index 回写（官方骨架） ----------
    order_fix: list[dict] = []
    for (subject, grade, sem), skel in skeletons.items():
        try:
            tb_id = resolve_textbook(cur, subject, grade, sem)
        except SystemExit:
            continue
        for name, order in skel.items():
            row = cur.execute("select id,order_index from chapters where textbook_id=? and name=?",
                               (tb_id, name)).fetchone()
            if row is None:
                continue
            if int(row["order_index"]) != int(order):
                order_fix.append({
                    "chapter_id": int(row["id"]), "name": name,
                    "from": int(row["order_index"]), "to": int(order),
                    "subject": subject, "grade": grade, "semester": sem,
                })

    print(f"# 占位章节清理 · 阶段 1（{'试跑' if args.dry_run else '执行'}）· 库 {db.name}")
    print(f"- 判定表：{Path(args.plan).name}")
    print(f"- 迁移旧样章 {len(actions)} 个；保留标记 {len(keeps)} 个；order_index 回写 {len(order_fix)} 处"
          + (f"；已完成跳过 {len(already)} 个" if already else ""))
    for a in actions:
        print(f"  [迁移/{a['rule']}] {a['subject']} g{a['grade']} 「{a['legacy_name']}」"
              f"({a['questions']} 题) → 「{a['target_name']}」")
    for k in keeps:
        print(f"  [保留/R-C] {k['subject']} g{k['grade']} 「{k['legacy_name']}」({k['questions']} 题)")
    if errors:
        print("\n[预检未通过，不做任何改动]")
        for e in errors:
            print(f"  - {e}")
        return 3

    if args.dry_run:
        print("\n[试跑完成] 未写数据库")
        return 0

    # ---------- 备份 ----------
    backup = backup_db()

    if need_alembic:
        rc, out = run_alembic()
        print(f"- alembic upgrade head：EXIT={rc}")
        if rc != 0:
            con.close()
            die(f"alembic 升级失败，未做任何数据改动：\n{out[-800:]}")
        con = sqlite3.connect(str(db))
        con.row_factory = sqlite3.Row
        cur = con.cursor()

    # ---------- 执行 ----------
    before = {t: cur.execute(f"select count(*) from {t}").fetchone()[0]
              for t in ("textbooks", "chapters", "knowledge_points", "questions")}
    moved: list[dict] = []
    deleted: list[dict] = []
    marked: list[dict] = []

    for a in actions:
        for qid, (tid, tname) in a["_targets"].items():
            cur.execute("update questions set chapter_id=? where id=? and chapter_id=?",
                        (tid, qid, a["legacy_id"]))
        left = cur.execute("select count(*) from questions where chapter_id=?",
                           (a["legacy_id"],)).fetchone()[0]
        moved.append({
            "legacy_chapter_id": a["legacy_id"], "legacy_chapter": a["legacy_name"],
            "target_chapter_id": a["target_id"], "target_chapter": a["target_name"],
            "subject": a["subject"], "grade": a["grade"], "semester": a["semester"],
            "rule": a["rule"], "questions_moved": a["questions"],
            "per_question_overrides": a["overrides"], "evidence": a["evidence"],
        })
        if left == 0:
            cur.execute("delete from chapters where id=?", (a["legacy_id"],))
            deleted.append({"chapter_id": a["legacy_id"], "name": a["legacy_name"],
                            "order_index_before": a["legacy_order_before"],
                            "questions_moved_to": a["target_id"]})
        else:
            note = (f"R-C 兜底：判定为迁移到「{a['target_name']}」，但迁移后仍有 {left} 题留在本章，"
                    f"改按占位保留。依据：{a['evidence']}")
            cur.execute(
                "update chapters set is_placeholder=1, order_index=?, placeholder_note=? where id=?",
                (SINK_BASE + a["legacy_id"], note, a["legacy_id"]))
            marked.append({"chapter_id": a["legacy_id"], "name": a["legacy_name"],
                           "questions": left, "note": note})

    for k in keeps:
        note = f"R-C 保留：{k['reason']} 建议：{k['suggestion']}"
        cur.execute(
            "update chapters set is_placeholder=1, order_index=?, placeholder_note=? where id=?",
            (SINK_BASE + k["legacy_id"], note, k["legacy_id"]))
        marked.append({"chapter_id": k["legacy_id"], "name": k["legacy_name"],
                       "questions": k["questions"], "note": note})

    for f in order_fix:
        cur.execute("update chapters set order_index=? where id=?", (f["to"], f["chapter_id"]))

    # 官方章显式置 0（防御：万一历史上有误标）
    for (subject, grade, sem), skel in skeletons.items():
        try:
            tb_id = resolve_textbook(cur, subject, grade, sem)
        except SystemExit:
            continue
        for name in skel:
            cur.execute("update chapters set is_placeholder=0 where textbook_id=? and name=?",
                        (tb_id, name))

    # 删除旧章后，修正引用这些章节的考试（exams.chapter_ids 是 JSON 数组）
    legacy_to_target = {a["legacy_id"]: a["target_id"] for a in actions}
    exam_fix: list[dict] = []
    for row in list(cur.execute("select id, title, chapter_ids from exams")):
        raw = row["chapter_ids"]
        if not raw:
            continue
        try:
            arr = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            continue
        if not isinstance(arr, list):
            continue
        new_arr, changed = [], False
        for cid in arr:
            if not isinstance(cid, int):
                continue
            target = legacy_to_target.get(cid)
            if target is not None:
                changed = True
                if target not in new_arr:
                    new_arr.append(target)
            elif cid not in new_arr:
                new_arr.append(cid)
        if changed:
            cur.execute("update exams set chapter_ids=? where id=?",
                        (json.dumps(new_arr, ensure_ascii=False), row["id"]))
            exam_fix.append({"exam_id": row["id"], "title": row["title"],
                             "from": arr, "to": new_arr})

    con.commit()

    # ---------- 事后自检 ----------
    after = {t: cur.execute(f"select count(*) from {t}").fetchone()[0]
             for t in ("textbooks", "chapters", "knowledge_points", "questions")}
    qc = cur.execute("pragma quick_check").fetchone()[0]
    fk = cur.execute("pragma foreign_key_check").fetchall()
    orphan = cur.execute(
        "select count(*) from questions q left join chapters c on c.id=q.chapter_id "
        "where c.id is null").fetchone()[0]
    ph = cur.execute("select count(*) from chapters where is_placeholder=1").fetchone()[0]
    conflicts = []
    for (subject, grade, sem), skel in skeletons.items():
        try:
            tb_id = resolve_textbook(cur, subject, grade, sem)
        except SystemExit:
            continue
        groups = {}
        for row in cur.execute("select id,name,order_index from chapters where textbook_id=?",
                               (tb_id,)):
            groups.setdefault(int(row["order_index"]), []).append(row["name"])
        for oi, names in groups.items():
            if len(names) > 1:
                conflicts.append({"subject": subject, "grade": grade, "semester": sem,
                                  "order_index": oi, "names": names})

    report = {
        "_meta": {
            "kind": "chapter_cleanup_stage1",
            "generated": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "tool": "chapter_cleanup.py（人工运维，--confirm I_KNOW）",
            "database": str(db),
            "backup": str(backup),
            "plan": str(Path(args.plan)),
            "restore_hint": (f'python db_ops.py restore --backup "{backup}" --force --confirm I_KNOW'),
            "semantics": "R-A/R-B 旧样章：题目迁移到教材真实章节后删除旧章；"
                         "R-C 旧样章：题目原地保留 + is_placeholder=1 + order_index 沉底；"
                         "教材真实章节 order_index 回写官方章节骨架序。题目零删除。",
        },
        "stats": {
            "before": before, "after": after,
            "delta": {t: after[t] - before[t] for t in before},
            "chapters_deleted": len(deleted),
            "chapters_marked_placeholder": len(marked),
            "questions_moved": sum(m["questions_moved"] for m in moved),
            "order_index_fixed": len(order_fix),
        },
        "checks": {
            "quick_check": qc,
            "foreign_key_violations": len(fk),
            "orphan_question_chapter_refs": orphan,
            "placeholder_chapters_left": ph,
            "order_index_conflicts_left": conflicts,
            "questions_preserved": before["questions"] == after["questions"],
        },
        "migrated": moved,
        "deleted_chapters": deleted,
        "marked_chapters": marked,
        "order_index_fixed": order_fix,
        "exams_chapter_ids_fixed": exam_fix,
        # ---- 统一骨架（第十二轮评审 B 项）：与 db_ops.py audit 的报告对齐 ----
        # 消费方统一按 changes[] / rollback 读，不必再分辨 deleted / deleted_chapters / migrated。
        "changes": (
            [{"table": "chapter", "id": d["chapter_id"], "name": d["name"],
              "action": "delete", "questions_moved_to": d.get("questions_moved_to")} for d in deleted]
            + [{"table": "chapter", "id": m["chapter_id"], "name": m["name"],
                "action": "mark_placeholder", "questions": m.get("questions")} for m in marked]
            + [{"table": "chapter", "id": m["legacy_chapter_id"], "name": m["legacy_chapter"],
                "action": "move_questions", "to_chapter_id": m["target_chapter_id"],
                "to_chapter": m["target_chapter"], "questions_moved": m.get("questions_moved"),
                "rule": m.get("rule")} for m in moved]
            + [{"table": "chapter", "id": o["chapter_id"], "name": o["name"],
                "action": "fix_order_index", "before": o["from"], "after": o["to"]} for o in order_fix]
        ),
        "rollback": {
            "backup": str(backup),
            "command": f'python db_ops.py restore --backup "{backup}" --force --confirm I_KNOW',
        },
    }
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = HERE / f"db_op_{stamp}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # 阶段 3 用的导入别名表（与判定表同源）
    alias = {
        "_meta": {
            "kind": "chapter_import_alias",
            "generated": report["_meta"]["generated"],
            "purpose": "导入层旧章名 → 教材真实章节名映射；旧版数据章名整章丢弃",
            "source": "docs/content-templates/exports/automation_20261108_codebuddy/chapter_cleanup_plan_20261108.json",
            "note": "aliases：旧章名重定向到教材真实章节；discard：旧版数据章名与知识点板块名，导入时整块丢弃",
        },
        "aliases": [
            {"subject": m["subject"], "grade": m["grade"], "semester": m["semester"],
             "legacy": m["legacy"], "canonical": m["target"], "rule": m["rule"]}
            for m in plan["migrate"]
        ],
        "discard": _discard_rows(plan),
    }
    alias_path = BACKEND / "app" / "services" / "chapter_aliases.json"
    alias_path.write_text(json.dumps(alias, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"- 计数：{before} → {after}（delta {report['stats']['delta']}）")
    print(f"- 迁移题目 {report['stats']['questions_moved']} 道；删除旧章 {len(deleted)} 个；"
          f"标记占位 {len(marked)} 个；order_index 回写 {len(order_fix)} 处；"
          f"考试章节引用修正 {len(exam_fix)} 条")
    print(f"- 自检：quick_check={qc}；外键问题 {len(fk)}；悬空题目章引用 {orphan}；"
          f"剩余占位章 {ph}；剩余撞号 {len(conflicts)}")
    print(f"- 题目总数守恒：{'是' if before['questions'] == after['questions'] else '否（异常！）'}")
    print(f"- 报告：{out_path}")
    print(f"- 导入别名表：{alias_path}")
    print(f"[回滚] python db_ops.py restore --backup \"{backup}\" --force --confirm I_KNOW")
    con.close()
    return 0 if (qc == "ok" and not fk and orphan == 0 and not conflicts) else 1


if __name__ == "__main__":
    raise SystemExit(main())
