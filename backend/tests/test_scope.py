import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_student_access
from app.core.scope import (
    ensure_student_access,
    mask_phone,
    resolve_student_ids,
    scope_for_permission,
)
from app.models.user import ParentChildBinding, User


def _create_user(
    db: Session, phone: str, role: str, grade: int | None = None, school_id: int | None = None
) -> User:
    user = User(
        phone=phone,
        password_hash="hash",
        nickname=role,
        role=role,
        grade=grade,
        school_id=school_id,
    )
    db.add(user)
    db.flush()
    return user


def test_scope_for_permission_uses_requested_permission() -> None:
    assert scope_for_permission("student", "learn:stats:self:read") == "SELF"
    assert scope_for_permission("parent", "learn:stats:child:read") == "CHILD"
    assert scope_for_permission("teacher", "learn:stats:class:read") == "CLASS"
    assert scope_for_permission("admin", "system:config:write") == "ALL"
    assert scope_for_permission("student", "learn:stats:child:read") is None


def test_resolve_self_scope(db: Session) -> None:
    student = _create_user(db, "13900000001", "student", grade=3)
    assert resolve_student_ids(db, student, "SELF") == {student.id}


def test_resolve_child_scope_only_active_bindings(db: Session) -> None:
    parent = _create_user(db, "13900000002", "parent")
    active_child = _create_user(db, "13900000003", "student", grade=2)
    pending_child = _create_user(db, "13900000004", "student", grade=5)
    db.add_all(
        [
            ParentChildBinding(parent_id=parent.id, child_id=active_child.id, status="active"),
            ParentChildBinding(parent_id=parent.id, child_id=pending_child.id, status="pending"),
        ]
    )
    db.flush()

    assert resolve_student_ids(db, parent, "CHILD") == {active_child.id}


def test_resolve_school_scope(db: Session) -> None:
    admin = _create_user(db, "13900000005", "school_admin", school_id=10)
    same_school = _create_user(db, "13900000006", "student", grade=7, school_id=10)
    _create_user(db, "13900000007", "student", grade=7, school_id=11)

    assert resolve_student_ids(db, admin, "SCHOOL") == {same_school.id}
    assert resolve_student_ids(db, _create_user(db, "13900000008", "school_admin"), "SCHOOL") == set()


def test_resolve_all_and_none_scope(db: Session) -> None:
    admin = _create_user(db, "13900000009", "admin")
    assert resolve_student_ids(db, admin, "ALL") is None
    assert resolve_student_ids(db, admin, "NONE") == set()


def test_ensure_student_access_denied(db: Session) -> None:
    student = _create_user(db, "13900000010", "student", grade=3)
    other = _create_user(db, "13900000011", "student", grade=4)

    ensure_student_access(db, student, "SELF", student.id)
    with pytest.raises(HTTPException) as exc:
        ensure_student_access(db, student, "SELF", other.id)
    assert exc.value.status_code == 403
    assert exc.value.detail["code"] == "SCOPE_DENIED"


def test_require_student_access_dependency(db: Session) -> None:
    parent = _create_user(db, "13900000012", "parent")
    child = _create_user(db, "13900000013", "student", grade=2)
    other = _create_user(db, "13900000014", "student", grade=6)
    db.add(ParentChildBinding(parent_id=parent.id, child_id=child.id, status="active"))
    db.flush()

    dependency = require_student_access("learn:stats:child:read")
    access = dependency(student_id=child.id, current=parent, db=db)
    assert access.scope == "CHILD"
    assert access.student_id == child.id
    assert access.allowed_ids == {child.id}

    with pytest.raises(HTTPException) as exc:
        dependency(student_id=other.id, current=parent, db=db)
    assert exc.value.detail["code"] == "SCOPE_DENIED"


def test_require_student_access_defaults_to_self(db: Session) -> None:
    student = _create_user(db, "13900000015", "student", grade=4)
    dependency = require_student_access("learn:stats:self:read")

    access = dependency(current=student, db=db)
    assert access.student_id == student.id


def test_mask_phone() -> None:
    assert mask_phone("13812345678") == "138****5678"
    assert mask_phone(None) is None
    assert mask_phone("123") == "***"


def test_resolve_class_scope_is_safe_default(db: Session) -> None:
    teacher = _create_user(db, "13900000020", "teacher", school_id=10)
    assert resolve_student_ids(db, teacher, "CLASS") == set()


def test_resolve_unknown_scope_returns_empty(db: Session) -> None:
    student = _create_user(db, "13900000021", "student", grade=3)
    assert resolve_student_ids(db, student, "UNKNOWN") == set()


def test_resolve_child_scope_without_binding_returns_empty(db: Session) -> None:
    parent = _create_user(db, "13900000022", "parent")
    assert resolve_student_ids(db, parent, "CHILD") == set()


def test_ensure_student_access_all_scope_allows_any(db: Session) -> None:
    admin = _create_user(db, "13900000023", "admin")
    other = _create_user(db, "13900000024", "student", grade=6)
    ensure_student_access(db, admin, "ALL", other.id)


def test_scope_for_permission_denies_unrequested_scope() -> None:
    assert scope_for_permission("student", "learn:exam:report:self") == "SELF"
    assert scope_for_permission("parent", "learn:exam:take") is None
    assert scope_for_permission("teacher", "content:question:write") is None
    assert scope_for_permission("unknown_role", "learn:content:read") is None
