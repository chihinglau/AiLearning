from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.content import KnowledgePointOut, QuestionPublic


class LearnStartIn(BaseModel):
    chapter_id: Optional[int] = None
    knowledge_point_id: Optional[int] = None
    subject: Optional[str] = None
    count: int = Field(default=10, ge=1, le=50)


class LearnStartOut(BaseModel):
    questions: list[QuestionPublic]


class LearnSubmitIn(BaseModel):
    question_id: int
    user_answer: dict[str, Any]
    duration_ms: int = Field(default=0, ge=0)


class LearnSubmitOut(BaseModel):
    is_correct: bool
    correct_answer: dict[str, Any]
    analysis: Optional[str] = None
    mastery_score: Optional[float] = None
    in_wrong_book: bool = False


class KnowledgeNodeOut(KnowledgePointOut):
    """知识点（树节点）+ 个人掌握度。"""

    mastery_score: float = 0.0
    mastery_confidence: int = 0
    mastery_band: str = "weak"
    question_count: int = 0


class ChapterTreeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    textbook_id: int
    grade: int
    name: str
    order_index: int
    summary: Optional[str]
    knowledge_points: list[KnowledgeNodeOut] = []


class WrongQuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question_id: int
    wrong_count: int
    correct_streak: int
    status: str
    interval_days: int
    next_review_at: Optional[datetime]
    last_wrong_at: datetime
    wrong_reason: Optional[str]
    # 联表冗余，方便错题本列表直接渲染
    subject: str = ""
    q_type: str = "choice"
    stem: str = ""
    chapter_id: int = 0
    knowledge_point_id: Optional[int] = None
    difficulty: int = 3


class WrongReasonIn(BaseModel):
    wrong_reason: str = Field(pattern=r"^(careless|concept|method|calculation|reading|other)$")


class MasteryMapOut(BaseModel):
    items: dict[str, float]


class LearnStatsOut(BaseModel):
    total_answered: int
    total_correct: int
    accuracy: float
    streak_days: int
    due_review_count: int
    active_wrong_count: int
    weak_points: list[KnowledgeNodeOut]
