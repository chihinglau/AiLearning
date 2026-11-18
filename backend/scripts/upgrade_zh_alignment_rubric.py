"""语文自建题库两项整改（幂等，按 source_ref 定位）：

1. 「积累与运用」填空/阅读简答：由全册锚定第一单元改为**逐单元轮转对齐**
   （按教材章节顺序 chapters[i % n]），使每册各单元的填空语料都有覆盖。
2. 习作评分点：由 3 条通用维度改为**中考口径三维分档量规**
   （内容 40% / 结构 30% / 语言 30%，各分一、二、三档并给出分值与描述）。

用法：
    python scripts/upgrade_zh_alignment_rubric.py --dry-run
    python scripts/upgrade_zh_alignment_rubric.py --apply
"""

from __future__ import annotations

import argparse

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.content import Chapter, Question, Textbook

# 三维分档量规（中考作文通用口径，按题面满分比例换算）
RUBRIC_DIMENSIONS = [
    {
        "dimension": "内容",
        "weight": 0.40,
        "focus": "立意与选材：切题、中心明确、材料具体真实",
        "bands": [
            {"level": "一类", "ratio": [0.90, 1.00], "descriptor": "完全切题，中心突出，材料具体、有细节"},
            {"level": "二类", "ratio": [0.70, 0.89], "descriptor": "基本切题，中心较明确，材料较具体"},
            {"level": "三类", "ratio": [0.50, 0.69], "descriptor": "部分切题，中心不够明确，材料笼统"},
        ],
    },
    {
        "dimension": "结构",
        "weight": 0.30,
        "focus": "条理与衔接：段落清楚、顺序合理、有过渡",
        "bands": [
            {"level": "一类", "ratio": [0.90, 1.00], "descriptor": "层次清晰，详略得当，过渡自然，首尾完整"},
            {"level": "二类", "ratio": [0.70, 0.89], "descriptor": "层次基本清楚，详略尚可，有简单过渡"},
            {"level": "三类", "ratio": [0.50, 0.69], "descriptor": "层次不清或流水账，缺少过渡"},
        ],
    },
    {
        "dimension": "语言",
        "weight": 0.30,
        "focus": "表达与规范：语句通顺、用词准确、书写标点规范",
        "bands": [
            {"level": "一类", "ratio": [0.90, 1.00], "descriptor": "语句通顺连贯，用词准确，有生动表达，错别字极少"},
            {"level": "二类", "ratio": [0.70, 0.89], "descriptor": "语句基本通顺，偶有用词不当或少量语病"},
            {"level": "三类", "ratio": [0.50, 0.69], "descriptor": "语病较多或语句不通，影响理解"},
        ],
    },
]


def build_rubric(min_words: int, total_score: float = 100.0) -> dict:
    """生成三维分档量规；分值为题面满分的比例换算结果。"""
    rows = []
    for dim in RUBRIC_DIMENSIONS:
        rows.append({
            "dimension": dim["dimension"],
            "weight": dim["weight"],
            "full_score": round(total_score * dim["weight"], 1),
            "focus": dim["focus"],
            "bands": [
                {
                    "level": band["level"],
                    "score_range": [
                        round(total_score * dim["weight"] * band["ratio"][0], 1),
                        round(total_score * dim["weight"] * band["ratio"][1], 1),
                    ],
                    "descriptor": band["descriptor"],
                }
                for band in dim["bands"]
            ],
        })
    return {
        "standard": "中考作文评分口径（内容/结构/语言 三维分档）",
        "total_score": total_score,
        "min_words": min_words,
        "dimensions": rows,
    }


def chapters_of(db, book_id: int) -> list[int]:
    return [
        c.id for c in db.scalars(
            select(Chapter).where(Chapter.textbook_id == book_id)
            .order_by(Chapter.order_index, Chapter.id)
        )
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    changed_align = changed_rubric = 0
    with SessionLocal() as db:
        books = list(db.scalars(select(Textbook).where(Textbook.subject == "chinese")))
        for book in books:
            ch_ids = chapters_of(db, book.id)
            if not ch_ids:
                continue
            for q in db.scalars(
                select(Question).where(
                    Question.source_ref.like(f"selfbank:zh_fill:{book.id}:%")
                )
            ):
                idx = int(q.source_ref.rsplit(":", 1)[1])
                target = ch_ids[(idx - 1) % len(ch_ids)]
                if q.chapter_id != target:
                    changed_align += 1
                    if args.apply:
                        q.chapter_id = target
            for q in db.scalars(
                select(Question).where(
                    Question.source_ref.like(f"selfbank:zh_answer:{book.id}:%")
                )
            ):
                idx = int(q.source_ref.rsplit(":", 1)[1])
                target = ch_ids[(idx - 1) % len(ch_ids)]
                if q.chapter_id != target:
                    changed_align += 1
                    if args.apply:
                        q.chapter_id = target
            for q in db.scalars(
                select(Question).where(
                    Question.source_ref.like(f"selfbank:zh_comp:{book.id}:%")
                )
            ):
                content = dict(q.content or {})
                min_words = int(content.get("min_words") or 0)
                rubric = build_rubric(min_words)
                if content.get("rubric") != rubric:
                    changed_rubric += 1
                    if args.apply:
                        content["rubric"] = rubric
                        # 保留原 3 条要点作为「写作提示」，评分改为三维量规
                        content["scoring_points"] = [
                            f"{d['dimension']}（{int(d['weight'] * 100)}%）：{d['focus']}"
                            for d in RUBRIC_DIMENSIONS
                        ]
                        q.content = content
                        answer = dict(q.answer or {})
                        answer["rubric"] = rubric
                        answer["scoring_points"] = content["scoring_points"]
                        q.answer = answer
        if args.apply:
            db.commit()

    print(f"逐单元对齐改动 {changed_align} 题；习作量规改动 {changed_rubric} 题")
    if not args.apply:
        print("干跑模式：未写库")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
