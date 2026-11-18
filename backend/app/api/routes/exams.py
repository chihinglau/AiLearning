"""考试闭环接口（P0-28）：考试列表/详情、开始与续答、防抖保存、幂等交卷与客观自动判。"""

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Response, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.core import cache
from app.core.config import settings
from app.db.session import get_db
from app.models.assignment import Assignment
from app.models.content import KnowledgePoint, Question
from app.models.exam import Exam, ExamAnswer, ExamAttempt, ExamBlueprint, ListeningPlay
from app.models.org import ClassMember, SchoolClass
from app.models.practice import StudentQuestionRecord
from app.models.user import AuditLog, User
from app.schemas.content import QuestionPublic
from app.schemas.exam import (
    ExamAbilityStatOut,
    ExamAnswerOut,
    ExamAnswerSaveIn,
    ExamAttemptBriefOut,
    ExamAttemptHistoryOut,
    ExamAttemptOut,
    ExamAttemptStartIn,
    ExamClassAverageOut,
    ExamDetailOut,
    ExamGenerateIn,
    ExamGenerateOut,
    ExamKpStatOut,
    ExamNextActionOut,
    ExamQuestionOut,
    ExamReportOut,
    ExamReviewActionOut,
    ExamReviewIn,
    ExamReviewNoteIn,
    ExamReviewOut,
    ExamSaveIn,
    ExamSaveOut,
    ExamSelfAssessIn,
    ExamSelfAssessOut,
    ExamSubjectiveItemOut,
    ExamSubmitIn,
    ExamSubmitOut,
    ExamSummaryOut,
    ExamSampleReviewIn,
    ExamSamplingItemOut,
    ExamSamplingOut,
    ExamTrendOut,
    ExamTrendPointOut,
    ExamTypeStatOut,
    ExamWrongItemOut,
    MockExamAssignIn,
    MockExamAssignOut,
    PastPaperDetailOut,
    PastPaperFiltersOut,
    PastPaperOut,
)
from app.services import learning as engine
from app.services import wrong_reason as wrong_reason_service
from app.services.assignment import class_authorized
from app.services.audit import record_audit
from app.services.exam_paper import generate_paper, resolve_scope_chapters
from app.services.exam_paper_docs import (
    build_spec_table,
    recent_question_ids,
    render_answer_sheet_html,
    sample_exams,
)
from app.services.recommendation import student_visible_exam_clauses
from app.services.usage import (
    daily_limit_status,
    limit_exceeded_detail,
    retry_after_seconds,
)

router = APIRouter(prefix="/exams", tags=["考试"])

# 客观题：交卷即判；其余题型（calc/answer/listen 等）一期进入待批/自评
OBJECTIVE_TYPES = {"choice", "multiple", "fill", "judge"}

# PG-04（2026-11-16 PM 裁决）：作废按考试类型区分的回流权重系数。
# 掌握度回流统一按 1.0 计入，避免「单元测 0.8 / 期中 0.6 / 期末 0.5」这类无依据的衰减。
EXAM_TYPE_WEIGHT: dict[str, float] = {}
DEFAULT_EXAM_WEIGHT = 1.0

# 能力维度（D-04 §8.5）：默认按题型映射，学科可覆盖
ABILITY_LABELS = {
    "understand": "理解",
    "calculate": "计算",
    "apply": "应用",
    "analyze": "分析",
}
ABILITY_ORDER = ("understand", "calculate", "apply", "analyze")
ABILITY_BY_Q_TYPE = {
    "choice": "understand",
    "judge": "understand",
    "fill": "calculate",
    "multiple": "analyze",
    "calc": "apply",
    "answer": "analyze",
    "listen": "understand",
}
SUBJECT_ABILITY_OVERRIDES: dict[str, dict[str, str]] = {
    # 英语更关注语言应用；语文填空侧重理解
    "english": {"fill": "apply", "listen": "understand"},
    "chinese": {"fill": "understand"},
}


def _ability_of(subject: str, q_type: str) -> str:
    override = SUBJECT_ABILITY_OVERRIDES.get(subject, {})
    return override.get(q_type) or ABILITY_BY_Q_TYPE.get(q_type, "understand")


# ---------------------------------------------------------------------------
# 试卷解析
# ---------------------------------------------------------------------------


def _paper_items(exam: Exam) -> list[dict[str, Any]]:
    """把 exams.questions JSON 归一化为 [{question_id, score, section...}]。

    兼容三种历史形态：纯题目 id、{"question_id": ..}、蓝图生成的完整条目。
    """
    raw = list(exam.questions or [])
    default_score = float(exam.total_score) / len(raw) if raw else 0.0
    items: list[dict[str, Any]] = []
    for order, entry in enumerate(raw):
        if isinstance(entry, dict):
            question_id = entry.get("question_id", entry.get("id"))
            score = entry.get("score", default_score)
            section_index = int(entry.get("section_index", 0))
            section_name = entry.get("section_name")
        else:
            question_id = entry
            score = default_score
            section_index = 0
            section_name = None
        if question_id is None:
            continue
        items.append(
            {
                "question_id": int(question_id),
                "score": float(score),
                "section_index": section_index,
                "section_name": section_name,
                "order_index": order,
            }
        )
    return items


def _question_map(db: Session, question_ids: list[int]) -> dict[int, Question]:
    if not question_ids:
        return {}
    return {
        q.id: q
        for q in db.scalars(select(Question).where(Question.id.in_(question_ids)))
    }


def _exam_or_404(db: Session, exam_id: int) -> Exam:
    exam = db.get(Exam, exam_id)
    if exam is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="试卷不存在")
    return exam


def _window_state(exam: Exam, now: datetime) -> str:
    """考试窗口状态：未配置 / 未开始 / 开放中 / 已结束。"""
    if exam.window_start is None and exam.window_end is None:
        return "unscheduled"
    if exam.window_start is not None and now < exam.window_start:
        return "scheduled"
    if exam.window_end is not None and now >= exam.window_end:
        return "closed"
    return "open"


def _ensure_takeable(exam: Exam, user: User, db: Optional[Session] = None) -> None:
    """学生只能参加本年级已发布、且处于开放窗口内的试卷。

    班级作业卷额外校验班级成员关系，避免同年级其他班学生按 id 直接进入。
    """
    if user.role != "student":
        return
    if exam.status != "published":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="试卷不存在")
    if user.grade and exam.grade != user.grade:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "GRADE_MISMATCH", "message": "试卷年级与当前年级不一致"},
        )
    state = _window_state(exam, datetime.utcnow())
    if state == "scheduled":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "EXAM_WINDOW_NOT_OPEN", "message": "考试尚未开放"},
        )
    if state == "closed":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "EXAM_WINDOW_CLOSED", "message": "考试已结束"},
        )
    if exam.source == "assignment" and db is not None:
        assignment = db.scalar(
            select(Assignment).where(Assignment.exam_id == exam.id)
        )
        if assignment is not None and db.scalar(
            select(ClassMember).where(
                ClassMember.class_id == assignment.class_id,
                ClassMember.student_id == user.id,
            )
        ) is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "ASSIGNMENT_NOT_MEMBER",
                    "message": "仅本班学生可参加该作业",
                },
            )
    # 班级同卷模考：仅本班学生可进入，保证全班共用同一张卷
    if exam.class_id is not None and db is not None:
        if db.scalar(
            select(ClassMember).where(
                ClassMember.class_id == exam.class_id,
                ClassMember.student_id == user.id,
            )
        ) is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "EXAM_NOT_MEMBER",
                    "message": "仅本班学生可参加该模考",
                },
            )


def _license_note_for(exam: Exam, viewer: Optional[User]) -> Optional[str]:
    """授权说明属 R-07 台账内部信息（评审 R2-06 遗留项）：仅管理侧可见。

    学生端只保留 `source_name`（来源标签），不接收授权条款原文，避免把台账
    细节当作对外授权凭证展示。
    """
    if viewer is not None and viewer.role == "student":
        return None
    return exam.license_note


def _detail_out(
    db: Session,
    exam: Exam,
    now: Optional[datetime] = None,
    viewer: Optional[User] = None,
) -> ExamDetailOut:
    items = _paper_items(exam)
    questions = _question_map(db, [item["question_id"] for item in items])
    out: list[ExamQuestionOut] = []
    for item in items:
        question = questions.get(item["question_id"])
        if question is None:
            continue
        out.append(
            ExamQuestionOut(
                **QuestionPublic.model_validate(question).model_dump(),
                score=item["score"],
                section_index=item["section_index"],
                section_name=item["section_name"],
                order_index=item["order_index"],
            )
        )
    return ExamDetailOut(
        id=exam.id,
        title=exam.title,
        subject=exam.subject,
        grade=exam.grade,
        year=exam.year,
        source=exam.source,
        exam_type=exam.exam_type,
        total_score=exam.total_score,
        time_limit_min=exam.time_limit_min,
        status=exam.status,
        question_count=len(out),
        window_start=exam.window_start,
        window_end=exam.window_end,
        window_state=_window_state(exam, now or datetime.utcnow()),
        region=exam.region,
        is_past_paper=bool(exam.is_past_paper),
        class_id=exam.class_id,
        source_name=exam.source_name,
        license_note=_license_note_for(exam, viewer),
        adapted_from=exam.adapted_from,
        questions=out,
    )


# ---------------------------------------------------------------------------
# 作答与计时
# ---------------------------------------------------------------------------


def _remaining_seconds(exam: Exam, attempt: ExamAttempt, now: datetime) -> int:
    if attempt.status != "in_progress":
        return 0
    started = attempt.started_at or now
    elapsed = int((now - started).total_seconds())
    return max(0, int(exam.time_limit_min or 0) * 60 - elapsed)


