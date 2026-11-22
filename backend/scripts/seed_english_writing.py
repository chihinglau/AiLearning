"""英语 7–9 年级书面表达（composition）入库。

背景：上教版新教材重建后，7–9 年级题库只有 listening / choice / fill 四类，
期中卷、期末卷的「五、书面表达」节要 1 道 composition，缺题型会直接拒卷
（EXAM_PAPER_UNSUPPORTED）。本脚本按册补齐写作题：每册 4 道，落在第 1/3/5/7 单元，
同一册内不重复主题，期中(half_book)与期末(book)都抽得到不同题。

source_ref = selfbank:en_w:{chapter_id}:{idx}
"""

from __future__ import annotations

import argparse

from sqlalchemy import delete, select

from app.db.session import SessionLocal
from app.models.content import Chapter, KnowledgePoint, Question, Textbook
from scripts.align_sz_curriculum import POINT_SUFFIXES, SZ_VERSION_ENGLISH

SOURCE_NAME = "自建题型题库（原创）"
LICENSE_NOTE = "自建原创题，仅用于本平台教研与练习；不涉及第三方教材原文与真题。"

# (grade, semester, unit_index, title, stem, min_words, sample, scoring_points)
WRITING_ITEMS = [
    # ---------------- 7 年级上册 ----------------
    (7, "first", 1, "My best friend",
     "请以 “My best friend” 为题，写一篇 60 词左右的短文。要求：1）介绍他/她的外貌与性格；"
     "2）写一件你们一起经历过的事；3）说明你为什么珍惜这段友谊。", 60,
     "My best friend is Chen Jie. She is short but full of energy, and she always has a smile on her face. "
     "We met in Grade One and have shared the same desk for years. Last term I fell off my bike and could not "
     "walk to school, so she brought me the homework every evening. I am lucky to have a friend who is always "
     "there for me.",
     ["写清外貌与性格特点（8 分）", "用一般过去时叙述一件共同经历（8 分）", "语句通顺、拼写与标点规范，60 词以上（4 分）"]),
    (7, "first", 3, "My favourite season",
     "请以 “My favourite season” 为题，写一篇 60 词左右的短文。要求：1）点明你最喜欢的季节；"
     "2）写出该季节的天气特点；3）写两件你在这个季节常做的事。", 60,
     "My favourite season is autumn. In Shenzhen, autumn comes late, but the days become cool and the sky "
     "looks clear and blue. I like flying kites with my father in the park on Sunday afternoons. We also go "
     "hiking in the hills when the weather is fine. Autumn makes me feel calm and happy, and it is the best "
     "time of the year for me.",
     ["点明季节并描述天气（8 分）", "写出两件与该季节相关的活动（8 分）", "时态一致、连接词使用恰当，60 词以上（4 分）"]),
    (7, "first", 5, "A trip to space",
     "想象一次太空旅行，以 “A trip to space” 为题写一篇 60 词左右的短文。要求：1）写你怎样到达太空；"
     "2）写你在太空中看到或做了什么；3）写出你的感受。", 60,
     "Last night I had a dream. I flew to space in a small white rocket. From the window I saw the Earth, blue "
     "and round, like a glass ball. I walked on the Moon and my steps were slow and light. I picked up a grey "
     "stone and put it in my pocket. When I woke up, I still felt the silence of space.",
     ["想象合理，交代到达太空的方式（6 分）", "写清所见所做，至少两个细节（10 分）", "表达真实感受，语言连贯（4 分）"]),
    (7, "first", 7, "My after-school life",
     "以日记形式写一篇 60 词左右的短文，介绍你的课后生活。要求：1）开头写日期；2）写两个课后活动；"
     "3）写出你的收获。", 60,
     "Monday, 15 September\nAfter school I stay for the science club. We build small cars with paper and "
     "bottles. Today my car ran the fastest, and the teacher said, “Well done!” I also play table tennis on "
     "Wednesdays. Our coach teaches us to serve and to move quickly, and I have become much better than last "
     "year. After-school time is busy, but I learn a lot and make new friends.",
     ["日记格式正确（日期 + 正文）（4 分）", "写清两个课后活动及过程（10 分）", "写出收获，一般现在时为主（6 分）"]),

    # ---------------- 7 年级下册 ----------------
    (7, "second", 1, "A person I admire",
     "请以 “A person I admire” 为题，写一篇 60 词左右的短文。要求：1）写明这个人是谁；2）写他/她做过的一件让你敬佩的事；"
     "3）说明你想从他/她身上学到什么。", 60,
     "The person I admire most is my grandmother. She is seventy years old, but she still grows vegetables in "
     "her small garden every morning. She never complains, and she always helps our neighbours when they are "
     "in trouble. When I feel sad, she tells me stories and makes me laugh. I hope I can be as strong and kind "
     "as she is.",
     ["写明人物身份与关系（6 分）", "用具体事例说明敬佩的原因（10 分）", "写出自己的学习目标，语言得体（4 分）"]),
    (7, "second", 3, "Let's protect our trees",
     "学校英文报征集环保短文，请以 “Let's protect our trees” 为题写一篇 60 词左右的短文。要求：1）说明树木的作用；"
     "2）指出树木面临的威胁；3）提出两条具体可行的建议。", 60,
     "Trees are our good friends. They give us clean air, shade in summer and homes for birds. But some people "
     "cut down trees for money, and our city is getting hotter. Let's do something now. We can plant a tree "
     "every spring and look after it. We can also use less paper. If everyone helps, our city will be greener "
     "and healthier.",
     ["说明树木的两个作用（6 分）", "指出威胁，过渡自然（6 分）", "两条建议具体可行，用祈使句号召（8 分）"]),
    (7, "second", 5, "Why we should save water",
     "请以 “Why we should save water” 为题，写一篇 60 词左右的短文。要求：1）说明水在生活中的用途；"
     "2）说明为什么要节约用水；3）写出你在家节水的一个做法。", 60,
     "Water is important in our life. We drink it, cook with it and wash with it. But clean water is limited, "
     "and many places are short of it. In my home we save water every day. I turn off the tap when I brush my "
     "teeth, and my mother uses the water from washing rice to water the plants. Small habits can make a big "
     "difference.",
     ["写出水的两种用途（6 分）", "说清节水原因，逻辑清楚（8 分）", "写出一个真实做法，语句连贯（6 分）"]),
    (7, "second", 7, "A short poem about my school",
     "请为校刊写一首 4 行的英文小诗，主题是“我的学校”，并在诗后写 2—3 句说明你的创作想法（合计不少于 30 词）。", 30,
     "Green trees, blue sky,\nBirds sing and fly.\nOur school is small,\nBut we love it all.\n"
     "I wrote this poem because our school has a big garden. In spring the birds come back and sing in the "
     "morning. I wanted to share this happy picture with my classmates.",
     ["四行诗格式正确、押韵自然（8 分）", "诗歌内容与“我的学校”主题相关（6 分）", "说明创作想法清楚，语言通顺（6 分）"]),

    # ---------------- 8 年级上册 ----------------
    (8, "first", 1, "How I use a dictionary",
     "请以 “How I use a dictionary” 为题，写一篇 60 词左右的短文，向同学介绍你的查词典方法。要求："
     "1）说明查词的基本步骤；2）说明你会关注哪些信息；3）写出这样做的好处。", 60,
     "A dictionary is a useful tool for learning English. When I meet a new word, I first look at its spelling "
     "and then find it in the dictionary. I read the meaning, the part of speech and one example sentence. "
     "Sometimes I write the word and the sentence in my notebook. In this way I remember new words better and "
     "use them correctly.",
     ["步骤清楚，用 first/then 等顺序词（8 分）", "提到词义、词性、例句等信息（8 分）", "写出好处，语句规范（4 分）"]),
    (8, "first", 3, "My digital life",
     "请以 “My digital life” 为题，写一篇 60 词左右的短文。要求：1）写两个你使用数字设备的场景；"
     "2）写出你给自己定的一条使用规则；3）说明你对数字生活的看法。", 60,
     "Digital life makes my day easy and fast. In the morning I check the weather on my phone. At school I use "
     "a computer to search for information for my project. After dinner I watch a short English video with my "
     "family. But I also keep some rules: no phone for an hour before bed, and no games on school nights. "
     "Digital tools are helpful only when we use them wisely.",
     ["写出两个真实使用场景（8 分）", "使用规则明确、可执行（6 分）", "看法清楚，能收束全文（6 分）"]),
    (8, "first", 5, "My exchange trip plan",
     "你将要参加学校交换生项目，请给将要接待你的外国同学 Tom 写一封电子邮件（60 词左右）。要求："
     "1）说明访问时间与人数；2）介绍到校后的活动安排；3）询问一个你关心的问题。", 60,
     "Dear Tom,\nI am happy to tell you about our school exchange trip. We will visit your school next month "
     "and stay for five days. In the morning we will join your classes, and in the afternoon we will visit a "
     "museum and a park. I am a little nervous about speaking English all day, but I am also very excited. "
     "Could you tell me what clothes I should bring?\nYours,\nLi Hua",
     ["邮件格式（称呼、正文、落款）完整（4 分）", "时间与活动安排清楚，时态正确（10 分）", "问题得体，语气礼貌（6 分）"]),
    (8, "first", 7, "How to improve your memory",
     "请以 “How to improve your memory” 为题，写一篇 60 词左右的短文，给同学提三条建议。要求："
     "1）用 first/second/third 组织；2）每条建议说明理由；3）结尾鼓励同学尝试。", 60,
     "Everyone wants a good memory, and here are three ways to get one. First, review what you learn on the "
     "same day, because your memory fades quickly after that. Second, make pictures or stories with the new "
     "words; the funnier they are, the easier you remember them. Third, sleep well, because a tired brain "
     "cannot hold new information. Try these for a month and you will be surprised.",
     ["三条建议分点清楚（9 分）", "每条给出理由，句式多样（8 分）", "结尾有号召力，60 词以上（3 分）"]),

    # ---------------- 8 年级下册 ----------------
    (8, "second", 1, "A helping hand",
     "学校学生会将开展捐赠活动，请以学生会名义写一份 60 词左右的倡议书。要求：1）说明身边需要帮助的人；"
     "2）说明捐赠的时间、地点与物品；3）发出号召。", 60,
     "Dear classmates,\nMany children in our city need help. Some have no warm clothes in winter, and some "
     "cannot afford books. We can make a difference with small actions. Next Friday we will collect old books "
     "and winter coats in the school hall. You can also write a card with warm words. Let's give a helping "
     "hand and make this winter warmer for them.\nThe Student Union",
     ["倡议书格式与称呼正确（4 分）", "时间、地点、物品交代完整（10 分）", "号召有力，语气真诚（6 分）"]),
    (8, "second", 3, "My favourite cartoon",
     "请以 “My favourite cartoon” 为题，写一篇 60 词左右的短文。要求：1）写出动画片名与主角；"
     "2）介绍主角的一个特点并举一个例子；3）说明你喜欢它的原因。", 60,
     "My favourite cartoon is a Chinese animation about a clever monkey. He is brave and funny, and he never "
     "gives up when he meets difficulties. Once he lost his magic stick, but he still found a way to save his "
     "friends. The pictures are beautiful and the music is lovely. After a long day at school, watching one "
     "episode makes me relaxed and happy.",
     ["片名与主角交代清楚（6 分）", "用一个具体例子说明性格特点（10 分）", "喜欢的原因真实可信（4 分）"]),
    (8, "second", 5, "Protect the animals in danger",
     "请以 “Protect the animals in danger” 为题，写一篇 60 词左右的短文。要求：1）举出两种濒危动物；"
     "2）说明它们面临危险的原因；3）提出两条保护做法。", 60,
     "Many animals are in danger today. Tigers, pandas and whales are losing their homes because of cutting "
     "trees and dirty water. If we do nothing, our children may only see them in books. We can help in simple "
     "ways. We should not buy things made from wild animals, and we should keep rivers and parks clean. "
     "Every small action protects a life.",
     ["举出两种动物，用现在进行时描述现状（6 分）", "说清原因，因果衔接自然（8 分）", "两条做法具体，用 should 表达建议（6 分）"]),
    (8, "second", 7, "Is space exploration worth it?",
     "学校辩论社围绕“太空探索是否值得”征集观点短文。请写一篇 60 词左右的短文。要求：1）先说出一种反对意见；"
     "2）表明你的观点并给出两条理由；3）结尾提出你的建议。", 60,
     "Some people say space exploration costs too much money and we should spend it on schools and hospitals. "
     "I understand this idea, but I do not fully agree. Space research has given us weather satellites and "
     "better phones, and it teaches us about our own planet. Exploring space is like exploring the sea in the "
     "past. We should do it carefully, but we should not stop.",
     ["准确转述对方观点（6 分）", "观点明确，两条理由有支撑（10 分）", "结尾建议合理，逻辑完整（4 分）"]),

    # ---------------- 9 年级上册 ----------------
    (9, "first", 1, "A great person I admire",
     "请以 “A great person I admire” 为题，写一篇 70 词左右的短文。要求：1）写明人物身份；2）用一件具体事例说明他/她的贡献；"
     "3）写出他/她对你的影响。", 70,
     "The great person I admire most is Yuan Longping. He spent his whole life on rice. He walked in the fields "
     "under the hot sun, tested thousands of plants, and finally developed hybrid rice. Because of him, "
     "millions of people have enough to eat. He was famous all over the world, but he lived simply, wore old "
     "clothes and worked like a farmer. He shows me that a great person is someone who serves others.",
     ["人物身份与领域清楚（6 分）", "事例具体，突出贡献（10 分）", "写出对自己的影响，议论与叙述结合（4 分）"]),
    (9, "first", 3, "A family tradition",
     "请以 “A family tradition” 为题，写一篇 70 词左右的短文。要求：1）介绍你们家的一项传统；2）描述这项传统的具体过程；"
     "3）说明它对你们家的意义。", 70,
     "In my family there is a small tradition. Every Spring Festival, before dinner, we make dumplings "
     "together in the kitchen. My grandmother rolls the dough, my father cuts the meat, and I fold the "
     "dumplings, though mine are always ugly and fat. Then we put a coin in one dumpling. Whoever finds it is "
     "said to have good luck for the whole year. My cousins shout with joy when they find it. The food is "
     "simple, but it holds our family's warmth.",
     ["传统内容明确、有辨识度（6 分）", "过程描写有序，人物分工清楚（10 分）", "点明意义，结尾有升华（4 分）"]),
    (9, "first", 5, "What makes me happy",
     "请以 “What makes me happy” 为题，写一篇 70 词左右的短文。要求：1）写出三个让你开心的瞬间；"
     "2）选择其中一个展开描述；3）写出你对幸福的理解。", 70,
     "Happiness is not always about big things. For me, it often comes in small moments. I am happy when I "
     "finish a difficult maths problem and the answer is right. I am happy when I run with my friends after "
     "school and the cool wind touches my face. I am happy when my mother cooks my favourite noodles on "
     "Sunday, and the whole kitchen smells sweet. One evening I shared those noodles with my little cousin, "
     "and she smiled at me. I try to notice these moments, and my days become brighter.",
     ["三个瞬间并列清楚，句式有变化（10 分）", "其中一个瞬间有细节描写（8 分）", "对幸福的理解有思考（2 分）"]),
    (9, "first", 7, "The story I like best",
     "请以 “The story I like best” 为题，写一篇 70 词左右的书评。要求：1）写出书名与作者；2）简述故事内容（不剧透结局）；"
     "3）说明你喜欢它的理由。", 70,
     "The story I like best is a short novel by Mark Twain. It tells how a clever boy uses his wit to get out "
     "of trouble again and again. The language is funny, and every chapter has a small surprise. What I like "
     "most is the boy's honesty with himself: he is afraid, but he still does the right thing. I have read it "
     "twice, and each time I found something new.",
     ["书名与作者信息完整（6 分）", "内容简述清楚，不透露结局（8 分）", "理由有说服力，表达个人感受（6 分）"]),
]


