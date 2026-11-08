from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user_permissions, current_user_scope, get_current_user
from app.core.config import settings
from app.core.grade import (
    GradeValidationError,
    resolve_grade_profile,
    validate_elective_subjects,
)
from app.core.scope import mask_phone
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.db.session import get_db
from app.legal import current_version
from app.models.auth_token import RefreshToken
from app.models.user import AuditLog, User
from app.schemas.user import (
    MeOut,
    PermissionsOut,
    RefreshTokenIn,
    TokenOut,
    UserCreate,
    UserOut,
)
from app.services.audit import record_audit
from app.services.family import has_active_guardian
from app.services.legal import accepted_version, needs_reconsent, record_consents
from app.services.rbac import sync_user_role

router = APIRouter(prefix="/auth", tags=["账号"])


def _issue_refresh_token(
    db: Session,
    user: User,
    *,
    request: Request,
    family_id: str | None = None,
) -> str:
    """签发刷新令牌（明文返回给客户端，摘要落库）。"""
    raw = generate_refresh_token()
    now = datetime.utcnow()
    user_agent = (request.headers.get("user-agent") or "")[:255]
    row = RefreshToken(
        user_id=user.id,
        family_id=family_id or uuid4().hex,
        token_hash=hash_refresh_token(raw),
        token_version=user.token_version or 0,
        expires_at=now + timedelta(days=settings.refresh_token_expire_days),
        created_at=now,
        ip=request.client.host if request.client else None,
        user_agent=user_agent or None,
    )
    db.add(row)
    db.flush()
    return raw


def _token_response(user: User, refresh_token: str) -> TokenOut:
    return TokenOut(
        access_token=create_access_token(str(user.id), user.token_version or 0),
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


def _refresh_invalid() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "code": "REFRESH_TOKEN_INVALID",
            "message": "登录状态已失效，请重新登录",
        },
        headers={"WWW-Authenticate": "Bearer"},
    )


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
    refresh = _issue_refresh_token(db, user, request=request)
    record_audit(
        db,
        user_id=user.id,
        action="auth.login",
        message=f"phone={mask_phone(user.phone)}",
        ip=ip,
        commit=False,
    )
    db.commit()
    return _token_response(user, refresh)


@router.post("/refresh", response_model=TokenOut)
def refresh(
    payload: RefreshTokenIn,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenOut:
    """刷新令牌轮换：旧令牌立即作废，新令牌沿用同一 family_id。

    已撤销的令牌再次出现视为泄露重用，整族撤销并要求重新登录。
    """
    ip = request.client.host if request.client else None
    row = db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_refresh_token(payload.refresh_token)
        )
    )
    if row is None:
        raise _refresh_invalid()

    now = datetime.utcnow()
    if row.revoked_at is not None:
        revoked = (
            db.query(RefreshToken)
            .filter(
                RefreshToken.family_id == row.family_id,
                RefreshToken.revoked_at.is_(None),
            )
            .update({RefreshToken.revoked_at: now}, synchronize_session=False)
        )
        record_audit(
            db,
            user_id=row.user_id,
            action="auth.refresh_reuse",
            message=f"family={row.family_id}, revoked={revoked}",
            ip=ip,
            commit=False,
        )
        db.commit()
        raise _refresh_invalid()

    user = db.get(User, row.user_id)
    if (
        user is None
        or not user.is_active
        or row.expires_at <= now
        or row.token_version != (user.token_version or 0)
    ):
        row.revoked_at = now
        record_audit(
            db,
            user_id=row.user_id,
            action="auth.refresh_failed",
            message="expired_or_revoked_version",
            ip=ip,
            commit=False,
        )
        db.commit()
        raise _refresh_invalid()

    row.revoked_at = now
    row.last_used_at = now
    new_refresh = _issue_refresh_token(
        db, user, request=request, family_id=row.family_id
    )
    new_row = db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(new_refresh))
    )
    if new_row is not None:
        row.replaced_by_id = new_row.id
    record_audit(
        db,
        user_id=user.id,
        action="auth.refresh",
        message=f"family={row.family_id}",
        ip=ip,
        commit=False,
    )
    db.commit()
    return _token_response(user, new_refresh)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(payload: RefreshTokenIn, db: Session = Depends(get_db)) -> Response:
    """登出：撤销该刷新令牌所属的整个登录族（幂等）。"""
    row = db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_refresh_token(payload.refresh_token)
        )
    )
    if row is not None:
        revoked = (
            db.query(RefreshToken)
            .filter(
                RefreshToken.family_id == row.family_id,
                RefreshToken.revoked_at.is_(None),
            )
            .update(
                {RefreshToken.revoked_at: datetime.utcnow()},
                synchronize_session=False,
            )
        )
        record_audit(
            db,
            user_id=row.user_id,
            action="auth.logout",
            message=f"family={row.family_id}, revoked={revoked}",
            commit=False,
        )
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
