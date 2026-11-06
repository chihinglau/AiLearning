"""自适应学习闭环：组卷 → 提交（判题+掌握度+错题调度）→ 错题本 → 复习 → 学情。"""

from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_student_access
from app.core.grade import derive_grade_group, derive_semester, derive_stage
from app.core.scope import StudentAccess
from app.db.session import get_db
from app.models.content import Chapter, KnowledgePoint, Question, Textbook
from app.models.practice import MasteryScore, StudentQuestionRecord, WrongQuestion
from app.models.textbook import TextbookBinding
from app.models.user import User
from app.schemas.content import QuestionPublic
from app.schemas.learn import (
    ChapterTreeOut,
    HomeContinue,
    HomeOut,
    HomeRecommendation,
    HomeTextbook,
    HomeTodayPlan,
    KpBriefOut,
    KpDetailOut,
    KpSelfTestIn,
    KpStateOut,
    KnowledgeNodeOut,
    LearnStartIn,
    LearnStartOut,
    LearnStatsOut,
    LearnSubmitIn,
    LearnSubmitOut,
    MasteryMapOut,
    PracticePreviewIn,
    PracticePreviewOut,
    UnitDetailOut,
    UnitOut,
    UnitSectionOut,
    WrongQuestionOut,
    WrongReasonIn,
)
from app.services import learning as engine
from app.services import practice as practice_service
from app.services import study_state
from app.services import textbook as textbook_service

router = APIRouter(prefix="/learn", tags=["自适应学习"])


def _mastery_map(db: Session, *, user_id: int, subject: Optional[str]) -> dict[int, MasteryScore]:
    stmt = select(MasteryScore).where(MasteryScore.user_id == user_id)
    if subject:
        kp_ids = select(KnowledgePoint.id).where(KnowledgePoint.subject == subject)
        stmt = stmt.where(MasteryScore.knowledge_point_id.in_(kp_ids))
    return {row.knowledge_point_id: row for row in db.scalars(stmt)}


def _question_count_by_kp(db: Session, kp_ids: list[int]) -> dict[int, int]:
    if not kp_ids:
        return {}
    rows = db.execute(
        select(Question.knowledge_point_id, func.count(Question.id))
        .where(Question.knowledge_point_id.in_(kp_ids))
        .group_by(Question.knowledge_point_id)
    ).all()
    return {kp_id: count for kp_id, count in rows}


# ---------------------------------------------------------------------------
# 知识树（挂个人掌握度）
# ---------------------------------------------------------------------------


@router.get("/knowledge-tree", response_model=list[ChapterTreeOut])
def knowledge_tree(
    textbook_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ChapterTreeOut]:
    """章 → 知识点树：章节下的知识点由该章题目（question.knowledge_point_id）聚合，
    并挂上该学生的掌握度与题目数量。"""
    chapters = list(
        db.scalars(
            select(Chapter)
            .where(Chapter.textbook_id == textbook_id)
            .order_by(Chapter.order_index, Chapter.id)
        )
    )
    if not chapters:
        return []

    chapter_ids = [c.id for c in chapters]
    q_rows = db.execute(
        select(Question.chapter_id, Question.knowledge_point_id, func.count(Question.id))
        .where(Question.chapter_id.in_(chapter_ids))
        .group_by(Question.chapter_id, Question.knowledge_point_id)
    ).all()
    kp_ids = sorted({kp_id for _, kp_id, _ in q_rows if kp_id is not None})
    kp_map = {
        kp.id: kp
        for kp in db.scalars(select(KnowledgePoint).where(KnowledgePoint.id.in_(kp_ids)))
    } if kp_ids else {}
    mastery = _mastery_map(db, user_id=current.id, subject=None)
    attempted = _attempted_kps(db, user_id=current.id, kp_ids=kp_ids)
    due = _due_review_kps(
        db, user_id=current.id, kp_ids=kp_ids, now=datetime.utcnow()
    )
    last_studied = _last_studied_map(db, user_id=current.id, kp_ids=kp_ids)
    states = study_state.states_for(db, user_id=current.id, kp_ids=kp_ids)

    # chapter_id -> {kp_id: count}
    agg: dict[int, dict[int, int]] = {}
    for chapter_id, kp_id, count in q_rows:
        if kp_id is not None:
            agg.setdefault(chapter_id, {})[kp_id] = count

    result: list[ChapterTreeOut] = []
    for ch in chapters:
        tree = ChapterTreeOut.model_validate(ch)
        nodes: list[KnowledgeNodeOut] = []
        for kp_id, count in agg.get(ch.id, {}).items():
            kp = kp_map.get(kp_id)
            if kp is None:
                continue
            nodes.append(
                _kp_node(
                    kp,
                    question_count=count,
                    mastery=mastery,
                    attempted=attempted,
                    due=due,
                    last_studied=last_studied,
                    states=states,
                )
            )
        tree.knowledge_points = sorted(
            nodes, key=lambda n: (n.mastery_score, n.id)
        )
        result.append(tree)
    return result


