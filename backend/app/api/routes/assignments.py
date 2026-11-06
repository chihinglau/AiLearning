"""P2-03 班级作业 API：教师布置、学生查看、教师批改主观题。"""

from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.db.session import get_db
from app.models.assignment import Assignment
from app.models.exam import Exam
from app.models.org import ClassMember, SchoolClass
from app.models.user import User
from app.schemas.assignment import (
    AssignmentCreateIn,
    AssignmentDetailOut,
    AssignmentOut,
    AssignmentStudentOut,
    GradeBatchIn,
    GradeBatchOut,
    GradingItemOut,
    GradingListOut,
)
from app.services.assignment import (
    class_authorized,
    class_students,
    create_assignment,
    grade_batch,
    grade_items,
    is_class_member,
    latest_attempts,
    pending_grading_count,
)
from app.services.audit import record_audit

router = APIRouter(prefix="/assignments", tags=["班级作业"])

SUBMITTED_STATUSES = ("grading", "completed")


def _assignment_or_404(db: Session, assignment_id: int) -> Assignment:
    assignment = db.get(Assignment, assignment_id)
    if assignment is None:
        raise HTTPException(status_code=404, detail="作业不存在")
    return assignment


def _ensure_visible(db: Session, assignment: Assignment, current: User) -> SchoolClass:
    school_class = db.get(SchoolClass, assignment.class_id)
    if school_class is None:
        raise HTTPException(status_code=404, detail="班级不存在")
    if current.role in ("super_admin", "admin"):
        return school_class
    if current.role == "school_admin":
        if current.school_id == school_class.school_id:
            return school_class
        raise HTTPException(
            status_code=403,
            detail={"code": "ASSIGNMENT_NOT_ALLOWED", "message": "无权查看该作业"},
        )
    if current.role == "student":
        if is_class_member(db, assignment.class_id, current.id):
            return school_class
        raise HTTPException(
            status_code=403,
            detail={"code": "ASSIGNMENT_NOT_MEMBER", "message": "仅本班学生可查看作业"},
        )
    if assignment.teacher_id == current.id or class_authorized(
        db, current, school_class, assignment.subject
    ):
        return school_class
    raise HTTPException(
        status_code=403,
        detail={"code": "ASSIGNMENT_NOT_ALLOWED", "message": "无权查看该作业"},
    )


def _summary(
    db: Session, assignment: Assignment, school_class: SchoolClass, current: User
) -> Dict[str, object]:
    students = class_students(db, assignment.class_id)
    attempts = latest_attempts(db, assignment.exam_id, [student.id for student in students])
    submitted = sum(1 for attempt in attempts.values() if attempt.status in SUBMITTED_STATUSES)
    exam = db.get(Exam, assignment.exam_id)
    pending = pending_grading_count(db, exam, attempts) if exam is not None else 0
    mine = attempts.get(current.id)
    return {
        "id": assignment.id,
        "title": assignment.title,
        "subject": assignment.subject,
        "class_id": assignment.class_id,
        "class_name": school_class.name,
        "exam_id": assignment.exam_id,
        "due_at": assignment.due_at,
        "status": assignment.status,
        "created_at": assignment.created_at,
        "student_count": len(students),
        "submitted_count": submitted,
        "pending_grading": pending,
        "my_attempt_id": mine.id if mine else None,
        "my_status": mine.status if mine else None,
        "my_total_score": mine.total_score if mine else None,
    }


@router.post("", response_model=AssignmentDetailOut, status_code=status.HTTP_201_CREATED)
def create(
    payload: AssignmentCreateIn,
    current: User = Depends(require_permission("learn:assignment:create")),
    db: Session = Depends(get_db),
) -> AssignmentDetailOut:
    assignment, exam = create_assignment(
        db,
        current,
        class_id=payload.class_id,
        title=payload.title,
        subject=payload.subject,
        chapter_ids=payload.chapter_ids,
        count=payload.count,
        q_types=payload.q_types,
        time_limit_min=payload.time_limit_min,
        due_at=payload.due_at,
    )
    db.commit()
    record_audit(
        db,
        user_id=current.id,
        action="assignment.create",
        after={
            "assignment_id": assignment.id,
            "class_id": assignment.class_id,
            "exam_id": exam.id,
            "question_count": len(exam.questions),
        },
    )
    school_class = db.get(SchoolClass, assignment.class_id)
    return AssignmentDetailOut(
        **_summary(db, assignment, school_class, current),
        students=[
            AssignmentStudentOut(
                student_id=student.id,
                nickname=student.nickname,
                status="not_started",
            )
            for student in class_students(db, assignment.class_id)
        ],
    )


