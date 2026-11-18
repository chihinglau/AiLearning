# -*- coding: utf-8 -*-
"""按当前整册文件反查库内「已无对应」的旧题行（dry-run / --apply）。

判据：题行 (chapter_id, stem, q_type) 不在当日整册文件集合内 → 视为 stale。
只处理 92 册范围内（按 textbook: subject+grade+semester 定位）。
"""
import argparse, glob, io, json, os, re, sqlite3

CT = r"D:\ai\prj\trae\HuaWei\AiLearning\docs\content-templates"
DB = r"D:\ai\prj\trae\HuaWei\AiLearning\backend\ailearning_dev.db"
OUT = os.path.join(CT, "exports", "review_20261112")
REF_TABLES = (("student_question_records", "question_id"),
              ("wrong_questions", "question_id"),
              ("exam_answers", "question_id"))


def norm(s: str) -> str:
    return re.sub(r"\s+", "", str(s or ""))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--json-out", default=os.path.join(OUT, "stale_after_p123_20261114.json"))
    args = ap.parse_args()

    con = sqlite3.connect(DB)
    cur = con.cursor()
    books = sorted(glob.glob(os.path.join(CT, "daily_consolidated", "*", "g*", "*_20261113_book.json"))
                   or glob.glob(os.path.join(CT, "daily_rerun", "*", "g*", "*_20261113_book.json")))

    expected: dict[int, set] = {}
    for p in books:
        d = json.load(io.open(p, encoding="utf-8"))
        s, g, sem = d["subject"], d["grade"], d["semester"]
        tids = [r[0] for r in cur.execute(
            "select id from textbooks where subject=? and grade=? and semester=?", (s, g, sem))]
        if not tids:
            print(f"[警告] 库内无对应教材：{s} g{g} {sem}")
            continue
        chs = cur.execute(
            f"select id, name from chapters where textbook_id in ({','.join('?' * len(tids))})", tids).fetchall()
        chmap = {}
        for cid, cname in chs:
            chmap.setdefault(norm(cname), []).append(cid)
        for ch in d["chapters"]:
            cand = chmap.get(norm(ch["name"])) or []
            for cid in cand:
                bucket = expected.setdefault(cid, set())
                for q in ch["questions"]:
                    bucket.add((norm(q["stem"]), q["q_type"]))

    stale, scoped = [], 0
    tids_all = sorted({t for t in expected})
    for cid in tids_all:
        rows = cur.execute("select id, content, q_type, status from questions where chapter_id=?",
                           (cid,)).fetchall()
        scoped += len(rows)
        for qid, content, qtype, status in rows:
            try:
                stem = json.loads(content).get("stem") if content else ""
            except Exception:
                stem = ""
            if (norm(stem), qtype) not in expected[cid]:
                stale.append({"id": qid, "chapter_id": cid, "q_type": qtype,
                              "status": status, "stem": str(stem)[:60]})

    ref = set()
    for t, col in REF_TABLES:
        try:
            cur.execute(f"select {col} from {t}")
        except sqlite3.Error:
            continue
        ref |= {r[0] for r in cur.fetchall() if r[0]}
    stale_ids = [s["id"] for s in stale if s["id"] not in ref]
    stale_ref = [s["id"] for s in stale if s["id"] in ref]

    print(f"整册 {len(books)} 份 / 库内本章题行 {scoped} / stale {len(stale)}（其中被引用 {len(stale_ref)})")
    for s in stale[:20]:
        print("   -", s["id"], s["q_type"], s["stem"])

    res = {"books": len(books), "scoped_rows": scoped, "stale": len(stale),
           "stale_referenced": len(stale_ref), "ids": stale_ids,
           "referenced_ids": stale_ref, "applied": False, "detail": stale}
    if args.apply and stale_ids:
        before = cur.execute("select count(*) from questions").fetchone()[0]
        cur.execute("begin")
        cur.executemany("delete from questions where id=?", [(i,) for i in stale_ids])
        cur.execute("commit")
        after = cur.execute("select count(*) from questions").fetchone()[0]
        res.update({"applied": True, "before": before, "after": after,
                    "quick_check": cur.execute("pragma quick_check").fetchone()[0],
                    "fk_violations": cur.execute("pragma foreign_key_check").fetchall()[:5]})
        print(f"questions: {before} -> {after}（删 {before - after}）")
        print("quick_check:", res["quick_check"], "| fk:", res["fk_violations"])
    os.makedirs(os.path.dirname(args.json_out), exist_ok=True)
    io.open(args.json_out, "w", encoding="utf-8").write(json.dumps(res, ensure_ascii=False, indent=2))
    print("报告:", args.json_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
