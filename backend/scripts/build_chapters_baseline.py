"""只读生成各学科上册章节基线（供每日教研判断章名沿用还是新建）。

用法（在 backend 目录执行）：
    .venv\\Scripts\\python.exe -m scripts.build_chapters_baseline
    .venv\\Scripts\\python.exe -m scripts.build_chapters_baseline --output-dir ..\\docs\\content-templates\\baseline

输出：
    _chapters-baseline_YYYYMMDD.md   按日期归档
    _chapters-baseline_latest.md     固定名，每日任务只读它
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date
from pathlib import Path

from sqlalchemy import select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.content import Chapter, Question, Textbook

SUBJECTS: dict[str, str] = {
    "chinese": "语文",
    "math": "数学",
    "english": "英语",
    "politics": "道法",
    "physics": "物理",
    "chemistry": "化学",
    "biology": "生物",
    "history": "历史",
    "geography": "地理",
}
PLACEHOLDER = "样章·"


def _collect(db):
    textbooks = list(
        db.scalars(
            select(Textbook)
            .where(Textbook.semester == "first")
            .order_by(Textbook.subject, Textbook.grade)
        )
    )
    chapters = list(
        db.scalars(select(Chapter).order_by(Chapter.textbook_id, Chapter.order_index, Chapter.id))
    )
    kp_rows = db.execute(
        select(Question.chapter_id, Question.knowledge_point_id)
        .where(Question.knowledge_point_id.is_not(None))
        .distinct()
    ).all()
    chapter_kps: dict[int, set[int]] = defaultdict(set)
    for chapter_id, kp_id in kp_rows:
        chapter_kps[chapter_id].add(kp_id)
    by_textbook: dict[int, list[Chapter]] = defaultdict(list)
    for chapter in chapters:
        by_textbook[chapter.textbook_id].append(chapter)
    result: dict[str, list[dict]] = defaultdict(list)
    for textbook in textbooks:
        if textbook.grade > 9:  # 每日任务只覆盖义务教育 1-9 年级上册
            continue
        rows = by_textbook.get(textbook.id, [])
        kp_count = len(set().union(*(chapter_kps.get(row.id, set()) for row in rows))) if rows else 0
        result[textbook.subject].append(
            {
                "grade": textbook.grade,
                "version": textbook.version,
                "kp_count": kp_count,
                "chapters": [(row.order_index, row.name) for row in rows],
            }
        )
    return result


def _render_md(result: dict, *, generated: str, source: str) -> str:
    lines = [
        f"# 各学科上册库内已有章节基线（{generated} 实测，只读查库）",
        "",
        "> 用途：定时任务不连数据库，靠这份清单判断「这个年级的章节是沿用库里已有的，还是必须按教材目录新建」。",
        "",
        f"> 数据来源：`{source}`（目标库），`chapters` 按 `textbook_id` 关联 `textbooks`，只取上册（semester=first）。",
        "> 本文件由 `python -m scripts.build_chapters_baseline` 只读生成，**只在内容入库后重建**，不要手写。",
        "",
        "> 判读规则：",
        "",
        "1. 名字以 `样章·` 开头的是**占位章节**——该年级上册尚无真实章节，必须按教材真实目录新建章名，**禁止把知识点挂到样章下**。",
        "",
        "2. 真实章节名一律**沿用同名**，不要另起新名，否则库里会出现两个近似章节。",
        "",
        "3. 同一年级同一本书的章名一旦定下，后续每天沿用，不得中途改名。",
        "",
        "4. 下表里没有的年级 = 库内零章节，全部按教材目录新建。",
        "",
        "5. 拿不准教材目录时只建一个章节、只用确定无疑的章名，宁少建不编造。",
        "",
        "## 汇总",
        "",
        "| 学科 | 覆盖年级（1-9 上册） | 版本 | 已有真实章节的年级 | 需全部新建的年级 |",
        "|---|---|---|---|---|",
    ]
    for subject, grades in sorted(result.items()):
        covered = [item["grade"] for item in grades]
        real = [
            item["grade"]
            for item in grades
            if any(not name.startswith(PLACEHOLDER) for _order, name in item["chapters"])
        ]
        missing = [grade for grade in covered if grade not in real]
        versions = sorted({item["version"] for item in grades})
        lines.append(
            f"| {SUBJECTS.get(subject, subject)}（`{subject}`） "
            f"| {_ranges(covered)} | {'、'.join(versions) or '—'} "
            f"| {_ranges(real) or '无'} | {_ranges(missing) or '无'} |"
        )
    lines += ["", "## 明细", ""]
    for subject, grades in sorted(result.items()):
        versions = sorted({item["version"] for item in grades})
        lines += [
            f"### {SUBJECTS.get(subject, subject)}（`{subject}`，{'、'.join(versions)}）",
            "",
            "| 年级 | 上册已有章节（order_index / name） | 知识点数 | 处理方式 |",
            "|---|---|---|---|",
        ]
        for item in grades:
            if item["chapters"]:
                chapters = "；".join(f"{order} / `{name}`" for order, name in item["chapters"])
                placeholder = all(
                    name.startswith(PLACEHOLDER) for _order, name in item["chapters"]
                )
                how = (
                    "**禁止沿用样章**，按教材目录新建章节"
                    if placeholder
                    else "沿用同名，知识点挂这些真实章节"
                )
            else:
                chapters = "（零章节）"
                how = "按教材目录新建章节"
            lines.append(
                f"| {item['grade']} | {chapters} | {item['kp_count']} | {how} |"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _ranges(grades: list[int]) -> str:
    grades = sorted(set(grades))
    if not grades:
        return ""
    parts: list[str] = []
    start = prev = grades[0]
    for grade in grades[1:]:
        if grade == prev + 1:
            prev = grade
            continue
        parts.append(_part(start, prev))
        start = prev = grade
    parts.append(_part(start, prev))
    return "、".join(parts)


def _part(start: int, end: int) -> str:
    return str(start) if start == end else f"{start}-{end}"


def main() -> int:
    parser = argparse.ArgumentParser(description="生成各学科上册章节基线")
    parser.add_argument(
        "--output-dir",
        default="../docs/content-templates/baseline",
        help="输出目录（默认 ../docs/content-templates/baseline）",
    )
    parser.add_argument("--date", default=date.today().strftime("%Y%m%d"))
    args = parser.parse_args()

    session = SessionLocal()
    try:
        result = _collect(session)
    finally:
        session.close()

    generated = date.today().isoformat()
    source = settings.database_url
    content = _render_md(result, generated=generated, source=source)
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    for name in (f"_chapters-baseline_{args.date}.md", "_chapters-baseline_latest.md"):
        (output / name).write_text(content, encoding="utf-8")
    covered = sum(len(grades) for grades in result.values())
    print(f"章节基线已生成：{output}（学科 {len(result)} 个，年级 {covered} 个）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
