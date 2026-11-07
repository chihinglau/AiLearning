"""开发环境初始化（幂等，可重复运行）：

- 管理员 / 体验学生账号
- 全学段教材矩阵（小/初/高，深圳常用版本）
- 小学 1-3 年级语数英：完整章节 → 节 → 知识点 → 多题型题目（确定性数据）
- 4-12 年级各学科：每本教材 1 个样章（节 + 2 知识点 × 3 题）

用法：.venv\\Scripts\\python.exe -m scripts.seed
"""

from typing import Callable, Optional

from sqlalchemy import func, select

from app.core.security import hash_password
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.content import Chapter, KnowledgePoint, Question, Textbook
from app.models.exam import Exam, ExamBlueprint
from app.models.user import User
from app.services.exam_paper import generate_paper
from app.services.rbac import backfill_user_roles, sync_catalog

ADMIN_PHONE = "13800000000"
ADMIN_PASSWORD = "admin123"
DEMO_STUDENT_PHONE = "13900000000"
DEMO_STUDENT_PASSWORD = "student123"

# ---------------------------------------------------------------------------
# 题目构造助手
# ---------------------------------------------------------------------------


def choice(stem, options, answer, analysis, difficulty=2):
    """options: list[str] 或 list[(key,text)]；answer: 'A' 或 keys 列表(多选)。"""
    multiple = isinstance(answer, list)
    opts = []
    for i, item in enumerate(options):
        key = chr(ord("A") + i) if not isinstance(item, tuple) else item[0]
        text = item if not isinstance(item, tuple) else item[1]
        opts.append({"key": key, "text": text})
    return {
        "q_type": "multiple" if multiple else "choice",
        "content": {"stem": stem},
        "options": opts,
        "answer": {"value": answer},
        "analysis": analysis,
        "difficulty": difficulty,
    }


def judge(stem, is_true, analysis, difficulty=1):
    return {
        "q_type": "judge",
        "content": {"stem": stem},
        "options": [
            {"key": "T", "text": "正确"},
            {"key": "F", "text": "错误"},
        ],
        "answer": {"value": "T" if is_true else "F"},
        "analysis": analysis,
        "difficulty": difficulty,
    }


def fill(stem, answer, analysis, difficulty=2):
    return {
        "q_type": "fill",
        "content": {"stem": stem},
        "options": None,
        "answer": {"value": answer},
        "analysis": analysis,
        "difficulty": difficulty,
    }


# ---------------------------------------------------------------------------
# 教材矩阵（深圳常用版本）
# ---------------------------------------------------------------------------

VERSIONS = {
    "chinese": "人教版",
    "math": "北师大版",
    "english": "牛津深圳版",
    "physics": "人教版",
    "chemistry": "人教版",
    "biology": "人教版",
    "history": "部编版",
    "geography": "湘教版",
    "politics": "部编版",
}

# 高中阶段与义务教育阶段版本不同：数学为人教 A 版，英语为外研版
SENIOR_VERSIONS = {
    "math": "人教版A版",
    "english": "外研版",
}

PRIMARY_SUBJECTS = ["math", "chinese", "english"]
JUNIOR_SUBJECTS = {
    7: ["chinese", "math", "english", "biology", "history", "geography", "politics"],
    8: ["chinese", "math", "english", "physics", "biology", "history", "geography", "politics"],
    9: ["chinese", "math", "english", "physics", "chemistry", "history", "politics"],
}
SENIOR_SUBJECTS = [
    "chinese", "math", "english", "physics", "chemistry",
    "biology", "history", "geography", "politics",
]


# ---------------------------------------------------------------------------
# 小学数学：确定性题目生成（按年级/学期真实知识点）
# ---------------------------------------------------------------------------


def _arith_fill(a, b, op, idx, difficulty):
    sym = {"add": "+", "sub": "-", "mul": "×", "div": "÷"}[op]
    if op == "add":
        ans, ana = a + b, f"{a} 加 {b} 等于 {a + b}。"
    elif op == "sub":
        ans, ana = a - b, f"{a} 减 {b} 等于 {a - b}。"
    elif op == "mul":
        ans, ana = a * b, f"乘法口诀：{a} × {b} = {a * b}。"
    else:
        a, b = a * b, a
        ans = a // b
        ana = f"{a} ÷ {b} = {ans}（想乘法：{b} × {ans} = {a}）。"
    return fill(f"{a} {sym} {b} = （  ）", str(ans), ana, difficulty)


def _arith_choice(a, b, op, idx, difficulty):
    if op == "add":
        target, expr = a + b, f"{a} + {b}"
    elif op == "sub":
        target, expr = a - b, f"{a} - {b}"
    elif op == "mul":
        target, expr = a * b, f"{a} × {b}"
    else:
        a, b = a * b, a
        target, expr = a // b, f"{a} ÷ {b}"
    opts = [target, target + 1, target - 1, target + 2]
    # 打乱顺序由 idx 决定，保证确定性
    order = [opts[(i + idx) % 4] for i in range(4)]
    key = chr(ord("A") + order.index(target))
    return choice(f"{expr} = ?", [str(x) for x in order], key,
                  f"{expr} = {target}。", difficulty)


