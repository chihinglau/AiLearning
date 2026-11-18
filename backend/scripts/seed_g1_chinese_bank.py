"""补 g1 语文习作（composition）与第一单元字词填空（fill），并补 g1 数学上册单元填空。

用法：
    python scripts/seed_g1_chinese_bank.py --dry-run
    python scripts/seed_g1_chinese_bank.py --apply
"""

from __future__ import annotations

import argparse

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.content import Chapter, Question

SOURCE_NAME = "自建题型题库（原创）"
LICENSE_NOTE = "原创自建内容，不含第三方版权素材"

# 章节 -> 3 道字词/课文填空（答案唯一、可直接判分）
ZH_FILL: dict[int, list[tuple[str, str, str]]] = {
    # (题干, 答案, 解析)
    153: [
        ("一（　）小鸟。（填量词）", "只", "小鸟用「只」作量词。"),
        ("写出反义词：天——（　）", "地", "「天」与「地」相对。"),
        ("“人”字共有（　）笔。", "2", "「人」是两笔：撇、捺。"),
    ],
    154: [
        ("音节 mā 的声调是第（　）声。", "1", "ā 上标的是第一声。"),
        ("“o”和“e”都是（　）母。", "韵", "a o e 都是韵母。"),
        ("字母 b 的大写形式是（　）。", "B", "b 的大写是 B。"),
    ],
    155: [
        ("“b p m f”都是（　）母。", "声", "b p m f 都是声母。"),
        ("音节 pá 的声母是（　）。", "p", "pá 由声母 p 和韵母 a 组成。"),
        ("音节 dà 的韵母是（　）。", "a", "dà 的韵母是 a。"),
    ],
    156: [
        ("“ai ei ui”都是（　）韵母。", "复", "由两个元音合成的韵母叫复韵母。"),
        ("音节 hǎo 的韵母是（　）。", "ao", "hǎo 的韵母是 ao。"),
        ("音节 xīng 的韵母是（　）。", "ing", "xīng 的韵母是 ing。"),
    ],
    157: [
        ("《小小的船》中，月亮像一只（　）。", "小船", "课文把弯月比作小船。"),
        ("课文《秋天》里，天气（　）了。", "凉", "秋天天气变凉。"),
        ("“一片片叶子”中的“片”是（　）词。", "量", "「一片片」用量词「片」。"),
    ],
    158: [
        ("“日”和“月”合起来是（　）字。", "明", "日月合起来是「明」。"),
        ("“三人众”中的“众”表示人（　）。", "多", "三人为众，表示人多。"),
        ("升国旗时要（　）手敬礼。", "举", "升国旗时举手敬礼。"),
    ],
    159: [
        ("《比尾巴》中，猴子的尾巴（　）。", "长", "课文写猴子的尾巴长。"),
        ("《影子》里，影子常常跟着（　）。", "我", "影子常常跟着「我」。"),
        ("“影子在前”中，“前”的反义词是（　）。", "后", "前与后相对。"),
    ],
    160: [
        ("《雪地里的小画家》中，小鸭子画的是（　）。", "枫叶", "小鸭子的脚印像枫叶。"),
        ("冬天到了，青蛙在洞里（　）了。", "冬眠", "青蛙冬天要冬眠。"),
        ("《雪地里的小画家》中，小鸡画的是（　）。", "竹叶", "小鸡的脚印像竹叶。"),
    ],
    449: [
        ("“春夏秋冬”中，“秋”的后面是（　）。", "冬", "四季顺序是春夏秋冬。"),
        ("《姓氏歌》中，“木子”指的是（　）姓。", "李", "木子李。"),
        ("“春风”的“风”共有（　）笔。", "4", "「风」共四笔。"),
    ],
    450: [
        ("《吃水不忘挖井人》讲的是（　）带领乡亲挖井的故事。", "毛主席", "课文写毛主席关心乡亲。"),
        ("写出反义词：忘——（　）", "记", "「忘」与「记」相对。"),
        ("“井”字共有（　）笔。", "4", "「井」共四笔。"),
    ],
    451: [
        ("《我多想去看看》中，“我”想去（　）看升旗。", "北京", "课文写想去北京看升旗。"),
        ("“遥远”的意思是（　）。", "很远", "遥远就是距离很远。"),
        ("“告诉”中“诉”的声母是（　）。", "s", "sù 的声母是 s。"),
    ],
    452: [
        ("《一个接一个》中，小朋友先玩（　）。", "踩影子", "课文先写踩影子。"),
        ("“接”的意思是（　）。", "连着", "「接」表示连在一起。"),
        ("“睡觉”中“觉”的读音是（　）。", "jiào", "睡觉的「觉」读 jiào。"),
    ],
    453: [
        ("《动物儿歌》中，蜻蜓半空展翅（　）。", "飞", "儿歌写蜻蜓半空展翅飞。"),
        ("“蝴蝶”中“蝶”的部首是（　）。", "虫", "蝶的部首是虫字旁。"),
        ("蜘蛛在墙角（　）网。", "结", "蜘蛛结网。"),
    ],
    454: [
        ("《池上》中，小娃撑的是（　）。", "小艇", "诗里写小娃撑小艇。"),
        ("《小池》中，荷叶上立着一只（　）。", "蜻蜓", "小荷才露尖尖角，早有蜻蜓立上头。"),
        ("“泉眼无声惜细流”中“惜”的意思是（　）。", "爱惜", "「惜」是爱惜、珍惜。"),
    ],
    455: [
        ("《荷叶圆圆》中，荷叶是小水珠的（　）。", "摇篮", "小水珠把荷叶当摇篮。"),
        ("《荷叶圆圆》中，荷叶是小青蛙的（　）。", "歌台", "小青蛙把荷叶当歌台。"),
        ("《荷叶圆圆》中，荷叶是小蜻蜓的（　）。", "停机坪", "小蜻蜓把荷叶当停机坪。"),
    ],
    456: [
        ("要下雨了，燕子飞得（　）。", "低", "下雨前燕子低飞。"),
        ("要下雨了，蚂蚁在（　）。", "搬家", "下雨前蚂蚁搬家。"),
        ("要下雨了，小鱼到水面上来（　）。", "透气", "下雨前小鱼到水面透气。"),
    ],
}