# ---------------------------------------------------------------------------
# 目录视图：教材 → 单元 → 节 → 知识点（P0-19）
# ---------------------------------------------------------------------------


def _chapter_kps(db: Session, chapter_ids: list[int]) -> dict[int, dict[int, int]]:
    """chapter_id → {kp_id: 题目数}。"""
    if not chapter_ids:
        return {}
    rows = db.execute(
        select(Question.chapter_id, Question.knowledge_point_id, func.count(Question.id))
        .where(
            Question.chapter_id.in_(chapter_ids),
            Question.knowledge_point_id.is_not(None),
        )
        .group_by(Question.chapter_id, Question.knowledge_point_id)
    ).all()
    agg: dict[int, dict[int, int]] = {}
    for chapter_id, kp_id, count in rows:
        agg.setdefault(chapter_id, {})[int(kp_id)] = int(count)
    return agg


def _attempted_kps(db: Session, *, user_id: int, kp_ids: list[int]) -> set[int]:
    if not kp_ids:
        return set()
    rows = db.execute(
        select(Question.knowledge_point_id)
        .join(StudentQuestionRecord, StudentQuestionRecord.question_id == Question.id)
        .where(
            StudentQuestionRecord.user_id == user_id,
            Question.knowledge_point_id.in_(kp_ids),
        )
        .distinct()
    ).all()
    return {int(kp_id) for (kp_id,) in rows}


def _due_review_kps(db: Session, *, user_id: int, kp_ids: list[int], now: datetime) -> set[int]:
    if not kp_ids:
        return set()
    rows = db.execute(
        select(Question.knowledge_point_id)
        .join(WrongQuestion, WrongQuestion.question_id == Question.id)
        .where(
            WrongQuestion.user_id == user_id,
            WrongQuestion.status == "active",
            WrongQuestion.next_review_at.is_not(None),
            WrongQuestion.next_review_at <= now,
            Question.knowledge_point_id.in_(kp_ids),
        )
        .distinct()
    ).all()
    return {int(kp_id) for (kp_id,) in rows}


def _last_studied_map(db: Session, *, user_id: int, kp_ids: list[int]) -> dict[int, datetime]:
    if not kp_ids:
        return {}
    rows = db.execute(
        select(Question.knowledge_point_id, func.max(StudentQuestionRecord.attempted_at))
        .join(StudentQuestionRecord, StudentQuestionRecord.question_id == Question.id)
        .where(
            StudentQuestionRecord.user_id == user_id,
            Question.knowledge_point_id.in_(kp_ids),
        )
        .group_by(Question.knowledge_point_id)
    ).all()
    return {int(kp_id): last for kp_id, last in rows if last is not None}


def _kp_node(
    kp: KnowledgePoint,
    *,
    question_count: int,
    mastery: dict[int, MasteryScore],
    attempted: set[int],
    due: set[int],
    last_studied: dict[int, datetime],
    states: dict[int, study_state.KpStudyState] | None = None,
) -> KnowledgeNodeOut:
    row = mastery.get(kp.id)
    score = round(row.score, 1) if row else 0.0
    node = KnowledgeNodeOut.model_validate(kp)
    node.mastery_score = score
    node.mastery_confidence = row.confidence if row else 0
    node.mastery_band = engine.mastery_band(score)
    node.question_count = question_count
    persisted = (states or {}).get(kp.id)
    node.state = (
        engine.derive_study_state(
            mastery=score,
            attempted=kp.id in attempted,
            due_review=kp.id in due,
        )
        if persisted is None
        else persisted.state
    )
    if kp.id in due:
        node.state = study_state.REVIEWING
    node.last_studied_at = last_studied.get(kp.id)
    return node


