"""英语按单元数据池：组合式生成，按索引唯一映射，保证跨单元低重复。

单元卷需求：listening 8 / choice 12（单选 8 + 阅读 4）/ fill 8。
池不再手写固定条目，而是给出「维度槽位」，由 index 唯一解码出一组槽值，
池容量达数百至数千，因此按顺序取题时跨单元的题干重复率接近 1。

对外接口（全部按索引取值，不物化，避免导入时爆炸）：
    listening_item(idx) / grammar_item(idx) / fill_item(idx) / reading_passage(idx, band)
"""

from __future__ import annotations

import string

from scripts._slot_decode import decode

SOURCE_NAME = "自建题型题库（原创）"
LICENSE_NOTE = "原创自建内容，不含第三方版权素材"

# ---------------- 听力词群（16 组 × 10 词 = 160 词） ----------------
WORD_GROUPS = {
    "family": ["father", "mother", "brother", "sister", "uncle", "aunt", "cousin",
               "grandpa", "grandma", "parent"],
    "animals": ["cat", "dog", "bird", "fish", "rabbit", "panda", "monkey", "tiger",
                "duck", "horse"],
    "colors": ["red", "blue", "green", "yellow", "black", "white", "brown", "pink",
               "orange", "grey"],
    "food": ["rice", "bread", "milk", "egg", "apple", "banana", "orange", "cake",
             "noodle", "vegetable"],
    "school": ["book", "pen", "pencil", "ruler", "bag", "desk", "chair", "classroom",
               "eraser", "notebook"],
    "body": ["head", "hand", "eye", "ear", "nose", "mouth", "foot", "hair",
             "arm", "finger"],
    "weather": ["sunny", "rainy", "cloudy", "windy", "snowy", "hot", "cold", "warm",
                "cool", "foggy"],
    "numbers": ["one", "two", "three", "four", "five", "six", "seven", "eight",
                "nine", "ten"],
    "clothes": ["shirt", "coat", "dress", "shoe", "sock", "hat", "skirt", "sweater",
                "glove", "scarf"],
    "fruit": ["pear", "peach", "grape", "melon", "lemon", "cherry", "strawberry",
              "pineapple", "mango", "watermelon"],
    "jobs": ["doctor", "teacher", "farmer", "driver", "nurse", "cook", "worker",
             "police", "singer", "painter"],
    "places": ["park", "zoo", "library", "museum", "hospital", "supermarket",
               "cinema", "garden", "station", "playground"],
    "sports": ["football", "basketball", "swimming", "running", "tennis", "skating",
               "jumping", "cycling", "rowing", "climbing"],
    "nature": ["river", "mountain", "tree", "flower", "cloud", "rain", "wind", "lake",
               "field", "forest"],
    "home": ["bed", "sofa", "window", "door", "table", "fridge", "phone", "clock",
             "lamp", "cup"],
    "adjectives": ["happy", "tall", "short", "clean", "busy", "quiet", "brave", "kind",
                   "careful", "polite"],
}
GROUP_NAMES = list(WORD_GROUPS)


LISTEN_STEMS = [
    "听录音，选出你听到的单词。",
    "听录音，从四个单词中选出你听到的那一个。",
    "听一听，选出录音里出现的单词。",
    "听录音，选出与录音内容一致的单词。",
]


