# -*- coding: utf-8 -*-
"""重跑内容包：英语 七年级上册（牛津深圳版）english_g7。六单元按主题递进，覆盖时态、从句、被动、比较级与读写情境；题干与选项用英文，解析用中文。"""
PACK = {
    "subject": "english", "grade": 7, "version": "牛津深圳版", "semester": "first",
    "chapters": [
        {"name": "Unit 1 Trying new things", "summary": "围绕尝试新事物，练现在进行时、动词-ing、try 搭配与日记写作。", "points": [
            {"name": "Present simple and present continuous", "explanation": "习惯动作用一般现在时，此刻进行用 be 加动词-ing，Look、now 是进行时的时间标志。", "questions": [
                ("choice", "Look! Sam ___ a new sport.", ["tries", "is trying", "tried", "try"], "B", "Look提示用进行时，其余时态不对，所以选B。", 1),
                ("fill", "He ___ a club each week.", None, "joins", "每周习惯用三单joins。", 2),
                ("judge", "He is try a new game now.", None, "F", "进行时须is trying，原形try错。", 3),
                ("choice", "He ___ football now.", ["plays", "is playing", "played", "play"], "B", "now用进行时，其余时态不对，所以选B。", 4),
            ]},
            {"name": "Verb-ing spelling rules", "explanation": "一般加-ing；不发音 e 结尾去 e；重读闭音节双写末字母；ie 结尾改 y 加-ing。", "questions": [
                ("choice", "How to spell 'run' + ing?", ["runing", "running", "runnning", "runng"], "B", "重读闭音节双写n加ing，所以选B。", 1),
                ("fill", "write → ___", None, "writing", "以不发音e结尾，去e加ing。", 2),
                ("judge", "Lie becomes lieing.", None, "F", "lie变lying，ie改y加ing。", 3),
                ("choice", "Pick the correct -ing form.", ["swiming", "swimming", "swimimg", "swimmin"], "B", "双写m加ing才对，其余拼写错，所以选B。", 4),
            ]},
            {"name": "try to do vs try doing", "explanation": "try doing 表示试试看某做法，try to do 表示努力去做成，两者含义不同。", "questions": [
                ("choice", "___ climbing; it is fun.", ["Try", "Tries", "Tried", "Trying"], "A", "祈使句用Try表试试看，所以选A。", 1),
                ("fill", "I try ___ lift the box.", None, "to", "try to do表努力去做，用to。", 2),
                ("judge", "Try doing means an effort.", None, "F", "try doing是试试看，非努力做。", 3),
                ("choice", "Which means 'give it a go'?", ["try doing", "try to do", "stop doing", "keep to do"], "A", "表试一试用try doing，所以选A。", 4),
            ]},
            {"name": "Writing a diary entry", "explanation": "日记记录已发生的事，常用一般过去时，并写出当时的感受。", "questions": [
                ("choice", "A diary uses ___ tense.", ["past", "future", "passive", "plural"], "A", "日记记已发生的事，用过去时，所以选A。", 1),
                ("fill", "Yesterday I ___ a cake.", None, "baked", "昨天用过去式baked。", 2),
                ("judge", "A diary shows feelings.", None, "T", "日记可写感受，说法正确。", 3),
                ("answer", "Write about a new try.", None, "I tried skating and felt proud.", "评分：用过去式得1分；写出感受得1分。", 4),
            ]},
        ]},
        {"name": "Unit 2 Strong mind", "summary": "围绕坚强意志，练副词、比较级、情态动词与原因时间状语从句。", "points": [
            {"name": "Adjectives and adverbs of manner", "explanation": "形容词修饰名词，副词修饰动词，多数副词由形容词加-ly 构成。", "questions": [
                ("choice", "She works ___ every day.", ["hard", "hardly", "harder", "hardest"], "A", "用副词hard，hardly意不同，所以选A。", 1),
                ("fill", "He runs very ___ (quick).", None, "quickly", "修饰runs用副词quickly。", 2),
                ("judge", "Brave is an adverb.", None, "F", "brave是形容词，副词为bravely。", 3),
                ("choice", "Pick the adverb here.", ["careful", "carefully", "care", "caring"], "B", "只有该词以ly结尾作副词，所以选B。", 4),
            ]},
            {"name": "Comparatives with -er and than", "explanation": "两者比较用比较级，单音节词加-er，后接 than；good 的比较级是 better。", "questions": [
                ("choice", "Courage is ___ than fear.", ["better", "good", "best", "well"], "A", "than前用比较级better，所以选A。", 1),
                ("fill", "A is ___ (hard) than B.", None, "harder", "有than，hard加er得harder。", 2),
                ("judge", "More brave is correct.", None, "F", "brave以e结尾只加r变braver。", 3),
                ("choice", "Which is a comparative?", ["bravest", "braver", "brave", "bravely"], "B", "加er表更勇敢，其余形式不同，所以选B。", 4),
            ]},
            {"name": "Must, should and obligation", "explanation": "must、should 表必须或应该，后接动词原形，用来给出建议或要求。", "questions": [
                ("choice", "We ___ never give up.", ["should", "are", "do", "have"], "A", "should表应该，后接动词原形，所以选A。", 1),
                ("fill", "I ___ stay calm.", None, "must", "表必须保持冷静用must。", 2),
                ("judge", "Must is followed by a verb.", None, "T", "must后接动词原形，说法正确。", 3),
                ("choice", "Which shows obligation?", ["may go", "must go", "can go", "might go"], "B", "must表必须，其余表可能，所以选B。", 4),
            ]},
            {"name": "Because and when clauses", "explanation": "because 接完整从句表原因，when 引导时间从句，although 表让步。", "questions": [
                ("choice", "He trained ___ he was ill.", ["since", "although", "so", "if"], "B", "带病仍训练是让步，用although，所以选B。", 1),
                ("fill", "Call me ___ you need help.", None, "when", "when引导时间从句。", 2),
                ("judge", "Because joins a clause.", None, "T", "because后接完整从句表原因。", 3),
                ("answer", "Write why courage helps.", None, "It helps because we never give up.", "评分：用because从句得1分；意思完整得1分。", 4),
            ]},
        ]},
        {"name": "Unit 3 Jobs", "summary": "围绕职业话题，练职业名词后缀、三单、wh- 疑问句与宾语从句。", "points": [
            {"name": "Job nouns and suffixes", "explanation": "动词加-er、-or、-ist 可构成职业名词，如 teacher、actor、scientist。", "questions": [
                ("choice", "One who teaches is a ___.", ["teacher", "teach", "teaching", "taught"], "A", "动词加er表做该事的人，所以选A。", 1),
                ("fill", "One who acts is an ___.", None, "actor", "act加or表演员。", 2),
                ("judge", "Scientists study science.", None, "T", "科学家研究科学，ist表从业人。", 3),
                ("choice", "Which names a job?", ["doctor", "doctorly", "doc", "doctoring"], "A", "doctor是职业名词，其余不是，所以选A。", 4),
            ]},
            {"name": "Third-person singular -s", "explanation": "主语为第三人称单数、谈习惯工作时，动词加-s 或-es。", "questions": [
                ("choice", "A nurse ___ in a hospital.", ["work", "works", "working", "worked"], "B", "主语单数，动词加s得works，所以选B。", 1),
                ("fill", "She ___ a bus daily.", None, "drives", "daily表习惯，三单用drives。", 2),
                ("judge", "He fix bikes every day.", None, "F", "He后须用fixes，原形错误。", 3),
                ("choice", "Which sentence is correct?", ["teach", "teaches", "teaching", "taught"], "B", "三单加es得teaches，其余错，所以选B。", 4),
            ]},
            {"name": "Wh- questions about work", "explanation": "Where 问地点，Who 问人，What do you do 问职业，疑问词后接一般疑问句语序。", "questions": [
                ("choice", "___ does a nurse work?", ["Where", "Who", "What", "Whose"], "A", "问地点用Where，其余不合，所以选A。", 1),
                ("fill", "___ do you do? I am a vet.", None, "What", "问职业用What do you do。", 2),
                ("judge", "Who asks about a person.", None, "T", "Who对人提问，说法正确。", 3),
                ("choice", "Pick the question word.", ["When", "Because", "And", "Very"], "A", "只有该词是疑问词，其余不是，所以选A。", 4),
            ]},
            {"name": "Object clauses with that", "explanation": "陈述句作宾语时可用 that 引导宾语从句，从句须含主语和谓语。", "questions": [
                ("choice", "I know ___ he is a dentist.", ["that", "what", "who", "which"], "A", "陈述句作宾语用that引导，所以选A。", 1),
                ("fill", "I believe ___ she is right.", None, "that", "陈述内容作宾语用that。", 2),
                ("judge", "A clause has a subject.", None, "T", "从句须含主谓，说法正确。", 3),
                ("answer", "Write about a job.", None, "My aunt is a vet. She helps sick pets.", "评分：写出职业得1分；用三单动词得1分。", 4),
            ]},
        ]},
        {"name": "Unit 4 Smart home", "summary": "围绕智能家居，练将来时、一般现在时被动、方位介词与使用说明祈使句。", "points": [
            {"name": "Future with will and there will be", "explanation": "will 加动词原形表将来，There will be 表示将来会有某物。", "questions": [
                ("choice", "Next year homes ___ smart.", ["are", "will be", "were", "was"], "B", "Next year表将来，用will be，所以选B。", 1),
                ("fill", "There ___ a robot soon.", None, "will be", "soon表将来，用There will be。", 2),
                ("judge", "Will takes a base verb.", None, "T", "will后接动词原形，说法正确。", 3),
                ("choice", "Pick the future form.", ["is clean", "will clean", "cleaned", "cleans"], "B", "will加原形表将来，其余不是，所以选B。", 4),
            ]},
            {"name": "Present passive: be + done", "explanation": "一般现在时被动用 am/is/are 加过去分词，强调动作承受者。", "questions": [
                ("choice", "The door ___ by a sensor.", ["opens", "is opened", "opening", "open"], "B", "门被打开，用is加过去分词，所以选B。", 1),
                ("fill", "Lamps ___ (turn) on daily.", None, "are turned", "灯被打开，复数用are turned。", 2),
                ("judge", "Passive uses a past form.", None, "T", "被动语态含be加过去分词。", 3),
                ("choice", "Which is passive voice?", ["heats", "is heated", "heating", "heat"], "B", "be加过去分词才是被动，所以选B。", 4),
            ]},
            {"name": "Prepositions of place", "explanation": "next to 表相邻，above 表在上方，between 用于两者之间。", "questions": [
                ("choice", "The hub is next ___ the TV.", ["to", "of", "at", "on"], "A", "next to是固定搭配，所以选A。", 1),
                ("fill", "It hangs ___ the bed.", None, "above", "above表在上方且不接触。", 2),
                ("judge", "Between means two things.", None, "T", "between用于两者之间，说法正确。", 3),
                ("choice", "Which shows a place?", ["under", "quickly", "often", "because"], "A", "只有该词是方位介词，所以选A。", 4),
            ]},
            {"name": "Imperatives in a user guide", "explanation": "说明书用动词原形开头的祈使句给指令，否定形式用 Don't 加原形。", "questions": [
                ("choice", "___ the app first.", ["Open", "Opened", "Opening", "Opens"], "A", "祈使句用动词原形开头，所以选A。", 1),
                ("fill", "___ (not) touch the wires.", None, "Don't", "否定祈使句用Don't加原形。", 2),
                ("judge", "Imperatives omit 'you'.", None, "T", "祈使句省略主语you，说法正确。", 3),
                ("answer", "Write one smart-home rule.", None, "Turn off the lights when you leave.", "评分：用祈使句得1分；含时间从句得1分。", 4),
            ]},
        ]},
        {"name": "Unit 5 Films", "summary": "围绕电影话题，练一般过去时、最高级、定语从句与影评写作。", "points": [
            {"name": "Past simple: regular and irregular", "explanation": "过去时间用过去式，规则动词加-ed，see、go、buy 等为不规则变化。", "questions": [
                ("choice", "We ___ a film last night.", ["watch", "watched", "watches", "watching"], "B", "昨晚用过去式watched，所以选B。", 1),
                ("fill", "He ___ (see) it yesterday.", None, "saw", "see的过去式是不规则saw。", 2),
                ("judge", "Goed is the past of go.", None, "F", "go的过去式是went，不是goed。", 3),
                ("choice", "Pick the past tense.", ["buyed", "bought", "buying", "buys"], "B", "buy的过去式为bought，其余错，所以选B。", 4),
            ]},
            {"name": "Superlatives with the -est", "explanation": "三者以上比较用 the 加最高级，单音节词加-est，good 的最高级是 best。", "questions": [
                ("choice", "This is ___ film of all.", ["the best", "better", "good", "well"], "A", "of all表范围用最高级，所以选A。", 1),
                ("fill", "It is the ___ (funny) one.", None, "funniest", "the后加est，funny变funniest。", 2),
                ("judge", "The most tall is correct.", None, "F", "tall是单音节，加est变tallest。", 3),
                ("choice", "Which is a superlative?", ["longer", "longest", "long", "longly"], "B", "加est表最长，其余形式不同，所以选B。", 4),
            ]},
            {"name": "Relative clauses with who/that", "explanation": "先行词是人用 who，是物用 that 或 which 引导定语从句。", "questions": [
                ("choice", "The man ___ acts is kind.", ["who", "which", "where", "what"], "A", "先行词是人，用who引导，所以选A。", 1),
                ("fill", "I like the film ___ we saw.", None, "that", "先行词是物，从句用that。", 2),
                ("judge", "Who refers to people.", None, "T", "who指人，which指物，说法正确。", 3),
                ("choice", "Pick the relative word.", ["which", "because", "quickly", "under"], "A", "只有该词可引导定语从句，所以选A。", 4),
            ]},
            {"name": "Writing a film review", "explanation": "影评表达观点，可概述情节，并用过去时评价看过的影片。", "questions": [
                ("choice", "A review gives a(n) ___.", ["opinion", "ticket", "camera", "actor"], "A", "影评表达观点，其余是物件，所以选A。", 1),
                ("fill", "I ___ the ending a lot.", None, "liked", "评价看过的影片用过去式liked。", 2),
                ("judge", "A review may name the plot.", None, "T", "影评可概述情节，说法正确。", 3),
                ("answer", "Write one line of a review.", None, "The story was moving and the music was great.", "评分：用过去式得1分；写出评价得1分。", 4),
            ]},
        ]},
        {"name": "Unit 6 Mountains and rivers", "summary": "围绕山川地理，练比较级、被动语态、方位词与风景描写。", "points": [
            {"name": "Comparing with -er than", "explanation": "比较两处地貌用比较级加 than，如 higher、longer、deeper。", "questions": [
                ("choice", "Peak A is ___ than Peak B.", ["higher", "high", "highest", "highly"], "A", "than前用比较级higher，所以选A。", 1),
                ("fill", "A is ___ (long) than B.", None, "longer", "有than，long加er得longer。", 2),
                ("judge", "Than follows a comparative.", None, "T", "比较级后常接than，说法正确。", 3),
                ("choice", "Pick the comparative form.", ["deep", "deeper", "deepest", "deeply"], "B", "加er表更深，其余形式不同，所以选B。", 4),
            ]},
            {"name": "Passive in geography facts", "explanation": "描述地貌成因常用被动语态，如 is covered、are formed。", "questions": [
                ("choice", "The peak ___ with snow.", ["covers", "is covered", "covering", "cover"], "B", "山峰被雪覆盖，用被动，所以选B。", 1),
                ("fill", "Banks ___ (form) by rivers.", None, "are formed", "河岸被形成，用are formed。", 2),
                ("judge", "Passive needs a form of be.", None, "T", "被动须有be加过去分词。", 3),
                ("choice", "Pick the passive form.", ["feeds", "is fed", "feeding", "feed"], "B", "be加过去分词是被动，所以选B。", 4),
            ]},
            {"name": "Direction and place words", "explanation": "through 表穿过，in the north 表方位，toward 表方向。", "questions": [
                ("choice", "It flows ___ the hills.", ["through", "because", "often", "quickly"], "A", "只有该词是方位介词，其余不合，所以选A。", 1),
                ("fill", "It lies ___ the north.", None, "in", "在某方位用in the north。", 2),
                ("judge", "North shows a direction.", None, "T", "north是方位词，说法正确。", 3),
                ("choice", "Which shows direction?", ["toward", "very", "also", "soon"], "A", "只有该词表方向，其余是副词，所以选A。", 4),
            ]},
            {"name": "Describing a landscape", "explanation": "写景用 steep、clear、peaceful 等形容词，名词加-ful 可构成形容词。", "questions": [
                ("choice", "Which fits a landscape?", ["steep", "hungry", "noisy", "tidy"], "A", "steep形容山势，其余不写景，所以选A。", 1),
                ("fill", "The lake looks ___ (peace).", None, "peaceful", "peace加ful变形容词。", 2),
                ("judge", "Adjectives describe views.", None, "T", "形容词用来描写景色，说法正确。", 3),
                ("answer", "Write about a river.", None, "The clear river winds through green hills.", "评分：用形容词得1分；语句通顺得1分。", 4),
            ]},
        ]},
    ],
}
_REVIEW_Q = {
    "Unit 1 Trying new things": [
        (0, ("choice", "Now we ___ a new game.", ["are trying", "try", "tried", "tries"], "A", "Now用进行时，其余时态不对，所以选A。", 3)),
        (3, ("answer", "Ask a friend to join us.", None, "Why not try the art club with me?", "评分：用提建议句型得1分；语句通顺得1分。", 4)),
    ],
    "Unit 2 Strong mind": [
        (1, ("choice", "Which is the superlative?", ["stronger", "strongest", "strong", "strongly"], "B", "加est表最强，其余形式不同，所以选B。", 3)),
        (2, ("answer", "Give a shy friend advice.", None, "You should speak up and keep trying.", "评分：用should得1分；建议具体得1分。", 4)),
    ],
    "Unit 3 Jobs": [
        (0, ("choice", "Which one is a job suffix?", ["-er", "-ing", "-ed", "-ly"], "A", "er加动词后表人，其余不是，所以选A。", 3)),
        (2, ("answer", "Ask where someone works.", None, "Where does your uncle work?", "评分：用Where does得1分；三单正确得1分。", 4)),
    ],
    "Unit 4 Smart home": [
        (1, ("choice", "The floor ___ by a robot.", ["cleans", "is cleaned", "clean", "cleaning"], "B", "地板被清洁，用被动，所以选B。", 3)),
        (0, ("answer", "Describe a smart room.", None, "There will be a voice-controlled lamp.", "评分：用will be得1分；写出设备得1分。", 4)),
    ],
    "Unit 5 Films": [
        (0, ("choice", "We ___ popcorn last night.", ["eat", "ate", "eats", "eating"], "B", "叙述过去用过去式ate，所以选B。", 3)),
        (2, ("answer", "Ask which film is best.", None, "Which film do you like best?", "评分：用Which得1分；用最高级得1分。", 4)),
    ],
    "Unit 6 Mountains and rivers": [
        (0, ("choice", "Which is the highest form?", ["high", "higher", "highest", "highly"], "C", "加est表最高，其余不对，所以选C。", 3)),
        (1, ("answer", "Write how a lake is formed.", None, "The lake is fed by mountain streams.", "评分：用被动语态得1分；写出来源得1分。", 4)),
    ],
}
for _ch in PACK["chapters"]:
    for _idx, _q in _REVIEW_Q[_ch["name"]]:
        _ch["points"][_idx]["questions"].append(_q)
