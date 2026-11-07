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
from app.legal import current_version
from app.models.user import AuditLog, User
from app.schemas.user import MeOut, PermissionsOut, TokenOut, UserCreate, UserOut
from app.services.audit import record_audit
from app.services.family import has_active_guardian
from app.services.legal import accepted_version, needs_reconsent, record_consents
from app.services.rbac import sync_user_role

router = APIRouter(prefix="/auth", tags=["账号"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(
    payload: UserCreate, request: Request, db: Session = Depends(get_db)
) -> User:
    exists = db.scalar(select(User).where(User.phone == payload.phone))
    if exists is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="该手机号已注册"
        )

    try:
        profile = resolve_grade_profile(payload.grade, payload.stage, payload.role)
        validate_elective_subjects(payload.elective_subjects, payload.grade)
    except GradeValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": exc.code, "message": exc.message},
        ) from exc

    # R-03 法务：儿童账号注册须监护人明确同意，避免未取得同意即采集信息。
    if payload.is_child and not payload.guardian_consent:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "GUARDIAN_CONSENT_REQUIRED",
                "message": (
                    "未满 14 周岁账号注册需监护人阅读并确认"
                    "《隐私政策》《用户协议》"
                ),
            },
        )

    provided_versions = {
        "privacy": payload.privacy_version,
        "terms": payload.terms_version,
    }
    if any(version is not None for version in provided_versions.values()):
        expected = {
            "privacy": current_version("privacy"),
            "terms": current_version("terms"),
        }
        if provided_versions != expected:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "POLICY_VERSION_MISMATCH",
                    "message": "法务文档版本已更新，请重新阅读后同意",
                    "current": expected,
                },
            )

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
    sync_user_role(db, user, payload.role)
    if payload.privacy_version and payload.terms_version:
        record_consents(
            db,
            user_id=user.id,
            privacy_version=payload.privacy_version,
            terms_version=payload.terms_version,
            guardian_confirmed=payload.guardian_consent,
            ip=request.client.host if request.client else None,
            commit=False,
        )
    db.add(
        AuditLog(
            user_id=user.id,
            action="user.register",
            detail=(
                f"role={user.role}, is_child={user.is_child}, "
                f"guardian_consent={payload.guardian_consent}"
            ),
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
    return TokenOut(
        access_token=create_access_token(str(user.id), user.token_version or 0)
    )


@router.get("/me", response_model=MeOut)
def me(
    current: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> MeOut:
    data = UserOut.model_validate(current)
    return MeOut(
        **data.model_dump(),
        permissions=current_user_permissions(current, db),
        scope=current_user_scope(current, db),
        guardian_consent=(
            True if not current.is_child else has_active_guardian(db, current)
        ),
        privacy_version=accepted_version(db, current.id, "privacy"),
        terms_version=accepted_version(db, current.id, "terms"),
        needs_reconsent=needs_reconsent(db, current.id),
    )


@router.get("/permissions", response_model=PermissionsOut)
def permissions(
    current: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> PermissionsOut:
    return PermissionsOut(
        permissions=current_user_permissions(current, db),
        scope=current_user_scope(current, db),
    )
