"""按单元补语文习作（composition）：每单元 1 条，含中考三维量规（内容/结构/语言）。

量规不另造，直接复用库内 `selfbank:zh_comp:*` 已有模板，保证 54 题与新增题口径一致。
"""

from __future__ import annotations

import argparse
import copy

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.content import Chapter, Question, Textbook

SOURCE_NAME = "自建题型题库（原创）"
LICENSE_NOTE = "原创自建内容，不含第三方版权素材"

# 按学段：题目、提示、MinWords
PROMPTS = {
    (1, 2): [
        ("看图写话：下课以后", "下课了，同学们在操场上活动。请你用 3—5 句话写一写：谁在做什么，大家的心情怎样。", 60),
        ("我最喜欢的玩具", "请你写一写自己最喜欢的玩具：它是什么样子的？你为什么喜欢它？", 60),
        ("快乐的周末", "回忆一个让你开心的周末，用几句话写清楚：你和谁在一起、做了什么。", 60),
        ("我的好朋友", "写一写你的好朋友：他（她）长什么样？你们常一起做什么？", 60),
        ("一场小雨", "下小雨了，你看到了什么、听到了什么？用几句话写下来。", 70),
        ("我会做的一件事", "你会做哪件家务或小事？请按顺序写清楚你是怎么做的。", 70),
        ("我的小书包", "看看你的书包：里面有什么？你最喜欢哪一样？为什么？", 70),
        ("第一次坐公交车", "写一次坐公交车的经历：你看到了什么，遇到了谁。", 70),
        ("我家的小动物", "家里养过什么小动物？它长什么样？你和它之间发生过什么事？", 70),
        ("课间十分钟", "下课十分钟里，教室里和操场上分别是什么样子？", 70),
        ("今天我当家", "如果让你当一天家，你会做哪些事？写一写你的安排。", 70),
        ("窗外的树", "观察窗外的树：它的叶子、枝条是什么样子的？", 70),
        ("我给妈妈做件事", "你为妈妈做过什么事？她当时是什么反应？", 70),
        ("一个下雨天的早晨", "下雨天的早晨和平时有什么不同？写几句。", 70),
        ("我最爱去的地方", "你最爱去哪里？那里有什么吸引你？", 70),
        ("我学会了一招", "最近你学会了一个什么小本领？你是怎么学会的？", 70),
        ("放学路上", "放学回家的一段路上，你看到了什么？写几句。", 70),
    ],
    (3, 4): [
        ("写一个熟悉的人", "选一位你熟悉的人，用具体的事例写出他（她）的特点，不少于 300 字。", 300),
        ("一处景物", "按一定顺序写一处你喜欢的景物，写出它的特点，不少于 300 字。", 300),
        ("一次难忘的经历", "把一件让你难忘的事写清楚：起因、经过、结果要完整，不少于 300 字。", 300),
        ("我的动物朋友", "写一种你养过或见过的动物，抓住外形和习性，不少于 300 字。", 300),
        ("秋天的校园", "观察秋天的校园，用上看到的、听到的和想到的，不少于 300 字。", 300),
        ("我学会了____", "把题目补充完整，写清楚学会的过程和感受，不少于 300 字。", 300),
        ("我的小秘密", "写一件只有你知道的小事，把事情说清楚，不少于 300 字。", 300),
        ("一次小试验", "写一次你做过的实验或小制作：怎么做的，结果怎样，不少于 300 字。", 300),
        ("街头一角", "选一个街头场景写一写，注意人物和声音，不少于 300 字。", 300),
        ("我和书的故事", "写一件你与书有关的事，不少于 300 字。", 300),
        ("我的同桌", "写你的同桌：他（她）有什么特点？用一件事说明，不少于 300 字。", 300),
        ("下雨那天", "写一个下雨天发生的事，注意天气与心情的联系，不少于 300 字。", 300),
        ("一次误会", "写一次你与同学之间的误会：怎么发生，怎么解决，不少于 300 字。", 300),
        ("我最难忘的一顿饭", "写一顿你难忘的饭：和谁吃，在哪里，为什么难忘，不少于 300 字。", 300),
        ("教室里的小插曲", "写课堂上发生的一件小事，把过程写具体，不少于 300 字。", 300),
        ("我的家乡", "介绍你的家乡：一处景物或一种风俗，不少于 300 字。", 300),
        ("一句让我难忘的话", "写出这句话，并写清它为什么让你难忘，不少于 300 字。", 300),
    ],
    (5, 6): [
        ("成长路上的一件事", "选一件让你有所成长的事，写清细节与体会，不少于 450 字。", 450),
        ("家乡的风物", "介绍家乡的一处风物或一种风俗，写出它与人们生活的关系，不少于 450 字。", 450),
        ("一次合作", "写一次与他人合作的经历，突出过程中的困难与解决办法，不少于 450 字。", 450),
        ("我眼中的四季", "选一个季节，从景物、活动和感受三方面展开，不少于 450 字。", 450),
        ("写给____的一封信", "把题目补充完整，格式规范，内容具体，不少于 450 字。", 450),
        ("科技改变生活", "结合身边事例，写一写科技给生活带来的变化，不少于 450 字。", 450),
        ("那一次，我懂得了____", "把题目补充完整，写清是什么让你懂得，不少于 450 字。", 450),
        ("身边的劳动者", "写一位你身边的劳动者，用具体细节表现他的工作，不少于 450 字。", 450),
        ("我的一次选择", "写一次你做出选择的过程与理由，不少于 450 字。", 450),
        ("一件小事带来的改变", "写一件小事如何影响了你，注意前后对比，不少于 450 字。", 450),
        ("校园里的四季", "写校园在某个季节的样子，注意观察顺序，不少于 450 字。", 450),
        ("说说我的名字", "写你的名字的由来与含义，并写一件与之相关的事，不少于 450 字。", 450),
        ("一次户外活动", "写一次爬山、野营或运动会，写清过程与感受，不少于 450 字。", 450),
        ("我身边的变化", "写近几年身边的一处变化，用具体事例说明，不少于 450 字。", 450),
        ("我和我的母亲", "通过一到两件事写你与母亲的关系，不少于 450 字。", 450),
        ("教室里的一堂课", "写一堂印象最深的课，注意课堂细节，不少于 450 字。", 450),
        ("未来的____", "把题目补充完整，展开合理想象，不少于 450 字。", 450),
    ],
    (7, 9): [
        ("那一刻，我长大了", "围绕一个具体瞬间，写出心理变化与成长体会，不少于 600 字。", 600),
        ("留在心底的风景", "写一处（或一幕）让你久久难忘的风景，注意细节与情感，不少于 600 字。", 600),
        ("我与书的故事", "写一段与阅读有关的经历，表达你的思考，不少于 600 字。", 600),
        ("温暖", "以「温暖」为题，通过一件具体的事写出人情的温度，不少于 600 字。", 600),
        ("我的青春里有____", "把题目补充完整，写一篇记叙文，不少于 600 字。", 600),
        ("议论：小事不小", "围绕「小事不小」写一篇议论文，观点明确、论据充分，不少于 600 字。", 600),
        ("那束光", "以「那束光」为题，写一件改变你的事，不少于 600 字。", 600),
        ("慢下来", "以「慢下来」为题，议论或记叙均可，不少于 600 字。", 600),
        ("一次道歉", "写一次道歉或道歉的对象，写出心理变化，不少于 600 字。", 600),
        ("我所理解的责任", "结合具体事例谈责任，观点明确，不少于 600 字。", 600),
        ("窗外", "以「窗外」为题，写出所见与所想，不少于 600 字。", 600),
        ("给____上的一堂课", "把题目补充完整，写一堂让你印象深刻的课，不少于 600 字。", 600),
        ("与我同行的", "把题目补充完整，写一路上陪伴你的人或物，不少于 600 字。", 600),
        ("平凡与不平凡", "围绕这一话题写一篇议论文，不少于 600 字。", 600),
        ("一场争论", "写一次你参与的争论，写清各方观点与你的思考，不少于 600 字。", 600),
        ("旧物", "以「旧物」为题，写一件旧物背后的故事，不少于 600 字。", 600),
        ("一次出发", "写一次出发或远行，写出前因后果与感受，不少于 600 字。", 600),
        ("说「留下」", "围绕「留下」写一篇议论文或记叙文，不少于 600 字。", 600),
        ("一封没有寄出的信", "写一封你想写却没有寄出的信，说清为什么没寄，不少于 600 字。", 600),
        ("习惯", "以「习惯」为题，写一个你养成或改掉的习惯，不少于 600 字。", 600),
        ("那天我没说出口", "写一件当时没说出口、事后回想的事，写出心理活动，不少于 600 字。", 600),
    ],
}


