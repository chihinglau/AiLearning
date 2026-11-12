# -*- coding: utf-8 -*-
"""重跑内容包：英语 九年级上册（牛津深圳版）。

按骨架索引六个单元建立节级知识点，每点四题、章末再补两题；
题干与选项用英文、解析用中文，覆盖时态、从句、被动语态、非谓语、
词汇辨析与读写情境，全部为可核对的具体语言点，不用套话与多选题。
"""
PACK = {
    "subject": "english", "grade": 9, "version": "牛津深圳版", "semester": "first",
    "chapters": [
        {"name": "Unit 1 Teenage life", "summary": "围绕青少年生活，练现在完成时、宾语从句、动词辨析与 used to，并结合校园情境写作。", "points": [
            {"name": "现在完成时与 since、for 的连用", "explanation": "have/has + 过去分词表动作持续到现在；since 接点时间，for 接时间段，不与 yesterday 等明确过去时间连用。", "questions": [
                ("choice", "Lily ___ in Shenzhen since 2019.", ["has lived", "lives", "lived", "is living"], "A", "since 2019 表持续到现在，用现在完成时 has lived，所以选 A。", 1),
                ("fill", "I have known Amy ___ six years.", None, "for", "six years 是时间段，前面用 for；since 后须接点时间，所以填 for。", 2),
                ("judge", "He has finished his homework last night.", None, "F", "last night 是明确过去时间，不能用现在完成时，所以错。", 3),
                ("answer", "Write one sentence about your school life.", None, "I have joined the art club and I enjoy it a lot.", "要点：用现在完成时写一句完整句，时态与拼写正确即得分。", 4),
            ]},
            {"name": "宾语从句的语序与连接词", "explanation": "宾语从句用陈述语序；that 可省，whether/if 表是否，疑问词保留疑问含义；主句过去时从句时态相应后移。", "questions": [
                ("choice", "Do you know ___ she lives?", ["what", "where", "which", "who"], "B", "问地点用 where 引导宾语从句，从句用陈述语序，所以选 B。", 1),
                ("fill", "Could you tell me ___ the train leaves?", None, "when", "问时间用 when 引导宾语从句，从句须用陈述语序，所以填 when。", 2),
                ("judge", "I wonder that he will come tomorrow.", None, "F", "wonder 表想知道，须用 whether 或 if，不能用 that，所以错。", 3),
                ("answer", "Ask a classmate about his hobby politely.", None, "Could you tell me what your hobby is?", "要点：用 Could you tell me 加陈述语序宾语从句，语气礼貌即得分。", 4),
            ]},
            {"name": "spend、cost、take、pay 的辨析", "explanation": "spend 主语是人，搭配 on 或 doing；cost 主语是物；take 用 It takes sb time to do；pay 搭配 for。", "questions": [
                ("choice", "I ___ two hours on my homework.", ["cost", "took", "spent", "paid"], "C", "主语是人且搭配 on，用 spent；cost 主语是物，所以选 C。", 1),
                ("fill", "The new bike ___ me 500 yuan.", None, "cost", "主语是物、表花钱用 cost，其过去式不变，所以填 cost。", 2),
                ("judge", "It spent me an hour to clean the room.", None, "F", "花费时间用 take 的 It 句型，spend 主语须为人，所以错。", 3),
                ("answer", "Write a sentence about buying a book.", None, "I paid 30 yuan for this storybook.", "要点：pay 与 for 搭配、主语为人，句子完整即得分。", 4),
            ]},
            {"name": "used to 与 be used to doing 的区别", "explanation": "used to do 表过去常常做、现在已不；be used to doing 表习惯做；be used to do 是被动，表被用于做。", "questions": [
                ("choice", "He ___ be shy, but now he is outgoing.", ["is used to", "uses to", "was used to", "used to"], "D", "过去常常害羞且今非昔比，用 used to do，所以选 D。", 1),
                ("fill", "I am used ___ up early every morning.", None, "to getting", "be used to 后接动名词，填 to getting 表习惯早起。", 2),
                ("judge", "Wood is used to making paper.", None, "F", "be used to do 才是被用于做，表习惯才接动名词，所以错。", 3),
                ("answer", "Describe one habit you had as a child.", None, "I used to walk to school with my grandpa.", "要点：用 used to do 描述过去习惯，动词原形与拼写正确即得分。", 4),
            ]},
        ]},
        {"name": "Unit 2 People and their jobs", "summary": "围绕人物与职业，练定语从句、被动语态、职业名词后缀与反意疑问句。", "points": [
            {"name": "who、which、that 引导的定语从句", "explanation": "定语从句修饰先行词；指人用 who 或 that，指物用 which 或 that；关系词作宾语时可省略。", "questions": [
                ("choice", "The doctor ___ saved the boy is famous.", ["which", "what", "who", "whom"], "C", "先行词 doctor 指人且作主语，用 who，所以选 C。", 1),
                ("fill", "This is the book ___ I bought yesterday.", None, "that", "先行词 book 指物，关系词作 bought 宾语可用 that，所以填 that。", 2),
                ("judge", "The man which teaches us maths is kind.", None, "F", "先行词 man 指人，应用 who 或 that，不能用 which，所以错。", 3),
                ("answer", "Write about a job you admire.", None, "A nurse who helps patients every day is my hero.", "要点：含先行词与 who 引导定语从句，句意完整即得分。", 4),
            ]},
            {"name": "一般现在时与一般过去时的被动语态", "explanation": "被动语态为 be + 过去分词；一般现在用 am/is/are done，一般过去用 was/were done，承受者作主语。", "questions": [
                ("choice", "The classroom ___ every day by students.", ["cleans", "cleaned", "is cleaning", "is cleaned"], "D", "主语是被打扫的对象，every day 用一般现在被动 is cleaned，所以选 D。", 1),
                ("fill", "These photos ___ taken in 2010.", None, "were", "photos 是复数，2010 表过去，被动用 were taken，所以填 were。", 2),
                ("judge", "The letter was wrote by my sister.", None, "F", "被动语态须用过去分词 written，wrote 是过去式，所以错。", 3),
                ("answer", "Describe how bread is made in one line.", None, "Bread is made from flour by bakers.", "要点：用一般现在被动 is/are done，语义合理即得分。", 4),
            ]},
            {"name": "职业名词后缀 -er、-or、-ist", "explanation": "动词加 -er/-or 表从业者，如 teach 变 teacher；-ist 表专家，如 art 变 artist；cook 是人，cooker 是厨具。", "questions": [
                ("choice", "A person who drives a bus is a ___.", ["drive", "driver", "driving", "driven"], "B", "表从业者用名词后缀 -er，driver 正确，所以选 B。", 1),
                ("fill", "My aunt is a ___; she studies stars.", None, "scientist", "研究星星的是科学家，-ist 表专家，所以填 scientist。", 2),
                ("judge", "A cooker is someone who cooks meals.", None, "F", "cook 才是厨师，cooker 指炊具锅具，所以说法错误。", 3),
                ("answer", "Name two jobs ending with -er or -or.", None, "teacher, doctor", "要点：写出两个带 -er/-or 的职业名词，拼写正确即得分。", 4),
            ]},
            {"name": "反意疑问句的构成与回答", "explanation": "反意疑问句前肯后否、前否后肯，助动词与前句一致、主语用代词；回答按事实，前后须一致。", "questions": [
                ("choice", "She works in a hospital, ___?", ["doesn't she", "does she", "isn't she", "didn't she"], "A", "前句肯定且动词 works，附加疑问用 doesn't she，所以选 A。", 1),
                ("fill", "They have never been there, ___?", None, "have they", "never 表否定，前否后肯，助动词 have 提前，所以填 have they。", 2),
                ("judge", "He can swim, can't he? Yes, he can't.", None, "F", "回答须前后一致，事实肯定应说 Yes, he can，所以错。", 3),
                ("answer", "Add a tag question to: You like tea.", None, "You like tea, don't you?", "要点：前肯后否、助动词 do 与主语 you 一致，即得分。", 4),
            ]},
        ]},
        {"name": "Unit 3 Travellers' tales", "summary": "围绕旅行故事，练过去完成时、时间状语从句、间接引语与旅行词汇辨析。", "points": [
            {"name": "过去完成时 had done 的用法", "explanation": "过去完成时 had + 过去分词，表过去某时之前已完成的动作；常与 when、before、by the time、already 连用。", "questions": [
                ("choice", "When we arrived, the train ___.", ["left", "has left", "had left", "leaves"], "C", "火车离开发生在到达之前，用过去完成时 had left，所以选 C。", 1),
                ("fill", "By the time I got up, he ___ gone.", None, "had", "got up 是过去，动身更早用过去完成时 had gone，所以填 had。", 2),
                ("judge", "She had finished her trip before 2019.", None, "T", "before 加过去时间，先完成用过去完成时，时态与搭配正确，所以对。", 3),
                ("answer", "Write about a trip you had planned before.", None, "I had booked the tickets before we set off.", "要点：用 had done 表更早完成，时间关系清楚即得分。", 4),
            ]},
            {"name": "时间状语从句 when、while、as soon as", "explanation": "when 可接点或段动作，while 接延续动作，as soon as 表一……就；主句将来时从句用一般现在表将来。", "questions": [
                ("choice", "I will call you ___ I arrive.", ["while", "until", "because", "as soon as"], "D", "主句用 will，从句用一般现在表将来，一到达就打用 as soon as，所以选 D。", 1),
                ("fill", "___ I was reading, my friend called.", None, "While", "从句是延续动作 was reading，用 While 引导，所以填 While。", 2),
                ("judge", "I'll tell him when he will come back.", None, "F", "时间状语从句中不用 will，须用一般现在 comes 表将来，所以错。", 3),
                ("answer", "Write a line about a travel plan.", None, "As soon as we reach the hotel, we will rest.", "要点：主将从现，含时间状语从句且语义合理即得分。", 4),
            ]},
            {"name": "间接引语中的时态与人称变化", "explanation": "转述他人话时，主句过去则从句时态后移，人称与时间状语相应变化；陈述句用 that，疑问句用 if 或疑问词。", "questions": [
                ("choice", "He said he ___ tired that day.", ["is", "was", "has been", "will be"], "B", "主句是过去时，从句时态须后移为 was，所以选 B。", 1),
                ("fill", "She asked me where I ___ the ticket.", None, "had bought", "主句 asked 是过去，买票更早用过去完成时，所以填 had bought。", 2),
                ("judge", "Tom said that the view is beautiful.", None, "F", "主句 said 为过去，从句 is 应后移为 was，所以说法错误。", 3),
                ("answer", "Report: 'I will visit the museum.'", None, "She said she would visit the museum.", "要点：will 后移为 would、人称相应变化，转述正确即得分。", 4),
            ]},
            {"name": "旅行名词 journey、trip、travel 的辨析", "explanation": "journey 指较长陆路旅程，trip 指短途往返出行，travel 泛指旅行行为或作动词；take a trip 是常见搭配。", "questions": [
                ("choice", "We took a short ___ to the island.", ["trip", "journey", "travel", "tour"], "A", "短途往返用 trip，take a trip 是固定搭配，所以选 A。", 1),
                ("fill", "The ___ across the desert took a week.", None, "journey", "漫长陆路旅程用 journey，搭配 take 表耗时，所以填 journey。", 2),
                ("judge", "Travel is a countable noun for one tour.", None, "F", "travel 泛指旅行、通常不可数，一次出行应用 trip，所以错。", 3),
                ("answer", "Write a caption for a travel photo.", None, "A wonderful trip to Guilin last summer.", "要点：含旅行名词与时间，短语表意清楚即得分。", 4),
            ]},
        ]},
        {"name": "Unit 4 Folk customs", "summary": "围绕民俗，练情态被动、非谓语、节日介词与阅读推断，并写习俗介绍。", "points": [
            {"name": "含情态动词的被动语态", "explanation": "情态被动结构为 情态动词 + be + 过去分词，如 must be done、can be seen；否定在情态动词后加 not。", "questions": [
                ("choice", "Lanterns ___ hung before the festival.", ["must be", "must", "have", "are must"], "A", "灯笼被挂起是被动，情态动词后用 be done，所以选 must be。", 1),
                ("fill", "The old custom can still ___ seen today.", None, "be", "情态动词 can 后被动须接 be 加过去分词，所以填 be。", 2),
                ("judge", "Zongzi must be ate on that day.", None, "F", "被动须用过去分词 eaten，ate 是过去式，所以说法错误。", 3),
                ("answer", "Write a rule for a folk custom.", None, "Red paper must be put on the door before spring.", "要点：用情态动词加 be done 表被动规则，语义合理即得分。", 4),
            ]},
            {"name": "动名词与不定式作宾语", "explanation": "enjoy、finish、avoid、practise 后接动名词；want、decide、hope、plan 后接不定式；stop doing 与 stop to do 意义不同。", "questions": [
                ("choice", "People enjoy ___ mooncakes together.", ["to eat", "eat", "eating", "ate"], "C", "enjoy 后只接动名词 eating，所以选 C。", 1),
                ("fill", "They decided ___ a dragon boat race.", None, "to hold", "decide 后接不定式 to do，所以填 to hold。", 2),
                ("judge", "We finished to clean the hall.", None, "F", "finish 后须接动名词 cleaning，不能用不定式，所以错。", 3),
                ("answer", "Write about a custom you plan to try.", None, "I plan to learn paper cutting this winter.", "要点：plan 后接 to do，写出具体习俗活动即得分。", 4),
            ]},
            {"name": "节日名词与介词 at、on 的搭配", "explanation": "整个节期用 at，具体某一天用 on；如 at the Spring Festival、on Mid-Autumn Day，celebrate、tradition、relative 为高频词。", "questions": [
                ("choice", "Families reunite ___ the Spring Festival.", ["in", "on", "for", "at"], "D", "整个节期用 at the Spring Festival，所以选 D。", 1),
                ("fill", "People watch the moon ___ Mid-Autumn Day.", None, "on", "具体某一天用介词 on，所以填 on。", 2),
                ("judge", "We give red packets in New Year's Day.", None, "F", "具体节日当天用 on 加节日名，不用 in，所以说法错误。", 3),
                ("answer", "Name one custom and its festival.", None, "We eat zongzi at the Dragon Boat Festival.", "要点：习俗与节日对应正确，介词使用准确即得分。", 4),
            ]},
            {"name": "阅读中推断词义与主旨", "explanation": "读民俗短文可借上下文同义、举例与转折词推断生词；主旨常在首末句，细节题须回原文定位。", "questions": [
                ("choice", "In 'a yearly custom', yearly means ___.", ["every day", "every year", "once", "never"], "B", "custom 与按年重复提示，yearly 意为每年，所以选 B。", 1),
                ("fill", "A paragraph explains why; it gives a ___.", None, "reason", "解释为何庆祝即给出原因，所以填 reason。", 2),
                ("judge", "However signals a contrast in a text.", None, "T", "however 是转折信号词，提示前后内容相反，所以对。", 3),
                ("answer", "Write a topic sentence about a custom.", None, "The Dragon Boat Festival has a long history in China.", "要点：能概括全段主题、句子完整即得分。", 4),
            ]},
        ]},
        {"name": "Unit 5 Buildings", "summary": "围绕建筑，练被动语态、比较等级、方位说明与 where 引导的定语从句。", "points": [
            {"name": "完成时与过去时的被动语态", "explanation": "完成时态被动为 have/has been done，一般过去被动为 was/were done；说明建筑被建造时间常用被动。", "questions": [
                ("choice", "The bridge ___ built last century.", ["has", "was", "is", "had"], "B", "last century 是明确过去时间，用一般过去被动 was built，所以选 B。", 1),
                ("fill", "This tower has ___ repaired twice.", None, "been", "has been done 是现在完成被动，所以填 been。", 2),
                ("judge", "The wall can be saw from far away.", None, "F", "被动须用过去分词 seen，saw 是过去式，所以说法错误。", 3),
                ("answer", "Describe a building in passive voice.", None, "The library was built of stone in 1920.", "要点：用 be done 说明建造材料与时间，句子正确即得分。", 4),
            ]},
            {"name": "形容词比较级与最高级", "explanation": "单音节加 -er/-est，多音节用 more/most；than 前用比较级，the 加范围用最高级；不规则如 good-better-best。", "questions": [
                ("choice", "This tower is ___ than that one.", ["taller", "tallest", "tall", "more tall"], "A", "than 前用比较级，tall 的比较级是 taller，所以选 A。", 1),
                ("fill", "It is the ___ building in the city.", None, "tallest", "the 加范围 in the city 用最高级，所以填 tallest。", 2),
                ("judge", "This hall is more bigger than ours.", None, "F", "bigger 已是比较级，不能再加 more，所以说法错误。", 3),
                ("answer", "Compare two buildings in one line.", None, "The new museum is taller than the old library.", "要点：用比较级加 than，比较对象清楚即得分。", 4),
            ]},
            {"name": "说明文写作中的方位与顺序表达", "explanation": "介绍建筑按空间或逻辑顺序，用 in front of、next to、on the second floor、above 等方位词，使读者能还原位置。", "questions": [
                ("choice", "The gate is ___ front of the hall.", ["on", "at", "in", "to"], "C", "in front of 是固定方位短语，所以选 C。", 1),
                ("fill", "The shop is next ___ the old bridge.", None, "to", "next to 是固定搭配，表紧邻，所以填 to。", 2),
                ("judge", "A description may list rooms at random.", None, "F", "说明文须按空间或逻辑顺序，随意罗列让读者混乱，所以错。", 3),
                ("answer", "Write a line locating a school library.", None, "The library is on the second floor, next to the lab.", "要点：含准确方位短语，位置可还原即得分。", 4),
            ]},
            {"name": "定语从句中 where 与 which 的选择", "explanation": "先行词是地点且从句缺状语用 where，缺主语或宾语用 which 或 that；判断关键看从句成分是否完整。", "questions": [
                ("choice", "This is the museum ___ we met.", ["which", "who", "what", "where"], "D", "从句 we met 成分完整、缺地点状语，用 where，所以选 D。", 1),
                ("fill", "The house ___ stands by the river is old.", None, "that", "从句缺主语、先行词指物，用 that 引导，所以填 that。", 2),
                ("judge", "The park where we visited is lovely.", None, "F", "visited 缺宾语，应用 which 或 that，where 只作状语，所以错。", 3),
                ("answer", "Describe a place you often visit.", None, "The park where I read every Sunday is quiet.", "要点：含地点先行词与 where 从句，语义完整即得分。", 4),
            ]},
        ]},
        {"name": "Unit 6 Pollution", "summary": "围绕污染，练条件状语从句、非谓语、词族辨析与议论文观点表达。", "points": [
            {"name": "条件状语从句 if 与主将从现", "explanation": "if 引导条件状语从句，主句用将来时或情态动词时从句用一般现在表将来；unless 相当于 if not。", "questions": [
                ("choice", "If we ___ waste, the river gets cleaner.", ["reduce", "will reduce", "reduced", "reducing"], "A", "主句表将来结果，if 从句用一般现在 reduce，所以选 A。", 1),
                ("fill", "We will suffer ___ we protect the air.", None, "unless", "句意是若不保护空气就会受害，unless 表 if not，所以填 unless。", 2),
                ("judge", "If it will rain, we will stay home.", None, "F", "条件从句不能用 will，须用一般现在 rains 表将来，所以错。", 3),
                ("answer", "Write a tip to reduce pollution.", None, "If we ride bikes more, the air will be cleaner.", "要点：含 if 条件句且主将从现，建议可行即得分。", 4),
            ]},
            {"name": "非谓语动词作主语与目的状语", "explanation": "动名词或不定式可作主语，谓语用单数；to do 常表目的；现在分词表主动，过去分词表被动。", "questions": [
                ("choice", "___ water is important for everyone.", ["Save", "Saved", "Saving", "To saving"], "C", "动名词作主语用 Saving，谓语用单数 is，所以选 C。", 1),
                ("fill", "We plant trees ___ keep the air clean.", None, "to", "表目的用不定式 to keep，所以填 to。", 2),
                ("judge", "Recycle paper help cut down waste.", None, "F", "动名词作主语谓语须用单数 helps，所以说法错误。", 3),
                ("answer", "Write a slogan against pollution.", None, "To keep our city green, we should save every drop.", "要点：含不定式表目的，号召明确即得分。", 4),
            ]},
            {"name": "pollute、pollution、polluted 词族辨析", "explanation": "pollute 是动词，pollution 是不可数名词，polluted 是形容词或过去分词；air/water/noise pollution 为常见搭配。", "questions": [
                ("choice", "Air ___ is a serious problem today.", ["pollute", "pollution", "polluted", "polluting"], "B", "作主语须用名词 pollution，air pollution 是固定搭配，所以选 B。", 1),
                ("fill", "Factories must not ___ the river.", None, "pollute", "must not 后接动词原形，所以填 pollute。", 2),
                ("judge", "The polluting water smells terrible.", None, "F", "表被污染的水应用 polluted，polluting 表主动污染，所以错。", 3),
                ("answer", "Name two kinds of pollution.", None, "noise pollution, water pollution", "要点：写出两种污染类型，名词形式拼写正确即得分。", 4),
            ]},
            {"name": "议论文写作中表达观点与理由", "explanation": "提出观点用 I think 或 In my opinion，给理由用 because、firstly、besides，结尾用 so 或 in short 总结，理由须具体。", "questions": [
                ("choice", "___ my opinion, rubbish should be sorted.", ["In", "On", "At", "For"], "A", "in my opinion 是固定短语，所以选 A。", 1),
                ("fill", "We should save water ___ it is limited.", None, "because", "后句给出原因，用 because 连接，所以填 because。", 2),
                ("judge", "Firstly and besides can order reasons.", None, "T", "firstly 列第一点、besides 补充理由，都可组织论据，所以对。", 3),
                ("answer", "Give one reason to ban plastic bags.", None, "Because they pollute soil and harm sea animals.", "要点：用表原因的连接词，理由具体可核对即得分。", 4),
            ]},
        ]},
    ],
}

