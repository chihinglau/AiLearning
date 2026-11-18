"""题目质量门禁：答案泄漏到题干的结构化判定（2026-11-18 · CR-008）。

背景：`exports/answer_leak_review.csv` 里 99 条「需复核」全部是填空/解答题，
答案原样出现在题干里，学生不学也能抄。逐条修是一次性的，本模块提供可复用的
判定规则，让「入库」和「全库巡检」共用同一套口径，把问题挡在未来。

分级：
  BLOCK  硬泄漏（答案字紧贴填空位，或整段原词落在题干叙述里）→ 入库直接拒绝
  WARN   疑似（单字构词包含、答案落在候选括号内、阅读理解取原文、排序题元素）→ 只提示
  None   无问题

刻意排除的「伪泄漏」（两轮全库扫描把 583 条压到 106 条时逐类踩出来的）：
  1. 选择题 / 多选题 / 判断题：answer 存的是选项键（A/B/C）或 T/F，不是作答文本；
  2. 单字符 ASCII 答案：字母辨认题（b 和 d 中…）、拼音声母题，答案必须在题干出现；
  3. 阅读理解：答案取自短文原文，属题型必然；
  4. 算式 / 条件题：`五分之三减十分之三的结果是（ ）`，操作数必须写在题面；
  5. 子串假命中：`is ⊂ This`、`80 ⊂ 800`、`er ⊂ Father`，靠词边界匹配剔除；
  6. 排序 / 组词 / 偏旁题：`按顺序排：①睡觉②玩③回家`、`「草」可以组词`，题面必须给素材。
"""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

BLOCK = "block"
WARN = "warn"

# 答案本身就是「作答文本」的题型；其余题型答案是选项键或不适用
TEXT_ANSWER_TYPES = ("fill", "answer", "listening", "calc")

# 填空位：连续下划线，或空括号
_BLANK_RE = re.compile(r"[_＿]{2,}|[（(]\s*[)）]")
# 括号块（用于识别「已给候选词」的合法题型）
_PAREN_RE = re.compile(r"[（(]([^）)]*)[)）]")
# 候选提示词：出现任一即认为括号在给选项，而非留空
_CANDIDATE_HINT = ("/", "或", "选", "填", "二选一")
# 算式/条件题特征：题干含算式符号，答案几乎必然出现在题面
_ARITHMETIC_RE = re.compile(r"[0-9一二三四五六七八九十]+\s*(?:[/÷×+\-−减乘除加]|分之)")
# 阅读理解特征：答案取自短文，属题型必然
_READING_RE = re.compile(r"阅读短文|读短文|读一读|根据短文|根据课文|阅读课文|短文|文中")
# 题面必须给素材的题型：排序、组词、偏旁
_EXEMPT_RE = re.compile(r"排列|从大到小|从小到大|顺序是|组词|加偏旁|换偏旁|减偏旁|偏旁|音节")

_CN_RE = re.compile(r"[\u4e00-\u9fff]")


def answer_values(answer: Any) -> list[str]:
    """把 answer 归一化成候选答案文本列表。

    支持三种形态：`{"value": "x"}`（模板）、纯字符串、`["x", "y"]`。
    """
    if answer is None:
        return []
    if isinstance(answer, Mapping):
        raw = answer.get("value")
    else:
        raw = answer
    items = raw if isinstance(raw, Sequence) and not isinstance(raw, str) else [raw]
    out: list[str] = []
    for item in items:
        text = str(item or "").strip()
        if text:
            out.append(text)
    return out


