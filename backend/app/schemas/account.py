"""R-04 青少年模式时长与账号注销出入参。"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DailyLimitStatusOut(BaseModel):
    daily_limit_minutes: int
    used_minutes: int
    remaining_minutes: Optional[int] = None
    limited: bool
    unlocks_at: Optional[datetime] = None


class AccountDeleteIn(BaseModel):
    confirm: bool = False
    reason: Optional[str] = Field(default=None, max_length=200)


class AccountDeleteOut(BaseModel):
    requested_at: datetime
    due_at: datetime
    message: str
