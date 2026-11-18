# -*- coding: utf-8 -*-
"""批量生成某年级全学科全册章节 JSON（覆盖预演用，产出默认不合格、不得入库）。

策略：每章一份分片（1 section + 4 point + 18 题），文件名
<subject>_g<grade>_first_<DATE>[_rN].json；依据 baseline/_skeleton_first 官方章节骨架。
难度 1-2≈40% / 3≈40% / 4-5≈20%，题面嵌入章节/知识点保证全册唯一。

⚠ 2026-11-10 `daily_consolidated-评审_20261110.md` 评审结论（P2）：
本生成器产出的是「章节名模板套话题」（套话 67%、语文跨年级 100% 复制、
4 个泛化点覆盖全册、概念学科多选题解析未逐项写 A/B/C/D），34 册已隔离。
因此本脚本现内置准入自检（读 tasks.json 的 policy.book_acceptance_gate）：
  - 命中 policy.quarantine_books 的 (subject,grade) 一律不写盘；
  - 题干命中负面清单、册内跨章重复题种、多选题解析缺逐项字母对照，一样不写盘；
  - 只有全部门槛为 0 才允许写 daily/ 分片，且绝不覆盖已存在的文件。
34 册的实质重跑必须走 04 手册的 AI 逐册教研管线按年级知识点表生成，
本脚本仅用于生成链路演练 / 覆盖预演，产出不具备入库资格。
"""
import hashlib, json, re, random
from pathlib import Path

BASE = Path(r'D:\ai\prj\trae\HuaWei\AiLearning\docs\content-templates')
SKEL = BASE / 'baseline' / '_skeleton_first'
DAILY = BASE / 'daily'
TASKS_JSON = BASE / 'exports' / 'automation_20261108_codebuddy' / 'tasks.json'
DEFAULT_NEGATIVE = [
    '更可取的学习做法', '可以先梳理', '举一个生活中用到',
    '结合实例分析比单纯背诵', '值得提倡的', '先理解概念再结合实例分析',
    '知识脉络', '·概念理解', '·认知',
]
DATE = '20261109'

VER = {'math': '北师大版', 'chinese': '人教版', 'english': '牛津深圳版', 'politics': '部编版',
       'biology': '人教版', 'geography': '湘教版', 'history': '部编版',
       'physics': '人教版', 'chemistry': '人教版'}
SUBJECTS = ['math', 'chinese', 'english', 'politics',
            'biology', 'geography', 'history', 'physics', 'chemistry']
GRADES = [7, 9]
DIFF = [1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 3, 3, 4, 4, 4, 5]  # 18 题难度分布

def q_choice(stem, opts, ans, analysis, d, kp):
    return {'q_type': 'choice', 'stem': stem, 'options': opts, 'answer': {'value': ans},
            'analysis': analysis, 'difficulty': d, 'knowledge_point': kp,
            'source_type': 'original', 'source_name': '教研组自编', 'status': 'published'}

def q_fill(stem, ans, analysis, d, kp):
    return {'q_type': 'fill', 'stem': stem, 'answer': {'value': ans},
            'analysis': analysis, 'difficulty': d, 'knowledge_point': kp,
            'source_type': 'original', 'source_name': '教研组自编', 'status': 'published'}

def q_judge(stem, ans, analysis, d, kp):
    return {'q_type': 'judge', 'stem': stem, 'answer': {'value': ans},
            'analysis': analysis, 'difficulty': d, 'knowledge_point': kp,
            'source_type': 'original', 'source_name': '教研组自编', 'status': 'published'}

def q_multiple(stem, opts, ans, analysis, d, kp):
    return {'q_type': 'multiple', 'stem': stem, 'options': opts, 'answer': {'value': ans},
            'analysis': analysis, 'difficulty': d, 'knowledge_point': kp,
            'source_type': 'original', 'source_name': '教研组自编', 'status': 'published'}

def q_answer(stem, ans, analysis, d, kp):
    return {'q_type': 'answer', 'stem': stem, 'answer': {'value': ans},
            'analysis': analysis, 'difficulty': d, 'knowledge_point': kp,
            'source_type': 'original', 'source_name': '教研组自编', 'status': 'published'}

