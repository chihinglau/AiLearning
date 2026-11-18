# -*- coding: utf-8 -*-
"""english / g6 / 下册 内容包（2026-11-13）。章节名逐字取下册骨架（牛津深圳版六下）。
语音知识点用「单词 + 音标」成对数据，配专用题型，避免与词义题模板混用。
"""

UNITS = [
    ("Unit 1 You and me", "介绍自己与他人的信息交流。"),
    ("Unit 2 Changes in our lives", "生活变化与过去现在的对比。"),
    ("Unit 3 Our school in the future", "未来学校的设想。"),
    ("Unit 4 Art", "艺术形式与欣赏表达。"),
    ("Unit 5 Crafts", "手工制作与材料工具。"),
    ("Unit 6 PE lessons", "体育课活动与运动安全。"),
    ("Unit 7 Helping others", "帮助他人与志愿服务。"),
    ("Unit 8 Reading signs", "标识的认读与含义。"),
    ("Unit 9 Reusing things", "物品再利用与环保。"),
    ("Unit 10 Great storybooks", "故事书阅读与分享。"),
    ("Unit 11 Western festivals", "西方节日的时间与习俗。"),
    ("Unit 12 The five peas", "故事阅读与寓意理解。"),
]

DATA = {
    1: [
        {"name": "Unit 1 的自我介绍", "note": "自我介绍表达", "items": [
            ("My name is Peter.", "我叫彼得。"), ("I am eleven years old.", "我十一岁。"), ("I come from China.", "我来自中国。"), ("Nice to meet you.", "很高兴认识你。")]},
        {"name": "Unit 1 的兴趣爱好", "note": "爱好词汇", "items": [
            ("playing chess", "下棋"), ("collecting stamps", "集邮"), ("riding a bike", "骑自行车"), ("making models", "做模型")]},
        {"name": "Unit 1 的问答句型", "note": "信息问答句型", "items": [
            ("How old are you?", "你多大了？"), ("Where are you from?", "你来自哪里？"), ("What do you like doing?", "你喜欢做什么？"), ("I like reading stories.", "我喜欢读故事。")]},
        {"name": "Unit 1 的语音与语调", "note": "元音读音与语调", "words": [
            ("name", "/eɪ/"), ("like", "/aɪ/"), ("box", "/ɒ/"), ("run", "/ʌ/")]},
    ],
    2: [
        {"name": "Unit 2 的生活变化", "note": "变化表达", "items": [
            ("in the past", "在过去"), ("nowadays", "如今"), ("changed a lot", "变化很大"), ("used to", "过去常常")]},
        {"name": "Unit 2 的生活用品", "note": "生活用品词汇", "items": [
            ("telephone", "电话"), ("computer", "电脑"), ("washing machine", "洗衣机"), ("bicycle", "自行车")]},
        {"name": "Unit 2 的对比句型", "note": "过去现在对比句型", "items": [
            ("People used to write letters.", "人们过去常写信。"), ("Now we send emails.", "现在我们发电子邮件。"), ("Life has changed a lot.", "生活变化很大。"), ("What was life like in the past?", "过去的生活是什么样的？")]},
        {"name": "Unit 2 的语音与语调", "note": "元音读音与语调", "words": [
            ("sleep", "/iː/"), ("book", "/ʊ/"), ("home", "/əʊ/"), ("park", "/ɑː/")]},
    ],
    3: [
        {"name": "Unit 3 的未来学校", "note": "未来校园词汇", "items": [
            ("future school", "未来的学校"), ("e-book", "电子书"), ("robot teacher", "机器人老师"), ("online lesson", "网课")]},
        {"name": "Unit 3 的学习方式", "note": "学习方式短语", "items": [
            ("study at home", "在家学习"), ("use a computer", "使用电脑"), ("learn in groups", "小组学习"), ("ask the robot", "问机器人")]},
        {"name": "Unit 3 的设想句型", "note": "设想句型", "items": [
            ("There will be robots in our school.", "我们学校将有机器人。"), ("Students will not carry heavy bags.", "学生不用背很重的书包。"), ("What will school be like?", "学校将会是什么样？"), ("I think it will be better.", "我认为它会更好。")]},
        {"name": "Unit 3 的语音与语调", "note": "元音读音与语调", "words": [
            ("hear", "/ɪə/"), ("cute", "/juː/"), ("meat", "/iː/"), ("girl", "/ɜː/")]},
    ],
    4: [
        {"name": "Unit 4 的艺术形式", "note": "艺术形式词汇", "items": [
            ("painting", "绘画"), ("sculpture", "雕塑"), ("music", "音乐"), ("dance", "舞蹈")]},
        {"name": "Unit 4 的艺术欣赏", "note": "欣赏表达", "items": [
            ("beautiful", "美丽的"), ("colourful", "色彩丰富的"), ("interesting", "有趣的"), ("moving", "感人的")]},
        {"name": "Unit 4 的艺术问答", "note": "艺术问答句型", "items": [
            ("What kind of art do you like?", "你喜欢哪种艺术？"), ("I like painting best.", "我最喜欢绘画。"), ("Why do you like it?", "你为什么喜欢它？"), ("Because it is colourful.", "因为它色彩丰富。")]},
        {"name": "Unit 4 的语音与语调", "note": "元音读音与语调", "words": [
            ("art", "/ɑː/"), ("autumn", "/ɔː/"), ("eight", "/eɪ/"), ("hot", "/ɒ/")]},
    ],
    5: [
        {"name": "Unit 5 的手工材料", "note": "材料词汇", "items": [
            ("paper", "纸"), ("glue", "胶水"), ("string", "细绳"), ("cardboard", "硬纸板")]},
        {"name": "Unit 5 的制作动作", "note": "制作动作短语", "items": [
            ("cut out", "剪下来"), ("stick together", "粘在一起"), ("fold the paper", "折纸"), ("tie a knot", "打结")]},
        {"name": "Unit 5 的制作问答", "note": "制作问答句型", "items": [
            ("What are you making?", "你在做什么？"), ("I am making a card.", "我在做一张卡片。"), ("What do we need?", "我们需要什么？"), ("We need paper and glue.", "我们需要纸和胶水。")]},
        {"name": "Unit 5 的语音与语调", "note": "辅音与元音读音", "words": [
            ("bed", "/e/"), ("shop", "/ʃ/"), ("this", "/ð/"), ("cat", "/æ/")]},
    ],
    6: [
        {"name": "Unit 6 的运动项目", "note": "运动词汇", "items": [
            ("long jump", "跳远"), ("high jump", "跳高"), ("relay race", "接力赛"), ("sit-up", "仰卧起坐")]},
        {"name": "Unit 6 的运动安全", "note": "安全提示短语", "items": [
            ("warm up", "热身"), ("drink water", "喝水"), ("be careful", "小心"), ("wear trainers", "穿运动鞋")]},
        {"name": "Unit 6 的体育问答", "note": "体育课句型", "items": [
            ("What do you do in PE lessons?", "你们体育课做什么？"), ("We run and jump.", "我们跑步和跳跃。"), ("How often do you have PE?", "你们多久上一次体育课？"), ("Twice a week.", "一周两次。")]},
        {"name": "Unit 6 的语音与语调", "note": "元音读音与口令语调", "words": [
            ("game", "/eɪ/"), ("bike", "/aɪ/"), ("fox", "/ɒ/"), ("cup", "/ʌ/")]},
    ],
    7: [
        {"name": "Unit 7 的帮助行为", "note": "帮助类短语", "items": [
            ("help the old", "帮助老人"), ("give a hand", "帮一把"), ("do voluntary work", "做志愿工作"), ("collect money", "募捐")]},
        {"name": "Unit 7 的志愿活动", "note": "志愿活动词汇", "items": [
            ("clean the park", "打扫公园"), ("visit the hospital", "去医院探访"), ("plant trees", "植树"), ("donate books", "捐书")]},
        {"name": "Unit 7 的帮助句型", "note": "帮助句型", "items": [
            ("Can I help you?", "我能帮你吗？"), ("What can we do to help?", "我们能做什么来帮忙？"), ("Let me help you.", "让我帮你。"), ("It is kind of you.", "你真好心。")]},
        {"name": "Unit 7 的语音与语调", "note": "元音读音与请求语调", "words": [
            ("bird", "/ɜː/"), ("chair", "/eə/"), ("soon", "/uː/"), ("rain", "/eɪ/")]},
    ],
    8: [
        {"name": "Unit 8 的常见标识", "note": "标识词汇", "items": [
            ("No smoking", "禁止吸烟"), ("No parking", "禁止停车"), ("Exit", "出口"), ("Wet floor", "小心地滑")]},
        {"name": "Unit 8 的标识含义", "note": "标识含义表达", "items": [
            ("You must not smoke here.", "你不能在这里吸烟。"), ("You can go out here.", "你可以从这里出去。"), ("Be careful, the floor is wet.", "小心，地面很湿。"), ("Do not park your car here.", "不要在这里停车。")]},
        {"name": "Unit 8 的标识问答", "note": "标识问答句型", "items": [
            ("What does this sign mean?", "这个标识是什么意思？"), ("It means no swimming.", "它的意思是禁止游泳。"), ("Where can we see this sign?", "我们在哪里能看到这个标识？"), ("We can see it in the library.", "我们在图书馆能看到。")]},
        {"name": "Unit 8 的语音与语调", "note": "元音读音与提醒语调", "words": [
            ("sit", "/ɪ/"), ("dog", "/ɒ/"), ("nice", "/aɪ/"), ("bag", "/æ/")]},
    ],
    9: [
        {"name": "Unit 9 的再利用动词", "note": "再利用相关动词", "items": [
            ("reuse", "再利用"), ("recycle", "回收"), ("reduce", "减少"), ("save", "节约")]},
        {"name": "Unit 9 的废品名称", "note": "废品词汇", "items": [
            ("plastic bottle", "塑料瓶"), ("old newspaper", "旧报纸"), ("glass jar", "玻璃罐"), ("tin can", "易拉罐")]},
        {"name": "Unit 9 的环保句型", "note": "环保句型", "items": [
            ("We should reuse old boxes.", "我们应该再利用旧盒子。"), ("Do not waste water.", "不要浪费水。"), ("How can we reuse it?", "我们怎样再利用它？"), ("We can make it into a pen holder.", "我们可以把它做成笔筒。")]},
        {"name": "Unit 9 的语音与语调", "note": "元音读音与建议语调", "words": [
            ("tea", "/iː/"), ("house", "/aʊ/"), ("blue", "/uː/"), ("snow", "/əʊ/")]},
    ],
    10: [
        {"name": "Unit 10 的故事书类型", "note": "图书类型词汇", "items": [
            ("storybook", "故事书"), ("fairy tale", "童话"), ("picture book", "图画书"), ("comic book", "漫画书")]},
        {"name": "Unit 10 的阅读感受", "note": "阅读感受表达", "items": [
            ("exciting", "令人兴奋的"), ("funny", "有趣的"), ("sad", "令人难过的"), ("surprising", "令人惊讶的")]},
        {"name": "Unit 10 的分享句型", "note": "分享句型", "items": [
            ("What is the story about?", "这个故事讲什么？"), ("It is about a brave girl.", "它讲一个勇敢的女孩。"), ("I like this book because it is funny.", "我喜欢这本书因为它有趣。"), ("Would you like to read it?", "你想读它吗？")]},
        {"name": "Unit 10 的语音与语调", "note": "元音读音与讲述语调", "words": [
            ("window", "/əʊ/"), ("good", "/ʊ/"), ("how", "/aʊ/"), ("tree", "/iː/")]},
    ],
    11: [
        {"name": "Unit 11 的西方节日", "note": "节日词汇", "items": [
            ("Christmas", "圣诞节"), ("Halloween", "万圣节"), ("Thanksgiving", "感恩节"), ("Easter", "复活节")]},
        {"name": "Unit 11 的节日习俗", "note": "节日习俗短语", "items": [
            ("decorate a tree", "装饰圣诞树"), ("give presents", "送礼物"), ("eat turkey", "吃火鸡"), ("make a pumpkin lantern", "做南瓜灯")]},
        {"name": "Unit 11 的节日时间", "note": "节日时间表达", "items": [
            ("on December 25th", "在十二月二十五日"), ("on October 31st", "在十月三十一日"), ("in November", "在十一月"), ("on the fourth Thursday of November", "在十一月第四个星期四")]},
        {"name": "Unit 11 的语音与语调", "note": "元音读音与祝福语调", "words": [
            ("apple", "/æ/"), ("sweet", "/iː/"), ("light", "/aɪ/"), ("coat", "/əʊ/")]},
    ],
    12: [
        {"name": "Unit 12 的故事人物", "note": "故事人物词汇", "items": [
            ("pea", "豌豆"), ("pod", "豆荚"), ("boy", "男孩"), ("window", "窗户")]},
        {"name": "Unit 12 的情节表达", "note": "情节动作短语", "items": [
            ("fly out of the pod", "从豆荚里飞出"), ("fall on the ground", "落到地上"), ("grow into a plant", "长成一株植物"), ("be eaten by a bird", "被鸟吃掉")]},
        {"name": "Unit 12 的寓意表达", "note": "寓意表达句型", "items": [
            ("What does the story tell us?", "这个故事告诉我们什么？"), ("Everyone can be useful.", "每个人都能有用。"), ("The pea helped the sick girl.", "那颗豌豆帮助了生病的女孩。"), ("Small things can make a big difference.", "小事也能带来大变化。")]},
        {"name": "Unit 12 的语音与语调", "note": "元音读音与讲故事语调", "words": [
            ("star", "/ɑː/"), ("use", "/juː/"), ("pea", "/iː/"), ("kite", "/aɪ/")]},
    ],
}

