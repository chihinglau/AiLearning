"""自建题型题库：g1 英语听力（listening）+ 英语书面表达（composition）。

背景：题库原本只有 choice/fill/answer/judge/multiple，缺 STRICT_Q_TYPES 中的
listening / composition，导致 27 条英语蓝图全部被拒。
本脚本按教材章节主题原创生成听力题（脚本 + 选项 + 答案 + 解析），
并补英语书面表达题（题干 + 评分点 + 参考范文）。

用法：
    python scripts/seed_language_question_bank.py --dry-run
    python scripts/seed_language_question_bank.py --apply
"""

from __future__ import annotations

import argparse

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.content import Chapter, Question, Textbook

# ---------------------------------------------------------------- 上册（教材 5）
BOOK_FIRST: dict[int, dict] = {
    219: {
        "topic": "家庭成员",
        "topic_zh": "家人与家庭",
        "words": [
            ("father", "爸爸"), ("mother", "妈妈"), ("brother", "哥哥/弟弟"),
            ("sister", "姐姐/妹妹"), ("family", "家庭"), ("grandpa", "爷爷"),
            ("grandma", "奶奶"), ("baby", "婴儿"),
        ],
        "sentences": [
            ("This is my father.", "father"),
            ("This is my mother.", "mother"),
            ("I have a big family.", "family"),
            ("My brother is five.", "brother"),
            ("She is my sister.", "sister"),
            ("This is my grandma.", "grandma"),
        ],
        "qa": [
            ("Who is this?", "This is my mother.", "这是我的妈妈。"),
            ("Do you have a brother?", "Yes, I have one brother.", "是的，我有一个弟弟。"),
            ("How many people are in your family?", "There are five people in my family.", "我家有五口人。"),
        ],
    },
    220: {
        "topic": "问候与心情",
        "topic_zh": "问候与心情",
        "words": [
            ("hello", "你好"), ("morning", "早上"), ("happy", "开心的"),
            ("sad", "难过的"), ("fine", "好的"), ("tired", "累的"),
            ("today", "今天"), ("thanks", "谢谢"),
        ],
        "sentences": [
            ("Good morning, Miss Li.", "morning"),
            ("How are you today?", "today"),
            ("I am happy today.", "happy"),
            ("I am fine, thank you.", "fine"),
            ("He is a little sad.", "sad"),
            ("Goodbye, see you tomorrow.", "goodbye"),
        ],
        "qa": [
            ("How are you today?", "I am fine, thank you.", "我今天很好，谢谢。"),
            ("Good morning!", "Good morning, Miss Li!", "早上好，李老师！"),
            ("Are you happy?", "Yes, I am very happy.", "是的，我很开心。"),
        ],
    },
    221: {
        "topic": "学习用品",
        "topic_zh": "上学带的东西",
        "words": [
            ("pencil", "铅笔"), ("ruler", "尺子"), ("bag", "书包"),
            ("book", "书"), ("eraser", "橡皮"), ("pen", "钢笔"),
            ("case", "笔袋"), ("crayon", "蜡笔"),
        ],
        "sentences": [
            ("I take a pencil to school.", "pencil"),
            ("This is my new bag.", "bag"),
            ("I have a long ruler.", "ruler"),
            ("Where is my eraser?", "eraser"),
            ("I take three books to school.", "books"),
            ("My pen is blue.", "pen"),
        ],
        "qa": [
            ("What do you take to school?", "I take a pencil and a book.", "我带了一支铅笔和一本书。"),
            ("Is this your bag?", "Yes, it is my bag.", "是的，这是我的书包。"),
            ("How many rulers do you have?", "I have two rulers.", "我有两把尺子。"),
        ],
    },
    222: {
        "topic": "会做的事情",
        "topic_zh": "会做的事",
        "words": [
            ("sing", "唱歌"), ("dance", "跳舞"), ("draw", "画画"),
            ("swim", "游泳"), ("run", "跑"), ("jump", "跳"),
            ("read", "读书"), ("write", "写字"),
        ],
        "sentences": [
            ("I can sing a song.", "sing"),
            ("I can draw a cat.", "draw"),
            ("Can you swim?", "swim"),
            ("She can dance very well.", "dance"),
            ("I can jump ten times.", "jump"),
            ("He can run fast.", "run"),
        ],
        "qa": [
            ("What can you do?", "I can sing and dance.", "我会唱歌和跳舞。"),
            ("Can you swim?", "No, I can't. But I can run.", "不，我不会。但我会跑。"),
            ("Can your sister draw?", "Yes, she can draw a bird.", "会，她会画小鸟。"),
        ],
    },
    223: {
        "topic": "动物",
        "topic_zh": "喜欢的动物",
        "words": [
            ("cat", "猫"), ("dog", "狗"), ("rabbit", "兔子"),
            ("panda", "熊猫"), ("tiger", "老虎"), ("bird", "鸟"),
            ("small", "小的"), ("big", "大的"),
        ],
        "sentences": [
            ("My favourite animal is the panda.", "panda"),
            ("The rabbit is small and white.", "rabbit"),
            ("I have a black cat.", "cat"),
            ("The tiger is very big.", "tiger"),
            ("A bird can fly.", "bird"),
            ("The dog is my good friend.", "dog"),
        ],
        "qa": [
            ("What is your favourite animal?", "My favourite animal is the cat.", "我最喜欢的动物是猫。"),
            ("Is the rabbit big?", "No, it is small.", "不，它很小。"),
            ("Can a bird fly?", "Yes, it can fly.", "是的，它会飞。"),
        ],
    },
    224: {
        "topic": "颜色",
        "topic_zh": "看到的颜色",
        "words": [
            ("red", "红色"), ("blue", "蓝色"), ("yellow", "黄色"),
            ("green", "绿色"), ("black", "黑色"), ("white", "白色"),
            ("orange", "橙色"), ("pink", "粉色"),
        ],
        "sentences": [
            ("The apple is red.", "red"),
            ("I can see a blue bird.", "blue"),
            ("My bag is yellow.", "yellow"),
            ("The tree is green.", "green"),
            ("Her cat is black and white.", "white"),
            ("What colour is your pen?", "colour"),
        ],
        "qa": [
            ("What colour is your bag?", "It is yellow.", "它是黄色的。"),
            ("What colours can you see?", "I can see red and green.", "我能看到红色和绿色。"),
            ("Is the apple green?", "No, it is red.", "不，它是红色的。"),
        ],
    },
}