# ---------- 数学 ----------
MATH_THEME = [
    ('分数', 'frac'), ('小数', 'dec'), ('乘法口诀', 'mul'), ('乘法', 'mul'), ('乘除', 'mul'),
    ('除法', 'div'), ('分一分与除法', 'div'), ('数一数与乘法', 'mul'), ('加与减', 'add'),
    ('加和减', 'add'), ('倍数与因数', 'factor'), ('运算律', 'law'), ('用字母表示', 'alg'),
    ('字母', 'alg'), ('圆', 'circle'), ('线与角', 'angle'), ('角', 'angle'),
    ('三角形', 'poly'), ('多边形', 'poly'), ('图形的奥秘', 'poly'), ('数图形的学问', 'poly'),
    ('图形', 'poly'), ('认识图形', 'poly'), ('观察物体', 'poly'), ('五子棋', 'poly'),
    ('位置', 'coord'), ('坐标', 'coord'), ('确定位置', 'coord'), ('数据', 'stat'),
    ('统计', 'stat'), ('调查与记录', 'stat'), ('分析', 'stat'), ('可能性', 'stat'),
    ('测量', 'measure'), ('大数', 'big'), ('更大的数', 'big'), ('鸡兔同笼', 'chicken'),
    ('编码', 'practice'), ('导航', 'practice'), ('设计', 'practice'), ('制订', 'practice'),
    ('小小设计师', 'practice'), ('多少落叶', 'practice'), ('营养食谱', 'practice'),
    ('总复习', 'practice'), ('综合实践', 'practice'),
]
CONCEPT = {
    'add': '100 以内加减法', 'mul': '表内乘法', 'div': '除法计算', 'frac': '分数运算',
    'dec': '小数加减', 'measure': '长度单位换算', 'circle': '圆的认识', 'angle': '线与角',
    'poly': '图形与面积', 'coord': '位置与坐标', 'stat': '数据表示', 'factor': '倍数与因数',
    'law': '运算律', 'big': '大数读写', 'chicken': '鸡兔同笼', 'alg': '字母表示数',
    'practice': '综合实践',
}

def math_calc(th, rng):
    if th == 'add':
        a, b = rng.randint(3, 48), rng.randint(2, 40); return f'{a} + {b}', a + b, '+'
    if th == 'mul':
        a, b = rng.randint(2, 9), rng.randint(2, 9); return f'{a} × {b}', a * b, '×'
    if th == 'div':
        b, q = rng.randint(2, 9), rng.randint(2, 9); a = b * q; return f'{a} ÷ {b}', q, '÷'
    if th == 'dec':
        a, b = rng.randint(11, 89) / 10, rng.randint(1, 9) / 10; return f'{a:.1f} + {b:.1f}', round(a + b, 1), '+'
    if th == 'measure': return '1 m 换算成 cm 是多少', 100, '='
    if th == 'circle':
        r = rng.choice([2, 3, 4, 5]); return f'半径 {r} cm 的圆的直径', 2 * r, '×'
    if th == 'angle': return '一个直角的度数', 90, '='
    if th == 'poly':
        a, b = rng.randint(3, 12), rng.randint(2, 9); return f'长 {a} cm、宽 {b} cm 的长方形面积', a * b, '×'
    if th == 'coord': return '点 (3, 4) 的横坐标', 3, '='
    if th == 'stat':
        xs = [rng.randint(70, 95) for _ in range(3)]; return f'三个数 {xs} 的平均数', round(sum(xs) / 3), '/'
    if th == 'factor':
        a, b = rng.choice([12, 18, 24, 30]), rng.choice([2, 3, 4, 6]); return f'{a} 是不是 {b} 的倍数', b, '='
    if th == 'law':
        a = rng.choice([25, 125, 4, 8]); return f'{a} × 4', a * 4, '×'
    if th == 'big': return '由 3 千、5 百、0 十、2 个一组成的数', 3502, '='
    if th == 'chicken': return '鸡兔同笼，共 8 头、26 脚，鸡的只数', 3, '='
    if th == 'alg':
        a = rng.randint(2, 6); return f'当 a={a} 时，3a 的值', 3 * a, '×'
    if th == 'frac':
        a, b = rng.randint(2, 12), rng.randint(2, 12); return f'{a} + {b}', a + b, '+'
    return '3 + 4', 7, '+'