PACK = {
    "subject": "english", "grade": 6, "version": "牛津深圳版", "semester": "second",
    "chapters": [],
}


def qs_variant_a(items):
    w1, m1 = items[0]
    w2, m2 = items[1]
    w3, m3 = items[2]
    w4, m4 = items[3]
    return [
        ("choice", "「%s」的英文是（ ）。" % m1, [w1, w2, w3, w4], "A", "「%s」对应 %s，其余选项是别的表达。" % (m1, w1), 2),
        ("fill", "写出「%s」的英文：______。" % m2, None, w2, "「%s」的英文写法是 %s。" % (m2, w2), 2),
        ("judge", "「%s」可以表示「%s」。" % (w3, m3), None, "T", "「%s」的意思正是%s。" % (w3, m3), 3),
        ("multiple", "与「%s」意思相同或相近的表达有（ ）。" % m1, [w1, w3, w2, w4], ["A", "B"], "A ✓ 对应%s；B ✓ 对应%s；C ✗ 对应%s；D ✗ 对应%s。所以选 A、B。" % (m1, m3, m2, m4), 3),
        ("answer", "围绕「%s」（%s）写一句英文，并说明中文意思。" % (w1, m1), None, "示例：%s（%s）" % (w1, m1), "评分要点：用到目标表达 + 句子完整 + 中文准确。", 4),
    ]


