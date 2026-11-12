# -*- coding: utf-8 -*-
"""重跑内容包：英语 三年级上册（牛津深圳版）。

按骨架索引八个单元建立节级知识点，每点 4 题，另用 _REVIEW_Q 每章补 2 道章末综合题，
每章 18 题、全册 144 题。题干与选项用英文、解析用中文，词汇按单元主题递进不混用。
"""
PACK = {
    "subject": "english", "grade": 3, "version": "牛津深圳版", "semester": "first",
    "chapters": [
        {"name": "Unit 1 How do we feel?", "summary": "学习感觉形容词，用 How do you feel? 问答，练短音 a，并学会关心同伴、礼貌回应。", "points": [
            {"name": "感觉形容词词义辨认", "explanation": "happy 开心、sad 伤心、angry 生气、tired 累、hungry 饿、thirsty 渴、afraid 怕；用 I'm 加形容词说感觉。", "questions": [
                ("choice", "Tom lost his pen. He is ____.", ["sad", "happy", "glad", "fine"], "A", "丢了笔会难过，其余三项都表开心或还好，所以选 A。", 1),
                ("fill", "I want water. I am ____.", None, "thirsty", "想喝水说明口渴，用 thirsty，不是 hungry。", 2),
                ("judge", "'Angry' means very happy.", None, "F", "angry 是生气，不是开心，所以说法错误。", 2),
                ("choice", "Ben wants to sleep. He feels ____.", ["tired", "hungry", "afraid", "sad"], "A", "想睡觉是累了，其余三项是饿、怕、伤心，所以选 A。", 4),
            ]},
            {"name": "How do you feel? 问答与 be 动词", "explanation": "问感觉用 How do you feel? 答 I'm happy；说别人换成 He's 或 She's，am 与 is 别混用。", "questions": [
                ("choice", "How do you feel? —____ fine.", ["I'm", "He's", "She's", "It's"], "A", "回答自己用 I'm，其余三项说的是别人或物，所以选 A。", 1),
                ("fill", "How ____ Amy feel? She is tired.", None, "does", "主语 Amy 是第三人称单数，疑问句用 does。", 2),
                ("judge", "'I am happy.' is a right answer.", None, "T", "I'm happy 可回答感觉，be 动词搭配正确，所以说法正确。", 3),
                ("choice", "Sam feels sad. ____ needs a hug.", ["He", "She", "I", "It"], "A", "Sam 是男孩名用 He，其余三项不指 Sam，所以选 A。", 4),
            ]},
            {"name": "短音 a 读 /æ/ 的辨读", "explanation": "sad、happy、angry 里的 a 读短音 /æ/，嘴张大；name、game 里 a-e 读 /eɪ/，要分清。", "questions": [
                ("choice", "Which word has the /æ/ sound?", ["sad", "name", "game", "late"], "A", "sad 的 a 读 /æ/，其余三项 a-e 读 /eɪ/，所以选 A。", 1),
                ("fill", "Sad and happy have short ____.", None, "a", "两词中的 a 都读短音 /æ/，不是字母名。", 2),
                ("judge", "In 'angry', the a says /eɪ/.", None, "F", "angry 的 a 读 /æ/，不是 /eɪ/，所以说法错误。", 3),
                ("choice", "Which word rhymes with 'sad'?", ["bad", "bed", "box", "bun"], "A", "bad 与 sad 同韵 /æd/，其余韵脚都不同，所以选 A。", 4),
            ]},
            {"name": "关心同伴的交际用语", "explanation": "同伴不开心可问 Are you OK?，答 Yes, I'm fine now.；安慰说 Don't worry.，请求加 please 更礼貌。", "questions": [
                ("choice", "Friend looks sad. You say: ____", ["Are you OK?", "Go away!", "How old?", "Sit down!"], "A", "关心同伴问 Are you OK?，其余三项都不合情境，所以选 A。", 1),
                ("fill", "—Are you OK? —Yes, I'm ____ now.", None, "fine", "被关心后说 I'm fine now，表示现在好些了。", 2),
                ("judge", "'Don't worry.' can calm a friend.", None, "T", "Don't worry 用来安慰同伴，用语得体，所以说法正确。", 3),
                ("answer", "Write two lines to a sad friend.", None, "Are you OK? Don't worry. I am here.", "评分要点：关心问句 2 分；安慰句 2 分；句子完整、语气友好 1 分。", 4),
            ]},
        ]},
        {"name": "Unit 2 What's interesting about families?", "summary": "辨认家庭成员称谓，练 Who is he/she? 与 This is...，辨词尾 er 弱读，学会介绍家人与选用 my、your。", "points": [
            {"name": "家庭成员称谓的辨认", "explanation": "father 爸爸、mother 妈妈、grandfather 爷爷、grandmother 奶奶、uncle 叔叔、aunt 阿姨、cousin 堂表兄妹，按辈分性别区分。", "questions": [
                ("choice", "Mum's mum is my ____.", ["grandmother", "grandfather", "aunt", "cousin"], "A", "外婆是 grandmother，其余三项性别或辈分不符，所以选 A。", 1),
                ("fill", "Dad's brother is my ____.", None, "uncle", "爸爸的兄弟是叔叔，用 uncle，aunt 指女性长辈。", 2),
                ("judge", "'Cousin' means your father.", None, "F", "cousin 是堂表兄弟姐妹，不是父亲，所以说法错误。", 2),
                ("choice", "My mum's sister is my ____.", ["aunt", "uncle", "grandma", "sister"], "A", "妈妈的姐妹是阿姨，其余三项性别或辈分不对，所以选 A。", 4),
            ]},
            {"name": "Who is he/she? 与 This is... 问答", "explanation": "介绍家人用 This is my father.，问身份用 Who is he? 或 Who is she?，答 He's 或 She's my...，别把 he 与 she 弄反。", "questions": [
                ("choice", "____ is she? She's my aunt.", ["Who", "What", "How", "Where"], "A", "问人身份用 Who，其余三项问事物、方式、地点，所以选 A。", 1),
                ("fill", "This ____ my grandfather.", None, "is", "介绍单数家人用 This is，be 动词用 is。", 2),
                ("judge", "Ask 'Who is he?' about a girl.", None, "F", "女孩用 she，he 指男孩，所以说法错误。", 3),
                ("choice", "Point to a boy. You ask: ____", ["Who's he?", "Who's she?", "What's it?", "How's he?"], "A", "指男孩问 Who's he?，其余三项人称或疑问词不对，所以选 A。", 4),
            ]},
            {"name": "词尾 er 弱读 /ə/ 的辨读", "explanation": "father、mother、brother、sister、grandfather 词尾 er 读轻音 /ə/，不重读；拼写都是 er，不是 ar 或 or。", "questions": [
                ("choice", "Which word ends with /ə/?", ["sister", "cap", "pen", "map"], "A", "sister 词尾 er 读 /ə/，其余三项无此结尾，所以选 A。", 1),
                ("fill", "Father, mother: both end in ____.", None, "er", "两词词尾都是 er，读轻音 /ə/。", 2),
                ("judge", "The 'er' in 'brother' is stressed.", None, "F", "brother 重音在前，er 读轻音 /ə/，所以说法错误。", 3),
                ("choice", "Which word rhymes with 'mother'?", ["brother", "father", "sister", "uncle"], "A", "brother 与 mother 同韵，其余三项韵脚不同，所以选 A。", 4),
            ]},
            {"name": "介绍家人时 my 与 your 的选用", "explanation": "见面说 This is my family.，介绍自己家人用 my，问对方用 your；初次回应 Nice to meet you.，问人数用 How many。", "questions": [
                ("choice", "Is this ____ dad? Yes, he is.", ["your", "my", "his", "her"], "A", "问对方的爸爸用 your，其余三项人称不符，所以选 A。", 1),
                ("fill", "____ many people? Five.", None, "How", "问人数用 How many，答语给出数量。", 2),
                ("judge", "'Nice to meet you.' is polite.", None, "T", "初次见家人说这句很礼貌，所以说法正确。", 3),
                ("answer", "Write two lines about your family.", None, "This is my family. I have a brother.", "评分要点：介绍句 2 分；写出一位家人 2 分；句子完整、书写正确 1 分。", 4),
            ]},
        ]},
        {"name": "Unit 3 What do we look like?", "summary": "辨认五官与外貌形容词，练 I have 与 He has、his 与 her，辨短音 i 与 i-e，并学会描述长相。", "points": [
            {"name": "五官与外貌形容词词义", "explanation": "hair 头发、eyes 眼睛、nose 鼻子、mouth 嘴、ears 耳朵；long 与 short 说长短，big 与 small 说大小，tall 说个子高。", "questions": [
                ("choice", "We see with our ____.", ["eyes", "ears", "nose", "mouth"], "A", "看东西用眼睛，其余三项是听、闻、说话的器官，所以选 A。", 1),
                ("fill", "I have two big ____. I see well.", None, "eyes", "看东西用两只眼睛，two 后接复数 eyes。", 2),
                ("judge", "'Short hair' means long hair.", None, "F", "short 是短，long 才是长，所以说法错误。", 2),
                ("choice", "My friend is ____, not short.", ["tall", "big", "round", "thin"], "A", "后句说个子不矮，用 tall，其余三项不表身高，所以选 A。", 4),
            ]},
            {"name": "I have 与 He has 的选用", "explanation": "说自己用 I have big eyes.，说第三人称单数用 He 或 She has...；物主用 his 或 her，别把 have 与 has 混用。", "questions": [
                ("choice", "I ____ two small ears.", ["have", "has", "am", "is"], "A", "主语 I 用 have，has 只跟第三人称单数，am 与 is 不接名词，所以选 A。", 1),
                ("fill", "Lily ____ long hair. It is black.", None, "has", "Lily 是第三人称单数，动词用 has。", 2),
                ("judge", "'He have big eyes.' is right.", None, "F", "He 后要用 has，不用 have，所以说法错误。", 3),
                ("choice", "____ hair is short. He is a boy.", ["His", "Her", "My", "Your"], "A", "后句点明是男孩，物主用 His，其余三项人称不符，所以选 A。", 4),
            ]},
            {"name": "短音 i 与 i-e 长音的辨读", "explanation": "big、thin、pink 里 i 读短音 /ɪ/；bike、nine、like 里 i-e 读 /aɪ/，末尾 e 不发音但让 i 读字母名。", "questions": [
                ("choice", "Which word has short /ɪ/?", ["big", "bike", "nine", "like"], "A", "big 的 i 读 /ɪ/，其余三项 i-e 读 /aɪ/，所以选 A。", 1),
                ("fill", "'Bike' ends with a silent ____.", None, "e", "bike 末尾 e 不发音，只让 i 读 /aɪ/。", 2),
                ("judge", "'Thin' and 'nine' share one sound.", None, "F", "thin 是 /ɪ/，nine 是 /aɪ/，读音不同，所以说法错误。", 3),
                ("choice", "Which word rhymes with 'big'?", ["dig", "den", "bag", "bug"], "A", "dig 与 big 同韵 /ɪg/，其余韵脚都不同，所以选 A。", 4),
            ]},
            {"name": "描述长相的问句与应答", "explanation": "问长相用 What do you look like?，答 I'm tall. 或 I have short hair.；look like 是固定搭配，不能少 like。", "questions": [
                ("choice", "____ do you look like? I'm tall.", ["What", "Who", "How", "Where"], "A", "问长相用 What 加 look like，其余三项疑问词不对，所以选 A。", 1),
                ("fill", "What does he look ____? He's thin.", None, "like", "look like 固定搭配，问长相不能少 like。", 2),
                ("judge", "'I have big eyes.' tells a look.", None, "T", "这句用 have 加五官描述长相，所以说法正确。", 3),
                ("answer", "Write two lines about your face.", None, "I have two big eyes. My nose is small.", "评分要点：写出一处五官 2 分；用对 have 或 is 2 分；句子完整 1 分。", 4),
            ]},
        ]},
        {"name": "Unit 4 How do we have fun?", "summary": "辨认玩耍动作词，练 can 与 can't 问答，辨短音 o 与 o-e，并学会用 Let's 发出邀请与回应。", "points": [
            {"name": "玩耍动作动词词义辨认", "explanation": "run 跑、jump 跳、swim 游泳、sing 唱歌、dance 跳舞、draw 画画、skip 跳绳、fly a kite 放风筝，都是玩乐活动词。", "questions": [
                ("choice", "We ____ in the pool in summer.", ["swim", "sing", "draw", "read"], "A", "在水池里是游泳，其余三项都不在水里做，所以选 A。", 1),
                ("fill", "I ____ a song with my class.", None, "sing", "song 搭配动词 sing，表示唱一首歌。", 2),
                ("judge", "'Jump' means to move on water.", None, "F", "jump 是双脚离地跳，在水里移动是 swim，所以说法错误。", 2),
                ("choice", "Hold a rope and ____ over it.", ["skip", "swim", "sing", "draw"], "A", "拿绳子跳过是跳绳，其余三项与绳子无关，所以选 A。", 4),
            ]},
            {"name": "can 与 can't 表达能力", "explanation": "说能力用 I can swim.，疑问把 can 提前：Can you dance? 答 Yes, I can. 或 No, I can't.；can 后动词用原形。", "questions": [
                ("choice", "____ you ride a bike? Yes, I can.", ["Can", "Are", "Do", "Is"], "A", "问能力用 Can 开头，其余三项助动词不对，所以选 A。", 1),
                ("fill", "I can ____ a kite in the park.", None, "fly", "fly a kite 是固定说法，can 后接动词原形。", 2),
                ("judge", "'I can swims.' is correct.", None, "F", "can 后动词用原形 swim，不加 s，所以说法错误。", 3),
                ("choice", "—Can you dance? —No, I ____.", ["can't", "can", "am not", "don't"], "A", "否定回答用 can't，其余三项与 can 不呼应，所以选 A。", 4),
            ]},
            {"name": "短音 o 与 o-e 长音的辨读", "explanation": "hop、box、hot 里 o 读短音 /ɒ/；note、home、rope 里 o-e 读 /əʊ/，末尾 e 让 o 读字母名。", "questions": [
                ("choice", "Which word has short /ɒ/?", ["hop", "note", "home", "rope"], "A", "hop 的 o 读 /ɒ/，其余三项 o-e 读 /əʊ/，所以选 A。", 1),
                ("fill", "'Home' has o-e. The o says ____.", None, "/əʊ/", "home 里 o-e 读字母名 /əʊ/，不是短音。", 2),
                ("judge", "'Hop' and 'hope' sound the same.", None, "F", "hop 读 /ɒ/，hope 读 /əʊ/，不同音，所以说法错误。", 3),
                ("choice", "Which word rhymes with 'hop'?", ["top", "tap", "tip", "tub"], "A", "top 与 hop 同韵 /ɒp/，其余韵脚都不同，所以选 A。", 4),
            ]},
            {"name": "Let's 邀请与礼貌应答", "explanation": "邀请一起玩用 Let's run! 或 Let's swim!，后接动词原形不加 to；同意说 Great! 或 OK!，婉拒说 Sorry, I can't.", "questions": [
                ("choice", "____ play ball together! Great!", ["Let's", "Lets", "Let", "It's"], "A", "Let's 后接动词原形表邀请，其余三项形式不对，所以选 A。", 1),
                ("fill", "—Let's swim! —____! It is fun.", None, "Great", "赞同邀请可用 Great!，表示乐意一起去。", 2),
                ("judge", "Say 'Let's to run.' to invite.", None, "F", "Let's 后直接接动词原形，不加 to，所以说法错误。", 3),
                ("answer", "Write two lines to ask a friend.", None, "Let's fly a kite! Can you come?", "评分要点：写出 Let's 邀请句 2 分；动词用原形 2 分；语气友好 1 分。", 4),
            ]},
        ]},
        {"name": "Unit 5 What do we eat?", "summary": "辨认食物与饮料名词，练 Do you like...? 与 some，辨短音 u 与 u-e，并学会点餐与餐桌礼貌用语。", "points": [
            {"name": "食物与饮料名词词义", "explanation": "rice 米饭、noodles 面条、bread 面包、milk 牛奶、soup 汤、juice 果汁、carrot 胡萝卜；分清吃的东西与喝的东西。", "questions": [
                ("choice", "We drink ____ with a straw.", ["juice", "rice", "bread", "noodles"], "A", "用吸管喝的是果汁，其余三项都要嚼着吃，所以选 A。", 1),
                ("fill", "____ is white and we drink it.", None, "Milk", "白色且用来喝的是牛奶 milk，句首大写。", 2),
                ("judge", "'Noodles' are a kind of drink.", None, "F", "noodles 是面条，属于食物不是饮料，所以说法错误。", 2),
                ("choice", "Which one is a vegetable?", ["carrot", "milk", "bread", "juice"], "A", "carrot 是蔬菜，其余三项是奶、面包、果汁，所以选 A。", 4),
            ]},
            {"name": "Do you like...? 与 some 的用法", "explanation": "问喜好用 Do you like milk? 答 Yes, I do. 或 No, I don't.；请人吃说 Have some rice.，some 可跟不可数名词。", "questions": [
                ("choice", "____ you like soup? Yes, I do.", ["Do", "Are", "Can", "Is"], "A", "问喜好用 Do，答语 I do 呼应；其余三项不搭配，所以选 A。", 1),
                ("fill", "Have ____ bread, please. Thanks.", None, "some", "请人吃东西用 some，bread 不可数不加 a。", 2),
                ("judge", "'I don't like fish.' says no.", None, "T", "don't like 表示不喜欢，是否定回答，所以说法正确。", 3),
                ("choice", "—Do you like juice? —No, I ____.", ["don't", "do", "am not", "can't"], "A", "否定回答用 don't，其余三项与 Do 不呼应，所以选 A。", 4),
            ]},
            {"name": "短音 u 与 u-e 长音的辨读", "explanation": "cup、sun、cut 里 u 读短音 /ʌ/；cute、tube、use 里 u-e 读 /juː/，末尾 e 不发音但改变元音。", "questions": [
                ("choice", "Which word has short /ʌ/?", ["cup", "cute", "tube", "use"], "A", "cup 的 u 读 /ʌ/，其余三项 u-e 读 /juː/，所以选 A。", 1),
                ("fill", "'Cute' ends with silent ____.", None, "e", "cute 末尾 e 不发音，让 u 读 /juː/。", 2),
                ("judge", "'Cup' and 'cute' share one vowel.", None, "F", "cup 读 /ʌ/，cute 读 /juː/，元音不同，所以说法错误。", 3),
                ("choice", "Which word rhymes with 'cup'?", ["pup", "pen", "pig", "pop"], "A", "pup 与 cup 同韵 /ʌp/，其余韵脚都不同，所以选 A。", 4),
            ]},
            {"name": "点餐与餐桌礼貌用语", "explanation": "想吃说 Can I have some rice, please?，递给别人说 Here you are.，回应 Thank you. 或 Yummy!；请求要加 please。", "questions": [
                ("choice", "You want rice. Say: ____", ["Rice, please", "Give me", "I want", "No rice"], "A", "加 please 才有礼貌，其余三项生硬或拒绝，所以选 A。", 1),
                ("fill", "—Here you are. —____ you.", None, "Thank", "别人递来东西要道谢，用 Thank you。", 2),
                ("judge", "Say 'Yummy!' to thank the cook.", None, "T", "Yummy 夸食物好吃，是对做饭人的肯定，所以说法正确。", 3),
                ("answer", "Write two lines to order food.", None, "Can I have some noodles, please? Thank you.", "评分要点：点餐句 2 分；用 please 或 some 2 分；有道谢 1 分。", 4),
            ]},
        ]},
        {"name": "Unit 6 What do we like about small animals?", "summary": "辨认小动物名称与身体部位，练 It has 描述特征，辨短音 e 与 ee，并学会表达喜爱与照顾宠物。", "points": [
            {"name": "小动物名称词义辨认", "explanation": "cat 猫、dog 狗、rabbit 兔子、bird 鸟、mouse 老鼠、turtle 龟、hamster 仓鼠、chick 小鸡，按外形与住处区分。", "questions": [
                ("choice", "Long ears, soft fur. It is a ____.", ["rabbit", "turtle", "mouse", "bird"], "A", "长耳软毛是兔子，其余三项外形不符，所以选 A。", 1),
                ("fill", "A ____ has a hard shell.", None, "turtle", "有硬壳、爬得慢的是乌龟 turtle。", 2),
                ("judge", "A 'hamster' is a big farm animal.", None, "F", "hamster 仓鼠是小型宠物，不是大牲畜，所以说法错误。", 2),
                ("choice", "Up in a tree. Which has wings?", ["bird", "cat", "dog", "mouse"], "A", "树上会飞的是鸟，其余三种没有翅膀，所以选 A。", 4),
            ]},
            {"name": "It has 描述动物特征", "explanation": "说动物特征用 It has a long tail. 或 It has soft fur.；主语 it 用 has，两个特征可用 and 连起来。", "questions": [
                ("choice", "A rabbit ____ two long ears.", ["has", "have", "is", "are"], "A", "主语单数用 has，其余三项搭配不对，所以选 A。", 1),
                ("fill", "A cat has soft ____ on its body.", None, "fur", "猫身上软软的是毛，用 fur，不是羽毛。", 2),
                ("judge", "'It have a short tail.' is right.", None, "F", "it 后要用 has，不用 have，所以说法错误。", 3),
                ("choice", "A mouse has a long ____.", ["tail", "wing", "shell", "beak"], "A", "老鼠有长尾巴，其余三项是鸟或龟的部位，所以选 A。", 4),
            ]},
            {"name": "短音 e 与 ee 长音的辨读", "explanation": "pet、net、red 里 e 读短音 /e/；see、bee、tree 里 ee 读长音 /iː/，两个 e 连读成一个长音。", "questions": [
                ("choice", "Which word has long /iː/?", ["see", "pet", "net", "red"], "A", "see 的 ee 读 /iː/，其余三项 e 读 /e/，所以选 A。", 1),
                ("fill", "'Pet' has one ____. It says /e/.", None, "e", "pet 里单个 e 读短音 /e/，不是 ee。", 2),
                ("judge", "'Bee' and 'bed' sound the same.", None, "F", "bee 读 /iː/，bed 读 /e/，元音不同，所以说法错误。", 3),
                ("choice", "Which word rhymes with 'see'?", ["tree", "trip", "trap", "top"], "A", "tree 与 see 同韵 /iː/，其余韵脚都不同，所以选 A。", 4),
            ]},
            {"name": "表达喜爱与照顾宠物", "explanation": "说喜欢用 I like cats. 或 It's cute.，问原因用 What do you like about it?；照顾宠物要 feed it，给它食物。", "questions": [
                ("choice", "____ do you like about rabbits?", ["What", "Who", "Where", "How"], "A", "问喜欢哪一点用 What 加 about，其余疑问词不对，所以选 A。", 1),
                ("fill", "I ____ my cat. It is cute.", None, "like", "表达喜欢用 like，后句给出喜欢的理由。", 2),
                ("judge", "'Feed' means give food to a pet.", None, "T", "feed 是喂食，即给宠物东西吃，所以说法正确。", 3),
                ("answer", "Write two lines about a pet.", None, "I like my rabbit. It has long ears.", "评分要点：写出喜欢的动物 2 分；用 It has 描述特征 2 分；句子完整 1 分。", 4),
            ]},
        ]},
        {"name": "Unit 7 What do we know about weather?", "summary": "辨认天气形容词，练 How's the weather? 问答，辨词尾 y 读 /i/，并学会按天气选衣物与给出提醒。", "points": [
            {"name": "天气形容词词义辨认", "explanation": "sunny 晴、rainy 雨、windy 风、cloudy 多云、snowy 雪；都由天气名词加 y 构成，词尾 y 读 /i/。", "questions": [
                ("choice", "The sun is bright. It is ____.", ["sunny", "rainy", "snowy", "windy"], "A", "阳光明亮是晴天，其余三项与太阳不符，所以选 A。", 1),
                ("fill", "Take an umbrella. It is ____.", None, "rainy", "带伞说明下雨，用 rainy。", 2),
                ("judge", "'Snowy' means a lot of sun.", None, "F", "snowy 是下雪，不是出太阳，所以说法错误。", 2),
                ("choice", "Trees move. It is ____ today.", ["windy", "sunny", "snowy", "cloudy"], "A", "树摇说明有风，其余三项不会让树摇，所以选 A。", 4),
            ]},
            {"name": "How's the weather? 问答与 It's", "explanation": "问天气用 How's the weather?，答 It's rainy. 或 It's a windy day.；主语用 it，别用 I'm 回答天气。", "questions": [
                ("choice", "____ the weather? It's cloudy.", ["How's", "Who's", "What's", "Where's"], "A", "问天气用 How's，What's 要加 like，其余不搭配，所以选 A。", 1),
                ("fill", "It ____ cold today. Put on a coat.", None, "is", "说天气用 It is，主语 it 搭配 is。", 2),
                ("judge", "Answer weather with 'I'm fine'.", None, "F", "I'm fine 答感觉，天气要用 It's，所以说法错误。", 3),
                ("choice", "It's ____. No umbrella today.", ["sunny", "rainy", "snowy", "windy"], "A", "不用伞说明是晴天，其余三项多需遮挡，所以选 A。", 4),
            ]},
            {"name": "词尾 y 读 /i/ 的辨读", "explanation": "sunny、rainy、windy、cloudy、snowy 词尾 y 都读 /i/，轻而短；名词加 y 就变成形容天气的词。", "questions": [
                ("choice", "Which word ends with /i/?", ["windy", "wind", "sun", "rain"], "A", "windy 词尾 y 读 /i/，其余三项是名词收尾，所以选 A。", 1),
                ("fill", "Rain plus y makes ____.", None, "rainy", "名词 rain 加 y 变形容词 rainy，表示下雨的。", 2),
                ("judge", "In 'sunny', y says /aɪ/.", None, "F", "sunny 词尾 y 读 /i/，不是 /aɪ/，所以说法错误。", 3),
                ("choice", "Which word rhymes with 'sunny'?", ["funny", "sun", "rain", "wind"], "A", "funny 与 sunny 同韵，其余三项韵脚不同，所以选 A。", 4),
            ]},
            {"name": "按天气选衣物与提醒", "explanation": "雨天说 Take an umbrella. 或 Put on your raincoat.，冷天说 Put on your coat.，热天说 Take off your coat.，提醒要对应天气。", "questions": [
                ("choice", "It's rainy. Take your ____.", ["umbrella", "shorts", "fan", "cap"], "A", "下雨要带伞，其余三项是热天或不挡雨的用品，所以选 A。", 1),
                ("fill", "It's cold. ____ on your coat.", None, "Put", "穿上外套用 Put on，固定搭配。", 2),
                ("judge", "Wear a raincoat on a sunny day.", None, "F", "雨衣在雨天穿，晴天穿不对，所以说法错误。", 3),
                ("answer", "Write two lines for a rainy day.", None, "It is rainy. Take an umbrella.", "评分要点：天气句 2 分；写出对应用具 2 分；建议合理、句子完整 1 分。", 4),
            ]},
        ]},
        {"name": "Unit 8 Why do we like birthdays?", "summary": "辨认生日聚会物品，练 How old are you? 与年龄表达，辨 ir 读 /ɜː/，并学会祝福、送礼物与致谢。", "points": [
            {"name": "生日物品名词词义辨认", "explanation": "birthday 生日、cake 蛋糕、candle 蜡烛、present 礼物、balloon 气球、card 贺卡、wish 愿望，都是聚会上的具体物品。", "questions": [
                ("choice", "We put ____ on a cake and blow.", ["candles", "balloons", "cards", "gifts"], "A", "插在蛋糕上吹灭的是蜡烛，其余三项不插蛋糕，所以选 A。", 1),
                ("fill", "Make a ____ before you blow.", None, "wish", "吹蜡烛前先许愿，固定说法 make a wish。", 2),
                ("judge", "A 'balloon' is a kind of card.", None, "F", "balloon 是气球，card 是贺卡，两物不同，所以说法错误。", 2),
                ("choice", "You give it to a friend. A ____.", ["present", "candle", "wish", "party"], "A", "送给朋友的是礼物，其余三项不是送的物品，所以选 A。", 4),
            ]},
            {"name": "How old are you? 与年龄表达", "explanation": "问年龄用 How old are you? 答 I'm nine. 或 I'm ten.；说年龄用 be 动词，别说 I have nine。", "questions": [
                ("choice", "____ old are you? I'm nine.", ["How", "What", "Who", "Where"], "A", "问年龄用 How old，其余三项疑问词不对，所以选 A。", 1),
                ("fill", "I ____ nine. It's my birthday.", None, "am", "说年龄用 be 动词，主语 I 搭配 am。", 2),
                ("judge", "'I have nine.' tells your age.", None, "F", "说年龄用 I'm nine，have 表示拥有，所以说法错误。", 3),
                ("choice", "Nine candles. You are ____.", ["nine", "ten", "eight", "seven"], "A", "蜡烛数等于年龄，九支是九岁，其余三项数字不符，所以选 A。", 4),
            ]},
            {"name": "字母组合 ir 读 /ɜː/ 的辨读", "explanation": "birthday、girl、first、shirt 里 ir 读 /ɜː/，不读 /aɪ/；与 ar、or 的拼写和读音都要分清。", "questions": [
                ("choice", "Which word has /ɜː/?", ["girl", "go", "gum", "gap"], "A", "girl 的 ir 读 /ɜː/，其余三项元音不同，所以选 A。", 1),
                ("fill", "Birthday has 'ir'. It says ____.", None, "/ɜː/", "birthday 里 ir 读 /ɜː/，不是 /aɪ/。", 2),
                ("judge", "In 'shirt', ir says /aɪ/.", None, "F", "shirt 里 ir 读 /ɜː/，不是 /aɪ/，所以说法错误。", 3),
                ("choice", "Which word has 'ir' inside?", ["shirt", "short", "start", "star"], "A", "shirt 含 ir，其余三项是 or 或 ar，所以选 A。", 4),
            ]},
            {"name": "生日祝福与致谢的应答", "explanation": "祝寿说 Happy birthday!，送礼物说 Here's a present for you.，收礼答 Thank you. 或 I like it!，回应要对应对方的话。", "questions": [
                ("choice", "A birthday wish starts with ____.", ["Happy", "Sorry", "Please", "Thanks"], "A", "生日祝语以 Happy 开头，其余三项不用于祝贺，所以选 A。", 1),
                ("fill", "—Here's a gift. —____ you!", None, "Thank", "收到礼物要道谢，用 Thank you。", 2),
                ("judge", "Say 'Thank you.' after a gift.", None, "T", "收到礼物道谢是礼貌回应，所以说法正确。", 3),
                ("answer", "Write two lines on a birthday card.", None, "Happy birthday! Here is a card for you.", "评分要点：祝福语 2 分；写出送卡句 2 分；书写完整、语气友好 1 分。", 4),
            ]},
        ]},
    ],
}

