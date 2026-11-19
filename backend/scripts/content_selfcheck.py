"""生产内容自检（只读，不依赖 HTTP 与账号）。

用途：导入内容数据包后、以及每次发版前，确认「题库 + 试卷」在目标库上仍然自洽：
    卷内 question_id 可回查、分值合计等于卷面总分、题干/答案非空、
    g1–g9 × 语数英 × 单元/期中/期末 覆盖矩阵不缺格。

用法（在 backend 目录）：
    python -m scripts.content_selfcheck
    python -m scripts.content_selfcheck --json build/content_selfcheck.json
退出码：0 = 无阻断问题；1 = 存在阻断问题（打印清单）。
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime
from statistics import mean

from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.models.content import Chapter, KnowledgePoint, Question, Textbook
from app.models.exam import Exam, ExamBlueprint

VALID_Q_TYPES = {
    "choice", "multiple", "judge", "fill", "answer", "listening", "composition", "reading",
}
# 习作/解答题的答案形态是评分细则，不做"必须非空"的强判
LENIENT_ANSWER_TYPES = {"composition"}
SUBJECTS = {"chinese", "math", "english"}
EXAM_TYPES = ("unit", "midterm", "final")


def _text_of(content) -> str:
    if isinstance(content, dict):
        for key in ("stem", "question", "text", "title", "prompt"):
            value = content.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return json.dumps(content, ensure_ascii=False)
    return str(content or "")


def main() -> int:
    parser = argparse.ArgumentParser(description="生产内容自检")
    parser.add_argument("--json", default=None, help="把完整报告写入指定 JSON 路径")
    args = parser.parse_args()

    db = SessionLocal()
    issues: list[dict] = []
    warnings: list[dict] = []
    try:
        counts = {
            "textbooks": int(db.scalar(select(func.count()).select_from(Textbook)) or 0),
            "chapters": int(db.scalar(select(func.count()).select_from(Chapter)) or 0),
            "knowledge_points": int(db.scalar(select(func.count()).select_from(KnowledgePoint)) or 0),
            "questions": int(db.scalar(select(func.count()).select_from(Question)) or 0),
            "exam_blueprints": int(db.scalar(select(func.count()).select_from(ExamBlueprint)) or 0),
            "exams": int(db.scalar(select(func.count()).select_from(Exam)) or 0),
            "exams_published": int(
                db.scalar(select(func.count()).select_from(Exam).where(Exam.status == "published")) or 0
            ),
        }

        # ---------- 题目 ----------
        q_types = Counter()
        bad_type = bad_stem = bad_answer = 0
        listening = 0
        for row in db.execute(
            select(Question.id, Question.q_type, Question.content, Question.answer)
        ).all():
            _id, q_type, content, answer = row
            q_types[q_type] += 1
            if q_type == "listening":
                listening += 1
            if q_type not in VALID_Q_TYPES:
                bad_type += 1
                issues.append({"kind": "Q_INVALID_TYPE", "question_id": _id, "detail": q_type})
            if len(_text_of(content)) < 2:
                bad_stem += 1
                issues.append({"kind": "Q_EMPTY_STEM", "question_id": _id})
            if q_type not in LENIENT_ANSWER_TYPES and not str(answer or "").strip():
                bad_answer += 1
                issues.append({"kind": "Q_EMPTY_ANSWER", "question_id": _id, "q_type": q_type})

        # ---------- 试卷 ----------
        papers = db.scalars(select(Exam).where(Exam.status == "published")).all()
        q_by_id = {
            r[0]: r for r in db.execute(select(Question.id, Question.content, Question.q_type)).all()
        }
        matrix = defaultdict(int)
        score_gaps = 0
        for paper in papers:
            items = paper.questions or []
            if not items:
                issues.append({"kind": "PAPER_EMPTY", "exam_id": paper.id})
                continue
            ids = [item.get("question_id") for item in items if isinstance(item, dict)]
            if len(ids) != len(items):
                issues.append({"kind": "PAPER_BAD_ITEM", "exam_id": paper.id})
            missing = [qid for qid in ids if qid not in q_by_id]
            if missing:
                issues.append(
                    {"kind": "PAPER_MISSING_QUESTION", "exam_id": paper.id, "missing": missing[:20]}
                )
            if len(set(ids)) != len(ids):
                issues.append({"kind": "PAPER_DUP_QUESTION", "exam_id": paper.id})
            total = sum(float(item.get("score") or 0) for item in items if isinstance(item, dict))
            if abs(total - float(paper.total_score)) > 0.5:
                score_gaps += 1
                warnings.append(
                    {
                        "kind": "PAPER_SCORE_MISMATCH",
                        "exam_id": paper.id,
                        "title": paper.title,
                        "sum": total,
                        "total_score": paper.total_score,
                    }
                )
            matrix[(paper.grade, paper.subject, paper.exam_type)] += 1

        # ---------- 覆盖矩阵 ----------
        gaps = [
            {"grade": g, "subject": s, "exam_type": t}
            for g in range(1, 10)
            for s in ("chinese", "math", "english")
            for t in EXAM_TYPES
            if matrix[(g, s, t)] == 0
        ]

        grade_subject = defaultdict(int)
        for (g, s, _t), n in matrix.items():
            grade_subject[(g, s)] += n

        report = {
            "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "counts": counts,
            "question_types": dict(q_types),
            "listening_questions": listening,
            "papers_by_grade_subject": {
                f"g{g}_{s}": n for (g, s), n in sorted(grade_subject.items())
            },
            "coverage_gaps": gaps,
            "coverage_gap_count": len(gaps),
            "avg_papers_per_grade_subject": round(mean(grade_subject.values()), 2) if grade_subject else 0,
            "score_mismatch_papers": score_gaps,
            "issues": issues[:200],
            "issue_count": len(issues),
            "warnings": warnings[:100],
            "warning_count": len(warnings),
        }

        print(json.dumps({k: report[k] for k in (
            "counts", "question_types", "listening_questions", "coverage_gap_count",
            "score_mismatch_papers", "issue_count", "warning_count",
        )}, ensure_ascii=False, indent=2))
        if gaps:
            print("覆盖缺口（grade/subject/exam_type）：", json.dumps(gaps[:12], ensure_ascii=False))
        if issues:
            print("阻断问题样例：", json.dumps(issues[:5], ensure_ascii=False))

        if args.json:
            with open(args.json, "w", encoding="utf-8") as fh:
                json.dump(report, fh, ensure_ascii=False, indent=1)
            print(f"报告已写入 {args.json}")
    finally:
        db.close()
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