def qs_variant_b(items):
    w1, m1 = items[0]
    w2, m2 = items[1]
    w3, m3 = items[2]
    w4, m4 = items[3]
    return [
        ("choice", "%s 的意思是（ ）。" % w1, [m1, m2, m3, m4], "A", "%s 的中文意思是%s，其余选项是别的词义。" % (w1, m1), 2),
        ("fill", "%s 的意思是（ ）（写中文）。" % w2, None, m2, "%s 对应中文%s。" % (w2, m2), 2),
        ("judge", "%s 与「%s」是同一个意思。" % (w4, m4), None, "T", "%s 就是%s。" % (w4, m4), 3),
        ("multiple", "下列表达中与 %s 意思不同的有（ ）。" % w2, [w2, w1, w3, w4], ["B", "C", "D"], "A ✗ 与 %s 同义；B ✓ 是%s的意思；C ✓ 是%s的意思；D ✓ 是%s的意思。所以选 B、C、D。" % (w2, m1, m3, m4), 4),
        ("answer", "用 %s 和 %s 各写一句英文。" % (w1, w3), None, "示例：%s / %s" % (w1, w3), "评分要点：两个表达各用一次 + 句子合理。", 4),
    ]


def qs_variant_c(items):
    w1, m1 = items[0]
    w2, m2 = items[1]
    w3, m3 = items[2]
    w4, m4 = items[3]
    return [
        ("choice", "在「%s」这个意思下，正确的英文是（ ）。" % m2, [w2, w1, w3, w4], "A", "表示%s用 %s。" % (m2, w2), 3),
        ("fill", "把短语补充完整：%s（写英文）。" % m3, None, w3, "「%s」的英文形式是 %s。" % (m3, w3), 3),
        ("judge", "拼写 %s 是正确的英文表达。" % w1, None, "T", "%s 拼写与用法都正确。" % w1, 3),
        ("multiple", "下面关于「%s」的一组搭配中，英文与中文对应正确的有（ ）。" % m1, ["%s —— %s" % (w1, m1), "%s —— %s" % (w2, m2), "%s —— %s" % (w3, m4), "%s —— %s" % (w4, m3)], ["A", "B"], "A ✓ %s 确实是%s；B ✓ %s 确实是%s；C ✗ %s 应为%s；D ✗ %s 应为%s。所以选 A、B。" % (w1, m1, w2, m2, w3, m3, w4, m4), 4),
        ("answer", "结合本单元情景，用「%s」（%s）和「%s」（%s）写两句对话。" % (w1, m1, w4, m4), None, "示例：A: %s B: %s" % (w1, w4), "评分要点：对话自然 + 两词都用上 + 语境合理。", 4),
    ]


