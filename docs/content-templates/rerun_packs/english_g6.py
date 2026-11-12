# -*- coding: utf-8 -*-
"""重跑内容包：英语 六年级上册（牛津深圳版）。六单元按主题递进，覆盖词汇、时态句型、语音与读写情境；题干与选项用英文，解析用中文。"""
PACK = {
    "subject": "english", "grade": 6, "version": "牛津深圳版", "semester": "first",
    "chapters": [
        {"name": "Unit 1 Why do people move to new places?", "summary": "围绕迁居原因与地点，练 because、一般过去时、长音 /uː/ 与便条读写。", "points": [
            {"name": "Naming places: city, town, village", "explanation": "city、town、village 按规模区分，flat 是住宅，均可测量辨认。", "questions": [
                ("choice", "Which place has farms?", ["City", "Village", "Station", "Museum"], "B", "乡村有农田，其余属城市场所，所以选 B。", 1),
                ("fill", "A ___ is bigger than a town.", None, "city", "city 比 town 大，人口更多。", 2),
                ("judge", "A flat is a kind of home.", None, "T", "flat 指公寓，是一种住宅，说法正确。", 3),
                ("answer", "Name two new places.", None, "A city and a village.", "评分：写出两处地点各得 1 分；拼写对得 1 分。", 4),
            ]},
            {"name": "Because and past tense of move", "explanation": "because 接从句说明迁移原因；Last year、ago 用过去式 moved、lived。", "questions": [
                ("choice", "Why did Ben move?", ["For a job", "For a pen", "For a bus", "For a cake"], "A", "新工作是迁移缘由，其余是物品，所以选 A。", 1),
                ("fill", "We moved ___ Dad found work.", None, "because", "because 后接完整从句说明原因。", 2),
                ("choice", "Last year they ___ to a town.", ["moved", "move", "moves", "moving"], "A", "过去时间用 moved，其余形式不对，所以选 A。", 3),
                ("judge", "She move here in 2019.", None, "F", "过去时间须用 moved，原形错误。", 4),
            ]},
            {"name": "Long /uː/ in move and school", "explanation": "move、school、moon、food 含长音 /uː/，与 book、good 的 /ʊ/ 不同。", "questions": [
                ("choice", "Which word has /uː/?", ["Cat", "Moon", "Bed", "Pig"], "B", "该词含长音 /uː/，其余是短音，所以选 B。", 1),
                ("fill", "School and ___ rhyme.", None, "cool", "cool 与 school 同押 /uː/ 韵。", 2),
                ("judge", "Move and love sound the same.", None, "F", "move 发 /uː/，love 发 /ʌ/，并不相同。", 3),
                ("choice", "Which has /uː/ here?", ["food", "book", "look", "good"], "A", "该词发 /uː/，其余发 /ʊ/，所以选 A。", 4),
            ]},
            {"name": "Reading a moving note", "explanation": "读便条取信息，用 move to 与形容词描述迁居感受，写一句原因。", "questions": [
                ("choice", "He misses friends. He is ___.", ["sad", "glad", "fast", "cold"], "A", "想念朋友会难过，其余情绪不合，所以选 A。", 1),
                ("fill", "I moved ___ a new town.", None, "to", "move to 表搬往某地，用介词 to。", 2),
                ("judge", "A note can tell why we moved.", None, "T", "便条可写明搬家原因，说法正确。", 3),
                ("answer", "Write about your move.", None, "I moved here for my mum's job.", "评分：写出缘由得 1 分；用过去式得 1 分。", 4),
            ]},
        ]},
        {"name": "Unit 2 Why do we make art?", "summary": "围绕艺术创作，练画具词、to 表目的、/ɑː/ 发音与画面描述。", "points": [
            {"name": "Art tools: brush, clay, paint", "explanation": "brush、clay、paint 是画具材料，sculpture 为立体作品。", "questions": [
                ("choice", "What do you paint with?", ["Fork", "Brush", "Spoon", "Key"], "B", "画笔用于涂色，其余非画具，所以选 B。", 1),
                ("fill", "We shape ___ with our hands.", None, "clay", "黏土可用手塑形。", 2),
                ("judge", "A sculpture is flat on paper.", None, "F", "雕塑是立体作品，不是平面画，说法错误。", 3),
                ("answer", "Name two art materials.", None, "Paint and paper.", "评分：写出两种材料各得 1 分；拼写对得 1 分。", 4),
            ]},
            {"name": "To plus verb for purpose", "explanation": "to 加动词表创作目的，tell a story 为固定搭配。", "questions": [
                ("choice", "We draw ___ show a feeling.", ["to", "for", "of", "at"], "A", "to 加动词表目的，其余介词不合，所以选 A。", 1),
                ("fill", "Art can ___ a story.", None, "tell", "固定搭配意为讲故事。", 2),
                ("judge", "People make art only to sell.", None, "F", "表达与装饰也是目的，说法太绝对。", 3),
                ("choice", "Why make a portrait?", ["To recall", "To sleep", "To cook", "To run"], "A", "画像为记住某人，其余非目的，所以选 A。", 4),
            ]},
            {"name": "The /ɑː/ sound in art", "explanation": "art、star、dark、card 中 ar 发 /ɑː/，与 cat 的 /æ/ 不同。", "questions": [
                ("choice", "Find the /ɑː/ word.", ["Sit", "Cup", "Star", "Pen"], "C", "该词 ar 发 /ɑː/，其余是短音，所以选 C。", 1),
                ("fill", "Art and ___ share /ɑː/.", None, "card", "card 的 ar 与 art 同发 /ɑː/。", 2),
                ("judge", "Dark rhymes with park.", None, "T", "两词 ar 都发 /ɑː/，押韵正确。", 3),
                ("choice", "Find the ar sound.", ["cart", "cat", "cot", "cut"], "A", "该词 ar 发 /ɑː/，其余不含，所以选 A。", 4),
            ]},
            {"name": "Adjectives for a painting", "explanation": "lively、calm、bright 等形容词描述画面与感受。", "questions": [
                ("choice", "Loud colours look ___.", ["lively", "sleepy", "empty", "slow"], "A", "色彩浓烈显得活泼，其余不合，所以选 A。", 1),
                ("fill", "A quiet scene feels ___.", None, "calm", "安静画面带来平静感。", 2),
                ("judge", "Bright yellow feels happy.", None, "T", "明黄色常带来欢快感，说法正确。", 3),
                ("answer", "Describe your art.", None, "My painting is bright and happy.", "评分：用形容词得 1 分；语句通顺得 1 分。", 4),
            ]},
        ]},
        {"name": "Unit 3 How should we protect ourselves?", "summary": "围绕自我保护，练安全词、should、祈使句、/ʃ/ 发音与规则阅读。", "points": [
            {"name": "Safety words: exit, helmet", "explanation": "exit、helmet、first aid 是安全词，matches 不是玩具。", "questions": [
                ("choice", "Where do we leave in a fire?", ["Lift", "Desk", "Bag", "Exit"], "D", "火灾从安全出口撤离，其余不安全，所以选 D。", 1),
                ("fill", "A ___ guards your head.", None, "helmet", "头盔保护骑行时的头部。", 2),
                ("judge", "Matches are safe toys.", None, "F", "火柴易引火，不是儿童玩具。", 3),
                ("answer", "Name one thing in first aid.", None, "A bandage.", "评分：写出急救用品得 1 分；拼写对得 1 分。", 4),
            ]},
            {"name": "Should and shouldn't", "explanation": "should 表该做，shouldn't 表不该，后接动词原形。", "questions": [
                ("choice", "You ___ wear a seat belt.", ["should", "shouldn't", "can't", "needn't"], "A", "should 表该做，其余表否定或不能，所以选 A。", 1),
                ("fill", "We ___ run across the road.", None, "shouldn't", "马路上奔跑危险，用 shouldn't 表不该。", 2),
                ("judge", "Should gives safe advice.", None, "T", "should 用来给出该做的安全建议。", 3),
                ("choice", "Pick the safe advice.", ["Wait green", "Run now", "Push in", "Climb high"], "A", "等绿灯才安全，其余是危险动作，所以选 A。", 4),
            ]},
            {"name": "The /ʃ/ sound in should", "explanation": "should、ship、shoe 中 sh 发 /ʃ/，与 sip、chip 不同。", "questions": [
                ("choice", "Which word starts /ʃ/?", ["Sip", "Zip", "Ship", "Chip"], "C", "该词 sh 发 /ʃ/，其余开头不同，所以选 C。", 1),
                ("fill", "Should and ___ share /ʃ/.", None, "shoe", "shoe 的 sh 与 should 同发 /ʃ/。", 2),
                ("judge", "Chair starts with /ʃ/.", None, "F", "chair 以 /tʃ/ 开头，不是 /ʃ/。", 3),
                ("choice", "Which starts with sh?", ["shell", "sell", "cell", "tell"], "A", "该词 sh 发 /ʃ/，其余不发，所以选 A。", 4),
            ]},
            {"name": "Imperatives in a drill", "explanation": "祈使句用动词原形开头，Don't 表禁止，给出清楚指令。", "questions": [
                ("choice", "'Don't touch!' means ___.", ["No hands", "Go fast", "Speak up", "Sit down"], "A", "该句意为别用手碰，其余解释不对，所以选 A。", 1),
                ("fill", "___ the door in a drill.", None, "Open", "演练时缓慢开门，祈使句用 Open。", 2),
                ("judge", "Imperatives give orders.", None, "T", "祈使句直接给指令，简短清楚。", 3),
                ("answer", "Write one road rule for kids.", None, "Wait for the green light.", "评分：写出规则得 1 分；用祈使句得 1 分。", 4),
            ]},
        ]},
        {"name": "Unit 4 What makes things move?", "summary": "围绕力与运动，练 push/pull、三单 -s、-s 尾音与比较级。", "points": [
            {"name": "Push and pull verbs", "explanation": "push 使物体远离，pull 使物体靠近，是两种基本力。", "questions": [
                ("choice", "You ___ a door to open it.", ["Sleep", "Push", "Draw", "Sing"], "B", "推门用 push，其余动作不符，所以选 B。", 1),
                ("fill", "We ___ a rope closer.", None, "pull", "拉绳使物体靠近，用 pull。", 2),
                ("judge", "A push moves things away.", None, "T", "推使物体远离施力者，说法正确。", 3),
                ("answer", "Name one way to move a box.", None, "I push the box.", "评分：写出动作得 1 分；动词准确得 1 分。", 4),
            ]},
            {"name": "Third-person singular -s", "explanation": "单数主语后动词加 s，如 moves、pulls、rolls。", "questions": [
                ("choice", "Wind ___ the leaves.", ["moves", "move", "moving", "moved"], "A", "主语是单数，动词加 s，所以选 A。", 1),
                ("fill", "A magnet ___ iron nails.", None, "pulls", "主语单数，pull 加 s 变 pulls。", 2),
                ("judge", "He push the cart every day.", None, "F", "He 后须用 pushes，原形错误。", 3),
                ("choice", "Which is correct?", ["It rolls", "It roll", "It rolling", "It rolled"], "A", "It 后加 s 得 rolls，其余形式错，所以选 A。", 4),
            ]},
            {"name": "Sounds of the -s ending", "explanation": "清音后 s 读 /s/，浊音后读 /z/，ch/sh 后 es 读 /ɪz/。", "questions": [
                ("choice", "'moves' ends with ___ sound.", ["/s/", "/ɪz/", "/t/", "/z/"], "D", "词尾是浊音，s 读 /z/，所以选 D。", 1),
                ("fill", "'pushes' ends with /___/.", None, "ɪz", "sh 后 es 读 /ɪz/，多一个音节。", 2),
                ("judge", "'stops' ends with /s/.", None, "T", "p 是清音，s 读 /s/，说法正确。", 3),
                ("choice", "Where is /ɪz/ heard?", ["watches", "runs", "plays", "rolls"], "A", "该词 es 读 /ɪz/，其余读 /z/，所以选 A。", 4),
            ]},
            {"name": "Comparatives: faster, slower", "explanation": "两者比较用 -er，如 lighter、faster，配 than。", "questions": [
                ("choice", "A ball is ___ than a stone.", ["lighter", "heavy", "slow", "round"], "A", "球比石头轻，其余不合比较，所以选 A。", 1),
                ("fill", "A bike goes ___ than a cart.", None, "faster", "两者比速度，fast 加 er 得 faster。", 2),
                ("judge", "Rough ground slows rolling.", None, "T", "粗糙地面摩擦大，滚动变慢。", 3),
                ("answer", "Compare two moving toys.", None, "The car is faster than the truck.", "评分：用比较级得 1 分；写出两物得 1 分。", 4),
            ]},
        ]},
        {"name": "Unit 5 How do inventions change our lives?", "summary": "围绕发明改变生活，练发明名词、used to、/aɪ/ 与今昔对比。", "points": [
            {"name": "Naming inventions", "explanation": "bulb、telephone、wheel 是发明物，各有实际用途。", "questions": [
                ("choice", "What gives light at night?", ["Wheel", "Clock", "Bulb", "Pen"], "C", "电灯能发光，其余不照明，所以选 C。", 1),
                ("fill", "We talk on a ___ far away.", None, "telephone", "电话用于远距离通话。", 2),
                ("judge", "A wheel helps things roll.", None, "T", "轮子使物体滚动，说法正确。", 3),
                ("answer", "Name one invention at home.", None, "The washing machine.", "评分：写出发明物得 1 分；拼写对得 1 分。", 4),
            ]},
            {"name": "Used to and past tense", "explanation": "used to 表过去习惯，now 用现在时，invented 是过去式。", "questions": [
                ("choice", "People ___ send letters.", ["used to", "use to", "uses", "using"], "A", "used to 表过去习惯，其余形式错，所以选 A。", 1),
                ("fill", "Now we ___ emails.", None, "send", "now 表现在，用动词原形 send。", 2),
                ("judge", "Bell invented the telephone.", None, "T", "贝尔发明电话，史实正确。", 3),
                ("choice", "Which is past tense?", ["invented", "invent", "invents", "inventing"], "A", "加 ed 才是过去式，其余形式不对，所以选 A。", 4),
            ]},
            {"name": "The /aɪ/ sound in light", "explanation": "light、night、high、bright 中 igh 发 /aɪ/，与 sit 不同。", "questions": [
                ("choice", "Choose the /aɪ/ sound.", ["Net", "Nut", "Not", "Night"], "D", "该词 igh 发 /aɪ/，其余短音，所以选 D。", 1),
                ("fill", "Light and ___ share /aɪ/.", None, "high", "high 与 light 同含 igh 发 /aɪ/。", 2),
                ("judge", "Right rhymes with sit.", None, "F", "right 发 /aɪ/，sit 发 /ɪ/，不押韵。", 3),
                ("choice", "Spot the igh word.", ["bright", "bring", "big", "bug"], "A", "该词 igh 发 /aɪ/，其余不含，所以选 A。", 4),
            ]},
            {"name": "Before and now in a text", "explanation": "读今昔对比句，用形容词写发明带来的改变。", "questions": [
                ("choice", "Long ago, travel was ___.", ["harder", "swifter", "easier", "nearer"], "A", "过去出行更费力，其余不合，所以选 A。", 1),
                ("fill", "Now messages travel ___.", None, "fast", "现在信息传递快，用形容词 fast。", 2),
                ("judge", "Inventions make work easier.", None, "T", "发明减轻劳动，说法正确。", 3),
                ("answer", "Write how life changed.", None, "We now call friends by phone.", "评分：写出今昔对比得 1 分；语句通顺得 1 分。", 4),
            ]},
        ]},
        {"name": "Unit 6 What is a city?", "summary": "围绕城市构成，练场所名词、There be、soft c 与地图方位。", "points": [
            {"name": "City places: library, station", "explanation": "library、station、museum 是城市场所，功能各不相同。", "questions": [
                ("choice", "Where do you borrow books?", ["Bakery", "Garage", "Library", "Farm"], "C", "图书馆可借书，其余场所不符，所以选 C。", 1),
                ("fill", "Trains stop at the ___.", None, "station", "火车停靠在车站。", 2),
                ("judge", "A museum shows old things.", None, "T", "博物馆陈列旧物，说法正确。", 3),
                ("answer", "Name two city places.", None, "A park and a market.", "评分：写出两处场所各得 1 分；拼写对得 1 分。", 4),
            ]},
            {"name": "There is and There are", "explanation": "单数用 There is，复数用 There are，与名词数一致。", "questions": [
                ("choice", "___ a park near my flat.", ["There is", "There are", "There be", "It has"], "A", "单数名词配 There is，所以选 A。", 1),
                ("fill", "___ two buses on the road.", None, "There are", "复数名词用 There are。", 2),
                ("judge", "There are a bridge here.", None, "F", "单数名词应用 There is。", 3),
                ("choice", "___ many shops in the centre.", ["There are", "There is", "It is", "That is"], "A", "复数名词配 There are，所以选 A。", 4),
            ]},
            {"name": "Soft c in city", "explanation": "c 在 e、i、y 前发 /s/ 如 city，在 a、o、u 前发 /k/。", "questions": [
                ("choice", "How does 'c' sound in city?", ["/k/", "/tʃ/", "/g/", "/s/"], "D", "该词 c 发 /s/，其余音不符，所以选 D。", 1),
                ("fill", "Centre and ___ share /s/ c.", None, "circle", "该词首字母 c 也发 /s/。", 2),
                ("judge", "Cat and city start the same.", None, "F", "前词 c 发 /k/，后者发 /s/，不同。", 3),
                ("choice", "Which c is soft?", ["cinema", "cake", "cup", "cold"], "A", "该词 c 发 /s/，其余发 /k/，所以选 A。", 4),
            ]},
            {"name": "Prepositions on a city map", "explanation": "next to、between、opposite 描述位置，读地图取信息。", "questions": [
                ("choice", "The bank is ___ the park.", ["next to", "suddenly", "almost", "twice"], "A", "next to 表相邻，其余是副词，所以选 A。", 1),
                ("fill", "The shop is ___ two roads.", None, "between", "两者之间用 between。", 2),
                ("judge", "Opposite means across from.", None, "T", "opposite 意为在对面，说法正确。", 3),
                ("answer", "Write about your city.", None, "There is a museum near my home.", "评分：用 There is 得 1 分；写出场所得 1 分。", 4),
            ]},
        ]},
    ],
}
_REVIEW_Q = {
    "Unit 1 Why do people move to new places?": [
        (0, ("choice", "Why do many families move?", ["For work", "For toys", "For rain", "For games"], "A", "工作是常见迁移原因，其余不相关，所以选 A。", 3)),
        (1, ("answer", "Ask why someone moved.", None, "Why did you move to this city?", "评分：用 Why did 得 1 分；动词原形得 1 分。", 4)),
    ],
    "Unit 2 Why do we make art?": [
        (0, ("choice", "Why do we hang art at home?", ["To decorate", "To hide", "To break", "To boil"], "A", "挂画为装饰，其余动作不合理，所以选 A。", 3)),
        (1, ("answer", "Write why you like drawing.", None, "I draw to show my ideas.", "评分：用 to 表目的得 1 分；语句完整得 1 分。", 4)),
    ],
    "Unit 3 How should we protect ourselves?": [
        (0, ("choice", "A stranger calls. You ___.", ["Say no", "Get in", "Wave back", "Follow"], "A", "应拒绝陌生人，其余做法有风险，所以选 A。", 3)),
        (1, ("answer", "Give one fire drill tip.", None, "Walk, do not run, to the exit.", "评分：写出有序撤离得 1 分；用祈使句得 1 分。", 4)),
    ],
    "Unit 4 What makes things move?": [
        (0, ("choice", "What makes a leaf fall down?", ["Gravity", "Paint", "Music", "Paper"], "A", "重力使叶子下落，其余非力，所以选 A。", 3)),
        (1, ("answer", "Write what moves a kite.", None, "The wind moves the kite high.", "评分：写出风力得 1 分；用三单动词得 1 分。", 4)),
    ],
    "Unit 5 How do inventions change our lives?": [
        (0, ("choice", "Why is the wheel useful?", ["It rolls", "It sings", "It shines", "It rains"], "A", "轮子能滚动载物，其余不合，所以选 A。", 3)),
        (1, ("answer", "Compare letters and email.", None, "Email is quicker than a letter.", "评分：用比较级得 1 分；写出两者得 1 分。", 4)),
    ],
    "Unit 6 What is a city?": [
        (0, ("choice", "What makes a place a city?", ["Crowds", "One hut", "No road", "A farm"], "A", "城市人群密集，其余是乡村景象，所以选 A。", 3)),
        (1, ("answer", "Ask where the station is.", None, "Where is the bus station, please?", "评分：用 Where is 得 1 分；礼貌用语得 1 分。", 4)),
    ],
}
for _ch in PACK["chapters"]:
    for _idx, _q in _REVIEW_Q[_ch["name"]]:
        _ch["points"][_idx]["questions"].append(_q)
