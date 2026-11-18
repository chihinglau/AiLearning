# -*- coding: utf-8 -*-
"""骨架纠偏：physics g9 下册误用上册 10 章，按人教版分册改为上册 13–18、下册 19–22。"""
import io, json, os, shutil, datetime

CT = r"D:\ai\prj\trae\HuaWei\AiLearning\docs\content-templates"
SKEL = os.path.join(CT, "exports", "review_20261112",
                    "rerun_skeleton_index_g1g9_unified_20261113.json")

SCOPE = {
    "first": ["第十三章 内能", "第十四章 内能的利用", "第十五章 电流和电路",
              "第十六章 电压 电阻", "第十七章 欧姆定律", "第十八章 电功率"],
    "second": ["第十九章 生活用电", "第二十章 电与磁",
               "第二十一章 电磁波及其应用", "第二十二章 能源与可持续发展"],
}

d = json.load(io.open(SKEL, encoding="utf-8"))
bak = SKEL.replace(".json", f"_bak_{datetime.datetime.now():%Y%m%d%H%M%S}.json")
shutil.copy2(SKEL, bak)
print("备份:", os.path.basename(bak))

changed = []
for b in d["books"]:
    if b.get("subject") != "physics" or b.get("grade") != 9:
        continue
    sem = b.get("semester")
    new = SCOPE.get(sem)
    if not new:
        continue
    old = list(b.get("chapters") or [])
    b["chapters"] = new
    b["chapter_count"] = len(new)
    b["source"] = (b.get("source") or "") + "｜2026-11-14 分册纠偏（原误用上册 10 章，按人教版分册拆分）"
    changed.append((b.get("book"), sem, len(old), len(new)))

note = d.get("note") or ""
d["note"] = note + ("｜2026-11-14 骨架纠偏：physics g9 下册章节由「上册 10 章整份复制」改为 19–22 章，"
                    "上册限定 13–18 章（统一骨架范围不变，仍为 g1–g9 上下册 92 册）")
io.open(SKEL, "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=False, indent=2) + "\n")
for c in changed:
    print("已修正:", c)
print("骨架册数:", len(d["books"]))