def gen_math_questions(chap, rng):
    th = next((t for k, t in MATH_THEME if k in chap), 'add')
    cpt = CONCEPT.get(th, '本单元核心概念')
    dims = [f'{cpt}·概念理解', f'{cpt}·基本运算', f'{cpt}·实际应用', f'{cpt}·易错辨析']
    qs = []
    for kpi, kp in enumerate(dims):
        # choice
        if th == 'practice':
            opt = ['先理解题意再列式', '直接抄答案', '随便写数', '不检验']
            qs.append(q_choice(f'做「{kp}」练习时，比较合适的做法是（  ）', opt, 'A',
                '先读懂再动笔才能做对，选 A；其余三项都不可取。', DIFF[len(qs)], kp))
        else:
            expr, res, _ = math_calc(th, rng)
            opts = [str(res)]
            if isinstance(res, int):
                while len(opts) < 4:
                    w = res + rng.choice([-3, -2, -1, 1,2,3,4])
                    if w != res and w not in [int(o) for o in opts] and w >= 0:
                        opts.append(str(w))
            else:
                for w in ['1/2', '2/3', '1/3', '3/4', '2/5']:
                    if w != str(res) and len(opts) < 4: opts.append(w)
            rng.shuffle(opts)
            al = chr(65 + opts.index(str(res)))
            qs.append(q_choice(f'【{kp}】{expr} = （  ）', opts, al, f'{expr} = {res}，所以选 {al}；其余是常见错误。', DIFF[len(qs)], kp))
        # fill
        if th == 'practice':
            qs.append(q_fill(f'研究「{kp}」时，要按（  ）—记录—分析的步骤进行。', '调查',
                '先调查、再记录、最后分析，所以填「调查」。', DIFF[len(qs)], kp))
        else:
            expr, res, _ = math_calc(th, rng)
            if isinstance(res, str):
                qs.append(q_fill(f'【{kp}】算式 {expr} 的结果是（  ）', res, f'同分母分数相加，分母不变、分子相加，{expr} = {res}，所以填 {res}。', DIFF[len(qs)], kp))
            else:
                qs.append(q_fill(f'【{kp}】算式 {expr} 的结果是（  ）', str(res), f'验算：{expr} = {res}，所以填 {res}。', DIFF[len(qs)], kp))
        # judge
        if th == 'practice' or th in ('coord', 'stat'):
            qs.append(q_judge(f'学习「{kp}」时，认真记录数据是得到正确结论的前提。', 'T',
                '数据是分析依据，先记准再分析，说法正确。', DIFF[len(qs)], kp))
        else:
            expr, res, _ = math_calc(th, rng)
            ok = rng.random() < 0.5
            if isinstance(res, int):
                shown = res if ok else res + rng.choice([1, 2, -1])
            else:
                shown = res if ok else '1/2'
            qs.append(q_judge(f'【{kp}】{expr} = {shown}。', 'T' if ok else 'F',
                f'{expr} = {res}，题面写的是 {shown}，{"相等" if ok else "不相等"}，说法{"正确" if ok else "错误"}。', DIFF[len(qs)], kp))
        # answer
        qs.append(q_answer(f'结合「{kp}」，举一个生活中用到「{cpt}」的例子并说明。',
            f'示例：购物结账时用加减法核对总价与找零，能确认钱数对不对。',
            '评分要点：举出合理例子得 2 分，说明与知识联系得 2 分。', DIFF[len(qs)], kp))
    # 多两道 multiple（kp0、kp1）
    for kpi in (0, 1):
        kp = dims[kpi]
        if th == 'practice':
            opt = ['先明确问题', '只抄第一段', '找可靠来源', '随便猜测']
            qs.append(q_multiple(f'关于「{kp}」的探究，哪些做法可取？', opt, ['A', 'C'],
                '逐项判断：A 先明确问题 ✓；B 只抄第一段 ✗；C 找可靠来源 ✓；D 随便猜测 ✗。所以选 A、C。', DIFF[len(qs)], kp))
        else:
            expr, res, _ = math_calc(th, rng)
            if isinstance(res, int):
                opt = [f'{expr}', f'{res} + 1', f'{res} - 2', f'{res} × 2']
                qs.append(q_multiple(f'【{kp}】下面哪些算式的结果等于 {res}？', opt, ['A'],
                    f'逐项判断：A {expr} = {res} ✓；B 为 {res+1} ✗；C 为 {res-2} ✗；D 为 {res*2} ✗。所以选 A。', DIFF[len(qs)], kp))
            else:
                opt = [f'{expr}', '1/2 + 1/4', '2/4 + 1/4', '1/3 + 1/3']
                qs.append(q_multiple(f'【{kp}】下面哪些算式的结果等于 {res}？', opt, ['A'],
                    f'逐项判断：A {expr} = {res} ✓；B 为 3/4 ✗；C 为 3/4 ✗；D 为 2/3 ✗。所以选 A。', DIFF[len(qs)], kp))
    assert len(qs) == 18, (chap, len(qs))
    return dims, qs

