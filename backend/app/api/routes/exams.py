"""考试闭环接口（P0-28）：考试列表/详情、开始与续答、防抖保存、幂等交卷与客观自动判。"""

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.core import cache
from app.db.session import get_db
from app.models.assignment import Assignment
from app.models.content import KnowledgePoint, Question
from app.models.exam import Exam, ExamAnswer, ExamAttempt, ExamBlueprint
from app.models.org import ClassMember, SchoolClass
from app.models.practice import StudentQuestionRecord
from app.models.user import User
from app.schemas.content import QuestionPublic
from app.schemas.exam import (
    ExamAbilityStatOut,
    ExamAnswerOut,
    ExamAnswerSaveIn,
    ExamAttemptBriefOut,
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
    ExamSaveIn,
    ExamSaveOut,
    ExamSelfAssessIn,
    ExamSelfAssessOut,
    ExamSubjectiveItemOut,
    ExamSubmitIn,
    ExamSubmitOut,
    ExamSummaryOut,
    ExamTrendOut,
    ExamTrendPointOut,
    ExamTypeStatOut,
    ExamWrongItemOut,
    MockExamAssignIn,
    MockExamAssignOut,
    PastPaperOut,
)
from app.services import learning as engine
from app.services import wrong_reason as wrong_reason_service
from app.services.assignment import class_authorized
from app.services.audit import record_audit
from app.services.exam_paper import generate_paper
from app.services.recommendation import student_visible_exam_clauses
from app.services.usage import (
    daily_limit_status,
    limit_exceeded_detail,
    retry_after_seconds,
)

router = APIRouter(prefix="/exams", tags=["考试"])

# 客观题：交卷即判；其余题型（calc/answer/listen 等）一期进入待批/自评
OBJECTIVE_TYPES = {"choice", "multiple", "fill", "judge"}

# 考试回流掌握度权重：单元测 0.8、期中 0.6、期末 0.5（其余按 0.8）
EXAM_TYPE_WEIGHT = {"unit": 0.8, "midterm": 0.6, "final": 0.5}
DEFAULT_EXAM_WEIGHT = 0.8

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


def _detail_out(
    db: Session,
    exam: Exam,
    now: Optional[datetime] = None,
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
        exam=_detail_out(db, exam, now),
        answers=answers,
        next_index=next_index,
    )


# ---------------------------------------------------------------------------
# 列表与详情
# ---------------------------------------------------------------------------


@router.get("", response_model=list[ExamSummaryOut])
def list_exams(
    exam_type: Optional[str] = Query(default=None, alias="type"),
    status_filter: Optional[str] = Query(
        default=None, alias="status", pattern=r"^(available|in_progress|completed)$"
    ),
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ExamSummaryOut]:
    stmt = select(Exam)
    # 班级作业卷通过 /api/assignments 暴露，避免在通用考试列表中重复出现
    stmt = stmt.where(Exam.source != "assignment")
    if current.role == "student":
        # 与 /api/learn/home.pending_exams 共用同一可见性谓词（D-04 §8.7.1）
        stmt = stmt.where(*student_visible_exam_clauses(current))
    if exam_type:
        stmt = stmt.where(Exam.exam_type == exam_type)
    exams = list(db.scalars(stmt.order_by(Exam.id.desc()).limit(100)))
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
    for attempt in attempts:
        latest[attempt.exam_id] = attempt

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
        if status_filter and category != status_filter:
            continue
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
                window_state=_window_state(exam, now),
                region=exam.region,
                is_past_paper=bool(exam.is_past_paper),
                class_id=exam.class_id,
                attempt=brief,
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


@router.get("/past-papers", response_model=list[PastPaperOut])
def list_past_papers(
    subject: Optional[str] = Query(default=None, max_length=20),
    year: Optional[int] = Query(default=None, ge=2000, le=2100),
    region: Optional[str] = Query(default=None, max_length=40),
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[PastPaperOut]:
    """真题库：已发布的历年真题/模考卷，学生按年级过滤。"""
    stmt = select(Exam).where(
        Exam.status == "published",
        Exam.is_past_paper.is_(True),
        Exam.class_id.is_(None),
    )
    if current.role == "student" and current.grade:
        stmt = stmt.where(Exam.grade == current.grade)
    if subject:
        stmt = stmt.where(Exam.subject == subject)
    if year is not None:
        stmt = stmt.where(Exam.year == year)
    if region:
        stmt = stmt.where(Exam.region == region)
    exams = list(db.scalars(stmt.order_by(Exam.year.desc(), Exam.id.desc()).limit(60)))
    now = datetime.utcnow()
    return [
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
        )
        for exam in exams
    ]


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
    return _detail_out(db, exam)


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
    kp_weight = EXAM_TYPE_WEIGHT.get(exam.exam_type, DEFAULT_EXAM_WEIGHT)
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
            return _attempt_out(db, exam, in_progress, now)
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
    return _attempt_out(db, exam, attempt, datetime.utcnow())


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
    kp_weight = EXAM_TYPE_WEIGHT.get(exam.exam_type, DEFAULT_EXAM_WEIGHT)
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

    paper = generate_paper(
        db,
        user=current,
        blueprint=blueprint,
        chapter_ids=payload.chapter_ids,
        seed=payload.seed,
    )
    if not paper.items:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "NO_QUESTIONS", "message": "所选章节暂无可用题目"},
        )

    title = payload.title or blueprint.name
    exam = Exam(
        title=title,
        subject=blueprint.subject,
        grade=blueprint.grade or current.grade or 1,
        source="generated",
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
        chapter_ids=payload.chapter_ids,
        status="published",
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
        total_score=round(paper.total_score, 2),
        kp_coverage=paper.kp_coverage,
        difficulty_mix=paper.difficulty_mix,
        fallback_count=paper.fallback_count,
        insufficient=paper.insufficient,
    )