def _attempt_or_404(db: Session, attempt_id: int, user: User) -> ExamAttempt:
    attempt = db.get(ExamAttempt, attempt_id)
    if attempt is None or attempt.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="考试作答不存在",
        )
    return attempt


def _answers_out(
    db: Session,
    attempt: ExamAttempt,
    paper: list[dict[str, Any]],
) -> list[ExamAnswerOut]:
    rows = {
        row.question_id: row
        for row in db.scalars(
            select(ExamAnswer).where(ExamAnswer.attempt_id == attempt.id)
        )
    }
    result: list[ExamAnswerOut] = []
    for item in paper:
        row = rows.get(item["question_id"])
        if row is None:
            continue
        result.append(
            ExamAnswerOut(
                question_id=row.question_id,
                user_answer=row.user_answer,
                is_correct=row.is_correct,
                score=row.score,
                self_score=row.self_score,
                updated_at=row.updated_at,
            )
        )
    return result


def _attempt_out(
    db: Session,
    exam: Exam,
    attempt: ExamAttempt,
    now: datetime,
    viewer: Optional[User] = None,
) -> ExamAttemptOut:
    paper = _paper_items(exam)
    answers = _answers_out(db, attempt, paper)
    answered = {
        answer.question_id for answer in answers if answer.user_answer is not None
    }
    next_index = next(
        (i for i, item in enumerate(paper) if item["question_id"] not in answered),
        len(paper),
    )
    return ExamAttemptOut(
        id=attempt.id,
        exam_id=attempt.exam_id,
        status=attempt.status,
        seed=attempt.seed,
        started_at=attempt.started_at,
        submitted_at=attempt.submitted_at,
        duration_ms=attempt.duration_ms,
        objective_score=attempt.objective_score,
        subjective_score=attempt.subjective_score,
        total_score=attempt.total_score,
        submit_token=attempt.submit_token,
        remaining_seconds=_remaining_seconds(exam, attempt, now),
        server_now=now,
        exam=_detail_out(db, exam, now, viewer),
        answers=answers,
        next_index=next_index,
    )


# ---------------------------------------------------------------------------
# 列表与详情
# ---------------------------------------------------------------------------


@router.get("", response_model=list[ExamSummaryOut])
def list_exams(
    response: Response,
    exam_type: Optional[str] = Query(default=None, alias="type"),
    status_filter: Optional[str] = Query(
        default=None, alias="status", pattern=r"^(available|in_progress|completed)$"
    ),
    subject: Optional[str] = Query(default=None, max_length=20),
    window_state: Optional[str] = Query(
        default=None, pattern=r"^(open|scheduled|closed|unscheduled)$"
    ),
    q: Optional[str] = Query(default=None, max_length=80),
    page: Optional[int] = Query(default=None, ge=1),
    page_size: Optional[int] = Query(default=None, ge=1, le=100),
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ExamSummaryOut]:
    """考试中心列表（D-09 §4.3）：新增筛选均为可见性谓词之后的 AND 收窄。

    评审 R2-06（2026-11-14）：作答状态与窗口状态改为 SQL 条件后再取数与计数，
    修正旧实现「先按 hard_limit 截断、后在内存里过滤」导致的漏卷与总数失真；
    不带 page 时仍保持 CR-003 验收态（最多 100 条），响应体保持数组。
    """
    stmt = select(Exam)
    # 班级作业卷通过 /api/assignments 暴露，避免在通用考试列表中重复出现
    stmt = stmt.where(Exam.source != "assignment")
    if current.role == "student":
        # 与 /api/learn/home.pending_exams 共用同一可见性谓词（D-04 §8.7.1）
        stmt = stmt.where(*student_visible_exam_clauses(current))
    if exam_type:
        stmt = stmt.where(Exam.exam_type == exam_type)
    if subject:
        stmt = stmt.where(Exam.subject == subject)
    if q and q.strip():
        stmt = stmt.where(func.lower(Exam.title).contains(q.strip().lower()))

    now = datetime.utcnow()
    my_attempt = select(ExamAttempt.id).where(
        ExamAttempt.exam_id == Exam.id,
        ExamAttempt.user_id == current.id,
    )
    if status_filter == "available":
        stmt = stmt.where(~my_attempt.exists())
    elif status_filter == "in_progress":
        stmt = stmt.where(
            my_attempt.where(ExamAttempt.status == "in_progress").exists()
        )
    elif status_filter == "completed":
        stmt = stmt.where(my_attempt.where(ExamAttempt.status != "in_progress").exists())
    if window_state == "unscheduled":
        stmt = stmt.where(Exam.window_start.is_(None), Exam.window_end.is_(None))
    elif window_state == "scheduled":
        stmt = stmt.where(Exam.window_start.is_not(None), Exam.window_start > now)
    elif window_state == "closed":
        stmt = stmt.where(Exam.window_end.is_not(None), Exam.window_end <= now)
    elif window_state == "open":
        stmt = stmt.where(
            or_(
                and_(
                    Exam.window_start.is_(None),
                    Exam.window_end.is_not(None),
                    Exam.window_end > now,
                ),
                and_(
                    Exam.window_start.is_not(None),
                    Exam.window_start <= now,
                    or_(Exam.window_end.is_(None), Exam.window_end > now),
                ),
            )
        )

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    response.headers["X-Total-Count"] = str(total)
    if page is not None:
        size = page_size or 20
        stmt = stmt.offset((page - 1) * size).limit(size)
    else:
        stmt = stmt.limit(100)
    exams = list(db.scalars(stmt.order_by(Exam.id.desc())))
    if not exams:
        return []

    attempts = list(
        db.scalars(
            select(ExamAttempt)
            .where(
                ExamAttempt.user_id == current.id,
                ExamAttempt.exam_id.in_([exam.id for exam in exams]),
            )
            .order_by(ExamAttempt.id)
        )
    )
    latest: dict[int, ExamAttempt] = {}
    attempt_counts: dict[int, int] = {}
    for attempt in attempts:
        latest[attempt.exam_id] = attempt
        attempt_counts[attempt.exam_id] = attempt_counts.get(attempt.exam_id, 0) + 1

    now = datetime.utcnow()
    result: list[ExamSummaryOut] = []
    for exam in exams:
        attempt = latest.get(exam.id)
        if attempt is not None and attempt.status == "in_progress":
            category = "in_progress"
        elif attempt is not None:
            category = "completed"
        else:
            category = "available"
        state = _window_state(exam, now)
        brief = None
        if attempt is not None:
            brief = ExamAttemptBriefOut(
                id=attempt.id,
                status=attempt.status,
                seed=attempt.seed,
                started_at=attempt.started_at,
                submitted_at=attempt.submitted_at,
                duration_ms=attempt.duration_ms,
                objective_score=attempt.objective_score,
                subjective_score=attempt.subjective_score,
                total_score=attempt.total_score,
                remaining_seconds=_remaining_seconds(exam, attempt, now),
            )
        result.append(
            ExamSummaryOut(
                id=exam.id,
                title=exam.title,
                subject=exam.subject,
                grade=exam.grade,
                year=exam.year,
                exam_type=exam.exam_type,
                total_score=exam.total_score,
                time_limit_min=exam.time_limit_min,
                question_count=len(_paper_items(exam)),
                category=category,
                window_start=exam.window_start,
                window_end=exam.window_end,
                window_state=state,
                region=exam.region,
                is_past_paper=bool(exam.is_past_paper),
                class_id=exam.class_id,
                attempt=brief,
                source_name=exam.source_name,
                license_note=_license_note_for(exam, current),
                adapted_from=exam.adapted_from,
                attempt_count=attempt_counts.get(exam.id, 0),
            )
        )
    return result


