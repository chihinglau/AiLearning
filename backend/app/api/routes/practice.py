from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core import cache
from app.db.session import get_db
from app.models.content import KnowledgePoint, Question
from app.models.practice import StudentQuestionRecord
from app.models.user import User
from app.schemas.practice import (
    PracticeRecordOut,
    PracticeStartIn,
    PracticeStartOut,
    PracticeSubmitIn,
    PracticeSubmitOut,
)
from app.services.usage import (
    daily_limit_status,
    limit_exceeded_detail,
    retry_after_seconds,
)

router = APIRouter(prefix="/practice", tags=["同步练习"])


def _normalize(value: Any) -> str:
    """将答案值归一化，兼容选择题选项 key、填空题文本、多选列表。"""
    if isinstance(value, list):
        return "|".join(sorted(_normalize(item) for item in value))
    return str(value).strip().lower()


def grade_answer(question: Question, user_answer: dict[str, Any]) -> bool:
    expected = question.answer.get("value")
    actual = user_answer.get("value")
    if expected is None or actual is None:
        return False
    return _normalize(expected) == _normalize(actual)


@router.post("/start", response_model=PracticeStartOut)
def start_practice(
    payload: PracticeStartIn,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PracticeStartOut:
    # R-04 青少年模式：当日累计学习时长达到上限后停止抽题。
    limit = daily_limit_status(db, current)
    if limit["limited"]:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=limit_exceeded_detail(limit),
            headers={"Retry-After": str(retry_after_seconds(limit))},
        )

    stmt = select(Question)
    kp: Optional[KnowledgePoint] = None
    if payload.chapter_id:
        stmt = stmt.where(Question.chapter_id == payload.chapter_id)
    if payload.knowledge_point_id:
        kp = db.get(KnowledgePoint, payload.knowledge_point_id)
        if kp is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="知识点不存在",
            )
        stmt = stmt.where(Question.subject == kp.subject)
    if payload.subject:
        stmt = stmt.where(Question.subject == payload.subject)

    questions: List[Question] = list(
        db.scalars(stmt.order_by(func.random()).limit(payload.count * 3))
    )
    # 知识点与题目的关联以 tags（知识点名称）为准，SQLite/PostgreSQL 行为一致
    if kp is not None:
        questions = [q for q in questions if kp.name in (q.tags or [])]
    questions = questions[: payload.count]
    if not questions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="该范围暂无可用题目",
        )
    return PracticeStartOut(questions=questions)


@router.post("/submit", response_model=PracticeSubmitOut)
def submit_answer(
    payload: PracticeSubmitIn,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PracticeSubmitOut:
    question = db.get(Question, payload.question_id)
    if question is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="题目不存在")

    is_correct = grade_answer(question, payload.user_answer)
    db.add(
        StudentQuestionRecord(
            user_id=current.id,
            question_id=question.id,
            is_correct=is_correct,
            user_answer=payload.user_answer,
            duration_ms=payload.duration_ms,
        )
    )
    db.commit()
    cache.invalidate_user(current.id)
    return PracticeSubmitOut(
        is_correct=is_correct,
        correct_answer=question.answer,
        analysis=question.analysis,
    )


@router.get("/history", response_model=List[PracticeRecordOut])
def history(
    limit: int = Query(default=20, ge=1, le=100),
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[StudentQuestionRecord]:
    stmt = (
        select(StudentQuestionRecord)
        .where(StudentQuestionRecord.user_id == current.id)
        .order_by(StudentQuestionRecord.attempted_at.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt))
