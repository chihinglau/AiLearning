from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(tags=["系统"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name, "env": settings.app_env}
