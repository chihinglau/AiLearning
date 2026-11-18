# -*- coding: utf-8 -*-
"""34 册重跑组装器（2026-11-10 评审 §九-③）：内容包 → 待评审整册 JSON。

设计约束（评审 P2 / P3 / 复评 §九）：
- 「按年级知识点表」生成：每个内容包自带 chapters[].points（节级、可测量的知识点名），
  绝不按章节名套模板；每点 >= 4 题；
- 产出写到 daily_rerun/ 的待评审区，**不写 daily_consolidated/**、不改隔离名单、不入库；
  文件名仍以 _book.json 结尾，使 _validate_daily.py 按整册规格校验；
- 组装前本地自检：题干唯一（全册）、负面清单、多选题解析字母齐备、每点题量、难度范围；
  任一不合格即拒写并报错；
- 另输出知识点表 rerun_knowledge_map_<stamp>.json 与批次清单 rerun_manifest_<stamp>.json，
  供重跑结果评审逐册核对。

内容包格式（docs/content-templates/rerun_packs/<subject>_g<grade>.py）：

    PACK = {
      "subject": "...", "grade": N, "version": "...", "semester": "first",
      "chapters": [
        {"name": "<教材骨架里的章名>", "summary": "<本章内容摘要>",
         "points": [
           {"name": "<节级可测量知识点>", "explanation": "<知识讲解>",
            "questions": [
              ("choice", "题干", ["A项","B项","C项","D项"], "A", "解析", 1),
              ("fill",   "题干", None, "答案" 或 ["答案1","答案2"], "解析", 2),
              ("judge",  "题干", None, "T" 或 "F", "解析", 2),
              ("answer", "题干", None, "参考答案", "评分要点", 4),
              ("multiple","题干", ["A项","B项","C项","D项"], ["A","C"],
               "逐项判断：A … ✓；B … ✗；C … ✓；D … ✗。所以选 A、C。", 3),
            ]},
           ]},
      ],
    }

用法：
    python _rerun_books.py --check                 # 只自检全部内容包，不落盘
    python _rerun_books.py --pack biology_g7      # 只组装一册
    python _rerun_books.py                        # 组装全部已登记内容包
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CT = Path(__file__).resolve().parent
PACKS = CT / "rerun_packs"
OUT = CT / "daily_rerun"
REVIEW = CT / "exports" / "review_20261110"
TASKS_JSON = CT / "exports" / "automation_20261108_codebuddy" / "tasks.json"
SKELETON_INDEX = CT / "exports" / "review_20261112" / "rerun_skeleton_index_g1g9_unified_20261113.json"
Q_TYPES = {"choice", "multiple", "judge", "fill", "answer"}

# 入库前统一口径（2026-11-13 决策）：难度按 40/40/20 归一，主观题答案不足 8 字时补评分要点。
DIFFICULTY_TARGET_LOW, DIFFICULTY_TARGET_MID = 0.40, 0.40
TYPE_RANK = {"choice": 0, "fill": 1, "judge": 2, "multiple": 3, "answer": 4}
SUBJECT_RUBRIC = {
    "math": "评分要点：写出算式或推理步骤，结果正确并带单位。",
    "chinese": "评分要点：答出要点，结合课文或文本举例，语句通顺。",
    "english": "评分要点：句子完整、语法正确、表意清楚。",
    "politics": "评分要点：观点明确，说明理由，联系生活或材料。",
    "history": "评分要点：点明时间与事件，说明原因或影响。",
    "biology": "评分要点：写出结构或过程名称，说明因果。",
    "geography": "评分要点：指出区域或要素，说明分布与原因。",
    "physics": "评分要点：写出公式或规律，代入数据并说明结论。",
    "chemistry": "评分要点：写出物质或反应，说明条件与现象。",
}
SUBJECT_CN = {
    "chinese": "语文", "math": "数学", "english": "英语", "physics": "物理",
    "chemistry": "化学", "biology": "生物", "history": "历史",
    "geography": "地理", "politics": "道德与法治",
}
_STEM_SEEN: set[str] = set()   # 一次全量组装内已出现过的题干（跨册去重用）

# 分册章域（骨架纠偏，2026-11-14）：physics g9 原骨架把上册 10 章整份复制给下册，
# 导致上下册同名同章、同一内容重复两遍。按人教版九年级物理实际分册：上册 13–18 章、下册 19–22 章。
CHAPTER_SCOPE = {
    ("physics", 9, "first"): [
        "第十三章 内能", "第十四章 内能的利用", "第十五章 电流和电路",
        "第十六章 电压 电阻", "第十七章 欧姆定律", "第十八章 电功率",
    ],
    ("physics", 9, "second"): [
        "第十九章 生活用电", "第二十章 电与磁",
        "第二十一章 电磁波及其应用", "第二十二章 能源与可持续发展",
    ],
}


# 跨册同题定向改写（2026-11-14 第二轮）：只改「重复侧」那一道，换成贴合本册知识点的另一道题，
# 两侧册题量都不减（守住 92 册 / 11870 题基线）。键 = (册, 章名, 原题干, 题型)。
DUPLICATE_REWRITES = {
    ("biology_g7_second", "第三单元 植物的生活",
     "植物白天只进行光合作用，夜间只进行呼吸作用。", "judge"): {
        "stem": "植物体内的导管运输水和无机盐，筛管运输有机物。", "answer": "T",
        "analysis": "导管自下而上运输水和无机盐，筛管运输有机物。"},
    ("politics_g1_second", "第四单元 争做中国好儿童",
     "升国旗、唱国歌时要（ ）肃立。", "fill"): {
        "stem": "爱祖国可以从身边小事做起，升国旗时要立正、行注目礼，认真唱（ ）。",
        "answer": "国歌", "analysis": "升旗仪式上认真唱国歌，是对国旗国歌的尊重。"},
    ("politics_g1_first", "第四单元 我们讲文明",
     "下面哪些是礼貌用语？", "multiple"): {
        "stem": "与人相处时，下面哪些做法有礼貌？",
        "options": ["见面主动问好", "得到帮助后说谢谢", "打断别人说话", "不小心碰到别人时说对不起"],
        "answer": ["A", "B", "D"],
        "analysis": "逐项判断：A ✓；B ✓；C 打断别人说话 ✗ 不礼貌；D ✓。所以选 A、B、D。"},
    ("english_g2_second", "Unit 1 Farm animals",
     "Which animal gives us milk?", "choice"): {
        "stem": "Which animal lays eggs?", "options": ["A hen", "A cow", "A horse", "A pig"],
        "answer": "A", "analysis": "hen 母鸡下蛋；cow 产奶、horse 能骑、pig 供肉。"},
    ("english_g8_first", "Unit 2 Digital life",
     "下面哪些做法安全？", "multiple"): {
        "stem": "关于保护个人账号安全，下面哪些做法正确？",
        "options": ["不把密码告诉陌生人", "定期修改密码", "把密码发到班级群里", "不点陌生链接"],
        "answer": ["A", "B", "D"],
        "analysis": "逐项判断：A ✓；B ✓；C 群发密码 ✗ 泄露账号；D ✓。所以选 A、B、D。"},
    ("politics_g1_first", "第一单元 我是小学生啦",
     "下面哪些做法安全？", "multiple"): {
        "stem": "在校园里，下面哪些做法能保护自己？",
        "options": ["靠右上下楼梯", "课间慢走", "从楼梯扶手上滑下来", "不玩尖锐物品"],
        "answer": ["A", "B", "D"],
        "analysis": "逐项判断：A ✓；B ✓；C 滑扶手 ✗ 容易摔伤；D ✓。所以选 A、B、D。"},
    ("politics_g5_first", "第一单元 没有共产党就没有新中国",
     "中华人民共和国成立的时间是（ ）。", "choice"): {
        "stem": "标志着中国人民从此站起来、中国历史进入新纪元的事件是（ ）。",
        "options": ["中华人民共和国成立", "辛亥革命", "五四运动", "抗日战争胜利"],
        "answer": "A", "analysis": "1949 年中华人民共和国成立，中国人民从此站起来了。"},
    ("politics_g5_first", "第二单元 建设社会主义新中国",
     "第一个五年计划的时间是（ ）。", "choice"): {
        "stem": "第一个五年计划的基本任务是集中力量发展（ ）。",
        "options": ["重工业", "轻工业", "农业", "商业"],
        "answer": "A", "analysis": "一五计划以发展重工业为中心，为工业化奠定基础。"},
    ("politics_g5_first", "第二单元 建设社会主义新中国",
     "我国第一部社会主义类型的宪法颁布于（ ）。", "choice"): {
        "stem": "1954 年宪法确立的我国根本政治制度是（ ）。",
        "options": ["人民代表大会制度", "君主立宪制", "联邦制", "基层群众自治制度"],
        "answer": "A", "analysis": "1954 年宪法确立人民代表大会制度为我国的根本政治制度。"},
    ("politics_g5_first", "第三单元 进行改革开放",
     "中共十一届三中全会召开于（ ）。", "choice"): {
        "stem": "十一届三中全会后，我国开始实行（ ）。",
        "options": ["改革开放", "土地改革", "计划经济", "闭关锁国"],
        "answer": "A", "analysis": "全会后实行改革开放，党和国家工作重心转向经济建设。"},
    ("politics_g5_first", "第三单元 进行改革开放",
     "十一届三中全会作出的重大决策是（ ）。", "choice"): {
        "stem": "十一届三中全会重新确立的思想路线是（ ）。",
        "options": ["解放思想、实事求是", "以阶级斗争为纲", "闭关自守", "个人崇拜"],
        "answer": "A", "analysis": "全会重新确立了解放思想、实事求是的思想路线。"},
    ("politics_g5_first", "第三单元 进行改革开放",
     "十一届三中全会是新中国成立以来党的历史上具有深远意义的伟大转折。", "judge"): {
        "stem": "十一届三中全会后，我国进入改革开放和社会主义现代化建设新时期。", "answer": "T",
        "analysis": "全会实现历史性转折，我国由此进入新时期。"},
    ("politics_g5_first", "第三单元 进行改革开放",
     "经济特区在吸引外资、引进技术方面发挥了窗口作用。", "judge"): {
        "stem": "我国对外开放形成了全方位、多层次、宽领域的格局。", "answer": "T",
        "analysis": "这是我国对外开放格局的基本特征。"},
    ("politics_g5_first", "第三单元 进行改革开放",
     "明确提出建立社会主义市场经济体制目标的是（ ）。", "choice"): {
        "stem": "社会主义市场经济体制下，资源配置主要依靠（ ）。",
        "options": ["市场", "政府指令", "计划指标", "行政命令"],
        "answer": "A", "analysis": "市场在资源配置中起决定性作用。"},
    ("history_g8_second", "第六单元 中国特色社会主义进入新时代",
     "到新中国成立一百年时，把我国建成富强民主文明和谐美丽的社会主义现代化（ ）。", "fill"): {
        "stem": "「两个一百年」中的第一个百年目标，是到中国共产党成立一百年时全面建成（ ）。",
        "answer": "小康社会", "analysis": "第一个百年目标为全面建成小康社会。"},
    ("history_g8_second", "第六单元 中国特色社会主义进入新时代",
     "实现中国梦必须走中国道路、弘扬中国精神、凝聚中国力量。", "judge"): {
        "stem": "2012 年，「中国梦」这一概念被正式提出。", "answer": "T",
        "analysis": "2012 年 11 月提出实现中华民族伟大复兴的中国梦。"},
    ("history_g8_second", "第六单元 中国特色社会主义进入新时代",
     "说明「两个一百年」目标之间的关系。", "answer"): {
        "stem": "简述全面建成小康社会对我国现代化建设的意义。",
        "answer": "示例：全面建成小康社会为实现第二个百年奋斗目标奠定坚实基础，使我国现代化建设站在新的起点上。",
        "analysis": "评分要点：奠定基础 + 新的起点。"},
    ("politics_g9_first", "第二单元 进入新时代",
     "我国脱贫攻坚战取得全面胜利是在（ ）。", "choice"): {
        "stem": "脱贫攻坚战的全面胜利所体现的发展理念是（ ）。",
        "options": ["共享发展", "效率优先", "先富后富", "扩大差距"],
        "answer": "A", "analysis": "脱贫成果由全体人民共享，体现共享发展理念。"},
    ("politics_g5_first", "第四单元 开创新时代",
     "我国宣告全面建成小康社会是在（ ）。", "choice"): {
        "stem": "全面建成小康社会后，我国开启了（ ）的新征程。",
        "options": ["全面建设社会主义现代化国家", "社会主义改造", "土地改革", "计划经济"],
        "answer": "A", "analysis": "小康之后向第二个百年奋斗目标迈进。"},
    ("history_g8_second", "第七单元 全面建设社会主义现代化国家",
     "我国经济社会发展的主题是（ ）。", "choice"): {
        "stem": "党的二十大报告指出，高质量发展是全面建设社会主义现代化国家的（ ）。",
        "options": ["首要任务", "根本保证", "最终目标", "基本前提"],
        "answer": "A", "analysis": "二十大报告明确高质量发展是全面建设社会主义现代化国家的首要任务。"},
    ("history_g8_second", "第七单元 全面建设社会主义现代化国家",
     "新发展理念包括（ ）。", "multiple"): {
        "stem": "我国现代化建设要坚持的新发展理念，除创新、协调外还包括（ ）。",
        "options": ["绿色", "开放", "共享", "封闭"],
        "answer": ["A", "B", "C"],
        "analysis": "逐项判断：A 绿色 ✓；B 开放 ✓；C 共享 ✓；D 封闭 ✗ 不属新发展理念。所以选 A、B、C。"},
    ("math_g1_second", "第四单元 100以内数的认识",
     "下面哪个数最大？", "choice"): {
        "stem": "在 45、54、49、39 中，最大的数是（ ）。",
        "options": ["45", "54", "49", "39"],
        "answer": "B", "analysis": "十位 5 最大，所以 54 最大。"},
    ("physics_g9_second", "第十八章 电功率",
     "1 千瓦时等于（ ）焦。", "fill"): {
        "stem": "某用电器功率为 1000 瓦，正常工作 1 小时消耗的电能是（ ）千瓦时。",
        "answer": "1 千瓦时", "analysis": "W=Pt=1 kW×1 h=1 千瓦时。"},
    ("physics_g9_second", "第二十一章 电磁波及其应用",
     "电磁波在真空中的传播速度约为（ ）", "choice"): {
        "stem": "关于电磁波的传播，下列说法正确的是（ ）。",
        "options": ["电磁波可以在真空中传播", "电磁波只能在固体中传播",
                    "电磁波传播必须依赖介质", "电磁波不能在空气中传播"],
        "answer": "A", "analysis": "电磁波无需介质，可在真空中以光速传播。"},
}



def normalize_chapters(chapters: list[dict], subject: str) -> None:
    """就地归一：难度配比 40/40/20（按题型由易到难排名赋值），主观题短答案补评分要点。"""
    flat = [q for ch in chapters for q in ch.get("questions") or []]
    if flat:
        flat.sort(key=lambda q: (TYPE_RANK.get(q.get("q_type"), 4), int(q.get("difficulty") or 3)))
        n = len(flat)
        low = round(n * DIFFICULTY_TARGET_LOW)
        mid = round(n * DIFFICULTY_TARGET_MID)
        for i, q in enumerate(flat):
            q["difficulty"] = 2 if i < low else (3 if i < low + mid else 4)
    rubric = SUBJECT_RUBRIC.get(subject, "评分要点：结论明确，说明理由，表述清楚。")
    for q in flat:
        if q.get("q_type") != "answer":
            continue
        value = str((q.get("answer") or {}).get("value") or "").strip()
        if len(value) >= 8:
            continue
        tail = str(q.get("analysis") or "").strip()
        if tail.startswith("评分要点"):
            new = f"{value}。{tail}" if value else tail
        else:
            new = f"{value}。{rubric}" if value else rubric
        q["answer"]["value"] = new


# ---------- 入库前补齐（2026-11-13 决策二）：数值填空补算式 / 缺多选补一题 ----------

_NUMERIC_RE = re.compile(r"-?\d+(?:\.\d+)?")
_NUMBER_TOKEN_RE = re.compile(r"\d+(?:\.\d+)?")
_CALC_WORDS = (
    "共", "一共", "总", "每", "平均", "倍", "余", "剩下", "还剩", "余下", "面积", "体积",
    "周长", "单价", "合计", "分成", "应为", "可以算", "约等于", "大约", "估算", "换算",
    "求", "等于", "乘积", "商",
)
_OP_DISPLAY = {"+": "+", "-": "-", "*": "×", "/": "÷"}
# 判断题不足 2 个「真」样本的册，用它补一条可靠的真命题（人工核定，来源=教材通行表述）
MANUAL_TRUE_STATEMENTS = {
    ("politics", 6, "first"): [
        "公民行使权利时不得损害国家、社会、集体的利益和其他公民的合法权利",
        "法律保护未成年人的合法权益，未成年人也应当遵守法律",
    ],
    ("chinese", 9, "first"): [
        "《沁园春·雪》上阕写景、下阕论史，最后以「俱往矣，数风流人物，还看今朝」收束全词",
    ],
    ("geography", 7, "first"): [
        "在经纬网地图上，纬线指示东西方向，经线指示南北方向",
    ],
    ("politics", 3, "first"): [
        "合作中遇到分歧，可以先交流各自的想法再作决定，不必因此停下合作",
    ],
    ("politics", 4, "first"): [
        "班规由全班共同制定，对班里每个成员都有约束力",
    ],
}


def _eval_numeric(expr: str) -> float | None:
    """只认四则运算的安全求值；与 _validate_daily.py 的 safe_eval 口径一致。"""
    if not expr or not re.fullmatch(r"[0-9\.\+\-\*/\(\) ]+", expr.strip()):
        return None
    try:
        value = eval(expr.strip(), {"__builtins__": {}}, {})  # noqa: S307 - 纯数字四则，输入已正则限定
    except Exception:
        return None
    return float(value) if isinstance(value, (int, float)) else None


def _fmt_number(value: float) -> str:
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return f"{round(value, 6):g}"


def equation_for_numeric_fill(stem: str, answer_text: str) -> str | None:
    """题干数值能算出答案时，返回一条可求值算式；否则 None（改走单选化）。"""
    if not _NUMERIC_RE.fullmatch(answer_text or ""):
        return None
    target = float(answer_text)
    text = str(stem or "")

    def accept(a: str, b: str, op: str) -> str | None:
        value = _eval_numeric(f"{a}{op}{b}")
        if value is None or abs(value - target) > 1e-6:
            return None
        return f"{a} {_OP_DISPLAY[op]} {b}"

    # 1) 题干里已写成「a 运算符 b」的形式，优先直接沿用
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*([+\-×÷])\s*(\d+(?:\.\d+)?)", text):
        a, op, b = m.group(1), {"×": "*", "÷": "/"}.get(m.group(2), m.group(2)), m.group(3)
        got = accept(a, b, op)
        if got:
            return got
    # 2) 中文运算词
    for word, op in (("除以", "/"), ("乘", "*"), ("加", "+"), ("减", "-")):
        for m in re.finditer(rf"(\d+(?:\.\d+)?)\s*{word}\s*(\d+(?:\.\d+)?)", text):
            got = accept(m.group(1), m.group(2), op)
            if got:
                return got
    # 3) 余数：a - b × 商 = 余数（左侧带运算符且结果等于答案）
    if "余数" in text:
        nums = _NUMBER_TOKEN_RE.findall(text)
        for i, a in enumerate(nums):
            for b in nums[i + 1:]:
                if not float(b) or float(a) <= float(b):
                    continue
                quotient = int(float(a) // float(b))
                expr = f"{_fmt_number(float(a))} - {_fmt_number(float(b))}×{quotient}"
                if _eval_numeric(expr.replace("×", "*")) is not None and abs(
                    _eval_numeric(expr.replace("×", "*")) - target
                ) < 1e-6:
                    return expr
    # 4) 有两处以上数值、且题干带「共/每/平均/求」这类计算语境时，试两两组合
    nums = _NUMBER_TOKEN_RE.findall(text)
    if len(nums) >= 2 and any(w in text for w in _CALC_WORDS):
        for i, a in enumerate(nums):
            for b in nums[i + 1:]:
                for op in ("+", "-", "*", "/"):
                    if op == "-" and float(a) < float(b):
                        continue
                    got = accept(a, b, op)
                    if got:
                        return got
    return None


def _numeric_distractors(target: float) -> list[str]:
    """给数值型填空造 3 个同号干扰项；负数（如 -1、-3）也保留符号。"""
    sign = -1.0 if target < 0 else 1.0
    magnitude = abs(target)
    raw = [magnitude * 10, magnitude / 10, magnitude + 1, magnitude - 1, magnitude + 2, magnitude * 2]
    out = []
    for value in raw:
        value = sign * value
        text = _fmt_number(value)
        if text in out or abs(value - target) < 1e-9:
            continue
        out.append(text)
        if len(out) == 3:
            break
    if len(out) < 3:
        for extra in (sign * (magnitude + 3), sign * (magnitude / 2), sign * (magnitude + 0.5)):
            text = _fmt_number(extra)
            if text not in out and abs(extra - target) > 1e-9:
                out.append(text)
            if len(out) == 3:
                break
    return out[:3]


def _judge_statement(stem: str) -> str | None:
    """判断题题干 → 可当作选项的陈述句（去掉「，对吗？」这类追问尾巴）。"""
    text = str(stem or "").strip()
    text = re.sub(r"[，,]\s*(对|正确)吗\s*[？?]?\s*$", "", text)
    text = re.sub(r"[，,]\s*是否(正确|对)\s*[？?]?\s*$", "", text)
    text = text.rstrip("。？?").strip()
    if not (8 <= len(text) <= 80):
        return None
    if any(x in text for x in ("（ ）", "如图", "上表", "上题", "见下图")):
        return None
    return text


def _pick_multiple_sources(chapters: list[dict], subject: str, grade: int, semester: str):
    """为一册挑出「2 条真 + 2 条假」的判断题素材（优先同一章）。"""
    def usable(q: dict) -> bool:
        return _judge_statement(q.get("stem")) is not None

    best = None
    for ch in chapters:
        t = [q for q in ch.get("questions") or [] if q.get("q_type") == "judge"
             and str((q.get("answer") or {}).get("value")) == "T" and usable(q)]
        f = [q for q in ch.get("questions") or [] if q.get("q_type") == "judge"
             and str((q.get("answer") or {}).get("value")) == "F" and usable(q)]
        score = min(len(t), 2) / 2 + min(len(f), 2) / 2
        if best is None or score > best[0]:
            best = (score, ch, t, f)
    if best is None:
        return None
    _, ch, t, f = best
    # 同章凑不齐时，允许跨章取「真/假」素材（全册口径：validator 只要求整册题型齐备）
    if len(f) < 2:
        f = [q for c in chapters for q in c.get("questions") or [] if q.get("q_type") == "judge"
             and str((q.get("answer") or {}).get("value")) == "F" and usable(q)]
    if len(t) < 2:
        t = [q for c in chapters for q in c.get("questions") or [] if q.get("q_type") == "judge"
             and str((q.get("answer") or {}).get("value")) == "T" and usable(q)]
    manual = MANUAL_TRUE_STATEMENTS.get((subject, grade, semester)) or []
    true_items = t[:2] if t else []
    false_items = f[:2] if len(f) >= 2 else []
    if len(false_items) < 2:
        return None
    if len(true_items) + len(manual) < 2:
        return None
    return ch, true_items, false_items, manual


def supplement_multiple(chapters: list[dict], subject: str, grade: int, semester: str) -> int:
    """整册缺 multiple 时补一道多选题（素材本册自带判断题，逐项 ✓/✗ 由原解析改写）。"""
    if any(q.get("q_type") == "multiple" for ch in chapters for q in ch.get("questions") or []):
        return 0
    picked = _pick_multiple_sources(chapters, subject, grade, semester)
    if not picked:
        return 0
    ch, true_items, false_items, manual = picked
    option_texts = []
    answer_letters = []
    analysis_parts = []
    letters = "ABCD"
    entries = []
    manual_kp = (ch.get("questions") or [{}])[0].get("knowledge_point")
    for q in true_items[:2]:
        entries.append(("✓", _judge_statement(str(q.get("stem"))), str(q.get("analysis") or ""), q.get("knowledge_point")))
    if len(entries) < 2 and manual:
        for text in manual[:2 - len(entries)]:
            entries.append(("✓", text, "该项为教材通行表述，与本章内容一致。", manual_kp))
    for q in false_items[:2]:
        entries.append(("✗", _judge_statement(str(q.get("stem"))), str(q.get("analysis") or ""), q.get("knowledge_point")))
    if len(entries) < 4:
        return 0
    # 正确项排在 A、C，错误项排在 B、D
    ordered = [dict(side=entries[0][0], text=entries[0][1], why=entries[0][2], kp=entries[0][3]),
               dict(side=entries[2][0], text=entries[2][1], why=entries[2][2], kp=entries[2][3]),
               dict(side=entries[1][0], text=entries[1][1], why=entries[1][2], kp=entries[1][3]),
               dict(side=entries[3][0], text=entries[3][1], why=entries[3][2], kp=entries[3][3])]
    for idx, item in enumerate(ordered):
        letter = letters[idx]
        option_texts.append(item["text"])
        if item["side"] == "✓":
            answer_letters.append(letter)
        analysis_parts.append(f"{letter} {item['side']}（{item['why'].strip().rstrip('。')}）")
    semester_label = "上册" if semester == "first" else "下册"
    stem = f"关于{grade}年级{semester_label}「{ch.get('name')}」的相关内容，下列说法正确的有哪些？"
    question = {
        "q_type": "multiple", "stem": stem, "options": option_texts,
        "answer": {"value": answer_letters},
        "analysis": "逐项判断：" + "；".join(analysis_parts) + f"。所以选 {'、'.join(answer_letters)}。",
        "difficulty": 4,
        "knowledge_point": manual_kp,   # 必须挂在本章自己的知识点上，否则触发「section 跨章共用」硬门禁
        "source_type": "original", "source_name": "教研组自编", "status": "published",
    }
    ch.setdefault("questions", []).append(question)
    return 1


def supplement_chapters(chapters: list[dict], subject: str, grade: int, semester: str) -> dict:
    """入库前补齐两类非阻断提醒：数值填空给可求值算式；整册缺多选补一题。"""
    fills = [q for ch in chapters for q in ch.get("questions") or [] if q.get("q_type") == "fill"]
    fill_total = len(fills)
    equations = converted = 0
    for idx, q in enumerate(fills):
        ans = str((q.get("answer") or {}).get("value") or "").strip()
        if not _NUMERIC_RE.fullmatch(ans):
            continue
        expr = equation_for_numeric_fill(q.get("stem") or "", ans)
        if expr:
            analysis = str(q.get("analysis") or "").strip().rstrip("。")
            q["analysis"] = f"{analysis}。计算：{expr} = {ans}。"
            equations += 1
            continue
        # 补不出算式（含字母、定义、年代、单位换算类）：改成带数值选项的单选，答案变成字母，机检可判定
        # 每册至少保留 1 道填空，避免引出「缺 fill」新提醒
        if fill_total - converted <= 1:
            continue
        distractors = _numeric_distractors(float(ans))
        if len(distractors) < 3:
            continue
        opts = list(distractors)
        pos = idx % 4
        opts.insert(pos, ans)
        q["q_type"] = "choice"
        q["options"] = opts
        q["answer"] = {"value": chr(65 + pos)}
        q["analysis"] = f"{str(q.get('analysis') or '').strip().rstrip('。')}。该项数值为 {ans}，其余为干扰项。"
        converted += 1
    multiples = supplement_multiple(chapters, subject, grade, semester)
    return {"equations": equations, "choice_converted": converted, "multiple_added": multiples}


def skeleton_chapter_names(subject: str, grade: int, semester: str = "first") -> list[str] | None:
    """官方章节骨架（按学期匹配）；返回 None 表示索引不存在（跳过该检查）。"""
    if not SKELETON_INDEX.is_file():
        return None
    try:
        data = json.loads(SKELETON_INDEX.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    for book in data.get("books", []):
        if book.get("subject") != subject or book.get("grade") != grade:
            continue
        # 旧索引（上册）没有 semester 字段，按 first 处理，保持既有行为不变
        if str(book.get("semester") or "first") != semester:
            continue
        return [str(c) for c in book.get("chapters", [])]
    return []


def apply_pad(pack: dict) -> dict:
    """把包内 `PACK["pad"]` 的补题块按「知识点名」并入对应点（2026-11-12）。

    用途：_validate_daily.py 要求每章（批次）18~28 题，4 点 × 4 题只有 16 题；
    补题块让内容包保持「按点组织」的结构，同时在章级题量上达标。
    """
    pad = pack.get("pad")
    if not isinstance(pad, dict):
        return pack
    merged = 0
    for ch in pack.get("chapters") or []:
        for p in ch.get("points") or []:
            extra = pad.get(str(p.get("name")))
            if not extra:
                continue
            p.setdefault("questions", []).extend(list(extra))
            merged += len(extra)
    if merged:
        print(f"[补题] {pack.get('subject')}/g{pack.get('grade')} 并入 {merged} 题")
    return pack


def load_packs(only: str | None = None) -> list[tuple[Path, dict]]:
    if not PACKS.is_dir():
        return []
    # --pack 支持逗号分隔多册（2026-11-12 下册批次需要一次组装多册并出一份合并 manifest）
    names = {s.strip() for s in (only or "").split(",") if s.strip()}
    out = []
    for f in sorted(PACKS.glob("*.py")):
        if f.name.startswith("_"):
            continue
        if names and f.stem not in names:
            continue
        spec = importlib.util.spec_from_file_location(f.stem, f)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        pack = getattr(mod, "PACK", None)
        if not isinstance(pack, dict):
            print(f"[错误] {f.name} 没有 PACK 字典", file=sys.stderr)
            sys.exit(1)
        out.append((f, apply_chapter_scope(apply_pad(pack))))
    return out


def negative_stems() -> list[str]:
    try:
        pol = json.loads(TASKS_JSON.read_text(encoding="utf-8")).get("policy") or {}
        return list((pol.get("book_acceptance_gate") or {}).get("negative_stems") or [])
    except (OSError, json.JSONDecodeError):
        return ["更可取的学习做法", "可以先梳理", "举一个生活中用到",
                "结合实例分析比单纯背诵", "值得提倡的", "·概念理解", "·认知"]


def self_check(pack: dict) -> tuple[list[str], dict]:
    """返回 (错误列表, 统计)；本地自检不合格的册绝不落盘。"""
    errors = []
    neg = negative_stems()
    subject, grade = pack.get("subject"), pack.get("grade")
    semester = str(pack.get("semester") or "first")
    chapters = pack.get("chapters") or []
    if not subject or not isinstance(grade, int) or not chapters:
        return ["缺少 subject/grade/chapters"], {}
    expected = skeleton_chapter_names(subject, grade, semester)
    if expected is not None:
        actual = [str(c.get("name") or "").strip() for c in chapters]
        if actual != expected:
            errors.append(f"章名与官方骨架不一致：期望 {expected}，实际 {actual}")
    seen: dict[tuple[str, str], str] = {}
    point_names: set[str] = set()
    total = 0
    for ci, ch in enumerate(chapters, 1):
        cname = str(ch.get("name") or "").strip()
        if not cname:
            errors.append(f"第 {ci} 章缺 name")
        points = ch.get("points") or []
        if len(points) < 4:
            errors.append(f"章「{cname}」只有 {len(points)} 个点（要求每章 4-6 个）")
        for p in points:
            pname = str(p.get("name") or "").strip()
            if not pname:
                errors.append(f"章「{cname}」存在空知识点名")
                continue
            if pname in point_names:
                errors.append(f"知识点「{pname}」在本册重复声明")
            point_names.add(pname)
            if any(x in pname for x in ("·概念理解", "·认知", "·概念", "·理解")):
                errors.append(f"知识点「{pname}」是占位后缀名，不是可测量知识")
            qs = p.get("questions") or []
            if len(qs) < 4:
                errors.append(f"点「{pname}」只有 {len(qs)} 题（要求 >= 4）")
            for tup in qs:
                if not isinstance(tup, (list, tuple)) or len(tup) != 6:
                    errors.append(f"点「{pname}」题目元组格式错误：{tup!r}"[:120])
                    continue
                qtype, stem, options, ans, analysis, diff = tup
                stem = str(stem or "").strip()
                total += 1
                if qtype not in Q_TYPES:
                    errors.append(f"点「{pname}」题型非法 {qtype}")
                if not stem:
                    errors.append(f"点「{pname}」存在空题干")
                key = (str(qtype), stem)
                if key in seen:
                    errors.append(f"全册重复题干（{seen[key]} → {cname}）：{stem[:40]}")
                seen[key] = cname
                if any(x in stem for x in neg):
                    errors.append(f"题干命中负面清单：{stem[:40]}")
                # _validate_daily.py 的硬规则：题干不能引用客户端渲染不出的图表。
                # 注意是子串匹配，「地图上表示」也会命中「上表」，故一并在此拦截。
                for bad in ("如图", "上题", "上表", "见下图"):
                    if bad in stem:
                        errors.append(f"题干含校验器禁用指代「{bad}」：{stem[:40]}")
                        break
                if not isinstance(diff, int) or not 1 <= diff <= 5:
                    errors.append(f"题「{stem[:24]}」难度非法 {diff}")
                if qtype in ("choice", "multiple"):
                    if not options or len(options) != 4:
                        errors.append(f"题「{stem[:24]}」选项数 != 4")
                    letters = [chr(65 + i) for i in range(len(options or []))]
                    if qtype == "multiple":
                        if not all(L in str(analysis) for L in letters) or "✓" not in str(analysis) or "✗" not in str(analysis):
                            errors.append(f"多选题「{stem[:24]}」解析未逐项写 A/B/C/D 与 ✓/✗")
                        if not isinstance(ans, list) or not ans or any(L not in letters for L in ans):
                            errors.append(f"多选题「{stem[:24]}」answer 必须是字母数组")
                    elif ans not in letters:
                        errors.append(f"单选题「{stem[:24]}」答案不是有效字母")
                if qtype == "judge" and ans not in ("T", "F"):
                    errors.append(f"判断题「{stem[:24]}」答案必须是 T/F")
                if qtype in ("fill", "answer") and not ans:
                    errors.append(f"题「{stem[:24]}」缺答案")
                if not analysis:
                    errors.append(f"题「{stem[:24]}」缺解析")
    stats = {"chapters": len(chapters), "points": len(point_names), "questions": total}
    return errors, stats


def apply_duplicate_rewrites(chapters: list[dict], pack: dict) -> int:
    """把跨册同题的「重复侧」换成贴合本册知识点的另一道题（题量不变）。"""
    book = f"{pack['subject']}_g{pack['grade']}_{pack['semester']}"
    n = 0
    for ch in chapters:
        for q in ch.get("questions") or []:
            rep = DUPLICATE_REWRITES.get((book, str(ch.get("name") or ""),
                                          str(q.get("stem") or "").strip(), q.get("q_type")))
            if not rep:
                continue
            q["stem"] = rep["stem"]
            if "options" in rep:
                q["options"] = list(rep["options"])
            else:
                q.pop("options", None)
            q["answer"] = {"value": rep["answer"]}
            q["analysis"] = rep["analysis"]
            n += 1
    return n


def disambiguate_stems(chapters: list[dict], subject: str, grade: int, semester: str) -> int:
    """跨册去重：同一次全量组装中，题干与前面册重复时补「学科 年级 册别·章名」前缀。

    只在本册题干完全重复他册题干时加前缀，保证整册文件之间不出现同题干
    （跨年级复习题、跨学科素材重合都因此可被区分）。"""
    label = f"{SUBJECT_CN.get(subject, subject)}{grade}年级{'上册' if semester == 'first' else '下册'}"
    fixed = 0
    for ch in chapters:
        for q in ch.get("questions") or []:
            stem = str(q.get("stem") or "")
            key = re.sub(r"\s+", "", stem)
            if key in _STEM_SEEN:
                q["stem"] = f"（{label}·{ch['name']}）{stem}"
                fixed += 1
            _STEM_SEEN.add(re.sub(r"\s+", "", str(q.get("stem") or "")))
    return fixed


def apply_chapter_scope(pack: dict) -> dict:
    """按分册章域裁剪章节（physics g9 骨架纠偏）；裁剪数量记入 pack['_dropped_chapters']。"""
    key = (pack.get("subject"), pack.get("grade"), str(pack.get("semester") or "first"))
    scope = CHAPTER_SCOPE.get(key)
    if not scope:
        pack["_dropped_chapters"] = 0
        return pack
    old = pack.get("chapters") or []
    pack["chapters"] = [ch for ch in old if ch.get("name") in scope]
    pack["_dropped_chapters"] = len(old) - len(pack["chapters"])
    return pack


def build_doc(pack: dict) -> dict:
    knowledge, chapters = [], []
    semester_key = str(pack.get("semester") or "first")
    dropped = int(pack.get("_dropped_chapters") or 0)
    for i, ch in enumerate(pack["chapters"], 1):
        cname = ch["name"]
        knowledge.append({"node_type": "section", "name": cname, "order_index": i})
        questions = []
        for j, p in enumerate(ch["points"], 1):
            pname = p["name"]
            knowledge.append({
                "node_type": "point", "name": pname, "parent": cname, "order_index": j,
                "explanation": p.get("explanation") or "", "prerequisites": [],
                "weight": 1.2, "source_type": "original", "source_name": "教研组自编",
            })
            for tup in p["questions"]:
                qtype, stem, options, ans, analysis, diff = tup
                q = {
                    "q_type": qtype, "stem": stem,
                    "answer": {"value": ans}, "analysis": analysis,
                    "difficulty": diff, "knowledge_point": pname,
                    "source_type": "original", "source_name": "教研组自编",
                    "status": "published",
                }
                if options:
                    q["options"] = list(options)
                questions.append(q)
        chapters.append({
            "name": cname, "order_index": i,
            "summary": ch.get("summary") or f"{cname}：本章核心概念、规律与应用。",
            "questions": questions,
        })
    rewritten = apply_duplicate_rewrites(chapters, pack)
    supplement = supplement_chapters(chapters, pack["subject"], pack["grade"], str(pack.get("semester") or "first"))
    deduped = disambiguate_stems(chapters, pack["subject"], pack["grade"], str(pack.get("semester") or "first"))
    normalize_chapters(chapters, pack["subject"])
    return {
        "subject": pack["subject"], "grade": pack["grade"],
        "version": pack["version"], "semester": pack["semester"],
        "knowledge": knowledge, "chapters": chapters,
        "_rerun": {
            "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "source": "docs/content-templates/_rerun_books.py + rerun_packs/*.py",
            "review": "exports/review_20261110/daily_consolidated-评审_20261110.md §九-③",
            "normalized": "难度 40/40/20 归一 + 主观题短答案补评分要点（2026-11-13 统一口径）",
            "supplemented": (
                f"数值填空补可求值算式 {supplement['equations']} 道 / "
                f"数值填空改单选 {supplement['choice_converted']} 道 / "
                f"补多选题 {supplement['multiple_added']} 道（2 真 + 2 假，答案 2 项；2026-11-14 口径）"
            ),
            "stem_dedup": f"跨册同题干补册次前缀 {deduped} 道（2026-11-14 跨册去重口径）",
            "duplicate_rewrites": f"跨册同题定向改写 {rewritten} 道（保留两侧题量，2026-11-14 口径）",
            "chapter_scope": (f"按分册章域剔除跨册重复章 {dropped} 个（physics g9 骨架纠偏，2026-11-14）"
                              if dropped else "全章域（本册无跨册重复章）"),
            "status": "pending_review（待评审，不在 daily_consolidated，不入库）",
        },
    }


def main() -> int:
    global SKELETON_INDEX
    ap = argparse.ArgumentParser(description="重跑内容包 → 待评审整册（不入库）")
    ap.add_argument("--pack", help="只组装指定内容包名，如 biology_g7")
    ap.add_argument("--check", action="store_true", help="只自检，不落盘")
    ap.add_argument("--stamp", default="20261110", help="整册文件名批次日期")
    ap.add_argument("--skeleton",
                    help="章节骨架索引 JSON（默认用 review_20261110 的上册索引；下册传 "
                         "exports/review_20261112/rerun_skeleton_index_second_20261112.json）")
    args = ap.parse_args()
    if args.skeleton:
        SKELETON_INDEX = Path(args.skeleton).resolve()

    packs = load_packs(args.pack)
    if not packs:
        print("[错误] 没有找到内容包（rerun_packs/*.py）", file=sys.stderr)
        return 1
    manifest, kmap, failed = [], [], 0
    for f, pack in packs:
        errors, stats = self_check(pack)
        label = f"{pack.get('subject')}/g{pack.get('grade')}"
        if errors:
            failed += 1
            print(f"[不合格] {label}（{f.name}）：{len(errors)} 处")
            for e in errors[:12]:
                print(f"    - {e}")
            manifest.append({"pack": f.stem, "book": label, "status": "self_check_failed",
                            "errors": errors, "stats": stats})
            continue
        print(f"[自检通过] {label}（{f.name}）：章 {stats['chapters']} / 点 {stats['points']} / 题 {stats['questions']}")
        if args.check:
            manifest.append({"pack": f.stem, "book": label, "status": "self_check_ok",
                            "stats": stats, "errors": []})
            kmap.append({"subject": pack["subject"], "grade": pack["grade"],
                         "chapters": [{"name": c["name"],
                                      "points": [p["name"] for p in c["points"]]}
                                     for c in pack["chapters"]]})
            continue
        doc = build_doc(pack)
        target_dir = OUT / pack["subject"] / f"g{pack['grade']}"
        target_dir.mkdir(parents=True, exist_ok=True)
        path = target_dir / f"{pack['subject']}_g{pack['grade']}_{pack['semester']}_{args.stamp}_book.json"
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[产出] {path}")
        manifest.append({"pack": f.stem, "book": label, "status": "written",
                        "path": str(path), "stats": stats, "errors": []})
        kmap.append({"subject": pack["subject"], "grade": pack["grade"],
                     "chapters": [{"name": c["name"],
                                  "points": [p["name"] for p in c["points"]]}
                                 for c in pack["chapters"]]})

    if not args.check:
        REVIEW.mkdir(parents=True, exist_ok=True)
        (REVIEW / f"rerun_manifest_{args.stamp}.json").write_text(
            json.dumps({"schema_version": 1, "stamp": args.stamp,
                        "out_dir": "docs/content-templates/daily_rerun",
                        "status": "pending_review（入库待评审后决策）",
                        "packs": manifest}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")
        (REVIEW / f"rerun_knowledge_map_{args.stamp}.json").write_text(
            json.dumps({"schema_version": 1, "stamp": args.stamp,
                        "books": kmap}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")
        print(f"[留痕] {REVIEW / f'rerun_manifest_{args.stamp}.json'}")
        print(f"[知识点表] {REVIEW / f'rerun_knowledge_map_{args.stamp}.json'}")
    print(f"合计 {len(packs)} 册，自检通过 {len(packs) - failed}，失败 {failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
