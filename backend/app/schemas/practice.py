from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.content import QuestionPublic


class PracticeStartIn(BaseModel):
    chapter_id: Optional[int] = None
    knowledge_point_id: Optional[int] = None
    subject: Optional[str] = None
    count: int = Field(default=10, ge=1, le=50)


class PracticeStartOut(BaseModel):
    questions: list[QuestionPublic]


class PracticeSubmitIn(BaseModel):
    question_id: int
    user_answer: dict[str, Any]
    duration_ms: int = Field(default=0, ge=0)


class PracticeSubmitOut(BaseModel):
    is_correct: bool
    correct_answer: dict[str, Any]
    analysis: Optional[str] = None


class PracticeRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question_id: int
    is_correct: bool
    user_answer: Optional[dict[str, Any]]
    duration_ms: int
    wrong_reason: Optional[str]
    mastered: bool
    attempted_at: datetime