ZH_COMPOSITION: dict[int, list[dict]] = {
    3: [
        {
            "title": "课间活动",
            "prompt": "下课了，同学们在操场上活动。请你用 3—5 句话写一写：谁在做什么，大家的心情怎样。",
            "points": [
                "写清时间、地点和人物（6 分）",
                "写出至少两个同学的具体活动（7 分）",
                "句子通顺，正确使用标点（7 分）",
            ],
            "sample": "下课了，操场上真热闹。小明在跳绳，小红在踢毽子。"
                      "我和同桌一起玩老鹰捉小鸡。大家都玩得很开心。",
        },
        {
            "title": "我的书包",
            "prompt": "请你用 3—5 句话介绍自己的书包：它是什么颜色、里面装着什么、你怎样爱护它。",
            "points": [
                "写出书包的颜色或样子（6 分）",
                "写出书包里的两样物品（7 分）",
                "语句通顺，书写工整（7 分）",
            ],
            "sample": "我有一个蓝色的书包。书包上有两只小熊猫。"
                      "里面装着语文书、数学书和一支铅笔。我每天把它整理得整整齐齐。",
        },
        {
            "title": "我喜欢的季节",
            "prompt": "请你用 3—5 句话写一写你最喜欢的季节：这个季节什么样、你喜欢做什么。",
            "points": [
                "写清是哪个季节（6 分）",
                "写出这个季节的一个景物或天气特点（7 分）",
                "写出自己在这个季节做的一件事，句子通顺（7 分）",
            ],
            "sample": "我最喜欢秋天。秋天到了，树叶变黄了，风一吹就落下来。"
                      "我和爸爸去公园捡落叶，还堆了一个小树叶堆。秋天真美。",
        },
    ],
    4: [
        {
            "title": "我的家",
            "prompt": "请你用 3—5 句话介绍自己的家：家里有谁、大家常常一起做什么。",
            "points": [
                "写清家里有几个人、分别是谁（6 分）",
                "写出一件家人一起做的事（7 分）",
                "句子通顺、标点正确（7 分）",
            ],
            "sample": "我家有三口人：爸爸、妈妈和我。爸爸很高，妈妈爱笑。"
                      "晚上我们一起吃饭，还一起看电视。我很爱我的家。",
        },
        {
            "title": "我帮了他",
            "prompt": "请你用 3—5 句话写一件你帮助别人的事：什么时候、你帮谁做了什么、心里怎么想。",
            "points": [
                "写清时间、人物和事情（6 分）",
                "写清帮助的过程（7 分）",
                "写出自己的感受，语句通顺（7 分）",
            ],
            "sample": "今天上午，同桌忘带铅笔了。我把自己的铅笔借给他。"
                      "他说谢谢我，我笑着说不用谢。帮助别人我心里很高兴。",
        },
        {
            "title": "我喜欢的小动物",
            "prompt": "请你用 3—5 句话写一写你喜欢的小动物：它长什么样、你喜欢和它做什么。",
            "points": [
                "写出动物的名称和样子（6 分）",
                "写出它的一个动作或习惯（7 分）",
                "写出你喜欢它的理由，语句通顺（7 分）",
            ],
            "sample": "我最喜欢的小动物是小猫。它有白白的身子，眼睛圆圆的。"
                      "它常在阳光下睡觉。我放学回家，它就跑到门口接我。",
        },
    ],
}

