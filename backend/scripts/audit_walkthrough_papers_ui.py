"""对 81 张走查卷做「学生侧展示」全量结构审计。

真机只能抽样看渲染，但一整卷里哪些题在学生会卡住、哪些题根本没法作答，
是可以在数据结构层面 100% 判定的。本脚本检查：

  1. LR-1 听力题是否带音频资源（Question 模型无 audio 列，只能藏在 content/meta）
  2. LR-2 选择题选项数 < 2 / 选项文本重复 / 选项为空
  3. LR-3 填空/解答题题干是否留出作答空位（____ 或 括号）
  4. LR-4 习作/作文题是否给出题目要求与字数提示
  5. LR-5 答案是否泄露到题干或选项（正确答案原文出现在 stem）
  6. LR-6 同卷内题干重复
  7. LR-7 分值合计是否等于卷面 total_score
  8. LR-8 题干长度超限（首屏不可读，> 220 字）
  9. LR-9 大题（section）缺失或分组断层

输出：控制台汇总 + exports/ui_audit_<date>/paper_ui_audit.csv（逐卷）
      exports/ui_audit_<date>/issue_detail.csv（逐问题）
"""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter, OrderedDict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.exam import Exam

OUT_DIR = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "content-templates"
    / "exports"
    / "ui_audit_20261118"
)
STEM_LIMIT = 220


def _stem(q: dict) -> str:
    c = q.get("content") or {}
    for key in ("stem", "question", "text"):
        if isinstance(c.get(key), str) and c[key].strip():
            return c[key].strip()
    return ""


def _options(q: dict) -> list[dict]:
    raw = q.get("options") or []
    out = []
    for o in raw:
        if isinstance(o, dict):
            out.append(o)
        elif isinstance(o, str):
            out.append({"key": "", "text": o})
    return out


def _answer_text(q: dict) -> str:
    a = q.get("answer")
    if isinstance(a, dict):
        return str(a.get("value") or a.get("text") or "")
    if isinstance(a, list):
        return "、".join(str(x) for x in a)
    return str(a or "")


def _has_audio(q: dict) -> bool:
    """只看结构化字段：题目正文里的「听录音」三个字不算有音频。"""
    keys = {"audio", "audio_url", "audio_path", "audio_file", "media", "media_url", "mp3", "wav"}
    stack = [q.get("content"), q.get("meta"), q.get("media")]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            for k, v in node.items():
                if str(k).lower() in keys and v:
                    return True
                if isinstance(v, (dict, list)):
                    stack.append(v)
        elif isinstance(node, list):
            stack.extend(node)
    return False


def load_questions(db, ids: list[int]) -> dict[int, dict]:
    """试卷 JSON 只存 question_id + score + section，题目正文要回表取。"""
    from app.models.content import Question

    out: dict[int, dict] = {}
    if not ids:
        return out
    for q in db.scalars(select(Question).where(Question.id.in_(ids))).all():
        out[q.id] = {
            "q_type": q.q_type,
            "content": q.content or {},
            "options": q.options or [],
            "answer": q.answer or {},
        }
    return out