MATH_CURRICULUM: dict[int, dict[str, list]] = {
    1: {
        "first": [
            ("10以内加减法", "理解加减法含义，能正确计算10以内加减法",
             [lambda i: _arith_fill(3 + i, 2, "add", i, 1),
              lambda i: _arith_choice(4, i + 1, "add", i, 1),
              lambda i: _arith_fill(9, 2 + i, "sub", i, 2),
              lambda i: _arith_choice(8, 3 + (i % 2), "sub", i, 2)]),
            ("比较与位置", "会比较多少、长短、高矮，认识上下前后左右",
             [lambda i: judge("苹果比西瓜大。", False, "结合生活，西瓜比苹果大。", 1),
              lambda i: choice("上下楼梯要靠（  ）行。", ["左", "右", "中间"], "B",
                               "安全常识：上下楼梯靠右行。", 1),
              lambda i: fill("比 5 多 2 的数是（  ）。", "7", "5 + 2 = 7。", 2),
              lambda i: judge("小明的左手和右手是相对的。", True,
                              "左手和右手是一对相对的位置。", 2)]),
            ("认识图形", "直观认识长方体、正方体、圆柱、球",
             [lambda i: choice("下面形状像球的是（  ）。", ["魔方", "篮球", "书本"], "B",
                               "篮球是球体。", 1),
              lambda i: judge("魔方的形状是正方体。", True, "魔方六个面都是正方形。", 1),
              lambda i: choice("易拉罐的形状像（  ）。", ["圆柱", "球", "正方体"], "A",
                               "易拉罐上下两个圆面、侧面弯曲，是圆柱。", 2),
              lambda i: fill("长方体有（  ）个面。", "6", "长方体有6个面。", 2)]),
        ],
        "second": [
            ("20以内进位加与退位减", "掌握凑十法、破十法，正确计算20以内进退位加减",
             [lambda i: _arith_fill(8, 4 + (i % 3), "add", i, 2),
              lambda i: _arith_fill(13, 5 + (i % 3), "sub", i, 2),
              lambda i: _arith_choice(7, 5 + (i % 3), "add", i, 2),
              lambda i: _arith_choice(15, 7 + (i % 2), "sub", i, 3)]),
            ("100以内数的认识", "认识数位（个位、十位），会读写100以内的数",
             [lambda i: fill("1 个十和 5 个一合起来是（  ）。", "15",
                             "十位1、个位5，写作15。", 1),
              lambda i: choice("36 的“3”表示（  ）。", ["3个一", "3个十", "3个百"], "B",
                               "3在十位上，表示3个十。", 2),
              lambda i: judge("100 里面有 10 个十。", True, "10个十是100。", 1),
              lambda i: fill("和 49 相邻的两个数是 48 和（  ）。", "50",
                             "49前面48，后面50。", 2)]),
            ("观察物体", "从不同方向观察简单物体，辨认看到的形状",
             [lambda i: judge("从前面和从后面看同一辆玩具汽车，看到的形状一样。", False,
                              "方向不同，看到的形状可能不同。", 2),
              lambda i: choice("观察一个球，无论从哪个方向看都是（  ）。",
                               ["圆", "正方形", "三角形"], "A", "球从任何方向看都是圆。", 1),
              lambda i: judge("一本书从上面看是长方形。", True, "书本封面是长方形。", 1),
              lambda i: fill("观察物体一般从前面、上面和（  ）面看。", "侧",
                             "三视图：前面、上面、侧面。", 2)]),
        ],
    },
    2: {
        "first": [
            ("100以内加减法", "正确计算两位数加减两位数（进退位）",
             [lambda i: _arith_fill(23 + i, 15, "add", i, 2),
              lambda i: _arith_fill(50, 18 + (i % 5), "sub", i, 2),
              lambda i: _arith_choice(36, 27 + (i % 3), "add", i, 3),
              lambda i: choice("小明有 45 元，买书用去 18 元，还剩（  ）元。",
                               ["27", "33", "23"], "A", "45 - 18 = 27（元）。", 3)]),
            ("乘法口诀（2-5）", "理解乘法含义，熟记2-5的乘法口诀",
             [lambda i: _arith_fill(3, 2 + (i % 4), "mul", i, 1),
              lambda i: _arith_choice(4, 3 + (i % 3), "mul", i, 2),
              lambda i: fill("把 4 + 4 + 4 改写成乘法算式是 4 × （  ）。", "3",
                             "3个4相加，4×3。", 2),
              lambda i: judge("2 × 5 和 5 × 2 用同一句口诀。", True,
                              "都是“二五一十”。", 1)]),
            ("元角分", "认识人民币，知道1元=10角、1角=10分",
             [lambda i: fill("1 元 = （  ）角。", "10", "1元=10角。", 1),
              lambda i: choice("一支铅笔 5 角，付 1 元应找回（  ）。",
                               ["5角", "5元", "1角"], "A", "1元-5角=5角。", 2),
              lambda i: fill("1 角 = （  ）分。", "10", "1角=10分。", 1),
              lambda i: judge("一张 10 元可以换 10 张 1 元。", True, "10个1元是10元。", 2)]),
        ],
        "second": [
            ("除法的初步认识", "理解平均分，会用乘法口诀求商",
             [lambda i: _arith_fill(6 + i * 2, 2, "div", i, 2),
              lambda i: _arith_choice(12, 3 + (i % 2), "div", i, 2),
              lambda i: fill("把 8 个桃平均放在 2 个盘里，每盘放（  ）个。", "4",
                             "8 ÷ 2 = 4。", 2),
              lambda i: judge("12 ÷ 3 = 4，想口诀“三四十二”。", True,
                              "做除法想乘法：3×4=12。", 2)]),
            ("方向与路线", "认识东、南、西、北及东南、东北、西南、西北",
             [lambda i: judge("太阳每天从东方升起。", True, "太阳东升西落。", 1),
              lambda i: choice("晚上面对北极星，后面是（  ）方。",
                               ["南", "北", "东"], "A", "面对北，背后是南。", 2),
              lambda i: fill("地图通常按上北、下南、左西、（  ）东绘制。", "右",
                             "地图方向：上北下南左西右东。", 2),
              lambda i: judge("东南方向在东和南之间。", True, "东与南之间是东南。", 1)]),
            ("测量（厘米和米）", "认识长度单位厘米、米，会估测和测量",
             [lambda i: fill("1 米 = （  ）厘米。", "100", "1米=100厘米。", 1),
              lambda i: choice("教室门的高度大约是 2（  ）。", ["厘米", "米", "拃"], "B",
                               "门高约2米，2厘米太矮。", 2),
              lambda i: judge("小明的食指宽大约 1 厘米。", True, "1厘米大约一指宽。", 1),
              lambda i: fill("直尺上从刻度 0 到刻度 5 是（  ）厘米。", "5",
                             "5 - 0 = 5（厘米）。", 2)]),
        ],
    },
    3: {
        "first": [
            ("一位数乘多位数", "掌握多位数乘一位数的笔算（含进位、0的乘法）",
             [lambda i: _arith_fill(12 + i, 3, "mul", i, 2),
              lambda i: _arith_choice(24, 4, "mul", i, 3),
              lambda i: fill("0 和任何数相乘都得（  ）。", "0", "0乘任何数都得0。", 1),
              lambda i: choice("一箱牛奶 24 盒，4 箱共（  ）盒。",
                               ["96", "86", "28"], "A", "24×4=96（盒）。", 3)]),
            ("周长", "理解周长含义，掌握长方形、正方形周长计算",
             [lambda i: fill("长方形长 5 厘米、宽 3 厘米，周长是（  ）厘米。", "16",
                             "(5+3)×2=16（厘米）。", 3),
              lambda i: fill("正方形边长 4 分米，周长是（  ）分米。", "16",
                             "4×4=16（分米）。", 2),
              lambda i: choice("绕操场跑一圈的长度就是操场的（  ）。",
                               ["周长", "面积", "边长"], "A", "封闭图形一周的长度叫周长。", 1),
              lambda i: judge("周长相等的两个长方形，形状一定相同。", False,
                              "周长相等，长和宽不一定相同。", 3)]),
            ("分数的初步认识", "结合情境初步认识几分之一、几分之几",
             [lambda i: choice("把一个月饼平均分成 4 份，每份是它的（  ）。",
                               ["1/4", "1/2", "4/1"], "A", "平均分成4份，每份是四分之一。", 1),
              lambda i: judge("把一个西瓜分成 3 块，每块一定是它的 1/3。", False,
                              "必须“平均分”，每份才是1/3。", 2),
              lambda i: fill("1/2 读作（  ）分之一。（填汉字）", "二", "1/2读作二分之一。", 1),
              lambda i: choice("1/5 和 1/3 比较，（  ）大。", ["1/5", "1/3", "一样大"], "B",
                               "分子相同，分母越小分数越大。", 3)]),
        ],
        "second": [
            ("两位数乘两位数", "掌握两位数乘两位数笔算，解决实际问题",
             [lambda i: _arith_fill(12, 11 + i, "mul", i, 3),
              lambda i: _arith_choice(13, 12 + (i % 2), "mul", i, 3),
              lambda i: choice("每行 14 人，共 12 行，一共（  ）人。",
                               ["168", "148", "26"], "A", "14×12=168（人）。", 3),
              lambda i: fill("25 × 40 的积末尾有（  ）个 0。", "3",
                             "25×40=1000，末尾3个0。", 4)]),
            ("面积", "理解面积含义，掌握长方形/正方形面积与面积单位换算",
             [lambda i: fill("长方形长 6 厘米、宽 4 厘米，面积是（  ）平方厘米。", "24",
                             "6×4=24（平方厘米）。", 2),
              lambda i: fill("1 平方分米 = （  ）平方厘米。", "100",
                             "1分米=10厘米，10×10=100。", 3),
              lambda i: choice("课桌面的面积约是 24（  ）。",
                               ["平方厘米", "平方分米", "米"], "B",
                               "课桌面积约24平方分米。", 2),
              lambda i: judge("边长 4 米的正方形，周长和面积相等。", False,
                              "周长16米、面积16平方米，单位不同不能比较。", 4)]),
            ("小数的初步认识", "结合元角分、米分米认识一位小数，会比较和加减",
             [lambda i: fill("3 元 5 角用小数表示是（  ）元。", "3.5",
                             "5角=0.5元，3元5角=3.5元。", 2),
              lambda i: choice("0.8 米表示（  ）。", ["8米", "8分米", "8厘米"], "B",
                               "0.8米=8分米。", 2),
              lambda i: fill("0.5 + 0.3 = （  ）。", "0.8", "5个0.1加3个0.1是8个0.1。", 1),
              lambda i: choice("下面最大的数是（  ）。", ["0.6", "0.9", "0.4"], "B",
                               "整数部分相同，比较十分位：9最大。", 2)]),
        ],
    },
}


# ---------------------------------------------------------------------------
# 小学语文 1-3 年级
# ---------------------------------------------------------------------------