# 7-9 上教版（沪教牛津深圳版）每单元 8 个主题词。听力题按单元取词，
# 干扰项也来自同单元词表，避免旧实现「全局通用词池 + 答案永远 A」导致的
# 两处问题：①题目与本单元主题无关（如 Unit 1 Friendship 出 head/hand/eye/ear）；
# ②答案固定 A，学生不听音频也能蒙对。
UNIT_LISTENING_WORDS = {
    # 7A
    "Friendship": ["friend", "friendly", "kind", "helpful", "share", "trust",
                   "together", "classmate"],
    "School life": ["classroom", "teacher", "lesson", "timetable", "subject",
                    "uniform", "library", "homework"],
    "The seasons": ["spring", "summer", "autumn", "winter", "weather", "warm",
                    "cool", "season"],
    "The Earth": ["earth", "ocean", "mountain", "forest", "river", "desert",
                  "island", "planet"],
    "Off to space": ["rocket", "astronaut", "space", "moon", "planet", "star",
                     "launch", "satellite"],
    "Travelling around Asia": ["travel", "country", "city", "temple", "museum",
                               "ticket", "journey", "Asia"],
    "Fun after school": ["hobby", "club", "sport", "music", "painting", "chess",
                         "join", "activity"],
    "Collecting as a hobby": ["collect", "stamp", "coin", "card", "album",
                              "series", "valuable", "hobby"],
    # 7B
    "People around us": ["neighbour", "cousin", "uncle", "aunt", "grandparent",
                         "relative", "polite", "friendly"],
    "Travelling around the world": ["passport", "flight", "hotel", "luggage",
                                    "map", "sightseeing", "abroad", "tourist"],
    "Trees and us": ["tree", "leaf", "branch", "root", "forest", "wood",
                     "plant", "oxygen"],
    "Our animal friends": ["panda", "elephant", "tiger", "monkey", "dolphin",
                           "rabbit", "protect", "wild"],
    "Water": ["water", "river", "lake", "ocean", "rain", "save", "drink",
              "fresh"],
    "Electricity": ["electricity", "light", "battery", "wire", "power",
                    "switch", "safe", "energy"],
    "Poems": ["poem", "poet", "rhyme", "line", "verse", "rhythm", "imagine",
              "feeling"],
    "From hobby to career": ["career", "job", "skill", "practice", "dream",
                             "future", "hobby", "choose"],
    # 8A
    "Look it up!": ["dictionary", "entry", "word", "meaning", "spell",
                    "example", "search", "alphabet"],
    "Amazing numbers": ["number", "zero", "million", "digit", "count", "maths",
                        "total", "half"],
    "Our digital lives": ["computer", "internet", "email", "website", "online",
                          "screen", "password", "digital"],
    "Inventions": ["invention", "inventor", "machine", "telephone", "wheel",
                   "design", "create", "useful"],
    "Going on an exchange trip": ["exchange", "student", "host", "family",
                                  "culture", "language", "visit", "welcome"],
    "Wisdom counts": ["wisdom", "clever", "advice", "decision", "experience",
                      "wise", "learn", "mistake"],
    "The secret of memory": ["memory", "remember", "forget", "mind", "method",
                             "review", "practise", "brain"],
    "Pets and us": ["pet", "dog", "cat", "rabbit", "feed", "care", "cute",
                    "owner"],
    # 8B
    "Helping those in need": ["help", "charity", "volunteer", "donate", "poor",
                              "kind", "support", "community"],
    "Body language": ["smile", "nod", "gesture", "signal", "eye", "hand",
                      "meaning", "express"],
    "Comics and animation": ["comic", "cartoon", "character", "story", "picture",
                             "funny", "hero", "animation"],
    "Arts and heritage": ["art", "museum", "heritage", "painting", "ancient",
                          "culture", "protect", "history"],
    "Saving animals in danger": ["danger", "endangered", "protect", "habitat",
                                 "wildlife", "rescue", "extinct", "environment"],
    "Learning by doing": ["practise", "experiment", "skill", "experience",
                          "learn", "try", "activity", "improve"],
    "Space exploration": ["space", "planet", "rocket", "astronaut", "explore",
                          "universe", "telescope", "mission"],
    "Imagine that!": ["imagine", "dream", "creative", "idea", "future", "magic",
                      "invent", "wonder"],
    # 9A
    "Great people": ["hero", "great", "courage", "leader", "example", "respect",
                     "achieve", "famous"],
    "Great ideas": ["idea", "think", "creative", "solution", "change",
                    "improve", "possible", "clever"],
    "Family traditions": ["tradition", "family", "festival", "custom",
                          "celebrate", "together", "ancestor", "gather"],
    "A better me": ["improve", "habit", "goal", "confident", "healthy",
                    "change", "effort", "progress"],
    "My time, my joy": ["time", "enjoy", "relax", "hobby", "free", "happy",
                        "balance", "moment"],
    "Food and health": ["food", "healthy", "vegetable", "fruit", "diet",
                        "vitamin", "energy", "balance"],
    "Reading Mark Twain": ["novel", "author", "humour", "story", "adventure",
                           "character", "famous", "write"],
    "The power of love": ["love", "care", "kindness", "family", "heart",
                          "warmth", "support", "together"],
}