MATH_FILL: list[tuple[int, str, str, str]] = [
    (308, "10 可以分成 6 和（　）。", "4", "6 和 4 合起来是 10。"),
    (308, "8 和 9 中，较大的数是（　）。", "9", "9 比 8 大。"),
    (308, "按顺序填数：6、7、（　）、9。", "8", "6、7、8、9 依次多 1。"),
    (308, "5 和 2 合起来是（　）。", "7", "5 + 2 = 7。"),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    plan: list[Question] = []
    with SessionLocal() as db:
        chapter_kps: dict[int, list[int]] = {}
        for chapter_id in list(ZH_FILL) + [308]:
            kps = list(db.scalars(
                select(Question.knowledge_point_id)
                .where(Question.chapter_id == chapter_id, Question.knowledge_point_id.is_not(None))
                .distinct()
            ))
            chapter_kps[chapter_id] = [kp for kp in kps if kp]
        chapters = {c.id: c for c in db.scalars(select(Chapter).where(Chapter.id.in_(list(ZH_FILL) + [308])))}

        for chapter_id, items in ZH_FILL.items():
            kps = chapter_kps.get(chapter_id) or [None]
            for index, (stem, answer, analysis) in enumerate(items, start=1):
                plan.append(Question(
                    chapter_id=chapter_id,
                    knowledge_point_id=kps[(index - 1) % len(kps)],
                    subject="chinese",
                    q_type="fill",
                    content={"stem": stem},
                    options=None,
                    answer={"value": answer},
                    analysis=analysis,
                    difficulty=2,
                    tags=["fill", "grade1", chapters[chapter_id].name],
                    status="published",
                    source_type="original",
                    source_name=SOURCE_NAME,
                    source_ref=f"selfbank:zh_fill:{chapter_id}:{index}",
                    license_note=LICENSE_NOTE,
                ))

        for chapter_id, stem, answer, analysis in MATH_FILL:
            plan.append(Question(
                chapter_id=chapter_id,
                knowledge_point_id=(chapter_kps.get(chapter_id) or [None])[0],
                subject="math",
                q_type="fill",
                content={"stem": stem},
                options=None,
                answer={"value": answer},
                analysis=analysis,
                difficulty=2,
                tags=["fill", "grade1", chapters[chapter_id].name],
                status="published",
                source_type="original",
                source_name=SOURCE_NAME,
                source_ref=f"selfbank:math_fill:{chapter_id}:{stem[:8]}",
                license_note=LICENSE_NOTE,
            ))

        for book_id, comps in ZH_COMPOSITION.items():
            anchor = 153 if book_id == 3 else 449
            for index, comp in enumerate(comps, start=1):
                plan.append(Question(
                    chapter_id=anchor,
                    knowledge_point_id=None,
                    subject="chinese",
                    q_type="composition",
                    content={
                        "stem": comp["prompt"],
                        "title": comp["title"],
                        "min_words": 60,
                        "scoring_points": comp["points"],
                        "sample": comp["sample"],
                    },
                    options=None,
                    answer={
                        "value": comp["sample"],
                        "scoring_points": comp["points"],
                        "open_ended": True,
                    },
                    analysis="参考范文：" + comp["sample"],
                    difficulty=4,
                    tags=["composition", "grade1", comp["title"]],
                    status="published",
                    source_type="original",
                    source_name=SOURCE_NAME,
                    source_ref=f"selfbank:zh_comp:{book_id}:{index}",
                    license_note=LICENSE_NOTE,
                ))

    print(f"计划写入 {len(plan)} 题：fill {sum(1 for q in plan if q.q_type=='fill')} / "
          f"composition {sum(1 for q in plan if q.q_type=='composition')}")
    if not args.apply:
        print("干跑模式：未写库（加 --apply 落库）")
        return 0

    created = skipped = 0
    with SessionLocal() as db:
        for question in plan:
            if db.scalar(select(Question.id).where(Question.source_ref == question.source_ref)):
                skipped += 1
                continue
            db.add(question)
            created += 1
        db.commit()
    print(f"入库完成：created={created} skipped={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