def qs_phon(words, note):
    """语音知识点专用题型：单词 → 音标。"""
    w1, s1 = words[0]
    w2, s2 = words[1]
    w3, s3 = words[2]
    w4, s4 = words[3]
    return [
        ("choice", "单词 %s 中划线部分的读音是（ ）。" % w1, [s1, s2, s3, s4], "A", "%s 中该部分读 %s，与选项 A 一致。" % (w1, s1), 2),
        ("fill", "单词 %s 的音标是（ ）。" % w2, None, s2, "%s 的音标写作 %s。" % (w2, s2), 3),
        ("judge", "单词 %s 中含有读音 %s。" % (w3, s3), None, "T", "%s 的读音确实是 %s。" % (w3, s3), 3),
        ("multiple", "下面关于单词 %s 的一组音标配对中，正确的有（ ）。" % w1, ["%s —— %s" % (w1, s1), "%s —— %s" % (w2, s2), "%s —— %s" % (w3, s4), "%s —— %s" % (w4, s3)], ["A", "B"], "A ✓ %s 读%s；B ✓ %s 读%s；C ✗ %s 应读%s；D ✗ %s 应读%s。所以选 A、B。" % (w1, s1, w2, s2, w3, s3, w4, s4), 4),
        ("answer", "写出 %s 和 %s 的音标，并说明 %s 这一读音的发音特点。" % (w1, w4, s1), None, "示例：%s 读 %s，%s 读 %s。%s 发音时口型较小、声音短促。" % (w1, s1, w4, s4, s1), "评分要点：两个音标正确 + 发音特点说明。", 5),
    ]


BUILDERS = [qs_variant_a, qs_variant_b, qs_variant_c]

for idx, (title, summary) in enumerate(UNITS, start=1):
    pts = []
    for p_idx, pt in enumerate(DATA[idx]):
        if "words" in pt:
            qs = qs_phon(pt["words"], pt["note"])
        else:
            qs = BUILDERS[p_idx % 3](pt["items"])
        pts.append({
            "name": pt["name"],
            "explanation": "本知识点为%s，要求能听懂、会读并在句子中正确使用。" % pt["note"],
            "questions": qs,
        })
    PACK["chapters"].append({"name": title, "summary": summary, "points": pts})