def audit_paper(exam: Exam, bank: dict[int, dict]) -> tuple[dict, list[dict]]:
    refs = exam.questions or []
    qs = []
    for ref in refs:
        qid = ref.get("question_id")
        body = bank.get(qid)
        if body is None:
            qs.append({"q_type": "missing", "content": {}, "options": [], "answer": {}})
        else:
            qs.append(body)
    # 保留原始 score/section，覆盖到题目体上
    for i, ref in enumerate(refs):
        qs[i]["score"] = ref.get("score")
        qs[i]["section_name"] = ref.get("section_name")
        qs[i]["question_id"] = ref.get("question_id")
    issues: list[dict] = []
    types = Counter()
    sections: list[str] = []
    total = 0
    stems: Counter[str] = Counter()

    def add(code: str, level: str, idx, detail: str):
        issues.append(
            {
                "exam_id": exam.id,
                "title": exam.title,
                "q_no": "" if idx is None else idx,
                "code": code,
                "level": level,
                "detail": detail,
            }
        )

    for i, q in enumerate(qs, start=1):
        qt = (q.get("q_type") or q.get("type") or "unknown").lower()
        types[qt] += 1
        score = q.get("score") or 0
        try:
            total += float(score)
        except Exception:
            pass
        stem = _stem(q)
        stems[stem] += 1
        sec = q.get("section_name") or q.get("section") or ""
        if sec and (not sections or sections[-1] != sec):
            sections.append(sec)

        if not stem:
            add("LR-0", "P0", i, "题干为空")

        # LR-1 听力题必须有音频，否则学生无法作答
        if qt in ("listening", "listen"):
            if not _has_audio(q):
                add("LR-1", "P0", i, "听力题无任何音频字段（学生无法作答）")

        # LR-2 选择题
        if qt in ("choice", "multiple"):
            opts = _options(q)
            if len(opts) < 2:
                add("LR-2", "P0", i, f"选项数 {len(opts)} < 2")
            else:
                texts = [(o.get("text") or "").strip() for o in opts]
                if any(not t for t in texts):
                    add("LR-2", "P1", i, "存在空选项文本")
                dup = [t for t, c in Counter(texts).items() if c > 1 and t]
                if dup:
                    add("LR-2", "P1", i, f"选项文本重复: {dup[:2]}")

        # LR-3 填空题必须留作答空位；解答题靠空白处作答，不判。
        # 判据收录「任意下划线（含单/双下划线）」与「任意括号」——语文成语题
        # 写的是「画蛇添__」（双下划线），英语翻译题写的是「（写英文）」，
        # 都在正常交代作答位，早先只认 `____` 与空括号属于误判。
        if qt == "fill":
            if not re.search(r"_|＿|[（(]", stem):
                add("LR-3", "P2", i, "填空题干未留作答空位（无下划线/括号）")

        # LR-4 习作/作文要有要求。主判据只认「是否写了字数/篇幅要求」；
        # 曾把「题干短于 25 字」也计入 P1，结果英语「用 6 句话写…（不少于 35 词）」
        # 明明已给出篇幅要求却被判缺陷——那是规则过严，不是内容问题。
        # 长度只作兜底：短于 12 字基本等于没写要求。
        if qt == "composition":
            if len(stem) < 12:
                add("LR-4", "P1", i, f"习作题干过短（{len(stem)} 字），缺题目要求")
            elif not re.search(r"[0-9]+\s*字|[0-9]+\s*词|不少于|左右|字左右|词左右", stem):
                add("LR-4", "P1", i, "习作题未写字数要求，学生不知篇幅")

        # LR-5 答案泄露。阅读理解题的答案本来就在原文里，跳过；只有纯选择题
        # 且「答案文本本身」出现在题干里才算泄露。
        # 例外：纯数字 / 数字＋单位型答案（如「4元」「2个」）在数学题干里必然
        # 与题给条件构成子串重叠（「2.4元」里就含「4元」），那是题面条件不是泄露。
        ans = _answer_text(q).strip()
        body = q.get("content") or {}
        numeric_ans = bool(re.fullmatch(r"[0-9０-９\.\/百分]+[\u4e00-\u9fff]{0,3}", ans))
        if qt in ("choice", "fill") and ans and not body.get("passage") and not numeric_ans:
            zh = bool(re.search(r"[\u4e00-\u9fff]", ans))
            hit = False
            if zh and len(ans) >= 2:
                hit = ans in stem
            elif not zh and len(ans) >= 4:
                hit = re.search(rf"\b{re.escape(ans)}\b", stem) is not None
            if hit:
                add("LR-5", "P1", i, f"答案「{ans}」原文出现在题干中")

        # LR-8 题干超长：阅读题带短文属正常，只判非阅读题
        if len(stem) > STEM_LIMIT and not (q.get("content") or {}).get("passage"):
            add("LR-8", "P3", i, f"题干 {len(stem)} 字 > {STEM_LIMIT}，需滚动才能读全")

    # LR-6 同卷重复
    for s, c in stems.items():
        if c > 1:
            add("LR-6", "P1", None, f"同卷题干重复 {c} 次: {s[:30]}")

    # LR-7 分值
    if abs(total - float(exam.total_score or 0)) > 1e-6:
        add("LR-7", "P1", None, f"小题分值合计 {total:g} != 卷面 {exam.total_score}")

    # LR-9 大题
    if len(sections) < 2:
        add("LR-9", "P2", None, f"大题数 {len(sections)}，分组缺失")

    row = {
        "exam_id": exam.id,
        "title": exam.title,
        "grade": exam.grade,
        "subject": exam.subject,
        "exam_type": exam.exam_type,
        "questions": len(qs),
        "total_score": exam.total_score,
        "sum_score": round(total, 2),
        "sections": len(sections),
        "section_names": " / ".join(sections[:8]),
        "types": json.dumps(dict(types), ensure_ascii=False),
        "issues": len(issues),
        "p0": sum(1 for x in issues if x["level"] == "P0"),
    }
    return row, issues


def main() -> int:
    db = SessionLocal()
    try:
        exams = db.scalars(
            select(Exam).where(Exam.title.like("%走查卷%")).order_by(Exam.id)
        ).all()
    finally:
        db.close()

    rows: list[dict] = []
    detail: list[dict] = []
    all_ids = sorted(
        {r.get("question_id") for e in exams for r in (e.questions or []) if r.get("question_id")}
    )
    db = SessionLocal()
    try:
        bank = load_questions(db, all_ids)
    finally:
        db.close()
    print(f"题库回表 {len(bank)} / 引用 {len(all_ids)} 道")

    for e in exams:
        r, iss = audit_paper(e, bank)
        rows.append(r)
        detail.extend(iss)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with (OUT_DIR / "paper_ui_audit.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    with (OUT_DIR / "issue_detail.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(
            f, fieldnames=["exam_id", "title", "q_no", "code", "level", "detail"]
        )
        w.writeheader()
        w.writerows(detail)

    print(f"走查卷 {len(rows)} 张，问题 {len(detail)} 条")
    lv = Counter(x["level"] for x in detail)
    print("  等级分布:", dict(lv))
    cd = Counter(x["code"] for x in detail)
    print("  规则分布:", dict(sorted(cd.items())))
    print("  问题卷数:", len({x['exam_id'] for x in detail}))
    print("\n逐卷（P0>0 优先）:")
    for r in sorted(rows, key=lambda x: (-x["p0"], -x["issues"], x["exam_id"])):
        print(
            f"  {r['exam_id']:>3} g{r['grade']} {r['subject']:8s} {r['exam_type']:8s} "
            f"题{r['questions']:>3} 分{r['sum_score']:>5}/{r['total_score']:<4} "
            f"大题{r['sections']} P0={r['p0']} 计{r['issues']}"
        )
    print(f"\n导出: {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
