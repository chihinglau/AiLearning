import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.user import GradeHistory, User


def _add_student(db: Session, phone: str, grade: int) -> User:
    user = User(phone=phone, password_hash="hash", nickname="student", role="student", grade=grade)
    db.add(user)
    db.flush()
    return user


def test_user_new_grade_fields_defaults(db: Session) -> None:
    user = _add_student(db, "13700000001", 3)

    assert user.region == "shenzhen"
    assert user.semester == "first"
    assert user.token_version == 0
    assert user.grade_group is None
    assert user.enrollment_year is None
    assert user.graduated_at is None


def test_grade_history_unique_per_target_year(db: Session) -> None:
    user = _add_student(db, "13700000002", 4)
    history = GradeHistory(
        user_id=user.id,
        from_grade=3,
        to_grade=4,
        school_year="2026-2027",
        source="promotion",
    )
    db.add(history)
    db.commit()

    db.add(
        GradeHistory(
            user_id=user.id,
            from_grade=3,
            to_grade=4,
            school_year="2026-2027",
            source="promotion",
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
