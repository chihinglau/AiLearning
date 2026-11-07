"""P2-08 数据导出与合规审计（脱敏导出 + 用途登记）。"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import (
    current_user_scope,
    get_current_user,
    has_permission,
)
from app.core.permissions import SCOPE_ALL, SCOPE_CHILD, SCOPE_SCHOOL, SCOPE_SELF
from app.core.scope import mask_phone
from app.db.session import get_db
from app.models.user import ParentChildBinding, User
from app.schemas.export import ExportMetaOut, ExportOut
from app.services.audit import record_audit
from app.services.export import (
    EXPORT_PURPOSES,
    build_export,
    resolve_purpose,
    section_counts,
)

router = APIRouter(prefix="/data", tags=["数据合规"])


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _active_binding(db: Session, parent_id: int, child_id: int) -> ParentChildBinding | None:
    return db.scalar(
        select(ParentChildBinding).where(
            ParentChildBinding.parent_id == parent_id,
            ParentChildBinding.child_id == child_id,
            ParentChildBinding.status == "active",
            ParentChildBinding.consent_at.is_not(None),
        )
    )


def _authorize(db: Session, current: User, student_id: int) -> tuple[str, User]:
    """返回 (访问范围, 目标学生)；无权限抛 403。"""
    target = db.get(User, student_id)
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "STUDENT_NOT_FOUND", "message": "未找到该学生账号"},
        )
    if student_id == current.id:
        return SCOPE_SELF, target
    if _active_binding(db, current.id, student_id) is not None:
        return SCOPE_CHILD, target
    if not has_permission(current, "data:export", db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "PERMISSION_DENIED", "message": "权限不足，无法导出他人数据"},
        )
    scope = current_user_scope(current, db)
    if scope == SCOPE_ALL:
        return SCOPE_ALL, target
    if (
        scope == SCOPE_SCHOOL
        and current.school_id is not None
        and target.school_id == current.school_id
        and target.role == "student"
    ):
        return SCOPE_SCHOOL, target
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"code": "SCOPE_DENIED", "message": "无权导出该学生数据"},
    )


@router.get("/export", response_model=ExportOut)
def export_student_data(
    request: Request,
    response: Response,
    student_id: int | None = Query(default=None, ge=1),
    purpose: str | None = Query(default=None),
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """导出个人学习数据副本：手机号脱敏、用途登记并写入审计。"""
    target_id = student_id if isinstance(student_id, int) else current.id
    scope, target = _authorize(db, current, target_id)
    # 单测直接调用时 Query 默认值是标记对象，统一归一化为 None
    requested_purpose = purpose if isinstance(purpose, str) else None
    code, label = resolve_purpose(requested_purpose, scope)

    bundle, truncated = build_export(db, target)
    counts = section_counts(bundle)

    record_audit(
        db,
        user_id=current.id,
        action="data.export",
        message=(
            f"purpose={code}, target={target.id}, scope={scope}, "
            f"truncated={str(truncated).lower()}"
        ),
        after={
            "purpose": code,
            "purpose_label": label,
            "target_user_id": target.id,
            "target_phone_masked": mask_phone(target.phone),
            "scope": scope,
            "format": "json",
            "sections": counts,
        },
        ip=_ip(request),
        commit=False,
    )
    db.commit()

    response.headers["Content-Disposition"] = (
        f"attachment; filename=ai-learning-export-{target.id}-"
        f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.json"
    )
    response.headers["X-Export-Purpose"] = code

    return {
        "meta": ExportMetaOut(
            student_id=target.id,
            requested_by=current.id,
            requester_role=current.role,
            scope=scope,
            purpose=code,
            purpose_label=label,
            generated_at=datetime.utcnow(),
            masked_fields=["phone"],
            truncated=truncated,
            section_counts=counts,
        ),
        **bundle,
    }


@router.get("/export/purposes")
def list_export_purposes(
    current: User = Depends(get_current_user),
) -> dict[str, str]:
    """可选导出用途字典（前端用途选择器使用）。"""
    return EXPORT_PURPOSES