# ---------------------------------------------------------------- 下册（教材 6）
BOOK_SECOND: dict[int, dict] = {
    513: {
        "topic": "看见的事物",
        "topic_zh": "看到的东西",
        "words": [
            ("see", "看见"), ("look", "看"), ("tree", "树"),
            ("flower", "花"), ("kite", "风筝"), ("cloud", "云"),
            ("sky", "天空"), ("bird", "鸟"),
        ],
        "sentences": [
            ("Look at the tree.", "tree"),
            ("I can see a kite in the sky.", "kite"),
            ("Look at the beautiful flower.", "flower"),
            ("I can see a bird in the tree.", "bird"),
            ("Look at the white cloud.", "cloud"),
            ("See the blue sky.", "sky"),
        ],
        "qa": [
            ("What can you see?", "I can see a kite.", "我能看到一只风筝。"),
            ("Look at the flower. What colour is it?", "It is red.", "它是红色的。"),
            ("Can you see the bird?", "Yes, I can see it in the tree.", "能看到，它在树上。"),
        ],
    },
    514: {
        "topic": "听到的声音",
        "topic_zh": "听到的声音",
        "words": [
            ("listen", "听"), ("hear", "听见"), ("bell", "铃声"),
            ("car", "汽车"), ("drum", "鼓"), ("song", "歌曲"),
            ("loud", "响亮的"), ("quiet", "安静的"),
        ],
        "sentences": [
            ("Listen to the bell.", "bell"),
            ("I can hear a car.", "car"),
            ("The drum is very loud.", "drum"),
            ("Listen and hear the song.", "song"),
            ("The classroom is quiet.", "quiet"),
            ("Can you hear me?", "hear"),
        ],
        "qa": [
            ("What can you hear?", "I can hear a bell.", "我能听到铃声。"),
            ("Is the drum loud?", "Yes, it is very loud.", "是的，它很响。"),
            ("Listen! What is it?", "It is a car.", "是一辆汽车。"),
        ],
    },
    515: {
        "topic": "味道与气味",
        "topic_zh": "尝到和闻到的",
        "words": [
            ("taste", "尝"), ("smell", "闻"), ("sweet", "甜的"),
            ("sour", "酸的"), ("nice", "好闻的"), ("apple", "苹果"),
            ("cake", "蛋糕"), ("lemon", "柠檬"),
        ],
        "sentences": [
            ("The cake tastes sweet.", "sweet"),
            ("The lemon is sour.", "sour"),
            ("Smell the flowers. They are nice.", "nice"),
            ("Taste the apple.", "apple"),
            ("I can smell a cake.", "smell"),
            ("The soup tastes good.", "taste"),
        ],
        "qa": [
            ("How does the cake taste?", "It tastes sweet.", "它尝起来是甜的。"),
            ("Smell the lemon. Is it nice?", "No, it is sour.", "不，它是酸的。"),
            ("What can you smell?", "I can smell a cake.", "我能闻到蛋糕的味道。"),
        ],
    },
    516: {
        "topic": "玩具",
        "topic_zh": "喜欢的玩具",
        "words": [
            ("toy", "玩具"), ("ball", "球"), ("doll", "洋娃娃"),
            ("car", "小汽车"), ("robot", "机器人"), ("bear", "小熊"),
            ("play", "玩"), ("like", "喜欢"),
        ],
        "sentences": [
            ("I like my new toy.", "toy"),
            ("This is a red ball.", "ball"),
            ("My doll has long hair.", "doll"),
            ("I play with my robot.", "robot"),
            ("The toy car is small.", "car"),
            ("I like the brown bear.", "bear"),
        ],
        "qa": [
            ("What toy do you like?", "I like the toy car.", "我喜欢小汽车玩具。"),
            ("Is this your doll?", "Yes, it is my doll.", "是的，这是我的洋娃娃。"),
            ("Can we play with the ball?", "OK, let's play.", "好的，我们一起玩。"),
        ],
    },
    517: {
        "topic": "食物",
        "topic_zh": "喜欢的食物",
        "words": [
            ("rice", "米饭"), ("noodles", "面条"), ("egg", "鸡蛋"),
            ("fish", "鱼"), ("meat", "肉"), ("soup", "汤"),
            ("breakfast", "早饭"), ("hungry", "饿的"),
        ],
        "sentences": [
            ("I like noodles.", "noodles"),
            ("I have an egg for breakfast.", "egg"),
            ("The fish is fresh.", "fish"),
            ("I am hungry now.", "hungry"),
            ("Mum makes soup.", "soup"),
            ("I eat rice at noon.", "rice"),
        ],
        "qa": [
            ("What do you like?", "I like noodles and eggs.", "我喜欢面条和鸡蛋。"),
            ("Are you hungry?", "Yes, I am very hungry.", "是的，我很饿。"),
            ("What do you have for breakfast?", "I have an egg and some milk.", "我吃一个鸡蛋，喝一些牛奶。"),
        ],
    },
    518: {
        "topic": "饮料",
        "topic_zh": "喜欢的饮料",
        "words": [
            ("milk", "牛奶"), ("water", "水"), ("juice", "果汁"),
            ("tea", "茶"), ("coffee", "咖啡"), ("cup", "杯子"),
            ("drink", "喝"), ("thirsty", "渴的"),
        ],
        "sentences": [
            ("I drink milk every morning.", "milk"),
            ("Can I have some water?", "water"),
            ("The orange juice is sweet.", "juice"),
            ("Grandpa likes tea.", "tea"),
            ("I am thirsty.", "thirsty"),
            ("This cup is for you.", "cup"),
        ],
        "qa": [
            ("What do you want to drink?", "I want some water.", "我想喝点水。"),
            ("Do you like juice?", "Yes, I like orange juice.", "是的，我喜欢橙汁。"),
            ("Are you thirsty?", "Yes, I am thirsty.", "是的，我渴了。"),
        ],
    },
    519: {
        "topic": "季节",
        "topic_zh": "四季与活动",
        "words": [
            ("spring", "春天"), ("summer", "夏天"), ("autumn", "秋天"),
            ("winter", "冬天"), ("hot", "热的"), ("cold", "冷的"),
            ("season", "季节"), ("swim", "游泳"),
        ],
        "sentences": [
            ("Spring is warm and green.", "spring"),
            ("In summer it is very hot.", "summer"),
            ("Autumn is my favourite season.", "autumn"),
            ("In winter we make a snowman.", "winter"),
            ("I swim in summer.", "swim"),
            ("It is cold today.", "cold"),
        ],
        "qa": [
            ("Which season do you like?", "I like autumn.", "我喜欢秋天。"),
            ("What do you do in summer?", "I swim in the river.", "我在河里游泳。"),
            ("Is it hot in winter?", "No, it is cold.", "不，很冷。"),
        ],
    },
    520: {
        "topic": "天气",
        "topic_zh": "天气",
        "words": [
            ("sunny", "晴朗的"), ("rainy", "下雨的"), ("windy", "有风的"),
            ("cloudy", "多云的"), ("weather", "天气"), ("rain", "雨"),
            ("wind", "风"), ("umbrella", "雨伞"),
        ],
        "sentences": [
            ("It is sunny today.", "sunny"),
            ("Take an umbrella. It is rainy.", "umbrella"),
            ("It is windy outside.", "windy"),
            ("The weather is nice.", "weather"),
            ("I can see a cloudy sky.", "cloudy"),
            ("The wind is strong.", "wind"),
        ],
        "qa": [
            ("How is the weather today?", "It is sunny.", "今天是晴天。"),
            ("Is it rainy?", "Yes, take your umbrella.", "是的，带上你的雨伞。"),
            ("Can we go out in the wind?", "No, the wind is too strong.", "不行，风太大了。"),
        ],
    },
    521: {
        "topic": "衣物",
        "topic_zh": "衣服与穿着",
        "words": [
            ("shirt", "衬衫"), ("coat", "外套"), ("dress", "连衣裙"),
            ("shoes", "鞋子"), ("socks", "袜子"), ("hat", "帽子"),
            ("wear", "穿"), ("new", "新的"),
        ],
        "sentences": [
            ("I wear a white shirt.", "shirt"),
            ("Put on your coat. It is cold.", "coat"),
            ("Her dress is pink.", "dress"),
            ("My shoes are new.", "shoes"),
            ("Where are my socks?", "socks"),
            ("He wears a blue hat.", "hat"),
        ],
        "qa": [
            ("What are you wearing?", "I am wearing a shirt and shoes.", "我穿着衬衫和鞋子。"),
            ("Is your coat new?", "Yes, it is new.", "是的，它是新的。"),
            ("Where is my hat?", "It is on the bed.", "它在床上。"),
        ],
    },
    522: {
        "topic": "日常活动",
        "topic_zh": "日常活动",
        "words": [
            ("run", "跑步"), ("read", "读书"), ("write", "写字"),
            ("play", "玩"), ("help", "帮忙"), ("morning", "早上"),
            ("evening", "晚上"), ("home", "家"),
        ],
        "sentences": [
            ("I run in the morning.", "run"),
            ("I read a book at home.", "read"),
            ("I help my mother at home.", "help"),
            ("We play football in the evening.", "evening"),
            ("I write my name.", "write"),
            ("I go home after school.", "home"),
        ],
        "qa": [
            ("What do you do in the morning?", "I run and read.", "我跑步和读书。"),
            ("Do you help your mother?", "Yes, I help her at home.", "是的，我在家帮她。"),
            ("What do you do in the evening?", "I play with my sister.", "我和妹妹一起玩。"),
        ],
    },
    523: {
        "topic": "新年",
        "topic_zh": "新年与祝福",
        "words": [
            ("new year", "新年"), ("happy", "快乐的"), ("gift", "礼物"),
            ("card", "贺卡"), ("party", "聚会"), ("family", "家人"),
            ("wish", "祝愿"), ("red", "红色的"),
        ],
        "sentences": [
            ("Happy New Year!", "new year"),
            ("I make a card for my mother.", "card"),
            ("We have a family party.", "party"),
            ("This gift is for you.", "gift"),
            ("I wish you a happy new year.", "wish"),
            ("The red packet is nice.", "red"),
        ],
        "qa": [
            ("Happy New Year!", "Happy New Year to you too!", "也祝你新年快乐！"),
            ("What do you do on New Year's Day?", "We have a party and eat together.", "我们聚会、一起吃饭。"),
            ("Is this gift for me?", "Yes, it is for you.", "是的，是给你的。"),
        ],
    },
    524: {
        "topic": "故事阅读",
        "topic_zh": "男孩与狼的故事",
        "words": [
            ("boy", "男孩"), ("wolf", "狼"), ("sheep", "羊"),
            ("run", "跑"), ("shout", "喊"), ("help", "帮助"),
            ("true", "真的"), ("lie", "谎言"),
        ],
        "sentences": [
            ("The boy looks after the sheep.", "sheep"),
            ("A wolf comes to the hill.", "wolf"),
            ("The boy shouts for help.", "shout"),
            ("The farmers run to the hill.", "run"),
            ("This time the wolf is not there.", "wolf"),
            ("We should not tell a lie.", "lie"),
        ],
        "qa": [
            ("Who looks after the sheep?", "A boy looks after the sheep.", "一个男孩照看羊群。"),
            ("Why do the farmers run to the hill?", "Because the boy shouts for help.", "因为男孩喊救命。"),
            ("What do we learn from the story?", "We should not tell a lie.", "我们不应该说谎。"),
        ],
    },
}

