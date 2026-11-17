"""为「概念/方法类」缺口知识点手写选择题（无法由 fill 自动改写的场景）。

适用范围：赏析句子的方法、病句与标点。这类知识点的 fill 答案是文字性步骤描述，
自动派生干扰项只能拿到不相干的词语，会造出一眼假的选项，因此采用人工撰写的标准题。

已知数据问题：4325 与 4349 同名（赏析句子的方法），4326 与 4350 同名（病句与标点），
是跨年级重复建的知识点；本脚本按各自年级分别补题，不合并知识点。

用法（backend 目录下）：
    .venv\\Scripts\\python.exe scripts\\seed_manual_choice_for_gap_kps.py --apply
"""

from __future__ import annotations

import argparse
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.models.content import KnowledgePoint, Question, Textbook, Chapter  # noqa: E402

TAG = "coverage_patch"

# (知识点 id, 年级, 学期, 题干, 正确项文本, 三个干扰项)
MANUAL = [
    (
        4325, 4, "first",
        "赏析句子时，下面做法最恰当的一项是（  ）。",
        "先指出句子用了什么修辞或写法，再结合句意说明效果，最后联系主旨与情感",
        ["只指出句子用了什么修辞，不做其他分析", "把句子改写成白话文再抄一遍", "只写「这句话很生动」这类笼统评价"],
    ),
    (
        4326, 4, "first",
        "「通过这次活动，使我懂得了合作的重要。」这句话的毛病是（  ）。",
        "缺少主语（「通过……使……」把主语淹没了）",
        ["用词不当，动词搭配不合适", "语序不当，状语位置放错", "重复啰嗦，意思前后重复"],
    ),
    (
        4349, 6, "first",
        "赏析句子时，下面做法最恰当的一项是（  ）。",
        "先指出句子用了什么修辞或写法，再结合句意说明效果，最后联系主旨与情感",
        ["只指出句子用了什么修辞，不做其他分析", "把句子改写成白话文再抄一遍", "只写「这句话很生动」这类笼统评价"],
    ),
    (
        4350, 6, "first",
        "「通过这次活动，使我懂得了合作的重要。」这句话的毛病是（  ）。",
        "缺少主语（「通过……使……」把主语淹没了）",
        ["用词不当，动词搭配不合适", "语序不当，状语位置放错", "重复啰嗦，意思前后重复"],
    ),
]
KEYS = ("A", "B", "C", "D")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    created = 0
    updated = 0
    with SessionLocal() as db:
        for kp_id, grade, semester, stem, correct, distractors in MANUAL:
            kp = db.query(KnowledgePoint).filter_by(id=kp_id).first()
            if kp is None:
                print(f"  - kp={kp_id} 不存在，跳过")
                continue
            textbook = db.query(Textbook).filter_by(subject="chinese", grade=grade, semester=semester).first()
            chapters = db.scalars(
                select(Chapter).where(Chapter.textbook_id == textbook.id).order_by(Chapter.order_index)
            ).all()
            # 沿用该知识点原题所在章节，保证落在期中的前半册范围内
            sibling = db.scalars(
                select(Question).where(Question.knowledge_point_id == kp_id).order_by(Question.id)
            ).first()
            chapter_id = sibling.chapter_id if sibling else chapters[0].id

            existing = db.scalars(
                select(Question).where(
                    Question.knowledge_point_id == kp_id,
                    Question.q_type == "choice",
                    Question.content["stem"].as_string() == stem,
                )
            ).first()

            # 选项顺序确定性打乱：手写题若固定把正确答案放在 A，会重演「全选 A 也能得分」的口径问题
            texts = [correct] + list(distractors)
            order = list(range(4))
            random.Random(f"manual-{kp_id}").shuffle(order)
            options = [{"key": KEYS[i], "text": texts[idx]} for i, idx in enumerate(order)]
            answer_key = KEYS[order.index(0)]

            if existing is not None:
                existing.options = options
                existing.answer = {"value": answer_key}
                existing.difficulty = 1
                updated += 1
                print(f"  ~ kp={kp_id} 已存在，重排选项后答案={answer_key}")
                continue

            row = Question(
                chapter_id=chapter_id,
                knowledge_point_id=kp_id,
                subject="chinese",
                q_type="choice",
                content={"stem": stem},
                options=options,
                answer={"value": answer_key},
                analysis=f"人工撰写的标准题，用于补齐「{kp.name}」在 easy 难度带内的选择题覆盖。",
                # choice 段难度带是 easy（排名分位低 60%），题必须落在带内才参与选卷
                difficulty=1,
                tags=[TAG, "choice", "chinese", f"g{grade}", "manual"],
                status="published",
                source_type="original",
            )
            db.add(row)
            created += 1
            print(f"  + kp={kp_id} {kp.name[:20]:22s} ch={chapter_id} 题干={stem[:30]} 正确={answer_key}")

        print(f"[manual] 新建 {created} 道，更新 {updated} 道")
        if not args.apply:
            db.rollback()
            print("[manual] 干跑结束，未写库（加 --apply 生效）")
            return 0
        db.commit()
        print("[manual] 已提交")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
