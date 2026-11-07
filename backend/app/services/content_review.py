"""内容审核双人复核服务（P2-09、D-03 §5.3/§8）。"""

from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.content import Question
from app.models.content_review import ContentReview
from app.models.exam import Exam
from app.models.user import User
from app.services.audit import record_audit

CONTENT_TYPES = ("question", "exam")

SUBMIT_PERMISSIONS = {
    "question": "content:question:write",
    "exam": "content:exam:write",
}

REVIEW_STATUSES = ("pending", "approved", "rejected", "published")


def _review_or_404(db: Session, review_id: int) -> ContentReview:
    review = db.get(ContentReview, review_id)
    if review is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "REVIEW_NOT_FOUND", "message": "复核单不存在"},
        )
    return review


def _target(db: Session, content_type: str, content_id: int) -> tuple[object, str]:
    """返回 (内容对象, 标题)；类型非法或内容不存在抛 404/422。"""
    if content_type == "question":
        question = db.get(Question, content_id)
        if question is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "CONTENT_NOT_FOUND", "message": "题目不存在"},
            )
        return question, f"题目 #{question.id}"
    if content_type == "exam":
        exam = db.get(Exam, content_id)
        if exam is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "CONTENT_NOT_FOUND", "message": "试卷不存在"},
            )
        return exam, exam.title
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={"code": "CONTENT_TYPE_INVALID", "message": "仅支持题目/试卷复核"},
    )


def submit_review(
    db: Session,
    *,
    user: User,
    content_type: str,
    content_id: int,
    note: str | None,
    ip: str | None,
) -> ContentReview:
    """运营提交复核；同一内容存在待复核单时拒绝重复提交。"""
    _, title = _target(db, content_type, content_id)
    pending = db.scalar(
        select(ContentReview).where(
            ContentReview.content_type == content_type,
            ContentReview.content_id == content_id,
            ContentReview.status == "pending",
        )
    )
    if pending is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "REVIEW_PENDING_EXISTS", "message": "该内容已有待复核单"},
        )
    review = ContentReview(
        content_type=content_type,
        content_id=content_id,
        title=title,
        note=note,
        status="pending",
        submitted_by=user.id,
        submitted_at=datetime.utcnow(),
    )
    db.add(review)
    db.flush()
    record_audit(
        db,
        user_id=user.id,
        action="content.review.submit",
        message=f"review={review.id}, type={content_type}, content={content_id}",
        after={"review_id": review.id, "content_type": content_type, "content_id": content_id},
        ip=ip,
        commit=False,
    )
    db.commit()
    db.refresh(review)
    return review


def decide_review(
    db: Session,
    *,
    user: User,
    review_id: int,
    decision: str,
    comment: str | None,
    ip: str | None,
) -> ContentReview:
    """审核员复核：提交人不得自审；驳回必须填写原因。"""
    review = _review_or_404(db, review_id)
    if review.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "REVIEW_STATE_INVALID", "message": "该复核单已处理"},
        )
    if review.submitted_by == user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "REVIEW_SELF_DENIED", "message": "提交人不得复核自己的内容"},
        )
    if decision not in ("approve", "reject"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "DECISION_INVALID", "message": "decision 仅支持 approve/reject"},
        )
    if decision == "reject" and not (comment or "").strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "REVIEW_COMMENT_REQUIRED", "message": "驳回需填写原因"},
        )
    review.status = "approved" if decision == "approve" else "rejected"
    review.reviewed_by = user.id
    review.reviewed_at = datetime.utcnow()
    review.comment = comment
    record_audit(
        db,
        user_id=user.id,
        action="content.review.decide",
        message=f"review={review.id}, decision={decision}",
        after={
            "review_id": review.id,
            "decision": decision,
            "status": review.status,
            "comment": comment,
        },
        ip=ip,
        commit=False,
    )
    db.commit()
    db.refresh(review)
    return review


def publish_review(db: Session, *, user: User, review_id: int, ip: str | None) -> ContentReview:
    """复核通过后由运营发布；复核人不得自行发布（双人复核）。"""
    review = _review_or_404(db, review_id)
    if review.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "REVIEW_NOT_APPROVED", "message": "复核未通过，不能发布"},
        )
    if review.reviewed_by == user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "PUBLISH_SELF_DENIED", "message": "复核人不得自行发布内容"},
        )
    target, _ = _target(db, review.content_type, review.content_id)
    before_status = getattr(target, "status", None)
    target.status = "published"
    review.status = "published"
    review.published_by = user.id
    review.published_at = datetime.utcnow()
    record_audit(
        db,
        user_id=user.id,
        action="content.publish",
        message=f"review={review.id}, type={review.content_type}, content={review.content_id}",
        before={"status": before_status},
        after={"status": "published", "review_id": review.id},
        ip=ip,
        commit=False,
    )
    db.commit()
    db.refresh(review)
    return review


def list_reviews(db: Session, *, status_filter: str | None) -> list[ContentReview]:
    stmt = select(ContentReview)
    if status_filter:
        stmt = stmt.where(ContentReview.status == status_filter)
    stmt = stmt.order_by(ContentReview.id.desc())
    return list(db.scalars(stmt).all())