def _unit_out(
    chapter: Chapter,
    *,
    kps: dict[int, KnowledgePoint],
    counts: dict[int, int],
    mastery: dict[int, MasteryScore],
    attempted: set[int],
) -> UnitOut:
    kp_ids = list(counts)
    scores = [mastery[kp_id].score if kp_id in mastery else 0.0 for kp_id in kp_ids]
    avg = round(sum(scores) / len(scores), 1) if scores else 0.0
    learned = sum(1 for kp_id in kp_ids if kp_id in attempted or kp_id in mastery)
    parents = {kps[kp_id].parent_id for kp_id in kp_ids if kps[kp_id].parent_id}
    return UnitOut(
        id=chapter.id,
        textbook_id=chapter.textbook_id,
        grade=chapter.grade,
        name=chapter.name,
        order_index=chapter.order_index,
        summary=chapter.summary,
        section_count=len(parents),
        kp_count=len(kp_ids),
        question_count=sum(counts.values()),
        avg_mastery=avg,
        mastery_band=engine.mastery_band(avg),
        learned_kp_count=learned,
        progress=round(learned / len(kp_ids), 3) if kp_ids else 0.0,
    )


@router.get("/textbook/{textbook_id}/units", response_model=list[UnitOut])
def textbook_units(
    textbook_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[UnitOut]:
    textbook = db.get(Textbook, textbook_id)
    if textbook is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="教材不存在")
    chapters = list(
        db.scalars(
            select(Chapter)
            .where(Chapter.textbook_id == textbook_id)
            .order_by(Chapter.order_index, Chapter.id)
        )
    )
    if not chapters:
        return []

    agg = _chapter_kps(db, [c.id for c in chapters])
    all_kp_ids = sorted({kp_id for counts in agg.values() for kp_id in counts})
    kps = {
        kp.id: kp
        for kp in db.scalars(select(KnowledgePoint).where(KnowledgePoint.id.in_(all_kp_ids)))
    } if all_kp_ids else {}
    mastery = _mastery_map(db, user_id=current.id, subject=None)
    attempted = _attempted_kps(db, user_id=current.id, kp_ids=all_kp_ids)

    return [
        _unit_out(
            chapter,
            kps=kps,
            counts=agg.get(chapter.id, {}),
            mastery=mastery,
            attempted=attempted,
        )
        for chapter in chapters
    ]


@router.get("/unit/{chapter_id}", response_model=UnitDetailOut)
def unit_detail(
    chapter_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UnitDetailOut:
    chapter = db.get(Chapter, chapter_id)
    if chapter is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="单元不存在")

    counts = _chapter_kps(db, [chapter.id]).get(chapter.id, {})
    kp_ids = list(counts)
    kps = {
        kp.id: kp
        for kp in db.scalars(select(KnowledgePoint).where(KnowledgePoint.id.in_(kp_ids)))
    } if kp_ids else {}
    mastery = _mastery_map(db, user_id=current.id, subject=None)
    attempted = _attempted_kps(db, user_id=current.id, kp_ids=kp_ids)
    due = _due_review_kps(db, user_id=current.id, kp_ids=kp_ids, now=datetime.utcnow())
    last_studied = _last_studied_map(db, user_id=current.id, kp_ids=kp_ids)
    states = study_state.states_for(db, user_id=current.id, kp_ids=kp_ids)

    nodes = [
        _kp_node(
            kp,
            question_count=counts.get(kp.id, 0),
            mastery=mastery,
            attempted=attempted,
            due=due,
            last_studied=last_studied,
            states=states,
        )
        for kp in kps.values()
    ]
    nodes.sort(key=lambda n: (n.order_index, n.id))

    parent_ids = sorted({n.parent_id for n in nodes if n.parent_id})
    parents = {
        kp.id: kp
        for kp in db.scalars(
            select(KnowledgePoint).where(KnowledgePoint.id.in_(parent_ids))
        )
    } if parent_ids else {}
    sections: list[UnitSectionOut] = []
    for parent_id in parent_ids:
        parent = parents.get(parent_id)
        if parent is None:
            continue
        children = [n for n in nodes if n.parent_id == parent_id]
        avg = round(sum(n.mastery_score for n in children) / len(children), 1)
        sections.append(
            UnitSectionOut(
                id=parent.id,
                name=parent.name,
                order_index=parent.order_index,
                kp_count=len(children),
                avg_mastery=avg,
                mastery_band=engine.mastery_band(avg),
            )
        )
    sections.sort(key=lambda s: (s.order_index, s.id))

    return UnitDetailOut(
        unit=_unit_out(
            chapter, kps=kps, counts=counts, mastery=mastery, attempted=attempted
        ),
        sections=sections,
        knowledge_points=nodes,
    )


