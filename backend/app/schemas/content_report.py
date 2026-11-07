"""R-07 内容举报 Schema。"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

REPORT_TARGET_TYPES = ("question", "textbook", "other")
REPORT_REASONS = ("answer_error", "inappropriate", "infringement", "other")


class ContentReportIn(BaseModel):
    target_type: Literal["question", "textbook", "other"]
    target_id: Optional[int] = None
    reason: Literal["answer_error", "inappropriate", "infringement", "other"]
    description: Optional[str] = Field(default=None, max_length=500)


class ContentReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reporter_id: int
    target_type: str
    target_id: Optional[int]
    reason: str
    description: Optional[str]
    status: str
    handled_by: Optional[int]
    handled_at: Optional[datetime]
    handle_note: Optional[str]
    created_at: datetime


class ContentReportHandleIn(BaseModel):
    action: Literal["takedown", "dismiss"]
    note: Optional[str] = Field(default=None, max_length=200)