@router.get("/blueprints", response_model=list[dict[str, Any]])
def list_blueprints(
    current: User = Depends(require_permission("content:exam:write")),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """App 考试入库表单的可选蓝图（D-04 §8.7.3）。

    必须注册在 /{exam_id} 之前，否则路径会被当作 exam_id 解析。
    """
    rows = db.scalars(
        select(ExamBlueprint)
        .where(ExamBlueprint.is_active.is_(True))
        .order_by(ExamBlueprint.id)
    )
    return [
        {
            "code": row.code,
            "name": row.name,
            "subject": row.subject,
            "grade": row.grade,
            "exam_type": row.exam_type,
            "total_score": row.total_score,
            "time_limit_min": row.time_limit_min,
        }
        for row in rows
    ]


@router.get("/past-papers/filters", response_model=PastPaperFiltersOut)
def past_paper_filters(
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PastPaperFiltersOut:
    """真题库可用筛选项（D-09 §5.3）：避免前端硬编码年份/学科/地区。"""
    stmt = select(
        Exam.year, Exam.subject, Exam.region, Exam.grade, Exam.exam_type
    ).where(
        Exam.status == "published",
        Exam.is_past_paper.is_(True),
        Exam.class_id.is_(None),
    )
    if current.role == "student" and current.grade:
        stmt = stmt.where(Exam.grade == current.grade)
    rows = db.execute(stmt).all()
    return PastPaperFiltersOut(
        years=sorted({int(row[0]) for row in rows if row[0] is not None}, reverse=True),
        subjects=sorted({str(row[1]) for row in rows if row[1]}),
        regions=sorted({str(row[2]) for row in rows if row[2]}),
        grades=sorted({int(row[3]) for row in rows if row[3] is not None}),
        exam_types=sorted({str(row[4]) for row in rows if row[4]}),
    )


@router.get("/attempts", response_model=list[ExamAttemptHistoryOut])
def list_attempt_history(
    response: Response,
    exam_id: Optional[int] = Query(default=None, ge=1),
    page: Optional[int] = Query(default=None, ge=1),
    page_size: Optional[int] = Query(default=None, ge=1, le=100),
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ExamAttemptHistoryOut]:
    """本人历次考试作答（D-09 §4.7）。必须注册在 /{exam_id} 之前。

    评审 §9.5-1：历史作答改为服务端分页，X-Total-Count 为分页前真实总数；
    不带 page 时保持旧行为（最多 200 条）。
    """
    stmt = (
        select(ExamAttempt, Exam)
        .join(Exam, Exam.id == ExamAttempt.exam_id)
        .where(ExamAttempt.user_id == current.id)
    )
    if exam_id is not None:
        stmt = stmt.where(ExamAttempt.exam_id == exam_id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    response.headers["X-Total-Count"] = str(total)
    if page is not None:
        size = page_size or 20
        stmt = stmt.offset((page - 1) * size).limit(size)
    else:
        stmt = stmt.limit(200)
    rows = list(db.execute(stmt.order_by(ExamAttempt.id.desc())))
    return [
        ExamAttemptHistoryOut(
            attempt_id=attempt.id,
            exam_id=exam.id,
            exam_title=exam.title,
            exam_type=exam.exam_type,
            status=attempt.status,
            total_score=attempt.total_score,
            full_score=exam.total_score,
            started_at=attempt.started_at,
            submitted_at=attempt.submitted_at,
            duration_ms=attempt.duration_ms,
        )
        for attempt, exam in rows
    ]


# ---------------------------------------------------------------------------
# 真题审核发布流（D-09 §5.7 P2 / CR-005）：仅 is_past_paper=true 生效。
# 静态路径 /reviews 必须注册在 /{exam_id} 之前；普通卷不进入本流程。
# ---------------------------------------------------------------------------

EXAM_REVIEW_STATES = ("draft", "pending_review", "published", "offline")


def _reviewable_or_404(db: Session, exam_id: int) -> Exam:
    exam = db.get(Exam, exam_id)
    if exam is None or not exam.is_past_paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "EXAM_REVIEW_NOT_FOUND", "message": "待复核真题不存在"},
        )
    # 评审 §9.5-2：班级派发副本（class_id 非空）是模板卷的下游产物，
    # 复核对象应始终是模板卷本身，避免同一张真题在多个班级副本上重复走审核流。
    if exam.class_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "EXAM_CLASS_COPY_NOT_REVIEWABLE",
                "message": "班级派发的真题副本不进入审核队列，请操作其模板卷",
            },
        )
    return exam


def _require_exam_source(exam: Exam) -> None:
    """真题来源卡口：缺来源不得提交复核、更不得发布（R-07 台账）。"""
    if not (exam.source_name and exam.source_name.strip()):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "EXAM_SOURCE_REQUIRED",
                "message": "历年真题必须补录来源名称后才可提交复核或发布",
            },
        )


@router.get("/reviews", response_model=list[ExamReviewOut])
def list_exam_reviews(
    response: Response,
    review_status: str = Query(default="pending_review"),
    page: Optional[int] = Query(default=None, ge=1),
    page_size: Optional[int] = Query(default=None, ge=1, le=100),
    current: User = Depends(require_permission("content:review:decide")),
    db: Session = Depends(get_db),
) -> list[ExamReviewOut]:
    """审核队列：默认只列待复核真题，可按状态查看历史（不含答案）。

    评审 §9.5-1：队列改为服务端分页，X-Total-Count 为分页前真实总数；
    不带 page 时保持旧行为（最多 200 条）。
    """
    if review_status not in EXAM_REVIEW_STATES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "EXAM_REVIEW_STATUS_INVALID",
                "message": "审核状态不合法",
            },
        )
    stmt = select(Exam).where(
        Exam.is_past_paper.is_(True), Exam.status == review_status
    )
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    response.headers["X-Total-Count"] = str(total)
    if page is not None:
        size = page_size or 20
        stmt = stmt.offset((page - 1) * size).limit(size)
    else:
        stmt = stmt.limit(200)
    rows = db.scalars(stmt.order_by(Exam.id.desc())).unique().all()
    return [
        ExamReviewOut(
            id=exam.id,
            title=exam.title,
            subject=exam.subject,
            grade=exam.grade,
            year=exam.year,
            region=exam.region,
            status=exam.status,
            is_past_paper=exam.is_past_paper,
            source_name=exam.source_name,
            license_note=exam.license_note,
            adapted_from=exam.adapted_from,
            reviewed_by=exam.reviewed_by,
            reviewed_at=exam.reviewed_at,
            published_by=exam.published_by,
            published_at=exam.published_at,
            review_note=exam.review_note,
            created_at=exam.created_at,
        )
        for exam in rows
    ]


@router.get("/review-sampling", response_model=ExamSamplingOut)
def list_review_sampling(
    ratio: float = Query(default=0.1, gt=0, le=1),
    seed: Optional[int] = Query(default=None),
    only_unreviewed: bool = Query(default=True),
    limit: int = Query(default=500, ge=1, le=2000),
    current: User = Depends(require_permission("content:exam:write")),
    db: Session = Depends(get_db),
) -> ExamSamplingOut:
    """抽检队列（PG-05）：自建卷按比例稳定随机抽样，默认只抽未复核的。

    PM 口径为 10%；`seed` 相同则抽样结果一致，便于复现与留痕。
    """
    stmt = select(Exam).where(
        Exam.source == "generated", Exam.status == "published"
    )
    if only_unreviewed:
        stmt = stmt.where(Exam.reviewed_at.is_(None))
    rows = db.scalars(stmt.order_by(Exam.id.asc()).limit(limit)).all()
    effective_seed = int(seed if seed is not None else datetime.now().strftime("%Y%m%d"))
    sampled = sample_exams(rows, ratio, effective_seed)
    return ExamSamplingOut(
        total_candidates=len(rows),
        sampled_count=len(sampled),
        ratio=ratio,
        seed=effective_seed,
        items=[
            ExamSamplingItemOut(
                exam_id=exam.id,
                title=exam.title,
                subject=exam.subject,
                grade=exam.grade,
                exam_type=exam.exam_type,
                question_count=len(exam.questions or []),
                total_score=exam.total_score,
                reviewed_at=exam.reviewed_at,
            )
            for exam in sampled
        ],
    )


@router.post("/{exam_id}/sample-review", response_model=ExamReviewActionOut)
def submit_sample_review(
    exam_id: int,
    payload: ExamSampleReviewIn,
    current: User = Depends(require_permission("content:exam:write")),
    db: Session = Depends(get_db),
) -> ExamReviewActionOut:
    """登记抽检结论：通过则留痕；不通过回草稿待整改，并写入抽检意见。"""
    exam = db.get(Exam, exam_id)
    if exam is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="试卷不存在")
    if exam.is_past_paper:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "EXAM_SAMPLE_SCOPE_INVALID",
                "message": "抽检仅适用于自建卷，真题请走双人复核流",
            },
        )
    exam.reviewed_by = current.id
    exam.reviewed_at = datetime.utcnow()
    exam.review_note = (
        ("[抽检通过] " if payload.passed else "[抽检退回] ") + payload.note.strip()
    )
    if not payload.passed:
        exam.status = "draft"
        exam.published_by = None
        exam.published_at = None
    record_audit(
        db,
        user_id=current.id,
        action="exam.sample_review",
        message=f"抽检{'通过' if payload.passed else '退回'}：{payload.note[:200]}",
        after={"exam_id": exam.id, "passed": payload.passed},
        commit=False,
    )
    db.commit()
    return ExamReviewActionOut(
        exam_id=exam.id,
        status=exam.status,
        reviewed_by=exam.reviewed_by,
        reviewed_at=exam.reviewed_at,
        review_note=exam.review_note,
        action="sample_review",
    )


@router.post("/{exam_id}/submit-review", response_model=ExamReviewActionOut)
def submit_exam_review(
    exam_id: int,
    payload: ExamReviewNoteIn,
    current: User = Depends(require_permission("content:exam:write")),
    db: Session = Depends(get_db),
) -> ExamReviewActionOut:
    exam = _reviewable_or_404(db, exam_id)
    if exam.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "EXAM_INVALID_STATE",
                "message": "仅草稿真题可提交复核",
            },
        )
    _require_exam_source(exam)
    exam.status = "pending_review"
    exam.review_note = payload.note
    exam.reviewed_by = None
    exam.reviewed_at = None
    record_audit(
        db,
        user_id=current.id,
        action="exam.review.submit",
        message=f"exam={exam.id}, from=draft, to=pending_review",
    )
    db.commit()
    return ExamReviewActionOut(
        exam_id=exam.id, status=exam.status, action="submit"
    )


def _last_submitter_id(db: Session, exam_id: int) -> Optional[int]:
    """取最近一次「提交复核」的操作人（评审 R2-03：approve 必须换人复核）。

    审计 detail 为 JSON（含 message="exam={id}, from=..., to=..."），用包含匹配即可
    精确到本卷（逗号可防止 exam=5 命中 exam=50）。
    """
    row = db.scalar(
        select(AuditLog)
        .where(
            AuditLog.action == "exam.review.submit",
            AuditLog.detail.contains(f"exam={exam_id},"),
        )
        .order_by(AuditLog.id.desc())
        .limit(1)
    )
    return row.user_id if row is not None else None


