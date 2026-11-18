"""读题文本预处理规则（设计 D-01 §3.9.5 / §3.9.12）。

与客户端 `app/lib/core/speech/question_speech.dart` 保持同一份规则表：
文案、顺序、边界必须逐条一致，任一侧变更都要同步 `RULES_VERSION`
（缓存键组成部分）并同步 `app/test/question_speech_test.dart` 与本模块单测。
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping, Sequence
from typing import Any

# 读法规则版本：参与音频缓存键（设计 §3.9.6）。与客户端 `SpeechRules.version` 同步。
RULES_VERSION = 1

# 首期生成/分发范围（设计 §3.9.7）：语文/数学只给低年级读题用。
ALLOWED_GRADES: tuple[int, ...] = (1, 2, 3)
ALLOWED_SUBJECTS: tuple[str, ...] = ("chinese", "math", "english")

# 英语读题是全学段能力（1–9 年级）：低年级靠读题理解题意，高年级靠听读记发音。
# 语文/数学维持 1–3 年级，避免长题干合成成本与播放时长失控。
READING_GRADES_BY_SUBJECT: dict[str, tuple[int, ...]] = {
    "english": (1, 2, 3, 4, 5, 6, 7, 8, 9),
}


def reading_grades(subject: str) -> tuple[int, ...]:
    """某学科的读题音频覆盖年级；未登记的学科回落到 `ALLOWED_GRADES`。"""
    return READING_GRADES_BY_SUBJECT.get(subject, ALLOWED_GRADES)


def reading_allowed(subject: str, grade: int) -> bool:
    """服务端是否提供该题读题音频（学科 × 年级双条件）。"""
    return subject in ALLOWED_SUBJECTS and grade in reading_grades(subject)

# 音色与学科绑定：英语用英文模型，语文/数学用中文模型。
VOICE_BY_SUBJECT: dict[str, str] = {
    "chinese": "vits-piper-zh_CN-huayan-medium",
    "math": "vits-piper-zh_CN-huayan-medium",
    "english": "vits-piper-en_US-lessac-medium",
}

_DIGITS = ["零", "一", "二", "三", "四", "五", "六", "七", "八", "九"]

_UNIT_LABELS = {
    "km": "千米",
    "cm": "厘米",
    "mm": "毫米",
    "kg": "千克",
    "ml": "毫升",
    "m": "米",
    "g": "克",
    "L": "升",
}

_SUPERSCRIPT_DIGITS = {
    "⁰": "0",
    "¹": "1",
    "²": "2",
    "³": "3",
    "⁴": "4",
    "⁵": "5",
    "⁶": "6",
    "⁷": "7",
    "⁸": "8",
    "⁹": "9",
}

_SUBSCRIPT_DIGITS = {
    "₀": "0",
    "₁": "1",
    "₂": "2",
    "₃": "3",
    "₄": "4",
    "₅": "5",
    "₆": "6",
    "₇": "7",
    "₈": "8",
    "₉": "9",
}

_BLANK_RE = re.compile(r"[_＿]{2,}")
_FRACTION_RE = re.compile(r"(\d+)\s*/\s*(\d+)")
_UNIT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(km|cm|mm|kg|ml|m|g|L)")
_SUPERSCRIPT_RE = re.compile(r"([0-9A-Za-z\)])([⁰¹²³⁴⁵⁶⁷⁸⁹]+)")
_SUBSCRIPT_RE = re.compile(r"([0-9A-Za-z\)])([₀₁₂₃₄₅₆₇₈₉]+)")
_OPTION_PREFIX_RE = re.compile(r"(^|\n)[ \t]*([A-Za-z])[.、．]")
_SPACE_RE = re.compile(r"\s+")
_OPTION_SCRIPT_PREFIX_RE = re.compile(r"^选项\s*[A-Za-z]\s*[，,]?\s*")


def normalize(text: str) -> str:
    """按设计 §3.9.12 的顺序清洗。

    顺序：填空线 → 分数 → 单位 → 幂/上下标 → 运算符 → 选项 → 归一化。
    """
    if not text:
        return text
    out = _BLANK_RE.sub("空格", text)
    out = _FRACTION_RE.sub(
        lambda m: f"{to_chinese_number(int(m.group(2)))}分之"
        f"{to_chinese_number(int(m.group(1)))}",
        out,
    )
    out = _UNIT_RE.sub(
        lambda m: f"{_spoken_number(m.group(1), liang=True)}{_UNIT_LABELS[m.group(2)]}",
        out,
    )

    def _superscript(match: re.Match[str]) -> str:
        buffer = [match.group(1)]
        for mark in match.group(2):
            if mark == "²":
                buffer.append(" 的平方")
            elif mark == "³":
                buffer.append(" 的立方")
            else:
                buffer.append(f" 的 {_SUPERSCRIPT_DIGITS[mark]} 次方")
        return "".join(buffer)

    out = _SUPERSCRIPT_RE.sub(_superscript, out)

    def _subscript(match: re.Match[str]) -> str:
        digits = "".join(_SUBSCRIPT_DIGITS[mark] for mark in match.group(2))
        return f"{match.group(1)} 下标 {digits}"

    out = _SUBSCRIPT_RE.sub(_subscript, out)
    out = (
        out.replace("÷", "除以")
        .replace("×", "乘")
        .replace("±", "正负")
        .replace("≥", "大于等于")
        .replace("≤", "小于等于")
        .replace("=", "等于")
    )
    out = _OPTION_PREFIX_RE.sub(
        lambda m: f"{m.group(1)}选项 {m.group(2)}，", out
    )
    return _SPACE_RE.sub(" ", out).strip()


def option_script(key: str, text: str) -> str:
    """单个选项的朗读文本：「选项 A，……」。已带字母前缀时先剥离，避免重复。"""
    cleaned = _OPTION_SCRIPT_PREFIX_RE.sub("", normalize(text), count=1)
    return f"选项 {key}，{cleaned}"


def question_script(
    stem: str, options: Sequence[Mapping[str, Any]] | None = None
) -> str:
    """整题朗读文本：题干 + 逐项选项，句间断开。"""
    parts = [normalize(stem)]
    for option in options or ():
        text = str(option.get("text") or "")
        if not text.strip():
            continue
        parts.append(option_script(str(option.get("key") or ""), text))
    return "。".join(part for part in parts if part)


def text_for_question(question: Any) -> str:
    """从 Question 模型生成朗读文本（题干取 `content.stem`）。"""
    content = question.content or {}
    stem = str(content.get("stem") or "")
    return question_script(stem, question.options or [])


def to_chinese_number(value: int) -> str:
    """阿拉伯数字转中文读法，覆盖 0–999；超出范围原样返回（与客户端一致）。"""
    if value < 0 or value > 999:
        return str(value)
    if value < 10:
        return _DIGITS[value]
    if value < 20:
        rest = value % 10
        return "十" if rest == 0 else f"十{_DIGITS[rest]}"
    if value < 100:
        tens, rest = divmod(value, 10)
        if rest == 0:
            return f"{_DIGITS[tens]}十"
        return f"{_DIGITS[tens]}十{_DIGITS[rest]}"
    hundreds, rest = divmod(value, 100)
    if rest == 0:
        return f"{_DIGITS[hundreds]}百"
    if rest < 10:
        return f"{_DIGITS[hundreds]}百零{_DIGITS[rest]}"
    return f"{_DIGITS[hundreds]}百{to_chinese_number(rest)}"


def _spoken_number(raw: str, *, liang: bool = False) -> str:
    if "." not in raw:
        value = int(raw)
        if liang and value == 2:
            return "两"
        return to_chinese_number(value)
    whole, _, decimals = raw.partition(".")
    whole_text = "零" if int(whole) == 0 else to_chinese_number(int(whole))
    decimal_text = "".join(_DIGITS[int(digit)] for digit in decimals)
    return f"{whole_text}点{decimal_text}"


def voice_for_subject(subject: str) -> str:
    return VOICE_BY_SUBJECT.get(subject, VOICE_BY_SUBJECT["chinese"])


# 英语题里有大量「中文题干 + 英文选项」的混排题（如「「妈妈」的英文是（ ）」），
# 整段用英文模型合成会把中文读空。按语种切段、各自用对应音色合成后拼接。
_CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")
_SPEECH_CHAR_RE = re.compile(r"[A-Za-z0-9]")
# 选项前缀由规则生成（「选项 A，」）。英语题的选项本身是英文，中文前缀会把整段
# 切成「中文前缀 + 英文内容」两截、四个选项反复换音色；合成前把前缀本地化成
# 「Option A, 」，题干与选项各自成为纯净单语种段。
_EN_OPTION_PREFIX_RE = re.compile(r"选项\s*([A-Za-z0-9])\s*，\s*")
# 填空题占位 `____` 被规则读成「空格」；英语题里读 blank 才自然。
_EN_BLANK_RE = re.compile(r"空格")


def _localize_option_prefix(text: str) -> str:
    return _EN_OPTION_PREFIX_RE.sub(lambda m: f"Option {m.group(1)}, ", text)


def _localize_english_markers(text: str) -> str:
    return _EN_BLANK_RE.sub("blank", text)


def speech_segments(text: str, subject: str) -> list[tuple[str, str]]:
    """朗读文本按语种切段，返回 `[(音色, 文本段), ...]`。

    非英语学科只有一个音色，原样整段返回；英语先本地化选项前缀，再按中英文字符
    边界切段，纯标点（无字母数字）的碎片并入相邻中文段，避免合成出空音频。
    """
    default_voice = voice_for_subject(subject)
    if subject != "english" or not text.strip():
        return [(default_voice, text)]

    text = _localize_english_markers(_localize_option_prefix(text))
    zh_voice = VOICE_BY_SUBJECT["chinese"]
    en_voice = VOICE_BY_SUBJECT["english"]

    raw: list[list[str]] = []
    buf: list[str] = []
    lang = ""
    for ch in text:
        cur = "zh" if _CJK_RE.match(ch) else "en"
        if buf and cur != lang:
            raw.append([lang, "".join(buf)])
            buf = []
        buf.append(ch)
        lang = cur
    if buf:
        raw.append([lang, "".join(buf)])

    merged: list[list[str]] = []
    for cur_lang, seg in raw:
        # 不含字母数字的英文碎片（标点、括号、空格）跟随前一段；开头则等后一段。
        if cur_lang == "en" and not _SPEECH_CHAR_RE.search(seg):
            if merged:
                merged[-1][1] += seg
                continue
            merged.append(["zh", seg])
            continue
        if merged and merged[-1][0] == cur_lang:
            merged[-1][1] += seg
            continue
        merged.append([cur_lang, seg])

    segments: list[tuple[str, str]] = []
    for cur_lang, seg in merged:
        stripped = seg.strip()
        if not stripped:
            continue
        voice = zh_voice if cur_lang == "zh" else en_voice
        if segments and segments[-1][0] == voice:
            segments[-1] = (voice, f"{segments[-1][1]} {stripped}")
            continue
        segments.append((voice, stripped))
    return segments or [(default_voice, text)]


def cache_key_for_segments(segments: Sequence[tuple[str, str]], speed: float) -> str:
    """分语种缓存的键：单段退化为原 `cache_key`（存量单语种资产不失效）。"""
    if len(segments) <= 1:
        voice, text = segments[0] if segments else (VOICE_BY_SUBJECT["chinese"], "")
        return cache_key(text, voice, speed)
    payload = f"{RULES_VERSION}|mix|{speed:.2f}|" + "".join(
        f"{voice}\u0001{text}\u0002" for voice, text in segments
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def question_segments(question: Any, speed: float) -> tuple[list[tuple[str, str]], str]:
    """整题朗读文本的分语种分段与缓存键。"""
    text = text_for_question(question)
    segments = speech_segments(text, str(question.subject or ""))
    return segments, cache_key_for_segments(segments, speed)



def cache_key(text: str, voice: str, speed: float) -> str:
    """缓存键：`sha256(清洗后文本 + 音色 + 语速 + 规则版本)`（设计 §3.9.6）。"""
    payload = f"{RULES_VERSION}|{voice}|{speed:.2f}|{text}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def audio_rel_path(key: str) -> str:
    """`audio/{hash前2位}/{hash}.opus`。"""
    return f"audio/{key[:2]}/{key}.opus"


# ---------------------------------------------------------------------------
# 听力材料音频（CR-008 / TT-09）
# ---------------------------------------------------------------------------
# 听力题播的是 `content.script`（听力材料原文），不是「题干 + 选项」；两者语义不同，
# 共用 `cache_key` 会互相覆盖，所以单独一套前缀与目录：`audio/listening/{hash前2位}/`。
LISTENING_RULES_VERSION = 1

# 听力材料首期范围：英语 1–9 年级（全库 1348 条 listening 题全部是 english）
LISTENING_GRADES: tuple[int, ...] = (1, 2, 3, 4, 5, 6, 7, 8, 9)
LISTENING_SUBJECTS: tuple[str, ...] = ("english",)


def listening_script(question: Any) -> str:
    """听力材料朗读文本：取 `content.script`，只做空白归一化。

    不套用 `normalize()`：那是中文读法规则（分数、单位、上下标），对英文材料无意义，
    反而可能把 `2/3` 之类读成「三分之二」。
    """
    content = question.content or {}
    raw = str(content.get("script") or "")
    return _SPACE_RE.sub(" ", raw).strip()


def listening_cache_key(text: str, voice: str, speed: float) -> str:
    payload = f"listening|{LISTENING_RULES_VERSION}|{voice}|{speed:.2f}|{text}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def listening_audio_rel_path(key: str) -> str:
    return f"audio/listening/{key[:2]}/{key}.opus"