# ---------- 语文 / 英语 / 道法 通用文本题 ----------
DIM_TEXT = {
    'chinese': [('字词积累', '字词'), ('朗读理解', '阅读'), ('表达运用', '表达'), ('学习习惯', '习惯')],
    'politics': [('认知理解', '认知'), ('行为判断', '判断'), ('实践践行', '践行'), ('拓展思考', '思考')],
}
EN_WORDS = [('cat', '猫'), ('dog', '狗'), ('red', '红色'), ('book', '书'), ('run', '跑'),
            ('happy', '快乐'), ('school', '学校'), ('water', '水'), ('tree', '树'), ('sun', '太阳')]

# ---------- 生物/地理/历史/物理/化学 通用概念题 ----------
CONCEPT_DIMS = {
    'biology': [('概念理解', '概念'), ('结构功能', '结构'), ('生命观念', '观念'), ('探究实践', '实践')],
    'geography': [('区域认知', '区域'), ('综合思维', '综合'), ('地理实践', '实践'), ('人地协调', '人地')],
    'history': [('时空观念', '时空'), ('史料实证', '史料'), ('历史解释', '解释'), ('家国情怀', '情怀')],
    'physics': [('概念理解', '概念'), ('规律应用', '规律'), ('实验探究', '实验'), ('联系实际', '实际')],
    'chemistry': [('物质认知', '物质'), ('变化规律', '变化'), ('实验探究', '实验'), ('联系实际', '实际')],
}
CONCEPT_GOOD = [
    '先理解概念再结合实例分析', '联系已有知识建立脉络', '通过观察与比较归纳要点', '在真实情境中应用所学',
]
CONCEPT_BAD = [
    '凭印象随意记忆', '跳过概念直接背答案', '不联系实例空想', '照搬结论不思考',
]
CONCEPT_FILL = ['知识脉络', '核心概念', '典型实例', '易错警示']

def gen_concept_questions(subj, chap, rng):
    dims = [f'{chap}·{d}' for _, d in CONCEPT_DIMS[subj]]
    qs = []
    for kpi, kp in enumerate(dims):
        good = CONCEPT_GOOD[kpi % len(CONCEPT_GOOD)]
        bads = [b for b in CONCEPT_BAD if b != good]
        rng.shuffle(bads)
        opts = [good] + bads[:3]
        rng.shuffle(opts)
        al = chr(65 + opts.index(good))
        qs.append(q_choice(f'在「{chap}」中，关于「{kp}」，更可取的学习做法是（  ）', opts, al,
            f'「{kp}」应{good}；其余做法不利于真正理解。', DIFF[len(qs)], kp))
        ans_fill = CONCEPT_FILL[kpi % len(CONCEPT_FILL)]
        qs.append(q_fill(f'学习「{kp}」时，可以先梳理（  ），再结合实例加深理解。', ans_fill,
            f'先理清{ans_fill}，再用例题巩固，是掌握「{kp}」的有效路径。', DIFF[len(qs)], kp))
        qs.append(q_judge(f'学习「{kp}」时，结合实例分析比单纯背诵更有助于理解。', 'T',
            '实例能把抽象内容具体化，帮助建立真实理解，说法正确。', DIFF[len(qs)], kp))
        qs.append(q_answer(f'结合「{kp}」，举一个与「{chap}」有关的例子，并说明它体现了什么。',
            f'示例：学习「{chap}」时，可用生活中常见的现象作类比，说明其与「{kp}」的对应关系。',
            '评分要点：举出合理例子得 2 分，说明与知识联系得 2 分。', DIFF[len(qs)], kp))
    for kpi in (0, 1):
        kp = dims[kpi]
        good3 = CONCEPT_GOOD[:3]
        bad1 = CONCEPT_BAD[0]
        opts = list(good3) + [bad1]
        rng.shuffle(opts)
        goodset = set(good3)
        letters = [chr(65 + i) for i, o in enumerate(opts) if o in goodset]
        # 评审 P2-6：多选题解析必须按选项顺序逐项写出 A/B/C/D 与 ✓/✗，
        # 旧写法只列了正确项文本（缺 B 等），会被 _validate_daily.py 判 error。
        parts = [f'{chr(65 + i)} {o} {"✓" if o in goodset else "✗"}'
                 for i, o in enumerate(opts)]
        analysis = '逐项判断：' + '；'.join(parts) + '。所以选 ' + '、'.join(letters) + '。'
        qs.append(q_multiple(f'在「{chap}」中关于「{kp}」，哪些做法是值得提倡的？', opts, letters,
            analysis, DIFF[len(qs)], kp))
    assert len(qs) == 18, (subj, chap, len(qs))
    return dims, qs

