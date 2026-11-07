"""P2-09 内容审核双人复核接口。"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, has_permission, require_permission
from app.db.session import get_db
from app.models.content_review import ContentReview
from app.models.user import User
from app.schemas.content_review import (
    ContentReviewDecisionIn,
    ContentReviewOut,
    ContentReviewSubmitIn,
)
from app.services.content_review import (
    CONTENT_TYPES,
    REVIEW_STATUSES,
    SUBMIT_PERMISSIONS,
    decide_review,
    list_reviews,
    publish_review,
    submit_review,
)

router = APIRouter(prefix="/content", tags=["内容审核"])


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _can_submit(db: Session, user: User) -> bool:
    return any(has_permission(user, perm, db) for perm in SUBMIT_PERMISSIONS.values())


def _review_or_404(db: Session, review_id: int) -> ContentReview:
    review = db.get(ContentReview, review_id)
    if review is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "REVIEW_NOT_FOUND", "message": "复核单不存在"},
        )
    return review


@router.post("/reviews", response_model=ContentReviewOut, status_code=status.HTTP_201_CREATED)
def submit_content_review(
    payload: ContentReviewSubmitIn,
    request: Request,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ContentReview:
    if payload.content_type not in CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "CONTENT_TYPE_INVALID", "message": "仅支持题目/试卷复核"},
        )
    if not has_permission(current, SUBMIT_PERMISSIONS[payload.content_type], db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "PERMISSION_DENIED", "message": "无权提交该类型内容复核"},
        )
    return submit_review(
        db,
        user=current,
        content_type=payload.content_type,
        content_id=payload.content_id,
        note=payload.note,
        ip=_ip(request),
    )


@router.get("/reviews", response_model=list[ContentReviewOut])
def get_content_reviews(
    status_filter: str | None = Query(
        default=None, alias="status", pattern=r"^(pending|approved|rejected|published)$"
    ),
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ContentReview]:
    can_decide = has_permission(current, "content:review:decide", db)
    if not can_decide and not _can_submit(db, current):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "PERMISSION_DENIED", "message": "无权查看内容复核单"},
        )
    reviews = list_reviews(db, status_filter=status_filter)
    # 运营仅可见自己提交的复核单；审核员可查看全部
    if not can_decide:
        reviews = [item for item in reviews if item.submitted_by == current.id]
    return reviews


@router.get("/reviews/{review_id}", response_model=ContentReviewOut)
def get_content_review(
    review_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ContentReview:
    review = _review_or_404(db, review_id)
    if not (
        has_permission(current, "content:review:decide", db)
        or has_permission(current, "content:publish", db)
        or review.submitted_by == current.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "PERMISSION_DENIED", "message": "无权查看该复核单"},
        )
    return review


@router.post("/reviews/{review_id}/decision", response_model=ContentReviewOut)
def decide_content_review(
    review_id: int,
    payload: ContentReviewDecisionIn,
    request: Request,
    current: User = Depends(require_permission("content:review:decide")),
    db: Session = Depends(get_db),
) -> ContentReview:
    return decide_review(
        db,
        user=current,
        review_id=review_id,
        decision=payload.decision,
        comment=payload.comment,
        ip=_ip(request),
    )


@router.post("/reviews/{review_id}/publish", response_model=ContentReviewOut)
def publish_content_review(
    review_id: int,
    request: Request,
    current: User = Depends(require_permission("content:publish")),
    db: Session = Depends(get_db),
) -> ContentReview:
    return publish_review(db, user=current, review_id=review_id, ip=_ip(request))


@router.get("/review-statuses")
def list_review_statuses(
    current: User = Depends(get_current_user),
) -> list[str]:
    """复核状态字典（前端筛选使用）。"""
    return list(REVIEW_STATUSES)