def _find_point(db, chapter: Chapter, grade: int):
    section = db.scalar(
        select(KnowledgePoint).where(
            KnowledgePoint.subject == "english",
            KnowledgePoint.grade == grade,
            KnowledgePoint.node_type == "section",
            KnowledgePoint.name == chapter.name,
        )
    )
    if section is None:
        return None
    return db.scalar(
        select(KnowledgePoint).where(
            KnowledgePoint.parent_id == section.id,
            KnowledgePoint.order_index == 4,  # 第 4 个 point = 词汇填空与表达
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    created = updated = 0
    with SessionLocal() as db:
        for grade, semester, unit_index, title, stem, min_words, sample, points in WRITING_ITEMS:
            book = db.scalar(
                select(Textbook).where(
                    Textbook.subject == "english",
                    Textbook.grade == grade,
                    Textbook.semester == semester,
                    Textbook.version == SZ_VERSION_ENGLISH,
                )
            )
            if book is None:
                print(f"g{grade}-{semester} 无上教版教材，跳过")
                continue
            chapter = db.scalar(
                select(Chapter).where(
                    Chapter.textbook_id == book.id,
                    Chapter.order_index == unit_index,
                    Chapter.is_placeholder == 0,
                )
            )
            if chapter is None:
                print(f"g{grade}-{semester} 第 {unit_index} 单元缺失，跳过")
                continue

            kp = _find_point(db, chapter, grade)
            content = {
                "stem": stem,
                "title": title,
                "sample": sample,
                "min_words": min_words,
                "scoring_points": points,
            }
            payload = dict(
                chapter_id=chapter.id,
                knowledge_point_id=kp.id if kp else None,
                subject="english",
                q_type="composition",
                content=content,
                options=None,
                answer={"value": sample, "open_ended": True, "scoring_points": points},
                analysis="参考范文：" + sample.replace("\n", " "),
                difficulty=3,
                tags=["composition", f"grade{grade}", title],
                status="published",
                source_type="original",
                source_name=SOURCE_NAME,
                source_ref=f"selfbank:en_w:{chapter.id}:1",
                license_note=LICENSE_NOTE,
            )
            existing = db.scalar(
                select(Question).where(Question.source_ref == payload["source_ref"])
            )
            if existing is not None:
                for k, v in payload.items():
                    setattr(existing, k, v)
                updated += 1
            else:
                db.add(Question(**payload))
                created += 1
            print(f"  g{grade}-{semester} U{unit_index} {title} → {chapter.name}")

        if args.apply:
            db.commit()
        print(f"{'已写入' if args.apply else '干跑'}：写作题新建 {created} / 改写 {updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