SITUATIONS: dict[int, str] = {
    219: "你想向同学介绍站在身边的妈妈",
    220: "早上在校门口遇到李老师",
    221: "你正在收拾书包，准备上学",
    222: "同学问你放学后会不会游泳",
    223: "你在动物园看到一只很小很白的动物",
    224: "同学问你手里的苹果是什么颜色",
    513: "你和同学在公园里抬头看天空",
    514: "教室里忽然响起清脆的声音",
    515: "你尝了一口妈妈刚做好的蛋糕",
    516: "你在玩具箱里找最喜欢的那件玩具",
    517: "午饭时你想告诉妈妈你喜欢吃什么",
    518: "你刚运动完，觉得很渴",
    519: "同学问你现在是什么季节、你最喜欢哪个季节",
    520: "出门前你想知道今天要不要带伞",
    521: "天冷了，妈妈让你出门前多穿一件",
    522: "老师问你在家会帮妈妈做什么",
    523: "新年第一天，你见到邻居阿姨",
    524: "你在读《男孩与狼》的故事，想说说故事的道理",
}

EN_COMPOSITION: dict[int, list[dict]] = {
    5: [
        {
            "title": "My family",
            "prompt": "请用 3—5 句话介绍你的家庭：家里有几个人、他们分别是谁、你最喜欢和谁一起做什么。",
            "points": [
                "用 This is my… / I have… 介绍至少 3 位家人（6 分）",
                "写出 1 件和家人一起做的事（6 分）",
                "语句通顺、单词拼写正确、书写规范（6 分）",
            ],
            "sample": "This is my family. This is my father and this is my mother. "
                      "I have a little brother. I play with my brother after school. I love my family.",
        },
        {
            "title": "My school things",
            "prompt": "请用 3—5 句话写一写你上学带的物品：带了几样、它们是什么颜色。",
            "points": [
                "用 I take… 写出至少 3 样学习用品（6 分）",
                "用颜色词描述其中 2 样物品（6 分）",
                "句式完整、拼写与标点正确（6 分）",
            ],
            "sample": "I take a pencil and two books to school. My pencil is yellow. "
                      "My bag is blue. I like my school things.",
        },
    ],
    6: [
        {
            "title": "My favourite animal",
            "prompt": "请用 3—5 句话写你最喜欢的动物：它是什么、大小和颜色、你会和它做什么。",
            "points": [
                "写出动物名称并说明是最喜欢的（6 分）",
                "用 1—2 个形容词描述大小或颜色（6 分）",
                "写出与它相处的一件事，语句通顺（6 分）",
            ],
            "sample": "My favourite animal is the rabbit. It is small and white. "
                      "It has long ears. I play with my rabbit every day.",
        },
        {
            "title": "The weather today",
            "prompt": "请用 3—5 句话写今天的天气：天气怎么样、你穿了什么、你做了什么。",
            "points": [
                "用 1 个天气词说明天气（6 分）",
                "写出穿着或携带的物品（6 分）",
                "写出当天做的一件事，语句通顺（6 分）",
            ],
            "sample": "It is sunny today. I wear a white shirt and blue shoes. "
                      "I play football with my friends. I am happy today.",
        },
    ],
}

