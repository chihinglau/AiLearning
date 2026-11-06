"""P2-03 班级作业：统一组卷、班级派发与教师主观题批改。

设计要点（D-04 §8.1/§8.5、D-03 §5.2）：
- 一次作业 = 一张试卷（`exams.source="assignment"`）+ 一个班级，全班共用同一套题；
- 学生仅本班成员可作答，教师需具备该班该学科授课关系（班主任可跨学科）；
- 教师批改主观题写入 `exam_answers.score/teacher_comment`，并重算作答总分与状态。
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.assignment import Assignment
from app.models.content import Question
from app.models.exam import Exam, ExamAnswer, ExamAttempt, ExamBlueprint
from app.models.org import ClassMember, SchoolClass, TeacherClassAssignment
from app.models.user import User
from app.services.audit import record_audit
from app.services.exam_paper import generate_paper

Q_TYPES = {"choice", "multiple", "judge", "fill", "answer"}
ASSIGNMENT_SEED = 2026
DEFAULT_DUE_DAYS = 7
SUBJECTIVE_TYPE = "answer"


def _forbidden(code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail={"code": code, "message": message}
    )


def _invalid(code: str, message: str) -> HTTPException:
    return HTTPException(status_code=422, detail={"code": code, "message": message})


def build_sections(count: int, q_types: List[str]) -> List[Dict[str, Any]]:
    """按题型均分题量，每节 5 分；未知题型回退单选。"""
    valid = [item for item in dict.fromkeys(q_types) if item in Q_TYPES] or ["choice"]
    base, extra = divmod(count, len(valid))
    sections: List[Dict[str, Any]] = []
    for index, q_type in enumerate(valid):
        wanted = base + (1 if index < extra else 0)
        if wanted <= 0:
            continue
        sections.append(
            {
                "name": f"{q_type} 部分",
                "q_type": q_type,
                "count": wanted,
                "score_each": 5,
            }
        )
    return sections


def class_authorized(
    db: Session, user: User, school_class: SchoolClass, subject: str
) -> bool:
    """教师是否有权对目标班级/学科布置作业或批改。"""
    if user.role in ("super_admin", "admin"):
        return True
    if user.role == "school_admin":
        return user.school_id is not None and user.school_id == school_class.school_id
    if school_class.head_teacher_id == user.id:
        return True
    assignment = db.scalar(
        select(TeacherClassAssignment).where(
            TeacherClassAssignment.teacher_id == user.id,
            TeacherClassAssignment.class_id == school_class.id,
        )
    )
    if assignment is None:
        return False
    return assignment.subject == subject or assignment.role_in_class == "head_teacher"


def class_students(db: Session, class_id: int) -> List[User]:
    student_ids = list(
        db.scalars(
            select(ClassMember.student_id).where(ClassMember.class_id == class_id)
        )
    )
    if not student_ids:
        return []
    return list(db.scalars(select(User).where(User.id.in_(student_ids)).order_by(User.id)))


def is_class_member(db: Session, class_id: int, user_id: int) -> bool:
    return (
        db.scalar(
            select(ClassMember).where(
                ClassMember.class_id == class_id, ClassMember.student_id == user_id
            )
        )
        is not None
    )


def create_assignment(
    db: Session,
    teacher: User,
    *,
    class_id: int,
    title: str,
    subject: str,
    chapter_ids: List[int],
    count: int,
    q_types: List[str],
    time_limit_min: int,
    due_at: Optional[datetime],
) -> Tuple[Assignment, Exam]:
    school_class = db.get(SchoolClass, class_id)
    if school_class is None:
        raise HTTPException(status_code=404, detail="班级不存在")
    if not class_authorized(db, teacher, school_class, subject):
        raise _forbidden("ASSIGNMENT_NOT_ALLOWED", "无该班级/学科的布置权限")
    if not class_students(db, class_id):
        raise _invalid("CLASS_EMPTY", "班级暂无学生，无法布置作业")

    now = datetime.utcnow()
    if due_at is not None and due_at.tzinfo is not None:
        due_at = due_at.astimezone(timezone.utc).replace(tzinfo=None)
    deadline = due_at or now + timedelta(days=DEFAULT_DUE_DAYS)
    if deadline <= now:
        raise _invalid("DUE_AT_INVALID", "截止时间必须晚于当前时间")

    sections = build_sections(count, q_types)
    blueprint = ExamBlueprint(
        code=f"assignment_preview_{teacher.id}_{int(now.timestamp())}",
        name=title,
        subject=subject,
        grade=school_class.grade,
        exam_type="custom",
        total_score=int(count * 5),
        time_limit_min=time_limit_min,
        sections=sections,
        kp_coverage_min=0.0,
        difficulty_mix={},
        is_active=False,
    )
    paper = generate_paper(
        db, user=teacher, blueprint=blueprint, chapter_ids=chapter_ids, seed=ASSIGNMENT_SEED
    )
    if not paper.items:
        raise _invalid("NO_QUESTION", "所选章节暂无可用题目")

    exam = Exam(
        title=title,
        subject=subject,
        grade=school_class.grade,
        source="assignment",
        total_score=int(round(paper.total_score)),
        time_limit_min=time_limit_min,
        questions=[
            {
                "question_id": item.question.id,
                "score": item.score,
                "section_index": item.section_index,
                "section_name": item.section_name,
            }
            for item in paper.items
        ],
        exam_type="custom",
        chapter_ids=chapter_ids,
        status="published",
        window_start=now,
        window_end=deadline,
    )
    db.add(exam)
    db.flush()

    assignment = Assignment(
        title=title,
        teacher_id=teacher.id,
        class_id=class_id,
        exam_id=exam.id,
        subject=subject,
        due_at=deadline,
        status="published",
    )
    db.add(assignment)
    db.flush()
    return assignment, exam


def latest_attempts(
    db: Session, exam_id: int, user_ids: Optional[List[int]] = None
) -> Dict[int, ExamAttempt]:
    stmt = select(ExamAttempt).where(ExamAttempt.exam_id == exam_id)
    if user_ids is not None:
        if not user_ids:
            return {}
        stmt = stmt.where(ExamAttempt.user_id.in_(user_ids))
    latest: Dict[int, ExamAttempt] = {}
    for attempt in db.scalars(stmt.order_by(ExamAttempt.id)):
        latest[attempt.user_id] = attempt
    return latest


def pending_grading_count(db: Session, exam: Exam, attempts: Dict[int, ExamAttempt]) -> int:
    """待批改学生数：交卷后进入 grading 状态、尚未完成批改的作答数。"""
    return sum(1 for attempt in attempts.values() if attempt.status == "grading")


def grade_items(db: Session, assignment: Assignment) -> List[Dict[str, Any]]:
    exam = db.get(Exam, assignment.exam_id)
    if exam is None:
        return []
    member_ids = [student.id for student in class_students(db, assignment.class_id)]
    attempts = latest_attempts(db, exam.id, member_ids)
    if not attempts:
        return []
    attempt_by_id = {attempt.id: attempt for attempt in attempts.values()}
    max_scores = {
        int(item["question_id"]): float(item["score"]) for item in exam.questions
    }
    answers = list(
        db.scalars(
            select(ExamAnswer).where(
                ExamAnswer.attempt_id.in_(list(attempt_by_id)),
                ExamAnswer.question_id.in_(list(max_scores)),
            )
        )
    )
    questions = {
        question.id: question
        for question in db.scalars(
            select(Question).where(Question.id.in_(list(max_scores)))
        )
    }
    users = {
        student.id: student for student in class_students(db, assignment.class_id)
    }
    items: List[Dict[str, Any]] = []
    for answer in answers:
        question = questions.get(answer.question_id)
        if question is None or question.q_type != SUBJECTIVE_TYPE:
            continue
        attempt = attempt_by_id.get(answer.attempt_id)
        if attempt is None or attempt.status == "in_progress":
            continue
        student = users.get(attempt.user_id)
        items.append(
            {
                "attempt_id": attempt.id,
                "student_id": attempt.user_id,
                "student_name": student.nickname if student else None,
                "question_id": question.id,
                "q_type": question.q_type,
                "content": question.content or {},
                "answer": question.answer or {},
                "analysis": question.analysis,
                "user_answer": answer.user_answer,
                "max_score": max_scores[question.id],
                "current_score": answer.score,
                "comment": answer.teacher_comment,
            }
        )
    return items


def _recompute_attempt(db: Session, attempt: ExamAttempt, exam: Exam) -> None:
    answers = {
        answer.question_id: answer
        for answer in db.scalars(
            select(ExamAnswer).where(ExamAnswer.attempt_id == attempt.id)
        )
    }
    subjective_total = 0.0
    pending = 0
    for item in exam.questions:
        question = db.get(Question, int(item["question_id"]))
        if question is None or question.q_type != SUBJECTIVE_TYPE:
            continue
        answer = answers.get(question.id)
        if answer is None:
            continue
        if answer.score is None:
            pending += 1
        else:
            subjective_total += float(answer.score)
    attempt.subjective_score = round(subjective_total, 2)
    attempt.total_score = (
        round(float(attempt.objective_score or 0.0) + subjective_total, 2)
        if pending == 0
        else None
    )
    attempt.status = "grading" if pending else "completed"


def grade_batch(
    db: Session,
    teacher: User,
    assignment: Assignment,
    items: List[Dict[str, Any]],
) -> Dict[str, int]:
    school_class = db.get(SchoolClass, assignment.class_id)
    if school_class is None:
        raise HTTPException(status_code=404, detail="班级不存在")
    if not class_authorized(db, teacher, school_class, assignment.subject):
        raise _forbidden("GRADE_NOT_ALLOWED", "无该班级的批改权限")

    exam = db.get(Exam, assignment.exam_id)
    if exam is None:
        raise HTTPException(status_code=404, detail="作业试卷不存在")
    member_ids = {student.id for student in class_students(db, assignment.class_id)}
    attempts = latest_attempts(db, exam.id, list(member_ids))
    attempt_by_id = {attempt.id: attempt for attempt in attempts.values()}
    max_scores = {
        int(item["question_id"]): float(item["score"]) for item in exam.questions
    }
    subjective_ids = {
        question_id
        for question_id, question in {
            question.id: question
            for question in db.scalars(
                select(Question).where(Question.id.in_(list(max_scores)))
            )
        }.items()
        if question.q_type == SUBJECTIVE_TYPE
    }

    touched_attempts: set[int] = set()
    for item in items:
        attempt = attempt_by_id.get(int(item["attempt_id"]))
        if attempt is None:
            raise _invalid("ATTEMPT_NOT_IN_ASSIGNMENT", "作答不属于该班作业")
        question_id = int(item["question_id"])
        if question_id not in subjective_ids:
            raise _invalid("QUESTION_NOT_SUBJECTIVE", "仅主观题支持教师批改")
        score = float(item["score"])
        if score > max_scores[question_id]:
            raise _invalid("SCORE_EXCEEDED", "评分超过该题满分")
        answer = db.scalar(
            select(ExamAnswer).where(
                ExamAnswer.attempt_id == attempt.id,
                ExamAnswer.question_id == question_id,
            )
        )
        if answer is None:
            raise _invalid("ANSWER_NOT_FOUND", "该作答记录不存在")
        before = {"score": answer.score, "comment": answer.teacher_comment}
        answer.score = score
        answer.teacher_comment = item.get("comment")
        answer.graded_by = teacher.id
        answer.graded_at = datetime.utcnow()
        touched_attempts.add(attempt.id)
        record_audit(
            db,
            user_id=teacher.id,
            action="assignment.answer.grade",
            before={"attempt_id": attempt.id, "question_id": question_id, **before},
            after={
                "attempt_id": attempt.id,
                "question_id": question_id,
                "score": score,
                "comment": item.get("comment"),
            },
            commit=False,
        )

    completed = 0
    pending = 0
    for attempt_id in touched_attempts:
        attempt = attempt_by_id[attempt_id]
        _recompute_attempt(db, attempt, exam)
        if attempt.status == "completed":
            completed += 1
        else:
            pending += 1
    db.flush()

    remaining = sum(
        1
        for attempt in attempts.values()
        if attempt.status == "grading"
    )
    return {"graded": len(items), "completed_attempts": completed, "pending_attempts": remaining}
