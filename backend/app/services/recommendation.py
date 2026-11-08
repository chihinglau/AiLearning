"""P1-11 首页下一步推荐服务（D-04 §6.6）。

优先级：今日到期复习 → 当前单元薄弱（<40 学讲解、40-70 专项练习）
→ 单元全部 ≥70 且未测 → 学期进度落后 → 每日一练。
"""

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.grade import semester_start
from app.models.content import Chapter, Question
from app.models.exam import Exam, ExamAttempt
from app.models.practice import KpStudyState, MasteryScore, StudentQuestionRecord
from app.models.user import User

WEAK_THRESHOLD = 40.0
UNIT_MASTERED_THRESHOLD = 70.0
# 学期进度基准：每两周推进一个单元
WEEKS_PER_UNIT = 2


def _chapter_kp_ids(db: Session, chapter_id: int) -> set[int]:
    return {
        int(kp_id)
        for kp_id in db.scalars(
            select(Question.knowledge_point_id).where(
                Question.chapter_id == chapter_id,
                Question.knowledge_point_id.is_not(None),
            )
        )
    }


def _mastery_map(db: Session, user_id: int, kp_ids: set[int]) -> dict[int, float]:
    if not kp_ids:
        return {}
    rows = db.execute(
        select(MasteryScore.knowledge_point_id, MasteryScore.score).where(
            MasteryScore.user_id == user_id,
            MasteryScore.knowledge_point_id.in_(kp_ids),
        )
    ).all()
    return {int(kp_id): float(score) for kp_id, score in rows}


def _global_weakest(db: Session, user_id: int) -> Optional[MasteryScore]:
    return db.scalar(
        select(MasteryScore)
        .where(MasteryScore.user_id == user_id)
        .order_by(MasteryScore.score.asc())
        .limit(1)
    )


def _current_chapter(
    db: Session, textbook_ids: list[int], studied_chapter_id: Optional[int]
) -> Optional[Chapter]:
    if studied_chapter_id is not None:
        chapter = db.get(Chapter, studied_chapter_id)
        if chapter is not None:
            return chapter
    if not textbook_ids:
        return None
    return db.scalar(
        select(Chapter)
        .where(
            Chapter.textbook_id.in_(textbook_ids),
            Chapter.is_placeholder == 0,  # 占位/旧样章不参与单元推荐
        )
        .order_by(Chapter.textbook_id, Chapter.order_index, Chapter.id)
        .limit(1)
    )


def _unit_exam(
    db: Session, user: User, chapter: Chapter, now: datetime
) -> Optional[Exam]:
    """当前单元可用且未完成的单元测（已发布、年级匹配、窗口未关闭）。"""
    exams = list(
        db.scalars(
            select(Exam)
            .where(
                Exam.status == "published",
                Exam.exam_type == "unit",
                Exam.grade == (user.grade or chapter.grade),
            )
            .order_by(Exam.id.desc())
            .limit(20)
        )
    )
    taken = set(
        db.scalars(
            select(ExamAttempt.exam_id).where(
                ExamAttempt.user_id == user.id,
                ExamAttempt.status != "in_progress",
            )
        )
    )
    for exam in exams:
        if chapter.id not in {int(item) for item in (exam.chapter_ids or [])}:
            continue
        if exam.id in taken:
            continue
        if exam.window_end is not None and now >= exam.window_end:
            continue
        return exam
    return None


def _learned_chapters(
    db: Session, user_id: int, chapters: list[Chapter]
) -> set[int]:
    if not chapters:
        return set()
    chapter_kps = {
        chapter.id: _chapter_kp_ids(db, chapter.id) for chapter in chapters
    }
    kp_ids: set[int] = set()
    for ids in chapter_kps.values():
        kp_ids.update(ids)
    if not kp_ids:
        return set()
    learned_kps = set(
        db.scalars(
            select(KpStudyState.knowledge_point_id).where(
                KpStudyState.user_id == user_id,
                KpStudyState.knowledge_point_id.in_(kp_ids),
                KpStudyState.state != "未学习",
            )
        )
    )
    learned_kps.update(
        db.scalars(
            select(Question.knowledge_point_id)
            .join(
                StudentQuestionRecord,
                StudentQuestionRecord.question_id == Question.id,
            )
            .where(
                StudentQuestionRecord.user_id == user_id,
                Question.knowledge_point_id.in_(kp_ids),
            )
        )
    )
    return {
        chapter_id
        for chapter_id, ids in chapter_kps.items()
        if ids & learned_kps
    }


def _next_chapter(
    db: Session, textbook_ids: list[int], learned: set[int]
) -> Optional[Chapter]:
    if not textbook_ids:
        return None
    chapters = list(
        db.scalars(
            select(Chapter)
            .where(
                Chapter.textbook_id.in_(textbook_ids),
                Chapter.is_placeholder == 0,  # 占位/旧样章不参与单元推荐
            )
            .order_by(Chapter.textbook_id, Chapter.order_index, Chapter.id)
        )
    )
    return next((chapter for chapter in chapters if chapter.id not in learned), None)