@router.post("/{exam_id}/review", response_model=ExamReviewActionOut)
def decide_exam_review(
    exam_id: int,
    payload: ExamReviewIn,
    current: User = Depends(require_permission("content:review:decide")),
    db: Session = Depends(get_db),
) -> ExamReviewActionOut:
    expected = {
        "approve": "pending_review",
        "reject": "pending_review",
        "offline": "published",
        "restore": "offline",
    }[payload.decision]
    exam = _reviewable_or_404(db, exam_id)
    if exam.status != expected:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "EXAM_INVALID_STATE",
                "message": (
                    f"{payload.decision} 需要 {expected} 状态，当前为 {exam.status}"
                ),
            },
        )
    now = datetime.utcnow()
    if payload.decision == "approve":
        _require_exam_source(exam)
        submitter_id = _last_submitter_id(db, exam.id)
        # 评审 R2-03：同一个人不能既提交又复核发布（双人复核），避免留痕自审自发。
        if submitter_id is not None and submitter_id == current.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "EXAM_REVIEW_SELF",
                    "message": "双人复核：提交人与复核发布人不能是同一账号",
                },
            )
        exam.status = "published"
        exam.reviewed_by = current.id
        exam.reviewed_at = now
        exam.published_by = current.id
        exam.published_at = now
    elif payload.decision == "reject":
        # 评审 R2-04：退回必须给理由，否则前端无从整改。
        if not (payload.note and payload.note.strip()):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "EXAM_REVIEW_NOTE_REQUIRED",
                    "message": "退回（reject）必须填写复核意见",
                },
            )
        exam.status = "draft"
        exam.reviewed_by = current.id
        exam.reviewed_at = now
        exam.published_by = None
        exam.published_at = None
    elif payload.decision == "restore":
        # 评审 R2-05：误下线可回草稿，但必须重新走提交复核与发布（不直接复原 published）。
        exam.status = "draft"
        exam.reviewed_by = None
        exam.reviewed_at = None
        exam.published_by = None
        exam.published_at = None
    else:
        exam.status = "offline"
    if payload.note:
        exam.review_note = payload.note
    record_audit(
        db,
        user_id=current.id,
        action=f"exam.review.{payload.decision}",
        message=f"exam={exam.id}, from={expected}, to={exam.status}",
    )
    db.commit()
    return ExamReviewActionOut(
        exam_id=exam.id,
        status=exam.status,
        action=payload.decision,
        reviewed_by=exam.reviewed_by,
        published_by=exam.published_by if payload.decision == "approve" else None,
    )


@router.get("/past-papers/{paper_id}", response_model=PastPaperDetailOut)
def past_paper_detail(
    paper_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PastPaperDetailOut:
    """真题详情/预览：不含答案，附完整溯源（D-09 §5.5）。"""
    exam = db.get(Exam, paper_id)
    if (
        exam is None
        or exam.status != "published"
        or not exam.is_past_paper
        or exam.class_id is not None
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="真题不存在")
    if current.role == "student" and current.grade and exam.grade != current.grade:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "GRADE_MISMATCH", "message": "试卷年级与当前年级不一致"},
        )
    attempt_count = len(
        list(
            db.scalars(
                select(ExamAttempt.id).where(
                    ExamAttempt.user_id == current.id,
                    ExamAttempt.exam_id == exam.id,
                )
            )
        )
    )
    base = PastPaperOut(
        id=exam.id,
        title=exam.title,
        subject=exam.subject,
        grade=exam.grade,
        year=exam.year,
        region=exam.region,
        exam_type=exam.exam_type,
        total_score=exam.total_score,
        time_limit_min=exam.time_limit_min,
        question_count=len(_paper_items(exam)),
        window_start=exam.window_start,
        window_end=exam.window_end,
        window_state=_window_state(exam, datetime.utcnow()),
        source_name=exam.source_name,
        license_note=_license_note_for(exam, current),
        adapted_from=exam.adapted_from,
    )
    return PastPaperDetailOut(
        **base.model_dump(),
        source=exam.source,
        attempt_count=attempt_count,
        reviewed_by=exam.reviewed_by,
        reviewed_at=exam.reviewed_at,
        published_by=exam.published_by,
        published_at=exam.published_at,
    )


@router.get("/past-papers", response_model=list[PastPaperOut])
def list_past_papers(
    response: Response,
    subject: Optional[str] = Query(default=None, max_length=20),
    year: Optional[int] = Query(default=None, ge=2000, le=2100),
    region: Optional[str] = Query(default=None, max_length=40),
    grade: Optional[int] = Query(default=None, ge=1, le=12),
    exam_type: Optional[str] = Query(default=None, max_length=20),
    attempt_status: Optional[str] = Query(
        default=None, pattern=r"^(none|in_progress|completed)$"
    ),
    q: Optional[str] = Query(default=None, max_length=80),
    page: Optional[int] = Query(default=None, ge=1),
    page_size: Optional[int] = Query(default=None, ge=1, le=100),
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[PastPaperOut]:
    """真题库（D-09 §5.3）：年份/学科/地区/类型/状态均由服务端过滤。

    学生仍锁定 current.grade（§11 Q4 维持现状），grade 参数仅对非学生生效。
    """
    stmt = select(Exam).where(
        Exam.status == "published",
        Exam.is_past_paper.is_(True),
        Exam.class_id.is_(None),
    )
    if current.role == "student" and current.grade:
        stmt = stmt.where(Exam.grade == current.grade)
    elif grade is not None:
        stmt = stmt.where(Exam.grade == grade)
    if subject:
        stmt = stmt.where(Exam.subject == subject)
    if year is not None:
        stmt = stmt.where(Exam.year == year)
    if region:
        stmt = stmt.where(Exam.region == region)
    if exam_type:
        stmt = stmt.where(Exam.exam_type == exam_type)
    if q and q.strip():
        stmt = stmt.where(func.lower(Exam.title).contains(q.strip().lower()))
    my_attempt = select(ExamAttempt.id).where(
        ExamAttempt.exam_id == Exam.id,
        ExamAttempt.user_id == current.id,
    )
    if attempt_status == "none":
        stmt = stmt.where(~my_attempt.exists())
    elif attempt_status == "in_progress":
        stmt = stmt.where(
            my_attempt.where(ExamAttempt.status == "in_progress").exists()
        )
    elif attempt_status == "completed":
        stmt = stmt.where(my_attempt.where(ExamAttempt.status != "in_progress").exists())

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    response.headers["X-Total-Count"] = str(total)
    if page is not None:
        size = page_size or 20
        stmt = stmt.offset((page - 1) * size).limit(size)
    else:
        stmt = stmt.limit(60)
    exams = list(db.scalars(stmt.order_by(Exam.year.desc(), Exam.id.desc())))
    now = datetime.utcnow()
    attempts = (
        list(
            db.scalars(
                select(ExamAttempt)
                .where(
                    ExamAttempt.user_id == current.id,
                    ExamAttempt.exam_id.in_([exam.id for exam in exams]),
                )
                .order_by(ExamAttempt.id)
            )
        )
        if exams
        else []
    )
    latest: dict[int, ExamAttempt] = {}
    for attempt in attempts:
        latest[attempt.exam_id] = attempt

    result: list[PastPaperOut] = []
    for exam in exams:
        attempt = latest.get(exam.id)
        if attempt is not None and attempt.status == "in_progress":
            category = "in_progress"
        elif attempt is not None:
            category = "completed"
        else:
            category = "available"
        brief = None
        if attempt is not None:
            brief = ExamAttemptBriefOut(
                id=attempt.id,
                status=attempt.status,
                seed=attempt.seed,
                started_at=attempt.started_at,
                submitted_at=attempt.submitted_at,
                duration_ms=attempt.duration_ms,
                objective_score=attempt.objective_score,
                subjective_score=attempt.subjective_score,
                total_score=attempt.total_score,
                remaining_seconds=_remaining_seconds(exam, attempt, now),
            )
        result.append(
            PastPaperOut(
                id=exam.id,
                title=exam.title,
                subject=exam.subject,
                grade=exam.grade,
                year=exam.year,
                region=exam.region,
                exam_type=exam.exam_type,
                total_score=exam.total_score,
                time_limit_min=exam.time_limit_min,
                question_count=len(_paper_items(exam)),
                window_start=exam.window_start,
                window_end=exam.window_end,
                window_state=_window_state(exam, now),
                category=category,
                attempt=brief,
                source_name=exam.source_name,
                license_note=_license_note_for(exam, current),
                adapted_from=exam.adapted_from,
            )
        )
    return result


@router.post("/mock", response_model=MockExamAssignOut)
def assign_class_mock(
    payload: MockExamAssignIn,
    current: User = Depends(require_permission("learn:assignment:create")),
    db: Session = Depends(get_db),
) -> MockExamAssignOut:
    """教师把一张真题/模考模板派发为班级同卷模考（全班共用同一 exam id）。"""
    template = db.get(Exam, payload.exam_id)
    if template is None or template.status != "published":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模考模板不存在",
        )
    school_class = db.get(SchoolClass, payload.class_id)
    if school_class is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="班级不存在")
    if not class_authorized(db, current, school_class, template.subject):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "CLASS_FORBIDDEN", "message": "无权为该班级布置模考"},
        )
    if school_class.grade and template.grade and school_class.grade != template.grade:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "CLASS_GRADE_MISMATCH",
                "message": "模考年级与班级年级不一致",
            },
        )
    if (
        payload.window_start is not None
        and payload.window_end is not None
        and payload.window_start >= payload.window_end
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "EXAM_WINDOW_INVALID",
                "message": "结束时间必须晚于开始时间",
            },
        )
    questions = list(template.questions or [])
    if not questions:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "NO_QUESTIONS", "message": "模考模板暂无题目"},
        )

    exam = Exam(
        title=payload.title or f"{school_class.name}·{template.title}",
        subject=template.subject,
        grade=template.grade,
        year=template.year,
        source="mock_class",
        exam_type="mock",
        total_score=template.total_score,
        time_limit_min=template.time_limit_min,
        questions=questions,
        blueprint_id=template.blueprint_id,
        chapter_ids=template.chapter_ids,
        status="published",
        window_start=payload.window_start,
        window_end=payload.window_end,
        region=template.region,
        is_past_paper=False,
        class_id=school_class.id,
    )
    db.add(exam)
    db.flush()
    student_count = len(
        list(
            db.scalars(
                select(ClassMember.student_id).where(
                    ClassMember.class_id == school_class.id
                )
            )
        )
    )
    record_audit(
        db,
        user_id=current.id,
        action="exam.mock.assign",
        message=(
            f"exam={exam.id}, class={school_class.id}, "
            f"template={template.id}, students={student_count}"
        ),
    )
    db.commit()
    db.refresh(exam)
    return MockExamAssignOut(
        exam_id=exam.id,
        class_id=school_class.id,
        title=exam.title,
        question_count=len(_paper_items(exam)),
        student_count=student_count,
        window_start=exam.window_start,
        window_end=exam.window_end,
    )