# 章末综合情境题：每章 2 道，使每章题量达到 18 道，挂在本章已有知识点上。
_REVIEW_Q = {
    "Unit 1 Teenage life": [
        (0, ("choice", "I ___ in this school for three years.", ["lived", "have lived", "live", "am living"], "B", "for three years 是时间段，用现在完成时 have lived，所以选 B。", 3)),
        (3, ("answer", "Write two lines about a teenage change.", None, "I used to be quiet, but now I have made many friends.", "要点：含 used to 与现在完成时，两句语义连贯即得分。", 4)),
    ],
    "Unit 2 People and their jobs": [
        (0, ("choice", "The nurse ___ cares for grandma is kind.", ["which", "who", "whose", "what"], "B", "先行词 nurse 指人，用 who 引导定语从句，所以选 B。", 3)),
        (1, ("answer", "Write about a worker using passive voice.", None, "The streets are cleaned by workers early every morning.", "要点：用一般现在被动与人称合理的职业情境，句子正确即得分。", 4)),
    ],
    "Unit 3 Travellers' tales": [
        (0, ("choice", "When we got there, it ___ raining.", ["stops", "has stopped", "will stop", "had stopped"], "D", "雨停在到达之前，先发生用过去完成时 had stopped，所以选 D。", 3)),
        (1, ("answer", "Write two lines about a travel memory.", None, "We had packed before dawn and left as soon as it was light.", "要点：含过去完成时与时间状语从句，叙事连贯即得分。", 4)),
    ],
    "Unit 4 Folk customs": [
        (0, ("choice", "Gifts ___ be given to elders at New Year.", ["are", "have", "were", "should"], "D", "含情态动词的被动用 should be done，所以选 D。", 3)),
        (1, ("answer", "Write two lines about a folk custom.", None, "At the festival, people enjoy making lanterns together.", "要点：含动名词与节日介词，表意连贯即得分。", 4)),
    ],
    "Unit 5 Buildings": [
        (0, ("choice", "The temple ___ in 1600 still stands.", ["built", "building", "builds", "was built"], "A", "过去分词作后置定语表被动，所以选 built。", 3)),
        (1, ("answer", "Write a caption for a famous building.", None, "The tallest tower in the city was built of stone long ago.", "要点：含最高级与被动语态，表意清楚即得分。", 4)),
    ],
    "Unit 6 Pollution": [
        (0, ("choice", "If everyone ___ less, waste will drop.", ["will throw", "threw", "throws away", "throwing"], "C", "主句将来时，if 从句用一般现在 throws away，所以选 C。", 3)),
        (1, ("answer", "Write a two-line call to protect rivers.", None, "To keep rivers clean, we must stop dumping waste into them.", "要点：含不定式表目的与环保动词，号召具体即得分。", 4)),
    ],
}
for _ch in PACK["chapters"]:
    for _idx, _q in _REVIEW_Q[_ch["name"]]:
        _ch["points"][_idx]["questions"].append(_q)
