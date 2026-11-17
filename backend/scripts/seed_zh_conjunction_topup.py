"""按单元补指定知识点的填空（关联词语搭配类）。

场景与 `seed_zh_synonym_topup.py` 相同：某些「积累与运用」考点在全库题量不小，
但按章均匀挂载（每章 1 道），摊到单元（1-3 章）只剩 1 道可用题。单元卷要覆盖
8 个核心考点、卷面只有 15 题，这一道题一旦没进卷，该单元核心覆盖就卡在 0.875。

本脚本只补「实际出卷时该考点没进卷」的单元，不碰已达标的单元；只新增不改旧题；
难度定为 1（落在 fill 节的 easy 带内，否则会被 _allowed_ids 过滤）。

用法：
    python scripts/seed_zh_conjunction_topup.py --kp 4513 --grade 7
    python scripts/seed_zh_conjunction_topup.py --kp 4513 --grade 7 --apply
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.content import Chapter, KnowledgePoint, Question, Textbook
from app.models.exam import ExamBlueprint
from app.models.user import User
from app.services.core_kp_list import (
    build_core_list_for_chapters,
    core_kps_for_chapters,
)
from app.services.exam_paper import generate_paper, resolve_scope_chapters

# (题干, 答案)。题干里用 __ 表示要填的空，与库内既有 39 道同格式。
CONJUNCTIONS = [
    ("填上合适的关联词：__他年纪很小，__做事很老练。", "虽然……但是"),
    ("填上合适的关联词：__你努力学习，__能取得好成绩。", "只有……才"),
    ("填上合适的关联词：__雨下得很大，比赛__没有中断。", "尽管……却"),
    ("填上合适的关联词：__明天下雨，我们__改期再出发。", "如果……就"),
    ("填上合适的关联词：他__成绩好，__很爱帮助同学。", "不但……而且"),
    ("填上合适的关联词：__走多远，他__记得回家的路。", "无论……都"),
]
PER_UNIT = 2
TAG = "coverage_patch"
SOURCE_NAME = "自建·关联词补量"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kp", type=int, required=True)
    parser.add_argument("--grade", type=int, required=True)
    parser.add_argument("--subject", default="chinese")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    with SessionLocal() as db:
        kp = db.get(KnowledgePoint, args.kp)
        if kp is None:
            print(f"KP {args.kp} 不存在")
            return 1
        blueprint = db.scalar(
            select(ExamBlueprint).where(
                ExamBlueprint.code == f"g{args.grade}_{args.subject}_unit"
            )
        )
        admin = db.scalar(select(User).order_by(User.id).limit(1))
        if blueprint is None or admin is None:
            print("缺少单元卷蓝图或用户")
            return 1

        existing = {
            str((q.content or {}).get("stem", ""))
            for q in db.scalars(
                select(Question).where(
                    Question.knowledge_point_id == args.kp,
                    Question.status == "published",
                )
            ).all()
        }
        word_iter = iter([c for c in CONJUNCTIONS if c[0] not in existing])
        created = 0
        print(f"kp{args.kp} {kp.name}｜g{args.grade} {args.subject}")

        for semester in ("first", "second"):
            book = db.scalar(
                select(Textbook).where(
                    Textbook.subject == args.subject,
                    Textbook.grade == args.grade,
                    Textbook.semester == semester,
                )
            )
            if book is None:
                continue
            ui = 1
            while ui <= 12:
                try:
                    chs = resolve_scope_chapters(
                        db, textbook_id=book.id, scope="unit", unit_index=ui
                    )
                except (IndexError, ValueError):
                    break
                if not chs:
                    break
                core = build_core_list_for_chapters(db, chs, book)
                if args.kp not in {r["kp_id"] for r in core}:
                    ui += 1
                    continue
                paper = generate_paper(
                    db, user=admin, blueprint=blueprint, chapter_ids=chs,
                    seed=30000,
                    core_kps=core_kps_for_chapters(
                        db, textbook_id=book.id, chapter_ids=chs
                    ),
                )
                covered = {
                    int(i.question.knowledge_point_id) for i in paper.items
                    if i.question.knowledge_point_id
                }
                if args.kp in covered:
                    ui += 1
                    continue
                in_unit = db.scalars(
                    select(Question).where(
                        Question.knowledge_point_id == args.kp,
                        Question.chapter_id.in_(chs),
                        Question.status == "published",
                    )
                ).all()
                if len(in_unit) > PER_UNIT:
                    ui += 1
                    continue
                hosts = sorted({q.chapter_id for q in in_unit}) or [
                    c for c in chs
                    if (db.get(Chapter, c).is_placeholder == 0)
                ]
                host = hosts[0]
                for _ in range(PER_UNIT):
                    try:
                        stem, ans = next(word_iter)
                    except StopIteration:
                        print("候选题用尽，提前结束")
                        ui = 99
                        break
                    if stem in existing:
                        continue
                    print(f"  {semester} U{ui:2d} ch{host}  {stem}  -> {ans}")
                    created += 1
                    if not args.apply:
                        continue
                    db.add(Question(
                        chapter_id=host,
                        knowledge_point_id=args.kp,
                        subject=args.subject,
                        q_type="fill",
                        content={"stem": stem},
                        options=None,
                        answer={"value": ans},
                        analysis=f"该句是关联词搭配，填入「{ans}」后前后分句关系才成立。",
                        difficulty=1,
                        tags=[TAG],
                        status="published",
                        source_type="selfbank",
                        source_name=SOURCE_NAME,
                    ))
                    existing.add(stem)
                ui += 1

        if args.apply:
            db.commit()
            print(f"\n已写入 {created} 道（kp{args.kp}）")
        else:
            print(f"\n预览：将写入 {created} 道（kp{args.kp}）。加 --apply 落库。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