CHINESE_CURRICULUM: dict[int, dict[str, list]] = {
    1: {
        "first": [
            ("汉语拼音", "掌握声母、韵母、整体认读音节和四声", [
                choice("下面属于声母的是（  ）。", ["b", "a", "o"], "A",
                       "b是声母，a、o是单韵母。", 1),
                choice("“mā”的声调是第（  ）声。", ["一", "二", "四"], "A",
                       "mā是第一声（阴平）。", 1),
                judge("“yi、wu、yu”是整体认读音节。", True,
                      "yi、wu、yu都要整体认读，不拼读。", 1),
                fill("汉语拼音有（  ）个单韵母。（填数字）", "6",
                     "6个单韵母：a、o、e、i、u、ü。", 2),
            ]),
            ("识字（一）", "认识基本汉字，了解象形字特点", [
                choice("“日”字最早像（  ）的形状。", ["太阳", "月亮", "河流"], "A",
                       "“日”是象形字，像太阳。", 1),
                judge("“山”是象形字。", True, "“山”像三座山峰。", 1),
                fill("“天”字共（  ）画。", "4", "天：横、横、撇、捺，共4画。", 2),
                choice("“人”加两横可以变成（  ）。", ["天", "口", "木"], "A",
                       "人加两横是“天”。", 2),
            ]),
            ("反义词与数量词", "积累常见反义词，正确使用量词", [
                choice("“大”的反义词是（  ）。", ["小", "多", "上"], "A", "大对小。", 1),
                fill("一（  ）小鸟（填量词）", "只", "表示动物常用“只”。", 1),
                judge("“上”和“下”是一对反义词。", True, "上对下。", 1),
                fill("一（  ）黄牛（填量词）", "头", "体形较大的牲畜用“头”。", 2),
            ]),
        ],
        "second": [
            ("偏旁部首与笔顺", "认识常见偏旁，按笔顺规则写字", [
                choice("“江、河、海”都有三点水，这些字多与（  ）有关。",
                       ["水", "火", "树木"], "A", "三点水的字多与水有关。", 2),
                judge("“先横后竖、先撇后捺”是基本笔顺规则。", True,
                      "如“十”先横后竖，“人”先撇后捺。", 1),
                fill("“木”字共（  ）画。", "4", "木：横、竖、撇、捺，共4画。", 1),
                choice("“妈、姐、妹”都有女字旁，多与（  ）有关。",
                       ["女性", "力气", "房屋"], "A", "女字旁的字多与女性有关。", 2),
            ]),
            ("生字组词", "正确认读并给生字组词", [
                choice("“春”可以组成词语（  ）。", ["春天", "夏天", "秋风"], "A",
                       "春——春天、春风。", 1),
                judge("“花”只能组“花朵”一个词。", False,
                      "还可以组：开花、花草、花园等。", 1),
                fill("“草”可以组词为（  ）地。", "草", "草地。", 1),
                choice("下面词语书写正确的是（  ）。",
                       ["朋友", "朋有", "棚友"], "A", "“朋友”才是正确写法。", 2),
            ]),
            ("课文朗读与背诵", "正确朗读课文，背诵古诗与日积月累", [
                fill("《春晓》的作者是唐代诗人（  ）。（填人名，2字）", "孟浩然",
                     "《春晓》：春眠不觉晓……孟浩然作。", 3),
                judge("朗读时遇到句号要有较长停顿。", True,
                      "句号表示一句话完了，停顿较长。", 1),
                fill("“夜来风雨声”的下一句是：花落知（  ）。（2字）", "多少",
                     "花落知多少。", 2),
                judge("“一寸光阴一寸金”告诉我们要珍惜时间。", True,
                      "这句谚语强调时间宝贵。", 2),
            ]),
        ],
    },
    2: {
        "first": [
            ("多音字", "据词定音，掌握常见多音字读音", [
                choice("“快乐”的“乐”读（  ）。", ["lè", "yuè", "lē"], "A",
                       "快乐(lè)；音乐(yuè)。", 2),
                judge("“音乐”的“乐”读 yuè。", True, "音乐(yuè)。", 1),
                fill("“长大”的“长”读（  ）。（写拼音，不带声调）", "zhang",
                     "长大(zhǎng)；长短(cháng)。", 3),
                choice("下面词语中“地”读 dì 的是（  ）。",
                       ["土地", "飞快地跑", "高兴地说"], "A",
                       "名词前读dì；状语后读de。", 3),
            ]),
            ("量词与词语搭配", "准确使用量词，搭配动宾短语", [
                fill("一（  ）石桥（填量词）", "座", "桥用“座”。", 2),
                choice("（  ）衣裳（填动词）", ["穿", "喝", "听"], "A",
                       "穿衣裳；喝水；听音乐。", 1),
                judge("“一群大雁、一艘轮船”的量词都用对了。", True,
                      "大雁成群、轮船用艘。", 2),
                fill("一（  ）图画（填量词）", "幅", "图画用“幅”。", 2),
            ]),
            ("比喻句初步", "认识比喻句，能找出本体和喻体", [
                choice("“弯弯的月亮像小船”把月亮比作（  ）。",
                       ["小船", "镰刀", "圆盘"], "A", "喻体是小船。", 2),
                judge("“小红长得像妈妈”是比喻句。", False,
                      "同类比较不是比喻；比喻要用不同类事物打比方。", 3),
                fill("比喻句常用的比喻词有“像、好像、仿佛、（  ）”等。（1字）", "似",
                     "“似的/如同/犹如”等也是比喻词。", 3),
                choice("“荷叶挨挨挤挤的，像碧绿的大圆盘”中喻体是（  ）。",
                       ["大圆盘", "荷叶", "碧玉"], "A", "把荷叶比作大圆盘。", 2),
            ]),
        ],
        "second": [
            ("近反义词", "积累近义词、反义词", [
                choice("“高兴”的近义词是（  ）。", ["快乐", "伤心", "生气"], "A",
                       "高兴≈快乐。", 1),
                choice("“危险”的反义词是（  ）。", ["安全", "困难", "容易"], "A",
                       "危险对安全。", 2),
                judge("“寒冷”和“严寒”是近义词。", True, "都表示非常冷。", 2),
                fill("“复杂”的反义词是（  ）。（2字）", "简单", "复杂对简单。", 2),
            ]),
            ("标点符号", "正确使用逗号、句号、问号、感叹号", [
                choice("“你今天去图书馆吗（  ）”应填（  ）。",
                       ["？", "。", "，"], "A", "疑问句末尾用问号。", 1),
                judge("“这里的风景真美啊！”感叹号使用正确。", True,
                      "强烈感叹语气用感叹号。", 1),
                fill("表示一句话中间的停顿，要用（  ）号。（1字）", "逗", "句中停顿用逗号。", 1),
                choice("下面标点正确的是（  ）。",
                       ["妈妈说：“快吃饭了。”", "妈妈说“快吃饭了。”",
                        "妈妈说：快吃饭了。"], "A", "提示语后用冒号，说话内容加引号。", 3),
            ]),
            ("阅读：提取信息", "从短文中找出明显的信息", [
                judge("做“从文中找答案”的题目时，应先读问题再带着问题读短文。", True,
                      "带着问题读，目标更明确。", 2),
                choice("短文中写“小白兔爱吃胡萝卜和青菜”，小白兔爱吃（  ）种食物。",
                       ["2", "1", "3"], "A", "胡萝卜和青菜，共2种。", 2),
                fill("文中说“小猫在屋顶上晒太阳”，地点是（  ）。（3字）", "屋顶上",
                     "直接提取“在屋顶上”。", 2),
                judge("回答提取信息题可以照抄文中的关键句子。", True,
                      "答案就在文中时可用原文词句作答。", 2),
            ]),
        ],
    },
    3: {
        "first": [
            ("修改病句", "识别成分残缺、重复啰嗦、搭配不当", [
                choice("“我们要学习他助人为乐。”这句的病因是（  ）。",
                       ["成分残缺", "前后矛盾", "词序颠倒"], "A",
                       "缺宾语，应是“学习他助人为乐的精神”。", 3),
                judge("“我忍不住不禁笑了起来”语义重复。", True,
                      "“忍不住”和“不禁”重复，删其一。", 2),
                fill("修改病句：“上课了，都在认真听讲。”应在“都在”前加（  ）。（2字）",
                     "同学们", "句子缺主语。", 3),
                choice("“春天的杭州是个美丽的季节。”的病因是（  ）。",
                       ["搭配不当", "重复啰嗦", "成分残缺"], "A",
                       "杭州不是季节，应改为“杭州的春天”。", 4),
            ]),
            ("关联词", "正确使用并列、因果、转折、假设关联词", [
                choice("（  ）明天下雨，运动会（  ）改期。应填（  ）。",
                       ["如果……就……", "一边……一边……", "虽然……但是……"], "A",
                       "假设关系用“如果……就……”。", 2),
                judge("“因为他刻苦训练，所以成绩提高很快。”关联词使用正确。", True,
                      "因果关系：因为……所以……。", 2),
                fill("表示转折关系常用“虽然……（  ）……”。（2字）", "但是",
                     "虽然……但是……表转折。", 2),
                choice("“小红（  ）会唱歌，（  ）会跳舞。”应填（  ）。",
                       ["不但……而且……", "因为……所以……", "如果……就……"], "A",
                      "递进关系用“不但……而且……”。", 3),
            ]),
            ("古诗文积累", "背诵并理解课标古诗", [
                fill("《所见》中“牧童骑（  ）牛”。", "黄", "牧童骑黄牛。", 2),
                fill("“停车坐爱枫林晚，霜叶红于（  ）月花。”", "二",
                     "霜叶红于二月花。", 3),
                judge("《夜书所见》的作者是宋代诗人叶绍翁。", True,
                      "叶绍翁《夜书所见》。", 2),
                choice("“知有儿童挑促织”中“促织”指（  ）。",
                       ["蟋蟀", "知了", "蝴蝶"], "A", "促织就是蟋蟀。", 3),
            ]),
        ],
        "second": [
            ("修辞手法", "辨析比喻、拟人、排比、夸张", [
                choice("“春风轻轻地抚摸着小草。”运用了（  ）修辞。",
                       ["拟人", "比喻", "夸张"], "A", "“抚摸”把春风当作人写。", 3),
                judge("“桂林的山真奇啊，真秀啊，真险啊！”是排比句。", True,
                      "三个结构相似的分句构成排比。", 2),
                fill("“飞流直下三千尺”运用了（  ）的修辞手法。（2字）", "夸张",
                     "“三千尺”极力夸张瀑布之高。", 3),
                choice("下面是拟人句的是（  ）。",
                       ["小草偷偷地从土里钻出来", "弯弯的月亮像小船",
                        "他跑得像兔子一样快"], "A",
                      "“偷偷地钻”赋予小草人的动作情态。", 3),
            ]),
            ("概括段意", "用谁干什么/什么怎么样概括段意", [
                judge("概括段意可以直接找段落的中心句。", True,
                      "段首/段尾的中心句常可直接概括段意。", 2),
                choice("“谁干什么”句式适合概括（  ）的段意。",
                       ["写事写人", "写景", "说明物品"], "A",
                      "写事写人的段落常用“谁干什么”。", 3),
                fill("段意要简洁、（  ），不能写得太细。（2字）", "完整",
                     "概括要简洁而完整。", 2),
                judge("概括段意时可以加入自己的看法和评论。", False,
                      "段意是内容概括，不应加入个人评论。", 3),
            ]),
            ("习作：把过程写清楚", "按顺序把一件事的经过写具体", [
                choice("写事一般按事情发展的先后顺序，即（  ）。",
                       ["起因—经过—结果", "结果—开头—经过", "经过—起因—结果"], "A",
                      "按起因、经过、结果写清楚。", 2),
                judge("把事情写具体，要写清人物的动作、语言和神态。", True,
                      "细节描写让事情更生动。", 2),
                fill("记叙文六要素是：时间、地点、人物、起因、经过、（  ）。", "结果",
                     "六要素齐全，事情才完整。", 3),
                choice("写“包饺子”，最应重点写清的是（  ）。",
                       ["包饺子的过程", "饺子的历史", "碗的颜色"], "A",
                      "重点写主要过程，详略得当。", 3),
            ]),
        ],
    },
}