@router.get("/kp/{kp_id}", response_model=KpDetailOut)
def kp_detail(
    kp_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KpDetailOut:
    kp = db.get(KnowledgePoint, kp_id)
    if kp is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识点不存在")

    question_count = (
        db.scalar(
            select(func.count(Question.id)).where(
                Question.knowledge_point_id == kp.id
            )
        )
        or 0
    )
    mastery = _mastery_map(db, user_id=current.id, subject=None)
    attempted = _attempted_kps(db, user_id=current.id, kp_ids=[kp.id])
    due = _due_review_kps(
        db, user_id=current.id, kp_ids=[kp.id], now=datetime.utcnow()
    )
    last_studied = _last_studied_map(db, user_id=current.id, kp_ids=[kp.id])
    row = mastery.get(kp.id)
    score = round(row.score, 1) if row else 0.0
    persisted = study_state.get(db, user_id=current.id, kp_id=kp.id)
    state = (
        persisted.state
        if persisted is not None
        else engine.derive_study_state(
            mastery=score,
            attempted=kp.id in attempted,
            due_review=kp.id in due,
        )
    )
    if kp.id in due:
        state = study_state.REVIEWING

    section = db.get(KnowledgePoint, kp.parent_id) if kp.parent_id else None
    prereq_ids = list(kp.prerequisites or [])
    prereqs = {
        item.id: item
        for item in db.scalars(
            select(KnowledgePoint).where(KnowledgePoint.id.in_(prereq_ids))
        )
    } if prereq_ids else {}

    return KpDetailOut(
        id=kp.id,
        subject=kp.subject,
        grade=kp.grade,
        name=kp.name,
        node_type=kp.node_type,
        explanation=kp.explanation,
        section_id=section.id if section else None,
        section_name=section.name if section else None,
        prerequisites=[
            KpBriefOut(
                id=prereq.id,
                name=prereq.name,
                subject=prereq.subject,
                mastery_score=round(mastery[prereq.id].score, 1)
                if prereq.id in mastery
                else 0.0,
            )
            for prereq in prereqs.values()
        ],
        mastery_score=score,
        mastery_confidence=row.confidence if row else 0,
        mastery_band=engine.mastery_band(score),
        question_count=question_count,
        state=state,
        state_evidence=persisted.evidence_count if persisted else 0,
        last_studied_at=last_studied.get(kp.id),
    )


def _kp_or_404(db: Session, kp_id: int) -> KnowledgePoint:
    kp = db.get(KnowledgePoint, kp_id)
    if kp is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识点不存在")
    return kp


@router.post("/kp/{kp_id}/read", response_model=KpStateOut)
def mark_kp_read(
    kp_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KpStateOut:
    """阅读讲解：未学习 → 学习中。"""
    _kp_or_404(db, kp_id)
    row = study_state.mark(db, user_id=current.id, kp_id=kp_id, event="read")
    db.commit()
    db.refresh(row)
    return KpStateOut.model_validate(row)


@router.post("/kp/{kp_id}/selftest", response_model=KpStateOut)
def submit_kp_selftest(
    kp_id: int,
    payload: KpSelfTestIn,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KpStateOut:
    """自测达标（≥80 分）→ 已掌握，否则待巩固。"""
    _kp_or_404(db, kp_id)
    row = study_state.mark(
        db,
        user_id=current.id,
        kp_id=kp_id,
        event="selftest",
        achieved=payload.score >= study_state.SELFTEST_PASS_SCORE,
    )
    db.commit()
    db.refresh(row)
    return KpStateOut.model_validate(row)


# ---------------------------------------------------------------------------
# 掌握度映射
# ---------------------------------------------------------------------------


@router.get("/mastery", response_model=MasteryMapOut)
def mastery(
    subject: Optional[str] = None,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MasteryMapOut:
    rows = _mastery_map(db, user_id=current.id, subject=subject)
    return MasteryMapOut(items={str(kp_id): round(row.score, 1) for kp_id, row in rows.items()})


# ---------------------------------------------------------------------------
# 练习预览（P0-21）
# ---------------------------------------------------------------------------


@router.post("/practice/preview", response_model=PracticePreviewOut)
def practice_preview(
    payload: PracticePreviewIn,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PracticePreviewOut:
    """组卷预览：题量、知识点覆盖、预计时长、seed（与开始练习共用同一 seed）。"""
    plan = practice_service.build_plan(
        db,
        user=current,
        scope_type=payload.scope_type,
        scope_ids=payload.scope_ids,
        count=payload.count,
        q_types=payload.q_types or None,
        seed=payload.seed,
        mode=payload.mode,
        duration_limit_min=payload.duration_limit_min,
    )
    return PracticePreviewOut(
        count=plan.count,
        available=plan.available,
        insufficient=plan.insufficient,
        estimated_minutes=plan.estimated_minutes,
        kp_coverage=plan.kp_coverage,
        covered_kp_count=plan.covered_kp_count,
        range_kp_count=plan.range_kp_count,
        q_type_mix=plan.q_type_mix,
        due_review_count=plan.due_review_count,
        seed=plan.seed,
    )


# ---------------------------------------------------------------------------
# 自适应组卷
# ---------------------------------------------------------------------------


@router.post("/start", response_model=LearnStartOut)
def start(
    payload: LearnStartIn,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LearnStartOut:
    now = datetime.utcnow()
    stmt = select(Question)
    kp: Optional[KnowledgePoint] = None
    if payload.knowledge_point_id:
        kp = db.get(KnowledgePoint, payload.knowledge_point_id)
        if kp is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识点不存在")
        stmt = stmt.where(Question.knowledge_point_id == kp.id)
    if payload.chapter_id:
        stmt = stmt.where(Question.chapter_id == payload.chapter_id)
    if payload.subject:
        stmt = stmt.where(Question.subject == payload.subject)

    candidates = list(db.scalars(stmt))

    # 教材与年级不一致时练习前二次确认（D-04 §13）
    scope_subject = payload.subject or (kp.subject if kp is not None else None)
    if scope_subject is None and payload.chapter_id:
        chapter = db.get(Chapter, payload.chapter_id)
        if chapter is not None:
            book = db.get(Textbook, chapter.textbook_id)
            scope_subject = book.subject if book is not None else None
    if scope_subject is None and payload.scope_type and payload.scope_ids:
        first_id = payload.scope_ids[0]
        if payload.scope_type == "kp":
            node = db.get(KnowledgePoint, first_id)
            scope_subject = node.subject if node is not None else None
        elif payload.scope_type == "chapter":
            chapter = db.get(Chapter, first_id)
            if chapter is not None:
                book = db.get(Textbook, chapter.textbook_id)
                scope_subject = book.subject if book is not None else None
        elif payload.scope_type == "textbook":
            book = db.get(Textbook, first_id)
            scope_subject = book.subject if book is not None else None
    if (
        current.role == "student"
        and scope_subject
        and not payload.confirm_mismatch
        and textbook_service.has_mismatch(db, current, scope_subject)
    ):
        raise HTTPException(
            status_code=428,
            detail={
                "code": "TEXTBOOK_MISMATCH",
                "message": "当前教材与年级不一致，请确认后继续",
                "subject": scope_subject,
            },
        )

    # P0-22：新范围方式与预览共用同一组参数 + 同一 seed（预览=实际）
    if payload.scope_type:
        plan = practice_service.build_plan(
            db,
            user=current,
            scope_type=payload.scope_type,
            scope_ids=payload.scope_ids,
            count=payload.count,
            q_types=payload.q_types or None,
            seed=payload.seed,
            mode=payload.mode,
            duration_limit_min=payload.duration_limit_min,
        )
        if not plan.questions:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="该范围暂无可用题目")
        return LearnStartOut(
            questions=[QuestionPublic.model_validate(q) for q in plan.questions],
            seed=plan.seed,
        )

    # 兼容旧种子（题目只用 tags 关联知识点名称）
    if kp is not None:
        linked = [q for q in candidates if q.knowledge_point_id == kp.id]
        tagged = [q for q in candidates if kp.name in (q.tags or [])]
        candidates = list({q.id: q for q in linked + tagged}.values())
    if not candidates:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="该范围暂无可用题目")

    # 取该范围内知识点掌握度的加权平均（以主 KP 为准）
    score = 0.0
    if kp is not None:
        m = db.scalar(
            select(MasteryScore).where(
                MasteryScore.user_id == current.id,
                MasteryScore.knowledge_point_id == kp.id,
            )
        )
        score = m.score if m else 0.0
    else:
        kp_ids = {q.knowledge_point_id for q in candidates if q.knowledge_point_id}
        if kp_ids:
            ms = list(
                db.scalars(
                    select(MasteryScore).where(
                        MasteryScore.user_id == current.id,
                        MasteryScore.knowledge_point_id.in_(kp_ids),
                    )
                )
            )
            score = sum(x.score for x in ms) / len(ms) if ms else 0.0

    review_ids = engine.due_review_question_ids(db, user_id=current.id, now=now)
    review_quota = min(3, max(0, payload.count // 4))
    difficulties = engine.pick_difficulties(score, payload.count)
    questions = engine.choose_questions(
        candidates,
        difficulties,
        review_ids=review_ids,
        review_quota=review_quota,
    )
    return LearnStartOut(
        questions=[QuestionPublic.model_validate(q) for q in questions[: payload.count]]
    )


# ---------------------------------------------------------------------------
# 提交：判题 + 记录 + 掌握度 + 错题本
# ---------------------------------------------------------------------------


@router.post("/submit", response_model=LearnSubmitOut)
def submit(
    payload: LearnSubmitIn,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LearnSubmitOut:
    question = db.get(Question, payload.question_id)
    if question is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="题目不存在")

    is_correct = engine.grade_answer(question, payload.user_answer)

    record = StudentQuestionRecord(
        user_id=current.id,
        question_id=question.id,
        is_correct=is_correct,
        user_answer=payload.user_answer,
        duration_ms=payload.duration_ms,
    )
    db.add(record)

    mastery_row = engine.update_mastery(
        db,
        user_id=current.id,
        knowledge_point_id=question.knowledge_point_id
        or _kp_id_by_tag(db, question),
        is_correct=is_correct,
    )
    if mastery_row is not None and question.knowledge_point_id is not None:
        # 首次练习 → 待巩固；掌握度≥85 → 已掌握（P0-20 状态机）
        study_state.mark(
            db,
            user_id=current.id,
            kp_id=question.knowledge_point_id,
            event="practice",
            achieved=mastery_row.score >= 85,
        )
    wrong = engine.upsert_wrong_question(
        db, user_id=current.id, question=question, is_correct=is_correct
    )
    db.commit()

    return LearnSubmitOut(
        is_correct=is_correct,
        correct_answer=question.answer,
        analysis=question.analysis,
        mastery_score=round(mastery_row.score, 1) if mastery_row else None,
        in_wrong_book=bool(wrong and wrong.status == "active"),
    )


def _kp_id_by_tag(db: Session, question: Question) -> Optional[int]:
    """旧数据兼容：题目只有 tags（知识点名称）时回查 KP id。"""
    for name in question.tags or []:
        kp = db.scalar(
            select(KnowledgePoint).where(
                KnowledgePoint.subject == question.subject,
                KnowledgePoint.name == name,
            )
        )
        if kp is not None:
            return kp.id
    return None


# ---------------------------------------------------------------------------
# 错题本
# ---------------------------------------------------------------------------


def _target_student(access: StudentAccess) -> int:
    if access.student_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "STUDENT_ID_REQUIRED", "message": "请选择要查看的学生"},
        )
    return access.student_id


@router.get("/wrong-questions", response_model=list[WrongQuestionOut])
def wrong_questions(
    status_filter: str = Query(default="active", alias="status"),
    subject: Optional[str] = None,
    access: StudentAccess = Depends(require_student_access("learn:wrong:self")),
    db: Session = Depends(get_db),
) -> list[WrongQuestionOut]:
    user_id = _target_student(access)
    stmt = select(WrongQuestion).where(WrongQuestion.user_id == user_id)
    if status_filter in ("active", "mastered"):
        stmt = stmt.where(WrongQuestion.status == status_filter)
    rows = list(
        db.scalars(stmt.order_by(WrongQuestion.last_wrong_at.desc()).limit(200))
    )
    q_ids = [r.question_id for r in rows]
    questions = {
        q.id: q
        for q in db.scalars(select(Question).where(Question.id.in_(q_ids)))
    } if q_ids else {}
    result: list[WrongQuestionOut] = []
    for row in rows:
        q = questions.get(row.question_id)
        out = WrongQuestionOut.model_validate(row)
        if q is not None:
            out.subject = q.subject
            out.q_type = q.q_type
            out.stem = str(q.content.get("stem", ""))
            out.chapter_id = q.chapter_id
            out.knowledge_point_id = q.knowledge_point_id
            out.difficulty = q.difficulty
        if subject and out.subject != subject:
            continue
        result.append(out)
    return result


@router.post("/wrong-questions/{wrong_id}/reason", response_model=WrongQuestionOut)
def tag_reason(
    wrong_id: int,
    payload: WrongReasonIn,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WrongQuestion:
    row = db.get(WrongQuestion, wrong_id)
    if row is None or row.user_id != current.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="错题不存在")
    row.wrong_reason = payload.wrong_reason
    db.commit()
    db.refresh(row)
    return row


@router.get("/review/today", response_model=LearnStartOut)
def review_today(
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LearnStartOut:
    now = datetime.utcnow()
    ids = engine.due_review_question_ids(db, user_id=current.id, now=now)
    if not ids:
        return LearnStartOut(questions=[])
    questions = list(
        db.scalars(select(Question).where(Question.id.in_(ids)).limit(20))
    )
    return LearnStartOut(
        questions=[QuestionPublic.model_validate(q) for q in questions]
    )


# ---------------------------------------------------------------------------
# 学情总览
# ---------------------------------------------------------------------------


@router.get("/stats", response_model=LearnStatsOut)
def stats(
    access: StudentAccess = Depends(
        require_student_access(
            ("learn:stats:self:read", "learn:stats:child:read", "learn:stats:class:read")
        )
    ),
    db: Session = Depends(get_db),
) -> LearnStatsOut:
    user_id = _target_student(access)
    total = db.scalar(
        select(func.count(StudentQuestionRecord.id)).where(
            StudentQuestionRecord.user_id == user_id
        )
    ) or 0
    correct = db.scalar(
        select(func.count(StudentQuestionRecord.id)).where(
            StudentQuestionRecord.user_id == user_id,
            StudentQuestionRecord.is_correct.is_(True),
        )
    ) or 0
    due_count = db.scalar(
        select(func.count(WrongQuestion.id)).where(
            WrongQuestion.user_id == user_id,
            WrongQuestion.status == "active",
            WrongQuestion.next_review_at.is_not(None),
            WrongQuestion.next_review_at <= datetime.utcnow(),
        )
    ) or 0
    active_wrong = db.scalar(
        select(func.count(WrongQuestion.id)).where(
            WrongQuestion.user_id == user_id,
            WrongQuestion.status == "active",
        )
    ) or 0

    # 连续学习天数：按本地日期对答题记录去重
    days = db.scalars(
        select(func.date(StudentQuestionRecord.attempted_at))
        .where(StudentQuestionRecord.user_id == user_id)
        .distinct()
    ).all()
    streak = _calc_streak(sorted({str(d) for d in days}, reverse=True))

    # 薄弱知识点 Top3（掌握度低于 70 分，按掌握度升序）
    weak_nodes: list[KnowledgeNodeOut] = []
    mastery_rows = list(
        db.scalars(
            select(MasteryScore)
            .where(
                MasteryScore.user_id == user_id,
                MasteryScore.score < 70,
            )
            .order_by(MasteryScore.score.asc())
            .limit(3)
        )
    )
    for m in mastery_rows:
        kp = db.get(KnowledgePoint, m.knowledge_point_id)
        if kp is None:
            continue
        node = KnowledgeNodeOut.model_validate(kp)
        node.mastery_score = round(m.score, 1)
        node.mastery_band = engine.mastery_band(m.score)
        weak_nodes.append(node)

    return LearnStatsOut(
        total_answered=total,
        total_correct=correct,
        accuracy=round(correct / total, 3) if total else 0.0,
        streak_days=streak,
        due_review_count=due_count,
        active_wrong_count=active_wrong,
        weak_points=weak_nodes,
    )


def _calc_streak(reverse_days: list[str]) -> int:
    """reverse_days 为倒序唯一日期字符串（YYYY-MM-DD）；从今天/昨天起连续计数。"""
    if not reverse_days:
        return 0
    today = datetime.utcnow().date()
    allowed = {today.isoformat(), (today - timedelta(days=1)).isoformat()}
    if reverse_days[0] not in allowed:
        return 0
    streak = 1
    cursor = datetime.fromisoformat(reverse_days[0]).date()
    for day in reverse_days[1:]:
        cursor = cursor - timedelta(days=1)
        if day == cursor.isoformat():
            streak += 1
        else:
            break
    return streak


# 学段分组对应的单次练习量（D-03 §4.2）
_PRACTICE_PLAN = {
    "primary_low": (8, 12),
    "primary_mid": (12, 20),
    "primary_high": (14, 20),
    "junior": (18, 30),
    "senior": (20, 45),
}


def _home_textbook(
    subject: str, textbook: Textbook, semester: str, grade: int
) -> HomeTextbook:
    return HomeTextbook(
        subject=subject,
        textbook_id=textbook.id,
        version=textbook.version,
        grade=textbook.grade,
        semester=semester,
        mismatch=textbook.grade != grade,
    )


@router.get("/home", response_model=HomeOut)
def home(
    current: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> HomeOut:
    """学习首页聚合：当前教材、今日计划、继续学习、下一步推荐、待办考试。"""
    if current.role != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "NOT_STUDENT", "message": "仅学生账号可访问学习首页"},
        )

    now = datetime.utcnow()
    grade = current.grade or 1
    stage = current.stage or derive_stage(grade)
    grade_group = current.grade_group or derive_grade_group(grade)
    semester = current.semester or derive_semester(now)
    region = current.region or "shenzhen"

    rows = db.execute(
        select(TextbookBinding, Textbook)
        .join(Textbook, Textbook.id == TextbookBinding.textbook_id)
        .where(
            TextbookBinding.user_id == current.id,
            TextbookBinding.status == "active",
        )
        .order_by(TextbookBinding.subject)
    ).all()
    textbooks = [_home_textbook(b.subject, t, b.semester, grade) for b, t in rows]
    needs_binding = not textbooks
    mismatch_subjects = textbook_service.mismatched_subjects(db, current)
    recommended = []
    if needs_binding:
        recommended = [
            _home_textbook(subject, textbook, semester, grade)
            for subject, textbook in textbook_service.recommended_textbooks(
                db, grade=grade, semester=semester, region=region
            )
        ]

    due_review = db.scalar(
        select(func.count(WrongQuestion.id)).where(
            WrongQuestion.user_id == current.id,
            WrongQuestion.status == "active",
            WrongQuestion.next_review_at.is_not(None),
            WrongQuestion.next_review_at <= now,
        )
    ) or 0
    question_count, minutes = _PRACTICE_PLAN.get(grade_group, _PRACTICE_PLAN["primary_mid"])

    latest = db.scalar(
        select(StudentQuestionRecord)
        .where(StudentQuestionRecord.user_id == current.id)
        .order_by(StudentQuestionRecord.attempted_at.desc())
        .limit(1)
    )
    continue_learning: Optional[HomeContinue] = None
    if latest is not None:
        question = db.get(Question, latest.question_id)
        if question is not None:
            chapter = db.get(Chapter, question.chapter_id)
            kp = (
                db.get(KnowledgePoint, question.knowledge_point_id)
                if question.knowledge_point_id
                else None
            )
            continue_learning = HomeContinue(
                subject=question.subject,
                chapter_id=chapter.id if chapter else None,
                chapter_name=chapter.name if chapter else None,
                knowledge_point_id=kp.id if kp else None,
                knowledge_point_name=kp.name if kp else None,
            )

    weakest = db.scalar(
        select(MasteryScore)
        .where(MasteryScore.user_id == current.id)
        .order_by(MasteryScore.score.asc())
        .limit(1)
    )
    if due_review > 0:
        recommendation = HomeRecommendation(
            action="review", label="去复习", reason=f"今日有 {due_review} 道错题到期"
        )
    elif weakest is not None and weakest.score < 40:
        kp = db.get(KnowledgePoint, weakest.knowledge_point_id)
        recommendation = HomeRecommendation(
            action="learn_kp",
            label="先学讲解",
            reason="存在掌握度低于 40 的知识点",
            knowledge_point_id=kp.id if kp else None,
        )
    elif weakest is not None and weakest.score < 70:
        recommendation = HomeRecommendation(
            action="practice",
            label="专项练习",
            reason="存在掌握度 40-70 的知识点，建议专项巩固",
            knowledge_point_id=weakest.knowledge_point_id,
        )
    elif continue_learning is not None:
        recommendation = HomeRecommendation(
            action="continue", label="继续学习", reason="接着上次的学习内容继续"
        )
    else:
        recommendation = HomeRecommendation(
            action="daily", label="每日一练", reason="保持手感，从每日一练开始"
        )

    return HomeOut(
        grade=grade,
        stage=stage,
        grade_group=grade_group,
        semester=semester,
        region=region,
        needs_binding=needs_binding,
        textbooks=textbooks,
        recommended=recommended,
        mismatch_subjects=mismatch_subjects,
        today_plan=HomeTodayPlan(
            due_review=due_review,
            practice_questions=question_count,
            practice_minutes=minutes,
            new_kp_target=1,
        ),
        continue_learning=continue_learning,
        recommendation=recommendation,
        pending_exams=[],
    )
