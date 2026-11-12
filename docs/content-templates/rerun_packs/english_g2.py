# -*- coding: utf-8 -*-
"""重跑内容包：英语 二年级上册（牛津深圳版）。

按骨架索引六个 Unit 建立节级知识点，每点 4 题，另用 _REVIEW_Q 每章补 2 题。
题干与选项用英文、解析用中文，词汇句型语音按单元主题递进，不跨单元复用词批。
"""
PACK = {
    "subject": "english", "grade": 2, "version": "牛津深圳版", "semester": "first",
    "chapters": [
        {"name": "Unit 1 What can you do with your five senses?", "summary": "学习五官与 see/hear/smell/taste/touch 五个感官动词，用 I can... 描述感受，用 sweet/soft 等词搭配，并辨识字母 Ss 的 /s/ 首音。", "points": [
            {"name": "五官与感官动词的配对", "explanation": "eyes 配 see、ears 配 hear、nose 配 smell、tongue 配 taste、hands 配 touch；问 What can you do with your eyes? 用 I can see 回答。", "questions": [
                ("choice", "What can you do with your eyes?", ["See a flower", "Hear a bell", "Smell soap", "Taste candy"], "A", "眼睛 eyes 用来看 flower；另三项用耳、鼻、舌，所以选 A。", 1),
                ("fill", "I ___ with my ears and ___ with my nose.", None, ["hear", "smell"], "耳朵 ears 对应 hear，鼻子 nose 对应 smell，按器官填。", 2),
                ("judge", "We taste a lemon with our hands.", None, "F", "taste 用舌头 tongue，hands 用来摸，搭配错，所以错。", 3),
                ("answer", "Name two sense words for your face.", None, "see, smell", "评分要点：两个感官动词各得 2 分；与器官搭配合理得 1 分。", 4),
            ]},
            {"name": "What can you do? I can... 问答句型", "explanation": "问 What can you do? 用 I can + 感官动词回答；Can you hear the bell? 的简答是 Yes, I can. / No, I can't.，can 后加 not 表否定。", "questions": [
                ("choice", "What can you do with a bell?", ["I can hear it", "I can eat it", "I can smell it", "I can wear it"], "A", "铃会响，用耳朵 hear；其余三个动词不合铃声，所以选 A。", 1),
                ("fill", "Can you see the sun? Yes, I ___.", None, "can", "Can you...? 的肯定简答是 Yes, I can，can 不变。", 2),
                ("judge", "'No, I can.' is the right short answer.", None, "F", "否定简答要用 No, I can't，原句漏了 not，所以错。", 3),
                ("answer", "Ask a friend about the nose in English.", None, "What can you do with your nose?", "评分要点：用 What can you...? 提问得 2 分；提到 nose 得 2 分；语序正确得 1 分。", 4),
            ]},
            {"name": "感官形容词与名词搭配", "explanation": "sweet 配 candy、sour 配 lemon、soft 配 pillow、hard 配 stone、loud 配 drum；用 It is + 形容词 或 It tastes... 描述，味道与触感声音不能混用。", "questions": [
                ("choice", "How does a lemon taste?", ["Sweet", "Sour", "Soft", "Loud"], "B", "柠檬酸用 Sour；Sweet 是糖味，Soft 与 Loud 不表味道，所以选 B。", 1),
                ("fill", "A pillow is ___, but a stone is ___.", None, ["soft", "hard"], "枕头软 soft，石头硬 hard，两词互为反义。", 2),
                ("judge", "We say a drum is sweet.", None, "F", "sweet 说味道，鼓要用 loud 说声音，搭配不当，所以错。", 3),
                ("answer", "Write one word for candy's taste.", None, "sweet", "评分要点：写出 sweet 得 3 分；用 It tastes... 成句再得 2 分。", 4),
            ]},
            {"name": "字母 Ss 发 /s/ 的首音辨识", "explanation": "字母 Ss 在 see、sun、sit、sea、sing 词首发 /s/；把首音相同的词归一类，与元音或别的辅音起首的词区分。", "questions": [
                ("choice", "Which word starts with the /s/ sound?", ["sun", "cat", "ink", "up"], "A", "sun 以 s 开头发 /s/；cat、ink、up 首音不同，所以选 A。", 1),
                ("fill", "Ss is for ___ and ___.", None, ["sun", "sit"], "Ss 读 /s/，sun 与 sit 都以它开头。", 2),
                ("judge", "'See' and 'sing' start the same.", None, "T", "两词词首都是 s，都发 /s/，首音相同，所以对。", 3),
                ("answer", "Say two /s/ words you know.", None, "sea, sock", "评分要点：两个 /s/ 首音词各得 2 分；拼写正确再得 1 分。", 4),
            ]},
        ]},
        {"name": "Unit 2 What do you like about your family?", "summary": "认读 father/mother/grandpa/uncle 等家庭成员词，用 Who is he/she? 与 He/She is... 介绍家人，用 kind/tall/young/busy 描述，学字母 Ff 的 /f/。", "points": [
            {"name": "家庭成员称呼词的辨认", "explanation": "father 与 mother 合称 parents，grandpa/grandma 是祖辈，uncle/aunt/cousin 是叔姨与堂表亲，brother/sister 是亲兄弟姐妹，按辈分与性别区分。", "questions": [
                ("choice", "Your mother's father is your ___.", ["uncle", "grandpa", "brother", "cousin"], "B", "妈妈的爸爸是 grandpa；uncle 为叔舅、brother 为兄弟、cousin 为堂表，所以选 B。", 1),
                ("fill", "Father and mother are my ___.", None, "parents", "father 与 mother 合称 parents，指父母两人。", 2),
                ("judge", "A cousin is the same as a brother.", None, "F", "cousin 是堂表亲，brother 是亲兄弟，亲疏不同，所以错。", 3),
                ("answer", "Write two words for family members.", None, "uncle, aunt", "评分要点：两个不同家庭成员词各得 2 分；拼写正确得 1 分。", 4),
            ]},
            {"name": "Who is he/she? He/She is... 问答", "explanation": "问 Who is he? 用 He is my + 男性称呼；问 Who is she? 用 She is my + 女性称呼。he 指男、she 指女、it 指物、they 指复数，不能混用。", "questions": [
                ("choice", "Who is she? ___ is my grandma.", ["She", "He", "It", "They"], "A", "grandma 是女性用 She；He 指男、It 指物、They 指复数，所以选 A。", 1),
                ("fill", "___ is he? He is my ___.", None, ["Who", "uncle"], "问人用 Who，He is my 后接男性称呼 uncle。", 2),
                ("judge", "We say 'He is my mother'.", None, "F", "mother 是女性，主语要用 She，he 用错，所以错。", 3),
                ("answer", "Introduce your father in one sentence.", None, "He is my father. He is tall.", "评分要点：用 He is my... 介绍得 2 分；加一句描述得 2 分；he 正确得 1 分。", 4),
            ]},
            {"name": "描述家人的形容词与 My... is...", "explanation": "kind 善良、tall 高、young 年轻、busy 忙、short 矮；形容词放 be 动词后作表语，如 My grandma is kind.，tall 与 short、young 与 old 互为反义。", "questions": [
                ("choice", "My grandpa is not short. He is ___.", ["tall", "kind", "young", "busy"], "A", "not short 的反义是 tall；其余三词不说身高，所以选 A。", 1),
                ("fill", "My sister is ___, so she cannot play.", None, "busy", "没时间玩说明忙 busy，放 be 动词后作表语。", 2),
                ("judge", "'My father is young' means he is old.", None, "F", "young 是年轻，与 old 相反，释义说反，所以错。", 3),
                ("answer", "Write one word to describe your mum.", None, "kind", "评分要点：写出形容人的词得 3 分；用 My mum is... 成句再得 2 分。", 4),
            ]},
            {"name": "字母 Ff 与 /f/ 的对应", "explanation": "Ff 在 father、family、fish、four、face、five 词首发 /f/，上齿轻碰下唇送气；与元音起首或别的辅音起首的词区分。", "questions": [
                ("choice", "Find the word with /f/ at the start.", ["fish", "owl", "ant", "ox"], "A", "fish 以 f 开头发 /f/；owl、ant、ox 以元音起首，所以选 A。", 1),
                ("fill", "___ and ___ begin with /f/.", None, ["father", "four"], "father 与 four 词首都发 /f/，按首音填两词。", 2),
                ("judge", "The first sound of 'family' is /f/.", None, "T", "family 词首是 f，发 /f/，判断正确，所以对。", 3),
                ("answer", "Write two words with /f/ first.", None, "fish, five", "评分要点：两个 /f/ 首音词各得 2 分；拼写正确再得 1 分。", 4),
            ]},
        ]},
        {"name": "Unit 3 What is your favourite toy?", "summary": "认读 ball/doll/kite/robot/teddy 等玩具词，用 What is your favourite toy? 与 My favourite toy is... 问答，用颜色词和 It is... 描述，学字母 Bb 的 /b/。", "points": [
            {"name": "玩具名词的辨认", "explanation": "ball 可拍、kite 靠风飞、doll 与 teddy bear 用来抱、robot 会走会说、train 在地上跑、blocks 可搭；按玩法区分不同玩具。", "questions": [
                ("choice", "Which toy flies in the wind?", ["A kite", "A doll", "A ball", "A train"], "A", "kite 靠风飞；doll 抱、ball 拍、train 地上跑，所以选 A。", 1),
                ("fill", "A ___ can walk and talk like a person.", None, "robot", "会走会说话的玩具是 robot，不是布娃娃。", 2),
                ("judge", "A teddy bear is not a real bear.", None, "T", "teddy bear 是玩具熊，不是真熊，说法正确，所以对。", 3),
                ("answer", "Name two toys you can play with.", None, "a ball, a kite", "评分要点：两个不同玩具名词各得 2 分；拼写正确得 1 分。", 4),
            ]},
            {"name": "What is your favourite toy? 问答", "explanation": "favourite 意为最喜欢的；问 What is your favourite toy? 答 My favourite toy is a... 或直接说玩具名，简答可用 I like... best。", "questions": [
                ("choice", "What is your favourite toy?", ["I am fine", "My kite", "It is red", "Thank you"], "B", "问最爱的玩具要答玩具名 My kite；其余是问候、颜色、道谢，所以选 B。", 1),
                ("fill", "My ___ toy is a robot.", None, "favourite", "favourite 意为最喜爱的，修饰 toy，放在 My 后。", 2),
                ("judge", "'Favourite' means you like it most.", None, "T", "favourite 就是最喜欢、排第一，释义正确，所以对。", 3),
                ("answer", "Ask your friend about a toy.", None, "What is your favourite toy?", "评分要点：用 What is your favourite...? 提问得 3 分；提到 toy 得 2 分。", 4),
            ]},
            {"name": "颜色词与 It is + colour 描述", "explanation": "red 红、blue 蓝、green 绿、yellow 黄；问 What colour is it? 答 It is red.，形容词放名词前说 a red ball，不能说 a ball red。", "questions": [
                ("choice", "The grass is ___. What colour?", ["Green", "Red", "Blue", "Yellow"], "A", "草是绿色 Green；Red、Blue、Yellow 都不符，所以选 A。", 1),
                ("fill", "The sky is ___ and a banana is ___.", None, ["blue", "yellow"], "天空常是 blue，香蕉是 yellow，按常识填颜色。", 2),
                ("judge", "We say 'a ball red' in English.", None, "F", "形容词要放名词前，正确是 a red ball，语序颠倒，所以错。", 3),
                ("answer", "Write the colour of your toy.", None, "It is blue.", "评分要点：用 It is + 颜色成句得 3 分；颜色词拼写正确得 2 分。", 4),
            ]},
            {"name": "字母 Bb 发 /b/ 的首音辨识", "explanation": "Bb 在 ball、bear、bike、book、blue、bus 词首发 /b/，双唇闭合再放开、声带振动；与 /p/ 的清音相对，按首音给词归类。", "questions": [
                ("choice", "Pick the word that begins with /b/.", ["ball", "jam", "net", "cup"], "A", "ball 以 b 开头发 /b/；jam、net、cup 首音不同，所以选 A。", 1),
                ("fill", "Bb: name two words, ___ and ___.", None, ["bear", "bike"], "Bb 读 /b/，bear 与 bike 都以 b 开头。", 2),
                ("judge", "'Book' and 'blue' both begin with /b/.", None, "T", "两词词首都是 b，都发 /b/，首音相同，所以对。", 3),
                ("answer", "Name two /b/ words.", None, "bus, bag", "评分要点：两个 /b/ 首音词各得 2 分；拼写正确再得 1 分。", 4),
            ]},
        ]},
        {"name": "Unit 4 What is around your home?", "summary": "认读 park/shop/school/library 等家周边场所，用 There is a... near my home. 介绍，用 near/next to/behind 说位置，学字母 Pp 的 /p/。", "points": [
            {"name": "家周边场所名词", "explanation": "park 玩耍、shop 买东西、school 上课、library 安静读书、zoo 看动物、playground 运动、hospital 看病；按功能辨认不同场所。", "questions": [
                ("choice", "Where can you read quietly?", ["A zoo", "A shop", "A library", "A park"], "C", "安静读书去 library；zoo 看动物、shop 买物、park 玩，所以选 C。", 1),
                ("fill", "We buy bread at a ___ and play at a ___.", None, ["shop", "park"], "买东西在 shop，玩耍在 park，按功能填场所。", 2),
                ("judge", "A hospital is a place to see animals.", None, "F", "看动物去 zoo，hospital 是看病处，功能说错，所以错。", 3),
                ("answer", "Name two places near a home.", None, "a shop, a school", "评分要点：两个不同场所名词各得 2 分；拼写正确得 1 分。", 4),
            ]},
            {"name": "There is / There are 句型", "explanation": "介绍附近有什么用 There be：单数 a park 配 There is，复数 two shops 配 There are；is 与 are 随后面名词的单复数变化，不用 am 或 be。", "questions": [
                ("choice", "___ a park near my home.", ["There is", "There are", "There am", "There be"], "A", "a park 单数用 There is；are 配复数，am 与 be 不用于此句型，所以选 A。", 1),
                ("fill", "There ___ two shops near my school.", None, "are", "two shops 是复数，be 动词用 are，不用 is。", 2),
                ("judge", "'There are a zoo' is correct.", None, "F", "a zoo 是单数，要用 There is a zoo，are 用错，所以错。", 3),
                ("answer", "Tell one thing near your home.", None, "There is a library near my home.", "评分要点：用 There is a... 句型得 3 分；场所词正确得 2 分。", 4),
            ]},
            {"name": "方位介词 near / next to / behind", "explanation": "near 在附近、next to 紧挨着、behind 在后面、in front of 在前面、far 远；问 Where is the shop? 用 It's next to the park. 回答。", "questions": [
                ("choice", "The shop is right ___ the school.", ["next to", "behind", "far", "in front of"], "A", "right next to 是紧挨；behind、far、in front of 都不是，所以选 A。", 1),
                ("fill", "The tree is ___ the house, not in front.", None, "behind", "not in front 提示相反方位，在后面用 behind。", 2),
                ("judge", "'Near' means very far away.", None, "F", "near 是距离近，far 才是远，释义相反，所以错。", 3),
                ("answer", "Ask where the park is.", None, "Where is the park?", "评分要点：用 Where is...? 提问得 3 分；场所名词正确得 2 分。", 4),
            ]},
            {"name": "字母 Pp 发 /p/ 的首音辨识", "explanation": "Pp 在 park、pencil、play、purple、pink、pen 词首发 /p/，双唇送气、声带不振动；与 /b/ 的浊音相对，按首音归类。", "questions": [
                ("choice", "Which word begins like 'park'?", ["pencil", "van", "web", "lip"], "A", "pencil 与 park 都发 /p/ 起首；van、web、lip 不同，所以选 A。", 1),
                ("fill", "Two Pp words are ___ and ___.", None, ["play", "pink"], "play 与 pink 都以 p 开头发 /p/，填同首音词。", 2),
                ("judge", "You hear /p/ at the start of 'purple'.", None, "T", "purple 词首是 p，发 /p/，判断正确，所以对。", 3),
                ("answer", "Think of two /p/ words.", None, "pink, pen", "评分要点：两个 /p/ 首音词各得 2 分；拼写正确再得 1 分。", 4),
            ]},
        ]},
        {"name": "Unit 5 What do you like about farms?", "summary": "认读 cow/duck/hen/sheep/horse 等农场动物与 moo/quack 叫声，用 How many...? There are... 数动物，学字母 Dd 的 /d/。", "points": [
            {"name": "农场动物名词", "explanation": "cow 产奶、hen 下蛋、duck 会游、sheep 产毛、horse 能骑、goat 与 pig 也养在农场；按外形与产物区分，sheep 是羊不是鸟。", "questions": [
                ("choice", "Which animal gives us milk?", ["A cow", "A hen", "A duck", "A horse"], "A", "奶牛 cow 产奶；hen 下蛋、duck 会游、horse 能骑，所以选 A。", 1),
                ("fill", "A ___ lays eggs and a ___ says quack.", None, ["hen", "duck"], "母鸡 hen 下蛋，鸭子 duck 叫 quack，按特征填。", 2),
                ("judge", "A sheep is a farm bird.", None, "F", "sheep 是有毛的羊，不是鸟；hen、duck 才是禽，所以错。", 3),
                ("answer", "Name two animals on a farm.", None, "a cow, a horse", "评分要点：两个不同农场动物各得 2 分；拼写正确得 1 分。", 4),
            ]},
            {"name": "动物叫声拟声词", "explanation": "cow 叫 moo、duck 叫 quack、hen 叫 cluck、sheep 叫 baa、horse 叫 neigh、pig 叫 oink；句型 The cow says \"moo.\" 把动物与声音配对。", "questions": [
                ("choice", "What does a duck say?", ["Moo", "Quack", "Baa", "Neigh"], "B", "鸭子叫 Quack；Moo 是牛、Baa 是羊、Neigh 是马，所以选 B。", 1),
                ("fill", "The cow says ___ and the hen says ___.", None, ["moo", "cluck"], "牛叫 moo、母鸡叫 cluck，按动物配拟声词。", 2),
                ("judge", "A horse says 'oink'.", None, "F", "oink 是猪叫，马叫 neigh，搭配错误，所以错。", 3),
                ("answer", "Write the sound a sheep makes.", None, "baa", "评分要点：写出 baa 得 3 分；用 The sheep says... 成句再得 2 分。", 4),
            ]},
            {"name": "How many...? There are... 数词问答", "explanation": "问 How many cows? 答 There are + 数词 + 复数名词；one 后接单数，two 起接复数并加 -s，如 three ducks、one cow。", "questions": [
                ("choice", "How many legs does a hen have?", ["Two", "One", "Four", "Six"], "A", "母鸡两条腿 Two；One 太少、Four 是牛马、Six 是昆虫，所以选 A。", 1),
                ("fill", "There are ___ ducks and ___ cow.", None, ["three", "one"], "ducks 复数填 three，cow 单数填 one，数词与单复数对应。", 2),
                ("judge", "We say 'two cow' in English.", None, "F", "two 后名词加 -s，正确是 two cows，所以错。", 3),
                ("answer", "Ask how many pigs there are.", None, "How many pigs are there?", "评分要点：用 How many...? 提问得 3 分；名词用复数再得 2 分。", 4),
            ]},
            {"name": "字母 Dd 发 /d/ 的首音辨识", "explanation": "Dd 在 duck、dog、desk、door、dig 词首发 /d/，舌尖抵上齿龈、声带振动；与 /t/ 的清音相对，把首音相同的词归一类。", "questions": [
                ("choice", "Say these. Which one starts with /d/?", ["duck", "box", "hat", "key"], "A", "duck 以 d 开头发 /d/；box、hat、key 首音不同，所以选 A。", 1),
                ("fill", "___ and ___ start with Dd.", None, ["dog", "door"], "dog 与 door 词首都是 d，发 /d/。", 2),
                ("judge", "'Desk' and 'dig' share the /d/ sound.", None, "T", "两词词首都是 d，首音相同，判断正确，所以对。", 3),
                ("answer", "Give two words that start with /d/.", None, "desk, dig", "评分要点：两个 /d/ 首音词各得 2 分；拼写正确再得 1 分。", 4),
            ]},
        ]},
        {"name": "Unit 6 How do people celebrate the Mid-Autumn Festival?", "summary": "认读 moon/mooncake/lantern 等中秋词，用 We eat... / We look at... 说庆祝活动，用 round/bright/full 描述月亮，学字母 Mm 的 /m/。", "points": [
            {"name": "中秋节名词", "explanation": "Mid-Autumn Festival 是中秋节，moon 月亮、mooncake 月饼、lantern 灯笼、story 故事、night 夜晚；mooncake 用来吃、lantern 用来提、moon 用来赏。", "questions": [
                ("choice", "What do people eat at this festival?", ["Mooncakes", "Lanterns", "The moon", "A story"], "A", "中秋吃月饼 Mooncakes；lantern 提、moon 看、story 讲，所以选 A。", 1),
                ("fill", "We look at the ___ and carry a ___.", None, ["moon", "lantern"], "赏月看 moon，提灯笼 carry a lantern，按活动填词。", 2),
                ("judge", "A lantern is a kind of cake.", None, "F", "lantern 是提的灯笼，mooncake 才是糕点，类别错，所以错。", 3),
                ("answer", "Name two things about this festival.", None, "the moon, mooncakes", "评分要点：两个不同节日事物各得 2 分；拼写正确得 1 分。", 4),
            ]},
            {"name": "We eat... / We look at... 庆祝句型", "explanation": "用 We + 动词 说一起做的事：We eat mooncakes. We look at the moon. We carry lanterns.；主语 We 是复数，动词不加 s，look at 是固定搭配。", "questions": [
                ("choice", "___ eat mooncakes at night.", ["We", "It", "He do", "She"], "A", "和同伴一起用 We；It 指物，He 与 She 是单数，所以选 A。", 1),
                ("fill", "We ___ at the full moon at night.", None, "look", "look at 是固定搭配，赏月用 look at the moon。", 2),
                ("judge", "'We looks at the moon' is right.", None, "F", "主语 We 是复数，动词用 look 不加 s，所以错。", 3),
                ("answer", "Say one thing you do at night.", None, "We eat mooncakes together.", "评分要点：用 We + 动词成句得 3 分；活动与中秋相关得 2 分。", 4),
            ]},
            {"name": "round / bright / full 描述月亮", "explanation": "round 圆、bright 亮、full 满、dim 暗、square 方、long 长、small 小；The moon is round and bright.，形容词放 be 后或名词前说 a round mooncake。", "questions": [
                ("choice", "The Mid-Autumn moon is ___.", ["Square", "Round", "Long", "Small"], "B", "中秋月是圆的 Round；Square 方、Long 长、Small 小，所以选 B。", 1),
                ("fill", "The moon is ___ tonight, not dim.", None, "bright", "not dim 提示反义，亮用 bright，放 be 后。", 2),
                ("judge", "We say 'a mooncake round'.", None, "F", "形容词放名词前，正确是 a round mooncake，语序错，所以错。", 3),
                ("answer", "Write one word for the full moon.", None, "round", "评分要点：写出 round 或 bright 得 3 分；用 The moon is... 成句再得 2 分。", 4),
            ]},
            {"name": "字母 Mm 发 /m/ 的首音辨识", "explanation": "Mm 在 moon、mooncake、mouth、map、mango 词首发 /m/，双唇闭合、气流从鼻出；与别的首音区分，按首音给词归类。", "questions": [
                ("choice", "Which word has /m/ first?", ["moon", "zip", "fan", "bed"], "A", "moon 以 m 开头发 /m/；zip、fan、bed 首音不同，所以选 A。", 1),
                ("fill", "Give two /m/ words: ___ and ___.", None, ["mouth", "map"], "mouth 与 map 都以 m 开头发 /m/。", 2),
                ("judge", "The letter m in 'mango' says /m/.", None, "T", "mango 词首 m 发 /m/，判断正确，所以对。", 3),
                ("answer", "List two /m/ words, please.", None, "mango, mooncake", "评分要点：两个 /m/ 首音词各得 2 分；拼写正确再得 1 分。", 4),
            ]},
        ]},
    ],
}