# ---------------------------------------------------------------------------
# 小学英语 1-3 年级（牛津深圳版）
# ---------------------------------------------------------------------------

ENGLISH_CURRICULUM: dict[int, dict[str, list]] = {
    1: {
        "first": [
            ("Greetings 问候", "会用 Hello/Hi/Good morning 问候并自我介绍", [
                choice("早上见到老师应说：（  ）",
                       ["Good morning!", "Good night!", "Goodbye!"], "A",
                       "早上好用 Good morning。", 1),
                fill("别人对你说 Hello，你应回答：（  ）（填一个单词）", "Hello",
                     "用 Hello/Hi 回应问候。", 1),
                judge("“Goodbye”表示告别。", True, "Goodbye=再见。", 1),
                choice("自我介绍名字时说：（  ）",
                       ["I'm Tom.", "I'm fine.", "I'm six."], "A",
                       "I'm + 名字 用于自我介绍。", 2),
            ]),
            ("Colours 颜色", "认读 red/yellow/blue/green 等颜色词", [
                choice("香蕉的颜色是：（  ）", ["yellow", "blue", "green"], "A",
                       "香蕉是 yellow（黄色）。", 1),
                judge("“blue”表示蓝色。", True, "blue=蓝色。", 1),
                fill("红灯的英文是：（  ） light.", "red", "red=红色。", 1),
                choice("草地的颜色是：（  ）", ["green", "red", "black"], "A",
                       "草地是 green（绿色）。", 2),
            ]),
            ("Numbers 1-10", "认读并数数 1-10", [
                fill("“三”的英文是：（  ）", "three", "three=三。", 1),
                choice("How many? 🍎🍎🍎 （  ）", ["three", "five", "two"], "A",
                       "图中有3个苹果：three。", 1),
                judge("“ten”表示数字 10。", True, "ten=十。", 1),
                fill("2 + 3 = （  ）（写英文数词）", "five", "2+3=5，five。", 2),
            ]),
        ],
        "second": [
            ("School things 文具", "认读 pen/pencil/ruler/bag 等", [
                choice("用来写字、带橡皮头的是：（  ）", ["pencil", "bag", "dog"], "A",
                       "pencil=铅笔。", 1),
                fill("“尺子”的英文是：（  ）", "ruler", "ruler=尺子。", 1),
                judge("“bag”意思是书包。", True, "bag=书包/袋子。", 1),
                choice("Show （  ） your pen. 空格意思是“给我看看”，应填：（  ）",
                       ["me", "I", "my"], "A", "Show me... 给我看看……。", 3),
            ]),
            ("Animals 动物", "认读 cat/dog/pig/bird 等动物词，会用 What's this?", [
                choice("“汪汪”叫的动物是：（  ）", ["dog", "cat", "duck"], "A",
                       "dog=狗。", 1),
                fill("“猫”的英文是：（  ）", "cat", "cat=猫。", 1),
                judge("问“这是什么”用：What's this?", True,
                      "What's this?=这是什么？", 2),
                choice("—What's this? —It's （  ） elephant.",
                       ["an", "a", "two"], "A",
                       "elephant以元音音素开头，用an。", 3),
            ]),
            ("My body 身体部位", "认读 eye/ear/nose/mouth/face", [
                choice("We see with our （  ）.", ["eyes", "ears", "mouth"], "A",
                       "用眼睛(eyes)看东西。", 2),
                fill("“鼻子”的英文是：（  ）", "nose", "nose=鼻子。", 1),
                judge("We hear with our ears.（我们用耳朵听。）", True,
                      "ears=耳朵，用来听。", 2),
                choice("Touch your （  ）.（摸你的嘴巴）", ["mouth", "nose", "eye"], "A",
                       "mouth=嘴巴。", 2),
            ]),
        ],
    },
    2: {
        "first": [
            ("My family 家庭成员", "认读 father/mother/brother/sister 等", [
                choice("爸爸的英文是：（  ）", ["father", "mother", "sister"], "A",
                       "father=父亲。", 1),
                fill("妈妈的英文是：（  ）", "mother", "mother=母亲。", 1),
                judge("“brother”指兄弟。", True, "brother=兄/弟。", 1),
                choice("This is （  ） sister.（这是我的妹妹）",
                       ["my", "I", "me"], "A", "形容词性物主代词 my+名词。", 3),
            ]),
            ("Food 食物", "认读 rice/bread/milk/egg 等，会用 I like...", [
                choice("早餐常喝的白色饮品是：（  ）", ["milk", "bread", "fish"], "A",
                       "milk=牛奶。", 1),
                fill("“鸡蛋”的英文是：（  ）", "egg", "egg=鸡蛋。", 1),
                judge("I like apples. 表示“我喜欢苹果”。", True,
                      "like+食物表示喜欢。", 2),
                choice("I don't like （  ）.（我不喜欢鱼）",
                       ["fish", "rice", "cake"], "A", "fish=鱼。", 2),
            ]),
            ("Numbers 11-20", "认读 11-20，发现 -teen 规律", [
                fill("“十五”的英文是：（  ）", "fifteen", "fifteen=15。", 2),
                choice("12 的英文是：（  ）", ["twelve", "twenty", "two"], "A",
                       "twelve=12。", 1),
                judge("“twenty”表示 20。", True, "twenty=20。", 1),
                fill("13 的英文是：（  ）", "thirteen", "thirteen=13。", 2),
            ]),
        ],
        "second": [
            ("Clothes 服装", "认读 shirt/skirt/cap/shoes，会用 put on", [
                choice("女孩子穿的裙子是：（  ）", ["skirt", "shirt", "shoe"], "A",
                       "skirt=短裙。", 2),
                fill("“鞋子”常用复数形式：（  ）", "shoes", "shoes=鞋（成双）。", 2),
                judge("Put on your cap. 意思是“戴上你的帽子”。", True,
                      "put on=穿上/戴上。", 2),
                choice("These （  ） my shoes.", ["are", "is", "am"], "A",
                       "these/复数后用 are。", 3),
            ]),
            ("Action verbs 动作", "认读 run/jump/swim/fly，会用 Can you...?", [
                choice("小鸟会：（  ）", ["fly", "swim", "read"], "A",
                       "fly=飞。", 1),
                fill("“跑”的英文是：（  ）", "run", "run=跑。", 1),
                judge("—Can you swim? —Yes, I can.", True,
                      "Can you...? 问能力，肯定回答 Yes, I can.", 2),
                choice("—Can a fish fly? —（  ）",
                       ["No, it can't.", "Yes, I can.", "No, I can't."], "A",
                       "主语是 a fish，用 it；鱼不会飞。", 3),
            ]),
            ("Toys & colours 综合", "用 What colour is it? 问答颜色", [
                choice("—What colour is the ball? —It's （  ）.（红色）",
                       ["red", "a red", "reds"], "A", "It's + 颜色词，不加冠词。", 2),
                fill("“玩具”的英文是：（  ）", "toy", "toy=玩具。", 2),
                judge("What colour is it? 用来询问颜色。", True,
                      "what colour=什么颜色。", 1),
                choice("I have （  ） doll.", ["a", "an", "two"], "A",
                       "doll以辅音音素开头，用a。", 3),
            ]),
        ],
    },
    3: {
        "first": [
            ("My school 学校场所", "认读 classroom/library/playground", [
                choice("我们在（  ）里读书、借书。", ["library", "toilet", "shop"], "A",
                       "library=图书馆。", 2),
                fill("“操场”的英文是：（  ）", "playground", "playground=操场。", 2),
                judge("classroom 的意思是教室。", True, "classroom=教室。", 1),
                choice("We play football on the （  ）.",
                       ["playground", "library", "classroom"], "A",
                       "在操场踢足球。", 2),
            ]),
            ("Weather 天气", "认读 sunny/rainy/windy/cloudy，会用 How's the weather?", [
                choice("下大雨的天气是：（  ）", ["rainy", "sunny", "windy"], "A",
                       "rainy=下雨的。", 2),
                fill("“晴朗的”英文是：（  ）", "sunny", "sunny=晴朗的。", 2),
                judge("—How's the weather? —It's windy.", True,
                      "How's the weather? 问天气。", 2),
                choice("It's （  ）. We can make a snowman.",
                       ["snowy", "hot", "rainy"], "A",
                       "下雪天(snowy)才能堆雪人。", 3),
            ]),
            ("现在进行时初步", "理解 be + doing 表示正在做某事", [
                choice("Look! The boy （  ） football.",
                       ["is playing", "plays", "play"], "A",
                       "Look!提示现在进行时：be+doing。", 3),
                judge("“I am reading.”表示我正在看书。", True,
                      "am reading=正在读。", 2),
                fill("They are （  ）（swim）now. 填 swim 的 -ing 形式：", "swimming",
                     "swim双写m加ing：swimming。", 4),
                choice("—What are you doing? —（  ）",
                       ["I'm singing.", "I can sing.", "I like singing."], "A",
                       "问正在做什么，用现在进行时回答。", 3),
            ]),
        ],
        "second": [
            ("Daily activities 日常活动", "用一般现在时描述习惯性动作", [
                choice("I （  ） my teeth every morning.",
                       ["brush", "brushes", "brushing"], "A",
                       "I/you/we/they 后用动词原形。", 3),
                fill("“起床”的英文短语是：get （  ）", "up", "get up=起床。", 2),
                judge("She goes to school at seven. 中 goes 用对了。", True,
                      "she 是第三人称单数，go→goes。", 3),
                choice("He （  ） TV after dinner.",
                       ["watches", "watch", "watching"], "A",
                       "he 三单，watch→watches。", 3),
            ]),
            ("Prepositions 方位介词", "掌握 in/on/under/behind", [
                choice("球在桌子下面应说：The ball is （  ） the table.",
                       ["under", "on", "in"], "A", "under=在……下面。", 2),
                fill("书在书桌上：The book is （  ） the desk.", "on",
                     "on=在……上面（接触）。", 2),
                judge("The cat is in the box. 表示猫在盒子外面。", False,
                      "in 表示在盒子里面。", 2),
                choice("—Where is the bag? —It's （  ） the door.（门后面）",
                       ["behind", "in", "under"], "A", "behind=在……后面。", 3),
            ]),
            ("Shopping 购物", "会用 How much is it? 问价格并回答", [
                choice("询问价格应说：（  ）",
                       ["How much is it?", "How old are you?", "What is it?"], "A",
                       "How much=多少钱。", 2),
                fill("—How much is it? —（  ） yuan.（十元）", "Ten",
                     "直接用数词回答价格。", 2),
                judge("在商店里店员常说：Can I help you?", True,
                      "Can I help you?=您想买点什么？", 2),
                choice("—Can I help you? —（  ）",
                       ["I want a pen, please.", "I'm ten.", "I'm fine."], "A",
                       "说明想买的东西。", 3),
            ]),
        ],
    },
}


