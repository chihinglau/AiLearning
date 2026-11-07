"""P2-08 合规数据导出接口 Schema。"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ExportMetaOut(BaseModel):
    """用途登记元信息：谁在何时、以何种用途、导出谁的数据。"""

    student_id: int
    requested_by: int
    requester_role: str
    scope: str
    purpose: str
    purpose_label: str
    generated_at: datetime
    masked_fields: list[str] = Field(default_factory=lambda: ["phone"])
    truncated: bool = False
    section_counts: dict[str, int] = Field(default_factory=dict)


class ExportOut(BaseModel):
    meta: ExportMetaOut
    profile: dict[str, Any]
    learning_stats: dict[str, Any]
    grade_histories: list[dict[str, Any]]
    guardian_bindings: list[dict[str, Any]]
    textbook_bindings: list[dict[str, Any]]
    question_records: list[dict[str, Any]]
    wrong_questions: list[dict[str, Any]]
    mastery_scores: list[dict[str, Any]]
    kp_study_states: list[dict[str, Any]]
    practice_sessions: list[dict[str, Any]]
    exam_attempts: list[dict[str, Any]]
