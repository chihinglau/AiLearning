# -*- coding: utf-8 -*-
"""重跑内容包：英语 四年级上册（牛津深圳版），pack english_g4。
按骨架索引 8 个单元建立节级知识点，每点 4 题，另补章末综合情境题各 2 题。
题干与选项用英文、解析用中文，覆盖真实词汇、句型、语音与交际情境。"""
PACK = {
    "subject": "english", "grade": 4, "version": "牛津深圳版", "semester": "first",
    "chapters": [
        {"name": "Unit 1 Where do people live?", "summary": "学习住所与房屋部位名词，用 There is/There are 和 Where do you live? 介绍住处，并辨认 ar 与 a-e 的读音。", "points": [
            {"name": "认读住所名词 flat、house、village、city", "explanation": "flat 是公寓，house 是独栋房子，village 是村庄，city 是城市，四个词都表示住处。", "questions": [
                ("choice", "Which word is a home?", ["A bus", "A flat", "A cake", "A tree"], "B", "flat 是住房，其余是车、食物、树，所以选 B。", 1),
                ("fill", "I ___ in a flat with my family.", None, ["live"], "主语 I 后用动词原形 live 表示居住，填 live。", 2),
                ("judge", "A village is bigger than a city.", None, "F", "city 城市远大于 village 村庄，说法相反，所以 F。", 3),
                ("answer", "Write about your home in English.", None, "I live in a flat in a city.", "写出 I live in 加住所得 2 分；名词正确得 2 分。", 4),
            ]},
            {"name": "用 There is / There are 描述房屋", "explanation": "单数用 There is，复数用 There are；描述房间数量时按单复数选 is 或 are。", "questions": [
                ("choice", "___ a garden near my flat.", ["There are", "There have", "There is", "It has"], "C", "a garden 单数用 There is，其余搭配不对，所以选 C。", 1),
                ("fill", "There ___ three bedrooms here.", None, ["are"], "three bedrooms 是复数，be 动词用 are，填 are。", 2),
                ("judge", "There are a lift in this building.", None, "F", "a lift 是单数，应说 There is a lift，所以 F。", 3),
                ("answer", "Write: two things in your flat.", None, "There is a kitchen. There are two bedrooms.", "用 There is/are 各写一句得 2 分；单复数一致得 2 分。", 4),
            ]},
            {"name": "用 Where do you live 问答与介词 in、on", "explanation": "问住处用 Where do you live?，答 I live in a flat；城市用 in，农场用 on。", "questions": [
                ("choice", "___ do you live? In a flat.", ["Where", "What", "Who", "How"], "A", "答语是地点，问地点用 Where，其余疑问词不合，所以选 A。", 1),
                ("fill", "I live ___ the fifth floor.", None, ["on"], "表示在第几层楼用介词 on，填 on。", 2),
                ("judge", "We say I live in a farm.", None, "F", "农场前用 on a farm，不用 in，所以 F。", 3),
                ("answer", "Ask your friend where he lives.", None, "Where do you live?", "用 Where do you live? 提问得 2 分；疑问词正确得 2 分。", 4),
            ]},
            {"name": "辨认 ar 与 a-e 的发音", "explanation": "ar 常读 /ɑː/，如 car、park；a-e 常读 /eɪ/，如 name、cake。听音辨词要看字母组合。", "questions": [
                ("choice", "Which word has /ɑː/?", ["Cake", "Name", "Gate", "Car"], "D", "car 里 ar 读 /ɑː/，其余 a-e 读 /eɪ/，所以选 D。", 1),
                ("fill", "Park and card both have ___ sound.", None, ["/ɑː/"], "park 与 card 的 ar 都读 /ɑː/，填此音标。", 2),
                ("judge", "Name and game rhyme with cat.", None, "F", "name、game 读 /eɪ/，cat 读 /æ/，不押韵，所以 F。", 3),
                ("answer", "Write two words with /eɪ/ sound.", None, "Cake and name.", "写出两个 a-e 发 /eɪ/ 的词各得 2 分。", 4),
            ]},
        ]},
        {"name": "Unit 2 Where do animals live?", "summary": "学习动物栖息地名词，用 Where does a ... live? 与介词 in、on、near 描述位置，辨认 oo 长短音。", "points": [
            {"name": "认读栖息地名词 forest、river、cave、sea", "explanation": "forest 森林、river 河流、cave 洞穴、sea 海都是动物住处，位置常用 in、near 说明。", "questions": [
                ("choice", "Which is a home for a bird?", ["A shoe", "A cup", "A nest", "A road"], "C", "nest 是鸟巢，其余都不是动物住所，所以选 C。", 1),
                ("fill", "A fish lives ___ a river.", None, ["in"], "鱼生活在河里，用介词 in，填 in。", 2),
                ("judge", "A camel lives on the ice.", None, "F", "camel 骆驼住在沙漠 desert，不在冰上，所以 F。", 3),
                ("answer", "Name one animal home in English.", None, "A nest in a tree.", "写出一个动物住所名词得 2 分；搭配合理得 2 分。", 4),
            ]},
            {"name": "用 Where does a 单数动物 live 提问", "explanation": "主语是单数动物时，用 does 提问，答语动词加 -s，如 It lives in a forest。", "questions": [
                ("choice", "Where ___ a panda live?", ["do", "does", "is", "are"], "B", "a panda 单数，助动词用 does，其余不配，所以选 B。", 1),
                ("fill", "It ___ in a forest.", None, ["lives"], "主语 It 后动词加 -s，填 lives。", 2),
                ("judge", "Where do a bee live is correct.", None, "F", "a bee 单数应用 does，且语序错，所以 F。", 3),
                ("answer", "Ask where an eagle lives.", None, "Where does an eagle live?", "用 does 提问得 2 分；主语与动词搭配对得 2 分。", 4),
            ]},
            {"name": "用 in、on、near 说动物位置", "explanation": "in 表示在里面，on 表示在表面，near 表示在附近；描述鸟、鱼、熊的位置时按实际关系选词。", "questions": [
                ("choice", "A bird sits ___ a tree.", ["in", "At sea", "In a cup", "On ice"], "A", "鸟在树里用 in a tree，其余场所不合理，所以选 A。", 1),
                ("fill", "A bear sleeps ___ a cave.", None, ["in"], "熊在洞穴里冬眠，用 in，填 in。", 2),
                ("judge", "A bee lives in a river.", None, "F", "蜜蜂住在花丛或蜂巢，不在河里，所以 F。", 3),
                ("answer", "Write where a bee lives.", None, "A bee lives near flowers.", "写出 bee 的住处得 2 分；介词使用正确得 2 分。", 4),
            ]},
            {"name": "辨认 oo 的长短音", "explanation": "oo 在 moon、zoo 里读长音 /uː/，在 book、foot 里读短音 /ʊ/；同是 oo，读音要按词记。", "questions": [
                ("choice", "Which word has short /ʊ/?", ["Moon", "Zoo", "Food", "Book"], "D", "book 里 oo 读短音 /ʊ/，其余读 /uː/，所以选 D。", 1),
                ("fill", "Moon and zoo share ___ sound.", None, ["/uː/"], "moon 与 zoo 的 oo 都读长音 /uː/，填此音标。", 2),
                ("judge", "Foot and food sound the same.", None, "F", "foot 读 /ʊ/，food 读 /uː/，元音不同，所以 F。", 3),
                ("answer", "Write two words with /uː/.", None, "Moon and zoo.", "写出两个 oo 读 /uː/ 的词各得 2 分。", 4),
            ]},
        ]},
        {"name": "Unit 3 How do we use numbers?", "summary": "学习 13 到 19 与整十数词，用 How many 问数量、读电话号码与价格，辨认 i-e 与 i 的读音。", "points": [
            {"name": "认读 13 到 19 与整十数词", "explanation": "13 到 19 多以 -teen 结尾，如 fourteen、fifteen；整十数以 -ty 结尾，如 twenty、fifty。", "questions": [
                ("choice", "Which word means 15?", ["Fifty", "Fifteen", "Fourteen", "Five"], "B", "15 是 fifteen，fifty 是 50，其余是 14 和 5，所以选 B。", 1),
                ("fill", "Ten and ten make ___.", None, ["twenty"], "10 加 10 等于 20，英文是 twenty，填 twenty。", 2),
                ("judge", "Thirteen is the same as thirty.", None, "F", "13 是 thirteen，30 是 thirty，读音与数值都不同，所以 F。", 3),
                ("answer", "Write the word for 18.", None, "Eighteen.", "写出 eighteen 得 2 分；拼写含 -teen 得 2 分。", 4),
            ]},
            {"name": "用 How many 问可数名词数量", "explanation": "问可数名词数量用 How many 加复数名词，答语用数词加名词，如 Six books。", "questions": [
                ("choice", "___ apples do you have?", ["How many", "How much", "How old", "How long"], "A", "apples 可数复数，问数量用 How many，其余疑问词不合，所以选 A。", 1),
                ("fill", "How many ___ are in a week?", None, ["days"], "一周有七天，how many 后接复数 days，填 days。", 2),
                ("judge", "How many milk is on the desk?", None, "F", "milk 不可数，应用 How much，所以 F。", 3),
                ("answer", "Count: write twelve plus three.", None, "Fifteen.", "算出 15 得 2 分；用英文数词 fifteen 得 2 分。", 4),
            ]},
            {"name": "读电话号码与价格", "explanation": "电话号码逐位读，0 可读 oh；价格用数词加 yuan，问价用 How much is it?", "questions": [
                ("choice", "How much is the pen? ___ ten yuan.", ["They're", "There", "It's", "I'm"], "C", "单数 the pen 用 It's 答价，其余主谓不配，所以选 C。", 1),
                ("fill", "My phone ___ is 8520 6611.", None, ["number"], "电话号码是 phone number，填 number。", 2),
                ("judge", "We read 0 as oh in a phone number.", None, "T", "电话号码里 0 常读作 oh，说法正确，所以 T。", 3),
                ("answer", "Say the price: 30 yuan, in English.", None, "It's thirty yuan.", "用 It's 加 yuan 得 2 分；thirty 拼写正确得 2 分。", 4),
            ]},
            {"name": "辨认 i-e 与 i 的发音", "explanation": "i-e 常读 /aɪ/，如 five、nine、bike；闭音节里单个 i 读 /ɪ/，如 sit、big、six。", "questions": [
                ("choice", "Which word has /aɪ/?", ["Big", "Sit", "Six", "Bike"], "D", "bike 里 i-e 读 /aɪ/，其余读 /ɪ/，所以选 D。", 1),
                ("fill", "Nine and five share ___ sound.", None, ["/aɪ/"], "nine 与 five 的 i-e 都读 /aɪ/，填此音标。", 2),
                ("judge", "Time and sit rhyme well.", None, "F", "time 读 /aɪ/，sit 读 /ɪ/，元音不同，所以 F。", 3),
                ("answer", "Write two words with /aɪ/.", None, "Nine and bike.", "写出两个 i-e 发 /aɪ/ 的词各得 2 分。", 4),
            ]},
        ]},
        {"name": "Unit 4 What do we buy?", "summary": "学习食物与日用品名词，用 How much is it? 问价、Can I help you? 购物交际，辨认 sh 与 ch。", "points": [
            {"name": "认读食物与日用品名词", "explanation": "bread 面包、milk 牛奶、juice 果汁是食品，shoes 鞋、socks 袜是衣物，购物按类别找货架。", "questions": [
                ("choice", "Which one can you drink?", ["Bread", "Socks", "Juice", "Rice"], "C", "juice 是果汁可喝，其余是食物或衣物，所以选 C。", 1),
                ("fill", "Mum buys ___ and bread.", None, ["milk"], "早餐常买牛奶和面包，填食品名词 milk。", 2),
                ("judge", "We can wear a bottle of juice.", None, "F", "juice 是喝的，不能穿，说法荒谬，所以 F。", 3),
                ("answer", "Write two things you can eat.", None, "Bread and apples.", "写出两个可食用名词各得 2 分。", 4),
            ]},
            {"name": "用 How much is it 问价与找零", "explanation": "问单价用 How much is it?，回答用 It's 加数词和 yuan；付钱后店员给的零钱叫 change。", "questions": [
                ("choice", "___ is the T-shirt? Ten yuan.", ["How much", "How many", "How old", "How big"], "A", "答语是价格，问价用 How much，其余疑问词不合，所以选 A。", 1),
                ("fill", "It ___ twenty yuan.", None, ["is"], "单数物品价格用 It is，缩写 It's，填 is。", 2),
                ("judge", "How much is your shoes?", None, "F", "shoes 复数应用 are，不用 is，所以 F。", 3),
                ("answer", "Ask the price of a bag.", None, "How much is the bag?", "用 How much is 提问得 2 分；单数一致得 2 分。", 4),
            ]},
            {"name": "用 Can I help you 购物交际", "explanation": "店员说 Can I help you?，顾客答 Yes, please；递东西说 Here you are。", "questions": [
                ("choice", "You want milk. You say: ___", ["I'm fine", "Sit down", "Good night", "Milk, please"], "D", "点牛奶说 Milk, please，其余不是购物用语，所以选 D。", 1),
                ("fill", "___ you are. Thank you!", None, ["Here"], "递东西给对方说 Here you are，填 Here。", 2),
                ("judge", "Can I help you? asks about age.", None, "F", "这句是店员提供帮助，不是问年龄，所以 F。", 3),
                ("answer", "Write a polite shop reply.", None, "Yes, please. I'd like some bread.", "用 Yes, please 应答得 2 分；说出所买物品得 2 分。", 4),
            ]},
            {"name": "辨认 sh 与 ch 的发音", "explanation": "sh 读 /ʃ/，如 ship、shop；ch 常读 /tʃ/，如 chair、cheese。两组起首辅音不同，别听混。", "questions": [
                ("choice", "Which word starts with /ʃ/?", ["Chair", "Ship", "Cheese", "Cheap"], "B", "ship 的 sh 读 /ʃ/，其余 ch 读 /tʃ/，所以选 B。", 1),
                ("fill", "Ship and shop share ___ sound.", None, ["/ʃ/"], "ship 与 shop 的 sh 都读 /ʃ/，填此音标。", 2),
                ("judge", "Chair and ship start the same.", None, "F", "chair 起音 /tʃ/，ship 起音 /ʃ/，不同，所以 F。", 3),
                ("answer", "Write two words with /tʃ/.", None, "Chair and cheese.", "写出两个 ch 发 /tʃ/ 的词各得 2 分。", 4),
            ]},
        ]},
        {"name": "Unit 5 How are the seasons different?", "summary": "学习四季与天气形容词，用 It's 和 Which season do you like? 描述季节，辨认 ea 与 ee。", "points": [
            {"name": "认读四季名词", "explanation": "一年有 spring 春、summer 夏、autumn 秋、winter 冬，说季节用 in spring。", "questions": [
                ("choice", "Which season has snow?", ["Winter", "Spring", "Summer", "Autumn"], "A", "winter 冬天下雪，其余季节不下雪，所以选 A。", 1),
                ("fill", "Flowers come out in ___.", None, ["spring"], "春天花开，季节名词用 spring，填 spring。", 2),
                ("judge", "Autumn comes before summer.", None, "F", "顺序是 summer 后 autumn，说法颠倒，所以 F。", 3),
                ("answer", "Write your favourite season.", None, "I like autumn best.", "写出季节名词得 2 分；句子完整得 2 分。", 4),
            ]},
            {"name": "用 It's 加天气形容词描述季节", "explanation": "描述天气用 It's 加形容词：hot、cold、warm、cool、rainy、snowy，主语 it 指天气。", "questions": [
                ("choice", "In summer it is very ___.", ["Cold", "Snowy", "Hot", "Icy"], "C", "夏天炎热用 hot，其余是冷天用语，所以选 C。", 1),
                ("fill", "It ___ rainy in spring.", None, ["is"], "主语 It 描述天气，be 动词用 is，填 is。", 2),
                ("judge", "We say it is snowy in summer.", None, "F", "夏天不下雪，snowy 属于冬天，所以 F。", 3),
                ("answer", "Describe today's weather.", None, "It is sunny and warm.", "用 It is 加天气词得 2 分；形容词正确得 2 分。", 4),
            ]},
            {"name": "用 Which season do you like 表达喜好", "explanation": "问喜好用 Which season do you like?，答语用 I like 加季节名，再用 because 给理由。", "questions": [
                ("choice", "___ season do you like? Winter.", ["How much", "Which", "How many", "Where"], "B", "在特定范围选一个用 Which，其余疑问词不合，所以选 B。", 1),
                ("fill", "I like summer ___ I can swim.", None, ["because"], "后半句说明原因，连词用 because，填 because。", 2),
                ("judge", "Which season you like is correct.", None, "F", "疑问句要加助动词 do，语序应为 do you like，所以 F。", 3),
                ("answer", "Ask which season Ben likes.", None, "Which season do you like, Ben?", "用 Which season 提问得 2 分；助动词 do 正确得 2 分。", 4),
            ]},
            {"name": "辨认 ea 与 ee 的发音", "explanation": "ee 读 /iː/，如 see、green；ea 在 sea、tea 里也读 /iː/，在 head 里读 /e/。", "questions": [
                ("choice", "Which word has /e/?", ["Sea", "Tea", "Green", "Head"], "D", "head 里 ea 读 /e/，其余读 /iː/，所以选 D。", 1),
                ("fill", "See and green share ___ sound.", None, ["/iː/"], "see 与 green 都读长音 /iː/，填此音标。", 2),
                ("judge", "Sea and head sound the same.", None, "F", "sea 读 /iː/，head 读 /e/，元音不同，所以 F。", 3),
                ("answer", "Write two words with /iː/.", None, "Tea and sea.", "写出两个读 /iː/ 的词各得 2 分。", 4),
            ]},
        ]},
        {"name": "Unit 6 What's amazing about plants?", "summary": "学习植物部位名词，用 Plants need 与 It has/They have 描述植物，辨认 ow 与 ou。", "points": [
            {"name": "认读植物部位名词", "explanation": "root 根、stem 茎、leaf 叶、flower 花、seed 种子、fruit 果实；根在土里，花果在地上。", "questions": [
                ("choice", "Which part is under the soil?", ["Root", "Flower", "Leaf", "Fruit"], "A", "root 根长在土下，其余部位在地上，所以选 A。", 1),
                ("fill", "A small ___ grows into a plant.", None, ["seed"], "种子 seed 发芽长成植株，填 seed。", 2),
                ("judge", "The stem carries water to leaves.", None, "T", "茎 stem 把水送到叶子，说法正确，所以 T。", 3),
                ("answer", "Name two parts of a plant.", None, "A stem and a leaf.", "写出两个部位名词各得 2 分。", 4),
            ]},
            {"name": "用 Plants need 说生长需求", "explanation": "植物需要 water、sunlight、soil、air，用 Plants need 加名词表达，need 后接名词。", "questions": [
                ("choice", "Plants need ___ to make food.", ["A shoe", "A book", "Sunlight", "Money"], "C", "植物靠 sunlight 造养分，其余无关，所以选 C。", 1),
                ("fill", "Plants ___ water and air.", None, ["need"], "主语 Plants 复数，动词用原形 need，填 need。", 2),
                ("judge", "A plant grows well with no water.", None, "F", "缺水植物会枯萎，不能长好，所以 F。", 3),
                ("answer", "Write what a seed needs.", None, "It needs water and sunlight.", "写出水与阳光各得 2 分；need 用法正确得 1 分。", 4),
            ]},
            {"name": "用 It has / They have 描述植物", "explanation": "单数用 It has，复数用 They have；描述叶子和花瓣数量时按主语单复数选词。", "questions": [
                ("choice", "A sunflower ___ yellow flowers.", ["have", "has", "is", "are"], "B", "主语单数 A sunflower 用 has，其余不配，所以选 B。", 1),
                ("fill", "Trees ___ many leaves.", None, ["have"], "主语 Trees 复数，动词用 have，填 have。", 2),
                ("judge", "It have green leaves is correct.", None, "F", "主语 It 单数应用 has，不用 have，所以 F。", 3),
                ("answer", "Write: what does a tree have?", None, "It has a stem and many leaves.", "用 It has 描述得 2 分；部位名词正确得 2 分。", 4),
            ]},
            {"name": "辨认 ow 与 ou 的发音", "explanation": "ow 读 /aʊ/（cow）或 /əʊ/（slow）；ou 常读 /aʊ/（house、out），读音要按词记。", "questions": [
                ("choice", "Which word has /aʊ/?", ["Slow", "Yellow", "Window", "Cow"], "D", "cow 里 ow 读 /aʊ/，其余读 /əʊ/，所以选 D。", 1),
                ("fill", "House and out share ___ sound.", None, ["/aʊ/"], "house 与 out 的 ou 都读 /aʊ/，填此音标。", 2),
                ("judge", "Slow and cow sound the same.", None, "F", "slow 读 /əʊ/，cow 读 /aʊ/，不同，所以 F。", 3),
                ("answer", "Write two words with /əʊ/.", None, "Slow and yellow.", "写出两个 ow 读 /əʊ/ 的词各得 2 分。", 4),
            ]},
        ]},
        {"name": "Unit 7 How do we keep safe on the road?", "summary": "学习交通设施与规则名词，用 must/mustn't 与祈使句说安全规则，辨认 ay 与 ai。", "points": [
            {"name": "认读交通设施与规则名词", "explanation": "认读 traffic lights、zebra crossing、pavement、helmet 等交通安全词。", "questions": [
                ("choice", "Where do we cross the road?", ["A bus", "A tree", "A crossing", "A shop"], "C", "过街走斑马线 a crossing，其余场所不合，所以选 C。", 1),
                ("fill", "Walk on the ___, not the road.", None, ["pavement"], "行人走人行道 pavement，填 pavement。", 2),
                ("judge", "A helmet keeps your head safe.", None, "T", "骑车戴头盔保护头部，说法正确，所以 T。", 3),
                ("answer", "Name two things on a road.", None, "Traffic lights and a crossing.", "写出两个交通设施名词各得 2 分。", 4),
            ]},
            {"name": "用 must / mustn't 与祈使句说规则", "explanation": "必须做用 must，禁止做用 mustn't 或 Don't 加动词原形；否定祈使句以 Don't 开头。", "questions": [
                ("choice", "We ___ stop at a red light.", ["mustn't", "must", "don't", "can't"], "B", "红灯必须停用 must，mustn't 表禁止，所以选 B。", 1),
                ("fill", "___ run on the road.", None, ["Don't"], "禁止在马路上跑，否定祈使句用 Don't，填 Don't。", 2),
                ("judge", "We mustn't wear a seat belt.", None, "F", "乘车必须系安全带，不能禁止，所以 F。", 3),
                ("answer", "Write one road rule with must.", None, "We must wait for the green light.", "用 We must 得 2 分；规则内容安全得 2 分。", 4),
            ]},
            {"name": "过街的 stop、look、go 交际指令", "explanation": "过街前说 Look left and right，绿灯亮才走；提醒同伴用 Wait! 或 Stop!，按停看行三步做。", "questions": [
                ("choice", "Green light means we can ___.", ["Go", "Stop", "Wait", "Hide"], "A", "绿灯行用 go，红灯才 stop，其余动作不合，所以选 A。", 1),
                ("fill", "___ left and right before you cross.", None, ["Look"], "过街前左右看，祈使句用 Look，填 Look。", 2),
                ("judge", "Wait! is a word to warn a friend.", None, "T", "Wait! 用来提醒同伴停下，说法正确，所以 T。", 3),
                ("answer", "Write two steps to cross safely.", None, "Stop, look left and right, then go.", "写出停与看两步各得 2 分；顺序合理得 1 分。", 4),
            ]},
            {"name": "辨认 ay 与 ai 的发音", "explanation": "ay 常在词尾读 /eɪ/（day、play），ai 常在词中读 /eɪ/（rain、train）；位置不同读音相同。", "questions": [
                ("choice", "Which word has /eɪ/ in the middle?", ["Day", "Play", "May", "Rain"], "D", "rain 的 ai 在词中读 /eɪ/，其余 ay 在词尾，所以选 D。", 1),
                ("fill", "Day and play share ___ sound.", None, ["/eɪ/"], "day 与 play 的 ay 都读 /eɪ/，填此音标。", 2),
                ("judge", "Train and may rhyme well.", None, "T", "两词都含 /eɪ/，押韵，说法正确，所以 T。", 3),
                ("answer", "Write two words with ai.", None, "Rain and train.", "写出两个含 ai 发 /eɪ/ 的词各得 2 分。", 4),
            ]},
        ]},
        {"name": "Unit 8 What do our grandparents do?", "summary": "学习祖父母日常活动动词，掌握第三人称单数 -s/-es 与 What does ... do?，辨认 o-e 与 o。", "points": [
            {"name": "认读日常活动动词短语", "explanation": "cook 做饭、garden 种花、read 读报、walk 散步、tell stories 讲故事都是日常活动。", "questions": [
                ("choice", "Growing flowers is called ___.", ["Read", "Fish", "Garden", "Cook"], "C", "种花叫 garden 园艺，其余是别的活动，所以选 C。", 1),
                ("fill", "Grandpa likes to ___ stories.", None, ["tell"], "讲故事是 tell stories，填动词 tell。", 2),
                ("judge", "Read a book means singing a song.", None, "F", "read a book 是读书，不是唱歌，所以 F。", 3),
                ("answer", "Write two things grandpa does.", None, "He reads and walks every day.", "写出两个活动动词各得 2 分。", 4),
            ]},
            {"name": "第三人称单数动词加 -s / -es", "explanation": "主语 He、She 是第三人称单数，动词加 -s 或 -es，如 cooks、goes、watches。", "questions": [
                ("choice", "Grandpa ___ the paper every day.", ["Read", "Reads", "Reading", "Are reading"], "B", "主语第三人称单数，动词加 -s 用 reads，所以选 B。", 1),
                ("fill", "She ___ to the park each morning.", None, ["goes"], "主语 She，go 的第三人称单数是 goes，填 goes。", 2),
                ("judge", "He cook dinner is correct English.", None, "F", "主语 He 后动词应为 cooks，所以 F。", 3),
                ("answer", "Write: grandma walks. Change to I.", None, "I walk every morning.", "主语换成 I 得 2 分；动词去 -s 得 2 分。", 4),
            ]},
            {"name": "用 What does your grandpa do 问答", "explanation": "问祖父母日常用 What does your grandpa do?，答 He 加动词 -s；does 后动词回原形。", "questions": [
                ("choice", "___ does your grandma do?", ["What", "Where", "Who", "How much"], "A", "问做什么活动用 What 加 do，其余疑问词不合，所以选 A。", 1),
                ("fill", "What ___ your grandpa do?", None, ["does"], "主语第三人称单数，疑问句助动词用 does，填 does。", 2),
                ("judge", "What does he do? He cook.", None, "F", "答语动词应为 cooks，与 does 问句一致，所以 F。", 3),
                ("answer", "Ask about grandma's morning.", None, "What does your grandma do in the morning?", "用 What does 引导提问得 2 分；主语正确得 2 分。", 4),
            ]},
            {"name": "辨认 o-e 与 o 的发音", "explanation": "o-e 常读 /əʊ/，如 note、home、rose；闭音节 o 读 /ɒ/，如 dog、box、hot、hop。", "questions": [
                ("choice", "Which word has /əʊ/?", ["Dog", "Box", "Hot", "Note"], "D", "note 的 o-e 读 /əʊ/，其余读 /ɒ/，所以选 D。", 1),
                ("fill", "Home and rose share ___ sound.", None, ["/əʊ/"], "home 与 rose 的 o-e 都读 /əʊ/，填此音标。", 2),
                ("judge", "Hop and hope sound the same.", None, "F", "hop 读 /ɒ/，hope 读 /əʊ/，元音不同，所以 F。", 3),
                ("answer", "Write two words with /ɒ/.", None, "Dog and box.", "写出两个 o 读 /ɒ/ 的词各得 2 分。", 4),
            ]},
        ]},
    ],
}