# ---------------------------------------------------------------------------
# 4-12 年级样章题库（每学科 1 章 × 2 知识点 × 3 题）
# ---------------------------------------------------------------------------

DEMO_CHAPTERS: dict[str, tuple[str, list[tuple[str, str, list]]]] = {
    "chinese": (
        "现代文阅读·词句赏析", [
            ("赏析句子的方法", "手法 + 内容 + 情感三步表述", [
                choice("赏析比喻句的答题步骤是（  ）。",
                       ["点明手法→分析内容→体会情感", "抄写原句→谈感受→默写",
                        "翻译句子→背答案"], "A", "规范答题三步法。", 3),
                judge("“一切景语皆情语”说明景物描写常寄托作者情感。", True,
                      "赏析景物描写要联系情感。", 2),
                fill("句子“树叶在风中跳舞”运用了（  ）的修辞手法。（2字）", "拟人",
                     "把树叶当作人来写。", 3),
            ]),
            ("病句与标点", "常见病句类型与标点规范", [
                choice("“通过这次学习，使我明白了道理。”的病因是（  ）。",
                       ["成分残缺（缺主语）", "搭配不当", "语序不当"], "A",
                       "“通过……使……”导致无主语。", 3),
                judge("并列书名号之间通常不用顿号。", True,
                      "如《春》《背影》，书名号间不再加顿号。", 3),
                fill("直接引用人物说话，提示语在中间时，提示语后用（  ）号。（1字）",
                     "逗", "“××，”他说，“××。”", 4),
            ]),
        ]
    ),
    "math": (
        "数与式·运算基础", [
            ("有理数与代数式", "符号法则、去括号、合并同类项", [
                fill("计算：(-3) + 5 = （  ）。", "2", "异号相加：5-3=2。", 2),
                choice("化简 3x + 2x - x 的结果是（  ）。",
                       ["4x", "5x", "6x"], "A", "3x+2x-x=4x。", 3),
                judge("去括号：-(a - b) = -a + b。", True,
                      "括号前是负号，去括号要变号。", 3),
            ]),
            ("方程与函数初步", "解方程、一次函数图象", [
                fill("解方程：2x - 6 = 0，x = （  ）。", "3", "2x=6，x=3。", 3),
                choice("一次函数 y = 2x + 1 的图象是（  ）。",
                       ["一条直线", "抛物线", "双曲线"], "A",
                       "一次函数图象是直线。", 2),
                judge("函数 y = -x + 3 中，y 随 x 增大而减小。", True,
                      "斜率 -1 < 0，单调递减。", 4),
            ]),
        ]
    ),
    "english": (
        "Grammar in use", [
            ("Tenses 时态", "一般现在/过去/将来时的区分", [
                choice("She usually （  ） to school by bus.",
                       ["goes", "went", "will go"], "A",
                       "usually 表习惯，用一般现在时；she 三单。", 3),
                judge("I have finished my homework. 是现在完成时。", True,
                      "have/has + 过去分词。", 3),
                fill("动词 go 的过去式是：（  ）", "went", "go-went-gone 不规则变化。", 2),
            ]),
            ("Vocabulary & reading", "考纲词汇与语篇理解", [
                choice("“environment”的中文意思是（  ）。",
                       ["环境", "政府", "实验"], "A", "environment=环境。", 2),
                judge("阅读主旨题应关注每段首句和文章标题。", True,
                      "主题句常出现在段首。", 2),
                fill("“important”的名词形式是：（  ）", "importance",
                     "important(adj.)→importance(n.)。", 4),
            ]),
        ]
    ),
    "physics": (
        "力学基础", [
            ("运动与力", "速度计算、力的三要素、牛顿第一定律", [
                fill("一辆车 2 小时行驶 100 km，平均速度是（  ）km/h。", "50",
                     "v=s/t=100/2=50 km/h。", 2),
                judge("物体不受外力时将保持静止或匀速直线运动状态。", True,
                      "牛顿第一定律（惯性定律）。", 3),
                choice("力的三要素是大小、方向和（  ）。",
                       ["作用点", "时间", "速度"], "A", "三要素决定力的作用效果。", 2),
            ]),
            ("压强与浮力", "压强公式、阿基米德原理", [
                fill("压强公式 p = F / （  ）。", "S", "p=F/S，S为受力面积。", 2),
                judge("浸在液体中的物体受到的浮力等于排开液体所受的重力。", True,
                      "阿基米德原理 F浮=G排=ρ液gV排。", 3),
                choice("刀刃磨得很薄是为了（  ）。",
                       ["增大压强", "减小压强", "增大压力"], "A",
                       "减小受力面积可增大压强。", 3),
            ]),
        ]
    ),
    "chemistry": (
        "化学用语与基本概念", [
            ("元素与化学式", "元素符号、化合价、化学式书写", [
                fill("氧元素的元素符号是：（  ）", "O", "氧 O；注意大写。", 1),
                judge("H₂O 表示水由氢、氧两种元素组成。", True,
                      "化学式宏观表示物质组成。", 2),
                fill("二氧化碳的化学式是：（  ）（下标数字正常写）", "CO2",
                     "CO₂，写作 CO2。", 2),
            ]),
            ("化学方程式", "质量守恒与方程式书写", [
                judge("书写化学方程式必须配平并注明反应条件。", True,
                      "遵守质量守恒定律。", 2),
                fill("氢气在氧气中燃烧的化学方程式：2H₂ + O₂ 点燃 2（  ）。", "H2O",
                     "2H₂+O₂ 点燃 2H₂O。", 3),
                choice("化学反应前后一定不变的是（  ）。",
                       ["原子种类和数目", "分子种类", "物质颜色"], "A",
                       "质量守恒：原子种类、数目、质量不变。", 3),
            ]),
        ]
    ),
    "biology": (
        "生物体的结构与功能", [
            ("细胞与生物体", "细胞结构、动植物细胞区别", [
                choice("控制物质进出细胞的结构是（  ）。",
                       ["细胞膜", "细胞壁", "液泡"], "A", "细胞膜具有选择透过性。", 2),
                judge("植物细胞有细胞壁和叶绿体，动物细胞没有。", True,
                      "动植物细胞的主要区别。", 2),
                fill("细胞生命活动的控制中心是（  ）。（2字）", "细胞",
                     "细胞核含遗传物质，是控制中心。", 3),
            ]),
            ("光合作用与呼吸作用", "两大生理过程的实质", [
                judge("光合作用制造有机物、储存能量；呼吸作用分解有机物、释放能量。",
                      True, "两个过程相反相成。", 3),
                choice("绿色植物光合作用产生的气体是（  ）。",
                       ["氧气", "二氧化碳", "氮气"], "A", "光合作用释放氧气。", 2),
                fill("呼吸作用主要在细胞的（  ）体中进行。（2字）", "线粒",
                     "线粒体是呼吸作用的主要场所。", 4),
            ]),
        ]
    ),
    "history": (
        "中国古代史·时序与制度", [
            ("重大时序", "用时间轴建立历史时序观念", [
                fill("秦统一六国的时间是公元前（  ）年。", "221",
                     "公元前221年，嬴政建立秦朝。", 2),
                judge("隋朝开凿的大运河加强了南北经济文化交流。", True,
                      "隋大运河以洛阳为中心。", 2),
                choice("“贞观之治”出现在（  ）统治时期。",
                       ["唐太宗", "汉武帝", "宋太祖"], "A", "李世民，年号贞观。", 2),
            ]),
            ("制度演变", "中央集权与选官制度", [
                judge("科举制创立于隋朝、完善于唐朝。", True,
                      "分科考试选拔官员。", 2),
                choice("秦朝在地方推行（  ），加强中央集权。",
                       ["郡县制", "分封制", "行省制"], "A", "废分封、行郡县。", 3),
                fill("明朝为加强皇权，废除了延续千年的（  ）制度。（2字）",
                     "丞相", "明太祖废丞相，六部直接听命皇帝。", 3),
            ]),
        ]
    ),
    "geography": (
        "地图与世界地理", [
            ("地图基础", "经纬网、方向、比例尺、等高线", [
                choice("在经纬网地图上，经线指示（  ）方向。",
                       ["南北", "东西", "东北"], "A",
                       "经线连南北极，指示南北；纬线指示东西。", 2),
                judge("比例尺越大，表示的范围越小、内容越详细。", True,
                      "比例尺与范围、详略的关系。", 3),
                fill("等高线越密集，坡度越（  ）。（1字）", "陡",
                     "密陡疏缓。", 2),
            ]),
            ("气候与地形", "气候类型判读、板块学说", [
                judge("全球岩石圈由六大板块拼合而成，板块交界处多火山地震。",
                      True, "板块构造学说。", 3),
                choice("终年高温多雨的气候类型是（  ）。",
                       ["热带雨林气候", "温带海洋性气候", "地中海气候"], "A",
                       "全年高温多雨是热带雨林气候特征。", 3),
                fill("世界最高的高原是（  ）高原。（2字）", "青藏",
                     "青藏高原，“世界屋脊”。", 1),
            ]),
        ]
    ),
    "politics": (
        "道德与法治·观点与材料", [
            ("核心观点", "把材料对应到教材观点", [
                judge("公民的权利和义务是统一的，享有权利必须履行义务。", True,
                      "权利义务相统一。", 2),
                choice("“国家的一切权力属于人民”，这是我国（  ）的核心内容。",
                       ["宪法", "刑法", "民法典"], "A",
                       "宪法是国家的根本法。", 2),
                fill("全面依法治国的总目标是建设中国特色社会主义法治体系、建设社会主义（  ）国家。（2字）",
                     "法治", "建设社会主义法治国家。", 3),
            ]),
            ("答题方法", "材料-观点-分析三段论", [
                judge("回答材料分析题应先读设问，再带着问题读材料。", True,
                      "审设问→找信息→联教材→规范答。", 2),
                choice("主观题答案组织一般采用（  ）。",
                       ["材料+教材观点+分析", "只抄材料", "只写自己的想法"], "A",
                       "观点与材料结合，分点作答。", 3),
                fill("价值判断题一般要先（  ）（判断对错），再说明理由。（2字）",
                     "判断", "先明确判断，再陈述理由。", 2),
            ]),
        ]
    ),
}


