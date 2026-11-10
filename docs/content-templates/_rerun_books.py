# -*- coding: utf-8 -*-
"""34 册重跑组装器（2026-11-10 评审 §九-③）：内容包 → 待评审整册 JSON。

设计约束（评审 P2 / P3 / 复评 §九）：
- 「按年级知识点表」生成：每个内容包自带 chapters[].points（节级、可测量的知识点名），
  绝不按章节名套模板；每点 >= 4 题；
- 产出写到 daily_rerun/ 的待评审区，**不写 daily_consolidated/**、不改隔离名单、不入库；
  文件名仍以 _book.json 结尾，使 _validate_daily.py 按整册规格校验；
- 组装前本地自检：题干唯一（全册）、负面清单、多选题解析字母齐备、每点题量、难度范围；
  任一不合格即拒写并报错；
- 另输出知识点表 rerun_knowledge_map_<stamp>.json 与批次清单 rerun_manifest_<stamp>.json，
  供重跑结果评审逐册核对。

内容包格式（docs/content-templates/rerun_packs/<subject>_g<grade>.py）：

    PACK = {
      "subject": "...", "grade": N, "version": "...", "semester": "first",
      "chapters": [
        {"name": "<教材骨架里的章名>", "summary": "<本章内容摘要>",
         "points": [
           {"name": "<节级可测量知识点>", "explanation": "<知识讲解>",
            "questions": [
              ("choice", "题干", ["A项","B项","C项","D项"], "A", "解析", 1),
              ("fill",   "题干", None, "答案" 或 ["答案1","答案2"], "解析", 2),
              ("judge",  "题干", None, "T" 或 "F", "解析", 2),
              ("answer", "题干", None, "参考答案", "评分要点", 4),
              ("multiple","题干", ["A项","B项","C项","D项"], ["A","C"],
               "逐项判断：A … ✓；B … ✗；C … ✓；D … ✗。所以选 A、C。", 3),
            ]},
           ]},
      ],
    }

用法：
    python _rerun_books.py --check                 # 只自检全部内容包，不落盘
    python _rerun_books.py --pack biology_g7      # 只组装一册
    python _rerun_books.py                        # 组装全部已登记内容包
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CT = Path(__file__).resolve().parent
PACKS = CT / "rerun_packs"
OUT = CT / "daily_rerun"
REVIEW = CT / "exports" / "review_20261110"
TASKS_JSON = CT / "exports" / "automation_20261108_codebuddy" / "tasks.json"
SKELETON_INDEX = REVIEW / "rerun_skeleton_index_20261110.json"
Q_TYPES = {"choice", "multiple", "judge", "fill", "answer"}


def skeleton_chapter_names(subject: str, grade: int) -> list[str] | None:
    """官方章节骨架；返回 None 表示索引不存在（跳过该检查）。"""
    if not SKELETON_INDEX.is_file():
        return None
    try:
        data = json.loads(SKELETON_INDEX.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    for book in data.get("books", []):
        if book.get("subject") == subject and book.get("grade") == grade:
            return [str(c) for c in book.get("chapters", [])]
    return []


def load_packs(only: str | None = None) -> list[tuple[Path, dict]]:
    if not PACKS.is_dir():
        return []
    out = []
    for f in sorted(PACKS.glob("*.py")):
        if f.name.startswith("_"):
            continue
        if only and f.stem != only:
            continue
        spec = importlib.util.spec_from_file_location(f.stem, f)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        pack = getattr(mod, "PACK", None)
        if not isinstance(pack, dict):
            print(f"[错误] {f.name} 没有 PACK 字典", file=sys.stderr)
            sys.exit(1)
        out.append((f, pack))
    return out


def negative_stems() -> list[str]:
    try:
        pol = json.loads(TASKS_JSON.read_text(encoding="utf-8")).get("policy") or {}
        return list((pol.get("book_acceptance_gate") or {}).get("negative_stems") or [])
    except (OSError, json.JSONDecodeError):
        return ["更可取的学习做法", "可以先梳理", "举一个生活中用到",
                "结合实例分析比单纯背诵", "值得提倡的", "·概念理解", "·认知"]


def self_check(pack: dict) -> tuple[list[str], dict]:
    """返回 (错误列表, 统计)；本地自检不合格的册绝不落盘。"""
    errors = []
    neg = negative_stems()
    subject, grade = pack.get("subject"), pack.get("grade")
    chapters = pack.get("chapters") or []
    if not subject or not isinstance(grade, int) or not chapters:
        return ["缺少 subject/grade/chapters"], {}
    expected = skeleton_chapter_names(subject, grade)
    if expected is not None:
        actual = [str(c.get("name") or "").strip() for c in chapters]
        if actual != expected:
            errors.append(f"章名与官方骨架不一致：期望 {expected}，实际 {actual}")
    seen: dict[tuple[str, str], str] = {}
    point_names: set[str] = set()
    total = 0
    for ci, ch in enumerate(chapters, 1):
        cname = str(ch.get("name") or "").strip()
        if not cname:
            errors.append(f"第 {ci} 章缺 name")
        points = ch.get("points") or []
        if len(points) < 4:
            errors.append(f"章「{cname}」只有 {len(points)} 个点（要求每章 4-6 个）")
        for p in points:
            pname = str(p.get("name") or "").strip()
            if not pname:
                errors.append(f"章「{cname}」存在空知识点名")
                continue
            if pname in point_names:
                errors.append(f"知识点「{pname}」在本册重复声明")
            point_names.add(pname)
            if any(x in pname for x in ("·概念理解", "·认知", "·概念", "·理解")):
                errors.append(f"知识点「{pname}」是占位后缀名，不是可测量知识")
            qs = p.get("questions") or []
            if len(qs) < 4:
                errors.append(f"点「{pname}」只有 {len(qs)} 题（要求 >= 4）")
            for tup in qs:
                if not isinstance(tup, (list, tuple)) or len(tup) != 6:
                    errors.append(f"点「{pname}」题目元组格式错误：{tup!r}"[:120])
                    continue
                qtype, stem, options, ans, analysis, diff = tup
                stem = str(stem or "").strip()
                total += 1
                if qtype not in Q_TYPES:
                    errors.append(f"点「{pname}」题型非法 {qtype}")
                if not stem:
                    errors.append(f"点「{pname}」存在空题干")
                key = (str(qtype), stem)
                if key in seen:
                    errors.append(f"全册重复题干（{seen[key]} → {cname}）：{stem[:40]}")
                seen[key] = cname
                if any(x in stem for x in neg):
                    errors.append(f"题干命中负面清单：{stem[:40]}")
                # _validate_daily.py 的硬规则：题干不能引用客户端渲染不出的图表。
                # 注意是子串匹配，「地图上表示」也会命中「上表」，故一并在此拦截。
                for bad in ("如图", "上题", "上表", "见下图"):
                    if bad in stem:
                        errors.append(f"题干含校验器禁用指代「{bad}」：{stem[:40]}")
                        break
                if not isinstance(diff, int) or not 1 <= diff <= 5:
                    errors.append(f"题「{stem[:24]}」难度非法 {diff}")
                if qtype in ("choice", "multiple"):
                    if not options or len(options) != 4:
                        errors.append(f"题「{stem[:24]}」选项数 != 4")
                    letters = [chr(65 + i) for i in range(len(options or []))]
                    if qtype == "multiple":
                        if not all(L in str(analysis) for L in letters) or "✓" not in str(analysis) or "✗" not in str(analysis):
                            errors.append(f"多选题「{stem[:24]}」解析未逐项写 A/B/C/D 与 ✓/✗")
                        if not isinstance(ans, list) or not ans or any(L not in letters for L in ans):
                            errors.append(f"多选题「{stem[:24]}」answer 必须是字母数组")
                    elif ans not in letters:
                        errors.append(f"单选题「{stem[:24]}」答案不是有效字母")
                if qtype == "judge" and ans not in ("T", "F"):
                    errors.append(f"判断题「{stem[:24]}」答案必须是 T/F")
                if qtype in ("fill", "answer") and not ans:
                    errors.append(f"题「{stem[:24]}」缺答案")
                if not analysis:
                    errors.append(f"题「{stem[:24]}」缺解析")
    stats = {"chapters": len(chapters), "points": len(point_names), "questions": total}
    return errors, stats


def build_doc(pack: dict) -> dict:
    knowledge, chapters = [], []
    for i, ch in enumerate(pack["chapters"], 1):
        cname = ch["name"]
        knowledge.append({"node_type": "section", "name": cname, "order_index": i})
        questions = []
        for j, p in enumerate(ch["points"], 1):
            pname = p["name"]
            knowledge.append({
                "node_type": "point", "name": pname, "parent": cname, "order_index": j,
                "explanation": p.get("explanation") or "", "prerequisites": [],
                "weight": 1.2, "source_type": "original", "source_name": "教研组自编",
            })
            for tup in p["questions"]:
                qtype, stem, options, ans, analysis, diff = tup
                q = {
                    "q_type": qtype, "stem": stem,
                    "answer": {"value": ans}, "analysis": analysis,
                    "difficulty": diff, "knowledge_point": pname,
                    "source_type": "original", "source_name": "教研组自编",
                    "status": "published",
                }
                if options:
                    q["options"] = list(options)
                questions.append(q)
        chapters.append({
            "name": cname, "order_index": i,
            "summary": ch.get("summary") or f"{cname}：本章核心概念、规律与应用。",
            "questions": questions,
        })
    return {
        "subject": pack["subject"], "grade": pack["grade"],
        "version": pack["version"], "semester": pack["semester"],
        "knowledge": knowledge, "chapters": chapters,
        "_rerun": {
            "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "source": "docs/content-templates/_rerun_books.py + rerun_packs/*.py",
            "review": "exports/review_20261110/daily_consolidated-评审_20261110.md §九-③",
            "status": "pending_review（待评审，不在 daily_consolidated，不入库）",
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="重跑内容包 → 待评审整册（不入库）")
    ap.add_argument("--pack", help="只组装指定内容包名，如 biology_g7")
    ap.add_argument("--check", action="store_true", help="只自检，不落盘")
    ap.add_argument("--stamp", default="20261110", help="整册文件名批次日期")
    args = ap.parse_args()

    packs = load_packs(args.pack)
    if not packs:
        print("[错误] 没有找到内容包（rerun_packs/*.py）", file=sys.stderr)
        return 1
    manifest, kmap, failed = [], [], 0
    for f, pack in packs:
        errors, stats = self_check(pack)
        label = f"{pack.get('subject')}/g{pack.get('grade')}"
        if errors:
            failed += 1
            print(f"[不合格] {label}（{f.name}）：{len(errors)} 处")
            for e in errors[:12]:
                print(f"    - {e}")
            manifest.append({"pack": f.stem, "book": label, "status": "self_check_failed",
                            "errors": errors, "stats": stats})
            continue
        print(f"[自检通过] {label}（{f.name}）：章 {stats['chapters']} / 点 {stats['points']} / 题 {stats['questions']}")
        if args.check:
            manifest.append({"pack": f.stem, "book": label, "status": "self_check_ok",
                            "stats": stats, "errors": []})
            kmap.append({"subject": pack["subject"], "grade": pack["grade"],
                         "chapters": [{"name": c["name"],
                                      "points": [p["name"] for p in c["points"]]}
                                     for c in pack["chapters"]]})
            continue
        doc = build_doc(pack)
        target_dir = OUT / pack["subject"] / f"g{pack['grade']}"
        target_dir.mkdir(parents=True, exist_ok=True)
        path = target_dir / f"{pack['subject']}_g{pack['grade']}_{pack['semester']}_{args.stamp}_book.json"
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[产出] {path}")
        manifest.append({"pack": f.stem, "book": label, "status": "written",
                        "path": str(path), "stats": stats, "errors": []})
        kmap.append({"subject": pack["subject"], "grade": pack["grade"],
                     "chapters": [{"name": c["name"],
                                  "points": [p["name"] for p in c["points"]]}
                                 for c in pack["chapters"]]})

    if not args.check:
        REVIEW.mkdir(parents=True, exist_ok=True)
        (REVIEW / f"rerun_manifest_{args.stamp}.json").write_text(
            json.dumps({"schema_version": 1, "stamp": args.stamp,
                        "out_dir": "docs/content-templates/daily_rerun",
                        "status": "pending_review（入库待评审后决策）",
                        "packs": manifest}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")
        (REVIEW / f"rerun_knowledge_map_{args.stamp}.json").write_text(
            json.dumps({"schema_version": 1, "stamp": args.stamp,
                        "books": kmap}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")
        print(f"[留痕] {REVIEW / f'rerun_manifest_{args.stamp}.json'}")
        print(f"[知识点表] {REVIEW / f'rerun_knowledge_map_{args.stamp}.json'}")
    print(f"合计 {len(packs)} 册，自检通过 {len(packs) - failed}，失败 {failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
