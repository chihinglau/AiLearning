"""导出样卷文档（PG-05）：细目表 + 试卷 PDF 前置 HTML + 答题卡。

用法：
    python scripts/sample_paper_docs.py --blueprint g3_math_unit --grade 3 --subject math --scope unit --unit-index 1
产物写入 docs/content-templates/exports/paper_blueprint_20261116/sample_<blueprint>/
"""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Optional

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.content import Question, Textbook
from app.models.exam import Exam, ExamBlueprint
from app.models.user import User
from app.services.exam_paper import generate_paper, resolve_scope_chapters
from app.services.exam_paper_docs import build_spec_table, render_answer_sheet_html


SUBJECT_NAMES = {
    "chinese": "语文", "math": "数学", "english": "英语",
    "physics": "物理", "chemistry": "化学", "biology": "生物",
    "history": "历史", "geography": "地理", "politics": "道德与法治",
}


def _stem(question: Question) -> str:
    content = question.content or {}
    if isinstance(content, dict):
        return str(content.get("stem") or content.get("text") or "")
    return str(content)


def _options(question: Question) -> list[str]:
    options = question.options
    if not options and isinstance(question.content, dict):
        options = question.content.get("options")
    if isinstance(options, dict):
        options = options.get("items") or options
    if isinstance(options, dict):
        return [f"{key}. {value}" for key, value in options.items()]
    if isinstance(options, list):
        rendered: list[str] = []
        for option in options:
            if isinstance(option, dict):
                key = str(option.get("key") or option.get("label") or "").strip()
                text = str(
                    option.get("text")
                    or option.get("value")
                    or option.get("content")
                    or ""
                ).strip()
                rendered.append(f"{key}. {text}" if key else text)
            else:
                rendered.append(str(option))
        return rendered
    return []


def _paper_html(exam: Exam, blueprint: ExamBlueprint, db, with_answer: bool) -> str:
    rows: list[str] = []
    ordered = sorted(exam.questions, key=lambda entry: int(entry.get("section_index", 0)))
    current_section: Optional[str] = None
    number = 0
    for item in ordered:
        question = db.get(Question, int(item["question_id"]))
        if question is None:
            continue
        section_name = str(item["section_name"])
        if section_name != current_section:
            current_section = section_name
            section_items = [
                entry for entry in ordered if str(entry["section_name"]) == section_name
            ]
            section_score = sum(float(entry.get("score", 0)) for entry in section_items)
            rows.append(
                f"<h2>{html.escape(section_name)}（共 {len(section_items)} 题，"
                f"{section_score:g} 分）</h2>"
            )
        number += 1
        parts = [
            f'<div class="q"><p class="stem"><b>{number}.</b>'
            f'（{item["score"]:g} 分）</p>'
        ]
        parts.append(f'<p>{html.escape(_stem(question))}</p>')
        opts = _options(question)
        if opts:
            parts.append('<ul class="opts">' + "".join(
                f"<li>{html.escape(opt)}</li>" for opt in opts
            ) + "</ul>")
        if with_answer:
            answer = question.answer
            if isinstance(answer, dict):
                answer_text = str(
                    answer.get("value")
                    or answer.get("text")
                    or answer.get("answer")
                    or answer.get("content")
                    or json.dumps(answer, ensure_ascii=False)
                )
            elif isinstance(answer, list):
                answer_text = "；".join(
                    str(item.get("value") or item) if isinstance(item, dict) else str(item)
                    for item in answer
                )
            else:
                answer_text = str(answer)
            parts.append(
                f'<p class="ans">【答案】{html.escape(answer_text)}</p>'
            )
            if question.analysis:
                parts.append(
                    f'<p class="ans">【解析】{html.escape(str(question.analysis))}</p>'
                )
        parts.append("</div>")
        rows.append("".join(parts))

    title = html.escape(exam.title + ("（含答案解析·教师版）" if with_answer else ""))
    return f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<title>{title}</title><style>
