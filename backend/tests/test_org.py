"""P1-01 学校/班级/成员/授课关系与 CLASS 范围解析。"""

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.scope import resolve_student_ids
from app.models.org import ClassMember, School, SchoolClass, TeacherClassAssignment
from app.models.user import User


def _user(db: Session, phone: str, role: str, school_id: int | None = None) -> User:
    user = User(
        phone=phone,
        password_hash="hash",
        nickname=role,
        role=role,
        school_id=school_id,
    )
    db.add(user)
    db.flush()
    return user


def _school_class(db: Session, school: School, name: str = "四年级1班") -> SchoolClass:
    room = SchoolClass(school_id=school.id, grade=4, name=name, school_year="2026-2027")
    db.add(room)
    db.flush()
    return room


def test_class_scope_follows_teacher_assignment_subject(db: Session) -> None:
    school = School(name="测试小学")
    db.add(school)
    db.flush()

    room = _school_class(db, school)
    teacher = _user(db, "13500000001", "teacher", school_id=school.id)
    other_teacher = _user(db, "13500000002", "teacher", school_id=school.id)
    student = _user(db, "13500000003", "student", school_id=school.id)
    other_student = _user(db, "13500000004", "student", school_id=school.id)

    db.add_all(
        [
            TeacherClassAssignment(
                teacher_id=teacher.id, class_id=room.id, subject="math"
            ),
            ClassMember(class_id=room.id, student_id=student.id),
        ]
    )
    db.flush()

    assert resolve_student_ids(db, teacher, "CLASS", subject="math") == {student.id}
    assert resolve_student_ids(db, teacher, "CLASS", subject="chinese") == set()
    assert resolve_student_ids(db, teacher, "CLASS") == {student.id}
    assert resolve_student_ids(db, other_teacher, "CLASS") == set()
    assert resolve_student_ids(db, other_teacher, "CLASS", subject="math") == set()
    assert other_student.id not in resolve_student_ids(db, teacher, "CLASS")


def test_head_teacher_sees_all_subjects_of_class(db: Session) -> None:
    school = School(name="测试中学")
    db.add(school)
    db.flush()

    room = _school_class(db, school, name="七年级2班")
    head = _user(db, "13500000005", "head_teacher", school_id=school.id)
    student = _user(db, "13500000006", "student", school_id=school.id)

    room.head_teacher_id = head.id
    db.add_all(
        [
            TeacherClassAssignment(
                teacher_id=head.id,
                class_id=room.id,
                subject="math",
                role_in_class="head_teacher",
            ),
            ClassMember(class_id=room.id, student_id=student.id),
        ]
    )
    db.flush()

    assert resolve_student_ids(db, head, "CLASS", subject="math") == {student.id}
    assert resolve_student_ids(db, head, "CLASS", subject="chinese") == {student.id}
    assert resolve_student_ids(db, head, "CLASS") == {student.id}


def test_class_scope_rejects_cross_school_and_unbound_teacher(db: Session) -> None:
    school_a = School(name="A 校")
    school_b = School(name="B 校")
    db.add_all([school_a, school_b])
    db.flush()

    room_b = _school_class(db, school_b, name="八年级3班")
    teacher_a = _user(db, "13500000007", "teacher", school_id=school_a.id)
    unbound = _user(db, "13500000008", "teacher")
    student = _user(db, "13500000009", "student", school_id=school_b.id)

    db.add_all(
        [
            TeacherClassAssignment(
                teacher_id=teacher_a.id, class_id=room_b.id, subject="math"
            ),
            TeacherClassAssignment(teacher_id=unbound.id, class_id=room_b.id, subject="math"),
            ClassMember(class_id=room_b.id, student_id=student.id),
        ]
    )
    db.flush()

    assert resolve_student_ids(db, teacher_a, "CLASS", subject="math") == set()
    assert resolve_student_ids(db, unbound, "CLASS", subject="math") == set()


def test_class_member_and_assignment_are_unique(db: Session) -> None:
    school = School(name="重复约束小学")
    db.add(school)
    db.flush()
    room = _school_class(db, school)
    teacher = _user(db, "13500000010", "teacher", school_id=school.id)
    student = _user(db, "13500000011", "student", school_id=school.id)

    db.add(ClassMember(class_id=room.id, student_id=student.id))
    db.add(
        TeacherClassAssignment(teacher_id=teacher.id, class_id=room.id, subject="math")
    )
    db.commit()

    with pytest.raises(IntegrityError):
        db.add(ClassMember(class_id=room.id, student_id=student.id))
        db.flush()
    db.rollback()

    with pytest.raises(IntegrityError):
        db.add(
            TeacherClassAssignment(teacher_id=teacher.id, class_id=room.id, subject="math")
        )
        db.flush()
