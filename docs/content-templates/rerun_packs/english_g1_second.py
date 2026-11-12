# -*- coding: utf-8 -*-
"""english / g1 / 下册 内容包（2026-11-12）。题干英文、解析中文；章节名取下册骨架。"""

PACK = {
    "subject": "english", "grade": 1, "version": "牛津深圳版", "semester": "second",
    "chapters": [
        {"name": "Unit 1 Look and see", "summary": "用 look at / see 谈论看到的事物。",
         "points": [
            {"name": "Look and see 看与见的基本动词", "explanation": "look 强调「看」的动作，see 强调「看见」的结果。",
             "questions": [
                ("choice", "Choose the best word: I ___ a bird in the tree.", ["look", "see", "listen", "taste"], "B", "see 表示看见的结果，看见树上的鸟用 see。", 2),
                ("fill", "Fill in: Look ___ the picture, please.", None, "at", "look at 是固定搭配，意为「看……」。", 2),
                ("judge", "「Look! A cat.」 means 看，一只猫。", None, "T", "Look 用于提醒别人注意看到的东西。", 2),
                ("answer", "Write one sentence with「I can see …」about your classroom.", None, "示例：I can see a blackboard.", "评分要点：句式正确，内容与教室相符。", 3),
             ]},
            {"name": "Look and see 公园里的常见事物", "explanation": "tree, flower, bird, kite 等词用来描述公园。",
             "questions": [
                ("choice", "Which word is a thing in the park?", ["flower", "pencil", "spoon", "chair"], "A", "flower 花，是公园里的事物。", 2),
                ("fill", "Fill in: I can see two ___（鸟）in the sky.", None, "birds", "两只鸟要用复数 birds。", 2),
                ("judge", "「a tree」 means 一棵树。", None, "T", "tree 是树，a 表示一。", 2),
                ("answer", "Name three things you can see in a park.", None, "示例：trees, flowers, birds", "评分要点：三个词都正确、符合公园情境。", 3),
             ]},
            {"name": "Look and see 冠词 a / an 的选择", "explanation": "元音音素开头的词前用 an，其余用 a。",
             "questions": [
                ("choice", "Choose the right one: ___ apple", ["a", "an", "the", "/"], "B", "apple 以元音音素开头，用 an。", 2),
                ("fill", "Fill in: This is ___ bird.（填 a 或 an）", None, "a", "bird 以辅音音素开头，用 a。", 2),
                ("judge", "We say「an orange」.", None, "T", "orange 以元音音素开头，用 an。", 3),
                ("answer", "Write two phrases: one with「a」and one with「an」.", None, "示例：a dog / an egg", "评分要点：冠词与首音匹配。", 3),
             ]},
            {"name": "Look and see 数量表达 one / two", "explanation": "数量大于一时名词要用复数形式。",
             "questions": [
                ("choice", "Choose the correct form: two ___", ["cat", "cats", "a cat", "an cat"], "B", "数词 two 后名词用复数 cats。", 2),
                ("fill", "Fill in: I see three ___（花）in the garden.", None, "flowers", "three 后接复数 flowers。", 2),
                ("judge", "「two bird」 is correct English.", None, "F", "应为 two birds，名词要加 s。", 3),
                ("answer", "Write a sentence with「I can see … four …」.", None, "示例：I can see four birds.", "评分要点：数量加复数，句子完整。", 3),
             ]},
         ]},
        {"name": "Unit 2 Listen and hear", "summary": "用 listen / hear 谈论听到的声音。",
         "points": [
            {"name": "Listen and hear 听与听见", "explanation": "listen 强调听得动作，常与 to 连用；hear 强调听见的结果。",
             "questions": [
                ("choice", "Choose the best word: ___! A dog is barking.", ["Listen", "See", "Taste", "Smell"], "A", "提醒别人注意声音用 Listen。", 2),
                ("fill", "Fill in: I can ___ a bird singing.", None, "hear", "hear 表示听见声音。", 2),
                ("judge", "We say「listen to the radio」.", None, "T", "listen 后接对象要用 to。", 3),
                ("answer", "Write one sentence about a sound you can hear now.", None, "示例：I can hear a car.", "评分要点：用 hear 且内容真实。", 3),
             ]},
            {"name": "Listen and hear 常见声音词汇", "explanation": "sing, bark, ring, cry 等动词表示不同声音。",
             "questions": [
                ("choice", "A dog can ___", ["sing", "bark", "ring", "read"], "B", "狗叫用 bark。", 2),
                ("fill", "Fill in: The bell can ___（响）.", None, "ring", "铃响用 ring。", 2),
                ("judge", "「A bird can bark.」 is true.", None, "F", "鸟叫用 sing，不是 bark。", 3),
                ("answer", "Match two animals with the sounds they make.", None, "示例：a bird – sing; a dog – bark", "评分要点：动物与声音对应正确。", 3),
             ]},
            {"name": "Listen and hear 教室里的指令句", "explanation": "Listen carefully. Open your book. 是常见的课堂指令。",
             "questions": [
                ("choice", "What does「Open your book」 mean?", ["合上书", "打开书", "读书", "放下书"], "B", "open 是打开，book 是书。", 2),
                ("fill", "Fill in: ___ carefully, please.", None, "Listen", "课堂指令 Listen carefully 意为「仔细听」。", 2),
                ("judge", "「Sit down, please.」 means 请坐下。", None, "T", "sit down 是坐下。", 2),
                ("answer", "Write one English instruction your teacher often says.", None, "示例：Stand up, please.", "评分要点：是指令句、拼写正确。", 3),
             ]},
            {"name": "Listen and hear 声音大小与形容词", "explanation": "loud / quiet 用来描述声音的大小。",
             "questions": [
                ("choice", "The music is too ___. I can't sleep.", ["quiet", "loud", "small", "new"], "B", "太吵用 loud。", 2),
                ("fill", "Fill in: Please be ___（安静）in the library.", None, "quiet", "图书馆要保持安静，用 quiet。", 2),
                ("judge", "「loud」 and 「quiet」 are opposites.", None, "T", "loud 与 quiet 意思相反。", 3),
                ("answer", "Write a sentence with「It is too loud」.", None, "示例：It is too loud in the street.", "评分要点：句意完整、用词正确。", 3),
             ]},
         ]},
        {"name": "Unit 3 Taste and smell", "summary": "用 taste / smell 谈论味道与气味。",
         "points": [
            {"name": "Taste and smell 两个感官动词", "explanation": "taste 尝味道，smell 闻气味，都与食物相关。",
             "questions": [
                ("choice", "Choose the best word: I can ___ the soup. It is salty.", ["see", "taste", "listen", "look"], "B", "尝汤的味道用 taste。", 2),
                ("fill", "Fill in: The flowers ___（闻起来）nice.", None, "smell", "闻起来用 smell。", 2),
                ("judge", "We use「smell」 for flowers and food.", None, "T", "smell 用于闻气味。", 2),
                ("answer", "Write one sentence with「It tastes …」about a food.", None, "示例：It tastes sweet.", "评分要点：taste 后接形容词，句意通顺。", 3),
             ]},
            {"name": "Taste and smell 味道形容词", "explanation": "sweet, sour, salty, hot 描述不同的味道。",
             "questions": [
                ("choice", "Lemons taste ___", ["sweet", "sour", "salty", "hot"], "B", "柠檬是酸的，用 sour。", 2),
                ("fill", "Fill in: Sugar is ___（甜的）.", None, "sweet", "糖是甜的。", 2),
                ("judge", "「salty」 means 咸的.", None, "T", "salty 表示咸。", 3),
                ("answer", "Write two sentences about tastes of two foods.", None, "示例：The candy is sweet. The soup is salty.", "评分要点：两种食物、两个味道词正确。", 3),
             ]},
            {"name": "Taste and smell 食物名词", "explanation": "soup, candy, cake, fruit 等是常见食物名词。",
             "questions": [
                ("multiple", "Which of these can you taste?", ["soup", "cake", "song", "candy"], ["A", "B", "D"], "逐项判断：A soup ✓ 汤可以尝；B cake ✓ 蛋糕可以尝；C song ✗ 歌曲不能尝；D candy ✓ 糖果可以尝。所以选 A、B、D。", 3),
                ("fill", "Fill in: I like fruit. I eat an ___（苹果）every day.", None, "apple", "苹果是 apple。", 2),
                ("judge", "「a soup」 is the correct way to count soup.", None, "F", "soup 通常不可数，说 some soup 更自然。", 4),
                ("answer", "Name three foods you like and one you dislike.", None, "示例：I like apples, cakes and milk. I don't like onions.", "评分要点：三种喜欢 + 一种不喜欢，用词正确。", 3),
             ]},
            {"name": "Taste and smell 感官句型 It tastes/smells …", "explanation": "It tastes / smells + 形容词 描述食物给人的感觉。",
             "questions": [
                ("choice", "Which sentence about taste is correct?", ["It taste sweet.", "It tastes sweet.", "It tasting sweet.", "It is taste sweet."], "B", "主语 it 是第三人称单数，动词加 s。", 3),
                ("fill", "Fill in: It ___（闻起来）good.", None, "smells", "第三人称单数要加 s。", 3),
                ("judge", "「It smells nice.」 is a correct sentence.", None, "T", "主语单数 + smells，正确。", 2),
                ("answer", "Describe a food with「It smells … and it tastes …」.", None, "示例：It smells good and it tastes sweet.", "评分要点：两个感官动词都用到。", 4),
             ]},
         ]},
        {"name": "Unit 4 Toys I like", "summary": "谈论喜欢的玩具。",
         "points": [
            {"name": "Toys I like 玩具词汇", "explanation": "ball, doll, car, kite, robot 是常见玩具词。",
             "questions": [
                ("choice", "Which one is a toy?", ["doll", "desk", "door", "dish"], "A", "doll 洋娃娃，是玩具。", 2),
                ("fill", "Fill in: I have a red ___（球）.", None, "ball", "球是 ball。", 2),
                ("judge", "「robot」 means 机器人.", None, "T", "robot 是机器人。", 2),
                ("answer", "Name three toys you have.", None, "示例：a ball, a kite and a car", "评分要点：三个玩具词正确。", 3),
             ]},
            {"name": "Toys I like 表达喜好 I like …", "explanation": "I like + 名词，表示喜欢某物；不喜欢说 I don't like。",
             "questions": [
                ("choice", "Which sentence with「I like」is correct?", ["I likes cars.", "I like cars.", "I like car.", "I liking cars."], "B", "主语 I 后动词用原形 like，可数名词复数 cars。", 2),
                ("fill", "Fill in: I ___（喜欢）this doll.", None, "like", "I like … 表示喜欢。", 2),
                ("judge", "「I don't like robots.」 means 我不喜欢机器人。", None, "T", "don't like 表示不喜欢。", 2),
                ("answer", "Write two sentences: one thing you like and one you don't like.", None, "示例：I like kites. I don't like toy guns.", "评分要点：一句 like、一句 don't like。", 3),
             ]},
            {"name": "Toys I like 询问他人喜好 Do you like …?", "explanation": "Do you like …? 用 Yes, I do. / No, I don't. 回答。",
             "questions": [
                ("choice", "—Do you like dolls? —___", ["Yes, I do.", "Yes, I like.", "No, I do.", "Yes, I am."], "A", "Do 提问要用 do 回答。", 3),
                ("fill", "Fill in: ___ you like this ball?（填疑问词）", None, "Do", "一般现在时的一般疑问句用 Do 开头。", 2),
                ("judge", "Answer「Do you like cars?」 with「Yes, I do.」", None, "T", "助动词 do 提问，回答也用 do。", 2),
                ("answer", "Ask a friend about toys and write the question.", None, "示例：Do you like robots?", "评分要点：疑问句语序正确。", 3),
             ]},
            {"name": "Toys I like 颜色与玩具搭配", "explanation": "颜色词放在名词前，如 a blue ball。",
             "questions": [
                ("choice", "Choose the right order.", ["a ball blue", "blue a ball", "a blue ball", "ball a blue"], "C", "颜色形容词在名词前，冠词在最前。", 2),
                ("fill", "Fill in: I like my ___（黄色的）kite.", None, "yellow", "黄色是 yellow。", 2),
                ("judge", "「a green robot」 means 一个绿色的机器人。", None, "T", "颜色词修饰名词。", 2),
                ("answer", "Describe your favourite toy with a colour word.", None, "示例：My favourite toy is a red car.", "评分要点：含颜色词、句子完整。", 3),
             ]},
         ]},
        {"name": "Unit 5 Food I like", "summary": "谈论喜欢的食物与三餐。",
         "points": [
            {"name": "Food I like 食物词汇与三餐", "explanation": "breakfast, lunch, dinner 表示三餐；rice, noodles, egg 是常见食物。",
             "questions": [
                ("choice", "Which meal do we eat in the morning?", ["breakfast", "lunch", "dinner", "snack"], "A", "早餐是 breakfast。", 2),
                ("fill", "Fill in: I have ___（米饭）for lunch.", None, "rice", "米饭是 rice，不可数。", 2),
                ("judge", "「noodles」 usually takes a plural form.", None, "T", "noodles 常用复数形式。", 3),
                ("answer", "Write what you have for breakfast.", None, "示例：I have an egg and some milk for breakfast.", "评分要点：含食物词、句子完整。", 3),
             ]},
            {"name": "Food I like some / a 的用法", "explanation": "不可数名词前用 some，可数单数前用 a / an。",
             "questions": [
                ("choice", "Which phrase with「some」is correct?", ["a rice", "some rice", "an rice", "many rice"], "B", "rice 不可数，用 some rice。", 2),
                ("fill", "Fill in: I want ___（一些）noodles.", None, "some", "noodles 复数前用 some。", 2),
                ("judge", "「some eggs」 is correct.", None, "T", "可数名词复数前可以用 some。", 2),
                ("answer", "Write two phrases: one with「some」and one with「an」.", None, "示例：some rice / an apple", "评分要点：两组搭配都正确。", 3),
             ]},
            {"name": "Food I like 喜欢与不喜欢的表达", "explanation": "I like / I don't like 用于表达对食物的喜好。",
             "questions": [
                ("choice", "Which negative sentence is correct?", ["I not like fish.", "I don't like fish.", "I doesn't like fish.", "I no like fish."], "B", "否定用 don't + 动词原形。", 2),
                ("fill", "Fill in: I ___（喜欢）vegetables.", None, "like", "I like vegetables。", 2),
                ("judge", "「I like fish very much.」 means 我很喜欢鱼。", None, "T", "very much 表示程度很深。", 2),
                ("answer", "Write one sentence about a food you don't like.", None, "示例：I don't like onions.", "评分要点：否定句式正确。", 3),
             ]},
            {"name": "Food I like 问句 What do you like?", "explanation": "What do you like? 回答用 I like …。",
             "questions": [
                ("choice", "—What do you like? —___", ["I like apples.", "I am apples.", "Yes, I do.", "I likes apples."], "A", "问喜好要用 I like … 回答。", 2),
                ("fill", "Fill in: ___ do you like?（填疑问词）", None, "What", "询问喜欢什么用 What。", 2),
                ("judge", "「What do you like?」 asks about food or things you like.", None, "T", "问的是喜欢什么。", 3),
                ("answer", "Write a question and an answer about food.", None, "示例：What do you like? I like noodles.", "评分要点：一问一答、句式正确。", 4),
             ]},
         ]},
        {"name": "Unit 6 Drinks I like", "summary": "谈论喜欢的饮料。",
         "points": [
            {"name": "Drinks I like 饮料词汇", "explanation": "water, milk, juice, tea 是常见饮料词。",
             "questions": [
                ("choice", "Which one is a drink?", ["juice", "cake", "rice", "bread"], "A", "juice 果汁，是饮料。", 2),
                ("fill", "Fill in: I drink ___（牛奶）every morning.", None, "milk", "牛奶是 milk。", 2),
                ("judge", "「tea」 means 茶.", None, "T", "tea 是茶。", 2),
                ("answer", "Name three drinks you know.", None, "示例：water, milk and juice", "评分要点：三个饮料词正确。", 3),
             ]},
            {"name": "Drinks I like 不可数名词与量", "explanation": "饮料多不可数，用 some / a glass of 表示数量。",
             "questions": [
                ("choice", "Which phrase about drinks is correct?", ["a water", "some water", "an water", "many water"], "B", "water 不可数，用 some water。", 2),
                ("fill", "Fill in: Can I have a ___（杯）of tea?", None, "cup", "一杯茶是 a cup of tea。", 3),
                ("judge", "「two milks」 is the best way to say 两杯牛奶.", None, "F", "应说 two cups of milk。", 3),
                ("answer", "Write a sentence with「a glass of」.", None, "示例：I want a glass of juice.", "评分要点：量词搭配正确。", 3),
             ]},
            {"name": "Drinks I like 礼貌请求 Can I have …?", "explanation": "Can I have …, please? 是礼貌索要的说法。",
             "questions": [
                ("choice", "Which is the most polite?", ["Give me water.", "Can I have some water, please?", "Water!", "I want water now."], "B", "Can I have … please 最礼貌。", 2),
                ("fill", "Fill in: ___ I have some milk?（填情态动词）", None, "Can", "请求许可用 Can I …?。", 2),
                ("judge", "Adding「please」 makes a request more polite.", None, "T", "please 让请求更客气。", 2),
                ("answer", "Write a polite request for a drink.", None, "示例：Can I have some juice, please?", "评分要点：含 Can I have、please。", 3),
             ]},
            {"name": "Drinks I like 冷热与口味描述", "explanation": "hot / cold / sweet 描述饮料。",
             "questions": [
                ("choice", "The tea is very ___. Be careful.", ["cold", "hot", "sweet", "new"], "B", "提醒小心烫，用 hot。", 2),
                ("fill", "Fill in: I like ___（冷的）water in summer.", None, "cold", "冷水用 cold water。", 2),
                ("judge", "「I like hot milk at night.」 is a reasonable sentence.", None, "T", "句意合理、搭配正确。", 3),
                ("answer", "Describe a drink you like with two adjectives.", None, "示例：I like cold juice. It is sweet.", "评分要点：两个形容词都用对。", 3),
             ]},
         ]},
        {"name": "Unit 7 Seasons", "summary": "谈论四季与季节里的活动。",
         "points": [
            {"name": "Seasons 四季名称", "explanation": "spring, summer, autumn, winter 是四季。",
             "questions": [
                ("choice", "It is very hot. Which season is it?", ["spring", "summer", "autumn", "winter"], "B", "夏天最热，用 summer。", 2),
                ("fill", "Fill in: ___（春天）comes after winter.", None, "Spring", "冬天之后是春天。", 2),
                ("judge", "There are four seasons in a year.", None, "T", "一年有四季。", 2),
                ("answer", "Write the four seasons in order from spring.", None, "spring, summer, autumn, winter", "评分要点：顺序正确、拼写正确。", 3),
             ]},
            {"name": "Seasons 季节与天气搭配", "explanation": "不同季节有典型天气：春天温暖、夏天炎热、秋天凉爽、冬天寒冷。",
             "questions": [
                ("choice", "In winter it is usually ___", ["hot", "cold", "cool", "warm"], "B", "冬天通常寒冷，用 cold。", 2),
                ("fill", "Fill in: In autumn it is ___（凉爽的）.", None, "cool", "秋天凉爽用 cool。", 3),
                ("judge", "「It is warm in spring.」 is a typical description.", None, "T", "春天温暖是常见描述。", 2),
                ("answer", "Write one sentence about the weather in your favourite season.", None, "示例：In autumn it is cool and windy.", "评分要点：季节与天气对应。", 3),
             ]},
            {"name": "Seasons 季节活动 I can … in …", "explanation": "用 I can … in spring/summer 说明季节里能做的事。",
             "questions": [
                ("choice", "Choose the best sentence.", ["I can swim in summer.", "I can swim in winter.", "I swimming in summer.", "I can swims in summer."], "A", "夏天游泳符合常识，can 后接动词原形。", 2),
                ("fill", "Fill in: I can fly a kite in ___（春天）.", None, "spring", "春天放风筝。", 2),
                ("judge", "「I can make a snowman in winter.」 is reasonable.", None, "T", "冬天可以堆雪人。", 3),
                ("answer", "Write two season activities.", None, "示例：I can swim in summer. I can make a snowman in winter.", "评分要点：两个活动与季节匹配。", 3),
             ]},
            {"name": "Seasons 季节与服装", "explanation": "不同季节穿不同衣服，coat / T-shirt / sweater 等词配合使用。",
             "questions": [
                ("choice", "In winter we wear a ___", ["T-shirt", "coat", "shorts", "skirt"], "B", "冬天穿外套 coat。", 2),
                ("fill", "Fill in: In summer I wear a ___（短袖）.", None, "T-shirt", "短袖 T 恤用 T-shirt。", 2),
                ("judge", "「We wear sweaters in winter.」 is reasonable.", None, "T", "冬天穿毛衣合理。", 3),
                ("answer", "Write what you wear in two different seasons.", None, "示例：In summer I wear a T-shirt. In winter I wear a coat.", "评分要点：两个季节、服装匹配。", 3),
             ]},
         ]},
        {"name": "Unit 8 Weather", "summary": "谈论天气：晴、雨、风、云。",
         "points": [
            {"name": "Weather 天气词汇", "explanation": "sunny, rainy, windy, cloudy, snowy 描述天气。",
             "questions": [
                ("choice", "It is raining. The weather is ___", ["sunny", "rainy", "windy", "snowy"], "B", "下雨的天气是 rainy。", 2),
                ("fill", "Fill in: It is ___（晴朗的）today.", None, "sunny", "晴朗用 sunny。", 2),
                ("judge", "「windy」 means 有风的.", None, "T", "windy 表示刮风。", 2),
                ("answer", "Describe today's weather in one sentence.", None, "示例：It is sunny today.", "评分要点：天气词正确、句子完整。", 3),
             ]},
            {"name": "Weather 询问天气 How's the weather?", "explanation": "How's the weather? 回答 It is + 天气形容词。",
             "questions": [
                ("choice", "—How's the weather? —___", ["It is sunny.", "I am sunny.", "Yes, it is.", "It sunny."], "A", "回答用 It is + 天气词。", 2),
                ("fill", "Fill in: ___ is the weather today?（填疑问词）", None, "How", "询问天气用 How's the weather。", 2),
                ("judge", "「How's the weather?」 asks about the weather.", None, "T", "问的就是天气。", 2),
                ("answer", "Ask and answer about the weather in English.", None, "示例：How's the weather? It is cloudy.", "评分要点：问答配套、格式正确。", 3),
             ]},
            {"name": "Weather 天气与活动选择", "explanation": "天气决定活动：雨天带伞、晴天外出。",
             "questions": [
                ("choice", "It is rainy. What should you take?", ["an umbrella", "a kite", "a ball", "a hat"], "A", "下雨要带雨伞 umbrella。", 2),
                ("fill", "Fill in: It is sunny. Let's go ___（外面）.", None, "outside", "晴天可以到外面。", 3),
                ("judge", "On a windy day, flying a kite is a good idea.", None, "T", "有风的日子适合放风筝。", 3),
                ("answer", "Write one sentence about what you do on a rainy day.", None, "示例：On a rainy day I stay at home and read.", "评分要点：活动与天气相符。", 3),
             ]},
            {"name": "Weather 天气与衣物", "explanation": "冷天加衣、热天减衣，raincoat / boots 应对雨天。",
             "questions": [
                ("choice", "On a cold day, we wear ___ clothes.", ["thin", "warm", "light", "small"], "B", "冷天穿暖和的衣服，用 warm。", 2),
                ("fill", "Fill in: It is cold. Put on your ___（外套）.", None, "coat", "冷天穿外套。", 2),
                ("judge", "We wear boots on a rainy day.", None, "T", "雨天穿雨靴。", 3),
                ("answer", "Write what you wear on a cold day.", None, "示例：On a cold day I wear a coat and a scarf.", "评分要点：衣物与天气对应。", 3),
             ]},
         ]},
        {"name": "Unit 9 Clothes", "summary": "谈论衣物与穿着。",
         "points": [
            {"name": "Clothes 衣物词汇", "explanation": "shirt, skirt, dress, shoes, socks 是常见衣物词。",
             "questions": [
                ("choice", "Which one do you wear on your feet?", ["shoes", "hat", "shirt", "skirt"], "A", "穿在脚上的是 shoes。", 2),
                ("fill", "Fill in: I wear ___（袜子）on my feet.", None, "socks", "袜子是 socks，常成双用复数。", 2),
                ("judge", "「dress」 is a kind of clothes for girls or women.", None, "T", "dress 是连衣裙。", 2),
                ("answer", "Name three clothes you wear to school.", None, "示例：a shirt, trousers and shoes", "评分要点：三个衣物词正确。", 3),
             ]},
            {"name": "Clothes 单复数与 a pair of", "explanation": "成双的衣物用 a pair of；复数名词配 are。",
             "questions": [
                ("choice", "Choose the correct phrase.", ["a shoes", "a pair of shoes", "a pair shoe", "pair of a shoes"], "B", "成双的鞋用 a pair of shoes。", 3),
                ("fill", "Fill in: My socks ___（be）blue.", None, "are", "socks 是复数，用 are。", 2),
                ("judge", "「My trousers is new.」 is correct.", None, "F", "trousers 是复数，应用 are。", 3),
                ("answer", "Write a sentence with「a pair of」.", None, "示例：I want a pair of new shoes.", "评分要点：搭配正确。", 3),
             ]},
            {"name": "Clothes 穿着动词 wear / put on", "explanation": "wear 表示穿着状态，put on 表示穿上的动作。",
             "questions": [
                ("choice", "It is cold. ___ your coat.", ["Wear", "Put on", "Take off", "Look"], "B", "「穿上」这个动作要用 put on。", 3),
                ("fill", "Fill in: She ___（穿着）a red dress today.", None, "wears", "表示穿着的状态用 wear，主语单数加 s。", 3),
                ("judge", "「He is wearing a hat.」 describes what he has on now.", None, "T", "wear 描述现在的穿着状态。", 3),
                ("answer", "Write two sentences: one with「wear」and one with「put on」.", None, "示例：I wear a shirt. Put on your shoes.", "评分要点：两个动词用法区分正确。", 4),
             ]},
            {"name": "Clothes 询问与赞美", "explanation": "What are you wearing? / It looks nice. 是常见交流句。",
             "questions": [
                ("choice", "—What are you wearing? —___", ["I am wearing a T-shirt.", "I wear T-shirt yesterday.", "Yes, I am.", "I like T-shirt."], "A", "问「正穿着什么」用现在进行时回答。", 3),
                ("fill", "Fill in: Your dress ___（看起来）nice.", None, "looks", "look 作「看起来」用，主语单数加 s。", 3),
                ("judge", "「It looks nice on you.」 is a compliment.", None, "T", "这是赞美的话。", 2),
                ("answer", "Write a sentence complimenting a friend's clothes.", None, "示例：Your new coat looks nice.", "评分要点：包含赞美表达、语法正确。", 3),
             ]},
         ]},
        {"name": "Unit 10 Activities", "summary": "谈论日常活动与can句型。",
         "points": [
            {"name": "Activities 常见活动词汇", "explanation": "run, jump, swim, sing, dance, draw 是常见活动动词。",
             "questions": [
                ("choice", "Which activity is done in water?", ["swim", "run", "draw", "sing"], "A", "游泳在水里进行。", 2),
                ("fill", "Fill in: I can ___（跳）very high.", None, "jump", "跳是 jump。", 2),
                ("judge", "「draw」 means 画画.", None, "T", "draw 表示画画。", 2),
                ("answer", "Name three activities you can do.", None, "示例：run, swim and sing", "评分要点：三个活动词正确。", 3),
             ]},
            {"name": "Activities can 表达能力", "explanation": "can + 动词原形 表示会做某事，否定用 can't。",
             "questions": [
                ("choice", "Which sentence with「can」is correct?", ["I can swims.", "I can swim.", "I can swimming.", "I can to swim."], "B", "can 后接动词原形。", 2),
                ("fill", "Fill in: She can ___（唱歌）well.", None, "sing", "can 后用原形 sing。", 2),
                ("judge", "「I can't fly.」 means 我不会飞。", None, "T", "can't 表示不能、不会。", 2),
                ("answer", "Write two sentences with「can」and「can't」.", None, "示例：I can jump. I can't swim.", "评分要点：一肯定一否定，语法正确。", 3),
             ]},
            {"name": "Activities 询问能力 Can you …?", "explanation": "Can you …? 回答 Yes, I can. / No, I can't.",
             "questions": [
                ("choice", "—Can you draw? —___", ["Yes, I can.", "Yes, I do.", "No, I don't.", "Yes, I am."], "A", "Can 提问用 can 回答。", 2),
                ("fill", "Fill in: ___ you swim?（填情态动词）", None, "Can", "询问能力用 Can you …?。", 2),
                ("judge", "「Can you sing?」 asks about ability.", None, "T", "问的是能力。", 3),
                ("answer", "Ask a friend about an activity and answer it.", None, "示例：Can you dance? Yes, I can.", "评分要点：问答对应、语法正确。", 4),
             ]},
            {"name": "Activities 活动与地点搭配", "explanation": "活动发生地点要合理，如 swim in the pool。",
             "questions": [
                ("choice", "Choose the best phrase.", ["swim in the pool", "swim in the book", "run in the cup", "sing in the shoe"], "A", "游泳池里游泳搭配合理。", 2),
                ("fill", "Fill in: I read books in the ___（图书馆）.", None, "library", "图书馆是 library。", 2),
                ("judge", "「I can play football in the classroom.」 is a good sentence.", None, "F", "教室里踢足球不合适。", 3),
                ("answer", "Write one sentence: an activity and a place.", None, "示例：I can draw in the art room.", "评分要点：活动与地点搭配合理。", 3),
             ]},
         ]},
        {"name": "Unit 11 New Year's Day", "summary": "谈论新年与祝福。",
         "points": [
            {"name": "New Year's Day 节日与日期表达", "explanation": "New Year's Day 是新年，Happy New Year 是常用祝福。",
             "questions": [
                ("choice", "What do we say on New Year's Day?", ["Happy New Year!", "Good morning!", "Thank you!", "Sorry!"], "A", "新年要说 Happy New Year。", 2),
                ("fill", "Fill in: ___ New Year!（填形容词）", None, "Happy", "祝福用 Happy New Year。", 2),
                ("judge", "New Year's Day is a festival.", None, "T", "新年是节日。", 2),
                ("answer", "Write a New Year greeting to a friend.", None, "示例：Happy New Year, Amy!", "评分要点：祝福语正确、有称呼。", 3),
             ]},
            {"name": "New Year's Day 新年活动与礼物", "explanation": "gift, card, party, fireworks 是新年相关词。",
             "questions": [
                ("choice", "Which is a New Year gift?", ["a card", "a desk", "a door", "a wall"], "A", "贺卡可以是新年礼物。", 2),
                ("fill", "Fill in: We have a ___（聚会）on New Year's Day.", None, "party", "聚会是 party。", 2),
                ("judge", "People may watch fireworks on New Year's Day.", None, "T", "新年常看烟花。", 3),
                ("answer", "Name two things people do on New Year's Day.", None, "示例：have a party and give gifts", "评分要点：两项活动合理。", 3),
             ]},
            {"name": "New Year's Day 祝福语与祝愿句型", "explanation": "I wish you … / Happy New Year to you 表达祝愿。",
             "questions": [
                ("choice", "Choose the best wish.", ["I wish you a happy New Year.", "I wish you a happy desk.", "You are a New Year.", "New Year is you."], "A", "祝愿句结构完整、意思通顺。", 3),
                ("fill", "Fill in: Happy New Year ___ you!", None, "to", "Happy New Year to you 是常见说法。", 2),
                ("judge", "「I wish you good luck.」 is a kind of wish.", None, "T", "这是祝愿的话。", 2),
                ("answer", "Write a wish for the new year.", None, "示例：I wish you good luck and happiness.", "评分要点：祝愿句完整。", 3),
             ]},
            {"name": "New Year's Day 复数的礼物与数量", "explanation": "多个礼物用复数 gifts，配数词。",
             "questions": [
                ("choice", "Choose the correct form.", ["three gift", "three gifts", "a gifts", "an gifts"], "B", "数词 three 后接复数 gifts。", 2),
                ("fill", "Fill in: I have two ___（卡片）for you.", None, "cards", "两张卡片用复数 cards。", 2),
                ("judge", "「many gift」 is correct.", None, "F", "应为 many gifts。", 3),
                ("answer", "Write a sentence about gifts you gave.", None, "示例：I gave my friend two cards.", "评分要点：数量与复数一致。", 3),
             ]},
         ]},
        {"name": "Unit 12 A boy and a wolf", "summary": "故事阅读：男孩与狼。",
         "points": [
            {"name": "A boy and a wolf 故事情节理解", "explanation": "故事讲男孩喊狼来了骗人，最后没人相信他。",
             "questions": [
                ("choice", "What does the boy do in the story?", ["He shouts「wolf」to trick people.", "He feeds the sheep.", "He runs away home.", "He helps the wolf."], "A", "故事里男孩喊「狼来了」骗人。", 3),
                ("fill", "Fill in: The boy ___（喊）「Wolf! Wolf!」", None, "shouts", "喊叫用 shout，单数主语加 s。", 3),
                ("judge", "At the end, people still believe the boy.", None, "F", "最后人们不再相信他。", 3),
                ("answer", "Tell the story in two sentences in English.", None, "示例：A boy shouts「wolf」to trick people. At last nobody believes him.", "评分要点：两句概括主要情节。", 4),
             ]},
            {"name": "A boy and a wolf 故事的教训", "explanation": "撒谎会失去别人的信任，这是故事的寓意。",
             "questions": [
                ("choice", "What is the lesson of the story?", ["Don't tell lies.", "Run fast.", "Eat more.", "Sleep early."], "A", "故事告诉我们不要说谎。", 3),
                ("fill", "Fill in: We should tell the ___（真相）.", None, "truth", "真相是 truth。", 3),
                ("judge", "Telling lies can make people stop trusting you.", None, "T", "说谎会失去信任。", 3),
                ("answer", "Write one sentence about why we should be honest.", None, "示例：We should be honest so that people trust us.", "评分要点：意思清楚、语法基本正确。", 4),
             ]},
            {"name": "A boy and a wolf 过去时态的初步感知", "explanation": "故事里的事已发生，动词常用过去式，如 shouted, ran。",
             "questions": [
                ("choice", "Choose the past form of「shout」.", ["shouts", "shouted", "shouting", "shout"], "B", "shout 的过去式是 shouted。", 3),
                ("fill", "Fill in: The boy ___（run）away yesterday.", None, "ran", "run 的过去式是 ran。", 4),
                ("judge", "「He shouted at the wolf.」 tells us it happened before.", None, "T", "shouted 表示已经发生。", 3),
                ("answer", "Write a past-tense sentence about the boy.", None, "示例：The boy shouted again and again.", "评分要点：用过去式、句意完整。", 4),
             ]},
            {"name": "A boy and a wolf 角色与对话朗读", "explanation": "故事中有男孩、农民、狼等角色，对话要读出语气。",
             "questions": [
                ("choice", "Who is tricked in the story?", ["the people who help the boy", "the wolf", "the sheep", "the boy's teacher"], "A", "被耍弄的是来帮忙的人们。", 3),
                ("fill", "Fill in: The ___（狼）comes at last.", None, "wolf", "狼是 wolf。", 2),
                ("judge", "Reading a dialogue aloud with feeling helps us understand the story.", None, "T", "有语气地朗读有助于理解。", 3),
                ("answer", "Write the boy's shout in English.", None, "示例：Wolf! Wolf! Help me!", "评分要点：符合故事情境。", 3),
             ]},
         ]},
    ],
}