# 章末综合情境题：每章 2 道，挂在本章对应知识点上，使每章正好 18 题。
_REVIEW_Q = {
    "Unit 1 How do we feel?": [
        (3, ("choice", "Ann cries. What do you ask first?", ["Are you OK?", "Your name?", "How old?", "Where's Dad?"], "A", "先关心对方感受，其余三项问姓名年龄去处，所以选 A。", 3)),
        (3, ("judge", "After help, say 'I'm fine now.'", None, "T", "被帮助后说自己好些了，回应得体，所以说法正确。", 4)),
    ],
    "Unit 2 What's interesting about families?": [
        (0, ("choice", "A man is Dad's dad. Who is he?", ["Grandfather", "Uncle", "Cousin", "Brother"], "A", "爸爸的爸爸是爷爷，其余三项辈分不对，所以选 A。", 3)),
        (1, ("judge", "Use 'she' for your grandmother.", None, "T", "grandmother 是女性，代词用 she，所以说法正确。", 4)),
    ],
    "Unit 3 What do we look like?": [
        (1, ("choice", "____ hair is long. She is a girl.", ["Her", "His", "My", "Its"], "A", "女孩物主用 Her，其余三项性别或人称不符，所以选 A。", 3)),
        (1, ("judge", "Use 'has' with 'she', not 'have'.", None, "T", "she 是第三人称单数，动词用 has，所以说法正确。", 4)),
    ],
    "Unit 4 How do we have fun?": [
        (1, ("choice", "No pool. Which can we still do?", ["Sing a song", "Swim fast", "Dive in", "Float"], "A", "没水池不能游泳，唱歌仍可做，其余三项都需水，所以选 A。", 3)),
        (1, ("judge", "'Can you hop?' asks about ability.", None, "T", "Can you 用来问对方会不会做，所以说法正确。", 4)),
    ],
    "Unit 5 What do we eat?": [
        (3, ("choice", "Guest comes. What do you offer?", ["Some juice", "No food", "Go home", "My pen"], "A", "待客应请喝果汁，其余三项不礼貌或无关，所以选 A。", 3)),
        (3, ("judge", "'Have some soup.' is a kind offer.", None, "T", "请人喝汤是友好招待，所以说法正确。", 4)),
    ],
    "Unit 6 What do we like about small animals?": [
        (3, ("choice", "A chick is small. Which word fits?", ["cute", "tall", "loud", "old"], "A", "小动物用 cute 形容讨喜，其余三项不贴切，所以选 A。", 3)),
        (1, ("judge", "A bird has wings, so it can fly.", None, "T", "鸟有翅膀，能飞，因果成立，所以说法正确。", 4)),
    ],
    "Unit 7 What do we know about weather?": [
        (0, ("choice", "Grey sky. How's the weather?", ["Cloudy", "Sunny", "Snowy", "Windy"], "A", "天灰无太阳是多云，其余三项不符，所以选 A。", 3)),
        (2, ("judge", "'Windy' and 'wind' share a root.", None, "T", "windy 由 wind 加 y 构成，同源，所以说法正确。", 4)),
    ],
    "Unit 8 Why do we like birthdays?": [
        (3, ("choice", "Friend blows candles. Say: ____", ["Make a wish!", "Good night.", "Sit down.", "Thank you."], "A", "吹蜡烛前该许愿，其余三项不合时点，所以选 A。", 3)),
        (3, ("judge", "A card can carry birthday wishes.", None, "T", "贺卡上可写生日祝福，符合交际习惯，所以说法正确。", 4)),
    ],
}
for _ch in PACK["chapters"]:
    for _idx, _q in _REVIEW_Q[_ch["name"]]:
        _ch["points"][_idx]["questions"].append(_q)
