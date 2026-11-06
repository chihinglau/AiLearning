from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user_permissions, current_user_scope, get_current_user
from app.core.grade import (
    GradeValidationError,
    resolve_grade_profile,
    validate_elective_subjects,
)
from app.core.scope import mask_phone
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.user import AuditLog, User
from app.schemas.user import MeOut, PermissionsOut, TokenOut, UserCreate, UserOut
from app.services.audit import record_audit

router = APIRouter(prefix="/auth", tags=["账号"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, request: Request, db: Session = Depends(get_db)) -> User:
    exists = db.scalar(select(User).where(User.phone == payload.phone))
    if exists is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该手机号已注册")

    try:
        profile = resolve_grade_profile(payload.grade, payload.stage, payload.role)
        validate_elective_subjects(payload.elective_subjects, payload.grade)
    except GradeValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": exc.code, "message": exc.message},
        ) from exc

    user = User(
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        nickname=payload.nickname or payload.phone[-4:],
        role=payload.role,
        stage=profile.stage if profile else None,
        grade=payload.grade,
        grade_group=profile.grade_group if profile else None,
        elective_subjects=payload.elective_subjects,
        grade_updated_at=datetime.utcnow() if profile else None,
        is_child=payload.is_child,
    )
    db.add(user)
    db.flush()
    db.add(
        AuditLog(
            user_id=user.id,
            action="user.register",
            detail=f"role={user.role}, is_child={user.is_child}",
            ip=request.client.host if request.client else None,
        )
    )
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenOut)
def login(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> TokenOut:
    ip = request.client.host if request.client else None
    user = db.scalar(select(User).where(User.phone == form.username))
    if user is None or not verify_password(form.password, user.password_hash):
        record_audit(
            db,
            user_id=user.id if user else None,
            action="auth.login_failed",
            message=f"phone={mask_phone(form.username)}",
            ip=ip,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="手机号或密码错误"
        )
    if not user.is_active:
        record_audit(
            db,
            user_id=user.id,
            action="auth.login_blocked",
            message="账号已停用",
            ip=ip,
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已停用")
    return TokenOut(access_token=create_access_token(str(user.id)))


@router.get("/me", response_model=MeOut)
def me(current: User = Depends(get_current_user)) -> MeOut:
    data = UserOut.model_validate(current)
    return MeOut(
        **data.model_dump(),
        permissions=current_user_permissions(current),
        scope=current_user_scope(current),
    )


@router.get("/permissions", response_model=PermissionsOut)
def permissions(current: User = Depends(get_current_user)) -> PermissionsOut:
    return PermissionsOut(
        permissions=current_user_permissions(current),
        scope=current_user_scope(current),
    )