def unit_topic(name: str) -> str:
    """`Unit 1 Friendship` → `Friendship`；非 Unit 命名原样返回。"""
    parts = (name or "").strip().split(" ", 2)
    if len(parts) >= 3 and parts[0].lower() == "unit":
        return parts[2].strip()
    return (name or "").strip()


def listening_items_for_unit(unit_name: str, count: int = 8) -> list[dict] | None:
    """按单元主题词表生成听力题；单元不在表内返回 None（回退旧通用词池）。

    答案位置按题序在 A/B/C/D 轮转（旧实现恒为 A），干扰项全部取自同单元词表。
    """
    words = UNIT_LISTENING_WORDS.get(unit_topic(unit_name))
    if not words:
        return None
    n = len(words)
    keys = "ABCD"
    items: list[dict] = []
    for i in range(count):
        ti = i % n
        target = words[ti]
        others: list[str] = []
        step = 1
        while len(others) < 3 and step < n * 2:
            cand = words[(ti + step + i) % n]
            if cand != target and cand not in others:
                others.append(cand)
            step += 1
        pos = i % 4
        opts_text = others[:pos] + [target] + others[pos:]
        items.append({
            "content": {"stem": LISTEN_STEMS[i % len(LISTEN_STEMS)],
                        "script": target,
                        "audio_note": "听力材料以教师朗读/后续 TTS 音频为准"},
            "options": [{"key": keys[j], "text": w} for j, w in enumerate(opts_text)],
            "answer": keys[pos],
            "analysis": f"录音念的是 {target}；其余 {others[0]} / {others[1]} / "
                        f"{others[2]} 是本单元其它主题词，注意听关键词。",
            "difficulty": 2,
        })
    return items