@router.get("", response_model=List[AssignmentOut])
def list_assignments(
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[AssignmentOut]:
    stmt = select(Assignment)
    if current.role == "student":
        class_ids = list(
            db.scalars(
                select(ClassMember.class_id).where(ClassMember.student_id == current.id)
            )
        )
        if not class_ids:
            return []
        stmt = stmt.where(Assignment.class_id.in_(class_ids))
    elif current.role == "school_admin":
        class_ids = list(
            db.scalars(
                select(SchoolClass.id).where(SchoolClass.school_id == current.school_id)
            )
        )
        if not class_ids:
            return []
        stmt = stmt.where(Assignment.class_id.in_(class_ids))
    elif current.role not in ("super_admin", "admin"):
        stmt = stmt.where(Assignment.teacher_id == current.id)
    assignments = list(db.scalars(stmt.order_by(Assignment.id.desc()).limit(100)))
    result: List[AssignmentOut] = []
    for assignment in assignments:
        school_class = db.get(SchoolClass, assignment.class_id)
        if school_class is None:
            continue
        result.append(AssignmentOut(**_summary(db, assignment, school_class, current)))
    return result


@router.get("/{assignment_id}", response_model=AssignmentDetailOut)
def detail(
    assignment_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AssignmentDetailOut:
    assignment = _assignment_or_404(db, assignment_id)
    school_class = _ensure_visible(db, assignment, current)
    summary = _summary(db, assignment, school_class, current)
    # 学生只看到自己的作答状态，不暴露同班同学名单与成绩
    if current.role == "student":
        return AssignmentDetailOut(**summary, students=[])
    students = [
        AssignmentStudentOut(
            student_id=student.id,
            nickname=student.nickname,
            status="not_started",
        )
        for student in class_students(db, assignment.class_id)
    ]
    attempts = latest_attempts(db, assignment.exam_id)
    by_user = {attempt.user_id: attempt for attempt in attempts.values()}
    for index, student in enumerate(students):
        attempt = by_user.get(student.student_id)
        if attempt is None:
            continue
        students[index] = AssignmentStudentOut(
            student_id=student.student_id,
            nickname=student.nickname,
            attempt_id=attempt.id,
            status=attempt.status,
            objective_score=attempt.objective_score,
            subjective_score=attempt.subjective_score,
            total_score=attempt.total_score,
            submitted_at=attempt.submitted_at,
        )
    return AssignmentDetailOut(**summary, students=students)


@router.get("/{assignment_id}/grading", response_model=GradingListOut)
def grading_list(
    assignment_id: int,
    current: User = Depends(require_permission("learn:exam:grade")),
    db: Session = Depends(get_db),
) -> GradingListOut:
    assignment = _assignment_or_404(db, assignment_id)
    school_class = db.get(SchoolClass, assignment.class_id)
    if school_class is None:
        raise HTTPException(status_code=404, detail="班级不存在")
    if not class_authorized(db, current, school_class, assignment.subject):
        raise HTTPException(
            status_code=403,
            detail={"code": "GRADE_NOT_ALLOWED", "message": "无该班级的批改权限"},
        )
    items = grade_items(db, assignment)
    return GradingListOut(
        assignment_id=assignment.id,
        items=[GradingItemOut(**item) for item in items],
    )


@router.post("/{assignment_id}/grade", response_model=GradeBatchOut)
def grade(
    assignment_id: int,
    payload: GradeBatchIn,
    current: User = Depends(require_permission("learn:exam:grade")),
    db: Session = Depends(get_db),
) -> GradeBatchOut:
    assignment = _assignment_or_404(db, assignment_id)
    result = grade_batch(
        db,
        current,
        assignment,
        [item.model_dump() for item in payload.items],
    )
    db.commit()
    record_audit(
        db,
        user_id=current.id,
        action="assignment.grade",
        after={
            "assignment_id": assignment.id,
            "graded": [item.model_dump() for item in payload.items][:20],
        },
    )
    return GradeBatchOut(**result)
