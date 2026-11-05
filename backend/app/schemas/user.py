from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    phone: str = Field(pattern=r"^1[3-9]\d{9}$", description="中国大陆手机号")
    password: str = Field(min_length=6, max_length=64)
    nickname: str = Field(default="", max_length=50)
    role: str = Field(default="student", pattern=r"^(student|parent)$")
    stage: Optional[str] = Field(default=None, pattern=r"^(primary|junior|senior)$")
    grade: Optional[int] = Field(default=None, ge=1, le=12)
    is_child: bool = False


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    phone: str
    nickname: str
    role: str
    stage: Optional[str]
    grade: Optional[int]
    is_child: bool
    daily_limit_minutes: int
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
