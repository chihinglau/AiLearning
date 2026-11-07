"""只读生成知识点名称基线（供每日教研离线自检使用）。

用法（在 backend 目录执行）：
    .venv\\Scripts\\python.exe -m scripts.build_kp_baseline
    .venv\\Scripts\\python.exe -m scripts.build_kp_baseline --output-dir ..\\docs\\content-templates

输出：
    _knowledge-points-baseline_YYYYMMDD.json
    _knowledge-points-baseline_YYYYMMDD.md
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import date
from pathlib import Path

from sqlalchemy import select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.content import KnowledgePoint


def _collect(db) -> tuple[dict, dict]:
    rows = list(
        db.execute(
            select(
                KnowledgePoint.subject,
                KnowledgePoint.grade,
                KnowledgePoint.name,
                KnowledgePoint.node_type,
                KnowledgePoint.parent_id,
            )
        ).all()
    )
    parents = {
        row.id: row.name for row in db.scalars(select(KnowledgePoint))
    }
    groups: dict[tuple[str, int, str], dict] = defaultdict(
        lambda: {"count": 0, "types": set(), "sections": set()}
    )
    for subject, grade, name, node_type, parent_id in rows:
        item = groups[(subject, grade, name)]
        item["count"] += 1
        item["types"].add(node_type)
        if node_type == "point" and parent_id:
            item["sections"].add(parents.get(parent_id, ""))
    names: dict[str, dict[str, dict[str, int]]] = defaultdict(dict)
    detail: dict[tuple[str, int, str], dict] = {}
    for (subject, grade, name), item in groups.items():
        names.setdefault(subject, {}).setdefault(str(grade), {})[name] = item["count"]
        detail[(subject, grade, name)] = item
    return dict(names), detail


def _render_md(names: dict, detail: dict, *, generated: str, source: str) -> str:
    subjects = {
        "chinese": "语文",
        "math": "数学",
        "english": "英语",
        "physics": "物理",
        "chemistry": "化学",
        "biology": "生物",
        "history": "历史",
        "geography": "地理",
        "politics": "道法",
    }
    ambiguous = [key for key, item in detail.items() if item["count"] >= 2]
    lines = [
        f"# 知识点名称基线（{generated}）",
        "",
        f"> 来源：`{source}`（只读）",
        "> 语义：subject → grade → name → 库内出现次数；次数 ≥ 2 表示同名，导入时按名称引用会被拒绝。",
        "> 新增内容导入后请重新运行 `python -m scripts.build_kp_baseline`，否则基线过期。",
        "",
        "## 概览",
        "",
        "| 学科 | 年级数 | 名称数 | 歧义名称数 |",
        "|---|---|---|---|",
    ]
    for subject, grades in sorted(names.items()):
        total = sum(len(v) for v in grades.values())
        bad = sum(1 for (s, _g, _n), item in detail.items() if s == subject and item["count"] >= 2)
        lines.append(
            f"| {subjects.get(subject, subject)}（`{subject}`） | {len(grades)} | {total} | {bad} |"
        )
    lines += ["", f"## 歧义名称（共 {len(ambiguous)} 组）", ""]
    if ambiguous:
        lines += [
            "| 学科 | 年级 | 名称 | 类型 | 次数 |",
            "|---|---|---|---|---|",
        ]
        for subject, grade, name in sorted(ambiguous):
            item = detail[(subject, grade, name)]
            types = "、".join(sorted(item["types"]))
            lines.append(
                f"| {subjects.get(subject, subject)} | {grade} | `{name}` | {types} | {item['count']} |"
            )
    else:
        lines.append("无。库内同学科同年级的知识点名称均唯一，可按名称安全引用。")
    lines += ["", "## 分学科明细", ""]
    for subject, grades in sorted(names.items()):
        lines += [f"### {subjects.get(subject, subject)}（`{subject}`）", ""]
        for grade in sorted(grades, key=int):
            items = [
                (name, detail[(subject, int(grade), name)])
                for name in grades[grade]
            ]
            lines += [
                f"#### {grade} 年级（{len(items)} 个名字）",
                "",
                "| 名称 | 类型 | 所属 section | 出现次数 | 可引用? |",
                "|---|---|---|---|---|",
            ]
            for name, item in sorted(items, key=lambda pair: pair[0]):
                types = "、".join(sorted(item["types"]))
                section = "、".join(sorted(s for s in item["sections"] if s)) or "（顶层）"
                can = "✅ 可引用" if item["count"] == 1 else "❌ 禁止引用（歧义）"
                lines.append(
                    f"| `{name}` | {types} | `{section}` | {item['count']} | {can} |"
                )
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="生成知识点名称基线")
    parser.add_argument(
        "--output-dir",
        default="../docs/content-templates",
        help="输出目录（默认 ../docs/content-templates）",
    )
    parser.add_argument("--date", default=date.today().strftime("%Y%m%d"))
    args = parser.parse_args()

    session = SessionLocal()
    try:
        names, detail = _collect(session)
    finally:
        session.close()

    generated = date.today().isoformat()
    source = settings.database_url
    ambiguous = sum(1 for item in detail.values() if item["count"] >= 2)
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    base = f"_knowledge-points-baseline_{args.date}"
    payload = {
        "_meta": {
            "generated": generated,
            "source": f"{source}（只读）",
            "semantics": "subject -> grade -> name -> 库内出现次数；次数>=2 表示同名歧义，导入时引用会被拒绝",
            "regenerate": "新增内容导入后需重新生成本文件，否则基线过期",
            "total_names": sum(len(v) for grades in names.values() for v in grades.values()),
            "ambiguous": ambiguous,
        },
        "names": names,
    }
    (output / f"{base}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    (output / f"{base}.md").write_text(
        _render_md(names, detail, generated=generated, source=source),
        encoding="utf-8",
    )
    print(
        f"基线已生成：{output / base}.json / .md"
        f"（名称 {payload['_meta']['total_names']} 个，歧义 {ambiguous} 组）"
    )
    return 1 if ambiguous else 0


if __name__ == "__main__":
    raise SystemExit(main())