# 章末综合情境题：每章 2 道，使每章正好 18 题，挂在本章已有知识点上。
_REVIEW_Q = {
    "Unit 1 Where do people live?": [
        (0, ("choice", "Ben lives on a farm. Where is it?", ["In a lift", "In a village", "In a bank", "In a cave"], "B", "farm 在乡村，village 最贴切，其余场所不合，所以选 B。", 3)),
        (2, ("judge", "I live in a flat on a farm.", None, "F", "flat 在楼里用 in，农场用 on，两句混搭矛盾，所以 F。", 4)),
    ],
    "Unit 2 Where do animals live?": [
        (0, ("choice", "A penguin lives on cold ice. Where?", ["A desert", "A forest", "The sea ice", "A nest"], "C", "企鹅住海冰，sea ice 最合，其余是沙漠森林鸟巢，所以选 C。", 3)),
        (1, ("answer", "Write: Where does a fish live?", None, "It lives in a river.", "用 It lives in 加地点作答得 2 分；动词加 -s 得 2 分。", 4)),
    ],
    "Unit 3 How do we use numbers?": [
        (0, ("choice", "Cake 15 yuan, milk 5. How much?", ["Fifteen", "Twenty yuan", "Fifty yuan", "Ten yuan"], "B", "15 加 5 得 20，即 twenty yuan，其余金额不对，所以选 B。", 3)),
        (2, ("judge", "Ten yuan plus five yuan is fifty.", None, "F", "10 加 5 得 15 fifteen，不是 50，所以 F。", 4)),
    ],
    "Unit 4 What do we buy?": [
        (0, ("choice", "50 yuan, bread 8 yuan. Change?", ["Fifty yuan", "Eight yuan", "Forty two", "Fifty eight"], "C", "50 减 8 得 42，即 forty two，其余金额不对，所以选 C。", 3)),
        (2, ("judge", "Say Thank you for the change.", None, "T", "收到找零说 Thank you 是礼貌用语，说法正确，所以 T。", 4)),
    ],
    "Unit 5 How are the seasons different?": [
        (0, ("choice", "Leaves fall. Which season is it?", ["Winter", "Autumn", "Spring", "Summer"], "B", "落叶是秋天 autumn，其余季节不合，所以选 B。", 3)),
        (1, ("answer", "Write: why do you like spring?", None, "I like spring because it is warm.", "用 because 给理由得 2 分；天气词正确得 2 分。", 4)),
    ],
    "Unit 6 What's amazing about plants?": [
        (0, ("choice", "You put a seed in soil. What next?", ["Water it", "Add a shoe", "Freeze it", "Hide it"], "A", "播种后要浇水，其余做法不利生长，所以选 A。", 3)),
        (1, ("judge", "Plants need soil only, not light.", None, "F", "植物还需要阳光与水，说法不全，所以 F。", 4)),
    ],
    "Unit 7 How do we keep safe on the road?": [
        (0, ("choice", "On a bike, what must you wear?", ["Glasses", "A helmet", "A cap", "A scarf"], "B", "骑车戴 helmet 护头，其余护具不管用，所以选 B。", 3)),
        (2, ("judge", "We can cross when the light is red.", None, "F", "红灯禁止通行，绿灯才能过，所以 F。", 4)),
    ],
    "Unit 8 What do our grandparents do?": [
        (0, ("choice", "Grandma walks daily. She ___.", ["Sleeps", "Swims", "Exercises", "Drives"], "C", "散步是锻炼 exercise，其余动作不对应，所以选 C。", 3)),
        (1, ("judge", "She watches TV. The verb has -es.", None, "T", "watch 以 ch 结尾，第三人称单数加 -es，所以 T。", 4)),
    ],
}
for _ch in PACK["chapters"]:
    for _idx, _q in _REVIEW_Q[_ch["name"]]:
        _ch["points"][_idx]["questions"].append(_q)
