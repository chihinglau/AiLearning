"""整册归集器：把 `_rN` 分片按章节归位，输出「一册一文件」的归集方案（默认只出方案，不写产物）。

背景（2026-11-09 g1/g8 上册评审结论）：
- 同一批次日期下并存 `_r1.._rN` 分片，每个文件 chapters 长度只有 1；
- `_import-manifest.json` 的键是「不带 _r 后缀」的那份，所以分片从来没进过库；
- 12 册文件里躺着 2078 道题，库内只有 326 道，70 个章节里 54 个 0 题。

用法（在任意目录执行）：
    python _consolidate_daily.py                      # 只出方案（默认，不改任何文件）
    python _consolidate_daily.py --out plan.json --md plan.md
    python _consolidate_daily.py --apply              # 真正写出 daily_consolidated/ 下的整册文件

按学科年级限定范围（2026-11-09 新增，支撑 46 个年级逐批推进）：
    python _consolidate_daily.py --subjects math,chinese --grades 1-9 --apply
    python _consolidate_daily.py --subjects english --grades 8 --semester second --stamp 20261201 --apply
    不传 --subjects/--grades 时仍按历史默认 12 册（g1+g8 上册），行为与改造前一致。

裁定规则（写进 04 手册，可复核）：
1. 同一章节多份并存时，优先「不带 _legacy」；其次「批次日期最新」；再次题量最多；最后 mtime 最新；
2. 分片文件一律不改名、不删除，只在方案里标注它归到哪一章；
3. 章节名不在教材骨架里的（legacy 旧样章）不并入整册文件，单列「越界章节」等人工决定。
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
from datetime import datetime
from pathlib import Path

CT = Path(__file__).resolve().parent
SKELETON_DIR = CT / "baseline" / "_skeleton_first"
PAIRS = [
    ("math", 1), ("chinese", 1), ("english", 1), ("politics", 1),
    ("math", 8), ("chinese", 8), ("english", 8), ("politics", 8),
    ("physics", 8), ("biology", 8), ("geography", 8), ("history", 8),
]
_FRAG_RE = re.compile(r"_r(\d+)\.json$", re.IGNORECASE)


def skeleton_chapters(subject: str, grade: int, semester: str = "first") -> list[str]:
    path = SKELETON_DIR / f"chapters_{subject}_g{grade}_{semester}_20261107.json"
    if not path.is_file():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    items = raw.get("chapters") if isinstance(raw, dict) else raw
    names = []
    for item in items or []:
        if isinstance(item, dict):
            names.append(str(item.get("name") or "").strip())
        else:
            names.append(str(item).strip())
    return [n for n in names if n]


def collect(subject: str, grade: int, semester: str = "first") -> tuple[list[dict], list[str]]:
    """返回 (章节候选清单, 待处理文件名)。只收指定学期的文件，避免上册整册混进下册内容。"""
    pattern = str(CT / "daily" / subject / f"g{grade}" /
                  f"{subject}_g{grade}_{semester}_*.json")
    chapters: dict[str, list[dict]] = {}
    files: list[str] = []
    for path_str in sorted(glob.glob(pattern)):
        path = Path(path_str)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        files.append(path.name)
        for chapter in data.get("chapters") or []:
            name = str(chapter.get("name") or "").strip()
            if not name:
                continue
            chapters.setdefault(name, []).append({
                "file": path.name,
                "fragment": bool(_FRAG_RE.search(path.name)),
                "legacy": bool(data.get("_legacy")),
                "questions": len(chapter.get("questions") or []),
                "points": len([k for k in data.get("knowledge") or []
                               if isinstance(k, dict) and k.get("node_type", "point") == "point"]),
                "mtime": datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                "mtime_ts": path.stat().st_mtime,
                "chapter": chapter,
                "knowledge": data.get("knowledge") or [],
                "top": {k: data.get(k) for k in ("subject", "grade", "version", "semester")},
            })
    return chapters, files


def _batch_date(name: str) -> int:
    match = re.search(r"_(20\d{6})", name)
    return int(match.group(1)) if match else 0


def pick(versions: list[dict]) -> tuple[dict, str]:
    ordered = sorted(
        versions,
        key=lambda v: (not v["legacy"], _batch_date(v["file"]), v["questions"], v["mtime_ts"]),
        reverse=True,
    )
    winner = ordered[0]
    reasons = []
    if any(v["legacy"] for v in versions) and not winner["legacy"]:
        reasons.append("优先非 legacy")
    dates = {_batch_date(v["file"]) for v in versions}
    if len(dates) > 1:
        reasons.append(f"批次最新（{_batch_date(winner['file'])}）")
    if len({v["questions"] for v in versions}) > 1:
        reasons.append(f"题量最多（{winner['questions']} 道）")
    if len(versions) > 1:
        reasons.append(f"mtime 最新（{winner['mtime']}）")
    return winner, "；".join(reasons) or "唯一版本"


def build_plan(pairs: list[tuple[str, int]] | None = None, semester: str = "first") -> dict:
    books = []
    for subject, grade in (pairs or PAIRS):
        chapters, files = collect(subject, grade, semester)
        official = skeleton_chapters(subject, grade, semester)
        entries = []
        for name, versions in sorted(chapters.items(), key=lambda kv: min(
                (v["chapter"].get("order_index") or 99) for v in kv[1])):
            winner, reason = pick(versions)
            entries.append({
                "name": name,
                "order_index": winner["chapter"].get("order_index"),
                "in_outline": name in official,
                "winner_file": winner["file"],
                "reason": reason,
                "questions": winner["questions"],
                "versions": [
                    {k: v[k] for k in ("file", "fragment", "legacy", "questions", "points", "mtime")}
                    for v in sorted(versions, key=lambda v: v["mtime_ts"], reverse=True)
                ],
            })
        covered = {e["name"] for e in entries if e["in_outline"]}
        missing = [name for name in official if name not in covered]
        books.append({
            "subject": subject,
            "grade": grade,
            "semester": semester,
            "files": files,
            "fragment_files": len([f for f in files if _FRAG_RE.search(f)]),
            "official_chapters": len(official),
            "covered_official": len(covered),
            "missing_chapters": missing,
            "outside_outline": [e["name"] for e in entries if not e["in_outline"]],
            "duplicated_chapters": [e["name"] for e in entries if len(e["versions"]) > 1],
            "questions_after_merge": sum(e["questions"] for e in entries if e["in_outline"]),
            "chapters": entries,
        })
    return {
        "schema": "consolidation-plan/1",
        "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "semester": semester,
        "pairs": f"{len(books)} 册",
        "rule": "非 legacy > 批次日期最新 > 题量最多 > mtime 最新；分片不改名不删除；越界章节不并入；"
                "库内已存在的知识点不在整册里重复声明；空节（既无点也无题）归集时剔除",
        "books": books,
    }


def render_md(plan: dict) -> str:
    lines = ["# 整册归集方案（只出方案，未改任何文件）", "",
             f"生成时间：{plan['generated_at']}", "", plan["rule"], "",
             "| 册 | 文件数 | 分片数 | 官方章 | 已覆盖 | 缺章 | 多版本章 | 越界章 | 归集后题量 |",
             "|---|---|---|---|---|---|---|---|---|"]
    for b in plan["books"]:
        lines.append(
            f"| {b['subject']}/g{b['grade']} | {len(b['files'])} | {b['fragment_files']} | "
            f"{b['official_chapters']} | {b['covered_official']} | {len(b['missing_chapters'])} | "
            f"{len(b['duplicated_chapters'])} | {len(b['outside_outline'])} | {b['questions_after_merge']} |"
        )
    for b in plan["books"]:
        lines += ["", f"## {b['subject']} / g{b['grade']}", ""]
        if b["missing_chapters"]:
            lines.append("缺章：" + "、".join(b["missing_chapters"]))
        if b["outside_outline"]:
            lines.append("越界章节（legacy 旧样章，不并入）：" + "、".join(b["outside_outline"]))
        if b["duplicated_chapters"]:
            lines.append("")
            lines.append("多版本章裁定：")
            for entry in b["chapters"]:
                if len(entry["versions"]) == 1:
                    continue
                names = " / ".join(
                    f"{v['file']}({v['questions']}题{'，legacy' if v['legacy'] else ''}，{v['mtime']})"
                    for v in entry["versions"]
                )
                lines.append(f"- 「{entry['name']}」→ 取 {entry['winner_file']}（{entry['reason']}）；候选：{names}")
    return "\n".join(lines) + "\n"


def baseline_names(subject: str, grade: int) -> dict[str, int]:
    """库内已存在的知识点名（`baseline/_knowledge-points-baseline_latest.json` 只读）。"""
    path = CT / "baseline" / "_knowledge-points-baseline_latest.json"
    if not path.is_file():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    names = (raw.get("names") or {}).get(subject, {})
    return names.get(str(grade)) or {}


def apply_plan(plan: dict, out_root: Path | None = None, stamp: str | None = None,
               semester: str = "first") -> list[str]:
    """把裁定后的章节写成一册一文件（默认目录 daily_consolidated，不动 daily 原文件）。

    整册文件与「当日批次文件」的差别（2026-11-09 校准时踩到的两个坑）：
    1. 整册会把全书知识点一次声明完，而其中绝大多数**库里已经存在**——重复声明会被
       导入器判成「同名覆盖」，所以已存在的知识点不再声明，只让题目按旧名挂载；
    2. r3/r4 里「既无知识点也无题」的空节不能带进整册（否则整册一导入就造空节），
       归集时剔除并记进 `_consolidated.dropped_sections`。
    """
    written = []
    out_root = out_root or (CT / "daily_consolidated")
    stamp = stamp or f"{datetime.now():%Y%m%d}"
    cache: dict[tuple[str, int], dict[str, list[dict]]] = {}
    for b in plan["books"]:
        subject, grade = b["subject"], b["grade"]
        key = (subject, grade)
        if key not in cache:
            cache[key] = collect(subject, grade, semester)[0]
        existing = baseline_names(subject, grade)
        chapters, knowledge, top = [], [], None
        seen_points = set()
        sources, dropped, reused = [], [], []
        for entry in b["chapters"]:
            if not entry["in_outline"]:
                continue
            source = next((v for v in cache[key].get(entry["name"], [])
                           if v["file"] == entry["winner_file"]), None)
            if source is None:
                continue
            top = top or source["top"]
            chapters.append(source["chapter"])
            sources.append({"chapter": entry["name"], "file": entry["winner_file"],
                            "questions": entry["questions"]})
            dropped_here = []
            for item in source["knowledge"]:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("name") or "").strip()
                node_type = item.get("node_type", "point")
                if node_type == "section":
                    per_section = [k for k in source["knowledge"]
                                   if isinstance(k, dict) and k.get("node_type", "point") == "point"
                                   and str(k.get("parent") or "").strip() == name]
                    direct = [q for q in (source["chapter"].get("questions") or [])
                              if str(q.get("knowledge_point") or "").strip() == name]
                    if not per_section and not direct:
                        dropped_here.append(name)
                        continue
                else:
                    if existing.get(name):
                        reused.append(name)
                        continue
                dedupe = (node_type, name)
                if dedupe in seen_points:
                    continue
                seen_points.add(dedupe)
                knowledge.append(item)
            if dropped_here:
                dropped.append({"chapter": entry["name"], "sections": dropped_here})
        if not chapters:
            continue
        # 复名知识点不声明之后，可能出现「整节的知识点都因同名被跳过」的空节 —— 一起剔除，
        # 否则整册一导入就造空节（校验器会判错，确实也不该入库）。
        parents_with_points = {
            str(item.get("parent") or "").strip()
            for item in knowledge
            if item.get("node_type", "point") == "point"
        }
        question_targets = set()
        for chapter in chapters:
            for question in chapter.get("questions") or []:
                question_targets.add(str(question.get("knowledge_point") or "").strip())
        kept_sections = []
        for item in knowledge:
            if item.get("node_type") == "section":
                name = str(item.get("name") or "").strip()
                if name not in parents_with_points and name not in question_targets:
                    dropped.append({"chapter": "（复名知识点不声明后变空）", "sections": [name]})
                    continue
            kept_sections.append(item)
        knowledge = kept_sections
        doc = dict(top or {})
        doc["knowledge"] = knowledge
        doc["chapters"] = chapters
        doc["_consolidated"] = {
            "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "rule": "非 legacy > 批次日期最新 > 题量最多 > mtime 最新",
            "sources": sources,
            "dropped_sections": dropped,
            "reused_point_names_not_redeclared": reused,
            "outside_outline_skipped": [e["name"] for e in b["chapters"] if not e["in_outline"]],
        }
        target = out_root / subject / f"g{grade}"
        target.mkdir(parents=True, exist_ok=True)
        path = target / f"{subject}_g{grade}_{semester}_{stamp}_book.json"
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        written.append(f"{path}（章 {len(chapters)} / 知识点 {len(knowledge)} / 复名不声明 {len(reused)} / 剔除空节 "
                       f"{sum(len(d['sections']) for d in dropped)}）")
    return written


def parse_pairs(subjects: str | None, grades: str | None) -> list[tuple[str, int]]:
    """--subjects + --grades → [(subject, grade)]；都不传时用默认 12 册（g1/g8 上册）。"""
    if not subjects and not grades:
        return list(PAIRS)
    subs = [s.strip() for s in (subjects or "").split(",") if s.strip()]
    if not subs:
        subs = sorted({s for s, _ in PAIRS})
    out = []
    spec = (grades or "1,8").strip()
    for sub in subs:
        gs: list[int] = []
        for part in spec.split(","):
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                lo, hi = (int(x) for x in part.split("-", 1))
                gs.extend(range(lo, hi + 1))
            else:
                gs.append(int(part))
        for grade in sorted(set(gs)):
            out.append((sub, grade))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="整册归集方案（默认 dry-run）")
    parser.add_argument("--out", help="方案 JSON 输出路径")
    parser.add_argument("--md", help="方案 Markdown 输出路径")
    parser.add_argument("--apply", action="store_true", help="真正写出整册文件（不写则只出方案）")
    parser.add_argument("--semester", default="first", choices=["first", "second"],
                        help="学期，默认 first（只收该学期的 daily 文件，避免上下册混册）")
    parser.add_argument("--subjects", help="逗号分隔学科，如 math,chinese；配合 --grades 限定本次范围")
    parser.add_argument("--grades", help="年级范围，如 1-9 或 1,8；配合 --subjects 使用")
    parser.add_argument("--stamp", help="整册文件名里的批次日期 YYYYMMDD，默认今天（同一天重跑会覆盖同名文件）")
    parser.add_argument("--out-dir", help="整册输出目录，默认 <CT>\\daily_consolidated")
    args = parser.parse_args()

    pairs = parse_pairs(args.subjects, args.grades)
    plan = build_plan(pairs, args.semester)
    if args.out:
        Path(args.out).write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.md:
        Path(args.md).write_text(render_md(plan), encoding="utf-8")
    if not args.out and not args.md:
        print(render_md(plan))

    total_q = sum(b["questions_after_merge"] for b in plan["books"])
    total_missing = sum(len(b["missing_chapters"]) for b in plan["books"])
    total_dup = sum(len(b["duplicated_chapters"]) for b in plan["books"])
    print(f"[方案] {len(plan['books'])} 册（semester={args.semester}），归集后题量 {total_q} 道，"
          f"缺章 {total_missing} 个，多版本章 {total_dup} 个")

    if args.apply:
        written = apply_plan(plan, Path(args.out_dir) if args.out_dir else None,
                             args.stamp, args.semester)
        for path in written:
            print(f"[写入] {path}")
    else:
        print("[dry-run] 未写任何文件；要生成整册文件请加 --apply")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
