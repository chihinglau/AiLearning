"""R-04 青少年模式：按中国时区统计今日学习时长并判定是否超限。"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.practice import StudentQuestionRecord
from app.models.user import User

CHINA_TZ = timezone(timedelta(hours=8))


def day_bounds(now: Optional[datetime] = None) -> tuple[datetime, datetime]:
    """返回中国时区「今天」对应的 UTC naive 起止时间（数据库统一存 UTC）。"""
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    local = current.astimezone(CHINA_TZ)
    start_local = local.replace(hour=0, minute=0, second=0, microsecond=0)
    end_local = start_local + timedelta(days=1)
    to_utc = timezone.utc
    return (
        start_local.astimezone(to_utc).replace(tzinfo=None),
        end_local.astimezone(to_utc).replace(tzinfo=None),
    )


def used_minutes(db: Session, user_id: int, now: Optional[datetime] = None) -> int:
    start, end = day_bounds(now)
    total_ms = db.scalar(
        select(func.coalesce(func.sum(StudentQuestionRecord.duration_ms), 0)).where(
            StudentQuestionRecord.user_id == user_id,
            StudentQuestionRecord.attempted_at >= start,
            StudentQuestionRecord.attempted_at < end,
        )
    ) or 0
    return int((total_ms + 59_999) // 60_000)


def unlocks_at(now: Optional[datetime] = None) -> datetime:
    """下一个中国时区零点（UTC naive）。"""
    return day_bounds(now)[1]


def daily_limit_status(
    db: Session, user: User, now: Optional[datetime] = None
) -> dict:
    limit = max(int(user.daily_limit_minutes or 0), 0)
    used = used_minutes(db, user.id, now)
    limited = limit > 0 and used >= limit
    return {
        "daily_limit_minutes": limit,
        "used_minutes": used,
        "remaining_minutes": max(limit - used, 0) if limit > 0 else None,
        "limited": limited,
        "unlocks_at": unlocks_at(now) if limited else None,
    }


def limit_exceeded_detail(status: dict) -> dict:
    return {
        "code": "DAILY_LIMIT_REACHED",
        "message": (
            f"今日学习时长已用完（上限 {status['daily_limit_minutes']} 分钟），"
            "请明天再来或联系家长调整"
        ),
        "limit_minutes": status["daily_limit_minutes"],
        "used_minutes": status["used_minutes"],
        "unlocks_at": (
            status["unlocks_at"].isoformat() if status["unlocks_at"] else None
        ),
    }


def retry_after_seconds(status: dict, now: Optional[datetime] = None) -> int:
    current = now or datetime.now(timezone.utc).replace(tzinfo=None)
    target = status["unlocks_at"]
    if target is None:
        return 3600
    return max(int((target - current).total_seconds()), 60)