@router.get("/{exam_id}", response_model=ExamDetailOut)
def exam_detail(
    exam_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExamDetailOut:
    exam = _exam_or_404(db, exam_id)
    _ensure_takeable(exam, current, db)
    return _detail_out(db, exam, viewer=current)


# ---------------------------------------------------------------------------
# 开始/续答 → 防抖保存 → 幂等交卷
# ---------------------------------------------------------------------------


# 图片作答：仅主观题支持，最多 2 张，单张 data URL 上限 3 MB、合计 4 MB
IMAGE_DATA_PREFIXES = (
    "data:image/png;base64,",
    "data:image/jpeg;base64,",
    "data:image/jpg;base64,",
    "data:image/webp;base64,",
)
MAX_IMAGE_DATA_URL = 3_000_000
MAX_IMAGES_TOTAL = 4_000_000
MAX_IMAGES_PER_ANSWER = 2


def _validate_answer_images(
    answer: ExamAnswerSaveIn, question: Optional[Question]
) -> None:
    """校验图片作答：仅主观题、白名单格式、大小与数量限制。"""
    if not isinstance(answer.user_answer, dict):
        return
    images = answer.user_answer.get("images")
    if images is None:
        return
    if not isinstance(images, list) or not images:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "IMAGE_INVALID", "message": "图片作答格式不正确"},
        )
    if question is None or question.q_type in OBJECTIVE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "IMAGE_NOT_ALLOWED", "message": "客观题不支持图片作答"},
        )
    if len(images) > MAX_IMAGES_PER_ANSWER:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "IMAGE_TOO_MANY", "message": "每道题最多上传 2 张图片"},
        )
    total = 0
    for image in images:
        if not isinstance(image, str) or not image.startswith(IMAGE_DATA_PREFIXES):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "IMAGE_INVALID",
                    "message": "仅支持 PNG/JPEG/WEBP 图片",
                },
            )
        if len(image) > MAX_IMAGE_DATA_URL:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "IMAGE_TOO_LARGE", "message": "单张图片不得超过 3 MB"},
            )
        total += len(image)
    if total > MAX_IMAGES_TOTAL:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "IMAGE_TOO_LARGE", "message": "图片合计不得超过 4 MB"},
        )


def _save_answers(
    db: Session,
    *,
    attempt: ExamAttempt,
    paper: list[dict[str, Any]],
    answers: list[ExamAnswerSaveIn],
) -> int:
    allowed = {item["question_id"] for item in paper}
    questions = _question_map(db, [answer.question_id for answer in answers])
    rows = {
        row.question_id: row
        for row in db.scalars(
            select(ExamAnswer).where(ExamAnswer.attempt_id == attempt.id)
        )
    }
    now = datetime.utcnow()
    saved = 0
    for answer in answers:
        if answer.question_id not in allowed:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "QUESTION_NOT_IN_EXAM", "message": "题目不属于该试卷"},
            )
        _validate_answer_images(answer, questions.get(answer.question_id))
        row = rows.get(answer.question_id)
        if row is None:
            row = ExamAnswer(
                attempt_id=attempt.id,
                question_id=answer.question_id,
                user_answer=answer.user_answer,
                updated_at=now,
            )
            db.add(row)
            rows[answer.question_id] = row
        else:
            row.user_answer = answer.user_answer
            row.updated_at = now
        saved += 1
    db.flush()
    return saved


def _finalize(
    db: Session,
    *,
    attempt: ExamAttempt,
    exam: Exam,
    paper: list[dict[str, Any]],
    submit_token: str,
    duration_ms: Optional[int],
) -> None:
    """客观题自动判分；存在主观题时进入 grading，交卷结果幂等。"""
    now = datetime.utcnow()
    questions = _question_map(db, [item["question_id"] for item in paper])
    rows = {
        row.question_id: row
        for row in db.scalars(
            select(ExamAnswer).where(ExamAnswer.attempt_id == attempt.id)
        )
    }

    objective_total = 0.0
    pending_grading = False
    for item in paper:
        question = questions.get(item["question_id"])
        if question is None:
            continue
        row = rows.get(item["question_id"])
        if question.q_type in OBJECTIVE_TYPES:
            is_correct = bool(
                row
                and row.user_answer is not None
                and engine.grade_answer(question, row.user_answer)
            )
            if row is None:
                row = ExamAnswer(attempt_id=attempt.id, question_id=item["question_id"])
                db.add(row)
                rows[item["question_id"]] = row
            row.is_correct = is_correct
            row.score = float(item["score"]) if is_correct else 0.0
            row.updated_at = now
            objective_total += row.score
        else:
            pending_grading = True
            if row is not None:
                row.is_correct = None
                row.score = None
                row.updated_at = now

    attempt.objective_score = round(objective_total, 2)
    attempt.subjective_score = None if pending_grading else 0.0
    attempt.total_score = round(objective_total, 2)
    attempt.status = "grading" if pending_grading else "completed"
    attempt.submitted_at = now
    attempt.submit_token = submit_token
    if duration_ms is not None:
        attempt.duration_ms = duration_ms
    else:
        attempt.duration_ms = int(
            (now - (attempt.started_at or now)).total_seconds() * 1000
        )
    db.flush()

    # P0-30 数据回流：客观题写入答题记录、错题本与掌握度（考试权重）
    kp_weight = DEFAULT_EXAM_WEIGHT  # PG-04：已作废按卷型加权
    for item in paper:
        question = questions.get(item["question_id"])
        if question is None or question.q_type not in OBJECTIVE_TYPES:
            continue
        row = rows.get(question.id)
        is_correct = row is not None and row.is_correct is True
        db.add(
            StudentQuestionRecord(
                user_id=attempt.user_id,
                question_id=question.id,
                is_correct=is_correct,
                user_answer=row.user_answer if row is not None else None,
                duration_ms=0,
                source="exam",
                attempt_id=attempt.id,
                kp_weight=kp_weight,
            )
        )
        engine.update_mastery(
            db,
            user_id=attempt.user_id,
            knowledge_point_id=question.knowledge_point_id,
            is_correct=is_correct,
            source="exam",
            weight=kp_weight,
        )
        wrong = engine.upsert_wrong_question(
            db, user_id=attempt.user_id, question=question, is_correct=is_correct
        )
        if not is_correct and wrong is not None and wrong.wrong_reason is None:
            wrong.wrong_reason = wrong_reason_service.classify_exam_wrong(
                question, row.user_answer if row is not None else None
            )
    db.flush()
    cache.invalidate_user(attempt.user_id)


def _submit_out(
    db: Session, attempt: ExamAttempt, paper: list[dict[str, Any]], *, duplicate: bool
) -> ExamSubmitOut:
    correct_count = sum(
        1
        for row in db.scalars(
            select(ExamAnswer).where(ExamAnswer.attempt_id == attempt.id)
        )
        if row.is_correct is True
    )
    return ExamSubmitOut(
        attempt_id=attempt.id,
        status=attempt.status,
        duplicate=duplicate,
        objective_score=attempt.objective_score,
        subjective_score=attempt.subjective_score,
        total_score=attempt.total_score,
        correct_count=correct_count,
        question_count=len(paper),
        pending_grading=attempt.status == "grading",
        submitted_at=attempt.submitted_at,
    )


