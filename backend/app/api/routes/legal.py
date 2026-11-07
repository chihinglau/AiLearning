"""法务文档公开访问与同意记录（R-03）。

- `GET /legal/privacy`、`GET /legal/terms`：免登录；浏览器访问返回 HTML，
  App 请求返回 JSON。
- `GET /legal/policies`：当前版本与公网地址，供 App「我的」页与版本升级判定。
- `POST /legal/consent`：登录用户同意当前版本后留痕（审计 `legal.consent.accepted`）。
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.legal import (
    TITLES,
    current_version,
    doc_names,
    read_markdown,
    render_html,
    updated_at,
)
from app.models.user import User
from app.schemas.legal import (
    ConsentIn,
    ConsentOut,
    LegalDocumentMeta,
    LegalDocumentOut,
    LegalPoliciesOut,
)
from app.services.legal import record_consents

router = APIRouter(prefix="/legal", tags=["法务"])


def _public_base(request: Request) -> str:
    if settings.legal_public_base_url.strip():
        return settings.legal_public_base_url.rstrip("/")
    return str(request.base_url).rstrip("/")


def _meta(request: Request, doc_type: str) -> LegalDocumentMeta:
    return LegalDocumentMeta(
        doc_type=doc_type,
        title=TITLES[doc_type],
        version=current_version(doc_type),
        updated_at=updated_at(doc_type),
        url=f"{_public_base(request)}/legal/{doc_type}",
    )


def _ensure_doc_type(doc_type: str) -> str:
    if doc_type not in doc_names():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="法务文档不存在"
        )
    return doc_type


@router.get("/policies", response_model=LegalPoliciesOut)
def policies(request: Request) -> LegalPoliciesOut:
    documents = [_meta(request, doc_type) for doc_type in doc_names()]
    return LegalPoliciesOut(version=current_version("privacy"), documents=documents)


@router.get(
    "/privacy", response_model=LegalDocumentOut, response_model_exclude_none=True
)
def privacy(request: Request):
    return _document(request, "privacy")


@router.get(
    "/terms", response_model=LegalDocumentOut, response_model_exclude_none=True
)
def terms(request: Request):
    return _document(request, "terms")


def _document(request: Request, doc_type: str):
    _ensure_doc_type(doc_type)
    accepts_html = "text/html" in request.headers.get("accept", "")
    markdown = read_markdown(doc_type)
    if accepts_html:
        return HTMLResponse(render_html(TITLES[doc_type], markdown))
    meta = _meta(request, doc_type)
    return LegalDocumentOut(**meta.model_dump(), content=markdown)


@router.get(
    "/{doc_type}",
    response_model=LegalDocumentOut,
    response_model_exclude_none=True,
)
def document(doc_type: str, request: Request):
    return _document(request, _ensure_doc_type(doc_type))


@router.post("/consent", response_model=ConsentOut)
def accept_consent(
    payload: ConsentIn,
    request: Request,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConsentOut:
    ip: Optional[str] = request.client.host if request.client else None
    expected = {
        "privacy": current_version("privacy"),
        "terms": current_version("terms"),
    }
    if (
        payload.privacy_version != expected["privacy"]
        or payload.terms_version != expected["terms"]
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "POLICY_VERSION_MISMATCH",
                "message": "法务文档版本已更新，请重新阅读后同意",
                "current": expected,
            },
        )
    accepted_at: datetime = record_consents(
        db,
        user_id=current.id,
        privacy_version=payload.privacy_version,
        terms_version=payload.terms_version,
        guardian_confirmed=payload.guardian_confirmed,
        ip=ip,
    )
    return ConsentOut(
        privacy_version=payload.privacy_version,
        terms_version=payload.terms_version,
        accepted_at=accepted_at,
    )
