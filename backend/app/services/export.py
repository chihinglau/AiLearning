"""P2-08 合规数据导出与用途登记（D-05 §7、D-03 §8）。

导出统一脱敏（手机号掩码）、按用途登记审计，并对超量数据做显式截断标记。
"""

from collections.abc import Sequence
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.core.permissions import SCOPE_ALL, SCOPE_CHILD, SCOPE_SCHOOL, SCOPE_SELF
from app.core.scope import mask_phone
from app.models.exam import Exam, ExamAttempt
from app.models.practice import (
    KpStudyState,
    MasteryScore,
    PracticeSession,
    StudentQuestionRecord,
    WrongQuestion,
)
from app.models.textbook import TextbookBinding
from app.models.user import GradeHistory, ParentChildBinding, User

# 单段最大导出条数；超出时截断并在 meta 中标记，避免响应体过大
SECTION_LIMIT = 1000

# 用途登记：code → 中文说明（D-05 §7「复制/导出」与 §6.1 审计要求）
EXPORT_PURPOSES = {
    "self_copy": "个人数据副本",
    "guardian_review": "监护人查阅",
    "school_management": "学校教学管理",
    "audit_investigation": "安全审计调查",
    "regulatory_request": "监管依法调取",
}

# 操作身份（数据范围）→ 允许登记的用途
PURPOSE_BY_SCOPE = {
    SCOPE_SELF: ("self_copy",),
    SCOPE_CHILD: ("guardian_review",),
    SCOPE_ALL: ("school_management", "audit_investigation", "regulatory_request"),
    SCOPE_SCHOOL: ("school_management", "audit_investigation", "regulatory_request"),
}


def resolve_purpose(purpose: str | None, scope: str) -> tuple[str, str]:
    """校验并归一化导出用途；不合格时抛 422。"""
    code = (purpose or "").strip()
    if not code:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "PURPOSE_REQUIRED", "message": "请填写数据导出用途"},
        )
    if code not in EXPORT_PURPOSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "PURPOSE_INVALID",
                "message": "用途无效，可选值：" + "、".join(EXPORT_PURPOSES),
            },
        )
    allowed = PURPOSE_BY_SCOPE.get(scope, ())
    if code not in allowed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "PURPOSE_NOT_ALLOWED", "message": "该用途与当前操作身份不匹配"},
        )
    return code, EXPORT_PURPOSES[code]


def _limited(rows: Sequence[Any]) -> tuple[list[Any], bool]:
    """超量截断：入参应已按 SECTION_LIMIT + 1 查询。"""
    values = list(rows)
    if len(values) > SECTION_LIMIT:
        return values[:SECTION_LIMIT], True
    return values, False


def _stats(db: Session, student_id: int) -> dict[str, Any]:
    answered = db.scalar(
        select(func.count())
        .select_from(StudentQuestionRecord)
        .where(StudentQuestionRecord.user_id == student_id)
    )
    correct = db.scalar(
        select(func.count())
        .select_from(StudentQuestionRecord)
        .where(
            StudentQuestionRecord.user_id == student_id,
            StudentQuestionRecord.is_correct.is_(True),
        )
    )
    wrong_active = db.scalar(
        select(func.count())
        .select_from(WrongQuestion)
        .where(WrongQuestion.user_id == student_id, WrongQuestion.status == "active")
    )
    mastery = db.scalar(
        select(func.count())
        .select_from(MasteryScore)
        .where(MasteryScore.user_id == student_id)
    )
    attempts = db.scalar(
        select(func.count()).select_from(ExamAttempt).where(ExamAttempt.user_id == student_id)
    )
    answered_total = int(answered or 0)
    correct_total = int(correct or 0)
    return {
        "answered_total": answered_total,
        "correct_total": correct_total,
        "correct_rate": round(correct_total / answered_total, 4) if answered_total else 0.0,
        "wrong_active": int(wrong_active or 0),
        "mastery_count": int(mastery or 0),
        "exam_attempt_total": int(attempts or 0),
    }


