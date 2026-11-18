# -*- coding: utf-8 -*-
"""骨架纠偏后的库侧清理：删除整册文件中已不存在、但库里仍留存的章节及其题目。

用法：
    python _scope_cleanup.py            # dry-run，只列清单
    python _scope_cleanup.py --apply    # 真正删除（先删题目，再删章节）
"""
import argparse, glob, io, json, os, sqlite3

CT = r"D:\ai\prj\trae\HuaWei\AiLearning\docs\content-templates"
DB = r"D:\ai\prj\trae\HuaWei\AiLearning\backend\ailearning_dev.db"
OUT = os.path.join(CT, "exports", "review_20261112")


def chapter_names_by_book():
    idx = {}
    for p in sorted(glob.glob(os.path.join(CT, "daily_consolidated", "*", "g*", "*_20261113_book.json"))):
        d = json.load(io.open(p, encoding="utf-8"))
        idx[(d["subject"], d["grade"], d["semester"])] = [c["name"] for c in d["chapters"]]
    return idx


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--json-out", default=os.path.join(OUT, "scope_cleanup_20261114.json"))
    a = ap.parse_args()

    idx = chapter_names_by_book()
    con = sqlite3.connect(DB)
    cur = con.cursor()

    plan, total_q, total_c = [], 0, 0
    rows = cur.execute("""
        SELECT c.id, c.name, t.subject, t.grade, t.semester, t.id
        FROM chapters c JOIN textbooks t ON c.textbook_id = t.id
    """).fetchall()
    for cid, cname, subj, grade, sem, tid in rows:
        expect = idx.get((subj, grade, sem))
        if expect is None:
            continue
        if cname not in expect:
            q = cur.execute("SELECT COUNT(*) FROM questions WHERE chapter_id=?", (cid,)).fetchone()[0]
            plan.append({"chapter_id": cid, "chapter": cname, "subject": subj,
                         "grade": grade, "semester": sem, "questions": q})
            total_q += q
            total_c += 1

    before = {t: cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
              for t in ("textbooks", "chapters", "knowledge_points", "questions")}
    print(f"待删章节 {total_c} 个 / 随删题目 {total_q} 道")
    for p in plan:
        print(f"  - {p['subject']} g{p['grade']} {p['semester']}｜{p['chapter']}（题 {p['questions']}）")
    print("库内现状:", before)

    applied = False
    if a.apply and plan:
        for p in plan:
            cur.execute("DELETE FROM questions WHERE chapter_id=?", (p["chapter_id"],))
            cur.execute("DELETE FROM chapters WHERE id=?", (p["chapter_id"],))
        con.commit()
        applied = True
        after = {t: cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                 for t in ("textbooks", "chapters", "knowledge_points", "questions")}
        print("已删除。库内现状:", after)

    out = {"db": DB, "applied": applied, "before": before,
           "after": ({t: cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                      for t in ("textbooks", "chapters", "knowledge_points", "questions")} if applied else before),
           "chapters": plan, "chapter_total": total_c, "question_total": total_q}
    io.open(a.json_out, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    print("报告:", a.json_out)
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
