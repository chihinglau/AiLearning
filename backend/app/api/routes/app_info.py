"""应用信息与备案号公开接口（R-06）。

`GET /app/info` 免登录：返回应用名称/版本、ICP 备案号、APP 备案号、软著登记号、
法务公网地址与客服邮箱，供 App「关于」页与商店审核展示。
"""

from fastapi import APIRouter, Request

from app.core.config import settings
from app.schemas.app_info import AppInfoOut

router = APIRouter(prefix="/app", tags=["应用信息"])


def _public_base(request: Request) -> str:
    if settings.legal_public_base_url.strip():
        return settings.legal_public_base_url.rstrip("/")
    return str(request.base_url).rstrip("/")


@router.get("/info", response_model=AppInfoOut)
def app_info(request: Request) -> AppInfoOut:
    base = _public_base(request)
    return AppInfoOut(
        name=settings.app_display_name,
        version=settings.app_version_label,
        icp_record_no=settings.icp_record_no,
        app_record_no=settings.app_record_no,
        software_copyright_no=settings.software_copyright_no,
        privacy_url=f"{base}/legal/privacy",
        terms_url=f"{base}/legal/terms",
        support_email=settings.support_email,
    )
