# -*- coding: utf-8 -*-
"""整册入库前验收闸门（2026-11-10 `daily_consolidated` 评审 P3，只读）。

评审 §五 P3 / §九-③：任一册必须同时满足以下硬门槛才允许进 `import-books`：

  1. `_validate_daily.py` 该册 0 错误；
  2. 册内跨章重复题种（同题型 + 同题干跨章出现）= 0；
  3. 「题挂载 section 被多个章共用」的题数 = 0；
  4. 模板套话题占比 <= 5%；
  5. 同题干答案唯一。

结构目标（section 数 >= 章数-1、point 数 >= 章数×4）只作告警：
2026-11-10 对 12 册已入库合格册只读校准后，math/g1 的 point=20 < 6×4=24，
按字面判硬门槛会误杀已入库册，故登记在 tasks.json 的 structural_exemptions。

用法（任意目录执行，本脚本不写库、不写内容文件，只可写 --json-out）：
    python _check_book_gate.py
    python _check_book_gate.py --include-quarantined
    python _check_book_gate.py <file-or-dir> --json-out <path>
    python _check_book_gate.py --no-validator            # 只跑内容五条，跳过校验器

退出码：0 = 全部通过；1 = 存在未通过册（或校验器汇总不可用）。
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

CT = Path(__file__).resolve().parent
TASKS = CT / "exports" / "automation_20261108_codebuddy" / "tasks.json"
VALIDATOR = CT / "_validate_daily.py"
VERSION_MAP = CT / "baseline" / "_subject-version-map.json"
BOOKS_DIR = CT / "daily_consolidated"

DEFAULT_NEGATIVE = [
    "更可取的学习做法", "可以先梳理", "举一个生活中用到",
    "结合实例分析比单纯背诵", "值得提倡的", "先理解概念再结合实例分析",
    "知识脉络", "·概念理解", "·认知",
]


def load_policy(path: Path | None) -> dict:
    p = path or TASKS
    cfg = {}
    if p.is_file():
        try:
            cfg = json.loads(p.read_text(encoding="utf-8")).get("policy") or {}
        except (json.JSONDecodeError, OSError):
            cfg = {}
    gate = cfg.get("book_acceptance_gate") or {}
    return {
        "policy_source": str(p) if p.is_file() else "built-in defaults",
        "negative_stems": list(gate.get("negative_stems") or DEFAULT_NEGATIVE),
        "cliche_max_ratio": float(gate.get("cliche_max_ratio", 0.05)),
        "points_per_chapter": 4,
    }


def collect_files(paths: list[Path], include_quarantined: bool) -> list[Path]:
    out: set[Path] = set()
    for p in paths:
        if p.is_file():
            out.add(p.resolve())
        elif p.is_dir():
            out.update(f.resolve() for f in p.rglob("*_book.json"))
            if include_quarantined:
                out.update(f.resolve() for f in p.rglob("*_book.quarantined.json"))
        else:
            print(f"[警告] 路径不存在：{p}", file=sys.stderr)
    return sorted(out)


def validator_results(files: list[Path], skip: bool) -> tuple[dict[str, dict], str]:
    """一次跑完所有册的 `_validate_daily.py --json-out`，按文件名索引机读结果。"""
    if skip:
        return {}, "skipped"
    if not files:
        return {}, "no-files"
    with tempfile.TemporaryDirectory(prefix="book-gate-") as td:
        jout = Path(td) / "validation.json"
        argv = [sys.executable, str(VALIDATOR), *[str(f) for f in files],
                "--json-out", str(jout)]
        if VERSION_MAP.is_file():
            argv += ["--version-map", str(VERSION_MAP)]
        proc = subprocess.run(
            argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace",
            env=dict(os.environ, PYTHONIOENCODING="utf-8"),
        )
        if not jout.is_file():
            tail = "\n".join((proc.stdout or "").splitlines()[-6:])
            print(f"[警告] 校验器未产出机读汇总（rc={proc.returncode}）：\n{tail}", file=sys.stderr)
            return {}, "unknown"
        summary = json.loads(jout.read_text(encoding="utf-8"))
        return {str(r.get("name")): r for r in summary.get("files", [])}, "ok"


def _answer_of(q: dict) -> str:
    ans = q.get("answer")
    if isinstance(ans, str):
        return ans.strip()
    return json.dumps(ans, ensure_ascii=False, sort_keys=True)


def check_book(path: Path, policy: dict, vres: dict | None, vstatus: str) -> dict:
    doc = json.loads(path.read_text(encoding="utf-8"))
    kn = [k for k in (doc.get("knowledge") or []) if isinstance(k, dict)]
    secnames = {str(k.get("name") or "").strip() for k in kn if k.get("node_type") == "section"}
    parent = {str(k.get("name") or "").strip(): str(k.get("parent") or "").strip()
              for k in kn if k.get("node_type", "point") == "point"}
    chapters = [c for c in (doc.get("chapters") or []) if isinstance(c, dict)]
    rows = []
    for ch in chapters:
        cname = str(ch.get("name") or "").strip()
        for q in (ch.get("questions") or []):
            if isinstance(q, dict):
                rows.append((cname, q))

    # 2. 跨章重复题种（同章内重复仅告警）
    seen: dict[tuple[str, str], str] = {}
    dup_cross = dup_intra = 0
    for cname, q in rows:
        key = (str(q.get("q_type") or "").strip(), str(q.get("stem") or "").strip())
        if key in seen:
            if seen[key] == cname:
                dup_intra += 1
            else:
                dup_cross += 1
        else:
            seen[key] = cname

    # 3. section 跨章共用
    owner: dict[str, set[str]] = defaultdict(set)
    section_of: dict[int, str | None] = {}
    for idx, (cname, q) in enumerate(rows):
        kp = str(q.get("knowledge_point") or "").strip()
        sec = parent.get(kp) or (kp if kp in secnames else None)
        section_of[idx] = sec
        if sec:
            owner[sec].add(cname)
    shared_sections = sum(1 for v in owner.values() if len(v) > 1)
    shared_q = 0
    unresolved_kp = 0
    for idx, sec in section_of.items():
        if sec is None:
            unresolved_kp += 1
        elif len(owner[sec]) > 1:
            shared_q += 1

    # 4. 模板套话题占比
    neg = policy["negative_stems"]
    cliche = sum(1 for _, q in rows
                 if any(x in str(q.get("stem") or "") for x in neg))
    ratio = cliche / max(1, len(rows))
    max_ratio = policy["cliche_max_ratio"]

    # 5. 同题干答案唯一
    answers: dict[str, set[str]] = defaultdict(set)
    for _, q in rows:
        answers[str(q.get("stem") or "").strip()].add(_answer_of(q))
    conflicts = sum(1 for v in answers.values() if len(v) > 1)

    # 1. 校验器 0 错误
    if vstatus == "skipped":
        verr, vwarn, vok = None, None, True
        vdetail = "显式 --no-validator 跳过"
    elif vres is None:
        verr, vwarn, vok = None, None, False
        vdetail = "校验器机读汇总不可用（保守判不通过）"
    else:
        verr = int(vres.get("errors") or 0)
        vwarn = int(vres.get("warnings") or 0)
        vok = bool(vres.get("passed")) and verr == 0
        vdetail = "; ".join(vres.get("error_messages") or [])[:300]

    ch_count, sec_count, pt_count = len(chapters), len(secnames), len(parent)
    hard = {
        "validator_0_errors": {"ok": vok, "value": verr, "detail": vdetail},
        "cross_chapter_duplicate_stems_0": {"ok": dup_cross == 0, "value": dup_cross,
                                             "same_chapter_duplicates_warn": dup_intra},
        "section_shared_questions_0": {"ok": shared_q == 0, "value": shared_q,
                                       "shared_sections": shared_sections},
        "cliche_ratio_le_5pct": {"ok": ratio <= max_ratio, "value": round(ratio, 4),
                                 "hits": cliche, "questions": len(rows), "max": max_ratio},
        "same_stem_unique_answer": {"ok": conflicts == 0, "value": conflicts},
    }
    warnings = []
    if dup_intra:
        warnings.append(f"同章内重复题干 {dup_intra} 处")
    if unresolved_kp:
        warnings.append(f"题挂载点在文件内未声明（依赖库内同名点）{unresolved_kp} 处")
    if sec_count < ch_count - 1:
        warnings.append(f"section {sec_count} < 章数-1 {ch_count - 1}")
    if pt_count < ch_count * policy["points_per_chapter"]:
        warnings.append(f"point {pt_count} < 章数×4 {ch_count * 4}（结构目标，见 structural_exemptions）")
    if vwarn:
        warnings.append(f"校验器提醒 {vwarn} 条（不阻断）")

    failed = [name for name, item in hard.items() if not item["ok"]]
    rel = path.relative_to(BOOKS_DIR).as_posix() if path.is_relative_to(BOOKS_DIR) else path.name
    return {
        "path": str(path), "name": path.name, "relative": rel, "passed": not failed,
        "failed_gates": failed, "hard": hard, "warnings": warnings,
        "stats": {"chapters": ch_count, "sections": sec_count, "points": pt_count,
                  "questions": len(rows), "cliche_hits": cliche, "unresolved_kp": unresolved_kp},
        "validator": {"status": vstatus, "errors": verr, "warnings": vwarn,
                      "passed": (vres or {}).get("passed")},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="整册入库前验收闸门（评审 P3，只读）")
    ap.add_argument("paths", nargs="*", help="整册文件或目录，默认 daily_consolidated")
    ap.add_argument("--include-quarantined", action="store_true",
                    help="目录模式下连 *.quarantined.json 一起复核")
    ap.add_argument("--json-out", dest="json_out", help="机读结果输出路径")
    ap.add_argument("--policy", type=Path, help="tasks.json 路径（默认自动定位）")
    ap.add_argument("--no-validator", action="store_true", help="不调用 _validate_daily.py")
    args = ap.parse_args()

    policy = load_policy(args.policy)
    roots = [Path(p).resolve() for p in args.paths] if args.paths else [BOOKS_DIR]
    files = collect_files(roots, args.include_quarantined)
    if not files:
        print("[错误] 没有找到整册文件", file=sys.stderr)
        return 1

    vmap, vstatus = validator_results(files, args.no_validator)
    results = []
    for f in files:
        try:
            r = check_book(f, policy, vmap.get(f.name) if vstatus == "ok" else None, vstatus)
        except (json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
            r = {"path": str(f), "name": f.name, "relative": f.name, "passed": False,
                 "failed_gates": ["readable_json"], "hard": {}, "warnings": [str(exc)],
                 "stats": {}, "validator": {"status": "read-error"}}
        results.append(r)
        s = r["stats"]
        print(f"{'PASS' if r['passed'] else 'FAIL'} {r['relative']}: "
              f"ch={s.get('chapters', 0)} sec={s.get('sections', 0)} pt={s.get('points', 0)} "
              f"q={s.get('questions', 0)} | "
              + " ".join(f"{k}={v['value']}" for k, v in r["hard"].items())
              + (f" | 未过：{','.join(r['failed_gates'])}" if r["failed_gates"] else ""))

    passed = sum(1 for r in results if r["passed"])
    summary = {
        "schema_version": 1,
        "source": "docs/content-templates/_check_book_gate.py",
        "review": "docs/content-templates/exports/review_20261110/daily_consolidated-评审_20261110.md §五 P3",
        "policy_source": policy["policy_source"],
        "validator_status": vstatus,
        "include_quarantined": args.include_quarantined,
        "hard_gates": list(results[0]["hard"].keys()) if results else [],
        "negative_stems": policy["negative_stems"],
        "totals": {"files": len(results), "passed": passed, "failed": len(results) - passed},
        "files": results,
    }
    if args.json_out:
        out = Path(args.json_out).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[机读汇总] {out}")
    print(f"合计 {len(results)} 个文件，通过 {passed} 个，失败 {len(results) - passed} 个")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
