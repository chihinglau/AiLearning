"""按卷生成题目快照清单（教研批量扫题用）。

输出两份 CSV 到 docs/content-templates/exports/paper_audit_20261118/：
  - question_snapshot.csv：一行一题，含年级/卷名/阶段/学科/题序/分节/题型/题干/选项/答案/分值
  - snapshot_issues.csv：自动体检出的可机检异常（空题干、题干过短、选择题选项不足、
    答案对不上选项、选项重复、残留占位词）

用法（backend 下）：
    python -m scripts.snapshot_papers
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal  # noqa: E402
from app.models.content import Question  # noqa: E402
from app.models.exam import Exam  # noqa: E402

OUT_DIR = Path(__file__).resolve().parents[2] / "docs" / "content-templates" / "exports" / "paper_audit_20261118"

PLACEHOLDER_PATTERN = re.compile(
    r"(TODO|FIXME|xxx|XXX|待补|待定|走查|自建题库|mock|placeholder|None|null|\?\?\?)"
)
SHORT_STEM_LIMIT = 4


def _stem(question: Question) -> str:
    content = question.content or {}
    if isinstance(content, dict):
        for key in ("stem", "question", "text", "title"):
            value = content.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return json.dumps(content, ensure_ascii=False)
    return str(content)


def _passage(question: Question) -> str:
    content = question.content or {}
    if isinstance(content, dict):
        for key in ("passage", "material", "context"):
            value = content.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return ""


def _options(question: Question) -> list[str]:
    options = question.options or []
    if not isinstance(options, list):
        return []
    texts: list[str] = []
    for option in options:
        if isinstance(option, dict):
            label = option.get("label") or option.get("key") or ""
            text = option.get("text") or option.get("content") or option.get("value") or ""
            texts.append(f"{label}. {text}".strip(". ") if label else str(text))
        else:
            texts.append(str(option))
    return texts


def _answer_keys(question: Question) -> list[str]:
    answer = question.answer or {}
    raw: list[str] = []
    if isinstance(answer, dict):
        for key in ("value", "answer", "correct", "choices", "keys", "blanks"):
            value = answer.get(key)
            if value is None:
                continue
            if isinstance(value, (list, tuple)):
                raw.extend(str(item) for item in value)
            else:
                raw.append(str(value))
    elif isinstance(answer, (list, tuple)):
        raw.extend(str(item) for item in answer)
    else:
        raw.append(str(answer))
    return [item.strip() for item in raw if item.strip()]


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    db = SessionLocal()
    exams = (
        db.query(Exam)
        .filter(Exam.status == "published")
        .order_by(Exam.grade, Exam.subject, Exam.exam_type)
        .all()
    )
    q_map = {q.id: q for q in db.query(Question).all()}

    snapshot_rows: list[dict] = []
    issue_rows: list[dict] = []

    for exam in exams:
        items = exam.questions or []
        for index, item in enumerate(items, start=1):
            qid = int(item.get("question_id") or item.get("id") or 0)
            question = q_map.get(qid)
            score = item.get("score")
            section = item.get("section_name") or ""
            base = {
                "grade": exam.grade,
                "exam_id": exam.id,
                "title": exam.title,
                "subject": exam.subject,
                "exam_type": exam.exam_type,
                "q_no": index,
                "section": section,
                "score": score,
            }
            if question is None:
                issue_rows.append({**base, "qid": qid, "code": "MISSING_QUESTION", "detail": "题号不在题库"})
                continue

            stem = _stem(question)
            options = _options(question)
            answers = _answer_keys(question)
            snapshot_rows.append(
                {
                    **base,
                    "qid": qid,
                    "q_type": question.q_type,
                    "difficulty": question.difficulty,
                    "stem": stem,
                    "passage": _passage(question),
                    "options": " | ".join(options),
                    "answer": " / ".join(answers),
                }
            )

            codes: list[tuple[str, str]] = []
            if not stem:
                codes.append(("EMPTY_STEM", "题干为空"))
            elif len(stem.strip()) < SHORT_STEM_LIMIT:
                codes.append(("SHORT_STEM", f"题干仅 {len(stem.strip())} 字：{stem}"))
            if PLACEHOLDER_PATTERN.search(stem) or (options and PLACEHOLDER_PATTERN.search(" ".join(options))):
                codes.append(("PLACEHOLDER", "题干/选项残留占位或内部词"))
            if question.q_type == "choice":
                if not options:
                    codes.append(("CHOICE_NO_OPTIONS", "选择题无选项"))
                elif len(options) < 3:
                    codes.append(("CHOICE_LT3", f"选择题仅 {len(options)} 个选项"))
                if answers and options:
                    labels = {opt.split(".")[0].strip().upper() for opt in options}
                    unmatched = [
                        answer for answer in answers
                        if answer.upper() not in labels and not any(answer in opt for opt in options)
                    ]
                    if unmatched:
                        codes.append(("ANSWER_NOT_IN_OPTIONS", f"答案 {unmatched} 不在选项中"))
            if options and len(set(options)) != len(options):
                codes.append(("DUP_OPTIONS", "存在重复选项"))
            if question.q_type == "fill" and not re.search(r"（|\(|_|＿", stem):
                codes.append(("FILL_NO_BLANK", "填空题题干没有留空标记"))
            for code, detail in codes:
                issue_rows.append({**base, "qid": qid, "code": code, "detail": detail})

    snapshot_path = OUT_DIR / "question_snapshot.csv"
    with snapshot_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(snapshot_rows[0].keys()))
        writer.writeheader()
        writer.writerows(snapshot_rows)

    issue_path = OUT_DIR / "snapshot_issues.csv"
    with issue_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=["grade", "exam_id", "title", "subject", "exam_type", "q_no", "section", "score", "qid", "code", "detail"])
        writer.writeheader()
        writer.writerows(issue_rows)

    print(f"试卷数 {len(exams)}，题目快照 {len(snapshot_rows)} 行 → {snapshot_path}")
    print(f"可机检异常 {len(issue_rows)} 条 → {issue_path}")
    by_code: dict[str, int] = {}
    for row in issue_rows:
        by_code[row["code"]] = by_code.get(row["code"], 0) + 1
    for code, count in sorted(by_code.items(), key=lambda kv: -kv[1]):
        print(f"  {code}: {count}")

    # 按卷生成可读 Markdown，供教研逐卷扫题
    md_dir = OUT_DIR / "snapshots"
    md_dir.mkdir(parents=True, exist_ok=True)
    grouped: dict[tuple[int, int], list[dict]] = {}
    for row in snapshot_rows:
        grouped.setdefault((row["exam_id"], row["grade"]), []).append(row)
    exam_by_id = {exam.id: exam for exam in exams}
    index_lines = ["# 81 卷题目快照索引", "", "每卷一个 Markdown 文件，按题序展开题干/选项/答案，供教研逐卷扫题。", ""]
    for (exam_id, _grade), rows_of_paper in sorted(grouped.items(), key=lambda kv: (kv[1][0]["grade"], kv[1][0]["subject"], kv[1][0]["exam_type"])):
        exam = exam_by_id.get(exam_id)
        if exam is None:
            continue
        first = rows_of_paper[0]
        filename = f"g{first['grade']}-{first['subject']}-{first['exam_type']}.md"
        lines = [f"# {exam.title}", "", f"- 年级：{first['grade']}", f"- 学科：{first['subject']}", f"- 阶段：{first['exam_type']}", f"- 题数：{len(rows_of_paper)}", ""]
        current_section = None
        for row in rows_of_paper:
            if row["section"] != current_section:
                current_section = row["section"]
                lines.append(f"## {current_section or '（未分节）'}")
                lines.append("")
            lines.append(f"**{row['q_no']}. [{row['q_type']}]（{row['score']} 分）** {row['stem']}")
            if row["passage"]:
                lines.append("")
                lines.append(f"> 材料：{row['passage']}")
            if row["options"]:
                lines.append("")
                for option in row["options"].split(" | "):
                    lines.append(f"- {option}")
            lines.append("")
            lines.append(f"答案：{row['answer']}")
            lines.append("")
        out_file = md_dir / filename
        out_file.write_text("\n".join(lines), encoding="utf-8")
        index_lines.append(f"- [{exam.title}]({filename}) — {len(rows_of_paper)} 题")
    (md_dir / "README.md").write_text("\n".join(index_lines) + "\n", encoding="utf-8")
    print(f"按卷 Markdown {len(grouped)} 份 → {md_dir}")
    db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
