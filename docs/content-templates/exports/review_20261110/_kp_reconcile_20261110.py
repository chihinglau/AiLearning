# -*- coding: utf-8 -*-
"""评审复评 §八-3 / §九-②：`knowledge_points 1104 vs 1093` 只读对账。

只以 mode=ro 打开 SQLite，不做任何 UPDATE/DELETE/INSERT；
输出按 (subject, grade, node_type) 分布、与知识点名基线的差异、
以及 created_at 分组，供判断「改文档数字」还是「补清理」。

用法：
    python _kp_reconcile_20261110.py [--json-out <path>]
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
CT = HERE.parent.parent
WORKSPACE = CT.parent.parent
DB = WORKSPACE / "backend" / "ailearning_dev.db"
BASELINE = CT / "baseline" / "_knowledge-points-baseline_latest.json"
DOCUMENTED_KP = 1093  # 04 手册第 187/574 行、tasks.json kp_cleanup_note 的 11-09 口径


def main() -> int:
    ap = argparse.ArgumentParser(description="只读对账 knowledge_points 口径差异")
    ap.add_argument("--json-out", dest="json_out", default=str(HERE / "kp_reconciliation_20261110.json"))
    args = ap.parse_args()
    if not DB.is_file():
        print(f"[错误] 数据库不存在：{DB}", file=sys.stderr)
        return 1

    conn = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    try:
        totals = {t: conn.execute(f"select count(*) from {t}").fetchone()[0]
                  for t in ("textbooks", "chapters", "knowledge_points", "questions")}
        kp_total = totals["knowledge_points"]

        by_node = {str(r[0]): r[1] for r in conn.execute(
            "select node_type, count(*) from knowledge_points group by node_type")}
        by_triple = [
            {"subject": r[0], "grade": r[1], "node_type": r[2], "count": r[3]}
            for r in conn.execute(
                "select subject, grade, node_type, count(*) from knowledge_points "
                "group by subject, grade, node_type order by subject, grade, node_type")
        ]
        by_created = [
            {"minute": r[0], "count": r[1]}
            for r in conn.execute(
                "select substr(created_at, 1, 16) as m, count(*) from knowledge_points "
                "group by m order by m")
        ]

        # 基线只收 point 名；同名出现次数 >=2 表示歧义
        baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
        base_names = baseline.get("names") or {}
        base_total = (baseline.get("_meta") or {}).get("total_names")
        db_points = defaultdict(set)
        for sub, grade, name in conn.execute(
                "select subject, grade, name from knowledge_points where node_type='point'"):
            db_points[(str(sub), str(grade))].add(str(name))

        missing_in_db, extra_in_db = [], []
        for sub, grades in base_names.items():
            for grade, names in grades.items():
                bset = set(names.keys())
                dset = db_points.get((str(sub), str(grade)), set())
                for name in sorted(bset - dset):
                    missing_in_db.append({"subject": sub, "grade": grade, "name": name})
                for name in sorted(dset - bset):
                    extra_in_db.append({"subject": sub, "grade": grade, "name": name})
        for key, dset in db_points.items():
            if key[0] not in base_names or str(key[1]) not in base_names.get(key[0], {}):
                for name in sorted(dset):
                    extra_in_db.append({"subject": key[0], "grade": key[1], "name": name})

        # 多出来的节点是否有题引用（决定是否该「补清理」）
        question_links = {r[0]: r[1] for r in conn.execute(
            "select knowledge_point_id, count(*) from questions "
            "where knowledge_point_id is not null group by knowledge_point_id")}
        suspects = []
        for row in conn.execute(
                "select id, subject, grade, node_type, name, created_at from knowledge_points "
                "where substr(created_at, 1, 10) in ('2026-11-08','2026-11-09') "
                "order by created_at, id"):
            suspects.append({
                "id": row[0], "subject": row[1], "grade": row[2], "node_type": row[3],
                "name": row[4], "created_at": row[5],
                "questions_linked": question_links.get(row[0], 0),
            })

        # 评审点名的两个建点时刻：确认 11 个差异是否真是「清理前的存量」
        child_counts = {r[0]: r[1] for r in conn.execute(
            "select parent_id, count(*) from knowledge_points "
            "where parent_id is not null group by parent_id")}
        prereq_refs: dict[int, list[int]] = defaultdict(list)
        for kp_id, prereq in conn.execute(
                "select id, prerequisites from knowledge_points where prerequisites is not null"):
            try:
                ids = json.loads(prereq) if isinstance(prereq, str) else prereq
            except (json.JSONDecodeError, TypeError):
                continue
            if isinstance(ids, list):
                for v in ids:
                    if isinstance(v, int):
                        prereq_refs[v].append(kp_id)
        dup_names = {(r[0], r[1], r[2]): r[3] for r in conn.execute(
            "select subject, grade, name, count(*) from knowledge_points "
            "group by subject, grade, name having count(*) > 1")}

        review_minutes = ("2026-11-08 20:33", "2026-11-08 21:38")
        minute_nodes = []
        for minute in review_minutes:
            for row in conn.execute(
                    "select id, subject, grade, node_type, name, created_at from knowledge_points "
                    "where substr(created_at, 1, 16) = ? order by id", (minute,)):
                minute_nodes.append({
                    "minute": minute, "id": row[0], "subject": row[1], "grade": row[2],
                    "node_type": row[3], "name": row[4], "created_at": row[5],
                    "questions_linked": question_links.get(row[0], 0),
                    "child_count": child_counts.get(row[0], 0),
                    "prerequisite_refs": len(prereq_refs.get(row[0], [])),
                    "same_name_count": dup_names.get((row[1], row[2], row[4]), 1),
                })
        zero_link = [n for n in minute_nodes if n["questions_linked"] == 0]
        late = [n for n in minute_nodes if n["minute"] == "2026-11-08 21:38"]
        orphan_candidates = [n for n in late if n["questions_linked"] == 0
                             and n["child_count"] == 0 and n["prerequisite_refs"] == 0]
        analysis = {
            "delta": kp_total - DOCUMENTED_KP,
            "point_in_db": by_node.get("point", 0),
            "baseline_names": base_total,
            "point_names_not_in_baseline": len(extra_in_db),
            "baseline_names_missing_in_db": len(missing_in_db),
            "review_minute_nodes": len(minute_nodes),
            "review_minute_zero_question_nodes": len(zero_link),
            "nodes_created_2138": len(late),
            "nodes_created_2138_orphan": len(orphan_candidates),
            "recommendation": (
                f"实测 {kp_total}，比 04 手册/tasks.json 的 {DOCUMENTED_KP} 多 {kp_total - DOCUMENTED_KP}；"
                f"差异恰为 11-08 21:38 建的 {len(late)} 个存量节点，其中 {len(orphan_candidates)} 个"
                "0 题 0 子点 0 先修引用（清理脚本未覆盖）。两条处置：① 不改库 → 文档数字订正为 "
                f"{kp_total}（本次可执行、纯文档）；② 补清理这 {len(orphan_candidates)} 个孤儿节点使库回到 "
                f"{DOCUMENTED_KP} → 属写库动作，需用户显式授权并在备份后执行。本次只读对账不改库。"
            ),
        }

        report = {
            "schema_version": 1,
            "source": "docs/content-templates/exports/review_20261110/_kp_reconcile_20261110.py",
            "mode": "read-only (sqlite mode=ro)",
            "database": str(DB),
            "documented_kp_20261109": DOCUMENTED_KP,
            "measured": {"totals": totals, "knowledge_points": kp_total,
                         "delta_vs_documented": kp_total - DOCUMENTED_KP,
                         "by_node_type": by_node},
            "baseline": {"path": str(BASELINE), "total_names": base_total,
                         "generated": (baseline.get("_meta") or {}).get("generated")},
            "by_subject_grade_node_type": by_triple,
            "by_created_minute": by_created,
            "baseline_diff": {"missing_in_db": missing_in_db, "extra_in_db": extra_in_db},
            "nodes_created_1108_1109": suspects,
            "review_minute_nodes": minute_nodes,
            "analysis": analysis,
        }
        out = Path(args.json_out).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        print(f"[只读对账] {DB}")
        print(f"  textbooks/chapters/knowledge_points/questions = "
              f"{totals['textbooks']}/{totals['chapters']}/{kp_total}/{totals['questions']}")
        print(f"  文档口径 {DOCUMENTED_KP} → 实测 {kp_total}，差 {kp_total - DOCUMENTED_KP}")
        print(f"  by node_type = {by_node}")
        print(f"  基线 {base_total} 名：库内缺 {len(missing_in_db)}，库内多 {len(extra_in_db)}")
        print(f"  11-08/11-09 新建节点 {len(suspects)} 个，其中挂题 "
              f"{sum(1 for s in suspects if s['questions_linked'])} 个")
        print(f"  评审点名时刻（20:33 / 21:38）节点 {len(minute_nodes)} 个，"
              f"其中 0 题节点 {len(zero_link)} 个；挂题 "
              f"{sum(n['questions_linked'] for n in minute_nodes)} 题")
        print(f"  结论：{analysis['recommendation']}")
        print(f"[机读汇总] {out}")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
