"""试卷配套文档（PG-05）：双向细目表、答题卡、跨卷重题去重、抽检抽样。

- `build_spec_table`：把蓝图分节与卷内实际题目对齐，输出可打印/可审计的双向细目表；
- `render_answer_sheet_html`：生成 A4 可直接打印的答题卡（不含题干与答案）；
- `recent_question_ids`：取同年级同学科同卷型最近 N 张卷的题号，用于跨卷重题去重；
- `sample_exams`：按比例稳定随机抽取待复核的自建卷（抽检 10%）。
"""

from __future__ import annotations

import html
import random
from datetime import datetime, timezone
from typing import Iterable, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.content import Chapter, KnowledgePoint, Question
from app.models.exam import Exam, ExamBlueprint


BAND_LABELS = {"easy": "易", "medium": "中", "hard": "难"}


def _band_of_section(section: dict) -> str:
    band = section.get("band")
    if band:
        return str(band)
    difficulty = section.get("difficulty")
    if isinstance(difficulty, (list, tuple)) and difficulty:
        low = min(difficulty)
        return "easy" if low <= 1 else ("medium" if low <= 3 else "hard")
    return "medium"


def build_spec_table(
    db: Session, exam: Exam, blueprint: Optional[ExamBlueprint]
) -> dict:
    """双向细目表：计划（蓝图）vs 实际（卷内题目），逐节列出题型/题量/分值/难度/知识点/章节。"""
    sections = list(blueprint.sections) if blueprint else []
    questions = {
        q.id: q
        for q in db.scalars(
            select(Question).where(
                Question.id.in_([int(item["question_id"]) for item in exam.questions])
            )
        )
    }
    chapter_names = {
        chapter.id: chapter.name
        for chapter in db.scalars(
            select(Chapter).where(
                Chapter.id.in_([q.chapter_id for q in questions.values() if q.chapter_id])
            )
        )
    }
    kp_names = {
        kp.id: kp.name
        for kp in db.scalars(
            select(KnowledgePoint).where(
                KnowledgePoint.id.in_(
                    [q.knowledge_point_id for q in questions.values() if q.knowledge_point_id]
                )
            )
        )
    }

    items_by_section: dict[int, list[dict]] = {}
    for item in exam.questions:
        index = int(item.get("section_index", 0))
        question = questions.get(int(item["question_id"]))
        if question is None:
            continue
        items_by_section.setdefault(index, []).append(
            {
                "question_id": question.id,
                "score": float(item.get("score", 0)),
                "q_type": question.q_type,
                "difficulty": question.difficulty,
                "knowledge_point": kp_names.get(question.knowledge_point_id, ""),
                "chapter": chapter_names.get(question.chapter_id, ""),
            }
        )

    rows: list[dict] = []
    for index, section in enumerate(sections):
        actual = items_by_section.get(index, [])
        planned_count = int(section.get("count", 0))
        planned_score = float(planned_count * float(section.get("score_each", 0)))
        rows.append(
            {
                "section_index": index,
                "section_name": section.get("name", f"第{index + 1}节"),
                "q_type": section.get("q_type"),
                "band": _band_of_section(section),
                "planned_count": planned_count,
                "planned_score": planned_score,
                "actual_count": len(actual),
                "actual_score": round(sum(item["score"] for item in actual), 2),
                "knowledge_points": sorted(
                    {item["knowledge_point"] for item in actual if item["knowledge_point"]}
                ),
                "chapters": sorted(
                    {item["chapter"] for item in actual if item["chapter"]}
                ),
                "questions": actual,
            }
        )

    # 卷内自建卷没有蓝图时（历史数据），按题目原始 section_index 聚合
    if not sections:
        for index in sorted(items_by_section):
            actual = items_by_section[index]
            rows.append(
                {
                    "section_index": index,
                    "section_name": f"第{index + 1}节",
                    "q_type": actual[0]["q_type"] if actual else None,
                    "band": "medium",
                    "planned_count": len(actual),
                    "planned_score": round(sum(item["score"] for item in actual), 2),
                    "actual_count": len(actual),
                    "actual_score": round(sum(item["score"] for item in actual), 2),
                    "knowledge_points": sorted(
                        {i["knowledge_point"] for i in actual if i["knowledge_point"]}
                    ),
                    "chapters": sorted({i["chapter"] for i in actual if i["chapter"]}),
                    "questions": actual,
                }
            )

    total_actual = round(sum(row["actual_score"] for row in rows), 2)
    kp_all = sorted({kp for row in rows for kp in row["knowledge_points"]})
    return {
        "exam_id": exam.id,
        "title": exam.title,
        "subject": exam.subject,
        "grade": exam.grade,
        "exam_type": exam.exam_type,
        "blueprint_code": blueprint.code if blueprint else None,
        "blueprint_name": blueprint.name if blueprint else None,
        "total_score": exam.total_score,
        "time_limit_min": exam.time_limit_min,
        "question_count": sum(row["actual_count"] for row in rows),
        "actual_score_total": total_actual,
        "score_matches": abs(total_actual - float(exam.total_score)) < 0.01,
        "knowledge_point_count": len(kp_all),
        "sections": rows,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _answer_area(row: dict, start: int = 1) -> str:
    q_type = (row.get("q_type") or "").lower()
    count = int(row.get("actual_count") or 0)
    if q_type in {"choice", "judge", "multiple"}:
        cells = "".join(
            f'<span class="opt">（<b>{n}</b>）</span>' for n in range(start, start + count)
        )
        return f'<div class="opts">{cells}</div>'
    if q_type == "fill":
        lines = "".join(
            f'<div class="line"><span>{n}.</span>'
            + "".join('<i class="blank"></i>' for _ in range(2))
            + "</div>"
            for n in range(start, start + count)
        )
        return lines
    # answer / composition / listening 等主观题：给足书写行
    rows_per = 6 if q_type != "composition" else 14
    blocks = "".join(
        '<div class="subj"><div class="subj-no">%d.</div><div class="subj-lines">%s</div></div>'
        % (n, "".join('<div class="line"></div>' for _ in range(rows_per)))
        for n in range(start, start + count)
    )
    return blocks


def render_answer_sheet_html(db: Session, exam: Exam) -> str:
    """A4 打印版答题卡：只含题号与作答区，不含题干与答案。"""
    blueprint = db.get(ExamBlueprint, exam.blueprint_id) if exam.blueprint_id else None
    spec = build_spec_table(db, exam, blueprint)
    subject_names = {
        "chinese": "语文", "math": "数学", "english": "英语",
        "physics": "物理", "chemistry": "化学", "biology": "生物",
        "history": "历史", "geography": "地理", "politics": "道德与法治",
    }
    title = html.escape(exam.title)
    subject = subject_names.get(exam.subject, exam.subject)

    section_blocks = []
    number = 0
    for row in spec["sections"]:
        name = html.escape(str(row["section_name"]))
        score = row["actual_score"]
        hint = {
            "choice": "每题仅填一个选项字母",
            "judge": "正确写“√”，错误写“×”",
            "fill": "按题号填写答案，字迹清晰",
            "answer": "写出解题过程与最终答案",
            "composition": "不少于规定字数，字迹工整",
            "listening": "听力作答请填写选项或单词",
        }.get((row["q_type"] or "").lower(), "按题号作答")
        section_blocks.append(
            f'<section><h3>{name}（共 {row["actual_count"]} 题，{score:g} 分）'
            f'</h3><p class="hint">{hint}</p>{_answer_area(row, number + 1)}</section>'
        )
        number += int(row["actual_count"])

    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>答题卡 · {title}</title>
<style>
  @page {{ size: A4; margin: 16mm; }}
  body {{ font-family: "Microsoft YaHei", "PingFang SC", sans-serif; color: #111; font-size: 12pt; }}
  h1 {{ font-size: 16pt; text-align: center; margin: 0 0 4mm; }}
  .meta {{ margin: 0 0 6mm; font-size: 11pt; }}
  .meta table {{ width: 100%; border-collapse: collapse; }}
  .meta td {{ border: 1px solid #333; padding: 3mm; }}
  section {{ margin-bottom: 6mm; page-break-inside: avoid; }}
  h3 {{ font-size: 12.5pt; margin: 0 0 2mm; }}
  .hint {{ font-size: 9.5pt; color: #555; margin: 0 0 2mm; }}
  .opts {{ display: flex; flex-wrap: wrap; gap: 6mm; }}
  .opt {{ min-width: 18mm; }}
  .line {{ border-bottom: 1px solid #999; height: 8mm; margin: 2mm 0; display: flex; align-items: center; gap: 4mm; }}
  .blank {{ display: inline-block; width: 30mm; border-bottom: 1px solid #999; height: 6mm; }}
  .subj {{ display: flex; gap: 3mm; }}
  .subj-no {{ width: 10mm; font-weight: 600; }}
  .subj-lines {{ flex: 1; }}
  .foot {{ margin-top: 8mm; font-size: 9pt; color: #666; text-align: center; }}
</style></head><body>
<h1>答题卡 · {title}</h1>
<div class="meta"><table>
<tr><td>姓名：</td><td>班级：</td><td>学号：</td></tr>
<tr><td>学科：{html.escape(subject)}</td><td>满分：{exam.total_score} 分</td>
<td>时长：{exam.time_limit_min} 分钟</td></tr>
</table></div>
{''.join(section_blocks)}
<div class="foot">本答题卡由系统按卷面结构自动生成，题号与分值与试卷一一对应。</div>
</body></html>"""


def recent_question_ids(
    db: Session,
    *,
    subject: str,
    grade: int,
    exam_type: str,
    limit: int = 3,
    before_exam_id: Optional[int] = None,
) -> list[int]:
    """同年级 + 同学科 + 同卷型最近 `limit` 张自建卷的题号（用于跨卷重题去重）。

    只统计在架卷（published/draft）：已下架（offline）的卷不再面向学生，其题号不应
    继续占用题池——否则旧走下架卷会持续挤占稀缺题型（实测英语听力因此短缺而拒绝出卷）。
    """
    stmt = select(Exam).where(
        Exam.subject == subject,
        Exam.grade == grade,
        Exam.exam_type == exam_type,
        Exam.source == "generated",
        Exam.status != "offline",
    )
    if before_exam_id is not None:
        stmt = stmt.where(Exam.id < before_exam_id)
    exams = db.scalars(stmt.order_by(Exam.id.desc()).limit(limit)).all()
    ids: list[int] = []
    for exam in exams:
        for item in exam.questions or []:
            try:
                ids.append(int(item["question_id"]))
            except (KeyError, TypeError, ValueError):
                continue
    return ids


def sample_exams(
    exams: Iterable[Exam], ratio: float, seed: Optional[int] = None
) -> list[Exam]:
    """按比例稳定随机抽检：同 seed 结果一致，便于复现与留痕。"""
    rows = sorted(exams, key=lambda exam: exam.id)
    if not rows or ratio <= 0:
        return []
    count = max(1, int(round(len(rows) * min(ratio, 1.0))))
    rng = random.Random(seed)
    return sorted(rng.sample(rows, min(count, len(rows))), key=lambda exam: exam.id)
