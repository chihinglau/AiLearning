# -*- coding: utf-8 -*-
"""真题导入包校验器（配套 D-10 / PA-01）。

用法：
    python _validate_past_papers.py <papers.json> [--strict]

只读校验，不连库、不写库。退出码：0 通过（允许 warning）；2 存在 error（--strict 下 warning 也失败）。
"""
from __future__ import annotations

import json
import sys
from collections import Counter

SUBJECTS = {
    "chinese", "math", "english", "science",
    "politics", "history", "geography", "biology", "physics", "chemistry",
}
YEARS = {"2021-2022", "2022-2023", "2023-2024", "2024-2025", "2025-2026"}
TERMS = {"first", "second"}
EXAM_TYPES = {"midterm", "final"}
REGIONS = {
    "福田区", "罗湖区", "南山区", "盐田区", "宝安区", "龙岗区",
    "龙华区", "坪山区", "光明区", "大鹏新区",
}
TIERS = {"L1", "L2", "L3", "L4"}
OBJ_TYPES = {"single_choice", "multi_choice", "fill_blank", "judge", "matching"}
AI_MARKERS = ("AI生成", "人工智能生成", "自动生成题目", "拼装卷", "仿真真题")

REQUIRED = [
    "paper_uid", "grade", "subject", "school_year", "term", "exam_type",
    "region", "school", "source_tier", "source_name", "source_url",
    "license_note", "file_ref", "total_score", "question_count", "ocr_status",
]


def validate(path: str, strict: bool) -> int:
    data = json.load(open(path, encoding="utf-8"))
    papers = data.get("papers") or []
    errors: list[str] = []
    warns: list[str] = []
    is_template = bool(data.get("_template"))

    if is_template:
        warns.append("模板态（_template=true）：仅校验结构，不视为可导入真题包")
    if not papers and not is_template:
        errors.append("papers 为空")

    uids: Counter[str] = Counter()
    stems: Counter[str] = Counter()

    for idx, p in enumerate(papers, 1):
        where = f"papers[{idx}] {p.get('paper_uid', '?')}"
        for k in REQUIRED:
            if p.get(k) in (None, "", []):
                (warns if is_template else errors).append(f"{where}: 缺字段 {k}")

        if p.get("source_tier") == "L4":
            errors.append(f"{where}: source_tier=L4（未授权转载）禁止入库")
        if p.get("source_tier") in {"L3", "L4"} and not p.get("license_note"):
            errors.append(f"{where}: L3/L4 必须填写 license_note")

        grade = p.get("grade")
        if not isinstance(grade, int) or not 1 <= grade <= 9:
            errors.append(f"{where}: grade 必须为 1–9 整数")
        elif grade <= 2 and p.get("is_past_paper"):
            errors.append(f"{where}: 1–2 年级政策上无纸笔考试，不得入真题库")

        if p.get("subject") not in SUBJECTS:
            errors.append(f"{where}: subject 非法 {p.get('subject')!r}")
        if p.get("school_year") not in YEARS:
            errors.append(f"{where}: school_year 须在近 5 学年 {sorted(YEARS)}")
        if p.get("term") not in TERMS:
            errors.append(f"{where}: term 须为 first/second")
        if p.get("exam_type") not in EXAM_TYPES:
            errors.append(f"{where}: exam_type 须为 midterm/final")
        if p.get("region") not in REGIONS:
            errors.append(f"{where}: region 非法 {p.get('region')!r}")
        if p.get("source_tier") not in TIERS:
            errors.append(f"{where}: source_tier 须为 L1–L4")
        if p.get("ocr_status") not in {"pending", "done", "verified"}:
            errors.append(f"{where}: ocr_status 非法")

        blob = json.dumps(p, ensure_ascii=False)
        for marker in AI_MARKERS:
            if marker in blob:
                errors.append(f"{where}: 含生成/拼装标记「{marker}」，禁止入库")

        uid = p.get("paper_uid") or ""
        if uid:
            uids[uid] += 1
            expect = f"SZ-{p.get('school_year', '')}-G{grade}-"
            if not uid.startswith(expect):
                warns.append(f"{where}: paper_uid 建议以 {expect} 开头")

        qs = p.get("questions") or []
        if not qs:
            (warns if is_template else errors).append(f"{where}: questions 为空")
            continue

        if p.get("question_count") not in (None, "", 0) and p["question_count"] != len(qs):
            errors.append(f"{where}: question_count={p['question_count']} 与题数 {len(qs)} 不一致")

        nums = [str(q.get("no", "")) for q in qs]
        dup = [n for n, c in Counter(nums).items() if c > 1]
        if dup:
            errors.append(f"{where}: 题号重复 {dup}")
        missing_no = [i for i, n in enumerate(nums, 1) if not n]
        if missing_no:
            errors.append(f"{where}: 第 {missing_no} 题缺 no")

        score_sum = 0
        for q in qs:
            score = q.get("score")
            if not isinstance(score, (int, float)) or score <= 0:
                errors.append(f"{where} 题{q.get('no')}: score 必须为正数")
            else:
                score_sum += score
            qtype = q.get("type")
            if qtype not in OBJ_TYPES and qtype != "subjective":
                errors.append(f"{where} 题{q.get('no')}: type 非法 {qtype!r}")
            if qtype in {"single_choice", "multi_choice"}:
                if len(q.get("options") or []) < 2:
                    errors.append(f"{where} 题{q.get('no')}: 选择题需 ≥2 个选项")
                if qtype == "single_choice" and len(q.get("options") or []) != 4:
                    warns.append(f"{where} 题{q.get('no')}: 单选题选项数非 4（核对原件）")
            if not (q.get("answer") or "").strip() and p.get("ocr_status") == "verified":
                errors.append(f"{where} 题{q.get('no')}: 已核验卷缺答案")
            stem = (q.get("stem") or "").strip()
            if stem.startswith("<") or "禁止改写" in stem:
                (warns if is_template else errors).append(f"{where} 题{q.get('no')}: 题干仍为占位文本")
            elif len(stem) < 4:
                errors.append(f"{where} 题{q.get('no')}: 题干过短")
            else:
                stems[stem] += 1

        total = p.get("total_score")
        if isinstance(total, (int, float)) and abs(score_sum - total) > 0.01:
            (warns if is_template else errors).append(
                f"{where}: 题分合计 {score_sum} ≠ 卷面总分 {total}"
            )

    for uid, c in uids.items():
        if c > 1:
            errors.append(f"paper_uid 重复 {uid} ×{c}")
    for s, c in stems.items():
        if c > 1:
            warns.append(f"题干在多卷重复 ×{c}（疑似重复卷/改编卷）：{s[:24]}…")

    tag = "模板" if is_template else "导入包"
    print(f"[{tag}] 卷数={len(papers)} errors={len(errors)} warnings={len(warns)}")
    for e in errors:
        print("  ERROR:", e)
    for w in warns[:40]:
        print("  WARN :", w)
    if len(warns) > 40:
        print(f"  ... 其余 {len(warns) - 40} 条 warning 省略")

    if errors or (strict and warns):
        return 2
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(validate(sys.argv[1], "--strict" in sys.argv))
