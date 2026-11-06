"""P2-06 AI 讲解与错题归因辅助接口（LLM 接入 + Prompt 安全 + 规则兜底）。"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_student_access
from app.core.config import settings
from app.core.scope import StudentAccess
from app.db.session import get_db
from app.models.content import KnowledgePoint, Question
from app.models.practice import StudentQuestionRecord, WrongQuestion
from app.models.user import User
from app.schemas.ai import (
    AIDiagnoseIn,
    AIDiagnoseOut,
    AIExplainIn,
    AIExplainOut,
)
from app.services import ai as ai_service
from app.services.audit import record_audit

router = APIRouter(prefix="/ai", tags=["AI 讲解"])


def _target_student(access: StudentAccess) -> int:
    if access.student_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "STUDENT_ID_REQUIRED", "message": "请选择要查看的学生"},
        )
    return access.student_id


def _question_or_404(db: Session, question_id: int) -> Question:
    question = db.get(Question, question_id)
    if question is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="题目不存在")
    return question


def _kp_name(db: Session, question: Question) -> Optional[str]:
    if question.knowledge_point_id is None:
        return None
    kp = db.get(KnowledgePoint, question.knowledge_point_id)
    return kp.name if kp is not None else None


def _latest_record(
    db: Session, *, user_id: int, question_id: int
) -> Optional[StudentQuestionRecord]:
    return db.scalar(
        select(StudentQuestionRecord)
        .where(
            StudentQuestionRecord.user_id == user_id,
            StudentQuestionRecord.question_id == question_id,
        )
        .order_by(
            StudentQuestionRecord.attempted_at.desc(),
            StudentQuestionRecord.id.desc(),
        )
        .limit(1)
    )


def _consume(user_id: int) -> int:
    try:
        return ai_service.consume_quota(user_id, settings.ai_rate_limit_per_hour)
    except ai_service.QuotaExceededError as error:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "AI_RATE_LIMITED",
                "message": "AI 讲解次数已用完，请稍后再试",
            },
        ) from error


@router.post("/explain", response_model=AIExplainOut)
def explain_question(
    payload: AIExplainIn,
    access: StudentAccess = Depends(
        require_student_access(("learn:wrong:self", "learn:exam:report:self"))
    ),
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AIExplainOut:
    target = _target_student(access)
    question = _question_or_404(db, payload.question_id)

    wrong: Optional[WrongQuestion] = None
    if payload.wrong_question_id is not None:
        wrong = db.get(WrongQuestion, payload.wrong_question_id)
        if wrong is None or wrong.user_id != target or wrong.question_id != question.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="错题不存在"
            )

    record = _latest_record(db, user_id=target, question_id=question.id)
    if wrong is None and record is None:
        # 未作答不允许查看讲解，避免变相泄题
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "AI_EXPLAIN_LOCKED",
                "message": "请先完成作答后再查看 AI 讲解",
            },
        )

    user_answer = record.user_answer if record is not None else None
    remaining = _consume(target)
    result = ai_service.AIService().explain(
        question,
        user_answer=user_answer,
        kp_name=_kp_name(db, question),
        focus=payload.focus,
    )
    record_audit(
        db,
        user_id=current.id,
        action="ai.explain",
        message=f"question={question.id}, target={target}, provider={result.provider}",
    )
    return AIExplainOut(
        question_id=result.question_id,
        provider=result.provider,
        focus=payload.focus,
        explanation=result.explanation,
        steps=result.steps,
        cautions=result.cautions,
        remaining_quota=remaining,
    )


@router.post("/diagnose", response_model=AIDiagnoseOut)
def diagnose_wrong_question(
    payload: AIDiagnoseIn,
    access: StudentAccess = Depends(require_student_access("learn:wrong:self")),
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AIDiagnoseOut:
    target = _target_student(access)
    wrong = db.get(WrongQuestion, payload.wrong_question_id)
    if wrong is None or wrong.user_id != target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="错题不存在")
    question = _question_or_404(db, wrong.question_id)
    record = _latest_record(db, user_id=target, question_id=question.id)
    user_answer = record.user_answer if record is not None else None

    remaining = _consume(target)
    result = ai_service.AIService().diagnose(
        question,
        wrong,
        user_answer=user_answer,
        kp_name=_kp_name(db, question),
    )
    record_audit(
        db,
        user_id=current.id,
        action="ai.diagnose",
        message=f"wrong={wrong.id}, target={target}, provider={result.provider}",
    )
    return AIDiagnoseOut(
        wrong_id=result.wrong_id,
        question_id=result.question_id,
        provider=result.provider,
        reason=result.reason,
        reason_label=result.reason_label,
        confidence=result.confidence,
        explanation=result.explanation,
        suggestions=result.suggestions,
        remaining_quota=remaining,
    )