@router.post("/{exam_id}/attempts", response_model=ExamAttemptOut)
def start_attempt(
    exam_id: int,
    payload: ExamAttemptStartIn = Body(default=ExamAttemptStartIn()),
    current: User = Depends(require_permission("learn:exam:take")),
    db: Session = Depends(get_db),
) -> ExamAttemptOut:
    """开始或续答：复用进行中的作答；已超时的作答由服务端强制交卷后新建一次。"""
    exam = _exam_or_404(db, exam_id)
    _ensure_takeable(exam, current, db)

    now = datetime.utcnow()
    attempts = list(
        db.scalars(
            select(ExamAttempt)
            .where(ExamAttempt.user_id == current.id, ExamAttempt.exam_id == exam.id)
            .order_by(ExamAttempt.id)
        )
    )
    in_progress = next(
        (attempt for attempt in reversed(attempts) if attempt.status == "in_progress"),
        None,
    )
    if in_progress is not None:
        if _remaining_seconds(exam, in_progress, now) > 0:
            return _attempt_out(db, exam, in_progress, now, current)
        _finalize(
            db,
            attempt=in_progress,
            exam=exam,
            paper=_paper_items(exam),
            submit_token=f"auto-expired-{in_progress.id}",
            duration_ms=None,
        )
        db.commit()

    # R-04 青少年模式：新建作答前校验当日学习时长上限（续答不受影响）。
    limit = daily_limit_status(db, current)
    if limit["limited"]:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=limit_exceeded_detail(limit),
            headers={"Retry-After": str(retry_after_seconds(limit))},
        )

    used_seeds = {attempt.seed for attempt in attempts}
    if payload.seed is not None:
        if payload.seed in used_seeds:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "SEED_CONFLICT",
                    "message": "该试卷已使用相同 seed 作答",
                },
            )
        seed = payload.seed
    else:
        seed = max(used_seeds or {0}) + 1

    attempt = ExamAttempt(
        user_id=current.id,
        exam_id=exam.id,
        seed=seed,
        status="in_progress",
        started_at=now,
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return _attempt_out(db, exam, attempt, datetime.utcnow(), current)


@router.patch("/attempts/{attempt_id}", response_model=ExamSaveOut)
def save_answers(
    attempt_id: int,
    payload: ExamSaveIn,
    current: User = Depends(require_permission("learn:exam:take")),
    db: Session = Depends(get_db),
) -> ExamSaveOut:
    """客户端 3 秒防抖保存：按 question 幂等 upsert，重复请求不产生重复行。"""
    attempt = _attempt_or_404(db, attempt_id, current)
    exam = _exam_or_404(db, attempt.exam_id)
    paper = _paper_items(exam)
    now = datetime.utcnow()

    saved = 0
    if attempt.status == "in_progress":
        if _window_state(exam, now) == "closed":
            _finalize(
                db,
                attempt=attempt,
                exam=exam,
                paper=paper,
                submit_token=f"auto-expired-{attempt.id}",
                duration_ms=None,
            )
        else:
            saved = _save_answers(
                db,
                attempt=attempt,
                paper=paper,
                answers=payload.answers,
            )
            if _remaining_seconds(exam, attempt, now) <= 0:
                _finalize(
                    db,
                    attempt=attempt,
                    exam=exam,
                    paper=paper,
                    submit_token=f"auto-expired-{attempt.id}",
                    duration_ms=None,
                )
    db.commit()
    db.refresh(attempt)
    return ExamSaveOut(
        attempt_id=attempt.id,
        saved=saved,
        saved_at=now,
        status=attempt.status,
        remaining_seconds=_remaining_seconds(exam, attempt, now),
        answers=_answers_out(db, attempt, paper),
    )


@router.post("/attempts/{attempt_id}/listening-plays")
def take_listening_play(
    attempt_id: int,
    question_id: int = Query(..., description="听力题 id"),
    current: User = Depends(require_permission("learn:exam:take")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """占用一次听力材料播放额度（CR-008）。

    客户端每次点「播放听力材料」先调本接口占额度，再播放本地缓存或下载音频，
    这样即使音频命中本地缓存，次数依然被正确累计。

    返回 `remaining` = 本次播放后剩余次数；超出上限抛 429
    `LISTENING_PLAY_LIMIT`，`detail` 带 limit / played / remaining。
    上限取 `settings.listening_play_limit_per_attempt`（默认 2）。
    """
    attempt = _attempt_or_404(db, attempt_id, current)
    exam = _exam_or_404(db, attempt.exam_id)
    paper = _paper_items(exam)
    if question_id not in {int(item["question_id"]) for item in paper}:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "QUESTION_NOT_IN_PAPER", "message": "该题不在本卷内"},
        )

    limit = max(settings.listening_play_limit_per_attempt, 1)
    play = db.execute(
        select(ListeningPlay).where(
            ListeningPlay.attempt_id == attempt_id,
            ListeningPlay.question_id == question_id,
        )
    ).scalar_one_or_none()
    now = datetime.utcnow()
    if play is None:
        play = ListeningPlay(
            attempt_id=attempt_id,
            question_id=question_id,
            user_id=current.id,
            play_count=1,
            first_played_at=now,
            last_played_at=now,
        )
        db.add(play)
    elif play.play_count >= limit:
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "LISTENING_PLAY_LIMIT",
                "message": f"该题听力材料最多播放 {limit} 次",
                "limit": limit,
                "played": play.play_count,
                "remaining": 0,
            },
        )
    else:
        play.play_count += 1
        play.last_played_at = now
    db.commit()
    db.refresh(play)
    return {
        "attempt_id": attempt_id,
        "question_id": question_id,
        "limit": limit,
        "played": play.play_count,
        "remaining": max(limit - play.play_count, 0),
    }


@router.post("/attempts/{attempt_id}/submit", response_model=ExamSubmitOut)
def submit_exam(
    attempt_id: int,
    payload: ExamSubmitIn,
    current: User = Depends(require_permission("learn:exam:take")),
    db: Session = Depends(get_db),
) -> ExamSubmitOut:
    """交卷：客观题自动判分；重复提交按 attempt 幂等返回首次结果。"""
    attempt = _attempt_or_404(db, attempt_id, current)
    exam = _exam_or_404(db, attempt.exam_id)
    paper = _paper_items(exam)

    if attempt.status != "in_progress":
        return _submit_out(db, attempt, paper, duplicate=True)

    # 窗口已关闭：不再接收新答案，按已保存内容强制交卷
    if _window_state(exam, datetime.utcnow()) == "closed":
        _finalize(
            db,
            attempt=attempt,
            exam=exam,
            paper=paper,
            submit_token=f"auto-expired-{attempt.id}",
            duration_ms=None,
        )
        db.commit()
        db.refresh(attempt)
        return _submit_out(db, attempt, paper, duplicate=False)

    if payload.answers:
        _save_answers(db, attempt=attempt, paper=paper, answers=payload.answers)
    _finalize(
        db,
        attempt=attempt,
        exam=exam,
        paper=paper,
        submit_token=payload.submit_token,
        duration_ms=payload.duration_ms,
    )
    db.commit()
    db.refresh(attempt)
    return _submit_out(db, attempt, paper, duplicate=False)


# ---------------------------------------------------------------------------
# 考试报告（P0-29）
# ---------------------------------------------------------------------------


def _scoring_points(question: Question) -> list[str]:
    """主观题评分点：优先取 answer.scoring_points，其次按分号切分文本。"""
    answer = question.answer or {}
    raw = answer.get("scoring_points") if isinstance(answer, dict) else None
    if isinstance(raw, list):
        return [str(point) for point in raw if point]
    if isinstance(raw, str) and raw.strip():
        return [part.strip() for part in raw.split("；") if part.strip()]
    return []


def _class_average(db: Session, exam: Exam, current: User) -> ExamClassAverageOut:
    """班级平均：仅统计同班已完成作答的聚合值，不返回任何学生标识。"""
    room = db.scalars(
        select(SchoolClass)
        .join(ClassMember, ClassMember.class_id == SchoolClass.id)
        .where(ClassMember.student_id == current.id)
        .order_by(SchoolClass.id)
    ).first()
    if room is None:
        return ExamClassAverageOut()

    student_ids = list(
        db.scalars(
            select(ClassMember.student_id).where(ClassMember.class_id == room.id)
        )
    )
    attempts = list(
        db.scalars(
            select(ExamAttempt).where(
                ExamAttempt.exam_id == exam.id,
                ExamAttempt.user_id.in_(student_ids),
                ExamAttempt.status == "completed",
                ExamAttempt.total_score.is_not(None),
            )
        )
    )
    if not attempts:
        return ExamClassAverageOut(class_name=room.name)

    average_score = (
        sum(float(attempt.total_score or 0) for attempt in attempts) / len(attempts)
    )
    return ExamClassAverageOut(
        available=True,
        class_name=room.name,
        student_count=len(attempts),
        average_score=round(average_score, 2),
        average_rate=(
            round(average_score / exam.total_score, 3) if exam.total_score else 0.0
        ),
    )


def _trend(db: Session, exam: Exam, current: User) -> ExamTrendOut:
    """同科同类考试最近 5 次的得分率趋势，delta 为最近一次相对上一次。"""
    rows = db.execute(
        select(ExamAttempt, Exam)
        .join(Exam, Exam.id == ExamAttempt.exam_id)
        .where(
            ExamAttempt.user_id == current.id,
            Exam.subject == exam.subject,
            Exam.exam_type == exam.exam_type,
            ExamAttempt.total_score.is_not(None),
        )
        .order_by(ExamAttempt.submitted_at.desc(), ExamAttempt.id.desc())
        .limit(5)
    ).all()
    points = [
        ExamTrendPointOut(
            attempt_id=row_attempt.id,
            exam_id=row_exam.id,
            exam_title=row_exam.title,
            exam_type=row_exam.exam_type,
            score_rate=(
                round(float(row_attempt.total_score or 0) / row_exam.total_score, 3)
                if row_exam.total_score
                else 0.0
            ),
            total_score=row_attempt.total_score,
            submitted_at=row_attempt.submitted_at,
        )
        for row_attempt, row_exam in reversed(rows)
    ]
    delta = (
        round(points[-1].score_rate - points[-2].score_rate, 3)
        if len(points) >= 2
        else None
    )
    return ExamTrendOut(points=points, delta_rate=delta)


