"""用户自助资料变更与账号注销（D-03 §4.4、§10.1；R-04）。"""

import secrets
from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.core.grade import (
    GradeValidationError,
    academic_year,
    resolve_grade_profile,
    semester_start,
)
from app.core.scope import mask_phone
from app.core.security import (
    bump_token_version,
    create_grade_change_ticket,
    decode_grade_change_ticket,
)
from app.db.session import get_db
from app.models.user import GradeHistory, ParentChildBinding, User
from app.schemas.account import AccountDeleteIn, AccountDeleteOut, DailyLimitStatusOut
from app.schemas.user import GradeChangeIn, GradeChangeOut
from app.services.audit import record_audit
from app.services.usage import daily_limit_status

router = APIRouter(prefix="/users", tags=["用户"])

GRADE_IMPACT_MESSAGE = "修改年级将影响教材绑定、练习范围与推荐，历史学情保留"


def _impact(current: User, target: int, stage: str) -> dict:
    return {
        "current_grade": current.grade,
        "target_grade": target,
        "cross_stage": stage != current.stage,
        "textbook_rebind_required": True,
        "message": GRADE_IMPACT_MESSAGE,
    }


@router.put("/me/grade", response_model=GradeChangeOut)
def change_grade(
    payload: GradeChangeIn,
    request: Request,
    current: User = Depends(require_permission("user:grade:change")),
    db: Session = Depends(get_db),
):
    if current.role != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "NOT_STUDENT", "message": "仅学生账号可修改年级"},
        )
    if payload.grade == current.grade:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "GRADE_UNCHANGED", "message": "目标年级与当前年级相同"},
        )
    try:
        profile = resolve_grade_profile(payload.grade, role="student")
    except GradeValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": exc.code, "message": exc.message},
        )
    assert profile is not None

    now = datetime.utcnow()
    last_change = db.scalar(
        select(GradeHistory).where(
            GradeHistory.user_id == current.id,
            GradeHistory.source == "self",
            GradeHistory.created_at >= semester_start(now),
        )
    )
    if last_change is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "GRADE_CHANGE_LIMIT",
                "message": "每学期仅可自助修改 1 次，如需调整请联系客服或校管",
            },
        )

    impact = _impact(current, payload.grade, profile.stage)
    if payload.confirm_token is None:
        ticket = create_grade_change_ticket(
            current.id, payload.grade, current.token_version or 0
        )
        return JSONResponse(
            status_code=428,
            content={
                "code": "CONFIRM_REQUIRED",
                "impact": impact,
                "confirm_token": ticket,
            },
        )

    ticket = decode_grade_change_ticket(payload.confirm_token)
    if (
        ticket is None
        or ticket.user_id != current.id
        or ticket.grade != payload.grade
        or ticket.version != (current.token_version or 0)
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "CONFIRM_INVALID",
                "message": "确认令牌无效或已过期，请重新发起修改",
            },
        )

    before = {
        "grade": current.grade,
        "stage": current.stage,
        "grade_group": current.grade_group,
    }
    current.grade = payload.grade
    current.stage = profile.stage
    current.grade_group = profile.grade_group
    current.grade_updated_at = now

    school_year = academic_year(now)
    exists = db.scalar(
        select(GradeHistory).where(
            GradeHistory.user_id == current.id,
            GradeHistory.to_grade == payload.grade,
            GradeHistory.school_year == school_year,
        )
    )
    if exists is None:
        db.add(
            GradeHistory(
                user_id=current.id,
                from_grade=before["grade"],
                to_grade=payload.grade,
                school_year=school_year,
                source="self",
                operator_id=current.id,
            )
        )

    record_audit(
        db,
        user_id=current.id,
        action="user.grade.change",
        message="source=self",
        before=before,
        after={
            "grade": payload.grade,
            "stage": profile.stage,
            "grade_group": profile.grade_group,
        },
        ip=request.client.host if request.client else None,
        commit=False,
    )
    bump_token_version(current)
    db.commit()

    return GradeChangeOut(
        grade=current.grade,
        stage=current.stage,
        grade_group=current.grade_group,
        cross_stage=impact["cross_stage"],
        textbook_rebind_required=True,
        token_version=current.token_version,
    )


def _add_business_days(start: datetime, days: int) -> datetime:
    current = start
    added = 0
    while added < days:
        current += timedelta(days=1)
        if current.weekday() < 5:
            added += 1
    return current


@router.get("/me/usage", response_model=DailyLimitStatusOut)
def my_usage(
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DailyLimitStatusOut:
    """今日学习时长与青少年模式剩余额度（R-04）。"""
    return DailyLimitStatusOut(**daily_limit_status(db, current))


@router.delete(
    "/me",
    response_model=AccountDeleteOut,
    status_code=status.HTTP_202_ACCEPTED,
)
def delete_my_account(
    payload: AccountDeleteIn,
    request: Request,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AccountDeleteOut:
    """账号注销（R-04）：立即停用并匿名化，15 个工作日内完成删除/匿名化。

    注销不可恢复：手机号、昵称、密码立即脱敏，家长绑定全部解除，全部 Token 失效。
    """
    if not payload.confirm:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "CONFIRM_REQUIRED",
                "message": "请明确确认后再提交注销申请",
            },
        )
    if current.deletion_requested_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "ALREADY_REQUESTED",
                "message": "注销申请已受理，请勿重复提交",
            },
        )

    now = datetime.utcnow()
    due = _add_business_days(now, 15)
    bindings = db.scalars(
        select(ParentChildBinding).where(
            or_(
                ParentChildBinding.parent_id == current.id,
                ParentChildBinding.child_id == current.id,
            )
        )
    ).all()
    for binding in bindings:
        binding.status = "revoked"
        binding.consent_at = None

    before = {
        "role": current.role,
        "is_active": current.is_active,
        "phone_masked": mask_phone(current.phone),
        "bindings": len(bindings),
    }
    current.deletion_requested_at = now
    current.is_active = False
    current.phone = f"deleted-{current.id}-{uuid4().hex[:8]}"
    current.nickname = "已注销用户"
    current.password_hash = f"deleted:{secrets.token_hex(8)}"
    bump_token_version(current)

    record_audit(
        db,
        user_id=current.id,
        action="account.deletion.requested",
        message=f"reason={payload.reason or '未填写'}, due_at={due.isoformat()}",
        before=before,
        after={"anonymized": True, "revoked_bindings": len(bindings)},
        ip=request.client.host if request.client else None,
        commit=False,
    )
    db.commit()

    return AccountDeleteOut(
        requested_at=now,
        due_at=due,
        message=(
            "注销申请已受理：账号已立即停用并匿名化，家长绑定已解除，"
            "全部登录凭证已失效；我们将在 15 个工作日内完成删除或匿名化。"
        ),
    )
