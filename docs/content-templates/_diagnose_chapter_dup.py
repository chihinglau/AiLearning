# -*- coding: utf-8 -*-
"""诊断：同一学科同一年级，上下册是否出现同名同章（骨架层面的重复）。"""
import glob, io, json, os, re, collections

CT = r"D:\ai\prj\trae\HuaWei\AiLearning\docs\content-templates"
SKEL = os.path.join(CT, "exports", "review_20261112",
                    "rerun_skeleton_index_g1g9_unified_20261113.json")


def norm(s):
    return re.sub(r"\s+", "", str(s or ""))


sk = json.load(io.open(SKEL, encoding="utf-8"))
print("骨架顶层键:", list(sk.keys())[:10])
books = sk.get("books") or sk.get("packs") or []
print("骨架册数:", len(books), "| 首册字段:", list(books[0].keys()) if books else None)

bykey = collections.defaultdict(dict)
for b in books:
    names = b.get("chapters") or b.get("chapter_names") or []
    if names and isinstance(names[0], dict):
        names = [n.get("name") or n.get("chapter") for n in names]
    bykey[(b.get("subject"), b.get("grade"))][b.get("semester")] = names

print("\n=== 上下册同名同章 ===")
for (s, g), sem in sorted(bykey.items()):
    first, second = sem.get("first") or [], sem.get("second") or []
    if not first or not second:
        continue
    fset = {norm(x): x for x in first if x}
    dup = [x for x in second if norm(x) in fset]
    if dup:
        print(f"{s} g{g}: 上册 {len(first)} 章 / 下册 {len(second)} 章 / 同名 {len(dup)} 章")
        for x in dup:
            print("    -", x)

print("\n=== 整册文件侧同样的检查（按 daily_consolidated 实测）===")
files = sorted(glob.glob(os.path.join(CT, "daily_consolidated", "*", "g*", "*_20261113_book.json")))
idx = collections.defaultdict(dict)
for p in files:
    d = json.load(io.open(p, encoding="utf-8"))
    idx[(d["subject"], d["grade"])][d["semester"]] = [c["name"] for c in d["chapters"]]
for (s, g), sem in sorted(idx.items()):
    first, second = sem.get("first") or [], sem.get("second") or []
    dups = sorted({norm(x) for x in second} & {norm(x) for x in first})
    if dups:
        print(f"{s} g{g}: 上册 {len(first)} / 下册 {len(second)} / 同名 {len(dups)}: {dups}")