SOURCE_NAME = "自建题型题库（原创）"
LICENSE_NOTE = "原创自建内容，不含第三方版权素材"


def _pick_distractors(pool: list[str], correct: str, count: int, start: int) -> list[str]:
    others = [item for item in pool if item != correct]
    offset = start % max(1, len(others))
    rotated = others[offset:] + others[:offset]
    return rotated[:count]


def _choice(correct: str, distractors: list[str], start: int) -> tuple[list[dict], dict]:
    texts = [correct] + distractors
    pivot = start % len(texts)
    texts = texts[pivot:] + texts[:pivot]
    keys = "ABCD"
    options = [{"key": keys[i], "text": text} for i, text in enumerate(texts)]
    return options, {"value": keys[texts.index(correct)]}


def _extra_objective_items(seed: dict, situation: str) -> list[dict]:
    """补充客观题：句型填空（fill，medium）+ 情景选择（choice，hard）。

    英语单元卷的「词汇填空」需 8 题、「阅读理解」需 4 道高区分题，
    原题库每章只有 2~3 道，故按本章句表派生补充。
    """
    items: list[dict] = []
    words = [word for word, _ in seed["words"]]
    for sentence, key in seed["sentences"][:2]:
        blanked = sentence.replace(key, "____", 1) if key in sentence else sentence
        items.append({
            "q_type": "fill",
            "stem": f"根据句意补全句子：{blanked}",
            "answer": {"value": key},
            "options": None,
            "analysis": f"原句为 “{sentence}”，空格处填 {key}。",
            "difficulty": 3,
        })

    sentences = [sentence for sentence, _ in seed["sentences"]]
    for index, correct in enumerate(sentences[1:3]):
        others = [s for s in sentences if s != correct]
        options, answer = _choice(correct, _pick_distractors(others, correct, 3, index), index)
        items.append({
            "q_type": "choice",
            "stem": f"根据情景选择最合适的句子：{situation}",
            "answer": answer,
            "options": options,
            "analysis": f"该情景最贴切的表达是 “{correct}”。",
            "difficulty": 5,
        })
    return items