@router.get("/attempts/{attempt_id}/report", response_model=ExamReportOut)
def exam_report(
    attempt_id: int,
    current: User = Depends(require_permission("learn:exam:report:self")),
    db: Session = Depends(get_db),
) -> ExamReportOut:
    """交卷后报告：总分、题型得分、知识点得分率、错题清单与下一步。"""
    attempt = _attempt_or_404(db, attempt_id, current)
    if attempt.status == "in_progress":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "EXAM_NOT_SUBMITTED", "message": "考试尚未交卷，暂无报告"},
        )

    exam = _exam_or_404(db, attempt.exam_id)
    paper = _paper_items(exam)
    questions = _question_map(db, [item["question_id"] for item in paper])
    rows = {
        row.question_id: row
        for row in db.scalars(
            select(ExamAnswer).where(ExamAnswer.attempt_id == attempt.id)
        )
    }
    kp_ids = sorted(
        {
            questions[item["question_id"]].knowledge_point_id
            for item in paper
            if item["question_id"] in questions
            and questions[item["question_id"]].knowledge_point_id is not None
        }
    )
    kp_names = {
        kp.id: kp.name
        for kp in db.scalars(
            select(KnowledgePoint).where(KnowledgePoint.id.in_(kp_ids))
        )
    } if kp_ids else {}

    type_bucket: dict[str, dict[str, float]] = {}
    kp_bucket: dict[Optional[int], dict[str, float]] = {}
    ability_bucket: dict[str, dict[str, float]] = {}
    wrong_items: list[ExamWrongItemOut] = []
    pending_subjective: list[ExamSubjectiveItemOut] = []
    question_count = 0
    answered_count = 0
    correct_count = 0
    objective_answered = 0

    for item in paper:
        question = questions.get(item["question_id"])
        if question is None:
            continue
        question_count += 1
        row = rows.get(question.id)
        answered = row is not None and row.user_answer is not None
        is_correct = row is not None and row.is_correct is True
        score = float(row.score) if row is not None and row.score is not None else 0.0

        if answered:
            answered_count += 1
        if is_correct:
            correct_count += 1
        if question.q_type in OBJECTIVE_TYPES and answered:
            objective_answered += 1

        type_bucket.setdefault(
            question.q_type,
            {
                "question_count": 0.0,
                "answered": 0.0,
                "correct": 0.0,
                "score": 0.0,
                "full_score": 0.0,
            },
        )
        type_stat = type_bucket[question.q_type]
        type_stat["question_count"] += 1
        type_stat["answered"] += 1 if answered else 0
        type_stat["correct"] += 1 if is_correct else 0
        type_stat["score"] += score
        type_stat["full_score"] += item["score"]

        kp_id = question.knowledge_point_id
        kp_bucket.setdefault(
            kp_id,
            {"question_count": 0.0, "correct": 0.0, "score": 0.0, "full_score": 0.0},
        )
        kp_stat = kp_bucket[kp_id]
        kp_stat["question_count"] += 1
        kp_stat["correct"] += 1 if is_correct else 0
        kp_stat["score"] += score
        kp_stat["full_score"] += item["score"]

        ability = _ability_of(question.subject, question.q_type)
        ability_bucket.setdefault(
            ability,
            {"question_count": 0.0, "correct": 0.0, "score": 0.0, "full_score": 0.0},
        )
        ability_stat = ability_bucket[ability]
        ability_stat["question_count"] += 1
        ability_stat["correct"] += 1 if is_correct else 0
        ability_stat["score"] += score
        ability_stat["full_score"] += item["score"]

        if row is not None and row.is_correct is False:
            wrong_items.append(
                ExamWrongItemOut(
                    question_id=question.id,
                    q_type=question.q_type,
                    stem=str(question.content.get("stem", "")),
                    user_answer=row.user_answer,
                    correct_answer=question.answer,
                    analysis=question.analysis,
                    score=score,
                    full_score=item["score"],
                )
            )
        elif question.q_type not in OBJECTIVE_TYPES and (
            row is None or row.score is None
        ):
            pending_subjective.append(
                ExamSubjectiveItemOut(
                    question_id=question.id,
                    q_type=question.q_type,
                    stem=str(question.content.get("stem", "")),
                    full_score=float(item["score"]),
                    user_answer=row.user_answer if row is not None else None,
                    reference_answer=question.answer,
                    scoring_points=_scoring_points(question),
                    analysis=question.analysis,
                    self_score=row.self_score if row is not None else None,
                )
            )

    def _rate(score: float, full_score: float) -> float:
        return round(score / full_score, 3) if full_score else 0.0

    type_stats = [
        ExamTypeStatOut(
            q_type=q_type,
            question_count=int(stat["question_count"]),
            answered=int(stat["answered"]),
            correct=int(stat["correct"]),
            score=round(stat["score"], 2),
            full_score=round(stat["full_score"], 2),
            score_rate=_rate(stat["score"], stat["full_score"]),
        )
        for q_type, stat in sorted(type_bucket.items())
    ]

    kp_stats = [
        ExamKpStatOut(
            knowledge_point_id=kp_id,
            name=(
                kp_names.get(kp_id, "未关联知识点")
                if kp_id is not None
                else "未关联知识点"
            ),
            question_count=int(stat["question_count"]),
            correct=int(stat["correct"]),
            score=round(stat["score"], 2),
            full_score=round(stat["full_score"], 2),
            score_rate=_rate(stat["score"], stat["full_score"]),
        )
        for kp_id, stat in kp_bucket.items()
    ]
    kp_stats.sort(key=lambda item: (item.score_rate, item.knowledge_point_id or 0))

    ability_stats = [
        ExamAbilityStatOut(
            ability=ability,
            label=ABILITY_LABELS.get(ability, ability),
            question_count=int(ability_bucket[ability]["question_count"]),
            score=round(ability_bucket[ability]["score"], 2),
            full_score=round(ability_bucket[ability]["full_score"], 2),
            score_rate=_rate(
                ability_bucket[ability]["score"], ability_bucket[ability]["full_score"]
            ),
        )
        for ability in ABILITY_ORDER
        if ability in ability_bucket
    ]

    weak_kp_ids = [
        item.knowledge_point_id
        for item in kp_stats
        if item.knowledge_point_id is not None and item.score_rate < 0.6
    ]
    next_actions: list[ExamNextActionOut] = []
    if weak_kp_ids:
        next_actions.append(
            ExamNextActionOut(
                action="weak_practice",
                label="薄弱点专项练习",
                knowledge_point_ids=weak_kp_ids,
                count=len(weak_kp_ids),
            )
        )
    if wrong_items:
        next_actions.append(
            ExamNextActionOut(
                action="wrong_review",
                label="错题重练",
                count=len(wrong_items),
            )
        )
    next_actions.append(ExamNextActionOut(action="retake", label="再考一次", count=1))

    return ExamReportOut(
        attempt_id=attempt.id,
        exam_id=exam.id,
        exam_title=exam.title,
        exam_type=exam.exam_type,
        status=attempt.status,
        total_score=attempt.total_score,
        full_score=float(exam.total_score),
        objective_score=attempt.objective_score,
        subjective_score=attempt.subjective_score,
        correct_count=correct_count,
        question_count=question_count,
        answered_count=answered_count,
        accuracy=(
            round(correct_count / objective_answered, 3) if objective_answered else 0.0
        ),
        duration_ms=attempt.duration_ms,
        submitted_at=attempt.submitted_at,
        type_stats=type_stats,
        kp_stats=kp_stats,
        ability_stats=ability_stats,
        class_average=_class_average(db, exam, current),
        trend=_trend(db, exam, current),
        wrong_questions=wrong_items,
        pending_subjective=pending_subjective,
        next_actions=next_actions,
    )


