from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class TextbookCreate(BaseModel):
    subject: str = Field(min_length=1, max_length=20)
    grade: int = Field(ge=1, le=12)
    version: str = Field(min_length=1, max_length=50)
    semester: str = Field(default="first", pattern=r"^(first|second)$")


class TextbookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    subject: str
    grade: int
    version: str
    semester: str
    is_active: bool
    created_at: datetime


class ChapterCreate(BaseModel):
    textbook_id: int
    grade: int = Field(ge=1, le=12)
    name: str = Field(min_length=1, max_length=100)
    order_index: int = 0
    summary: Optional[str] = None


class ChapterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    textbook_id: int
    grade: int
    name: str
    order_index: int
    summary: Optional[str]


class QuestionCreate(BaseModel):
    chapter_id: int
    subject: str = Field(min_length=1, max_length=20)
    q_type: str = Field(
        default="choice", pattern=r"^(choice|multiple|fill|judge|calc|listen)$"
    )
    content: dict[str, Any]
    options: Optional[List[dict[str, Any]]] = None
    answer: dict[str, Any]
    analysis: Optional[str] = None
    difficulty: int = Field(default=3, ge=1, le=5)
    tags: Optional[List[str]] = None


class QuestionOut(QuestionCreate):
    """管理端完整题目（含答案与解析）。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class QuestionPublic(BaseModel):
    """学生端题目：不含答案与解析，避免客户端作弊。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    chapter_id: int
    subject: str
    q_type: str
    content: dict[str, Any]
    options: Optional[List[dict[str, Any]]]
    difficulty: int
    tags: Optional[List[str]]


class KnowledgePointOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    subject: str
    name: str
    parent_id: Optional[int]
    grade: Optional[int]
    prerequisites: Optional[List[int]]
    explanation: Optional[str]
