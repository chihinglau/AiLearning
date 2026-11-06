"""家长-孩子绑定状态机（D-03 §7.2、§10.2）。"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.db.session import get_db
from app.models.user import ParentChildBinding, User
from app.schemas.family import (
    BindingCreate,
    BindingOut,
    ChildControlsIn,
    ChildOut,
)
from app.services.audit import record_audit

router = APIRouter(prefix="/family", tags=["家庭"])


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _get_binding(db: Session, binding_id: int) -> ParentChildBinding:
    binding = db.get(ParentChildBinding, binding_id)
    if binding is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "BINDING_NOT_FOUND", "message": "绑定关系不存在"},
        )
    return binding


@router.post("/bindings", response_model=BindingOut, status_code=status.HTTP_201_CREATED)
def request_binding(
    payload: BindingCreate,
    request: Request,
    current: User = Depends(require_permission("family:binding:request")),
    db: Session = Depends(get_db),
) -> ParentChildBinding:
    if current.role != "parent":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "NOT_PARENT", "message": "仅家长账号可发起绑定"},
        )
    child = db.scalar(
        select(User).where(User.phone == payload.child_phone, User.role == "student")
    )
    if child is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CHILD_NOT_FOUND", "message": "未找到该手机号对应的学生账号"},
        )

    binding = db.scalar(
        select(ParentChildBinding).where(
            ParentChildBinding.parent_id == current.id,
            ParentChildBinding.child_id == child.id,
        )
    )
    if binding is not None and binding.status == "active":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "ALREADY_BOUND", "message": "该孩子已与当前账号绑定"},
        )
    if binding is None:
        binding = ParentChildBinding(
            parent_id=current.id, child_id=child.id, relation=payload.relation, status="pending"
        )
        db.add(binding)
        db.flush()
    else:
        binding.status = "pending"
        binding.relation = payload.relation
        binding.consent_at = None

    record_audit(
        db,
        user_id=current.id,
        action="family.binding.request",
        message=f"child_id={child.id}",
        ip=_ip(request),
        commit=False,
    )
    db.commit()
    db.refresh(binding)
    return binding


@router.post("/bindings/{binding_id}/confirm", response_model=BindingOut)
def confirm_binding(
    binding_id: int,
    request: Request,
    current: User = Depends(require_permission("family:binding:manage")),
    db: Session = Depends(get_db),
) -> ParentChildBinding:
    binding = _get_binding(db, binding_id)
    if current.id not in (binding.parent_id, binding.child_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "SCOPE_DENIED", "message": "无权操作该绑定关系"},
        )
    if binding.status == "revoked":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "BINDING_REVOKED", "message": "绑定已解除，请重新发起"},
        )
    if binding.status == "active" and binding.consent_at is not None:
        return binding

    binding.status = "active"
    binding.consent_at = datetime.utcnow()
    record_audit(
        db,
        user_id=current.id,
        action="family.binding.confirm",
        message=f"binding_id={binding.id}, child_id={binding.child_id}",
        ip=_ip(request),
        commit=False,
    )
    db.commit()
    db.refresh(binding)
    return binding


@router.delete("/bindings/{binding_id}", response_model=BindingOut)
def revoke_binding(
    binding_id: int,
    request: Request,
    current: User = Depends(require_permission("family:binding:manage")),
    db: Session = Depends(get_db),
) -> ParentChildBinding:
    binding = _get_binding(db, binding_id)
    if current.id not in (binding.parent_id, binding.child_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "SCOPE_DENIED", "message": "无权操作该绑定关系"},
        )
    if binding.status != "revoked":
        binding.status = "revoked"
        record_audit(
            db,
            user_id=current.id,
            action="family.binding.revoke",
            message=f"binding_id={binding.id}, child_id={binding.child_id}",
            ip=_ip(request),
            commit=False,
        )
        db.commit()
        db.refresh(binding)
    return binding


def _child_out(child: User, binding: ParentChildBinding) -> ChildOut:
    return ChildOut(
        id=child.id,
        nickname=child.nickname,
        stage=child.stage,
        grade=child.grade,
        grade_group=child.grade_group,
        is_child=child.is_child,
        consent_at=binding.consent_at,
        bound_at=binding.created_at,
        daily_limit_minutes=child.daily_limit_minutes,
        teen_mode=child.teen_mode,
    )


@router.get("/children", response_model=list[ChildOut])
def list_children(
    current: User = Depends(require_permission("family:report:read")),
    db: Session = Depends(get_db),
) -> list[ChildOut]:
    rows = db.execute(
        select(User, ParentChildBinding)
        .join(ParentChildBinding, ParentChildBinding.child_id == User.id)
        .where(
            ParentChildBinding.parent_id == current.id,
            ParentChildBinding.status == "active",
        )
        .order_by(ParentChildBinding.created_at)
    ).all()
    return [_child_out(child, binding) for child, binding in rows]


@router.put("/children/{child_id}/controls", response_model=ChildOut)
def update_child_controls(
    child_id: int,
    payload: ChildControlsIn,
    request: Request,
    current: User = Depends(require_permission("family:binding:manage")),
    db: Session = Depends(get_db),
) -> ChildOut:
    """家长设置孩子每日时长与青少年模式（D-03 §10.2）。"""
    if payload.daily_limit_minutes is None and payload.teen_mode is None:
        raise HTTPException(
            status_code=422,
            detail={"code": "CONTROLS_REQUIRED", "message": "请至少设置一项"},
        )
    binding = db.scalar(
        select(ParentChildBinding).where(
            ParentChildBinding.parent_id == current.id,
            ParentChildBinding.child_id == child_id,
            ParentChildBinding.status == "active",
        )
    )
    child = db.get(User, child_id)
    if binding is None or child is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "BINDING_NOT_ACTIVE", "message": "未找到已生效的孩子绑定"},
        )

    before = {
        "daily_limit_minutes": child.daily_limit_minutes,
        "teen_mode": child.teen_mode,
    }
    if payload.daily_limit_minutes is not None:
        child.daily_limit_minutes = payload.daily_limit_minutes
    if payload.teen_mode is not None:
        child.teen_mode = payload.teen_mode
    record_audit(
        db,
        user_id=current.id,
        action="family.controls.update",
        before=before,
        after={
            "daily_limit_minutes": child.daily_limit_minutes,
            "teen_mode": child.teen_mode,
        },
        message=f"child_id={child.id}",
        ip=_ip(request),
        commit=False,
    )
    db.commit()
    db.refresh(child)
    return _child_out(child, binding)
