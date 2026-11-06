from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@dataclass(frozen=True)
class TokenData:
    subject: str
    version: int


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(
    subject: str, token_version: int = 0, expires_minutes: Optional[int] = None
) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes or settings.access_token_expire_minutes
    )
    payload: dict[str, Any] = {"sub": subject, "ver": token_version, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> Optional[TokenData]:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
    subject = payload.get("sub")
    if subject is None:
        return None
    # 兼容本次升级前签发的旧 Token（无 ver 字段视为 0）
    version = payload.get("ver", 0)
    try:
        return TokenData(subject=str(subject), version=int(version))
    except (TypeError, ValueError):
        return None


def bump_token_version(user: Any) -> int:
    """角色/年级等敏感变更后使旧 Token 失效。"""
    user.token_version = (user.token_version or 0) + 1
    return user.token_version
