"""主观题（解答/计算/习作）关键词覆盖判分：不再要求与参考答案逐字相同。"""

from app.models.content import Question
from app.services import learning as engine


def _mk(q_type: str, answer) -> Question:
    return Question(
        id=1,
        chapter_id=1,
        knowledge_point_id=1,
        subject="math",
        q_type=q_type,
        content={"stem": "?"},
        options=[],
        answer={"value": answer},
    )


GOU_GU = "示例：a 的平方加 b 的平方等于 c 的平方"


def test_math_formula_matches_text_answer():
    q = _mk("answer", GOU_GU)
    # 数学符号写法与文字表述都应判对（平方→幂指数、上标→数字）
    assert engine.grade_answer(q, {"value": "a²+b²=c²"}) is True
    assert engine.grade_answer(q, {"value": "a2+b2=c2"}) is True
    assert engine.grade_answer(q, {"value": "a的平方加b的平方等于c的平方"}) is True
    assert engine.grade_answer(q, {"value": "勾股定理：a² + b² = c²"}) is True


def test_key_points_coverage_passes():
    q = _mk("answer", "示例：大气圈的底部、水圈的大部、岩石圈的表面。")
    # 学生只写三部分名词（不写「的底部」这类细节）也应判对
    assert engine.grade_answer(q, {"value": "大气圈、水圈、岩石圈"}) is True


def test_off_topic_answer_fails():
    q = _mk("answer", GOU_GU)
    assert engine.grade_answer(q, {"value": "三角形内角和等于180度"}) is False
    assert engine.grade_answer(q, {"value": "勾股定理适用于直角三角形"}) is False
    assert engine.grade_answer(q, {"value": "不知道"}) is False
    assert engine.grade_answer(q, {"value": "a+b=c"}) is False


def test_partial_points_fail():
    q = _mk("answer", "示例：大气圈的底部、水圈的大部、岩石圈的表面。")
    # 只答对 3 项中的 2 项 → 覆盖率不足，判错
    assert engine.grade_answer(q, {"value": "大气圈和水圈"}) is False


def test_short_answer_keeps_exact_match():
    q = _mk("answer", "是")
    assert engine.grade_answer(q, {"value": "是"}) is True
    assert engine.grade_answer(q, {"value": "是的"}) is False


def test_composition_rubric():
    q = _mk("composition", "写清事情经过，有细节描写，语句通顺，不少于 400 字")
    assert (
        engine.grade_answer(
            q, {"value": "我写了一件难忘的事，经过写得很清楚，还加了细节描写，语句通顺。"}
        )
        is True
    )
    assert engine.grade_answer(q, {"value": "今天天气很好。"}) is False


def test_objective_types_unchanged():
    choice = _mk("choice", "A")
    assert engine.grade_answer(choice, {"value": " A "}) is True
    assert engine.grade_answer(choice, {"value": "B"}) is False
    fill = _mk("fill", ["3.5", "3.50"])
    assert engine.grade_answer(fill, {"value": "3.50"}) is True
    assert engine.grade_answer(fill, {"value": "3.6"}) is False