# 章末综合题：每章 2 道，使每章题量达到 18 道（_validate_daily.py 对整册的硬规则），
# 把本单元多个知识点串成真实交际情境题，挂在本章对应知识点上。
_REVIEW_Q = {
    "Unit 1 What can you do with your five senses?": [
        (0, ("choice", "Eyes closed, what can you still do?", ["See the cake", "Hear the music", "Read a card", "Watch a light"], "B", "闭眼不能看、读、看灯，耳朵仍能听音乐，所以选 B。", 3)),
        (1, ("answer", "Describe a rainy day with two senses.", None, "I can hear the rain. I can smell the wet ground.", "评分要点：两个不同感官动词各得 2 分；I can... 句型正确得 1 分。", 4)),
    ],
    "Unit 2 What do you like about your family?": [
        (0, ("choice", "A man is your mum's brother. Who is he?", ["Your uncle", "Your aunt", "Your grandpa", "Your cousin"], "A", "妈妈的兄弟是 uncle；aunt 为姨姑、grandpa 是祖辈、cousin 是同辈，所以选 A。", 3)),
        (2, ("answer", "Ask and answer about your aunt.", None, "Who is she? She is my aunt. She is kind.", "评分要点：Who is she? 提问得 2 分；She is my aunt 作答得 2 分；加形容词得 1 分。", 4)),
    ],
    "Unit 3 What is your favourite toy?": [
        (0, ("choice", "Which toy can move by itself?", ["A robot", "A kite", "A doll", "A book"], "A", "robot 能自己动；kite 靠风、doll 要人拿、book 不是玩具，所以选 A。", 3)),
        (2, ("answer", "Show a red ball. Say two sentences.", None, "This is my ball. It is red.", "评分要点：This is... 介绍玩具得 2 分；It is + 颜色得 2 分；两句完整得 1 分。", 4)),
    ],
    "Unit 4 What is around your home?": [
        (2, ("choice", "The park is close. Which word fits?", ["near", "behind", "far", "under"], "A", "close 就是近 near；far 反义，behind、under 说方位，所以选 A。", 3)),
        (1, ("answer", "Draw your home area. Say two sentences.", None, "There is a park near my home. The shop is next to it.", "评分要点：There is... 句型得 2 分；near 与 next to 方位得 2 分；两句连贯得 1 分。", 4)),
    ],
    "Unit 5 What do you like about farms?": [
        (0, ("choice", "'Moo' comes from the farm. What is it?", ["A hen", "A cow", "A duck", "A sheep"], "B", "moo 是牛叫，说明有 cow；其余动物叫声不同，所以选 B。", 3)),
        (2, ("answer", "Count the animals and tell your friend.", None, "There are four ducks and one cow on the farm.", "评分要点：There are + 数词 + 复数得 2 分；单复数一致得 2 分；成句得 1 分。", 4)),
    ],
    "Unit 6 How do people celebrate the Mid-Autumn Festival?": [
        (1, ("choice", "At night we sit outside. What do we do?", ["Watch the moon", "Eat the moon", "Carry a cake", "Read a lantern"], "A", "中秋夜赏月 Watch the moon；moon 不能吃、cake 不用提、lantern 不是读的，所以选 A。", 3)),
        (2, ("answer", "Tell a friend about the moon and food.", None, "The moon is round. We eat mooncakes.", "评分要点：用 round 或 bright 描述得 2 分；We eat... 说活动得 2 分；两句完整得 1 分。", 4)),
    ],
}
for _ch in PACK["chapters"]:
    for _idx, _q in _REVIEW_Q[_ch["name"]]:
        _ch["points"][_idx]["questions"].append(_q)
