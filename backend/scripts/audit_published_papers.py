"""81 张已发布试卷的全量体检（上机走查前的清障）。

检查项（逐卷逐题）：
  1. 题目数 / 总分 / 题型分布 / 章节覆盖
  2. 重复题（同一 qid 在一卷出现多次）
  3. 悬挂引用（qid 不在 questions 表）
  4. 题干为空 / 答案为空
  5. 年级、学科错配（chapter.grade / question.subject 与卷不一致）
  6. 答案泄漏门禁（复用 question_quality.check_answer_leak）
  7. 听力题音频就绪（listening 缓存文件存在）

用法（backend 下）：
    python -m scripts.audit_published_papers
    python -m scripts.audit_published_papers --out docs/content-templates/exports/paper_audit_YYYYMMDD
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.models.content import Chapter, Question  # noqa: E402
from app.models.exam import Exam  # noqa: E402
from app.services import question_quality, question_speech as speech  # noqa: E402

REPO_DIR = Path(__file__).resolve().parents[2]
AUDIO_DIR = REPO_DIR / "backend" / "build" / "question_audio"

# 以下几类由题型决定，属信息项而非缺陷，不计入待修问题：
#   - 阅读理解题：答案本来就取自短文原文，学生必须读完整段才找得到；
#   - 候选括号提示：「填『是』或『否』」这类题型把选项印在括号里；
#   - 单字构词包含：「语」出现在「成语」里、「雪」出现在「雪花」里，答案不是独立出现的词。
# 注意：构词包含里仍可能混有真提示（如答案「挡」而题干后文整词出现「挡住」），
# 报告会原样保留 reason，教研可逐条抽查。
_INFO_MARKERS = (
    "取自短文原文",
    "阅读理解题型必然",
    "属提示题型，非缺陷",
    "构词包含",
)


def _is_passage_derived(reason: str) -> bool:
    return any(marker in reason for marker in _INFO_MARKERS)


def _stem(question: Question) -> str:
    content = question.content or {}
    if isinstance(content, dict):
        return str(content.get("stem") or "")
    return str(content)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="已发布试卷全量体检")
    parser.add_argument("--out", default="")
    args = parser.parse_args(argv)

    out_dir = Path(
        args.out
        or (
            REPO_DIR
            / "docs"
            / "content-templates"
            / "exports"
            / f"paper_audit_{datetime.now():%Y%m%d}"
        )
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    db = SessionLocal()
    exams = db.execute(
        select(Exam).where(Exam.status == "published").order_by(Exam.grade, Exam.subject, Exam.exam_type)
    ).scalars().all()

    issue_rows: list[dict] = []
    paper_rows: list[dict] = []

    for exam in exams:
        items = exam.questions or []
        qids = [int(it.get("question_id") or 0) for it in items]
        scores = Counter()
        qtypes = Counter()
        chapters: set[int] = set()
        dup: list[int] = []
        orphan: list[int] = []
        empty_stem: list[int] = []
        empty_answer: list[int] = []
        grade_mismatch: list[int] = []
        subject_mismatch: list[int] = []
        leaks: list[tuple[int, str, str]] = []
        audio_missing: list[int] = []

        seen = set()
        for qid in qids:
            if qid in seen:
                dup.append(qid)
            seen.add(qid)

        questions = db.execute(select(Question).where(Question.id.in_(qids))).scalars().all() if qids else []
        by_id = {q.id: q for q in questions}

        for item in items:
            qid = int(item.get("question_id") or 0)
            s = float(item.get("score") or 0)
            scores[(item.get("section_name") or "未分节")] += s
            question = by_id.get(qid)
            if question is None:
                orphan.append(qid)
                continue
            qtypes[question.q_type] += 1
            chapters.add(question.chapter_id)
            stem = _stem(question)
            if not stem.strip():
                empty_stem.append(qid)
            if question.answer in (None, "", {}, []):
                empty_answer.append(qid)
            chapter = db.get(Chapter, question.chapter_id)
            if chapter is not None and int(chapter.grade) != int(exam.grade):
                grade_mismatch.append(qid)
            if question.subject and question.subject != exam.subject:
                subject_mismatch.append(qid)
            leak = question_quality.check_answer_leak(stem, question.answer, question.q_type)
            if leak is not None:
                level, reason = leak
                leaks.append((qid, level, reason))
            if question.q_type == "listening":
                script = speech.listening_script(question)
                voice = speech.voice_for_subject(question.subject)
                key = speech.listening_cache_key(script, voice, 1.0)
                path = AUDIO_DIR / speech.listening_audio_rel_path(key)
                if not path.is_file() or path.stat().st_size == 0:
                    audio_missing.append(qid)

        total_score = sum(float(it.get("score") or 0) for it in items)
        block = [x for x in leaks if x[1] == "block"]
        warn = [x for x in leaks if x[1] == "warn"]
        # 阅读理解题「答案取自短文原文」是题型必然：答案本来就在短文里，学生必须读完才找得到。
        # 归入 INFO 档，不计入待修问题，避免体检报告长期挂着无法消除的噪声。
        info = [x for x in warn if _is_passage_derived(x[2])]
        warn = [x for x in warn if not _is_passage_derived(x[2])]

        paper_rows.append(
            {
                "exam_id": exam.id,
                "title": exam.title,
                "grade": exam.grade,
                "subject": exam.subject,
                "exam_type": exam.exam_type,
                "questions": len(items),
                "total_score": total_score,
                "chapters": len(chapters),
                "q_types": ",".join(f"{k}:{v}" for k, v in sorted(qtypes.items())),
                "dup": len(dup),
                "orphan": len(orphan),
                "empty_stem": len(empty_stem),
                "empty_answer": len(empty_answer),
                "grade_mismatch": len(grade_mismatch),
                "subject_mismatch": len(subject_mismatch),
                "leak_block": len(block),
                "leak_warn": len(warn),
                "listening_audio_missing": len(audio_missing),
            }
        )

        for kind, values, note in (
            ("DUP", dup, "同一题在本卷出现多次"),
            ("ORPHAN", orphan, "题目不在题库"),
            ("EMPTY_STEM", empty_stem, "题干为空"),
            ("EMPTY_ANSWER", empty_answer, "答案为空"),
            ("GRADE_MISMATCH", grade_mismatch, "题目年级与卷年级不一致"),
            ("SUBJECT_MISMATCH", subject_mismatch, "题目学科与卷学科不一致"),
            ("AUDIO_MISSING", audio_missing, "听力音频未就绪"),
        ):
            for qid in values:
                issue_rows.append(
                    {
                        "exam_id": exam.id,
                        "title": exam.title,
                        "grade": exam.grade,
                        "subject": exam.subject,
                        "exam_type": exam.exam_type,
                        "question_id": qid,
                        "issue": kind,
                        "detail": note,
                    }
                )
        for qid, level, reason in leaks:
            bucket = "LEAK_" + level.upper()
            if level == "warn" and _is_passage_derived(reason):
                bucket = "LEAK_INFO"
            issue_rows.append(
                {
                    "exam_id": exam.id,
                    "title": exam.title,
                    "grade": exam.grade,
                    "subject": exam.subject,
                    "exam_type": exam.exam_type,
                    "question_id": qid,
                    "issue": bucket,
                    "detail": reason,
                }
            )
    paper_csv = out_dir / "paper_summary.csv"
    issue_csv = out_dir / "issue_detail.csv"
    with paper_csv.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(paper_rows[0].keys()))
        writer.writeheader()
        writer.writerows(paper_rows)
    with issue_csv.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(issue_rows[0].keys()) if issue_rows else [
            "exam_id", "title", "grade", "subject", "exam_type", "question_id", "issue", "detail"
        ])
        writer.writeheader()
        writer.writerows(issue_rows)

    kinds = Counter(row["issue"] for row in issue_rows)
    hard_rows = [row for row in issue_rows if row["issue"] != "LEAK_INFO"]
    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "papers": len(paper_rows),
        "issues": len(hard_rows),
        "info": len(issue_rows) - len(hard_rows),
        "by_kind": dict(kinds),
        "papers_with_issues": sum(
            1
            for row in paper_rows
            if any(
                row[key]
                for key in (
                    "dup", "orphan", "empty_stem", "empty_answer",
                    "grade_mismatch", "subject_mismatch", "leak_block",
                    "listening_audio_missing",
                )
            )
        ),
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\n产物目录：{out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
