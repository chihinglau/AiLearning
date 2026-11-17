"""为 kp4506「积累与运用·近义词辨析」按单元补量。

背景：kp4506 全库 66 道 fill，均匀挂在 66 个章节上（每章恰好 1 道）。但 g1 语文
按单元组卷时，一个单元只含 3 章，其中往往只有 1 章挂了这个考点，单元内可用题
只有 1 道。单元卷 15 题要覆盖 8 个核心考点，这一道题只要没能进卷，该单元核心
覆盖就卡在 0.875（实测 g1 语文上册 U4-U12、下册 U5 共 10 张）。

补法与 `add_choice_for_gap_kps.py` 一致：只新增、不改旧题；难度必须落在目标
题型难度带内（fill 节是 easy 带），否则会被 _allowed_ids 过滤、覆盖零贡献。

用法：
    python scripts/seed_zh_synonym_topup.py                 # 预览
    python scripts/seed_zh_synonym_topup.py --apply        # 落库
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

KP_ID = 4506
# 每个缺口单元要补 2 道；词表按「小学常用、近义关系明确」挑选，且不与库内 66 道重复
WORDS = [
    ("害怕", "恐惧"),
    ("喜欢", "喜爱"),
    ("洁白", "雪白"),
    ("宽阔", "宽广"),
    ("摇晃", "摇摆"),
    ("满足", "满意"),
    ("富裕", "富足"),
    ("荣誉", "声誉"),
    ("热闹", "喧闹"),
    ("简单", "简易"),
    ("急忙", "匆忙"),
    ("收拾", "整理"),
    ("说明", "阐明"),
    ("特别", "格外"),
    ("温暖", "暖和"),
    ("用心", "专心"),
    ("舒服", "舒适"),
    ("明亮", "光亮"),
    ("柔软", "松软"),
    ("灵活", "灵敏"),
    ("整齐", "齐整"),
    ("勇敢", "胆大"),
    ("安静", "宁静"),
    ("惊奇", "惊讶"),
    ("轻快", "轻盈"),
    ("理解", "懂得"),
]
PER_UNIT = 2
TAG = "coverage_patch"
SOURCE_NAME = "自建·近义词补量"


def _existing_stems(db) -> set[str]:
    rows = db.scalars(
        select(Question).where(Question.knowledge_point_id == KP_ID, Question.status == "published")
    ).all()
    return {str((q.content or {}).get("stem", "")) for q in rows}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--grade", type=int, default=1)
    parser.add_argument("--subject", default="chinese")
    args = parser.parse_args()

    with SessionLocal() as db:
        book = db.scalar(
            select(Textbook).where(
                Textbook.subject == args.subject,
                Textbook.grade == args.grade,
                Textbook.semester == "first",
            )
        )
        if book is None:
            print("找不到教材")
            return 1
        kp = db.get(KnowledgePoint, KP_ID)
        if kp is None:
            print(f"KP {KP_ID} 不存在")
            return 1

        existing = _existing_stems(db)
        blueprint = db.scalar(
            select(ExamBlueprint).where(ExamBlueprint.code == f"g{args.grade}_{args.subject}_unit")
        )
        admin = db.scalar(select(User).order_by(User.id).limit(1))
        if blueprint is None or admin is None:
            print("缺少单元卷蓝图或用户，无法判定缺口")
            return 1
        word_iter = iter([w for w in WORDS if f"写出「{w[0]}」的近义词：________。" not in existing])
        created = 0
        print(f"kp{KP_ID} {kp.name}｜目标教材 g{args.grade} {args.subject} {book.semester}")
        for semester in ("first", "second"):
            b = book if semester == "first" else db.scalar(
                select(Textbook).where(
                    Textbook.subject == args.subject,
                    Textbook.grade == args.grade,
                    Textbook.semester == semester,
                )
            )
            if b is None:
                continue
            ui = 1
            while ui <= 12:
                try:
                    chs = resolve_scope_chapters(db, textbook_id=b.id, scope="unit", unit_index=ui)
                except (IndexError, ValueError):
                    break
                if not chs:
                    break
                core = build_core_list_for_chapters(db, chs, b)
                if KP_ID not in {r["kp_id"] for r in core}:
                    ui += 1
                    continue
                # 只补「实际出卷时这个考点没进卷」的单元：出卷已覆盖的单元不动，
                # 否则会白白消耗词表（首版没做这个判定，把已达标的 U2/U3 也补了）。
                paper = generate_paper(
                    db, user=admin, blueprint=blueprint, chapter_ids=chs,
                    seed=30000, core_kps=core_kps_for_chapters(
                        db, textbook_id=b.id, chapter_ids=chs
                    ),
                )
                covered = {
                    int(i.question.knowledge_point_id) for i in paper.items
                    if i.question.knowledge_point_id
                }
                if KP_ID in covered:
                    ui += 1
                    continue
                in_unit = db.scalars(
                    select(Question).where(
                        Question.knowledge_point_id == KP_ID,
                        Question.chapter_id.in_(chs),
                        Question.status == "published",
                    )
                ).all()
                # 只补「单元内可用题不足 PER_UNIT+1」的单元：题量够就不动
                if len(in_unit) > PER_UNIT:
                    ui += 1
                    continue
                # 挂到「本单元内已有该考点题的那个章」；若没有，挂第一真实章
                host_ids = sorted({q.chapter_id for q in in_unit}) or [
                    c
                    for c in chs
                    if (db.get(Chapter, c).is_placeholder == 0)
                ]
                host = host_ids[0]
                for _ in range(PER_UNIT):
                    try:
                        word, syn = next(word_iter)
                    except StopIteration:
                        print("词表用尽，提前结束")
                        ui = 99
                        break
                    stem = f"写出「{word}」的近义词：________。"
                    if stem in existing:
                        continue
                    print(f"  {semester} U{ui:2d} ch{host}  {stem}  -> {syn}")
                    created += 1
                    if not args.apply:
                        continue
                    q = Question(
                        chapter_id=host,
                        knowledge_point_id=KP_ID,
                        subject="chinese",
                        q_type="fill",
                        content={"stem": stem},
                        options=None,
                        answer={"value": syn},
                        analysis=f"「{word}」与「{syn}」意思相近，可互换使用。",
                        difficulty=1,
                        tags=[TAG],
                        status="published",
                        source_type="selfbank",
                        source_name=SOURCE_NAME,
                    )
                    db.add(q)
                    existing.add(stem)
                ui += 1
        if args.apply:
            db.commit()
            print(f"\n已写入 {created} 道（kp{KP_ID}）")
        else:
            print(f"\n预览：将写入 {created} 道（kp{KP_ID}）。加 --apply 落库。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