def _progress_recommendation(
    db: Session, user: User, textbook_ids: list[int], now: datetime
) -> Optional[dict[str, Any]]:
    chapters = list(
        db.scalars(
            select(Chapter)
            .where(
                Chapter.textbook_id.in_(textbook_ids),
                Chapter.is_placeholder == 0,  # 占位/旧样章不参与单元推荐
            )
            .order_by(Chapter.textbook_id, Chapter.order_index, Chapter.id)
        )
    )
    if not chapters:
        return None
    weeks = max(0, (now - semester_start(now)).days // 7)
    expected_units = min(len(chapters), max(1, weeks // WEEKS_PER_UNIT))
    learned = _learned_chapters(db, user.id, chapters)
    if len(learned) >= expected_units:
        return None
    chapter = next((item for item in chapters if item.id not in learned), chapters[0])
    kp_ids = _chapter_kp_ids(db, chapter.id)
    kp_id = min(kp_ids) if kp_ids else None
    return {
        "action": "continue",
        "label": "继续学习",
        "reason": (
            f"学期进度落后：已学 {len(learned)} 个单元，"
            f"建议本周完成第 {max(1, len(learned) + 1)} 个单元"
        ),
        "chapter_id": chapter.id,
        "chapter_name": chapter.name,
        "knowledge_point_id": kp_id,
    }


def build_recommendation(
    db: Session,
    *,
    user: User,
    now: datetime,
    due_review: int,
    textbook_ids: list[int],
    studied_chapter_id: Optional[int],
) -> dict[str, Any]:
    """按 §6.6 顺序返回 action/label/reason 与可跳转的单元/知识点/试卷。"""
    if due_review > 0:
        return {
            "action": "review",
            "label": "去复习",
            "reason": f"今日有 {due_review} 道错题到期",
        }

    chapter = _current_chapter(db, textbook_ids, studied_chapter_id)
    if chapter is not None:
        kp_ids = _chapter_kp_ids(db, chapter.id)
        scores = _mastery_map(db, user.id, kp_ids)
        if kp_ids:
            weakest_kp = min(kp_ids, key=lambda kp_id: scores.get(kp_id, 0.0))
            weakest_score = scores.get(weakest_kp, 0.0)
            if weakest_score < WEAK_THRESHOLD:
                return {
                    "action": "learn_kp",
                    "label": "先学讲解",
                    "reason": "当前单元存在掌握度低于 40 的知识点",
                    "chapter_id": chapter.id,
                    "chapter_name": chapter.name,
                    "knowledge_point_id": weakest_kp,
                }
            if weakest_score < UNIT_MASTERED_THRESHOLD:
                return {
                    "action": "practice",
                    "label": "专项练习",
                    "reason": "当前单元存在掌握度 40-70 的知识点，建议专项巩固",
                    "chapter_id": chapter.id,
                    "chapter_name": chapter.name,
                    "knowledge_point_id": weakest_kp,
                }
            exam = _unit_exam(db, user, chapter, now)
            if exam is not None:
                return {
                    "action": "unit_test",
                    "label": "单元测试",
                    "reason": f"「{chapter.name}」已掌握，建议完成单元测检验",
                    "chapter_id": chapter.id,
                    "chapter_name": chapter.name,
                    "exam_id": exam.id,
                }

    # 当前单元无数据时回退到全局最薄弱知识点（兼容旧数据）
    if chapter is None or not _chapter_kp_ids(db, chapter.id):
        weakest = _global_weakest(db, user.id)
        if weakest is not None and weakest.score < WEAK_THRESHOLD:
            return {
                "action": "learn_kp",
                "label": "先学讲解",
                "reason": "存在掌握度低于 40 的知识点",
                "knowledge_point_id": weakest.knowledge_point_id,
            }
        if weakest is not None and weakest.score < UNIT_MASTERED_THRESHOLD:
            return {
                "action": "practice",
                "label": "专项练习",
                "reason": "存在掌握度 40-70 的知识点，建议专项巩固",
                "knowledge_point_id": weakest.knowledge_point_id,
            }

    progress = _progress_recommendation(db, user, textbook_ids, now)
    if progress is not None:
        return progress

    return {
        "action": "daily",
        "label": "每日一练",
        "reason": "保持手感，从每日一练开始",
    }


def _window_state(exam: Exam, now: datetime) -> str:
    if exam.window_start is None and exam.window_end is None:
        return "unscheduled"
    if exam.window_start is not None and now < exam.window_start:
        return "scheduled"
    if exam.window_end is not None and now >= exam.window_end:
        return "closed"
    return "open"


def build_pending_exams(
    db: Session, *, user: User, now: datetime, limit: int = 3
) -> list[dict[str, Any]]:
    """待办考试：本年级已发布、窗口未关闭且尚未完成的试卷。"""
    exams = list(
        db.scalars(
            select(Exam)
            .where(Exam.status == "published", Exam.grade == (user.grade or 1))
            .order_by(Exam.id.desc())
            .limit(20)
        )
    )
    if not exams:
        return []
    done = set(
        db.scalars(
            select(ExamAttempt.exam_id).where(
                ExamAttempt.user_id == user.id,
                ExamAttempt.status != "in_progress",
            )
        )
    )
    result: list[dict[str, Any]] = []
    for exam in exams:
        if exam.id in done:
            continue
        state = _window_state(exam, now)
        if state == "closed":
            continue
        result.append(
            {
                "exam_id": exam.id,
                "title": exam.title,
                "exam_type": exam.exam_type,
                "window_state": state,
                "window_start": exam.window_start,
                "window_end": exam.window_end,
            }
        )
        if len(result) >= limit:
            break
    return result
