# -*- coding: utf-8 -*-
"""g1-g9 全学科教研数据合规核实（独立审计，按 20261113 整册文件真实 schema）"""
import json, io, os, sqlite3, collections, datetime

CT   = r"D:\ai\prj\trae\HuaWei\AiLearning\docs\content-templates"
DB   = r"D:\ai\prj\trae\HuaWei\AiLearning\backend\ailearning_dev.db"
MAN  = os.path.join(CT, "exports", "review_20261110", "rerun_manifest_20261113.json")
SKEL = os.path.join(CT, "exports", "review_20261112", "rerun_skeleton_index_g1g9_unified_20261113.json")
OUT  = os.path.join(CT, "exports", "review_20261112")

QTYPES = {"choice", "fill", "judge", "multiple", "answer"}
PLACEHOLDER = ("待补充", "TODO", "TBD", "占位", "待定", "同上", "见教材")
RESIDUE = ("```", "{{", "}}", "undefined", "\ufffd")
LETTERS = "ABCDEFGH"


def load(p):
    return json.load(io.open(p, encoding="utf-8"))


def ans_of(q):
    a = q.get("answer")
    return a.get("value") if isinstance(a, dict) else a


def opt_count(q):
    o = q.get("options")
    return len([x for x in o if str(x).strip()]) if isinstance(o, list) else 0


def letter_ok(letter, n):
    return isinstance(letter, str) and letter.strip().upper() in LETTERS[:n]


m = load(MAN)
skel = load(SKEL)
skel_map = {}
items = skel.get("books") if isinstance(skel, dict) else skel
items = items or (skel.get("packs") if isinstance(skel, dict) else []) or []
for it in items:
    if not isinstance(it, dict):
        continue
    names = it.get("chapters") or it.get("chapter_names") or []
    if isinstance(names, list) and names and isinstance(names[0], dict):
        names = [n.get("name") or n.get("chapter") for n in names]
    skel_map[(it.get("subject"), it.get("grade"), it.get("semester"))] = names

con = sqlite3.connect(DB)
cur = con.cursor()
issues, books, gstems = [], [], collections.defaultdict(set)
total = collections.Counter()