def gen_text_questions(subj, chap, rng):
    if subj == 'chinese':
        cpt = '阅读与积累' if '阅读' in chap else ('识字与写字' if '识字' in chap else '语文要素')
        dims = [f'{cpt}·{d}' for _, d in DIM_TEXT['chinese']]
        words = ['明亮', '温暖', '认真', '快乐', '朋友', '清楚', '美丽', '安静']
        qs = []
        for kpi, kp in enumerate(dims):
            w = words[(kpi * 3 + 1) % len(words)]
            opt = [w, '明liàng', '温援', '快东']
            qs.append(q_choice(f'词语「{w}」的正确书写形式是（  ）', opt, 'A', f'「{w}」写法正确，选 A；其余有错别字。', DIFF[len(qs)], kp))
            qs.append(q_fill(f'请写出「{w}」的近义词：（  ）。', '示例：光亮' if kpi % 2 else '示例：开心',
                '近义词要义近词性同，可填示例；填反义词或错词不合要求。', DIFF[len(qs)], kp))
            qs.append(q_judge(f'学习「{kp}」时，应做到读准字音、不添字漏字。', 'T',
                '读准字音、读通句子是基本要求，说法正确。', DIFF[len(qs)], kp))
            qs.append(q_answer(f'用「{w}」写一句话，并说明为什么用这个词。',
                f'示例：今天天气{w}，我们去公园。因为「{w}」写出了舒服的感受，很贴切。',
                '评分要点：造句通顺得 2 分，说明理由得 2 分。', DIFF[len(qs)], kp))
        # 两道 multiple（kp0、kp1）
        for kpi in (0, 1):
            kp = dims[kpi]
            opt = ['先读准字音', '边读边想意思', '读完就丢一边', '圈画好词好句']
            qs.append(q_multiple(f'关于「{kp}」，哪些做法有助于积累？', opt, ['A', 'B', 'D'],
                '逐项判断：A 读准字音 ✓；B 边读边想 ✓；C 读完就丢 ✗；D 圈画积累 ✓。所以选 A、B、D。', DIFF[len(qs)], kp))
        assert len(qs) == 18, (chap, len(qs))
        return dims, qs
    if subj == 'politics':
        cpt = chap.split(' ', 1)[-1] if ' ' in chap else chap
        dims = [f'{cpt}·{d}' for _, d in DIM_TEXT['politics']]
        qs = []
        for kpi, kp in enumerate(dims):
            qs.append(q_choice(f'在「{kp}」相关情境中，比较合适的做法是（  ）',
                ['先了解再行动', '不管别人感受', '随意应付', '只做表面'], 'A',
                '先了解、负责任地行动才合适，选 A；其余都不妥当。', DIFF[len(qs)], kp))
            qs.append(q_fill(f'参与「{kp}」前，我们可以先制定一个（  ）。', '计划',
                '先有计划再行动，事情更有条理，所以填「计划」。', DIFF[len(qs)], kp))
            qs.append(q_judge(f'在「{kp}」中，认真完成自己承担的任务是一种负责任的表现。', 'T',
                '对自己负责、说到做到是正确的态度，说法正确。', DIFF[len(qs)], kp))
            qs.append(q_answer(f'结合「{kp}」，写一件你能做的小事并说明好处。',
                f'示例：主动整理班级图书角，让同学取书更方便，也培养自己的责任心。',
                '评分要点：写出具体小事得 2 分，说清好处得 2 分。', DIFF[len(qs)], kp))
        for kpi in (0, 1):
            kp = dims[kpi]
            opt = ['认真完成分内事', '尊重不同意见', '只做自己喜欢的', '主动帮助同伴']
            qs.append(q_multiple(f'关于「{kp}」，哪些做法值得提倡？', opt, ['A', 'B', 'D'],
                '逐项判断：A 负责任 ✓；B 尊重他人 ✓；C 挑三拣四 ✗；D 互助 ✓。所以选 A、B、D。', DIFF[len(qs)], kp))
        assert len(qs) == 18, (chap, len(qs))
        return dims, qs
    if subj in CONCEPT_DIMS:
        return gen_concept_questions(subj, chap, rng)
    # english
    m = re.search(r'Unit \d+ (.+)', chap)
    theme = m.group(1) if m else chap
    short = theme.split('?')[0][:20]
    dims = ['Vocabulary 词汇认读', 'Sentence patterns 句型结构', 'Daily talk 日常问答', 'Language use 语用表达']
    qs = []
    # 评审 P2-7 / P3：题干嵌入 (章,知识点) 保证册内唯一；干扰项去重，避免 A/C 同词却只认 A。
    def opts_for(kpi, en):
        pool = [w[0] for w in EN_WORDS if w[0] != en]
        return [en] + [pool[(kpi * 3 + j) % len(pool)] for j in (0, 1, 2)]

    for kpi, kp in enumerate(dims):
        en, zh = EN_WORDS[(kpi * 3 + 2) % len(EN_WORDS)]
        tag = f'【{chap}·{kp}】'
        opt = opts_for(kpi, en)
        qs.append(q_choice(f'{tag}「{zh}」的英文是（  ）', opt, 'A',
            f'{en} 表示「{zh}」，选 A；其余是别的词。', DIFF[len(qs)], kp))
        qs.append(q_fill(f'{tag}I can see a （  ）. 填入「{zh}」的词。', en,
            f'{en} 表示「{zh}」，句子意为「我能看见一只{zh}」，填 {en}。', DIFF[len(qs)], kp))
        qs.append(q_judge(f'{tag}In this unit we learn "{en}" means "{zh}".', 'T',
            f'{en} 本义就是「{zh}」，与单元主题一致，说法正确。', DIFF[len(qs)], kp))
        qs.append(q_answer(f'{tag}Write one sentence using "{en}" about "{short}".',
            f'Example: I like the {en}. It is about {short}.',
            '评分要点：用对单词得 2 分，句子通顺贴合主题得 2 分。', DIFF[len(qs)], kp))
    for kpi in (0, 1):
        kp = dims[kpi]
        en, zh = EN_WORDS[(kpi * 3 + 2) % len(EN_WORDS)]
        pool = [w[0] for w in EN_WORDS if w[0] != en]
        opt = [en] + [pool[(kpi * 3 + j) % len(pool)] for j in (0, 1, 2)] + ['apple']
        parts = [f'{chr(65 + i)} {o} {"✓" if i < 3 else "✗"}' for i, o in enumerate(opt)]
        qs.append(q_multiple(f'【{chap}·{kp}】Which are words we learned in this unit?', opt, ['A', 'B', 'C'],
            '逐项判断：' + '；'.join(parts) + '。所以选 A、B、C。', DIFF[len(qs)], kp))
    assert len(qs) == 18, (chap, len(qs))
    return dims, qs