@page {{ size: A4; margin: 16mm; }}
body {{ font-family: "Microsoft YaHei", sans-serif; font-size: 11.5pt; line-height: 1.7; }}
h1 {{ font-size: 15pt; text-align: center; }}
.meta {{ text-align:center; color:#555; font-size:10pt; margin-bottom:6mm; }}
h2 {{ font-size: 12.5pt; margin: 8mm 0 3mm; border-left: 3px solid #333; padding-left: 3mm; }}
.q {{ margin-bottom: 4mm; page-break-inside: avoid; }}
.stem {{ font-weight: 600; margin: 0; }}
.opts {{ margin: 1mm 0 0 6mm; padding: 0; list-style: none; }}
.ans {{ color: #1a5c1a; font-size: 10pt; }}
</style></head><body>
<h1>{title}</h1>
<div class="meta">学科 {html.escape(SUBJECT_NAMES.get(exam.subject, exam.subject))} · 年级 {exam.grade} · 满分 {exam.total_score} 分 · 时长 {exam.time_limit_min} 分钟 · 共 {len(exam.questions)} 题</div>
{"".join(rows)}
</body></html>"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--blueprint", required=True)
    parser.add_argument("--subject", default="math")
    parser.add_argument("--grade", type=int, required=True)
    parser.add_argument("--scope", default="unit", choices=["unit", "half_book", "book"])
    parser.add_argument("--unit-index", type=int, default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--out-root", default=None)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        blueprint = db.scalar(
            select(ExamBlueprint).where(ExamBlueprint.code == args.blueprint)
        )
        if blueprint is None:
            print(f"[sample] 蓝图不存在：{args.blueprint}")
            return 2
        textbooks = db.scalars(
            select(Textbook)
            .where(Textbook.subject == args.subject, Textbook.grade == args.grade)
            .order_by(Textbook.id)
        ).all()
        if not textbooks:
            print("[sample] 未找到对应教材")
            return 2
        textbook = textbooks[0]
        chapter_ids = resolve_scope_chapters(
            db,
            textbook_id=textbook.id,
            scope=args.scope,
            unit_index=args.unit_index,
        )
        print(f"[sample] 教材 {textbook.id}（{textbook.grade} 年级 {textbook.semester}）章节 {len(chapter_ids)} 个")
        if not chapter_ids:
            print("[sample] 范围内无章节")
            return 2
        user = db.scalar(select(User).where(User.role == "admin")) or db.scalar(select(User))
        paper = generate_paper(
            db, user=user, blueprint=blueprint, chapter_ids=chapter_ids,
            seed=args.seed,
        )
        if paper.refused:
            print(f"[sample] 拒绝出卷：{paper.refuse_reason}")
            for shortage in paper.shortages:
                print(
                    f"  - {shortage.section_name} 需要 {shortage.wanted} 题，"
                    f"实际 {shortage.got}（{shortage.reason}）"
                )
            return 1

        exam = Exam(
            title=blueprint.name,
            subject=blueprint.subject,
            grade=blueprint.grade or args.grade,
            source="generated",
            total_score=int(round(paper.total_score)),
            time_limit_min=blueprint.time_limit_min,
            questions=[
                {
                    "question_id": item.question.id,
                    "score": item.score,
                    "section_index": item.section_index,
                    "section_name": item.section_name,
                }
                for item in paper.items
            ],
            blueprint_id=blueprint.id,
            exam_type=blueprint.exam_type,
            chapter_ids=chapter_ids,
        )

        root = Path(args.out_root) if args.out_root else None
        if root is None:
            root = Path(__file__).resolve().parents[2] / "docs" / "content-templates" / "exports" / "paper_blueprint_20261116" / f"sample_{args.blueprint}"
        root.mkdir(parents=True, exist_ok=True)

        spec = build_spec_table(db, exam, blueprint)
        (root / "spec_table.json").write_text(
            json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (root / "answer_sheet.html").write_text(
            render_answer_sheet_html(db, exam), encoding="utf-8"
        )
        (root / "paper.html").write_text(
            _paper_html(exam, blueprint, db, with_answer=False), encoding="utf-8"
        )
        (root / "paper_teacher.html").write_text(
            _paper_html(exam, blueprint, db, with_answer=True), encoding="utf-8"
        )
        summary = {
            "blueprint": blueprint.code,
            "textbook_id": textbook.id,
            "chapter_ids": chapter_ids,
            "question_count": len(paper.items),
            "total_score": paper.total_score,
            "kp_coverage": paper.kp_coverage,
            "chapter_coverage": paper.chapter_coverage,
            "difficulty_mix": paper.difficulty_mix,
            "band_relaxed": paper.band_relaxed,
            "seed": paper.seed,
            "score_matches": spec["score_matches"],
            "out_dir": str(root),
        }
        (root / "summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
