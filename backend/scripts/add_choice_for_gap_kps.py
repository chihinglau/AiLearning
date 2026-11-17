"""按「缺覆盖的知识点」补选择题（补题型），消除'''知识点只在 fill 有题、fill 位置不够'''的死角。

背景（2026-11-17）：
- 8 张 <0.8 的卷全部 cap=1.0，即题量已够，差的是「该知识点在本章节范围内只有 fill 题」。
- 例：g7 数学期中的 fill 池在范围内有 19 个知识点，而卷面 fill 只有 6 个位置 → 5 个知识点
  永远进不了卷；但 choice 有 10 个位置、范围内这些知识点又没有 choice 题。

做法：
1. 复刻审计口径解析章节范围、生成一次卷，找出未被覆盖的知识点（miss_kps）。
2. 对每个 miss 知识点，取其范围内一道 fill 题，改写为选择题：
   - 题干沿用（保持原有语言，不做重写）
   - 正确项 = 原答案
   - 干扰项按学科规则从「同知识点其他答案」「同章节相邻数值」里取，不足时按典型算错方式派生
3. 选项按 (seed, kp) 确定性打乱并写 key，answer 存 key（与 normalize_choice_answers 口径一致）。
4. 只做 dry-run 除非 --apply。

用法（backend 目录下）：
    .venv\\Scripts\\python.exe scripts\\add_choice_for_gap_kps.py --grade 7 --subject math --semester second --exam-type midterm
    ... 加 --apply 写库
"""

from __future__ import annotations

import argparse
import os
import random
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import func, select  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.models.content import Chapter, KnowledgePoint, Question, Textbook  # noqa: E402
from app.models.exam import ExamBlueprint  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.exam_paper import generate_paper  # noqa: E402

KEYS = ("A", "B", "C", "D")
SEED = 20261117
TAG = "coverage_patch"
SEMESTER_CN = {"first": "上册", "second": "下册"}
# 补题必须落在该 q_type 的难度带里，否则会被 _allowed_ids 过滤掉、根本不参与选卷
BAND_DIFFICULTY = {"easy": 1, "medium": 3, "hard": 5}


def _target_difficulty(blueprint, q_type: str = "choice") -> int:
    for section in blueprint.sections:
        if section.get("q_type") == q_type:
            return BAND_DIFFICULTY.get(section.get("band") or "easy", 3)
    return 3


