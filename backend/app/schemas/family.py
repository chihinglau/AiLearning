from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class BindingCreate(BaseModel):
    child_phone: str = Field(pattern=r"^1[3-9]\d{9}$", description="孩子账号手机号")
    relation: str = Field(default="parent", max_length=20)


class BindingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    parent_id: int
    child_id: int
    relation: str
    status: str
    consent_at: Optional[datetime]
    created_at: datetime


class ChildOut(BaseModel):
    id: int
    nickname: str
    stage: Optional[str]
    grade: Optional[int]
    grade_group: Optional[str]
    is_child: bool
    consent_at: Optional[datetime]
    bound_at: datetime
    daily_limit_minutes: int = 120
    teen_mode: bool = False


class ChildControlsIn(BaseModel):
    daily_limit_minutes: Optional[int] = Field(default=None, ge=0, le=240)
    teen_mode: Optional[bool] = None