@router.post("/attempts/{attempt_id}/self-assess", response_model=ExamSelfAssessOut)
def self_assess(
    attempt_id: int,
    payload: ExamSelfAssessIn,
    current: User = Depends(require_permission("learn:exam:report:self")),
    db: Session = Depends(get_db),
) -> ExamSelfAssessOut:
    """主观题自评：按评分点给出 0~满分，写回成绩并回流掌握度/错题本。"""
    attempt = _attempt_or_404(db, attempt_id, current)
    if attempt.status == "in_progress":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "EXAM_NOT_SUBMITTED", "message": "考试尚未交卷，无法自评"},
        )

    exam = _exam_or_404(db, attempt.exam_id)
    paper = _paper_items(exam)
    paper_by_id = {item["question_id"]: item for item in paper}
    questions = _question_map(db, [item["question_id"] for item in paper])
    rows = {
        row.question_id: row
        for row in db.scalars(
            select(ExamAnswer).where(ExamAnswer.attempt_id == attempt.id)
        )
    }

    assessed: list[tuple[Question, float, float, bool]] = []
    seen: set[int] = set()
    for item in payload.items:
        if item.question_id in seen:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "SELF_ASSESS_DUPLICATE", "message": "同一题目重复自评"},
            )
        seen.add(item.question_id)
        question = questions.get(item.question_id)
        entry = paper_by_id.get(item.question_id)
        if question is None or entry is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "QUESTION_NOT_IN_PAPER",
                    "message": "题目不在本张试卷内",
                },
            )
        if question.q_type in OBJECTIVE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "SELF_ASSESS_NOT_SUBJECTIVE",
                    "message": "客观题由系统判分，无需自评",
                },
            )
        full_score = float(entry["score"])
        if item.score > full_score:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "SELF_SCORE_OUT_OF_RANGE",
                    "message": f"自评分不得超过 {full_score:g} 分",
                },
            )

        row = rows.get(question.id)
        first_assessment = row is None or row.self_score is None
        if row is None:
            row = ExamAnswer(
                attempt_id=attempt.id,
                question_id=question.id,
                user_answer=None,
            )
            db.add(row)
            db.flush()
            rows[question.id] = row
        row.self_score = item.score
        row.score = item.score
        row.updated_at = datetime.utcnow()
        assessed.append((question, full_score, item.score, first_assessment))

    # 成绩回写：首次自评按 60% 及格线回流掌握度与错题本
    kp_weight = DEFAULT_EXAM_WEIGHT  # PG-04：已作废按卷型加权
    for question, full_score, score, first_assessment in assessed:
        if not first_assessment:
            continue
        is_correct = score >= 0.6 * full_score
        db.add(
            StudentQuestionRecord(
                user_id=attempt.user_id,
                question_id=question.id,
                is_correct=is_correct,
                user_answer=rows[question.id].user_answer,
                duration_ms=0,
                source="exam",
                attempt_id=attempt.id,
                kp_weight=kp_weight,
            )
        )
        engine.update_mastery(
            db,
            user_id=attempt.user_id,
            knowledge_point_id=question.knowledge_point_id,
            is_correct=is_correct,
            source="exam",
            weight=kp_weight,
        )
        wrong = engine.upsert_wrong_question(
            db, user_id=attempt.user_id, question=question, is_correct=is_correct
        )
        if not is_correct and wrong is not None and wrong.wrong_reason is None:
            answer_row = rows.get(question.id)
            wrong.wrong_reason = wrong_reason_service.classify_exam_wrong(
                question, answer_row.user_answer if answer_row is not None else None
            )

    subjective_ids = [
        item["question_id"]
        for item in paper
        if questions.get(item["question_id"]) is not None
        and questions[item["question_id"]].q_type not in OBJECTIVE_TYPES
    ]
    subjective_rows = [rows.get(question_id) for question_id in subjective_ids]
    subjective_score = round(
        sum(
            row.score or 0
            for row in subjective_rows
            if row is not None and row.score is not None
        ),
        2,
    )
    pending_count = sum(
        1 for row in subjective_rows if row is None or row.score is None
    )
    attempt.subjective_score = subjective_score
    attempt.total_score = round(attempt.objective_score + subjective_score, 2)
    attempt.status = "completed" if pending_count == 0 else "grading"
    db.commit()
    cache.invalidate_user(attempt.user_id)

    return ExamSelfAssessOut(
        attempt_id=attempt.id,
        status=attempt.status,
        objective_score=attempt.objective_score,
        subjective_score=attempt.subjective_score,
        total_score=attempt.total_score,
        assessed_count=len(assessed),
        pending_count=pending_count,
    )


# ---------------------------------------------------------------------------
# 按蓝图生成试卷（运营/内容）
# ---------------------------------------------------------------------------


@router.post("/generate", response_model=ExamGenerateOut)
def generate_exam(
    payload: ExamGenerateIn,
    current: User = Depends(require_permission("content:exam:write")),
    db: Session = Depends(get_db),
) -> ExamGenerateOut:
    blueprint = db.scalar(
        select(ExamBlueprint).where(ExamBlueprint.code == payload.blueprint_code)
    )
    if blueprint is None or not blueprint.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="试卷蓝图不存在或已停用",
        )

    # D-09 §5.5 / L24：历年真题必须带来源，否则不允许发布（普通卷不受影响）。
    # 放在组卷之前快速失败，避免生成无来源的卷或白跑一次选题。
    if payload.is_past_paper and not (
        payload.source_name and payload.source_name.strip()
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "EXAM_SOURCE_REQUIRED",
                "message": "历年真题必须填写来源名称（source_name）",
            },
        )

    # PG-03 scope 抽象：有 textbook_id + scope 时按册/半册/单元推导章节；否则沿用 chapter_ids
    chapter_ids = list(payload.chapter_ids or [])
    if payload.textbook_id and payload.scope:
        chapter_ids = resolve_scope_chapters(
            db,
            textbook_id=payload.textbook_id,
            scope=payload.scope,
            unit_index=payload.unit_index,
        )
    if not chapter_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "CHAPTER_SCOPE_EMPTY", "message": "所选范围没有章节"},
        )

    # PG-05 跨卷重题去重：排除同年级同学科同卷型最近 3 张卷 + 手动排除清单
    exclude_ids = list(payload.exclude_question_ids or [])
    recent_ids: list[int] = []
    # 真题卷（外部录入）不参与自建卷去重，避免误删真题题号
    if payload.avoid_recent_repeats and not payload.is_past_paper:
        recent_ids = recent_question_ids(
            db,
            subject=blueprint.subject,
            grade=blueprint.grade or current.grade or 1,
            exam_type=blueprint.exam_type,
            limit=3,
        )
    exclude_all = sorted(set(exclude_ids) | set(recent_ids))

    # 期末卷按「本册必考核心考点清单」优先组卷：一张期末卷放不下全册 40-66 个
    # 知识点，按全量覆盖衡量是不可能达标的（要 47-53 题），改按核心清单考核。
    # 单元卷同性质（12-15 题对 19-26 个知识点），但清单要按该单元的章节单独建，
    # 不能拿全册 18 条取交集（一个单元只落得进 3-4 条）。期中卷不出清单。
    core_kps = None
    if blueprint.exam_type == "final" and payload.textbook_id:
        from app.services.core_kp_list import core_kps_for_scope

        core_kps = core_kps_for_scope(
            db,
            textbook_id=payload.textbook_id,
            chapter_ids=chapter_ids,
        ) or None
    elif blueprint.exam_type == "unit" and payload.textbook_id:
        from app.services.core_kp_list import core_kps_for_chapters

        core_kps = core_kps_for_chapters(
            db,
            textbook_id=payload.textbook_id,
            chapter_ids=chapter_ids,
        ) or None

    paper = generate_paper(
        db,
        user=current,
        blueprint=blueprint,
        chapter_ids=chapter_ids,
        seed=payload.seed,
        exclude_question_ids=exclude_all or None,
        core_kps=core_kps,
    )
    # PG-01：不接受降级卷——题型/题量/难度不足直接拒绝，不落库
    if paper.refused:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "EXAM_PAPER_UNSUPPORTED",
                "message": paper.refuse_reason or "题库不满足该蓝图要求，拒绝出卷",
                "shortages": [
                    {
                        "section": item.section_name,
                        "q_type": item.q_type,
                        "wanted": item.wanted,
                        "got": item.got,
                        "reason": item.reason,
                    }
                    for item in paper.shortages
                ],
            },
        )
    if not paper.items:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "NO_QUESTIONS", "message": "所选章节暂无可用题目"},
        )

    title = payload.title or blueprint.name
    # PG-01 命名合规：普通卷不得出现「真题」字样
    if not payload.is_past_paper and "真题" in title:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "EXAM_TITLE_MISLEADING",
                "message": "自主题库生成卷不得命名为「真题」",
            },
        )
    exam = Exam(
        title=title,
        subject=blueprint.subject,
        grade=blueprint.grade or current.grade or 1,
        source="generated",
        year=payload.year,
        source_name=payload.source_name.strip() if payload.source_name else None,
        license_note=payload.license_note,
        adapted_from=payload.adapted_from,
        total_score=int(round(paper.total_score)),
        time_limit_min=blueprint.time_limit_min,
        questions=[
            {
                "question_id": item.question.id,
                "score": item.score,
                "section_index": item.section_index,
                "section_name": item.section_name,
            }
            for item in paper.items
        ],
        blueprint_id=blueprint.id,
        exam_type=blueprint.exam_type,
        chapter_ids=chapter_ids,
        # D-09 §5.7 / CR-005：真题生成即草稿，须复核后才可发布；
        # 普通卷维持 L20「生成即入库可见」行为不变。
        status="draft" if payload.is_past_paper else "published",
        window_start=payload.window_start,
        window_end=payload.window_end,
        region=payload.region,
        is_past_paper=payload.is_past_paper,
    )
    db.add(exam)
    db.commit()
    db.refresh(exam)
    return ExamGenerateOut(
        exam_id=exam.id,
        title=exam.title,
        seed=paper.seed,
        question_count=len(paper.items),
        status=exam.status,
        total_score=round(paper.total_score, 2),
        kp_coverage=paper.kp_coverage,
        difficulty_mix=paper.difficulty_mix,
        fallback_count=0,
        insufficient=paper.insufficient,
        refused=paper.refused,
        refuse_reason=paper.refuse_reason or None,
        excluded_recent_count=len(recent_ids),
        excluded_manual_count=len(exclude_ids),
    )


@router.get("/{exam_id}/spec-table")
def get_exam_spec_table(
    exam_id: int,
    current: User = Depends(require_permission("content:exam:write")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """双向细目表：逐节列出计划题量/分值、实际题量/分值、题型、难度带、知识点与章节。"""
    exam = db.get(Exam, exam_id)
    if exam is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="试卷不存在")
    blueprint = db.get(ExamBlueprint, exam.blueprint_id) if exam.blueprint_id else None
    return build_spec_table(db, exam, blueprint)


@router.get("/{exam_id}/answer-sheet")
def get_exam_answer_sheet(
    exam_id: int,
    current: User = Depends(require_permission("content:exam:write")),
    db: Session = Depends(get_db),
) -> Response:
    """A4 打印版答题卡（HTML）：只含题号与作答区，不含题干与答案。"""
    exam = db.get(Exam, exam_id)
    if exam is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="试卷不存在")
    return Response(
        content=render_answer_sheet_html(db, exam),
        media_type="text/html; charset=utf-8",
        headers={
            "Content-Disposition": f'inline; filename="answer-sheet-{exam.id}.html"'
        },
    )