def _reading_items(seed: dict) -> list[dict]:
    """按本章句表拼两段小短文，每段 2 题（阅读理解，medium 难度）。"""
    sentences = [sentence for sentence, _ in seed["sentences"]]
    words = [word for word, _ in seed["words"]]
    gloss = dict(seed["words"])
    passages = [sentences[0:3], sentences[3:6]]
    topic_pool = [item["topic_zh"] for item in list(BOOK_FIRST.values()) + list(BOOK_SECOND.values())]
    items: list[dict] = []
    for index, passage in enumerate(passages):
        text = " ".join(passage)
        topic_zh = seed["topic_zh"]
        options, answer = _choice(topic_zh, _pick_distractors(topic_pool, topic_zh, 3, index), index)
        items.append({
            "q_type": "choice",
            "stem": f"阅读短文，选择短文主要谈论的内容。\n短文：{text}",
            "answer": answer,
            "options": options,
            "analysis": f"短文围绕「{topic_zh}」展开。",
            "difficulty": 4,
        })
        correct_word = next(
            (word for word in words if word in text), words[0]
        )
        other_zh = [text_zh for word, text_zh in seed["words"] if word != correct_word]
        options, answer = _choice(
            gloss.get(correct_word, correct_word),
            _pick_distractors(other_zh, gloss.get(correct_word, correct_word), 3, index + 1),
            index + 1,
        )
        items.append({
            "q_type": "choice",
            "stem": f"阅读短文，选出短文中出现内容的中文意思。\n短文：{text}",
            "answer": answer,
            "options": options,
            "analysis": f"短文中出现 {correct_word}，意思是「{gloss.get(correct_word, correct_word)}」。",
            "difficulty": 4,
        })
    return items