def build_export(db: Session, student: User) -> tuple[dict[str, Any], bool]:
    """组装学生个人数据副本（已脱敏）；返回 (数据段, 是否发生截断)。"""
    truncated = False

    profile = {
        "id": student.id,
        "nickname": student.nickname,
        "role": student.role,
        "stage": student.stage,
        "grade": student.grade,
        "grade_group": student.grade_group,
        "region": student.region,
        "semester": student.semester,
        "enrollment_year": student.enrollment_year,
        "school_id": student.school_id,
        "is_child": student.is_child,
        "teen_mode": student.teen_mode,
        "daily_limit_minutes": student.daily_limit_minutes,
        "phone": mask_phone(student.phone),
        "created_at": student.created_at,
        "grade_updated_at": student.grade_updated_at,
    }

    grade_histories, hit = _limited(
        db.scalars(
            select(GradeHistory)
            .where(GradeHistory.user_id == student.id)
            .order_by(desc(GradeHistory.created_at))
            .limit(SECTION_LIMIT + 1)
        )
    )
    truncated = truncated or hit

    guardian_bindings, hit = _limited(
        db.scalars(
            select(ParentChildBinding)
            .where(ParentChildBinding.child_id == student.id)
            .order_by(desc(ParentChildBinding.created_at))
            .limit(SECTION_LIMIT + 1)
        )
    )
    truncated = truncated or hit

    bindings, hit = _limited(
        db.scalars(
            select(TextbookBinding)
            .where(TextbookBinding.user_id == student.id)
            .order_by(desc(TextbookBinding.bound_at))
            .limit(SECTION_LIMIT + 1)
        )
    )
    truncated = truncated or hit

    records, hit = _limited(
        db.scalars(
            select(StudentQuestionRecord)
            .where(StudentQuestionRecord.user_id == student.id)
            .order_by(desc(StudentQuestionRecord.attempted_at))
            .limit(SECTION_LIMIT + 1)
        )
    )
    truncated = truncated or hit

    wrong_questions, hit = _limited(
        db.scalars(
            select(WrongQuestion)
            .where(WrongQuestion.user_id == student.id)
            .order_by(desc(WrongQuestion.last_wrong_at))
            .limit(SECTION_LIMIT + 1)
        )
    )
    truncated = truncated or hit

    mastery_scores, hit = _limited(
        db.scalars(
            select(MasteryScore)
            .where(MasteryScore.user_id == student.id)
            .order_by(desc(MasteryScore.score))
            .limit(SECTION_LIMIT + 1)
        )
    )
    truncated = truncated or hit

    kp_states, hit = _limited(
        db.scalars(
            select(KpStudyState)
            .where(KpStudyState.user_id == student.id)
            .order_by(desc(KpStudyState.updated_at))
            .limit(SECTION_LIMIT + 1)
        )
    )
    truncated = truncated or hit

    sessions, hit = _limited(
        db.scalars(
            select(PracticeSession)
            .where(PracticeSession.user_id == student.id)
            .order_by(desc(PracticeSession.started_at))
            .limit(SECTION_LIMIT + 1)
        )
    )
    truncated = truncated or hit

    attempt_rows, hit = _limited(
        db.execute(
            select(ExamAttempt, Exam)
            .join(Exam, Exam.id == ExamAttempt.exam_id)
            .where(ExamAttempt.user_id == student.id)
            .order_by(desc(ExamAttempt.started_at))
            .limit(SECTION_LIMIT + 1)
        ).all()
    )
    truncated = truncated or hit

    bundle = {
        "profile": profile,
        "learning_stats": _stats(db, student.id),
        "grade_histories": [
            {
                "from_grade": row.from_grade,
                "to_grade": row.to_grade,
                "school_year": row.school_year,
                "source": row.source,
                "created_at": row.created_at,
            }
            for row in grade_histories
        ],
        "guardian_bindings": [
            {
                "parent_id": row.parent_id,
                "relation": row.relation,
                "status": row.status,
                "consent_at": row.consent_at,
                "created_at": row.created_at,
            }
            for row in guardian_bindings
        ],
        "textbook_bindings": [
            {
                "subject": row.subject,
                "textbook_id": row.textbook_id,
                "semester": row.semester,
                "source": row.source,
                "is_primary": row.is_primary,
                "status": row.status,
                "bound_at": row.bound_at,
            }
            for row in bindings
        ],
        "question_records": [
            {
                "question_id": row.question_id,
                "is_correct": row.is_correct,
                "user_answer": row.user_answer,
                "wrong_reason": row.wrong_reason,
                "source": row.source,
                "attempted_at": row.attempted_at,
            }
            for row in records
        ],
        "wrong_questions": [
            {
                "question_id": row.question_id,
                "wrong_count": row.wrong_count,
                "correct_streak": row.correct_streak,
                "status": row.status,
                "wrong_reason": row.wrong_reason,
                "next_review_at": row.next_review_at,
                "last_wrong_at": row.last_wrong_at,
            }
            for row in wrong_questions
        ],
        "mastery_scores": [
            {
                "knowledge_point_id": row.knowledge_point_id,
                "score": row.score,
                "confidence": row.confidence,
                "updated_at": row.updated_at,
            }
            for row in mastery_scores
        ],
        "kp_study_states": [
            {
                "knowledge_point_id": row.knowledge_point_id,
                "state": row.state,
                "evidence_count": row.evidence_count,
                "updated_at": row.updated_at,
            }
            for row in kp_states
        ],
        "practice_sessions": [
            {
                "id": row.id,
                "mode": row.mode,
                "scope_type": row.scope_type,
                "total_count": row.total_count,
                "answered_count": row.answered_count,
                "correct_count": row.correct_count,
                "started_at": row.started_at,
                "finished_at": row.finished_at,
            }
            for row in sessions
        ],
        "exam_attempts": [
            {
                "id": attempt.id,
                "exam_id": attempt.exam_id,
                "exam_title": exam.title,
                "subject": exam.subject,
                "status": attempt.status,
                "started_at": attempt.started_at,
                "submitted_at": attempt.submitted_at,
                "objective_score": attempt.objective_score,
                "subjective_score": attempt.subjective_score,
                "total_score": attempt.total_score,
            }
            for attempt, exam in attempt_rows
        ],
    }
    return bundle, truncated


def section_counts(bundle: dict[str, Any]) -> dict[str, int]:
    """各数据段条数（写入用途登记审计）。"""
    counts: dict[str, int] = {}
    for key, value in bundle.items():
        if isinstance(value, list):
            counts[key] = len(value)
        elif key == "learning_stats":
            counts["answered_total"] = int(value.get("answered_total", 0))
    return counts