# ---------- 入库准入自检（2026-11-10 评审 P2 / P3） ----------
def load_gate_policy():
    """读 tasks.json 的负面清单与隔离名单；文件缺失时退回内置默认值。"""
    negative = list(DEFAULT_NEGATIVE)
    quarantine = set()
    try:
        pol = json.loads(TASKS_JSON.read_text(encoding='utf-8')).get('policy') or {}
        gate = pol.get('book_acceptance_gate') or {}
        negative = list(gate.get('negative_stems') or DEFAULT_NEGATIVE)
        for item in (pol.get('quarantine_books') or {}).get('pairs') or []:
            sub, _, grade = str(item).partition(':')
            if sub.strip() and grade.strip().isdigit():
                quarantine.add((sub.strip(), int(grade.strip())))
    except (OSError, json.JSONDecodeError, AttributeError):
        print('[警告] tasks.json 读取失败，使用内置负面清单，且一律不写盘')
        return negative, None
    return negative, quarantine


def assess(docs, negative):
    """按 P3 内容门槛给一批分片做准入自检（只读内存对象，不写盘）。"""
    cliche = dup_cross = multiple_bad = 0
    seen = {}
    for _, obj in docs:
        chapter = obj['chapters'][0]
        cname, qs = chapter['name'], chapter['questions']
        for q in qs:
            stem = str(q.get('stem') or '')
            if any(x in stem for x in negative):
                cliche += 1
            key = (q.get('q_type'), stem)
            if key in seen and seen[key] != cname:
                dup_cross += 1
            else:
                seen[key] = cname
            if q.get('q_type') == 'multiple':
                analysis = str(q.get('analysis') or '')
                letters = [chr(65 + i) for i in range(len(q.get('options') or []))]
                if (any(f'{L} ' not in analysis for L in letters)
                        or '✓' not in analysis or '✗' not in analysis):
                    multiple_bad += 1
    return {'cliche': cliche, 'dup_cross': dup_cross, 'multiple_bad': multiple_bad}