def listening_item(idx: int) -> dict:
    """听力：目标词 + 同群 3 个干扰词。索引唯一解码 (组, 词, 干扰起点)。"""
    groups = GROUP_NAMES
    g = groups[idx % len(groups)]
    rest = idx // len(groups)
    words = WORD_GROUPS[g]
    wi = rest % len(words)
    off = (rest // len(words)) % (len(words) - 1)
    target = words[wi]
    others = [words[(wi + off + 1 + k) % len(words)] for k in range(3)]
    keys = "ABCD"
    opts = [{"key": keys[j], "text": w} for j, w in enumerate([target] + others)]
    # 题干按索引轮换 4 种表述，避免全套听力共用同一句模板
    stem = LISTEN_STEMS[idx % len(LISTEN_STEMS)]
    return {
        "content": {"stem": stem, "script": target,
                    "audio_note": "听力材料以教师朗读/后续 TTS 音频为准"},
        "options": opts,
        "answer": "A",
        "analysis": f"录音内容为 {target}（{g} 类词）。",
        "difficulty": 1,
    }


# ---------------- 语法单选（模板 × 主语 × 宾语/地点 槽位） ----------------
SG_SUBJECTS = ["He", "She", "Tom", "Lily", "My father", "My mother", "Jack", "Anna"]
PL_SUBJECTS = ["They", "We", "The children", "My friends", "Tom and Lily", "The students"]
ALL_CLASSES = [("sg", s) for s in SG_SUBJECTS] + [("pl", s) for s in PL_SUBJECTS]

# (模板, 选项, sg 答案, pl 答案, 简析, 槽位)
GRAM_FRAMES = [
    ("{S} ___ to {P} by bus every day.", ["go", "goes", "going", "went"],
     "goes", "go", "一般现在时第三人称单数加 -es。",
     {"P": ["school", "work", "the park", "the library", "the museum", "the gym"]}),
    ("{S} ___ {O} every evening.", ["study", "studies", "studying", "studied"],
     "studies", "study", "第三人称单数 study→studies。",
     {"O": ["English", "maths", "Chinese", "science", "music", "art"]}),
    ("{S} ___ {O} after school.", ["play", "plays", "playing", "played"],
     "plays", "play", "一般现在时第三人称单数加 -s。",
     {"O": ["football", "basketball", "table tennis", "volleyball", "badminton", "baseball"]}),
    ("{S} ___ {O} in the evening.", ["watch", "watches", "watching", "watched"],
     "watches", "watch", "以 ch 结尾的动词加 -es。",
     {"O": ["TV", "a film", "the news", "a match", "a cartoon", "a show"]}),
    ("{S} ___ {O} at seven.", ["have", "has", "having", "had"],
     "has", "have", "第三人称单数 have→has。",
     {"O": ["breakfast", "lunch", "dinner", "a meal", "some bread", "some milk"]}),
    ("{S} ___ in {P}.", ["live", "lives", "living", "lived"],
     "lives", "live", "一般现在时第三人称单数加 -s。",
     {"P": ["Beijing", "Shanghai", "Shenzhen", "a small town", "the city centre", "a village"]}),
    ("{S} ___ very {O} today.", ["am", "is", "are", "be"],
     "is", "are", "be 动词随主语的人称和数变化。",
     {"O": ["happy", "tired", "busy", "excited", "hungry", "ready"]}),
    ("{S} ___ interested in {O}.", ["am", "is", "are", "be"],
     "is", "are", "be interested in 为固定搭配。",
     {"O": ["science", "music", "history", "art", "maths", "geography"]}),
    ("{S} ___ like {O}.", ["doesn't", "don't", "isn't", "aren't"],
     "doesn't", "don't", "第三人称单数否定用 doesn't。",
     {"O": ["apples", "music", "sports", "reading", "sweets", "cartoons"]}),
    ("{S} ___ {O} when the light is red.", ["must", "mustn't", "can", "need"],
     "mustn't", "mustn't", "红灯时禁止通行，用 mustn't。",
     {"O": ["cross the road", "run across the road", "walk across", "cross over",
            "go across the road", "hurry across"]}),
    ("{S} ___ good at {O}.", ["am", "is", "are", "be"],
     "is", "are", "be good at 为固定搭配。",
     {"O": ["English", "drawing", "singing", "maths", "swimming", "cooking"]}),
    ("{S} can ___ {O} very well.", ["dance", "dances", "dancing", "danced"],
     "dance", "dance", "情态动词 can 后接动词原形，不随主语变化。",
     {"O": ["dance", "sing", "draw", "cook", "swim", "skate"]}),
    ("{S} ___ many {O} in the bag.", ["is", "are", "was", "be"],
     "are", "are", "many 修饰可数名词复数，用 are。",
     {"O": ["books", "apples", "pencils", "toys", "oranges", "cakes"]}),
    ("{S} ___ a {O} on the desk.", ["is", "are", "am", "be"],
     "is", "is", "单数名词用 is。",
     {"O": ["book", "pen", "cup", "ruler", "clock", "bag"]}),
    # 补充句式结构（第二轮多样化）：there be / 进行时 / 比较级 / 情态 / 过去时 /
    # 将来时 / 疑问语序 / 名词所有格，避免全套题集中在「主谓单三」一种句式。
    ("There ___ a {O} and two chairs in the {P}.", ["is", "are", "be", "was"],
     "is", "is", "there be 结构遵循就近原则，最近的名词是单数，用 is。",
     {"O": ["desk", "bed", "sofa", "table", "window", "picture",
            "fridge", "cupboard", "clock", "bike"],
      "P": ["room", "classroom", "bedroom", "hall", "office", "library",
            "study", "garden", "kitchen"]}),
    ("There ___ two {O} on the {P}.", ["is", "are", "be", "am"],
     "are", "are", "there be 后接可数名词复数，用 are。",
     {"O": ["books", "pens", "cups", "bags", "rulers", "clocks",
            "pencils", "erasers", "boxes", "toys"],
      "P": ["desk", "table", "bed", "shelf", "floor", "wall",
            "chair", "bench", "sofa"]}),
    ("{S} ___ {O} now.", ["is reading", "are reading", "reads", "read"],
     "is reading", "are reading", "now 提示现在进行时，结构为 be + 现在分词。",
     {"O": ["a book", "a newspaper", "a story", "the news", "a magazine", "a letter"]}),
    ("{S} ___ than my {O}.", ["tall", "is taller", "are taller", "taller"],
     "is taller", "are taller", "than 提示比较级，且需保留 be 动词。",
     {"O": ["brother", "sister", "cousin", "deskmate", "neighbour", "friend"]}),
    ("___ {S} {O} very well?", ["Can", "Does", "Is", "Are"],
     "Can", "Can", "情态动词 can 提前构成疑问句，后接动词原形。",
     {"O": ["swim", "sing", "dance", "draw", "cook", "skate"]}),
    ("{S} ___ {O} yesterday.", ["go", "goes", "went", "going"],
     "went", "went", "yesterday 提示一般过去时，动词用过去式且不随主语变化。",
     {"O": ["to school", "home", "to the park", "to the zoo", "to the shop", "to the library"]}),
    ("{S} ___ {O} next Sunday.", ["visit", "visits", "will visit", "visited"],
     "will visit", "will visit", "next Sunday 提示一般将来时，用 will + 动词原形。",
     {"O": ["the museum", "the zoo", "the farm", "the park", "grandma", "the library"]}),
    ("This is my {O}. It is {P}.", ["sister", "sister's", "sisters", "sister is"],
     "sister's", "sister's", "表示「我姐姐的某物」要用名词所有格 sister's。",
     {"O": ["book", "bag", "pen", "desk", "bike", "umbrella",
            "ruler", "pencil", "coat", "hat"],
      "P": ["new", "old", "red", "big", "small", "clean",
            "heavy", "light", "dirty"]}),
]


def _frame_dims(frame) -> list:
    slots = frame[5]
    return [ALL_CLASSES] + [slots[k] for k in slots]


GRAM_POOL_SIZE = sum(len(_frame_dims(f)[0]) * 1 for f in GRAM_FRAMES for _ in [0])


def grammar_item(idx: int) -> dict:
    """按全局序号取题（旧接口，等价于按模板轮转）。"""
    return grammar_item_at(idx % len(GRAM_FRAMES), idx // len(GRAM_FRAMES))


def grammar_item_at(tpl_index: int, slot_pos: int) -> dict:
    """指定模板 + 模板内槽位序号构造单选题。

    与 idx%模板数 的旧映射相比，模板内槽位用独立游标递增，
    同一模板的 14×槽位 组合不会被重复取用，跨章题干不再撞车。
    """
    f = GRAM_FRAMES[tpl_index % len(GRAM_FRAMES)]
    tpl, opts, ans_sg, ans_pl, note, slots = f
    keys = list(slots)
    # 模板串不含 {S} 时，主语维度只取一项，否则 14 个主语会解出 14 份同一题干
    subjects = ALL_CLASSES if "{S}" in tpl else ALL_CLASSES[:1]
    dims = [subjects] + [slots[k] for k in keys]
    decoded = decode(slot_pos, dims)
    cls, subj = decoded[0]
    vals = decoded[1:]
    sentence = tpl.format(S=subj, **dict(zip(keys, vals)))
    keys_abcd = string.ascii_uppercase
    return {
        "content": {"stem": sentence},
        "options": [{"key": keys_abcd[j], "text": o} for j, o in enumerate(opts)],
        "answer": ans_sg if cls == "sg" else ans_pl,
        "analysis": note,
        "difficulty": 2,
    }


# ---------------- 词汇填空（模板 × 主语 × 宾语 槽位） ----------------
FILL_FRAMES = [
    ("{S} ___ (有) a new {O}.", "有", "has", "have",
     {"O": ["bike", "bag", "dog", "book", "watch", "phone", "computer", "kite"]}),
    ("{S} ___ (去) to {P} after school.", "去", "goes", "go",
     {"P": ["the park", "the library", "the zoo", "the museum", "the gym", "the playground"]}),
    ("{S} ___ (喜欢) {O}.", "喜欢", "likes", "like",
     {"O": ["music", "reading", "drawing", "football", "cooking", "singing"]}),
    ("{S} ___ (吃) {O} at twelve.", "吃", "eats", "eat",
     {"O": ["lunch", "breakfast", "dinner", "rice", "noodles", "bread"]}),
    ("{S} can ___ (看见) a {O} in the tree.", "看见", "see", "see",
     {"O": ["bird", "kite", "cat", "monkey", "ball", "bag"]}),
    ("{S} ___ (骑) a {O} to school.", "骑", "rides", "ride",
     {"O": ["bike", "horse", "motorbike", "bicycle", "scooter", "tandem"]}),
    ("{S} ___ (打开) the {O} for me.", "打开", "opens", "open",
     {"O": ["window", "door", "book", "box", "bag", "bottle"]}),
    ("{S} ___ (教) us {O}.", "教", "teaches", "teach",
     {"O": ["English", "maths", "music", "art", "PE", "science"]}),
    ("{S} ___ (学习) {O} every day.", "学习", "studies", "study",
     {"O": ["English", "maths", "Chinese", "science", "music", "art"]}),
    ("{S} ___ (帮助) {O}.", "帮助", "helps", "help",
     {"O": ["his friends", "her classmates", "the old man", "his mother", "her sister", "the teacher"]}),
    ("{S} usually ___ (步行) {O}.", "步行", "walks", "walk",
     {"O": ["to school", "home", "to the park", "to the bus stop", "to the shop", "to the library"]}),
    ("{S} ___ (打扫) the {O} on Friday.", "打扫", "cleans", "clean",
     {"O": ["classroom", "bedroom", "kitchen", "garden", "window", "floor"]}),
    ("{S} ___ (需要) some {O}.", "需要", "needs", "need",
     {"O": ["water", "paper", "help", "time", "milk", "bread"]}),
    ("{S} ___ (买) a present for {O}.", "买", "buys", "buy",
     {"O": ["his mother", "her father", "his sister", "her friend", "the teacher", "his grandpa"]}),
    ("{S} ___ (听) to the {O} carefully.", "听", "listens", "listen",
     {"O": ["teacher", "story", "radio", "music", "song", "advice"]}),
    ("{S} ___ (画) a {O} in the notebook.", "画", "draws", "draw",
     {"O": ["picture", "cat", "tree", "house", "flower", "map"]}),
    # 第二轮补充：动词短语型填空，覆盖「帮助/想要/找到/等待/穿戴/演唱」等常用动词，
    # 让填空不只停留在 be 动词与单三变化。
    ("{S} ___ (帮助) the old {O} cross the road.", "帮助", "helps", "help",
     {"O": ["man", "woman", "teacher", "neighbour", "classmate", "grandpa"]}),
    ("{S} ___ (想要) a glass of {O}.", "想要", "wants", "want",
     {"O": ["water", "milk", "juice", "tea", "coffee", "lemonade"]}),
    ("{S} ___ (找到) the {O} under the bed.", "找到", "finds", "find",
     {"O": ["ball", "book", "key", "toy", "pen", "sock"]}),
    ("{S} ___ (等待) for the {O}.", "等待", "waits", "wait",
     {"O": ["bus", "train", "teacher", "doctor", "friend", "postman"]}),
    ("{S} ___ (穿) a {O} today.", "穿", "wears", "wear",
     {"O": ["coat", "dress", "jacket", "sweater", "shirt", "uniform"]}),
    ("{S} ___ (唱歌) in the {O}.", "唱歌", "sings", "sing",
     {"O": ["classroom", "music room", "hall", "garden", "park", "playground"]}),
]

FILL_DIMS = [ALL_CLASSES]
FILL_POOL_SIZE = 0


def fill_item(idx: int) -> dict:
    """按全局序号取题（旧接口）。"""
    return fill_item_at(idx % len(FILL_FRAMES), idx // len(FILL_FRAMES))


def fill_item_at(tpl_index: int, slot_pos: int) -> dict:
    """指定模板 + 模板内槽位序号构造填空题（同 grammar_item_at 的去重思路）。"""
    f = FILL_FRAMES[tpl_index % len(FILL_FRAMES)]
    tpl, hint, ans_sg, ans_pl, slots = f
    keys = list(slots)
    subjects = ALL_CLASSES if "{S}" in tpl else ALL_CLASSES[:1]
    dims = [subjects] + [slots[k] for k in keys]
    decoded = decode(slot_pos, dims)
    cls, subj = decoded[0]
    vals = decoded[1:]
    sentence = tpl.format(S=subj, **dict(zip(keys, vals)))
    ans = ans_sg if cls == "sg" else ans_pl
    return {
        "content": {"stem": sentence, "hint": hint},
        "options": [],
        "answer": ans,
        "analysis": f"括号提示「{hint}」，应填 {ans}。",
        "difficulty": 2,
    }


# ---------------- 阅读理解（按学段的槽位短文，每篇 6 问） ----------------
NAMES = ["Tom", "Lily", "Jack", "Amy", "Ben", "Kate", "Mike", "Lucy", "Sam", "Anna"]
FRIENDS = ["his father", "her mother", "his friend", "her sister", "his brother",
           "her cousin", "his classmate", "her neighbour"]
ANIMALS = ["dog", "cat", "rabbit", "bird", "panda", "fish", "monkey", "duck"]
PETS = ["Coco", "Mimi", "Bobo", "Lulu", "Kitty", "Doudou", "Beibei", "Lele"]
COLORS = ["white", "black", "brown", "yellow", "grey", "orange"]
PLACES = ["park", "garden", "street", "zoo", "square", "playground"]
ACTS = ["run with a ball", "play with a stick", "jump on the grass",
        "chase a small ball", "climb a tree", "swim in the water"]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
TRIP_PLACES = ["beach", "zoo", "farm", "museum", "park", "mountain"]
WEATHER = ["sunny and warm", "cloudy and cool", "windy and dry", "clear and hot", "rainy and cold"]
TRIP_ACTS = ["collected shells", "took photos", "flew a kite", "picked fruit",
             "watched animals", "played games"]
THINGS = ["small crab", "old coin", "little shell", "red leaf", "lost key", "small stone"]
SPOTS = ["rock", "tree", "bench", "stone", "bush", "wall"]
REASONS = ["it was alive", "it was dirty", "it was too heavy", "it was not his"]
CITIES = ["Shenzhen", "Beijing", "Shanghai", "Guangzhou", "Hangzhou", "Chengdu"]
KMS = ["twenty", "thirty", "forty", "fifty", "sixty"]
PCTS = ["sixty", "seventy", "eighty", "ninety", "ninety-five"]
RIDERS = ["five hundred", "six hundred", "eight hundred", "one thousand", "two thousand"]


def _opts4(correct, pool, salt: int):
    """由正确项加 3 个同类干扰项组成 4 选项，保证互不重复。"""
    d = [x for x in pool if x != correct]
    picked = [d[(salt + k) % len(d)] for k in range(3)]
    uniq = []
    for x in picked:
        if x not in uniq:
            uniq.append(x)
    k = 3
    while len(uniq) < 3:
        x = d[(salt + k) % len(d)]
        if x not in uniq:
            uniq.append(x)
        k += 1
    texts = [correct] + uniq
    keys = "ABCD"
    return [{"key": keys[i], "text": t} for i, t in enumerate(texts)], "A"


def reading_passage(idx: int, band: tuple[int, int]) -> tuple[str, list]:
    """返回 (短文, [(问题, 选项, 答案), ...6 项])。"""
    if band == (1, 3):
        name, animal, pet, color, place, act = decode(
            idx, [NAMES, ANIMALS, PETS, COLORS, PLACES, ACTS])
        passage = (f"{name} has a small {animal}. Its name is {pet}. {pet} is {color} "
                   f"and it has two big eyes. Every morning {name} walks {pet} in the {place}. "
                   f"{pet} likes to {act}.")
        q = [
            (f"What is the {animal}'s name?",
             _opts4(pet, PETS + [name], idx)[0], pet),
            (f"What colour is {pet}?", _opts4(color, COLORS, idx + 1)[0], color),
            (f"When does {name} walk the {animal}?",
             _opts4("every morning", ["every morning", "every evening", "at noon", "at night"], idx)[0],
             "every morning"),
            (f"Where does {name} walk the {animal}?",
             _opts4(f"in the {place}", [f"in the {p}" for p in PLACES], idx)[0], f"in the {place}"),
            (f"What does {pet} like to do?", _opts4(act, ACTS, idx)[0], act),
            (f"Who has the {animal}?", _opts4(name, NAMES, idx)[0], name),
        ]
    elif band == (4, 6):
        day, name, friend, place, weather, a1, a2, thing, spot, reason = decode(
            idx, [DAYS, NAMES, FRIENDS, TRIP_PLACES, WEATHER, TRIP_ACTS, TRIP_ACTS,
                  THINGS, SPOTS, REASONS])
        passage = (f"Last {day}, {name} and {friend} went to the {place}. "
                   f"The weather was {weather}. They {a1} and {a2}. "
                   f"{name} found a {thing} near the {spot}. He put it back because it was "
                   f"{reason.replace('it was ', '')}.")
        q = [
            (f"When did {name} go to the {place}?",
             _opts4(f"last {day}", [f"last {d}" for d in DAYS], idx)[0], f"last {day}"),
            (f"Where did {name} go?",
             _opts4(f"the {place}", [f"the {p}" for p in TRIP_PLACES], idx)[0], f"the {place}"),
            ("What was the weather like?", _opts4(weather, WEATHER, idx)[0], weather),
            (f"What did {name} find near the {spot}?",
             _opts4(f"a {thing}", [f"a {t}" for t in THINGS], idx)[0], f"a {thing}"),
            (f"Who did {name} go with?", _opts4(friend, FRIENDS, idx)[0], friend),
            (f"Why did {name} put it back?",
             _opts4(reason, REASONS, idx)[0], reason),
        ]
    else:
        city, km, pct, riders = decode(idx, [CITIES, KMS, PCTS, RIDERS])
        passage = (f"More and more people in {city} ride bicycles to work. "
                   f"Bicycles are cheap and produce no pollution. However, cyclists often share "
                   f"narrow roads with cars, which can be dangerous. Last year the city built {km} "
                   f"kilometres of special lanes. A survey of {riders} riders found that {pct} "
                   f"percent of them felt safer after the lanes were built.")
        q = [
            ("Why do more people ride bicycles?",
             _opts4("cheap and clean", ["cheap and clean", "fast and new", "easy to park",
                                        "quiet and small"], idx)[0], "cheap and clean"),
            ("What problem do cyclists face?",
             _opts4("sharing narrow roads with cars",
                    ["sharing narrow roads with cars", "paying high fees",
                     "finding fuel", "repairing bikes"], idx)[0], "sharing narrow roads with cars"),
            ("What did the city build?",
             _opts4(f"{km} kilometres of special lanes",
                    [f"{k} kilometres of special lanes" for k in KMS], idx)[0],
             f"{km} kilometres of special lanes"),
            ("How many riders were in the survey?",
             _opts4(riders, RIDERS, idx)[0], riders),
            ("What did the survey find?",
             _opts4(f"{pct} percent felt safer", [f"{p} percent felt safer" for p in PCTS], idx)[0],
             f"{pct} percent felt safer"),
            ("What is the writer's attitude?",
             _opts4("supportive but aware of safety",
                    ["supportive but aware of safety", "completely against it",
                     "uninterested", "unsure"], idx)[0], "supportive but aware of safety"),
        ]
    return passage, q


def band_for_grade(grade: int) -> tuple[int, int]:
    if grade <= 3:
        return (1, 3)
    if grade <= 6:
        return (4, 6)
    return (7, 9)
