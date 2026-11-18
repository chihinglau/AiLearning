# -*- coding: utf-8 -*-
"""整改后仍同题但被前缀掩盖的重复检测：剥前缀后按 (题干, 题型) 比对跨册重复。"""
import glob, io, json, os, re, collections

CT = r"D:\ai\prj\trae\HuaWei\AiLearning\docs\content-templates"
PREFIX = re.compile(r"^（[^）]{0,40}）")
MAN = os.path.join(CT, "exports", "review_20261110", "rerun_manifest_20261113.json")


def norm(s):
    return re.sub(r"\s+", "", str(s or ""))


def bare(stem):
    return PREFIX.sub("", str(stem or "").strip())


m = json.load(io.open(MAN, encoding="utf-8"))
groups = collections.defaultdict(list)
for p in m["packs"]:
    d = json.load(io.open(p["path"], encoding="utf-8"))
    bid = f"{d['subject']}_g{d['grade']}_{d['semester']}"
    for ch in d["chapters"]:
        for q in ch["questions"]:
            groups[(norm(bare(q["stem"])), q["q_type"])].append(
                {"book": bid, "subject": d["subject"], "grade": d["grade"],
                 "semester": d["semester"], "chapter": ch["name"], "stem": q["stem"]})

dups = {k: v for k, v in groups.items() if len(v) > 1}
print("跨册同题组数:", len(dups), "涉及题行:", sum(len(v) for v in dups.values()))
rel = collections.Counter()
for k, v in dups.items():
    books_subj = {x["subject"] for x in v}
    books_grade = {x["grade"] for x in v}
    if len(books_subj) > 1:
        tag = "跨学科"
    elif len(books_grade) > 1:
        tag = "跨年级同学科"
    else:
        tag = "同年级同学科跨册"
    rel[tag] += 1
    print(f"\n[{tag}] {k[1]} | {v[0]['stem'][:56]}")
    for x in v:
        print(f"    - {x['book']} / {x['chapter']}")

out = {"groups": [{"key": list(k), "rel": ("跨学科" if len({x['subject'] for x in v}) > 1 else
                                       "跨年级同学科" if len({x['grade'] for x in v}) > 1 else "同年级同学科跨册"),
                   "items": v} for k, v in dups.items()]}
io.open(os.path.join(CT, "exports", "review_20261112", "same_content_after_prefix_20261114.json"),
        "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=2))
print("\n分类:", dict(rel))
print("明细: exports/review_20261112/same_content_after_prefix_20261114.json")
