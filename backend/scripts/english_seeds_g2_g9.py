"""g2–g9 英语书面表达语料 + 汇总入口。

COMP_RAW[教材 id] = [(标题, 提示语, 最少词数, [3 条评分点], 参考范文)]
english_seeds_g2_g9 汇总成生成器需要的 SEEDS / COMPOSITIONS。
"""

from scripts.seed_data_lower import SEEDS_LOWER
from scripts.seed_data_upper import SEEDS_UPPER

SEEDS = {**SEEDS_LOWER, **SEEDS_UPPER}

COMP_RAW = {
    # g2 上册
    13: [
        ("My five senses", "用 5 句话介绍你的五官和你能做的事。", 30,
         ["写出 3 种感官", "使用 I can ... 句型", "句子完整、拼写正确"],
         "I have two eyes. I can see a bird. I have two ears. I can hear a song. I have a nose. I can smell a flower."),
        ("My family", "用 5 句话介绍你的家人。", 30,
         ["至少写 3 位家人", "使用 This is my ...", "句末标点正确"],
         "This is my father. He is tall. This is my mother. She is kind. This is my grandpa. I love my family."),
        ("My favourite toy", "用 5 句话介绍你最喜欢的玩具。", 30,
         ["点明玩具名称", "说明喜欢的原因", "使用 I like / I play 句型"],
         "My favourite toy is a robot. It is blue and small. I play with it after school. It can walk and sing. I like my robot very much."),
    ],
    # g2 下册
    14: [
        ("My room", "用 5 句话介绍你的房间。", 30,
         ["用 There is / There are", "使用方位介词", "写出 2 件以上物品"],
         "This is my room. There is a bed in my room. There is a desk near the window. There are two chairs. I like my room."),
        ("In the park", "用 5 句话写你和朋友在公园里做什么。", 30,
         ["使用 Let's ...", "写出 2 种活动", "语句通顺"],
         "Today I go to the park with my friend. Let's play on the slide. Let's swing high. We see green trees. We are happy."),
        ("Hot summer", "用 5 句话写夏天的天气和你做的事。", 30,
         ["描述天气", "写出 2 种活动", "用 It is ... 句型"],
         "It is hot in summer. The sun is bright. I swim with my father. I eat ice cream. Summer is fun."),
    ],
    # g3 上册
    21: [
        ("How I feel", "用 5 句话写你一天中的心情变化。", 35,
         ["写出 2 种以上情绪", "使用 I feel ...", "有简单原因说明"],
         "I feel happy in the morning. I play with my friends. After school I feel tired. I have much homework. At night I feel happy again."),
        ("My family", "用 6 句话介绍你的家庭。", 35,
         ["写 3 位家人", "使用 Who is he/she?", "句子结构正确"],
         "This is my family. My father is a doctor. My mother is a teacher. My grandparents live in the country. My aunt has two children. I love my family."),
        ("My birthday", "用 6 句话写你的生日。", 35,
         ["写出时间与年龄", "写 2 项活动", "使用 birthday / present 等词"],
         "My birthday is in May. I am eight years old. We eat a birthday cake. There are eight candles. I get a present from my friend. I am very happy."),
    ],
    # g3 下册
    22: [
        ("My free time", "用 6 句话写你在空闲时间做什么。", 35,
         ["写 2 种以上活动", "使用一般现在时", "有频度表达"],
         "In my free time I read books. I draw pictures after school. Sometimes I play football. I like music too. My free time is fun."),
        ("My friend", "用 6 句话介绍你的朋友。", 35,
         ["写外貌与性格", "使用 He/She has ...", "说明你们一起做什么"],
         "My friend is Tom. He is tall. He has short hair. He is kind and helpful. We play together after school. I like my friend."),
        ("Children's Day", "用 6 句话写你在儿童节做的事。", 35,
         ["写出日期", "写 2 项活动", "表达感受"],
         "Children's Day is on the first of June. We have a party at school. We sing and play games. I get a gift from my teacher. We are very happy."),
    ],
    # g4 上册
    29: [
        ("Where I live", "用 6 句话介绍你住的地方。", 40,
         ["使用 There is / There are", "写住所与周边", "使用方位介词"],
         "I live in a flat near the park. There is a small garden behind the house. There are two shops on the street. My room is on the second floor. I like my home."),
        ("My favourite season", "用 6 句话写你最喜欢的季节。", 40,
         ["点明季节", "写天气与活动", "说明喜欢的原因"],
         "My favourite season is autumn. It is cool and yellow. The leaves fall from the trees. I fly a kite with my friends. I like autumn very much."),
        ("Road safety", "用 6 句话写道路安全规则。", 40,
         ["使用 must / mustn't", "写 2 条以上规则", "语句通顺"],
         "We must stop at a red light. We must look left and right. We must cross at the crossing. We mustn't play on the road. Safety comes first."),
    ],
    # g4 下册
    30: [
        ("My daily schedule", "用 6 句话写你一天的作息。", 40,
         ["写出时间点", "使用一般现在时", "有先后顺序词"],
         "I get up at seven. I have breakfast at seven thirty. I go to school at eight. I do my homework after school. I go to bed at nine."),
        ("My favourite job", "用 6 句话写你喜欢的职业。", 40,
         ["点明职业", "说明工作内容", "说明喜欢原因"],
         "I want to be a doctor. A doctor helps sick people. Doctors work in a hospital. They must be careful and kind. I like this job very much."),
        ("How I get along with others", "用 6 句话写你与同学相处的做法。", 40,
         ["使用 share / help", "写 2 种做法", "有礼貌用语"],
         "I share my books with my friends. We help each other. I say sorry when I am wrong. I say thank you when others help me. We are good friends."),
    ],
    # g5 上册
    37: [
        ("My weekend", "用 6 句话写你的周末。", 45,
         ["使用频度副词", "写 2 项以上活动", "使用一般现在时"],
         "At the weekend I often visit my grandma. We always have lunch together. Sometimes I go to the park. I play football with my friends. My weekend is busy but fun."),
        ("How to stay healthy", "用 6 句话写保持健康的建议。", 45,
         ["使用 should", "写饮食与运动", "语句连贯"],
         "We should eat fruit and vegetables. We should not eat too much sugar. We should exercise every day. Children should sleep nine hours. Healthy habits keep us strong."),
        ("Protecting the Earth", "用 6 句话写保护地球的做法。", 45,
         ["使用 should / can", "写 2 种以上做法", "有环保主题词"],
         "The Earth is our home. We should protect it. We can recycle paper and bottles. We should not waste water. Small actions make a big difference."),
    ],
    # g5 下册
    38: [
        ("My plan for the weekend", "用 6 句话写你的周末计划。", 45,
         ["使用 will 或 be going to", "写 2 天安排", "有时间顺序"],
         "I have a plan for the weekend. On Saturday I will do my homework. Then I will visit my friend. On Sunday I will go swimming with my father. I am sure it will be fun."),
        ("A holiday trip", "用 6 句话写一次假期旅行。", 45,
         ["写地点与交通", "写 2 项活动", "表达感受"],
         "Last summer I went to the beach with my family. We travelled by train. We stayed in a hotel near the sea. I swam and played on the sand. It was a wonderful holiday."),
        ("A great invention", "用 6 句话写一项伟大的发明。", 45,
         ["点明发明", "说明用途", "说明它如何改变生活"],
         "Paper is a great invention. People write and print on paper. The wheel is another great invention. It helps people travel faster. Inventions make our life easier."),
    ],
    # g6 上册
    45: [
        ("Why people move", "用 6–8 句话写人们搬家的原因。", 50,
         ["使用 because", "使用一般过去时", "写出 2 种以上原因"],
         "People move to new places for many reasons. Some move because they find new jobs. Some move because their children go to a new school. My family moved last year. We like the new place because it is quiet."),
        ("How I keep myself safe", "用 6–8 句话写自我保护的做法。", 50,
         ["使用 should / mustn't", "写 2 条以上安全规则", "有具体情景"],
         "Safety is important. We should be careful with strangers. We mustn't play near busy roads. We should call for help when we are in danger. Following these rules keeps us safe."),
        ("A city I know", "用 6–8 句话介绍一座城市。", 50,
         ["使用 There be", "写场所与方位", "有总体评价"],
         "This is a big city. There are many streets and parks. There is a museum near the library. The city is busy but clean. I like living here."),
    ],
    # g6 下册
    46: [
        ("Changes in my life", "用 6–8 句话写你生活中的变化。", 50,
         ["使用过去与现在对比", "使用 used to", "有具体例子"],
         "My life has changed a lot. I used to walk to school, but now I take the bus. Our village has new roads and tall buildings. Life is easier than before."),
        ("Helping others", "用 6–8 句话写你如何帮助他人。", 50,
         ["写志愿活动", "使用一般过去时", "表达感受"],
         "Last Saturday I volunteered at the community centre. I helped old people carry things. I talked with them and cleaned the room. They were very happy. Helping others makes me happy too."),
        ("A storybook I like", "用 6–8 句话介绍一本你喜欢的故事书。", 50,
         ["写出书名与主角", "概述情节", "说明喜欢的理由"],
         "I like the story about five peas. Five peas live in a pod. One pea falls into the soil and grows. In the end it makes a beautiful flower. The story tells us to keep hope."),
    ],
    # g7 上册
    53: [
        ("Trying something new", "用 6–8 句话写一次尝试新事物的经历。", 60,
         ["使用现在进行时", "写出过程与感受", "有结果或收获"],
         "This term I am trying something new. I am learning to play the piano. At first I felt nervous. I practice every day and I am improving. Now I can play a short song."),
        ("A job I want", "用 6–8 句话写你理想的职业。", 60,
         ["点明职业", "说明所需技能", "说明选择原因"],
         "I want to be an engineer. Engineers design and build machines. The job needs maths and computer skills. I am studying hard for it. I hope to work in a big company."),
        ("My favourite film", "用 6–8 句话写一部你喜欢的电影。", 60,
         ["写出片名与类型", "概述情节", "给出评价"],
         "My favourite film is a story about a brave boy. The plot is exciting. The actors did a great job. I watched it twice. I think it is a wonderful film."),
    ],
    # g7 下册
    54: [
        ("Music in my life", "用 6–8 句话写音乐对你的影响。", 60,
         ["写音乐类型", "写聆听或演奏经历", "表达感受"],
         "Music is important in my life. I enjoy pop and classical music. I listen to music when I am tired. Sometimes I play the violin. Music makes me relaxed and happy."),
        ("A helping hand", "用 6–8 句话写一次你帮助别人的经历。", 60,
         ["写具体情景", "使用一般过去时", "有感受或收获"],
         "Last month my neighbour was ill. I helped her buy food and water. I also walked her dog after school. She thanked me warmly. I learned that helping others brings joy."),
        ("Why honesty matters", "用 6–8 句话写诚实的价值。", 60,
         ["写出观点", "举一个例子", "有总结句"],
         "Honesty is important in our life. Once I broke a cup and told my mother the truth. She forgave me because I was honest. Honesty builds trust between people."),
    ],
    # g8 上册
    67: [
        ("Saving water", "用 8 句话左右写节约用水的做法与理由。", 70,
         ["说明水资源现状", "写 2 条以上做法", "使用被动语态或说明句式"],
         "Fresh water is limited on Earth. Many rivers are polluted by waste. We should save water at home. We can take shorter showers and reuse water for plants. Everyone can help."),
        ("Digital life", "用 8 句话左右写数字生活的利与弊。", 70,
         ["写出 2 点好处", "写出 2 点问题", "有个人观点"],
         "Digital life makes our life convenient. We can study and shop online. However, some students spend too much time on screens. We should protect our privacy and use the Internet wisely."),
        ("Teamwork", "用 8 句话左右写一次团队合作的经历。", 70,
         ["写出任务与分工", "写出合作过程", "有收获"],
         "Last term our class worked on a project. We discussed the plan and shared ideas. Everyone had a job to do. When we met problems, we helped each other. Our team finished the project on time."),
    ],
    # g8 下册
    68: [
        ("An invention that changed our life", "用 8 句话左右写一项改变生活的发明。", 70,
         ["点明发明", "说明用途与影响", "有评价"],
         "Electricity is one of the greatest discoveries. It lights our homes and powers machines. Without it, modern life would stop. It has changed the way we live and work."),
        ("How I use my pocket money", "用 8 句话左右写你的零花钱安排。", 70,
         ["说明来源", "写花销与储蓄", "有理财观点"],
         "I get pocket money from my parents every month. I save half of it in a box. The rest I spend on books and stationery. I never buy useless things. A budget helps me use money wisely."),
        ("Friendship", "用 8 句话左右写你对友谊的理解。", 70,
         ["写出友谊的意义", "举一个例子", "有总结"],
         "Friendship is built on trust and support. My best friend always helps me when I am in trouble. We had an argument once, but we talked and forgave each other. True friends stay together."),
    ],
    # g9 上册
    83: [
        ("My teenage life", "用 8–10 句话写你的青少年生活。", 80,
         ["使用 used to 对比", "写学习与生活平衡", "有个人感受"],
         "My life as a teenager is busy but colourful. I used to play games all day. Now I spend more time on schoolwork. I also keep good habits and do sports. I try to balance study and rest."),
        ("A person I admire", "用 8–10 句话写一位你敬佩的人物。", 80,
         ["写出人物与职业", "说明品质与事迹", "使用定语从句"],
         "I admire a doctor who works in my neighbourhood. She is responsible and patient with patients. During the busy season she worked day and night. Her hard work encourages me to study harder."),
        ("Protecting our environment", "用 8–10 句话写环保问题与建议。", 80,
         ["写出问题", "提出 2 条建议", "有呼吁句"],
         "Air pollution harms people's health. Factories should reduce emissions. We can use less plastic and save energy. Small actions can make a big difference. Let's protect our environment together."),
    ],
    # g9 下册
    84: [
        ("Sportsmanship", "用 8–10 句话写你对体育精神的理解。", 80,
         ["写出定义", "举比赛例子", "有总结"],
         "Sportsmanship means competing fairly and respecting rivals. In the school final, our team lost but we shook hands with the winners. Winning a medal is good, but losing with dignity is also great."),
        ("Finding balance in life", "用 8–10 句话写如何平衡学习与生活。", 80,
         ["写出压力来源", "提出 2 条建议", "有总结"],
         "Students face pressure from exams. A good routine reduces stress. I plan my time and relax with music. Enough sleep keeps me energetic. Balance makes life healthier and happier."),
        ("Experiencing a different culture", "用 8–10 句话写你体验不同文化的经历。", 80,
         ["写出文化场景", "描述差异", "表达尊重"],
         "Last year I met a student from England. He greeted me with a hug while I shook hands. We talked about our festivals and food. I learned that differences make the world interesting."),
    ],
}

COMPOSITIONS = {
    book_id: [
        {"title": title, "prompt": prompt, "min_words": words,
         "points": list(points), "sample": sample}
        for title, prompt, words, points, sample in items
    ]
    for book_id, items in COMP_RAW.items()
}