def _positions(text: str, candidate: str) -> list[int]:
    """答案在题干中的有效出现位置（带词边界过滤，剔除子串假命中）。"""
    found: list[int] = []
    for match in re.finditer(re.escape(candidate), text):
        prev = text[match.start() - 1] if match.start() > 0 else ""
        nxt = text[match.end()] if match.end() < len(text) else ""
        # 英文子串：is ⊂ This、er ⊂ Father
        if candidate.isascii() and (
            (prev and prev.isalnum()) or (nxt and nxt.isalnum())
        ):
            continue
        # 数字子串：80 ⊂ 800
        if candidate[:1].isdigit() and (
            (prev and prev.isdigit()) or (nxt and nxt.isdigit())
        ):
            continue
        found.append(match.start())
    return found


def _inside_candidate_paren(stem: str, answer: str) -> bool:
    for block in _PAREN_RE.findall(stem):
        if answer in block and any(hint in block for hint in _CANDIDATE_HINT):
            return True
    return False


def _next_to_blank(stem: str, answer: str) -> bool:
    """答案是否紧贴填空位（前 3 字或后 3 字内出现填空标记）。"""
    for pos in _positions(stem, answer):
        left = stem[max(0, pos - 3): pos]
        right = stem[pos + len(answer): pos + len(answer) + 3]
        if _BLANK_RE.search(left) or _BLANK_RE.search(right):
            return True
    return False


def _answer_in_word(stem: str, answer: str) -> bool:
    """单字答案是否只是题干里某个更长词的组成部分（雪花含雪、周长含周）。"""
    if len(answer) != 1 or not _CN_RE.match(answer):
        return False
    for pos in _positions(stem, answer):
        prev = stem[pos - 1] if pos > 0 else ""
        nxt = stem[pos + 1] if pos + 1 < len(stem) else ""
        if (prev and _CN_RE.match(prev)) or (nxt and _CN_RE.match(nxt)):
            return True
    return False


def is_arithmetic_stem(stem: str) -> bool:
    """算式/条件题识别：这类题干天然带答案所需的操作数，不算泄漏。"""
    return bool(_ARITHMETIC_RE.search(stem or ""))


def is_reading_comprehension(stem: str) -> bool:
    """阅读理解识别：含短文且篇幅较长，答案本应取自原文。"""
    text = stem or ""
    return len(text) >= 60 and bool(_READING_RE.search(text))


def check_answer_leak(
    stem: str, answer: Any, q_type: str | None = None
) -> tuple[str, str] | None:
    """判定一道题是否存在答案泄漏。

    返回 `(level, reason)`；无问题时返回 `None`。`q_type` 不传时按「文本答案」处理。
    """
    text = (stem or "").strip()
    if not text:
        return None
    if q_type is not None and q_type in ("choice", "multiple", "judge"):
        return None  # 答案存的是选项键 / T、F，不是作答文本
    if _EXEMPT_RE.search(text):
        return None  # 排序 / 组词 / 偏旁 / 音节题，题面必须给出素材
    candidates = answer_values(answer)
    if not candidates:
        return None
    for candidate in candidates:
        if len(candidate) <= 1 and candidate.isascii():
            continue  # 字母辨认 / 拼音声母 / 数字题
        positions = _positions(text, candidate)
        if not positions:
            continue
        if is_reading_comprehension(text):
            return WARN, f"答案「{candidate}」取自短文原文（阅读理解题型必然）"
        if _inside_candidate_paren(text, candidate):
            return WARN, f"答案「{candidate}」落在候选括号内（属提示题型，非缺陷）"
        if _next_to_blank(text, candidate):
            return BLOCK, f"答案「{candidate}」紧贴填空位，学生无需思考即可照抄"
        if len(candidate) >= 2:
            return BLOCK, f"答案「{candidate}」整段出现在题干叙述中"
        if _answer_in_word(text, candidate):
            return WARN, f"答案「{candidate}」是题干其他词的组成部分（构词包含）"
        return BLOCK, f"答案「{candidate}」原样出现在题干中"
    return None


def summary_line(level: str, reason: str) -> str:
    prefix = {"block": "BLOCK", "warn": "WARN"}.get(level, "INFO")
    return f"[{prefix}] {reason}"
