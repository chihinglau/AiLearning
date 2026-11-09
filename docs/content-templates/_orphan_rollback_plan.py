"""生成「33 题无出处」的回退方案（只读库，只写方案文件，不写库）。

做法：把 4 册库内题目按 stem 与本地全部 JSON（daily + daily_consolidated）比对，
找不到出处的题列出 id / chapter / stem，生成可人工审核的 SQL 回退脚本。
"""

import glob
import json
import os
import sqlite3
from pathlib import Path

CT = Path(r"D:\ai\prj\trae\HuaWei\AiLearning\docs\content-templates")
DB = r"D:\ai\prj\trae\HuaWei\AiLearning\backend\ailearning_dev.db"
OUT = CT / "exports" / "review_20261109"
PAIRS = [("math", 1), ("chinese", 1), ("english", 1), ("physics", 8)]
OTHERS = [("math", 8), ("chinese", 8), ("english", 8)]


def norm(text: str) -> str:
    return "".join(str(text or "").split())


def _stem(content) -> str:
    """库内 content 是 JSON（含题干），取题干部分。"""
    try:
        doc = json.loads(content) if isinstance(content, str) else content
    except (json.JSONDecodeError, TypeError):
        return str(content or "")
    if isinstance(doc, dict):
        return str(doc.get("stem") or doc.get("question") or doc.get("text") or "")
    return str(content or "")


def local_stems(subject: str, grade: int) -> set[str]:
    stems = set()
    for pattern in [f"daily/{subject}/g{grade}/*.json", f"daily_consolidated/{subject}/g{grade}/*.json"]:
        for path in glob.glob(str(CT / pattern)):
            try:
                doc = json.loads(Path(path).read_text(encoding="utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            for chapter in doc.get("chapters") or []:
                for q in chapter.get("questions") or []:
                    stems.add(norm(q.get("stem")))
    return stems


def main() -> int:
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    lines_md = ["# 33 题无出处 · 回退方案（只读生成，未写库）", "",
                "> 用法：确认后**人工**在停后端的前提下执行 SQL；执行前必先备份（`04` §3.1 ①）。",
                "> 本脚本只列出待删题，不判断是否还有人引用；执行后出 `db_op_*.json` 留痕。", ""]
    sql = ["-- 33 题无出处 · 回退脚本（人工执行；执行前先备份 dev 库）",
           "-- 生成时间：" + __import__("datetime").datetime.now().isoformat(timespec="seconds"),
           "-- 复核：执行第 1 段后题量应减少 33；第 2 段确认 0 残留", "",
           "-- 0) 先备份（在 04 手册第 3 节里跑 ops backup），再执行下面语句", ""]
    total = 0
    all_ids: list[int] = []
    for subject, grade in PAIRS:
        known = local_stems(subject, grade)
        rows = conn.execute(
            "SELECT q.id, q.content, q.chapter_id, c.name AS chapter_name "
            "FROM questions q LEFT JOIN chapters c ON c.id = q.chapter_id "
            "WHERE q.subject = ? AND c.grade = ?",
            (subject, grade),
        ).fetchall()
        orphans = [r for r in rows if norm(_stem(r["content"])) not in known]
        total += len(orphans)
        lines_md += [f"## {subject} g{grade}：库内 {len(rows)} 题，无出处 {len(orphans)} 题", "",
                     "| id | 章节 | 题干（截断 60 字） |", "|---|---|---|"]
        for r in orphans:
            stem_text = _stem(r["content"])
            lines_md.append(f"| {r['id']} | {r['chapter_name'] or r['chapter_id']} | {stem_text[:60].replace('|', '｜')} |")
        lines_md.append("")
        sql.append(f"-- {subject} g{grade}：{len(orphans)} 题")
        if orphans:
            ids = ",".join(str(r["id"]) for r in orphans)
            all_ids.extend(r["id"] for r in orphans)
            sql.append(f"DELETE FROM questions WHERE id IN ({ids});")
        chapter_counts = {}
        for r in rows:
            chapter_counts.setdefault(r["chapter_name"], 0)
            chapter_counts[r["chapter_name"]] += 1
        for name, kept in chapter_counts.items():
            if kept and name and kept <= len(orphans) and all(
                norm(_stem(r["content"])) not in known for r in rows if r["chapter_name"] == name
            ):
                lines_md.append(f"> 注意：删完后「{name}」将变为 0 题（孤题章），需随重跑补齐。")
                lines_md.append("")

    for subject, grade in OTHERS:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM questions q JOIN chapters c ON c.id=q.chapter_id "
            "WHERE q.subject=? AND c.grade=?", (subject, grade),
        ).fetchone()
        lines_md.append(f"- {subject} g{grade}：库内 {row['n']} 题，**整册内容来自 11-07 旧规格** → 走重跑覆盖，不逐题删")

    verify_ids = ",".join(str(i) for i in all_ids) or "0"
    sql += ["", "-- 复核：删完再跑一次，应为 0",
            f"SELECT COUNT(*) FROM questions WHERE id IN ({verify_ids});", ""]
    conn.close()

    (OUT / "orphan-rollback-plan_20261109.md").write_text("\n".join(lines_md) + "\n", encoding="utf-8")
    (OUT / "orphan-rollback_20261109.sql").write_text("\n".join(sql) + "\n", encoding="utf-8")
    print(f"无出处合计 {total} 题；已写 orphan-rollback-plan_20261109.md 与 orphan-rollback_20261109.sql")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