# ---------------------------------------------------------------------------
# 落库
# ---------------------------------------------------------------------------


def _get_or_create(db, model, defaults: Optional[dict] = None, **filters):
    row = db.scalar(select(model).filter_by(**filters))
    if row is None:
        row = model(**filters, **(defaults or {}))
        db.add(row)
        db.flush()
    return row


def _put_section(
    db, *, subject: str, grade: int, name: str, order_index: int
) -> KnowledgePoint:
    """单元（Chapter）下的"节"节点（L2），幂等。"""
    section = db.scalar(
        select(KnowledgePoint).where(
            KnowledgePoint.subject == subject,
            KnowledgePoint.grade == grade,
            KnowledgePoint.name == name,
            KnowledgePoint.node_type == "section",
        )
    )
    if section is None:
        section = KnowledgePoint(
            subject=subject,
            name=name,
            grade=grade,
            node_type="section",
            order_index=order_index,
        )
        db.add(section)
        db.flush()
    else:
        section.order_index = order_index
    return section


def _put_kp(
    db,
    *,
    subject: str,
    grade: int,
    name: str,
    explanation: str,
    section: KnowledgePoint,
    order_index: int,
) -> KnowledgePoint:
    """知识点（L3），幂等并挂到所属"节"。

    注意：不能直接用 `_get_or_create`——"节"与"知识点"可能同名，必须限定
    `node_type='point'`，否则会把"节"误当成知识点并改成自引用。
    """
    kp = db.scalar(
        select(KnowledgePoint).where(
            KnowledgePoint.subject == subject,
            KnowledgePoint.grade == grade,
            KnowledgePoint.name == name,
            KnowledgePoint.node_type == "point",
        )
    )
    if kp is None:
        kp = KnowledgePoint(
            subject=subject,
            name=name,
            grade=grade,
            node_type="point",
            explanation=explanation,
            parent_id=section.id,
            order_index=order_index,
        )
        db.add(kp)
        db.flush()
    else:
        kp.explanation = explanation
        kp.parent_id = section.id
        kp.order_index = order_index
    return kp