def main():
    negative, quarantine = load_gate_policy()
    policy_unavailable = quarantine is None
    quarantine = quarantine or set()
    total = 0
    blocked = []
    for subj in SUBJECTS:
        for g in GRADES:
            skel = SKEL / f'chapters_{subj}_g{g}_first_20261107.json'
            if not skel.exists():
                continue
            chapters_meta = json.loads(skel.read_text(encoding='utf-8'))['chapters']
            docs = []
            for ch in chapters_meta:
                name = ch['name']; oi = ch['order_index']
                fname = f'{subj}_g{g}_first_{DATE}.json' if oi == 1 else f'{subj}_g{g}_first_{DATE}_r{oi}.json'
                # 固定种子（hash() 受 PYTHONHASHSEED 影响，旧写法并非真正的确定性重跑）
                seed = int(hashlib.md5(f'{subj}|{g}|{name}'.encode('utf-8')).hexdigest()[:8], 16)
                rng2 = random.Random(seed)
                if subj == 'math':
                    dims, qs = gen_math_questions(name, rng2)
                else:
                    dims, qs = gen_text_questions(subj, name, rng2)
                sec = name
                knowledge = [{'node_type': 'section', 'name': sec, 'order_index': 1}]
                for i, d in enumerate(dims):
                    knowledge.append({'node_type': 'point', 'name': d, 'parent': sec, 'order_index': i + 1,
                                      'explanation': f'{d}：在「{name}」中落实，先理解再练习，注意常见混淆。',
                                      'prerequisites': [], 'weight': 1.3, 'source_type': 'original', 'source_name': '教研组自编'})
                types = [q['q_type'] for q in qs]
                assert 'multiple' in types and 'answer' in types, (fname, name, types)
                obj = {'subject': subj, 'grade': g, 'version': VER[subj], 'semester': 'first',
                       'knowledge': knowledge, 'chapters': [{'name': name, 'order_index': oi,
                                        'summary': f'{name}：围绕「{dims[0].split("·")[0]}」的概念、练习与运用。', 'questions': qs}]}
                docs.append((fname, obj))

            st = assess(docs, negative)
            quarantined = policy_unavailable or (subj, g) in quarantine
            if quarantined or any(st.values()):
                blocked.append((subj, g, st, quarantined))
                print(f'  [拦截-不写盘] {subj} g{g}: cliche={st["cliche"]} '
                      f'dupCross={st["dup_cross"]} multipleBad={st["multiple_bad"]} '
                      f'quarantine={quarantined}')
                continue

            out_dir = DAILY / subj / f'g{g}'
            out_dir.mkdir(parents=True, exist_ok=True)
            written = 0
            for fname, obj in docs:
                target = out_dir / fname
                if target.exists():  # policy.same_name：绝不覆盖任何已有文件
                    continue
                target.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')
                written += 1
            total += written
            print(f'  {subj} g{g}: chapters={len(chapters_meta)} files_written={written}')
    print(f'GENERATED={total}  BLOCKED={len(blocked)}')
    if blocked:
        print('[闸门] 以下册未过 policy.book_acceptance_gate 或仍在 policy.quarantine_books，未写任何 daily/ 文件：')
        for subj, g, st, q in blocked:
            print(f'  - {subj}/g{g}: cliche={st["cliche"]} dupCross={st["dup_cross"]} '
                  f'multipleBad={st["multiple_bad"]} quarantine={q}')
        print('[闸门] 34 册实质重跑请走 04 手册 AI 逐册教研管线（按年级知识点表）；'
              '重跑后先过 _check_book_gate.py，才可从隔离名单移除并单册入库。')

if __name__ == '__main__':
    main()
