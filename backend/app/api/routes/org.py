from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import (
    has_permission,
    require_admin,
    require_any_permission,
    require_permission,
)
from app.core.permissions import ALL_PERMISSIONS
from app.core.scope import teacher_class_ids
from app.db.session import get_db
from app.models.content import KnowledgePoint, Question
from app.models.org import ClassMember, School, SchoolClass, TeacherClassAssignment
from app.models.practice import MasteryScore, StudentQuestionRecord
from app.models.user import User
from app.schemas.org import (
    AssignmentCreate,
    AssignmentOut,
    ClassCreate,
    ClassMemberAdd,
    ClassMemberAddOut,
    ClassOut,
    ClassStatsOut,
    ClassWeakPointOut,
    SchoolCreate,
    SchoolOut,
)
from app.services.audit import record_audit

router = APIRouter(prefix="/org", tags=["学校组织"])

TEACHER_ROLES = ("teacher", "head_teacher")


def _forbidden(code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"code": code, "message": message},
    )


def _unprocessable(code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=422,
        detail={"code": code, "message": message},
    )


def _is_super(user: User) -> bool:
    return has_permission(user, ALL_PERMISSIONS)


def _resolve_school_id(user: User, requested: Optional[int]) -> int:
    if _is_super(user):
        if requested is None:
            raise _unprocessable("SCHOOL_REQUIRED", "请指定学校")
        return requested
    if user.school_id is None:
        raise _forbidden("SCHOOL_UNBOUND", "账号未绑定学校")
    if requested is not None and requested != user.school_id:
        raise _forbidden("CROSS_SCHOOL", "无权操作其他学校")
    return user.school_id


def _ensure_class_visible(db: Session, user: User, room: SchoolClass) -> None:
    if _is_super(user):
        return
    if user.role == "school_admin":
        if room.school_id != user.school_id:
            raise _forbidden("CROSS_SCHOOL", "无权访问其他学校班级")
        return
    if room.id not in teacher_class_ids(db, user):
        raise _forbidden("CLASS_DENIED", "无权访问该班级")


def _class_out(db: Session, room: SchoolClass) -> ClassOut:
    member_count = int(
        db.scalar(
            select(func.count()).select_from(ClassMember).where(
                ClassMember.class_id == room.id
            )
        )
        or 0
    )
    return ClassOut(
        id=room.id,
        school_id=room.school_id,
        grade=room.grade,
        name=room.name,
        head_teacher_id=room.head_teacher_id,
        school_year=room.school_year,
        member_count=member_count,
    )


