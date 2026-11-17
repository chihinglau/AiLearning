"""按年级跑一轮全科组卷体检（真实题库、不落库）。

用法：
    python scripts/grade_paper_audit.py --grade 1
    python scripts/grade_paper_audit.py --grade 1 --export-docs

产物：
    docs/content-templates/exports/paper_blueprint_20261116/grade<N>_audit_<yyyymmdd>.csv/.json/.md
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.content import Question, Textbook
from app.models.exam import Exam, ExamBlueprint
from app.models.user import User
from app.services.core_kp_list import build_core_list
from app.services.exam_paper import generate_paper, resolve_scope_chapters
from app.services.exam_paper_docs import build_spec_table, render_answer_sheet_html

SUBJECTS = ("chinese", "math", "english")
SUBJECT_NAMES = {"chinese": "语文", "math": "数学", "english": "英语"}
SEMESTER_NAMES = {"first": "上册", "second": "下册"}
EXAM_TYPE_NAMES = {"unit": "单元", "midterm": "期中", "final": "期末"}


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
        rendered = []
        for option in options:
            if isinstance(option, dict):
                key = str(option.get("key") or option.get("label") or "").strip()
                text = str(
                    option.get("text") or option.get("value")
                    or option.get("content") or ""
                ).strip()
                rendered.append(f"{key}. {text}" if key else text)
            else:
                rendered.append(str(option))
        return rendered
    return []


def _paper_html(exam: Exam, db, with_answer: bool) -> str:
    rows: list[str] = []
    ordered = sorted(exam.questions, key=lambda entry: int(entry.get("section_index", 0)))
    current = None
    number = 0
    for item in ordered:
        question = db.get(Question, int(item["question_id"]))
        if question is None:
            continue
        section = str(item["section_name"])
        if section != current:
            current = section
            group = [e for e in ordered if str(e["section_name"]) == section]
            rows.append(
                f"<h2>{section}（共 {len(group)} 题，"
                f"{sum(float(e.get('score', 0)) for e in group):g} 分）</h2>"
            )
        number += 1
        parts = [
            f'<div class="q"><p class="stem"><b>{number}.</b>'
            f'（{item["score"]:g} 分）</p><p>{_stem(question)}</p>'
        ]
        opts = _options(question)
        if opts:
            parts.append(
                '<ul class="opts">'
                + "".join(f"<li>{opt}</li>" for opt in opts)
                + "</ul>"
            )
        if with_answer:
            script = (question.content or {}).get("script") if isinstance(question.content, dict) else None
            if script:
                parts.append(f'<p class="ans">【听力材料】{script}</p>')
            answer = question.answer
            if isinstance(answer, dict):
                text = str(answer.get("value") or answer.get("text") or answer)
            else:
                text = str(answer)
            parts.append(f'<p class="ans">【答案】{text}</p>')
            if question.analysis:
                parts.append(f'<p class="ans">【解析】{question.analysis}</p>')
            points = (question.content or {}).get("scoring_points") if isinstance(question.content, dict) else None
            if points:
                parts.append('<p class="ans">【评分点】' + "；".join(points) + "</p>")
        else:
            if question.q_type == "listening":
                parts.append('<p class="tip">（听力材料由教师朗读，见教师版）</p>')
            elif question.q_type == "composition":
                parts.append('<p class="tip">（写在答题卡对应位置）</p>')
        parts.append("</div>")
        rows.append("".join(parts))

    title = exam.title + ("（含答案解析）" if with_answer else "")
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
.tip {{ color: #666; font-size: 9.5pt; font-style: italic; }}
</style></head><body>
<h1>{title}</h1>
<div class="meta">学科 {SUBJECT_NAMES.get(exam.subject, exam.subject)} · 年级 {exam.grade} · 满分 {exam.total_score} 分 · 时长 {exam.time_limit_min} 分钟 · 共 {len(exam.questions)} 题</div>
{''.join(rows)}
</body></html>"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--grade", type=int, required=True)
    parser.add_argument("--export-docs", action="store_true")
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    stamp = datetime.now().strftime("%Y%m%d")
    out_root = (
        Path(__file__).resolve().parents[2] / "docs" / "content-templates" / "exports"
        / "paper_blueprint_20261116"
    )
    out_root.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    with SessionLocal() as db:
        admin = db.scalar(select(User).order_by(User.id).limit(1))
        for subject in SUBJECTS:
            books = db.scalars(
                select(Textbook)
                .where(Textbook.subject == subject, Textbook.grade == args.grade)
                .order_by(Textbook.semester)
            ).all()
            if not books:
                rows.append({
                    "grade": args.grade, "subject": subject,
                    "semester": "", "exam_type": "",
                    "result": "NO_TEXTBOOK", "items": 0, "requested": 0,
                    "coverage": 0.0, "reason": "该年级该学科无教材",
                })
                continue
            for book in books:
                for exam_type in ("unit", "midterm", "final"):
                    code = f"g{args.grade}_{subject}_{exam_type}"
                    blueprint = db.scalar(
                        select(ExamBlueprint).where(ExamBlueprint.code == code)
                    )
                    if blueprint is None:
                        rows.append({
                            "grade": args.grade, "subject": subject,
                            "semester": book.semester, "exam_type": exam_type,
                            "result": "NO_BLUEPRINT", "items": 0, "requested": 0,
                            "coverage": 0.0, "reason": "蓝图未写库",
                        })
                        continue
                    scope = {"unit": "unit", "midterm": "half_book", "final": "book"}[exam_type]
                    chapters = resolve_scope_chapters(
                        db, textbook_id=book.id, scope=scope,
                        unit_index=1 if scope == "unit" else None,
                    )
                    # 期末卷按「必考核心考点清单」考核（与生产出卷同口径）：
                    # 全量 kp_coverage 保留为诊断指标，core_coverage 才是达标判据。
                    core_rows = build_core_list(db, book) if exam_type == "final" else []
                    core_ids = {row["kp_id"] for row in core_rows}
                    paper = generate_paper(
                        db, user=admin, blueprint=blueprint, chapter_ids=chapters,
                        seed=args.seed or (20000 + args.grade * 10),
                        core_kps=core_ids or None,
                    )
                    hit_core = 0
                    if core_ids:
                        covered_ids = {
                            int(item.question.knowledge_point_id)
                            for item in paper.items
                            if item.question.knowledge_point_id
                        }
                        hit_core = len(core_ids & covered_ids)
                    result = "REFUSED" if paper.refused else "OK"
                    rows.append({
                        "grade": args.grade,
                        "subject": subject,
                        "semester": book.semester,
                        "exam_type": exam_type,
                        "textbook_id": book.id,
                        "chapters": len(chapters),
                        "result": result,
                        "items": len(paper.items),
                        "requested": paper.requested,
                        "score": round(paper.total_score, 2),
                        "coverage": paper.kp_coverage,
                        "chapter_coverage": paper.chapter_coverage,
                        "kp_universe_size": paper.kp_universe_size,
                        "kp_coverage_cap": paper.kp_coverage_cap,
                        "coverage_normalized": paper.kp_coverage_normalized,
                        "core_total": len(core_ids),
                        "core_hit": hit_core,
                        "core_coverage": (
                            round(hit_core / len(core_ids), 4) if core_ids else 0.0
                        ),
                        "difficulty_mix": json.dumps(paper.difficulty_mix, ensure_ascii=False),
                        "kp_cross_band": paper.kp_cross_band,
                        "crossed_ratio": paper.crossed_ratio,
                        "band_relaxed": paper.band_relaxed,
                        "reason": paper.refuse_reason or "",
                        "shortage": (
                            f"{paper.shortages[0].section_name}:"
                            f"{paper.shortages[0].q_type}"
                            f" {paper.shortages[0].got}/{paper.shortages[0].wanted}"
                            if paper.shortages else ""
                        ),
                    })
                    print(
                        f"g{args.grade} {subject} {book.semester} {exam_type:8s} "
                        f"{result:8s} {len(paper.items):3d}/{paper.requested:3d} "
                        f"cov={paper.kp_coverage:.2f} "
                        f"(上限{paper.kp_coverage_cap:.2f}/归一{paper.kp_coverage_normalized:.2f}) "
                        f"{paper.refuse_reason}"
                    )

                    if args.export_docs and not paper.refused:
                        exam = Exam(
                            title=f"{args.grade}年级{SUBJECT_NAMES[subject]}"
                                  f"{SEMESTER_NAMES.get(book.semester, '')}"
                                  f"{EXAM_TYPE_NAMES[exam_type]}卷（自主题库生成）",
                            subject=subject,
                            grade=args.grade,
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
                            exam_type=exam_type,
                            chapter_ids=chapters,
                        )
                        target = (
                            out_root / f"grade{args.grade}_samples"
                            / f"{subject}_{book.semester}_{exam_type}"
                        )
                        target.mkdir(parents=True, exist_ok=True)
                        (target / "paper.html").write_text(
                            _paper_html(exam, db, with_answer=False), encoding="utf-8"
                        )
                        (target / "paper_teacher.html").write_text(
                            _paper_html(exam, db, with_answer=True), encoding="utf-8"
                        )
                        (target / "answer_sheet.html").write_text(
                            render_answer_sheet_html(db, exam), encoding="utf-8"
                        )
                        (target / "spec_table.json").write_text(
                            json.dumps(
                                build_spec_table(db, exam, blueprint),
                                ensure_ascii=False, indent=2,
                            ),
                            encoding="utf-8",
                        )

    csv_path = out_root / f"grade{args.grade}_audit_{stamp}.csv"
    json_path = out_root / f"grade{args.grade}_audit_{stamp}.json"
    md_path = out_root / f"grade{args.grade}_audit_{stamp}.md"

    fields = [
        "grade", "subject", "semester", "exam_type", "textbook_id", "chapters",
        "result", "items", "requested", "score", "coverage", "chapter_coverage",
        "kp_universe_size", "kp_coverage_cap", "coverage_normalized",
        "core_total", "core_hit", "core_coverage",
        "difficulty_mix", "kp_cross_band", "crossed_ratio",
        "band_relaxed", "reason", "shortage",
    ]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    ok = sum(1 for row in rows if row["result"] == "OK")
    refused = sum(1 for row in rows if row["result"] == "REFUSED")
    lines = [
        f"# G{args.grade} 全科组卷体检（{stamp}）",
        "",
        f"- 样本：{len(rows)} 次组卷（学科 × 上下册 × 3 卷型）",
        f"- 可出卷 **{ok}** / 拒绝 **{refused}** / 其他 {len(rows) - ok - refused}",
        "",
        "| 学科 | 册 | 卷型 | 结果 | 题量 | 总分 | 知识点覆盖(实测/上限) | 归一覆盖 | 难度分布 | 拒绝原因 |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        label = SUBJECT_NAMES.get(row["subject"], row["subject"])
        lines.append(
            f"| {label} | {SEMESTER_NAMES.get(row['semester'], row['semester'])} "
            f"| {EXAM_TYPE_NAMES.get(row['exam_type'], row['exam_type'])} "
            f"| {row['result']} | {row['items']}/{row['requested']} "
            f"| {row.get('score', 0)} "
            f"| {row.get('coverage', 0)}/{row.get('kp_coverage_cap', 0)} "
            f"| {row.get('coverage_normalized', 0)} "
            f"| {row.get('difficulty_mix', '')} | {row.get('reason', '')} |"
        )
    lines.append("")
    lines.append(
        "> 知识点覆盖口径：一题只挂一个知识点，命中上限 = min(知识点池, 题量)。"
        "「归一覆盖」= 实测 / 上限，1.00 表示在题量约束下已达结构上限；"
        "期末卷题量(18/22) 远小于册内知识点池，实测 0.36–0.71 属分母效应，不是语料不足。"
    )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"\n[grade{args.grade}] OK {ok} / REFUSED {refused} / 合计 {len(rows)}")
    print(f"CSV  -> {csv_path}")
    print(f"JSON -> {json_path}")
    print(f"MD   -> {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