for p in m["packs"]:
    d = load(p["path"])
    s, g, sem = d["subject"], d["grade"], d["semester"]
    bid = f"{s}_g{g}_{sem}"
    chs = d.get("chapters") or []
    kws = d.get("knowledge") or []
    declared = {k["name"] for k in kws if k.get("node_type") == "point"}
    total["books"] += 1
    total["chapters"] += len(chs)
    total["points"] += len(declared)

    exp = skel_map.get((s, g, sem))
    if exp:
        names = [c.get("name") for c in chs]
        miss = [n for n in exp if n not in names]
        extra = [n for n in names if n not in set(exp)]
        if miss:
            issues.append(("ERROR", bid, "SKELETON_MISSING", f"缺 {len(miss)} 章：{miss[:2]}"))
        if extra:
            issues.append(("ERROR", bid, "SKELETON_EXTRA", f"多 {len(extra)} 章：{extra[:2]}"))
    else:
        issues.append(("WARN", bid, "SKELETON_NOT_FOUND", "骨架无该册"))

    nq = 0
    types = collections.Counter()
    diffs = collections.Counter()
    dup = 0
    for ch in chs:
        qs = ch.get("questions") or []
        if not qs:
            issues.append(("ERROR", bid, "CHAPTER_NO_QUESTION", f"章「{ch.get('name')}」无题"))
        seen = collections.Counter()
        for q in qs:
            nq += 1
            qt = q.get("q_type")
            st = (q.get("stem") or "").strip()
            ans = ans_of(q)
            n = opt_count(q)
            types[qt] += 1
            diffs[q.get("difficulty")] += 1
            gstems[st].add(bid)
            seen[(st, qt)] += 1
            if qt not in QTYPES:
                issues.append(("ERROR", bid, "QTYPE_UNKNOWN", f"{qt} / {st[:40]}"))
            short_ok = qt == "judge" and len(st) >= 5 and st.rstrip().endswith(("。", "！", "？"))
            if len(st) < 6 and not short_ok:
                issues.append(("ERROR", bid, "STEM_TOO_SHORT", f"「{st}」"))
            if any(w in st for w in PLACEHOLDER) and not ("待定" in st and "待定系数" in st):
                issues.append(("ERROR", bid, "STEM_PLACEHOLDER", st[:50]))
            if any(w in st for w in RESIDUE):
                issues.append(("ERROR", bid, "STEM_RESIDUE", st[:50]))
            if q.get("knowledge_point") not in declared:
                issues.append(("ERROR", bid, "KP_NOT_DECLARED", f"{q.get('knowledge_point')} / {st[:40]}"))
            if q.get("difficulty") not in (1, 2, 3, 4, 5):
                issues.append(("ERROR", bid, "DIFFICULTY_INVALID", f"{q.get('difficulty')} / {st[:40]}"))
            if qt in ("choice", "multiple"):
                if n < 2:
                    issues.append(("ERROR", bid, "OPTIONS_MISSING", f"{qt} / {st[:40]}"))
                else:
                    if len({str(x) for x in q["options"]}) != len(q["options"]):
                        issues.append(("ERROR", bid, "OPTION_DUPLICATE", f"{len(q['options'])} 项含重复 / {st[:40]}"))
                    if qt == "choice":
                        if not letter_ok(ans, n):
                            issues.append(("ERROR", bid, "CHOICE_ANSWER_INVALID", f"{ans} / {st[:40]}"))
                    else:
                        if not isinstance(ans, list) or len(ans) < 2:
                            issues.append(("ERROR", bid, "MULTIPLE_ANSWER_INVALID", f"{ans} / {st[:40]}"))
                        elif any(not letter_ok(a, n) for a in ans):
                            issues.append(("ERROR", bid, "MULTIPLE_ANSWER_INVALID", f"{ans} / {st[:40]}"))
                        elif len(str(q.get("analysis") or "")) < 15:
                            issues.append(("WARN", bid, "MULTIPLE_ANALYSIS_THIN", st[:40]))
            elif qt == "judge":
                if str(ans).strip().upper() not in ("T", "F"):
                    issues.append(("ERROR", bid, "JUDGE_ANSWER_INVALID", f"{ans} / {st[:40]}"))
            elif qt == "fill":
                empty = ans is None or (isinstance(ans, str) and not ans.strip()) or (
                    isinstance(ans, list) and not [x for x in ans if str(x).strip()])
                if empty:
                    issues.append(("ERROR", bid, "FILL_ANSWER_EMPTY", st[:40]))
            elif qt == "answer":
                if not isinstance(ans, str) or len(ans.strip()) < 8:
                    issues.append(("WARN", bid, "SUBJECTIVE_ANSWER_SHORT", st[:40]))
            if not q.get("analysis") or len(str(q.get("analysis"))) < 4:
                issues.append(("WARN", bid, "ANALYSIS_TOO_SHORT", st[:40]))
        dup += sum(v - 1 for v in seen.values() if v > 1)
    if dup:
        issues.append(("ERROR", bid, "DUP_STEM_IN_CHAPTER", f"{dup} 处重复题干"))
    total["questions"] += nq

    for t in ("choice", "fill", "judge", "multiple", "answer"):
        if types[t] == 0:
            issues.append(("WARN", bid, "TYPE_MISSING", f"缺 {t}"))
    if diffs and (max(diffs) - min(diffs)) < 2:
        issues.append(("WARN", bid, "DIFFICULTY_FLAT", f"难度仅 {min(diffs)}~{max(diffs)}"))

    naked = sorted(n for n in declared
                   if n not in {q.get("knowledge_point") for ch in chs for q in (ch.get("questions") or [])})
    if naked:
        issues.append(("WARN", bid, "POINT_NO_QUESTION", f"{len(naked)} 个知识点无题：{naked[:2]}"))

    tids = [r[0] for r in cur.execute(
        "select id from textbooks where subject=? and grade=? and semester=?", (s, g, sem))]
    if not tids:
        issues.append(("ERROR", bid, "DB_TEXTBOOK_MISSING", "库内无该册教材"))
        db_ch = db_q = 0
    else:
        ph = ",".join("?" * len(tids))
        db_ch = cur.execute(f"select count(*) from chapters where textbook_id in ({ph})", tids).fetchone()[0]
        db_q = cur.execute(f"""select count(*) from questions q join chapters c on c.id=q.chapter_id
                               where c.textbook_id in ({ph})""", tids).fetchone()[0]
        if db_ch != len(chs):
            issues.append(("ERROR", bid, "DB_CHAPTER_MISMATCH", f"库 {db_ch} vs 文件 {len(chs)}"))
        if db_q != nq:
            issues.append(("ERROR", bid, "DB_QUESTION_MISMATCH", f"库 {db_q} vs 文件 {nq}"))

    books.append({"book": bid, "subject": s, "grade": g, "semester": sem,
                  "chapters": len(chs), "points": len(declared), "questions": nq,
                  "types": dict(types),
                  "difficulty": {str(k): v for k, v in sorted(diffs.items(), key=lambda x: (x[0] is None, x[0] or 0))},
                  "db_chapters": db_ch, "db_questions": db_q})

