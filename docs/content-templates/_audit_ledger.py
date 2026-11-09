"""台账/推进顺序体检：把「台账写到哪里」与「JSON 实际做到哪一章」对上（只读）。

背景（2026-11-09 评审）：`_rN` 分片生成后没有回写台账，
`ledger\math\g1.md` 仍写「上次做到 我上学啦」，而 r2~r6 已做到第五单元；
且 math g1 的 r5 是第五单元、r6 才是第四单元（顺序倒置）。

用法：
    python _audit_ledger.py                 # 打印
    python _audit_ledger.py --md out.md     # 写 Markdown
"""

from __future__ import annotations

import argparse
import glob
import json
import re
from pathlib import Path

CT = Path(__file__).resolve().parent
PAIRS = [
    ("math", 1), ("chinese", 1), ("english", 1), ("politics", 1),
    ("math", 8), ("chinese", 8), ("english", 8), ("politics", 8),
    ("physics", 8), ("biology", 8), ("geography", 8), ("history", 8),
]
_FRAG_RE = re.compile(r"_r(\d+)\.json$", re.IGNORECASE)
_POINTER_RE = re.compile(r"(上次做到|进度指针)[：: ]*(.+)")


def fragments(subject: str, grade: int) -> list[dict]:
    rows = []
    for path_str in sorted(glob.glob(str(CT / "daily" / subject / f"g{grade}" / f"{subject}_g{grade}_*.json"))):
        path = Path(path_str)
        match = _FRAG_RE.search(path.name)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        chapter = (data.get("chapters") or [{}])[0]
        rows.append({
            "file": path.name,
            "r": int(match.group(1)) if match else 0,
            "chapter": str(chapter.get("name") or ""),
            "order": chapter.get("order_index"),
            "questions": len(chapter.get("questions") or []),
        })
    return rows


def ledger_state(subject: str, grade: int) -> dict:
    path = CT / "ledger" / subject / f"g{grade}.md"
    state = {"exists": path.is_file(), "pointer": "", "rows": 0}
    if not path.is_file():
        return state
    text = path.read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        match = _POINTER_RE.search(line)
        if match and not state["pointer"]:
            state["pointer"] = match.group(2).strip()
        if line.startswith("| 2026"):
            state["rows"] += 1
    return state


def main() -> int:
    parser = argparse.ArgumentParser(description="台账与推进顺序体检（只读）")
    parser.add_argument("--md", help="输出 Markdown 路径")
    args = parser.parse_args()

    lines = ["# 台账 / 推进顺序体检（只读，未改任何文件）", ""]
    issues = 0
    for subject, grade in PAIRS:
        rows = fragments(subject, grade)
        state = ledger_state(subject, grade)
        lines.append(f"## {subject} / g{grade}")
        lines.append(f"- 台账：{'存在' if state['exists'] else '缺失'}"
                     f"（历史进度行 {state['rows']} 条；指针：{state['pointer'] or '未写'}）")
        seq = sorted(rows, key=lambda r: (r["r"], r["file"]))
        lines.append("- 本地文件推进顺序：" + " → ".join(
            f"{r['file']}({r['chapter'] or '无章节'}，order={r['order']}，{r['questions']}题)" for r in seq))
        reversals = []
        for prev, cur in zip(seq, seq[1:]):
            if isinstance(prev["order"], int) and isinstance(cur["order"], int) and cur["order"] < prev["order"]:
                reversals.append(f"{prev['file']}(order={prev['order']}) → {cur['file']}(order={cur['order']})")
        if reversals:
            issues += 1
            lines.append("- ⚠ 章节序号回退（有意回补旧章可以接受，但台账必须留痕；"
                         "无解释则是推进乱序）：" + "；".join(reversals))
        if state["pointer"] and seq:
            last = max((r for r in seq if isinstance(r["order"], int)), key=lambda r: r["order"], default=None)
            if last:
                lines.append(f"- 台账指针「{state['pointer']}」 vs 已做到「{last['chapter']}」"
                             "：指针未随分片推进（次日会重复做同一节）"
                             if state["pointer"] not in (last["chapter"] or "")
                             else "- 台账指针与最新分片一致")
        lines.append("")

    text = "\n".join(lines) + "\n"
    if args.md:
        Path(args.md).write_text(text, encoding="utf-8")
        print(f"[写入] {args.md}；顺序倒置 {issues} 处")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