def band_for(grade: int) -> tuple[int, int]:
    for lo, hi in PROMPTS:
        if lo <= grade <= hi:
            return (lo, hi)
    return (7, 9)


MAX_PROMPT_USES = 2  # 全库同一题目最多出现 2 次


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--grades", nargs="+", type=int, default=list(range(1, 10)))
    args = parser.parse_args()

    planned = []
    prompt_uses: dict[str, int] = {}
    with SessionLocal() as db:
        template = db.scalar(select(Question).where(Question.source_ref.like("selfbank:zh_comp:%")))
        if template is None:
            print("缺少三维量规模板，终止")
            return 1
        rubric_tpl = copy.deepcopy(template.content["rubric"])

        for book in db.scalars(
            select(Textbook).where(
                Textbook.subject == "chinese",
                Textbook.grade.in_(args.grades),
            ).order_by(Textbook.grade, Textbook.semester)
        ):
            chapters = list(db.scalars(
                select(Chapter).where(Chapter.textbook_id == book.id)
                .order_by(Chapter.order_index, Chapter.id)
            ))
            unit_heads = [c for c in chapters if "单元" in (c.name or "")]
            if not unit_heads:
                unit_heads = chapters
            pool = PROMPTS[band_for(book.grade)]
            for i, chapter in enumerate(unit_heads, start=1):
                # 全库账本：优先取「已用次数最少」的题目，避免兜底造成第 3 次复用
                cands = [pool[(book.id + i + offset) % len(pool)] for offset in range(len(pool))]
                chosen = min(cands, key=lambda p: (prompt_uses.get(p[0], 0), cands.index(p)))
                title, stem, min_words = chosen
                prompt_uses[title] = prompt_uses.get(title, 0) + 1
                rubric = copy.deepcopy(rubric_tpl)
                rubric["min_words"] = min_words
                planned.append({
                    "book": book, "chapter": chapter, "index": i,
                    "title": title, "stem": stem, "min_words": min_words, "rubric": rubric,
                    "difficulty": 4 if book.grade >= 7 else 3,
                })

        print(f"计划写入习作 {len(planned)} 题（覆盖 {len({p['book'].id for p in planned})} 册）")
        if not args.apply:
            print("干跑模式：未写库")
            return 0

        created = updated = 0
        for item in planned:
            ref = f"selfbank:zh_compu:{item['book'].id}:{item['chapter'].id}:{item['index']}"
            payload = dict(
                chapter_id=item["chapter"].id,
                subject="chinese",
                q_type="composition",
                content={
                    "stem": item["stem"],
                    "title": item["title"],
                    "min_words": item["min_words"],
                    "scoring_points": [
                        "内容（40%）：立意与选材：切题、中心明确、材料具体真实",
                        "结构（30%）：条理与衔接：段落清楚、顺序合理、有过渡",
                        "语言（30%）：表达与规范：语句通顺、用词准确、书写标点规范",
                    ],
                    "rubric": item["rubric"],
                },
                answer={"value": "开放式作答，按三维量规分档评分", "open_ended": True,
                        "rubric": item["rubric"]},
                analysis="按内容 40%、结构 30%、语言 30% 三维分档评分。",
                difficulty=item["difficulty"],
                tags=["composition", "习作", "by_unit", f"g{item['book'].grade}"],
                status="published",
                source_type="original",
                source_name=SOURCE_NAME,
                source_ref=ref,
                license_note=LICENSE_NOTE,
            )
            row = db.scalar(select(Question).where(Question.source_ref == ref))
            if row is not None:
                for k, v in payload.items():
                    setattr(row, k, v)
                row.knowledge_point_id = None
                updated += 1
                continue
            db.add(Question(knowledge_point_id=None, **payload))
            created += 1
        db.commit()
        print(f"新建 {created} 题，改写 {updated} 题")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