dups = {st: bs for st, bs in gstems.items() if len(bs) > 1 and st}
if dups:
    issues.append(("WARN", "GLOBAL", "DUP_STEM_ACROSS_BOOKS", f"{len(dups)} 个题干在 ≥2 册重复"))

db_cnt = {t: cur.execute(f"select count(*) from {t}").fetchone()[0]
          for t in ("textbooks", "chapters", "knowledge_points", "questions")}
orphan_q = cur.execute("select count(*) from questions q left join chapters c on c.id=q.chapter_id where c.id is null").fetchone()[0]
bad_kp = cur.execute("""select count(*) from questions q left join knowledge_points k on k.id=q.knowledge_point_id
                        where q.knowledge_point_id is not null and k.id is null""").fetchone()[0]
if orphan_q:
    issues.append(("ERROR", "DB", "QUESTION_ORPHAN_CHAPTER", f"{orphan_q} 道题章节不存在"))
if bad_kp:
    issues.append(("ERROR", "DB", "QUESTION_ORPHAN_KP", f"{bad_kp} 道题知识点不存在"))

errs = [i for i in issues if i[0] == "ERROR"]
warns = [i for i in issues if i[0] == "WARN"]
res = {"audit_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
       "scope": "g1-g9 九学科 上下册 92 册（20261113 整册口径）",
       "totals": dict(total), "db_counts": db_cnt,
       "verdict": {"errors": len(errs), "warnings": len(warns)},
       "warn_codes": dict(collections.Counter(c for _, _, c, _ in warns)),
       "error_codes": dict(collections.Counter(c for _, _, c, _ in errs)),
       "books": books,
       "issues": [{"level": lv, "book": b, "code": c, "detail": dd} for lv, b, c, dd in issues]}
io.open(os.path.join(OUT, "compliance_audit_g1g9_20261114.json"), "w", encoding="utf-8").write(
    json.dumps(res, ensure_ascii=False, indent=2))

print("books", total["books"], "chapters", total["chapters"], "points", total["points"], "questions", total["questions"])
print("DB:", db_cnt)
print("errors", len(errs), "warnings", len(warns))
print("error codes:", dict(collections.Counter(c for _, _, c, _ in errs)))
print("warn codes:", dict(collections.Counter(c for _, _, c, _ in warns)))
print("--- ERROR 明细（最多 25）---")
for lv, b, c, dd in errs[:25]:
    print(" ", b, c, dd)
print("--- 抽样规模 ---")
for b in books[:4]:
    print(" ", b["book"], "章", b["chapters"], "点", b["points"], "题", b["questions"],
          "库", b["db_chapters"], b["db_questions"], b["types"])
