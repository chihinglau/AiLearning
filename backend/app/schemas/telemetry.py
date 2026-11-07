from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class CrashReportIn(BaseModel):
    """App 崩溃/错误上报体；超长字段在服务端截断，不做长度拒绝。"""

    message: str = Field(min_length=1)
    stack: Optional[str] = None
    error_type: Optional[str] = None
    platform: Optional[str] = None
    app_version: Optional[str] = None
    os_version: Optional[str] = None
    device_model: Optional[str] = None
    route: Optional[str] = None
    occurred_at: Optional[datetime] = None


class CrashReportOut(BaseModel):
    id: int
    fingerprint: str
    occurred_at: datetime


class CrashGroupOut(BaseModel):
    fingerprint: str
    error_type: Optional[str]
    message: str
    platform: str
    count: int
    last_seen: datetime


class CrashSummaryOut(BaseModel):
    days: int
    total: int
    unique_fingerprints: int
    top: List[CrashGroupOut]
    by_platform: dict[str, int]
    by_version: dict[str, int]


class CrashItemOut(BaseModel):
    id: int
    source: str
    platform: str
    app_version: Optional[str]
    os_version: Optional[str]
    device_model: Optional[str]
    route: Optional[str]
    error_type: Optional[str]
    message: str
    stack_trace: Optional[str]
    fingerprint: str
    request_id: Optional[str]
    occurred_at: datetime
    created_at: datetime