@router.get("/schools", response_model=List[SchoolOut])
def list_schools(
    current: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> List[School]:
    return list(db.scalars(select(School).order_by(School.id)))


@router.post("/schools", response_model=SchoolOut, status_code=status.HTTP_201_CREATED)
def create_school(
    payload: SchoolCreate,
    current: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> School:
    school = School(name=payload.name, region=payload.region)
    db.add(school)
    db.commit()
    db.refresh(school)
    record_audit(
        db,
        user_id=current.id,
        action="org.school.create",
        after={"id": school.id, "name": school.name, "region": school.region},
    )
    return school


@router.get("/classes", response_model=List[ClassOut])
def list_classes(
    current: User = Depends(
        require_any_permission("org:class:manage", "learn:stats:class:read")
    ),
    db: Session = Depends(get_db),
) -> List[ClassOut]:
    if _is_super(current):
        rooms = list(db.scalars(select(SchoolClass).order_by(SchoolClass.id)))
    elif current.role == "school_admin":
        if current.school_id is None:
            raise _forbidden("SCHOOL_UNBOUND", "账号未绑定学校")
        rooms = list(
            db.scalars(
                select(SchoolClass)
                .where(SchoolClass.school_id == current.school_id)
                .order_by(SchoolClass.id)
            )
        )
    else:
        ids = teacher_class_ids(db, current)
        if not ids:
            return []
        rooms = list(
            db.scalars(select(SchoolClass).where(SchoolClass.id.in_(ids)).order_by(SchoolClass.id))
        )
    return [_class_out(db, room) for room in rooms]


@router.post("/classes", response_model=ClassOut, status_code=status.HTTP_201_CREATED)
def create_class(
    payload: ClassCreate,
    current: User = Depends(require_permission("org:class:manage")),
    db: Session = Depends(get_db),
) -> ClassOut:
    school_id = _resolve_school_id(current, payload.school_id)
    if db.get(School, school_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="学校不存在")

    exists = db.scalar(
        select(SchoolClass).where(
            SchoolClass.school_id == school_id,
            SchoolClass.grade == payload.grade,
            SchoolClass.name == payload.name,
        )
    )
    if exists is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "CLASS_EXISTS", "message": "同校同年级同名班级已存在"},
        )

    if payload.head_teacher_id is not None:
        head = db.get(User, payload.head_teacher_id)
        if head is None or head.role not in TEACHER_ROLES:
            raise _unprocessable("HEAD_TEACHER_INVALID", "班主任必须是教师角色")
        if head.school_id != school_id:
            raise _unprocessable("CROSS_SCHOOL", "班主任与班级不在同一学校")

    room = SchoolClass(
        school_id=school_id,
        grade=payload.grade,
        name=payload.name,
        school_year=payload.school_year,
        head_teacher_id=payload.head_teacher_id,
    )
    db.add(room)
    db.commit()
    db.refresh(room)
    record_audit(
        db,
        user_id=current.id,
        action="org.class.create",
        after={
            "id": room.id,
            "school_id": room.school_id,
            "grade": room.grade,
            "name": room.name,
        },
    )
    return _class_out(db, room)


@router.get("/classes/{class_id}/stats", response_model=ClassStatsOut)
def class_stats(
    class_id: int,
    subject: Optional[str] = Query(default=None, max_length=20),
    current: User = Depends(require_permission("learn:stats:class:read")),
    db: Session = Depends(get_db),
) -> ClassStatsOut:
    """班级学情聚合（D-03 §6.5）：只返回聚合值，不返回学生逐题作答原文。"""
    room = db.get(SchoolClass, class_id)
    if room is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="班级不存在")

    if not _is_super(current):
        if current.role == "school_admin":
            if room.school_id != current.school_id:
                raise _forbidden("SCOPE_DENIED", "无权查看该班级学情")
        elif class_id not in teacher_class_ids(db, current, subject):
            raise _forbidden("SCOPE_DENIED", "无权查看该班级学情")

    member_ids = list(
        db.scalars(select(ClassMember.student_id).where(ClassMember.class_id == class_id))
    )
    empty = ClassStatsOut(
        class_id=room.id,
        class_name=room.name,
        grade=room.grade,
        subject=subject,
        student_count=len(member_ids),
        active_student_count=0,
        submission_rate=0.0,
        total_answered=0,
        accuracy=0.0,
        avg_mastery=0.0,
        weak_points=[],
    )
    if not member_ids:
        return empty

    record_filters = [StudentQuestionRecord.user_id.in_(member_ids)]
    mastery_filters = [MasteryScore.user_id.in_(member_ids)]
    if subject:
        record_filters.append(Question.subject == subject)
        mastery_filters.append(KnowledgePoint.subject == subject)

    total_stmt = select(func.count(StudentQuestionRecord.id))
    correct_stmt = select(func.count(StudentQuestionRecord.id)).where(
        StudentQuestionRecord.is_correct.is_(True)
    )
    active_stmt = select(func.count(func.distinct(StudentQuestionRecord.user_id)))
    if subject:
        total_stmt = total_stmt.join(Question, Question.id == StudentQuestionRecord.question_id)
        correct_stmt = correct_stmt.join(
            Question, Question.id == StudentQuestionRecord.question_id
        )
        active_stmt = active_stmt.join(Question, Question.id == StudentQuestionRecord.question_id)
    total = db.scalar(total_stmt.where(*record_filters)) or 0
    correct = db.scalar(correct_stmt.where(*record_filters)) or 0
    week_ago = datetime.utcnow() - timedelta(days=7)
    active = (
        db.scalar(
            active_stmt.where(
                *record_filters,
                StudentQuestionRecord.attempted_at >= week_ago,
            )
        )
        or 0
    )

    mastery_stmt = select(func.avg(MasteryScore.score))
    if subject:
        mastery_stmt = mastery_stmt.join(
            KnowledgePoint, KnowledgePoint.id == MasteryScore.knowledge_point_id
        )
    avg_mastery = float(db.scalar(mastery_stmt.where(*mastery_filters)) or 0.0)

    weak_stmt = (
        select(
            MasteryScore.knowledge_point_id,
            func.avg(MasteryScore.score).label("avg_score"),
        )
        .join(KnowledgePoint, KnowledgePoint.id == MasteryScore.knowledge_point_id)
        .where(*mastery_filters)
        .having(func.avg(MasteryScore.score) < 70)
        .group_by(MasteryScore.knowledge_point_id)
        .order_by(func.avg(MasteryScore.score).asc())
        .limit(5)
    )
    weak_points: list[ClassWeakPointOut] = []
    for kp_id, avg_score in db.execute(weak_stmt).all():
        kp = db.get(KnowledgePoint, kp_id)
        if kp is None:
            continue
        weak_points.append(
            ClassWeakPointOut(
                knowledge_point_id=kp.id,
                name=kp.name,
                subject=kp.subject,
                avg_mastery=round(float(avg_score), 1),
            )
        )

    student_count = len(member_ids)
    return ClassStatsOut(
        class_id=room.id,
        class_name=room.name,
        grade=room.grade,
        subject=subject,
        student_count=student_count,
        active_student_count=int(active),
        submission_rate=round(active / student_count, 3) if student_count else 0.0,
        total_answered=int(total),
        accuracy=round(correct / total, 3) if total else 0.0,
        avg_mastery=round(avg_mastery, 1),
        weak_points=weak_points,
    )


