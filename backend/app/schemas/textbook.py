from datetime import datetime
from typing import List

from pydantic import BaseModel, Field


class TextbookBrief(BaseModel):
    id: int
    subject: str
    grade: int
    version: str
    semester: str


class BindingOut(BaseModel):
    id: int
    subject: str
    semester: str
    source: str
    is_primary: bool
    status: str
    bound_at: datetime
    textbook: TextbookBrief
    # 教材年级与当前年级不一致（D-04 §13）
    mismatch: bool = False


class RecommendedSubject(BaseModel):
    subject: str
    textbook_id: int
    version: str
    grade: int


class RecommendationOut(BaseModel):
    grade: int
    semester: str
    region: str
    subjects: List[RecommendedSubject]


class BindIn(BaseModel):
    subject: str = Field(min_length=2, max_length=20)
    textbook_id: int = Field(ge=1)


class AutoBindOut(BaseModel):
    bound: int
    bindings: List[BindingOut]