def _prune_default_sections(db) -> int:
    """迁移补建的"默认节"在知识点重新挂接后若无子节点则清理。"""
    db.flush()
    removed = 0
    for section in list(
        db.scalars(
            select(KnowledgePoint).where(
                KnowledgePoint.node_type == "section",
                KnowledgePoint.name == "默认节",
            )
        )
    ):
        if db.scalar(
            select(func.count(KnowledgePoint.id)).where(
                KnowledgePoint.parent_id == section.id
            )
        ) == 0:
            db.delete(section)
            removed += 1
    return removed


def _put_questions(db, *, chapter: Chapter, kp: KnowledgePoint, builders: list[Callable]):
    exists = db.scalar(
        select(Question).where(
            Question.chapter_id == chapter.id,
            Question.knowledge_point_id == kp.id,
        )
    )
    if exists is not None:
        return
    for idx, builder in enumerate(builders):
        data = builder(idx)
        db.add(
            Question(
                chapter_id=chapter.id,
                knowledge_point_id=kp.id,
                subject=kp.subject,
                q_type=data["q_type"],
                content=data["content"],
                options=data["options"],
                answer=data["answer"],
                analysis=data["analysis"],
                difficulty=data["difficulty"],
                tags=[kp.name],
            )
        )
    db.flush()


# ---------------------------------------------------------------------------
# 试卷蓝图（P0-25）：小学语数英单元测各 1 套
# ---------------------------------------------------------------------------

EXAM_BLUEPRINT_SEEDS: list[dict] = [
    {
        "code": "math_primary_unit",
        "name": "小学数学单元测试卷",
        "subject": "math",
        "grade": 3,
        "exam_type": "unit",
        "total_score": 100,
        "time_limit_min": 60,
        "sections": [
            {"name": "一、计算", "q_type": "fill", "count": 10, "score_each": 3, "difficulty": [1, 2]},
            {"name": "二、填空", "q_type": "fill", "count": 10, "score_each": 2, "difficulty": [1, 2]},
            {"name": "三、选择", "q_type": "choice", "count": 10, "score_each": 2, "difficulty": [2, 3]},
            {"name": "四、解决问题", "q_type": "answer", "count": 6, "score_each": 5, "difficulty": [2, 4]},
        ],
        "kp_coverage_min": 0.8,
        "difficulty_mix": {"easy": 0.7, "medium": 0.2, "hard": 0.1},
    },
    {
        "code": "chinese_primary_unit",
        "name": "小学语文单元测试卷",
        "subject": "chinese",
        "grade": 3,
        "exam_type": "unit",
        "total_score": 100,
        "time_limit_min": 60,
        "sections": [
            {"name": "一、字词积累", "q_type": "fill", "count": 10, "score_each": 2, "difficulty": [1, 2]},
            {"name": "二、句子运用", "q_type": "fill", "count": 5, "score_each": 4, "difficulty": [2, 3]},
            {"name": "三、阅读理解", "q_type": "answer", "count": 3, "score_each": 10, "difficulty": [2, 4]},
            {"name": "四、习作", "q_type": "answer", "count": 1, "score_each": 30, "difficulty": [3, 4]},
        ],
        "kp_coverage_min": 0.8,
        "difficulty_mix": {"easy": 0.7, "medium": 0.2, "hard": 0.1},
    },
    {
        "code": "english_primary_unit",
        "name": "小学英语单元测试卷",
        "subject": "english",
        "grade": 3,
        "exam_type": "unit",
        "total_score": 100,
        "time_limit_min": 60,
        "sections": [
            {"name": "一、听力选择", "q_type": "choice", "count": 10, "score_each": 3, "difficulty": [1, 2]},
            {"name": "二、单项选择", "q_type": "choice", "count": 10, "score_each": 2, "difficulty": [1, 2]},
            {"name": "三、阅读理解", "q_type": "choice", "count": 10, "score_each": 2, "difficulty": [2, 3]},
            {"name": "四、书写填空", "q_type": "fill", "count": 10, "score_each": 3, "difficulty": [1, 2]},
        ],
        "kp_coverage_min": 0.8,
        "difficulty_mix": {"easy": 0.7, "medium": 0.2, "hard": 0.1},
    },
]

# 期中/期末（P1-07）：章节集合内组卷，难度按 6:3:1 分数配比（60/30/10）
_COMPREHENSIVE_SECTIONS: dict[str, list[dict]] = {
    "math": [
        {"name": "一、基础计算", "q_type": "fill",
         "count": 10, "score_each": 3, "band": "easy"},
        {"name": "二、基础选择", "q_type": "choice",
         "count": 10, "score_each": 3, "band": "easy"},
        {"name": "三、提升填空", "q_type": "fill",
         "count": 5, "score_each": 4, "band": "medium"},
        {"name": "四、提升应用", "q_type": "answer",
         "count": 2, "score_each": 5, "band": "medium"},
        {"name": "五、综合应用", "q_type": "answer",
         "count": 1, "score_each": 10, "band": "hard"},
    ],
    "chinese": [
        {"name": "一、字词积累", "q_type": "fill",
         "count": 10, "score_each": 2, "band": "easy"},
        {"name": "二、句子运用", "q_type": "fill",
         "count": 10, "score_each": 2, "band": "easy"},
        {"name": "三、课文选择", "q_type": "choice",
         "count": 10, "score_each": 2, "band": "easy"},
        {"name": "四、阅读理解", "q_type": "answer",
         "count": 3, "score_each": 10, "band": "medium"},
        {"name": "五、习作表达", "q_type": "answer",
         "count": 1, "score_each": 10, "band": "hard"},
    ],
    "english": [
        {"name": "一、听力选择", "q_type": "choice",
         "count": 10, "score_each": 3, "band": "easy"},
        {"name": "二、基础填空", "q_type": "fill",
         "count": 10, "score_each": 3, "band": "easy"},
        {"name": "三、单项选择", "q_type": "choice",
         "count": 10, "score_each": 2, "band": "medium"},
        {"name": "四、提升填空", "q_type": "fill",
         "count": 5, "score_each": 2, "band": "medium"},
        {"name": "五、综合表达", "q_type": "answer",
         "count": 1, "score_each": 10, "band": "hard"},
    ],
}


def _comprehensive_blueprint(*, subject: str, label: str, exam_type: str) -> dict:
    suffix = "期中" if exam_type == "midterm" else "期末"
    return {
        "code": f"{subject}_primary_{exam_type}",
        "name": f"小学{label}{suffix}测试卷",
        "subject": subject,
        "grade": 3,
        "exam_type": exam_type,
        "total_score": 100,
        "time_limit_min": 90,
        "sections": _COMPREHENSIVE_SECTIONS[subject],
        "kp_coverage_min": 0.8,
        "difficulty_mix": {"easy": 0.6, "medium": 0.3, "hard": 0.1},
    }


EXAM_BLUEPRINT_SEEDS += [
    _comprehensive_blueprint(subject=subject, label=label, exam_type=exam_type)
    for subject, label in (("math", "数学"), ("chinese", "语文"), ("english", "英语"))
    for exam_type in ("midterm", "final")
]


def _put_blueprint(db, *, code: str, **fields) -> ExamBlueprint:
    """按 code 幂等写入蓝图，重复运行只更新字段。"""
    blueprint = db.scalar(select(ExamBlueprint).where(ExamBlueprint.code == code))
    if blueprint is None:
        blueprint = ExamBlueprint(code=code, **fields)
        db.add(blueprint)
    else:
        for key, value in fields.items():
            setattr(blueprint, key, value)
    db.flush()
    return blueprint


