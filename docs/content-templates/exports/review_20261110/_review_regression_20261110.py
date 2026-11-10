# -*- coding: utf-8 -*-
"""2026-11-10 `daily_consolidated` 评审整改 · 只读回归汇总。

不连库、不写内容文件，只汇总本次整改产出的机读证据，并单测 P1 的范围过滤
与 per_book 解析（PowerShell 内联 Python 会被吞引号，故落成脚本）。

用法：python _review_regression_20261110.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
CT = HERE.parent.parent
AUTO = CT / "exports" / "automation_20261108_codebuddy"
BOOKS = CT / "daily_consolidated"
sys.path.insert(0, str(AUTO))
import db_ops  # noqa: E402  (只读导入：本模块顶层不连库)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


checks: list[dict] = []


def ck(name: str, ok: bool, detail: str = "") -> None:
    checks.append({"check": name, "ok": bool(ok), "detail": detail})
    print(f"{'PASS' if ok else 'FAIL'} {name}" + (f" — {detail}" if detail else ""))


def main() -> int:
    cfg = load(AUTO / "tasks.json")
    pol = cfg["policy"]
    ck("tasks.json 合法且隔离名单 34 册", len(pol["quarantine_books"]["pairs"]) == 34,
       f"pairs={len(pol['quarantine_books']['pairs'])}")
    ck("P3 门槛/重跑队列已登记",
       bool(pol["book_acceptance_gate"]["script"]) and bool(pol["book_rerun_queue"]["pairs_ref"]))
    ck("新增两条治理留痕 note",
       bool(pol.get("kp_reconcile_20261110_note")) and bool(pol.get("import_books_note_20261110")))

    doc04 = (AUTO / "04-一键执行与入库操作手册.md").read_text(encoding="utf-8")
    ck("04 手册含 §3.8.7 / 隔离名单 / per_book / 1104 订正",
       all(x in doc04 for x in ("3.8.7", "隔离名单", "per_book", "1104")))
    manual = (CT / "批量生成某年级全学科全册章节操作手册.md").read_text(encoding="utf-8")
    ck("批量手册含 P3 闸门与隔离名单告警",
       "P3 验收闸门" in manual and "隔离名单" in manual and "不具备入库资格" in manual)

    plain = sorted(BOOKS.rglob("*_book.json"))
    quarantined = sorted(BOOKS.rglob("*_book.quarantined.json"))
    ck("整册目录 12 合格 + 34 隔离", len(plain) == 12 and len(quarantined) == 34,
       f"plain={len(plain)} quarantined={len(quarantined)}")

    all_files = plain
    scoped = db_ops._book_scope(all_files, BOOKS,
                                SimpleNamespace(subjects="math,chinese", grades="1,8", only=None))
    ck("P1-3 --subjects/--grades 范围过滤", len(scoped) == 4,
       "、".join(f.relative_to(BOOKS).as_posix() for f in scoped))
    only_one = db_ops._book_scope(all_files, BOOKS,
                                  SimpleNamespace(subjects=None, grades=None,
                                                  only="math/g1/math_g1_first_20261109_book.json"))
    ck("P1-3 --only 白名单单册", len(only_one) == 1,
       only_one[0].name if only_one else "无匹配")
    ck("P1-3 不过滤时保持全集合", len(db_ops._book_scope(
        all_files, BOOKS, SimpleNamespace(subjects=None, grades=None, only=None))) == 12)

    sample = (
        "math/g1/math_g1_first_20261109_book.json: 教材已存在，章节 +0/~0，知识点 +0/~0，题目 +0，跳过重复 139\n"
        "chinese/g8/chinese_g8_first_20261109_book.json: 已导入且文件未变，跳过（manifest）\n"
        "english/g8/english_g8_first_20261109_book.json: 导入失败 - boom"
    )
    rows = db_ops.parse_book_lines(sample)
    summ = db_ops.book_summary(rows)
    ck("复评 §八-4 per_book 解析三类行",
       [r["status"] for r in rows] == ["ok", "skipped_manifest", "failed"]
       and summ["questions_skipped"] == 139 and summ["failed"] == 1)

    gate = load(HERE / "book_gate_20261110.json")
    gate_all = load(HERE / "book_gate_all_20261110.json")
    ck("P3 闸门 12 册全通过", gate["totals"] == {"files": 12, "passed": 12, "failed": 0},
       str(gate["totals"]))
    ck("P3 闸门含隔离件 46 册 12/34", gate_all["totals"] == {"files": 46, "passed": 12, "failed": 34},
       str(gate_all["totals"]))
    failed_rel = {r["relative"].replace(".quarantined.json", ".json")
                  for r in gate_all["files"] if not r["passed"]}
    expected_rel = {
        f"{pair.split(':')[0]}/g{pair.split(':')[1]}/"
        f"{pair.split(':')[0]}_g{pair.split(':')[1]}_first_20261109_book.json"
        for pair in pol["quarantine_books"]["pairs"]
    }
    ck("P3 失败名单与隔离名单完全一致", failed_rel == expected_rel,
       f"failed={len(failed_rel)} expected={len(expected_rel)} diff={len(failed_rel ^ expected_rel)}")

    kp = load(HERE / "kp_reconciliation_20261110.json")
    ck("只读对账 1104 / 差 11 / 11-08 21:38 共 11 节点",
       kp["measured"]["knowledge_points"] == 1104
       and kp["analysis"]["delta"] == 11
       and kp["analysis"]["nodes_created_2138"] == 11,
       f"孤儿节点={kp['analysis']['nodes_created_2138_orphan']}")

    final = load(HERE / "books_validation_final_20261110.json")
    ck("目录模式整册校验 12/12", len(final["files"]) == 12
       and all(f["passed"] for f in final["files"]))

    gen = (CT.parent.parent / "_gen_fullbooks.py").read_text(encoding="utf-8")
    ck("生成器已接入准入自检与隔离名单",
       all(x in gen for x in ("load_gate_policy", "assess(", "quarantine", "拦截-不写盘")))

    out = HERE / "review_regression_20261110.json"
    report = {
        "schema_version": 1,
        "source": "docs/content-templates/exports/review_20261110/_review_regression_20261110.py",
        "mode": "read-only",
        "totals": {"checks": len(checks), "passed": sum(1 for c in checks if c["ok"]),
                   "failed": sum(1 for c in checks if not c["ok"])},
        "checks": checks,
    }
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[机读汇总] {out}")
    print(f"合计 {len(checks)} 项，通过 {report['totals']['passed']}，失败 {report['totals']['failed']}")
    return 0 if report["totals"]["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
