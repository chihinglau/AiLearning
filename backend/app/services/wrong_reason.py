"""P1-12 考试错题错因默认分类与复习优先级。"""

from datetime import datetime
from typing import Any, Optional

from app.models.content import Question
from app.models.practice import WrongQuestion

# 错因枚举（与 WrongReasonIn 一致）
REASON_LABELS = {
    "reading": "审题",
    "calculation": "计算",
    "concept": "概念",
    "method": "方法",
    "careless": "粗心",
    "other": "其他",
}

# 按题型给出考试错题默认错因：选择/判断→概念，填空/计算→计算，
# 多选（漏选/多选）→审题，主观作答→方法；未作答→粗心。
REASON_BY_Q_TYPE = {
    "choice": "concept",
    "judge": "concept",
    "fill": "calculation",
    "calc": "calculation",
    "multiple": "reading",
    "answer": "method",
    "listen": "method",
}


def _has_answer(user_answer: Optional[dict[str, Any]]) -> bool:
    if not user_answer:
        return False
    value = user_answer.get("value") if isinstance(user_answer, dict) else user_answer
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, dict)):
        return len(value) > 0
    return True


def classify_exam_wrong(
    question: Question, user_answer: Optional[dict[str, Any]]
) -> str:
    """考试错题默认错因；作答为空时归为粗心（漏答）。"""
    if not _has_answer(user_answer):
        return "careless"
    return REASON_BY_Q_TYPE.get(question.q_type, "other")


def review_priority(row: WrongQuestion, now: datetime) -> tuple[int, str]:
    """复习优先级：错误次数 + 遗忘次数 + 逾期天数，返回 (分数, 等级)。"""
    overdue = 0
    if row.next_review_at is not None:
        overdue = max(0, (now - row.next_review_at).days)
    score = row.wrong_count * 2 + row.lapses + overdue
    if row.status != "active":
        return 0, "low"
    if score >= 6:
        return score, "high"
    if score >= 3:
        return score, "medium"
    return score, "low"
