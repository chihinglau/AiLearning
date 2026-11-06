"""学期切换与学年升级任务（D-03 §4.4）：可重复执行、幂等。"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.grade import academic_year, derive_grade_group, derive_semester, derive_stage
from app.models.textbook import TextbookBinding
from app.models.user import GradeHistory, User
from app.services import textbook as textbook_service
from app.services.audit import record_audit


@dataclass
class SemesterSwitchResult:
    semester: str
    updated: int
    rebound: int


@dataclass
class PromotionResult:
    school_year: str
    promoted: int
    graduated: int
    skipped: Optional[str] = None


def _archive_bindings(db: Session, *, user_id: int, keep_semester: Optional[str] = None) -> int:
    """归档用户不再适用的教材绑定（旧学期或跨学段）。"""
    stmt = select(TextbookBinding).where(
        TextbookBinding.user_id == user_id, TextbookBinding.status == "active"
    )
    if keep_semester is not None:
        stmt = stmt.where(TextbookBinding.semester != keep_semester)
    rows = list(db.scalars(stmt))
    for row in rows:
        row.status = "archived"
    return len(rows)


def switch_semester(db: Session, *, now: Optional[datetime] = None) -> SemesterSwitchResult:
    """2 月/9 月切换学期：更新 `users.semester`，归档旧学期教材并重绑新学期教材。"""
    moment = now or datetime.utcnow()
    semester = derive_semester(moment)
    users = list(
        db.scalars(
            select(User).where(
                User.is_active.is_(True), User.graduated_at.is_(None)
            )
        )
    )
    updated = rebound = 0
    for user in users:
        if (user.semester or "") == semester:
            continue
        had_bindings = (
            db.scalar(
                select(func.count(TextbookBinding.id)).where(
                    TextbookBinding.user_id == user.id,
                    TextbookBinding.status == "active",
                )
            )
            or 0
        ) > 0
        _archive_bindings(db, user_id=user.id, keep_semester=semester)
        user.semester = semester
        updated += 1
        if user.role == "student" and had_bindings:
            textbook_service.auto_bind(db, user, now=moment)
            rebound += 1
    db.commit()
    return SemesterSwitchResult(semester=semester, updated=updated, rebound=rebound)


def _promoted_this_year(db: Session, *, user_id: int, school_year: str) -> bool:
    """同一学年内系统升级任务只执行一次（重复运行直接跳过）。"""
    return (
        db.scalar(
            select(GradeHistory.id).where(
                GradeHistory.user_id == user_id,
                GradeHistory.school_year == school_year,
                GradeHistory.source == "system",
            )
        )
        is not None
    )


def _write_history(
    db: Session,
    *,
    user_id: int,
    from_grade: int,
    to_grade: int,
    school_year: str,
    reason: str,
) -> GradeHistory:
    history = GradeHistory(
        user_id=user_id,
        from_grade=from_grade,
        to_grade=to_grade,
        school_year=school_year,
        source="system",
        reason=reason,
    )
    db.add(history)
    return history


def promote_grades(db: Session, *, now: Optional[datetime] = None) -> PromotionResult:
    """每年 9 月学年升级：`grade + 1`；12 年级毕业；以历史表唯一键保证幂等。"""
    moment = now or datetime.utcnow()
    school_year = academic_year(moment)
    if moment.month < 9:
        return PromotionResult(
            school_year=school_year, promoted=0, graduated=0, skipped="NOT_SEPTEMBER"
        )

    students = list(
        db.scalars(
            select(User).where(
                User.role == "student",
                User.is_active.is_(True),
                User.graduated_at.is_(None),
                User.grade.is_not(None),
            )
        )
    )
    promoted = graduated = 0
    for user in students:
        current = int(user.grade or 0)
        target = min(current + 1, 12)
        if _promoted_this_year(db, user_id=user.id, school_year=school_year):
            continue

        if current >= 12:
            user.graduated_at = moment
            _write_history(
                db,
                user_id=user.id,
                from_grade=current,
                to_grade=target,
                school_year=school_year,
                reason="graduated",
            )
            record_audit(
                db,
                user_id=user.id,
                action="user.grade.change",
                message="学年升级任务：高中毕业",
                before={"grade": current},
                after={"graduated_at": moment.isoformat()},
                commit=False,
            )
            graduated += 1
            continue

        new_stage = derive_stage(target)
        if user.stage != new_stage:
            # 6→7、9→10：强制重新确认教材版本与学科列表
            _archive_bindings(db, user_id=user.id)
        user.grade = target
        user.stage = new_stage
        user.grade_group = derive_grade_group(target)
        user.grade_updated_at = moment
        user.semester = derive_semester(moment)
        user.token_version = (user.token_version or 0) + 1
        _write_history(
            db,
            user_id=user.id,
            from_grade=current,
            to_grade=target,
            school_year=school_year,
            reason="promotion",
        )
        record_audit(
            db,
            user_id=user.id,
            action="user.grade.change",
            message="学年升级任务",
            before={"grade": current, "stage": derive_stage(current)},
            after={"grade": target, "stage": new_stage},
            commit=False,
        )
        promoted += 1

    db.commit()
    return PromotionResult(
        school_year=school_year, promoted=promoted, graduated=graduated
    )