@router.get("/classes/{class_id}/members", response_model=List[int])
def list_class_members(
    class_id: int,
    current: User = Depends(
        require_any_permission("org:student:manage", "learn:stats:class:read")
    ),
    db: Session = Depends(get_db),
) -> List[int]:
    room = db.get(SchoolClass, class_id)
    if room is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="班级不存在")
    _ensure_class_visible(db, current, room)
    return list(
        db.scalars(select(ClassMember.student_id).where(ClassMember.class_id == class_id))
    )


@router.post(
    "/classes/{class_id}/members",
    response_model=ClassMemberAddOut,
    status_code=status.HTTP_201_CREATED,
)
def add_class_members(
    class_id: int,
    payload: ClassMemberAdd,
    current: User = Depends(require_permission("org:student:manage")),
    db: Session = Depends(get_db),
) -> ClassMemberAddOut:
    room = db.get(SchoolClass, class_id)
    if room is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="班级不存在")
    _ensure_class_visible(db, current, room)

    students = list(
        db.scalars(select(User).where(User.id.in_(payload.student_ids)))
    )
    found = {student.id: student for student in students}
    for student_id in payload.student_ids:
        student = found.get(student_id)
        if student is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "STUDENT_NOT_FOUND", "message": f"学生 {student_id} 不存在"},
            )
        if student.role != "student":
            raise _unprocessable("STUDENT_ROLE_REQUIRED", f"账号 {student_id} 不是学生")
        if student.school_id != room.school_id:
            raise _unprocessable("CROSS_SCHOOL", f"学生 {student_id} 与班级不在同一学校")
        if student.grade != room.grade:
            raise _unprocessable("GRADE_MISMATCH", f"学生 {student_id} 年级与班级不一致")

    existing = set(
        db.scalars(
            select(ClassMember.student_id).where(
                ClassMember.class_id == class_id,
                ClassMember.student_id.in_(payload.student_ids),
            )
        )
    )
    added = 0
    for student_id in payload.student_ids:
        if student_id in existing:
            continue
        db.add(ClassMember(class_id=class_id, student_id=student_id))
        added += 1
    db.commit()
    record_audit(
        db,
        user_id=current.id,
        action="org.member.add",
        after={
            "class_id": class_id,
            "student_ids": [sid for sid in payload.student_ids if sid not in existing],
        },
    )
    return ClassMemberAddOut(added=added, skipped=len(payload.student_ids) - added)