PACK["pad"] = {
    "Look and see 看与见的基本动词": [
        ("choice", "Choose the best word: Please ___ at the picture on the wall.", ["look", "see", "hear", "taste"], "A", "look at 表示「看……」，强调看的动作。", 2),
    ],
    "Look and see 数量表达 one / two": [
        ("fill", "Fill in: I see one ___（鸟）in the tree.", None, "bird", "one 后接可数名词单数 bird。", 2),
    ],
    "Listen and hear 常见声音词汇": [
        ("choice", "Which word means「听见」?", ["listen", "hear", "look", "taste"], "B", "hear 表示听见，listen 表示听的动作。", 2),
    ],
    "Listen and hear 声音大小与形容词": [
        ("fill", "Fill in: The dog can ___（叫）loudly.", None, "bark", "狗叫用 bark。", 2),
    ],
    "Taste and smell 味道形容词": [
        ("choice", "Which food is usually sour?", ["candy", "lemon", "cake", "rice"], "B", "柠檬是酸的，用 sour 描述。", 2),
    ],
    "Taste and smell 感官句型 It tastes/smells …": [
        ("judge", "「It smells nice.」 describes a smell, not a taste.", None, "T", "smell 说的是气味，taste 说的是味道。", 3),
    ],
    "Toys I like 询问他人喜好 Do you like …?": [
        ("choice", "—Do you like this kite? —No, ___", ["I do.", "I don't.", "I am not.", "I like."], "B", "Do 提问的否定回答用 No, I don't.", 2),
    ],
    "Toys I like 玩具词汇": [
        ("fill", "Fill in: I have a ___（洋娃娃）.", None, "doll", "洋娃娃是 doll。", 2),
    ],
    "Food I like 食物词汇与三餐": [
        ("choice", "Which one is a healthy breakfast food?", ["an egg", "a toy", "a pencil", "a book"], "A", "鸡蛋是健康的早餐食物。", 2),
    ],
    "Food I like 喜欢与不喜欢的表达": [
        ("fill", "Fill in: We have ___（午饭）at noon.", None, "lunch", "中午吃的是 lunch。", 2),
    ],
    "Drinks I like 饮料词汇": [
        ("choice", "Which drink is usually white?", ["milk", "tea", "juice", "coffee"], "A", "牛奶是白色的饮料。", 2),
    ],
    "Drinks I like 不可数名词与量": [
        ("fill", "Fill in: A ___（杯）of tea, please.", None, "cup", "一杯茶是 a cup of tea。", 2),
    ],
    "Seasons 四季名称": [
        ("choice", "Which season comes after summer?", ["spring", "autumn", "winter", "summer"], "B", "夏天之后是秋天 autumn。", 2),
    ],
    "Seasons 季节与天气搭配": [
        ("fill", "Fill in: There are four ___（季节）in a year.", None, "seasons", "四个季节用复数 seasons。", 2),
    ],
    "Weather 天气词汇": [
        ("choice", "Which word describes a day with much wind?", ["sunny", "windy", "rainy", "snowy"], "B", "风大的天气用 windy。", 2),
    ],
    "Weather 天气与衣物": [
        ("fill", "Fill in: It is ___（下雪的）here in winter.", None, "snowy", "下雪的天气用 snowy。", 2),
    ],
    "Clothes 衣物词汇": [
        ("choice", "Which do you wear on your head?", ["a hat", "shoes", "socks", "trousers"], "A", "戴在头上的是 hat。", 2),
    ],
    "Clothes 穿着动词 wear / put on": [
        ("fill", "Fill in: I wear a ___（裙子）to the party.", None, "skirt", "裙子是 skirt。", 2),
    ],
    "Activities 常见活动词汇": [
        ("choice", "Which activity uses a ball?", ["play football", "draw a picture", "sing a song", "read a book"], "A", "踢足球要用球。", 2),
    ],
    "Activities can 表达能力": [
        ("fill", "Fill in: I can ___（画画）a cat.", None, "draw", "画画用 draw。", 2),
    ],
    "New Year's Day 节日与日期表达": [
        ("choice", "What do people often give on New Year's Day?", ["gifts", "desks", "walls", "doors"], "A", "新年常互送礼物 gifts。", 2),
    ],
    "New Year's Day 祝福语与祝愿句型": [
        ("fill", "Fill in: We say「Happy ___ Year!」", None, "New", "新年祝福是 Happy New Year。", 2),
    ],
    "A boy and a wolf 故事情节理解": [
        ("choice", "Why do people not believe the boy at last?", ["He told lies before.", "He is too young.", "He can't speak.", "He is a wolf."], "A", "他之前多次说谎，人们不再相信他。", 3),
    ],
    "A boy and a wolf 故事的教训": [
        ("judge", "The boy is honest in the story.", None, "F", "故事里男孩说谎，并不诚实。", 3),
    ],
}