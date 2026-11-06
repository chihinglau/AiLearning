"""P2-06 AI 讲解与错题归因接口 Schema。"""

from typing import List, Optional

from pydantic import BaseModel, Field


class AIExplainIn(BaseModel):
    question_id: int = Field(ge=1)
    wrong_question_id: Optional[int] = Field(default=None, ge=1)
    focus: Optional[str] = Field(default=None, pattern=r"^(concept|method|steps)$")


class AIExplainOut(BaseModel):
    question_id: int
    provider: str
    focus: Optional[str] = None
    explanation: str
    steps: List[str] = Field(default_factory=list)
    cautions: List[str] = Field(default_factory=list)
    remaining_quota: int


class AIDiagnoseIn(BaseModel):
    wrong_question_id: int = Field(ge=1)


class AIDiagnoseOut(BaseModel):
    wrong_id: int
    question_id: int
    provider: str
    reason: str
    reason_label: str
    confidence: str
    explanation: str
    suggestions: List[str] = Field(default_factory=list)
    remaining_quota: int
