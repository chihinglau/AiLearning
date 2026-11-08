# -*- coding: utf-8 -*-
"""把学期大纲 md 转成「章节骨架」导入批次（只有章节名，无知识点、无题目）。

用途：让 App 切到该学期时目录不再空白。
用法：python _build_chapters_skeleton_second.py [first|second]（默认 second）
输出目录：baseline/_skeleton/（下学期）或 baseline/_skeleton_first/（上学期）
命名：chapters_{subject}_g{grade}_{semester}_20261107.json
章节名直接取自 _outline_{subject}_{semester}_latest.md，保证与越界拦截基线同名。
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = ROOT / "baseline"
STAMP = "20261107"
SEMESTER = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in ("first", "second") else "second"
OUT = BASE / ("_skeleton" if SEMESTER == "second" else "_skeleton_first")

CN = "一二三四五六七八九"

VERSION = {
    "math": "北师大版", "chinese": "人教版", "english": "牛津深圳版", "politics": "部编版",
    "physics": "人教版", "chemistry": "人教版", "biology": "人教版", "history": "部编版",
    "geography": "湘教版",
}
GRADES = {
    "math": list(range(1, 9)), "chinese": list(range(1, 10)), "english": list(range(1, 10)),
    "politics": list(range(1, 10)), "physics": [8, 9], "chemistry": [9],
    "biology": [7, 8], "history": [7, 8, 9], "geography": [7, 8],
}


def parse_outline(path: Path) -> dict[int, list[tuple[str, list[str]]]]:
    """返回 {年级: [(名称, [节名...]), ...]}"""
    grades: dict[int, list[tuple[str, list[str]]]] = {}
    cur = None
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.startswith("#"):
            cur = None
            for i, cn in enumerate(CN, 1):
                if f"{cn}年级" in s:
                    cur = i
                    grades.setdefault(cur, [])
                    break
            continue
        if cur is None or not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < 2 or set(cells[0]) <= set("-: "):
            continue
        if cells[0].replace("**", "").strip() in ("序", "章", "单元", "年级"):
            continue
        name_cell = cells[1].replace("**", "").strip()
        detail_cell = cells[2] if len(cells) > 2 else ""
        grades[cur].append((name_cell, [x.strip() for x in detail_cell.split(" / ") if x.strip()]))
    return grades


def chapter_names(subject: str, rows: list[tuple[str, list[str]]]) -> list[str]:
    names: list[str] = []
    group_row = re.compile(r"^Unit\s*\d+\s*[-–]\s*\d+$", re.I)

    def expand(detail: list[str]) -> None:
        for item in detail:
            if item.startswith("Unit"):
                names.append(item.split(" / ")[0].strip())

    if subject == "english":
        # 英语：章节粒度取 Unit；Module 行、以及「Unit 1-8」这类分组行都展开子单元
        for name, detail in rows:
            if "待补" in name:
                continue
            if name.lower().startswith("module") or group_row.match(name):
                expand(detail)
            elif name.startswith("Unit"):
                if re.match(r"^Unit\s*\d+$", name, re.I) and detail:
                    expand(detail)
                else:
                    names.append(name.split(" / ")[0].strip())
            else:
                expand(detail)
    else:
        for name, _detail in rows:
            first = name.split(" / ")[0].strip()
            if first and first != "—" and "待补" not in first:
                names.append(first)
    seen: set[str] = set()
    result: list[str] = []
    for n in names:
        if n not in seen:
            seen.add(n)
            result.append(n)
    return result


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    total_files = 0
    total_chapters = 0
    index_rows: list[str] = []
    for subject, grades in GRADES.items():
        outline = BASE / f"_outline_{subject}_{SEMESTER}_latest.md"
        parsed = parse_outline(outline)
        for grade in grades:
            rows = parsed.get(grade, [])
            names = chapter_names(subject, rows)
            if not names:
                print(f"[warn] {subject} g{grade} 无章节名，跳过")
                continue
            doc = {
                "subject": subject,
                "grade": grade,
                "version": VERSION[subject],
                "semester": SEMESTER,
                "chapters": [
                    {
                        "name": n,
                        "order_index": i,
                        "summary": "教材目录骨架（章节占位，待补知识点与题目）",
                        "questions": [],
                    }
                    for i, n in enumerate(names, 1)
                ],
            }
            path = OUT / f"chapters_{subject}_g{grade}_{SEMESTER}_{STAMP}.json"
            path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            total_files += 1
            total_chapters += len(names)
            index_rows.append(f"| {subject} | {grade} | {VERSION[subject]} | {len(names)} | {path.name} |")
    (OUT / "_index.md").write_text(
        "# 下册章节骨架导入批次（2026-11-07）\n\n"
        "只含章节名（`chapters[].questions` 为空），用于让 App 切到下册时目录不空白。\n\n"
        "| 学科 | 年级 | 版本 | 章节数 | 文件 |\n|---|---|---|---|---|\n"
        + "\n".join(index_rows)
        + f"\n\n合计 {total_files} 个文件 / {total_chapters} 个章节。\n",
        encoding="utf-8",
    )
    print(f"[ok] {total_files} 文件 / {total_chapters} 章节 → {OUT}")


if __name__ == "__main__":
    main()
