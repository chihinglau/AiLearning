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
    # R-03 法务：儿童账号须监护人确认；同时可携带已阅读的政策版本用于留痕。
    guardian_consent: bool = False
    privacy_version: Optional[str] = Field(default=None, max_length=20)
    terms_version: Optional[str] = Field(default=None, max_length=20)


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
    # R-03 法务：已同意的版本与是否需要重新同意（版本升高时）
    privacy_version: Optional[str] = None
    terms_version: Optional[str] = None
    needs_reconsent: bool = False


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
    # 兼容旧客户端：refresh_token 可能为空，expires_in 为 access token 有效秒数。
    refresh_token: Optional[str] = None
    expires_in: int = 0


class RefreshTokenIn(BaseModel):
    refresh_token: str = Field(min_length=1, max_length=200)


class AdminUserOut(BaseModel):
    id: int
    phone_masked: str
    nickname: str
    role: str
    school_id: Optional[int] = None
    grade: Optional[int] = None
    grade_group: Optional[str] = None
    teacher_subjects: Optional[List[str]] = None
    grade_start: Optional[int] = None
    grade_end: Optional[int] = None
    is_active: bool


class AdminUserListOut(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[AdminUserOut]


class RoleChangeIn(BaseModel):
    grant: List[str] = Field(default_factory=list)
    revoke: List[str] = Field(default_factory=list)


class RoleChangeOut(BaseModel):
    id: int
    role: str
    token_version: int

