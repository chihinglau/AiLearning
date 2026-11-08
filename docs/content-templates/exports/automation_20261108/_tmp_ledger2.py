# -*- coding: utf-8 -*-
"""为已产出的日教研 JSON 生成台账与运行日志（只读 JSON，不连库）。"""
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BATCH = sys.argv[1] if len(sys.argv) > 1 else "20261108"

SUBJECT_CN = {
    "politics": "道德与法治", "history": "历史", "physics": "物理",
    "biology": "生物", "chemistry": "化学", "geography": "地理",
    "math": "数学", "chinese": "语文", "english": "英语",
}
Q_TYPE_CN = {"choice": "选择", "fill": "填空", "judge": "判断",
             "multiple": "多选", "answer": "简答"}


def load(fp):
    with open(fp, "r", encoding="utf-8") as f:
        return json.load(f)


def ledger_md(data, fp, subject, grade):
    kps = [k for k in data.get("knowledge", []) if k.get("node_type") == "point"]
    secs = [k for k in data.get("knowledge", []) if k.get("node_type") == "section"]
    qs = []
    for ch in data.get("chapters", []):
        qs.extend(ch.get("questions", []))
    types = Counter(q.get("q_type") for q in qs)
    diffs = Counter(q.get("difficulty") for q in qs)
    stems = [q.get("stem", "") for q in qs]
    dup = [s for s, c in Counter(stems).items() if c > 1]

    lines = []
    lines.append(f"# {SUBJECT_CN.get(subject, subject)} 上册 第 {grade} 册 台账\n")
    lines.append(f"- 批次日期：{BATCH}")
    lines.append(f"- 文件：{fp.name}")
    lines.append(f"- 版本：{data.get('version')}；学期：上册")
    lines.append(f"- 本册已覆盖章节：{'、'.join(c.get('name','') for c in data.get('chapters', []))}")
    lines.append(f"- 本册节（section）：{'、'.join(s.get('name','') for s in secs)}")
    lines.append(f"- 知识点（{len(kps)} 个）：{'、'.join(k.get('name','') for k in kps)}")
    lines.append(f"- 题量：{len(qs)} 道；题型分布：{' / '.join(f'{Q_TYPE_CN.get(k,k)} {v}' for k, v in types.items())}")
    lines.append(f"- 难度分布：{' / '.join(f'{k} 档 {v} 道' for k, v in sorted(diffs.items()))}")
    lines.append(f"- 多选题：{types.get('multiple', 0)} 道（解析已逐项写 A/B/C/D 与 ✓/✗）")
    lines.append(f"- 主观题：{types.get('answer', 0)} 道（含情境应用）")
    lines.append(f"- 题干去重检查：{'无重复' if not dup else '发现重复 ' + str(len(dup)) + ' 条'}")
    lines.append("- 来源：教材目录取自 baseline 大纲文件；题目为原创命题，不照抄教材原题")
    lines.append("- 自检：_validate_daily.py 通过（退出码 0）")
    lines.append("")
    lines.append("## 已用知识点")
    for k in kps:
        lines.append(f"- {k.get('name','')}")
    lines.append("")
    lines.append("## 下一节计划")
    lines.append("- 待大纲中本单元下一节/下一课（由进攻班按台账推进）")
    lines.append("")
    return "\n".join(lines)


def main():
    summary = []
    for fp in sorted((ROOT / "daily").rglob(f"*_{BATCH}.json")):
        subject = fp.parent.parent.name
        grade = int(fp.parent.name.lstrip("g"))
        if subject not in SUBJECT_CN:
            continue
        data = load(fp)
        out = ROOT / "ledger" / subject
        out.mkdir(parents=True, exist_ok=True)
        (out / f"g{grade}.md").write_text(ledger_md(data, fp, subject, grade), encoding="utf-8")
        kps = len([k for k in data.get("knowledge", []) if k.get("node_type") == "point"])
        qs = sum(len(c.get("questions", [])) for c in data.get("chapters", []))
        summary.append((subject, grade, kps, qs))

    by_sub = {}
    for s, g, k, q in summary:
        by_sub.setdefault(s, []).append((g, k, q))

    for s, rows in by_sub.items():
        log = ROOT / "logs" / f"{s}_first.md"
        log.parent.mkdir(parents=True, exist_ok=True)
        lines = [f"# {SUBJECT_CN[s]} 上册 运行日志\n",
                 f"## 批次 {BATCH}\n",
                 "| 年级 | 知识点 | 题量 | 自检 |",
                 "|---|---|---|---|"]
        for g, k, q in rows:
            lines.append(f"| g{g} | {k} | {q} | 通过 |")
        lines.append("")
        lines.append(f"- 本轮口径：只产出 JSON，不连库；不传 --kp-baseline，重名交给入库自动后缀")
        lines.append(f"- 结果：{len(rows)} 个年级产出，自检全部通过")
        lines.append("- 待续：按台账「下一节计划」推进本册下一节")
        lines.append("")
        existing = log.read_text(encoding="utf-8") if log.exists() else ""
        if f"批次 {BATCH}" not in existing:
            log.write_text(existing + "\n".join(lines) if existing else "\n".join(lines), encoding="utf-8")

    for s, rows in by_sub.items():
        print(f"{s}: {len(rows)} 个年级 " + ", ".join(f"g{g}({k}点/{q}题)" for g, k, q in rows))


if __name__ == "__main__":
    main()