def _listening_items(seed: dict, chapter_name: str) -> list[dict]:
    words = [word for word, _ in seed["words"]]
    gloss = dict(seed["words"])
    items: list[dict] = []
    idx = 0

    # 1) 听单词选词
    for word, word_zh in seed["words"][:2]:
        options, answer = _choice(word, _pick_distractors(words, word, 3, idx), idx)
        items.append({
            "stem": "听录音，选出你听到的单词。",
            "script": word,
            "answer": answer,
            "options": options,
            "analysis": f"录音朗读的是 {word}（{word_zh}），其余选项为同单元干扰词。",
            "difficulty": 1,
        })
        idx += 1

    # 2) 听句子选关键词
    for sentence, key in seed["sentences"][:2]:
        correct = key if key in gloss else words[0]
        options, answer = _choice(correct, _pick_distractors(words, correct, 3, idx), idx)
        items.append({
            "stem": "听录音，选出句子中出现的单词。",
            "script": sentence,
            "answer": answer,
            "options": options,
            "analysis": f"录音句子为 “{sentence}”，其中含 {correct}。",
            "difficulty": 2,
        })
        idx += 1

    # 3) 听问句选应答
    for question, reply, reply_zh in seed["qa"][:2]:
        others = [item[1] for item in seed["qa"] if item[1] != reply]
        while len(others) < 2:
            others.append(seed["qa"][0][1])
        options, answer = _choice(reply, others[:2], idx)
        items.append({
            "stem": "听录音，选出最合适的应答。",
            "script": question,
            "answer": answer,
            "options": options,
            "analysis": f"问句为 “{question}”，应答 “{reply}”（{reply_zh}）最贴切。",
            "difficulty": 2,
        })
        idx += 1

    # 4) 听对话选话题
    topic_zh = seed["topic_zh"]
    topic_pool = [seed2["topic_zh"] for seed2 in list(BOOK_FIRST.values()) + list(BOOK_SECOND.values())]
    topic_pool = [item for item in topic_pool if item != topic_zh]
    for question, reply, _ in seed["qa"][:2]:
        options, answer = _choice(topic_zh, _pick_distractors(topic_pool, topic_zh, 3, idx), idx)
        items.append({
            "stem": "听对话，选出两人最可能在谈论的内容。",
            "script": f"A: {question} B: {reply}",
            "answer": answer,
            "options": options,
            "analysis": f"对话关键词都落在「{topic_zh}」上。",
            "difficulty": 2,
        })
        idx += 1

    # 5) 听句子选中文意思
    for sentence, key in seed["sentences"][2:4]:
        key_zh = gloss.get(key, "本单元内容")
        other_zh = [text for word, text in seed["words"] if text != key_zh]
        options, answer = _choice(key_zh, _pick_distractors(other_zh, key_zh, 3, idx), idx)
        items.append({
            "stem": "听录音，选出句子中出现内容的中文意思。",
            "script": sentence,
            "answer": answer,
            "options": options,
            "analysis": f"“{sentence}” 中的 {key} 意思是「{key_zh}」。",
            "difficulty": 2,
        })
        idx += 1

    return items


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    plan: list[tuple[int, Question]] = []
    with SessionLocal() as db:
        chapters = {c.id: c for c in db.scalars(select(Chapter).where(Chapter.textbook_id.in_((5, 6))))}
        kp_by_chapter: dict[int, list[int]] = {}
        for chapter_id in chapters:
            kps = list(db.scalars(
                select(Question.knowledge_point_id)
                .where(Question.chapter_id == chapter_id, Question.knowledge_point_id.is_not(None))
                .distinct()
            ))
            kp_by_chapter[chapter_id] = [kp for kp in kps if kp]

        for book_id, seeds in ((5, BOOK_FIRST), (6, BOOK_SECOND)):
            for chapter_id, seed in seeds.items():
                chapter = chapters.get(chapter_id)
                if chapter is None:
                    print(f"[skip] chapter {chapter_id} 不在教材 {book_id}")
                    continue
                kps = kp_by_chapter.get(chapter_id) or [None]
                for index, item in enumerate(_listening_items(seed, chapter.name), start=1):
                    question = Question(
                        chapter_id=chapter_id,
                        # 听力题按章内已有知识点轮转，避免全章同挂一个 KP 被上限卡死
                        knowledge_point_id=kps[(index - 1) % len(kps)],
                        subject="english",
                        q_type="listening",
                        content={
                            "stem": item["stem"],
                            "script": item["script"],
                            "audio_note": "听力材料以教师朗读/后续 TTS 音频为准",
                        },
                        options=item["options"],
                        answer=item["answer"],
                        analysis=item["analysis"],
                        difficulty=item["difficulty"],
                        tags=["listening", "grade1", chapter.name],
                        status="published",
                        source_type="original",
                        source_name=SOURCE_NAME,
                        source_ref=f"selfbank:en_listen:{chapter_id}:{index}",
                        copyright_owner=None,
                        license_note=LICENSE_NOTE,
                    )
                    plan.append((chapter_id, question))

                for index, item in enumerate(
                    _extra_objective_items(seed, SITUATIONS[chapter_id])
                    + _reading_items(seed), start=1
                ):
                    plan.append((chapter_id, Question(
                        chapter_id=chapter_id,
                        knowledge_point_id=kps[(index - 1) % len(kps)],
                        subject="english",
                        q_type=item["q_type"],
                        content={"stem": item["stem"]},
                        options=item["options"],
                        answer=item["answer"],
                        analysis=item["analysis"],
                        difficulty=item["difficulty"],
                        tags=[item["q_type"], "grade1", chapter.name],
                        status="published",
                        source_type="original",
                        source_name=SOURCE_NAME,
                        source_ref=f"selfbank:en_extra:{chapter_id}:{index}",
                        license_note=LICENSE_NOTE,
                    )))

        # 书面表达：挂到该册第一个具名单元章节，保证期中/期末卷可取到
        for book_id, comps in EN_COMPOSITION.items():
            anchor = next(iter(BOOK_FIRST if book_id == 5 else BOOK_SECOND))
            for index, comp in enumerate(comps, start=1):
                plan.append((anchor, Question(
                    chapter_id=anchor,
                    knowledge_point_id=None,
                    subject="english",
                    q_type="composition",
                    content={
                        "stem": comp["prompt"],
                        "title": comp["title"],
                        "min_words": 20,
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
                    source_ref=f"selfbank:en_comp:{book_id}:{index}",
                    license_note=LICENSE_NOTE,
                )))

        listening = sum(1 for _, q in plan if q.q_type == "listening")
        composition = sum(1 for _, q in plan if q.q_type == "composition")
        print(f"计划写入：listening {listening} / composition {composition} / 合计 {len(plan)}")

        if not args.apply:
            for chapter_id, question in plan[:6]:
                print(f"  ch{chapter_id} {question.q_type} script={question.content.get('script')!r} "
                      f"stem={question.content.get('stem')}")
            print("干跑模式：未写库（加 --apply 落库）")
            return 0

        created = skipped = 0
        for chapter_id, question in plan:
            exists = db.scalar(select(Question.id).where(Question.source_ref == question.source_ref))
            if exists:
                skipped += 1
                continue
            db.add(question)
            created += 1
        db.commit()
        print(f"入库完成：created={created} skipped={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
