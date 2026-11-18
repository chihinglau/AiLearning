# -*- coding: utf-8 -*-
"""逐册核对：库内题量与整册文件完全相等，且文件内每道题都能在库内查到。"""
import glob, io, json, os, re, sqlite3

CT = r"D:\ai\prj\trae\HuaWei\AiLearning\docs\content-templates"
DB = r"D:\ai\prj\trae\HuaWei\AiLearning\backend\ailearning_dev.db"


def norm(s):
    return re.sub(r"\s+", "", str(s or ""))


con = sqlite3.connect(DB)
cur = con.cursor()
books = sorted(glob.glob(os.path.join(CT, "daily_consolidated", "*", "g*", "*_20261113_book.json")))
bad, total_file, total_db = [], 0, 0
for p in books:
    d = json.load(io.open(p, encoding="utf-8"))
    s, g, sem = d["subject"], d["grade"], d["semester"]
    tids = [r[0] for r in cur.execute(
        "select id from textbooks where subject=? and grade=? and semester=?", (s, g, sem))]
    if not tids:
        bad.append((os.path.basename(p), "教材缺失")); continue
    ph = ",".join("?" * len(tids))
    db_rows = cur.execute(f"""select q.id, q.content, q.q_type, c.name from questions q
                              join chapters c on c.id=q.chapter_id
                              where c.textbook_id in ({ph})""", tids).fetchall()
    total_db += len(db_rows)
    keys = set()
    for _id, content, qtype, cname in db_rows:
        try:
            stem = json.loads(content).get("stem")
        except Exception:
            stem = ""
        keys.add((norm(cname), norm(stem), qtype))
    cnt = 0
    missing = 0
    for ch in d["chapters"]:
        for q in ch["questions"]:
            cnt += 1
            if (norm(ch["name"]), norm(q["stem"]), q["q_type"]) not in keys:
                missing += 1
    total_file += cnt
    if cnt != len(db_rows) or missing:
        bad.append((os.path.basename(p), f"文件 {cnt} / 库 {len(db_rows)} / 查不到 {missing}"))

print(f"册数 {len(books)} / 文件题量 {total_file} / 库内题行 {total_db}")
print("不一致册:", len(bad))
for b in bad[:10]:
    print("  ", b)
print("总表:", dict(zip(("textbooks", "chapters", "knowledge_points", "questions"), (
    cur.execute("select count(*) from textbooks").fetchone()[0],
    cur.execute("select count(*) from chapters").fetchone()[0],
    cur.execute("select count(*) from knowledge_points").fetchone()[0],
    cur.execute("select count(*) from questions").fetchone()[0]))))
print("quick_check:", cur.execute("pragma quick_check").fetchone()[0])
print("fk:", cur.execute("pragma foreign_key_check").fetchall()[:3])