def _seed_blueprints(db) -> int:
    for spec in EXAM_BLUEPRINT_SEEDS:
        fields = {k: v for k, v in spec.items() if k != "code"}
        _put_blueprint(db, code=spec["code"], **fields)
    return len(EXAM_BLUEPRINT_SEEDS)


# P2-07 真题库：按蓝图生成 3 套演示真题（按标题+年份+地区幂等）
PAST_PAPER_SEEDS: list[dict] = [
    {
        "title": "深圳市一年级数学期末真题（2025）",
        "subject": "math",
        "grade": 1,
        "blueprint": "math_primary_unit",
        "year": 2025,
        "region": "深圳",
        "seed": 11,
    },
    {
        "title": "深圳市一年级语文期末真题（2025）",
        "subject": "chinese",
        "grade": 1,
        "blueprint": "chinese_primary_unit",
        "year": 2025,
        "region": "深圳",
        "seed": 12,
    },
    {
        "title": "深圳市三年级数学期末真题（2024）",
        "subject": "math",
        "grade": 3,
        "blueprint": "math_primary_unit",
        "year": 2024,
        "region": "深圳",
        "seed": 13,
    },
]


def _seed_past_papers(db) -> int:
    admin = db.scalar(select(User).where(User.phone == ADMIN_PHONE))
    if admin is None:
        return 0
    created = 0
    for spec in PAST_PAPER_SEEDS:
        exists = db.scalar(
            select(Exam).where(
                Exam.title == spec["title"],
                Exam.year == spec["year"],
                Exam.region == spec["region"],
                Exam.is_past_paper.is_(True),
            )
        )
        if exists is not None:
            continue
        blueprint = db.scalar(
            select(ExamBlueprint).where(ExamBlueprint.code == spec["blueprint"])
        )
        if blueprint is None:
            continue
        chapter_ids = list(
            db.scalars(
                select(Chapter.id)
                .join(Textbook, Chapter.textbook_id == Textbook.id)
                .where(
                    Textbook.subject == spec["subject"],
                    Textbook.grade == spec["grade"],
                )
            )
        )
        if not chapter_ids:
            continue
        paper = generate_paper(
            db,
            user=admin,
            blueprint=blueprint,
            chapter_ids=chapter_ids,
            seed=spec["seed"],
        )
        if not paper.items:
            continue
        db.add(
            Exam(
                title=spec["title"],
                subject=spec["subject"],
                grade=spec["grade"],
                year=spec["year"],
                source="past_paper",
                exam_type="mock",
                total_score=int(round(paper.total_score)),
                time_limit_min=blueprint.time_limit_min,
                questions=[
                    {
                        "question_id": item.question.id,
                        "score": item.score,
                        "section_index": item.section_index,
                        "section_name": item.section_name,
                    }
                    for item in paper.items
                ],
                blueprint_id=blueprint.id,
                chapter_ids=chapter_ids,
                status="published",
                region=spec["region"],
                is_past_paper=True,
            )
        )
        db.flush()
        created += 1
    return created


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # ---- 账号 ----
        if db.scalar(select(User).where(User.phone == ADMIN_PHONE)) is None:
            db.add(User(
                phone=ADMIN_PHONE,
                password_hash=hash_password(ADMIN_PASSWORD),
                nickname="内容管理员",
                role="admin",
            ))
            print(f"已创建管理员：{ADMIN_PHONE} / {ADMIN_PASSWORD}")

        if db.scalar(select(User).where(User.phone == DEMO_STUDENT_PHONE)) is None:
            db.add(User(
                phone=DEMO_STUDENT_PHONE,
                password_hash=hash_password(DEMO_STUDENT_PASSWORD),
                nickname="小深",
                role="student",
                stage="primary",
                grade=1,
            ))
            print(f"已创建体验学生：{DEMO_STUDENT_PHONE} / {DEMO_STUDENT_PASSWORD}")

        # ---- 教材矩阵 + 内容 ----
        matrix: list[tuple[int, str, str]] = []
        for grade in range(1, 7):
            for subj in PRIMARY_SUBJECTS:
                matrix.append((grade, subj, "first"))
                matrix.append((grade, subj, "second"))
        for grade, subjects in JUNIOR_SUBJECTS.items():
            for subj in subjects:
                matrix.append((grade, subj, "first"))
                matrix.append((grade, subj, "second"))
        for grade in (10, 11, 12):
            for subj in SENIOR_SUBJECTS:
                matrix.append((grade, subj, "first"))
                matrix.append((grade, subj, "second"))

        for grade, subj, semester in matrix:
            version = (
                SENIOR_VERSIONS.get(subj, VERSIONS[subj])
                if grade >= 10
                else VERSIONS[subj]
            )
            textbook = _get_or_create(
                db, Textbook,
                subject=subj, grade=grade, version=version, semester=semester,
            )

            # 小学 1-3 年级：完整内容
            if subj == "math" and grade in MATH_CURRICULUM and semester in MATH_CURRICULUM[grade]:
                chapters_spec = MATH_CURRICULUM[grade][semester]
            elif subj == "chinese" and grade in CHINESE_CURRICULUM and semester in CHINESE_CURRICULUM[grade]:
                chapters_spec = CHINESE_CURRICULUM[grade][semester]
            elif subj == "english" and grade in ENGLISH_CURRICULUM and semester in ENGLISH_CURRICULUM[grade]:
                chapters_spec = ENGLISH_CURRICULUM[grade][semester]
            else:
                # 其余：只在 first 学期放一个样章，避免每本教材重复两份
                if semester != "first" or subj not in DEMO_CHAPTERS:
                    continue
                demo_name, kp_specs = DEMO_CHAPTERS[subj]
                chapters_spec = [(f"样章·{demo_name}", kp_specs)]

            for order, spec in enumerate(chapters_spec, start=1):
                chapter = _get_or_create(
                    db, Chapter,
                    textbook_id=textbook.id, name=spec[0],
                    defaults={"grade": grade, "order_index": order},
                )
                section = _put_section(
                    db, subject=subj, grade=grade, name=spec[0], order_index=order
                )
                if len(spec) == 3:
                    # 小学完整内容：(章节名, 章节描述, [题目构造器/题目字典 ...])
                    # 章节名同时作为该章的核心知识点名称
                    _chapter_name, chapter_desc, items = spec
                    kp = _put_kp(db, subject=subj, grade=grade,
                                 name=spec[0], explanation=chapter_desc,
                                 section=section, order_index=1)
                    builders = [
                        it if callable(it) else (lambda i, d=it: d) for it in items
                    ]
                    _put_questions(db, chapter=chapter, kp=kp, builders=builders)
                else:
                    # 样章：(章节名, [(知识点名, 讲解, [题目字典 ...]), ...])
                    for kp_order, (kp_name, kp_explain, qitems) in enumerate(
                        spec[1], start=1
                    ):
                        kp = _put_kp(db, subject=subj, grade=grade,
                                     name=kp_name, explanation=kp_explain,
                                     section=section, order_index=kp_order)
                        builders = [
                            q if callable(q) else (lambda i, d=q: d) for q in qitems
                        ]
                        _put_questions(db, chapter=chapter, kp=kp, builders=builders)

        # 迁移补建的"默认节"在内容重新挂接后若无子节点则清理
        _prune_default_sections(db)

        # ---- 试卷蓝图（小学语数英单元测）----
        n_bp = _seed_blueprints(db)

        # ---- 真题库（P2-07）：演示真题卷，重复运行幂等 ----
        n_pp = _seed_past_papers(db)

        # ---- RBAC 目录与用户角色双写（P2-01，幂等）----
        sync_catalog(db)
        backfill_user_roles(db)

        db.commit()

        n_tb = db.scalar(select(func.count(Textbook.id)))
        n_ch = db.scalar(select(func.count(Chapter.id)))
        n_kp = db.scalar(select(func.count(KnowledgePoint.id)))
        n_q = db.scalar(select(func.count(Question.id)))
        print(f"内容就绪：教材 {n_tb} 本 / 章节 {n_ch} 个 / 知识点 {n_kp} 个 / 题目 {n_q} 道")
        print(f"试卷蓝图就绪：{n_bp} 套")
        print(f"真题库就绪：{n_pp} 套")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
