"""P2-09 内容审核双人复核 Schema。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ContentReviewSubmitIn(BaseModel):
    content_type: Literal["question", "exam"]
    content_id: int = Field(ge=1)
    note: str | None = None


class ContentReviewDecisionIn(BaseModel):
    decision: Literal["approve", "reject"]
    comment: str | None = None


class ContentReviewOut(BaseModel):
    id: int
    content_type: str
    content_id: int
    title: str
    note: str | None
    status: str
    submitted_by: int
    submitted_at: datetime
    reviewed_by: int | None
    reviewed_at: datetime | None
    comment: str | None
    published_by: int | None
    published_at: datetime | None

    model_config = {"from_attributes": True}
