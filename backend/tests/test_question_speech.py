"""TT-02/TT-03 读法规则（Python 侧）与服务端合成脚本共用同一份规则表。"""

import re
from pathlib import Path

import pytest

from app.services import question_speech as speech

DART_RULES = (
    Path(__file__).resolve().parents[2]
    / "app"
    / "lib"
    / "core"
    / "speech"
    / "question_speech.dart"
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("3/4", "四分之三"),
        ("1/2", "二分之一"),
        ("10/25", "二十五分之十"),
        ("x²", "x 的平方"),
        ("x³", "x 的立方"),
        ("2⁴", "2 的 4 次方"),
        ("a₁", "a 下标 1"),
        ("12÷4", "12除以4"),
        ("3×5", "3乘5"),
        ("±5", "正负5"),
        ("a≥b", "a大于等于b"),
        ("a≤b", "a小于等于b"),
        ("3cm", "三厘米"),
        ("5kg", "五千克"),
        ("2L", "两升"),
        ("____", "空格"),
        ("3/4 × 2cm = ____", "四分之三 乘 两厘米 等于 空格"),
        ("How many apples?", "How many apples?"),
    ],
)
def test_normalize_table(raw: str, expected: str) -> None:
    assert speech.normalize(raw) == expected


def test_normalize_idempotent() -> None:
    once = speech.normalize("3/4 × 2cm = ____")
    assert speech.normalize(once) == once


def test_option_script_and_prefix_strip() -> None:
    assert speech.option_script("A", "三个苹果") == "选项 A，三个苹果"
    assert speech.option_script("A", "A. 三个") == "选项 A，三个"


def test_question_script_joins_stem_and_options() -> None:
    script = speech.question_script(
        "3/4 是多少",
        [{"key": "A", "text": "1/2"}, {"key": "B", "text": "2/3"}],
    )
    assert script == "四分之三 是多少。选项 A，二分之一。选项 B，三分之二"


def test_question_script_skips_blank_option() -> None:
    options = [{"key": "A", "text": "  "}]
    assert speech.question_script("2加3是多少", options) == "2加3是多少"


def test_chinese_number_range() -> None:
    assert speech.to_chinese_number(0) == "零"
    assert speech.to_chinese_number(10) == "十"
    assert speech.to_chinese_number(25) == "二十五"
    assert speech.to_chinese_number(105) == "一百零五"
    assert speech.to_chinese_number(1000) == "1000"


def test_cache_key_stable_and_sensitive() -> None:
    base = speech.cache_key("四分之三", "zh_CN-huayan-medium", 1.0)
    assert base == speech.cache_key("四分之三", "zh_CN-huayan-medium", 1.0)
    assert base != speech.cache_key("四分之三", "zh_CN-huayan-medium", 0.85)
    assert base != speech.cache_key("四分之三", "en_US-lessac-medium", 1.0)
    assert base != speech.cache_key("四分之哦", "zh_CN-huayan-medium", 1.0)
    assert speech.audio_rel_path(base) == f"audio/{base[:2]}/{base}.opus"


def test_voice_mapping_by_subject() -> None:
    assert speech.voice_for_subject("english") == "vits-piper-en_US-lessac-medium"
    assert speech.voice_for_subject("math") == "vits-piper-zh_CN-huayan-medium"
    assert speech.voice_for_subject("chinese") == "vits-piper-zh_CN-huayan-medium"


def test_rules_version_matches_client() -> None:
    """规则表两侧共用：版本号不一致说明缓存键会漂移，必须同步。"""
    assert DART_RULES.exists(), f"缺少客户端规则文件：{DART_RULES}"
    match = re.search(
        r"static const int version = (\d+);", DART_RULES.read_text(encoding="utf-8")
    )
    assert match is not None
    assert int(match.group(1)) == speech.RULES_VERSION