@router.get("/assignments", response_model=List[AssignmentOut])
def list_assignments(
    current: User = Depends(
        require_any_permission("org:teacher:assign", "learn:stats:class:read")
    ),
    db: Session = Depends(get_db),
) -> List[TeacherClassAssignment]:
    stmt = select(TeacherClassAssignment).order_by(TeacherClassAssignment.id)
    if not _is_super(current):
        if current.role == "school_admin":
            if current.school_id is None:
                raise _forbidden("SCHOOL_UNBOUND", "账号未绑定学校")
            stmt = stmt.join(
                SchoolClass, SchoolClass.id == TeacherClassAssignment.class_id
            ).where(SchoolClass.school_id == current.school_id)
        else:
            stmt = stmt.where(TeacherClassAssignment.teacher_id == current.id)
    return list(db.scalars(stmt))


@router.post("/assignments", response_model=AssignmentOut, status_code=status.HTTP_201_CREATED)
def create_assignment(
    payload: AssignmentCreate,
    current: User = Depends(require_permission("org:teacher:assign")),
    db: Session = Depends(get_db),
) -> TeacherClassAssignment:
    room = db.get(SchoolClass, payload.class_id)
    if room is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="班级不存在")
    if not _is_super(current) and room.school_id != current.school_id:
        raise _forbidden("CROSS_SCHOOL", "无权操作其他学校班级")

    teacher = db.get(User, payload.teacher_id)
    if teacher is None or teacher.role not in TEACHER_ROLES:
        raise _unprocessable("TEACHER_ROLE_REQUIRED", "指定账号不是教师")
    if teacher.school_id != room.school_id:
        raise _unprocessable("CROSS_SCHOOL", "教师与班级不在同一学校")
    if teacher.teacher_subjects and payload.subject not in teacher.teacher_subjects:
        raise _unprocessable("SUBJECT_NOT_ALLOWED", "该教师未登记此学科")
    if teacher.grade_start is not None and room.grade < teacher.grade_start:
        raise _unprocessable("GRADE_OUT_OF_RANGE", "班级年级低于教师可选范围")
    if teacher.grade_end is not None and room.grade > teacher.grade_end:
        raise _unprocessable("GRADE_OUT_OF_RANGE", "班级年级高于教师可选范围")

    exists = db.scalar(
        select(TeacherClassAssignment).where(
            TeacherClassAssignment.teacher_id == payload.teacher_id,
            TeacherClassAssignment.class_id == payload.class_id,
            TeacherClassAssignment.subject == payload.subject,
        )
    )
    if exists is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "ASSIGNMENT_EXISTS", "message": "授课分配已存在"},
        )

    if payload.role_in_class == "head_teacher":
        if room.head_teacher_id is not None and room.head_teacher_id != teacher.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "HEAD_TEACHER_EXISTS", "message": "该班级已设置班主任"},
            )
        room.head_teacher_id = teacher.id

    assignment = TeacherClassAssignment(
        teacher_id=payload.teacher_id,
        class_id=payload.class_id,
        subject=payload.subject,
        role_in_class=payload.role_in_class,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    record_audit(
        db,
        user_id=current.id,
        action="org.teacher.assign",
        after={
            "id": assignment.id,
            "teacher_id": assignment.teacher_id,
            "class_id": assignment.class_id,
            "subject": assignment.subject,
            "role_in_class": assignment.role_in_class,
        },
    )
    return assignment
