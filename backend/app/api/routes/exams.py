"""考试闭环接口（P0-28）：考试列表/详情、开始与续答、防抖保存、幂等交卷与客观自动判。"""

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.db.session import get_db
from app.models.content import Question
from app.models.exam import Exam, ExamAnswer, ExamAttempt, ExamBlueprint
from app.models.user import User
from app.schemas.content import QuestionPublic
from app.schemas.exam import (
    ExamAnswerOut,
    ExamAnswerSaveIn,
    ExamAttemptBriefOut,
    ExamAttemptOut,
    ExamAttemptStartIn,
    ExamDetailOut,
    ExamGenerateIn,
    ExamGenerateOut,
    ExamQuestionOut,
    ExamSaveIn,
    ExamSaveOut,
    ExamSubmitIn,
    ExamSubmitOut,
    ExamSummaryOut,
)
from app.services import learning as engine
from app.services.exam_paper import generate_paper

router = APIRouter(prefix="/exams", tags=["考试"])

# 客观题：交卷即判；其余题型（calc/answer/listen 等）一期进入待批/自评
OBJECTIVE_TYPES = {"choice", "multiple", "fill", "judge"}


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


def _ensure_takeable(exam: Exam, user: User) -> None:
    """学生只能参加本年级已发布的试卷。"""
    if user.role != "student":
        return
    if exam.status != "published":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="试卷不存在")
    if user.grade and exam.grade != user.grade:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "GRADE_MISMATCH", "message": "试卷年级与当前年级不一致"},
        )


def _detail_out(db: Session, exam: Exam) -> ExamDetailOut:
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考试作答不存在")
    return attempt


def _answers_out(db: Session, attempt: ExamAttempt, paper: list[dict[str, Any]]) -> list[ExamAnswerOut]:
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


def _attempt_out(db: Session, exam: Exam, attempt: ExamAttempt, now: datetime) -> ExamAttemptOut:
    paper = _paper_items(exam)
    answers = _answers_out(db, attempt, paper)
    answered = {answer.question_id for answer in answers if answer.user_answer is not None}
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
        exam=_detail_out(db, exam),
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
    if current.role == "student":
        stmt = stmt.where(Exam.status == "published")
        if current.grade:
            stmt = stmt.where(Exam.grade == current.grade)
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
                attempt=brief,
            )
        )
    return result


@router.get("/{exam_id}", response_model=ExamDetailOut)
def exam_detail(
    exam_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExamDetailOut:
    exam = _exam_or_404(db, exam_id)
    _ensure_takeable(exam, current)
    return _detail_out(db, exam)


# ---------------------------------------------------------------------------
# 开始/续答 → 防抖保存 → 幂等交卷
# ---------------------------------------------------------------------------


def _save_answers(
    db: Session,
    *,
    attempt: ExamAttempt,
    paper: list[dict[str, Any]],
    answers: list[ExamAnswerSaveIn],
) -> int:
    allowed = {item["question_id"] for item in paper}
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
                row and row.user_answer is not None and engine.grade_answer(question, row.user_answer)
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
        attempt.duration_ms = int((now - (attempt.started_at or now)).total_seconds() * 1000)
    db.flush()


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
    _ensure_takeable(exam, current)

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

    used_seeds = {attempt.seed for attempt in attempts}
    if payload.seed is not None:
        if payload.seed in used_seeds:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "SEED_CONFLICT", "message": "该试卷已使用相同 seed 作答"},
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
        saved = _save_answers(db, attempt=attempt, paper=paper, answers=payload.answers)
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
# 按蓝图生成试卷（运营/内容）
# ---------------------------------------------------------------------------


@router.post("/generate", response_model=ExamGenerateOut)
def generate_exam(
    payload: ExamGenerateIn,
    current: User = Depends(require_permission("content:exam:write")),
    db: Session = Depends(get_db),
) -> ExamGenerateOut:
    blueprint = db.scalar(select(ExamBlueprint).where(ExamBlueprint.code == payload.blueprint_code))
    if blueprint is None or not blueprint.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="试卷蓝图不存在或已停用")

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
