"""R-02 生产化中间件：登录/注册限流与未捕获异常脱敏。"""

import logging
import uuid

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.rate_limit import rate_limiter
from app.services import telemetry

logger = logging.getLogger("ailearning.access")


def _rate_limit_for(path: str) -> int:
    rules = {
        f"{settings.api_prefix}/auth/login": settings.login_rate_limit_per_minute,
        f"{settings.api_prefix}/auth/register": settings.register_rate_limit_per_minute,
        f"{settings.api_prefix}/monitor/crash": settings.monitor_rate_limit_per_minute,
    }
    return rules.get(path, 0)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """按客户端 IP + 路径限制登录/注册频率，超限返回 429 RATE_LIMITED。"""

    async def dispatch(self, request: Request, call_next):
        if not settings.rate_limit_enabled or request.method == "OPTIONS":
            return await call_next(request)
        limit = _rate_limit_for(request.url.path)
        if limit <= 0:
            return await call_next(request)
        client_ip = request.client.host if request.client else "unknown"
        allowed, retry_after = rate_limiter.allow(
            f"{request.url.path}:{client_ip}", limit
        )
        if not allowed:
            logger.warning("rate_limited path=%s ip=%s", request.url.path, client_ip)
            return JSONResponse(
                status_code=429,
                content={"detail": "RATE_LIMITED"},
                headers={"Retry-After": str(retry_after)},
            )
        return await call_next(request)


class ErrorMaskingMiddleware(BaseHTTPMiddleware):
    """未捕获异常统一返回 INTERNAL_ERROR，避免堆栈/数据库信息泄漏到客户端。"""

    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as exc:
            request_id = uuid.uuid4().hex[:12]
            logger.exception(
                "unhandled_error request_id=%s method=%s path=%s",
                request_id,
                request.method,
                request.url.path,
            )
            # R-09：后端异常同步落监控表（写入失败只记日志，不影响响应）。
            telemetry.record_server_error(
                method=request.method,
                path=request.url.path,
                request_id=request_id,
                error=exc,
            )
            return JSONResponse(
                status_code=500,
                content={"detail": "INTERNAL_ERROR", "request_id": request_id},
            )