def _scope_chapters(db, textbook: Textbook, exam_type: str):
    chapters = db.scalars(
        select(Chapter)
        .where(Chapter.textbook_id == textbook.id, Chapter.is_placeholder == 0)
        .order_by(Chapter.order_index)
    ).all()
    if exam_type == "midterm":
        return chapters[: max(1, len(chapters) // 2)]
    return chapters


def _num(value: str) -> float | None:
    m = re.fullmatch(r"-?\d+(?:\.\d+)?", value.strip())
    return float(m.group()) if m else None


def _fmt(num: float) -> str:
    return str(int(num)) if abs(num - int(num)) < 1e-9 else f"{num:g}"


def _frac_and_distractors(value: str) -> list[str]:
    """概率/分数类：只生成 0<v<1 的真分数，避免出现 2/2 这种大于 1 的荒谬选项。"""
    m = re.fullmatch(r"(\d+)/(\d+)", value.strip())
    if not m:
        return []
    a, b = int(m.group(1)), int(m.group(2))
    cands = [f"{a}/{b + 1}", f"{a}/{b * 2}", f"{b - a}/{b}", f"{a + 1}/{b}",
             f"{a}/{b + 2}", f"{a}/{b + 3}", f"{a}/{b + 4}"]
    out: list[str] = []
    for c in cands:
        mm = re.fullmatch(r"(\d+)/(\d+)", c)
        if not mm:
            continue
        ca, cb = int(mm.group(1)), int(mm.group(2))
        if ca <= 0 or cb <= 0 or ca >= cb:
            continue
        if c != value.strip() and c not in out:
            out.append(c)
    return out


def _multi_blank_distractors(correct: str) -> list[str]:
    """多空答案（形如「4、4」）：逐位替换成常见误答，拼回成对选项。"""
    parts = [p.strip() for p in correct.split("、")]
    if len(parts) < 2 or not all(re.fullmatch(r"\d+", p) for p in parts):
        return []
    out: list[str] = []
    for index in range(len(parts)):
        for delta in (1, -1, 2):
            n = int(parts[index]) + delta
            if n <= 0:
                continue
            variant = list(parts)
            variant[index] = str(n)
            joined = "、".join(variant)
            if joined != correct and joined not in out:
                out.append(joined)
    return out


def _rect_distractors(stem: str, correct: str) -> list[str]:
    """长方形周长/面积题：按「典型算错方式」派生，比 ±1 更符合真实错因。"""
    m = re.search(r"长\s*(\d+(?:\.\d+)?)\s*(?:厘米|米|分米).*?宽\s*(\d+(?:\.\d+)?)", stem)
    if not m:
        return []
    a, b = float(m.group(1)), float(m.group(2))
    if "周长" in stem:
        cands = [a + b, a * b, 2 * a * b, a + b + 2]
    elif "面积" in stem:
        cands = [2 * (a + b), a + b, a * b * 2, 2 * a + 2 * b]
    else:
        return []
    out: list[str] = []
    for c in cands:
        text = _fmt(c)
        if text != correct.strip() and text not in out:
            out.append(text)
    return out


def _linear_distractors(stem: str, correct: str) -> list[str]:
    """一次函数求值：用「漏系数 / 漏常数 / 系数常数颠倒」这些真实错因做干扰项。"""
    m = re.search(r"y\s*=\s*(\d+)x\s*\+\s*(\d+).*?x\s*=\s*(\d+)", stem)
    if not m:
        return []
    a, b, x = int(m.group(1)), int(m.group(2)), int(m.group(3))
    cands = [a * x, x + b, x * b, a * x + b + 1, a * x + b - 1]
    out: list[str] = []
    for c in cands:
        text = _fmt(float(c))
        if text != correct.strip() and text not in out:
            out.append(text)
    return out


def _math_distractors(correct: str, siblings: list[str], stem: str = "") -> list[str]:
    """数值题：优先用「典型算错方式」派生，再补同知识点其他答案，去重后取 3 个。"""
    out: list[str] = []
    out.extend(_multi_blank_distractors(correct))
    out.extend(_frac_and_distractors(correct))
    out.extend(_rect_distractors(stem, correct))
    out.extend(_linear_distractors(stem, correct))
    n = _num(correct)
    if n is not None:
        # 只保留加减与减半：翻倍/三倍在周长、面积、概率类题目里不是合理的错误选项形态
        for cand in (n + 1, n - 1, n / 2):
            if cand >= 0:
                out.append(_fmt(cand))
    for s in siblings:
        out.append(s.strip())
    uniq: list[str] = []
    for item in out:
        if not item or item == correct.strip() or item in uniq:
            continue
        # 选项字母不可作为数值选项（防止 fill/choice 混池时把 key 当文本）
        if item in ("A", "B", "C", "D", "T", "F"):
            continue
        uniq.append(item)
    return uniq[:3]


def _chinese_distractors(correct: str, siblings: list[str]) -> list[str]:
    """词语题：同考试点家族的其他答案本身就是同类词语，是天然的合理干扰项。

    siblings 由调用方按「同知识点 → 同考点家族」两级顺序拼好，这里只做去重取前 3。
    """
    uniq: list[str] = []
    for s in siblings:
        s = s.strip()
        if not s or s == correct.strip() or s in uniq:
            continue
        # 选项不宜过长：超过 12 字的多半是句子而非词语，放进来会让正确项过于显眼
        if len(s) > 12:
            continue
        # 排除选项字母：fill 池若混入 choice 的 key，会出现「A/B」这种非法选项
        if s in ("A", "B", "C", "D", "T", "F"):
            continue
        uniq.append(s)
    return uniq[:3]


def _build_options(subject: str, correct: str, siblings: list[str], seed_key: str,
                   stem: str = "") -> list[dict] | None:
    if subject == "math":
        distractors = _math_distractors(correct, siblings, stem)
    else:
        distractors = _chinese_distractors(correct, siblings)
    if len(distractors) < 3:
        return None
    texts = [correct.strip()] + distractors[:3]
    order = list(range(4))
    random.Random(f"{SEED}-{seed_key}").shuffle(order)
    options = [{"key": KEYS[i], "text": texts[idx]} for i, idx in enumerate(order)]
    answer_key = KEYS[order.index(0)]
    return [{"key": o["key"], "text": o["text"], "correct": o["key"] == answer_key} for o in options]


def _choice_stem(stem: str) -> str:
    """把填空式题干改写成选择题式，避免出现「写出……：________。」这种仍是填空语气的题干。"""
    s = stem.strip()
    s = s.replace("________", "（  ）").replace("____", "（  ）")
    s = re.sub(r"^写出", "", s)
    s = re.sub(r"：\s*（\s*）", "是（  ）", s)
    s = re.sub(r"（\s*）\s*。\s*$", "（  ）。", s)
    s = re.sub(r"（\s*）\s*的\s*值\s*是", "的值是（  ）", s)
    return s.strip() or stem.strip()


def _answer_value(raw) -> str:
    if isinstance(raw, list):
        return "、".join(str(x) for x in raw)
    return str(raw)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--grade", type=int, required=True)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--semester", required=True, choices=["first", "second"])
    parser.add_argument("--exam-type", required=True, choices=["unit", "midterm", "final"])
    parser.add_argument("--unit-index", type=int, default=1, help="单元卷时指定第几个单元（1 起）")
    parser.add_argument(
        "--core-only", action="store_true",
        help="只补「期末必考核心考点清单」内的缺口，并按核心优先口径选卷",
    )
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    with SessionLocal() as db:
        textbook = db.query(Textbook).filter_by(
            subject=args.subject, grade=args.grade, semester=args.semester
        ).first()
        if textbook is None:
            print("[patch] 教材不存在")
            return 1
        blueprint = db.query(ExamBlueprint).filter_by(
            code=f"g{args.grade}_{args.subject}_{args.exam_type}"
        ).first()
        if blueprint is None:
            print("[patch] 蓝图不存在")
            return 1
        admin = db.query(User).filter(User.phone == "13800000000").first()

        chapters = _scope_chapters(db, textbook, args.exam_type)
        if args.exam_type == "unit":
            index = max(1, args.unit_index) - 1
            if index >= len(chapters):
                print("[patch] 单元序号超范围")
                return 1
            chapters = [chapters[index]]
        cids = [c.id for c in chapters]

        types = {s["q_type"] for s in blueprint.sections}
        pool = db.scalars(
            select(Question).where(Question.chapter_id.in_(cids), Question.subject == args.subject)
        ).all()
        universe = {q.knowledge_point_id for q in pool if q.knowledge_point_id and q.q_type in types}
        core_ids: set[int] = set()
        if args.core_only:
            from app.services.core_kp_list import build_core_list
            core_ids = {row["kp_id"] for row in build_core_list(db, textbook)}
            if not core_ids:
                print("[patch] 该册无可用的核心考点清单")
                return 1
        paper = generate_paper(
            db, user=admin, blueprint=blueprint, chapter_ids=cids, seed=1,
            core_kps=core_ids or None,
        )
        got = {q.knowledge_point_id for q in paper.questions if q.knowledge_point_id}
        if args.core_only:
            miss = sorted(core_ids - got)
        else:
            miss = sorted(k for k in universe if k not in got)

        print(f"[patch] g{args.grade} {args.subject} {SEMESTER_CN[args.semester]} {args.exam_type} "
              f"chapters={len(cids)} items={len(paper.questions)} universe={len(universe)} "
              f"covered={len(got & universe)} miss={len(miss)}")

        created = 0
        updated = 0
        skipped: list[str] = []
        for kp_id in miss:
            kp = db.query(KnowledgePoint).filter_by(id=kp_id).first()
            srcs = [q for q in pool if q.knowledge_point_id == kp_id and q.q_type == "fill"]
            if not srcs:
                skipped.append(f"kp={kp_id} 无 fill 源题")
                continue
            src = srcs[0]
            raw_stem = str((src.content or {}).get("stem") or "").strip()
            stem = _choice_stem(raw_stem)
            correct = _answer_value((src.answer or {}).get("value"))
            if not stem or not correct:
                skipped.append(f"kp={kp_id} 题干/答案为空")
                continue
            # 三级候选：同知识点 → 同系列（去掉「·变式N」）→ 同章节同题型
            # 只取 fill 题的答案：choice 题的 answer 存的是选项 key（A/B/C/D），当成选项文本会把字母塞进选项里
            siblings = [
                _answer_value((q.answer or {}).get("value"))
                for q in pool
                if q.knowledge_point_id == kp_id and q.id != src.id and q.q_type == "fill"
            ]
            if args.subject != "math":
                # 只用「同一考点家族」的答案做干扰项：近义辨析题的干扰项应当也是近义词，
                # 拿偏旁部首、笔画顺序的答案来充数（土/竖/你）会造出一眼假的题。
                parts = kp.name.split("·")
                core = parts[1] if len(parts) > 1 else kp.name
                family = db.scalars(
                    select(KnowledgePoint).where(
                        KnowledgePoint.subject == kp.subject,
                        KnowledgePoint.name.like(f"%·{core}·%"),
                        KnowledgePoint.id != kp_id,
                    )
                ).all()
                family_ids = {k2.id for k2 in family}
                if family_ids:
                    siblings += [
                        _answer_value((q.answer or {}).get("value"))
                        for q in db.scalars(
                            select(Question).where(
                                Question.knowledge_point_id.in_(family_ids),
                                Question.q_type == "fill",
                            )
                        ).all()
                    ]
            options = _build_options(
                args.subject, correct, siblings, f"{kp_id}-{args.grade}-{args.semester}", stem
            )
            if options is None:
                skipped.append(f"kp={kp_id} 干扰项不足（选项池 {len(siblings) + (1 if args.subject == 'math' else 0)}）")
                continue
            answer_key = next(o["key"] for o in options if o["correct"])
            target_diff = _target_difficulty(blueprint, "choice")
            payload = {
                "content": {"stem": stem},
                "options": [{"key": o["key"], "text": o["text"]} for o in options],
                "answer": {"value": answer_key},
                "analysis": f"由 fill 改写为 choice，用于补齐知识点覆盖（源题 id={src.id}）。",
                "difficulty": target_diff,
                "knowledge_point_id": kp_id,
                "chapter_id": src.chapter_id,
                "tags": [TAG, "choice", args.subject, f"g{args.grade}"],
                "status": "published",
                "source_type": "adapted",
                "adapted_from": f"question:{src.id}",
            }
            existing = db.scalars(
                select(Question).where(
                    Question.knowledge_point_id == kp_id,
                    Question.q_type == "choice",
                    Question.adapted_from == f"question:{src.id}",
                )
            ).first()
            if existing is not None:
                # 幂等：重跑时只同步内容与难度带，不重复建题
                for key, value in payload.items():
                    setattr(existing, key, value)
                updated += 1
                print(f"  ~ kp={kp_id} {kp.name[:26]:28s} 已存在，更新难度={target_diff} 选项="
                      f"{[o['text'] for o in options]}")
                continue
            row = Question(subject=args.subject, q_type="choice", **payload)
            db.add(row)
            created += 1
            print(f"  + kp={kp_id} {kp.name[:26]:28s} 题干={stem[:38]:40s} 正确={correct} 选项="
                  f"{[o['text'] for o in options]}")

        print(f"[patch] 新建 {created} 道，更新 {updated} 道，跳过 {len(skipped)} 处")
        for line in skipped:
            print("  -", line)

        if not args.apply:
            db.rollback()
            print("[patch] 干跑结束，未写库（加 --apply 生效）")
            return 0
        db.commit()
        print("[patch] 已提交")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
