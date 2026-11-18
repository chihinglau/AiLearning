"""答案泄漏门禁规则单测（CR-008）。

覆盖三类主张：
  1. 真泄漏必须判 BLOCK（成语补充把答案印在横线旁、答案词落在题干叙述里）；
  2. 伪泄漏必须不判（选择题选项键、英文子串 is⊂This、数字子串 80⊂800、
     阅读理解取原文、算式题、排序/组词题）；
  3. 中间态判 WARN（候选括号、单字构词包含）。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from app.services import question_quality as qq  # noqa: E402


@pytest.mark.parametrize(
    "stem,answer",
    [
        ("把成语补充完整：兴致勃__。", {"value": "勃"}),
        ("把成语补充完整：理所当然（　）。", {"value": "然"}),
        ("和新同学说话，要先说一声（ ）你好。", {"value": "你好"}),
        ("随意放生外来物种可能造成（ ）入侵，危害本地生态。", {"value": "外来物种"}),
        ("1937 年 12 月，日军攻陷南京，制造了（ ）大屠杀。", {"value": "南京"}),
    ],
)
def test_hard_leak_is_blocked(stem: str, answer: dict) -> None:
    verdict = qq.check_answer_leak(stem, answer, "fill")
    assert verdict is not None, f"应判为泄漏：{stem}"
    assert verdict[0] == qq.BLOCK


@pytest.mark.parametrize(
    "stem,answer,q_type",
    [
        # 选择题存的是选项键
        ("下列哪个是哺乳动物？（ ）", {"value": "A"}, "choice"),
        # 判断题存 T/F
        ("地球是圆的。", {"value": "T"}, "judge"),
        # 英文子串：is ⊂ This
        ("This（ ）my father.", {"value": "is"}, "fill"),
        # 英文子串：er ⊂ Father / mother
        ("Father, mother: both end in ____.", {"value": "er"}, "fill"),
        # 数字子串：80 ⊂ 800
        ("从家到学校 800 米，走 10 分钟，平均每分钟走（ ）米。", {"value": "80"}, "fill"),
        # 排序题：题面必须给排序素材
        ("把 91、19、90、99 从大到小排列：（　）", {"value": "99、91、90、19"}, "fill"),
        # 组词题：题面必须给字
        ("“草”可以组词为（  ）地。", {"value": "草"}, "fill"),
        # 单字符字母辨认题
        ("b 和 d 中，竖在右边的是（ ）。", {"value": "d"}, "fill"),
    ],
)
def test_false_positive_is_cleared(stem: str, answer: dict, q_type: str) -> None:
    assert qq.check_answer_leak(stem, answer, q_type) is None, stem


def test_reading_comprehension_is_warn() -> None:
    stem = (
        "阅读短文，回答问题。冬天到了，窗户上结了一层薄薄的冰花。有的像小树，"
        "有的像羽毛。我用手指轻轻一碰，冰花就化成了小水珠。问：冰花化成了什么？"
    )
    verdict = qq.check_answer_leak(stem, {"value": "小水珠"}, "fill")
    assert verdict is not None and verdict[0] == qq.WARN


def test_candidate_paren_is_warn() -> None:
    stem = "洗手后及时关好水龙头，是在（ ）（节约/浪费，选合适的一个）用水。"
    verdict = qq.check_answer_leak(stem, {"value": "节约"}, "fill")
    assert verdict is not None and verdict[0] == qq.WARN


def test_single_char_word_is_warn() -> None:
    stem = "天上飘下白白的雪花，叫下（ ）。"
    verdict = qq.check_answer_leak(stem, {"value": "雪"}, "fill")
    assert verdict is not None and verdict[0] == qq.WARN


@pytest.mark.parametrize(
    "stem",
    [
        "五分之三减十分之三的结果是（ ）。",
        "用 4 个同样的小正方形可以拼成一个大（ ）。",  # 不删：含数字但非算式，应由 check 判
    ],
)
def test_arithmetic_stem_recognised(stem: str) -> None:
    if "分之" in stem:
        assert qq.is_arithmetic_stem(stem)
    else:
        assert not qq.is_arithmetic_stem(stem)


def test_list_answer_values_forms() -> None:
    assert qq.answer_values({"value": "法治"}) == ["法治"]
    assert qq.answer_values({"value": ["民族", "平等"]}) == ["民族", "平等"]
    assert qq.answer_values("法治") == ["法治"]
    assert qq.answer_values(None) == []
