from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    phone: str = Field(pattern=r"^1[3-9]\d{9}$", description="中国大陆手机号")
    password: str = Field(min_length=6, max_length=64)
    nickname: str = Field(default="", max_length=50)
    role: str = Field(default="student", pattern=r"^(student|parent)$")
    stage: Optional[str] = Field(default=None, pattern=r"^(primary|junior|senior)$")
    grade: Optional[int] = Field(default=None, ge=1, le=12)
    elective_subjects: Optional[list[str]] = Field(default=None, max_length=3)
    is_child: bool = False


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    phone: str
    nickname: str
    role: str
    stage: Optional[str]
    grade: Optional[int]
    grade_group: Optional[str] = None
    is_child: bool
    daily_limit_minutes: int
    created_at: datetime


class PermissionsOut(BaseModel):
    permissions: List[str]
    scope: str


class MeOut(UserOut):
    permissions: List[str] = Field(default_factory=list)
    scope: str = "SELF"
    guardian_consent: bool = True


class GradeChangeIn(BaseModel):
    grade: int = Field(ge=1, le=12)
    confirm_token: Optional[str] = None


class GradeChangeOut(BaseModel):
    grade: int
    stage: str
    grade_group: str
    cross_stage: bool
    textbook_rebind_required: bool
    reauth_required: bool = True
    token_version: int


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
