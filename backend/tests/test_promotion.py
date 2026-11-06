"""P0-15 学期切换与学年升级任务测试。"""

from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.content import Textbook
from app.models.textbook import TextbookBinding
from app.models.user import GradeHistory, User
from app.services import promotion, textbook as textbook_service


def _student(client: TestClient, db: Session, phone: str, grade: int) -> User:
    response = client.post(
        "/api/auth/register", json={"phone": phone, "password": "pass1234", "grade": grade}
    )
    assert response.status_code == 201, response.text
    user = db.scalar(select(User).where(User.phone == phone))
    assert user is not None
    return user


def _seed_books(db: Session, grade: int, semester: str) -> dict[str, int]:
    books: dict[str, int] = {}
    for subject, version in [("chinese", "人教版"), ("math", "北师大版"), ("english", "牛津深圳版")]:
        book = Textbook(
            subject=subject, grade=grade, version=version, semester=semester, is_active=True
        )
        db.add(book)
        db.flush()
        books[subject] = book.id
    db.commit()
    return books


def test_switch_semester_rebinds_textbooks(client: TestClient, db: Session) -> None:
    user = _student(client, db, "13300000001", 3)
    _seed_books(db, 3, "first")
    _seed_books(db, 3, "second")
    textbook_service.auto_bind(db, user, now=datetime(2026, 11, 1))
    db.commit()

    result = promotion.switch_semester(db, now=datetime(2027, 2, 10))
    assert result.semester == "second"
    assert result.updated >= 1
    assert result.rebound == 1

    db.refresh(user)
    assert user.semester == "second"
    bindings = list(
        db.scalars(
            select(TextbookBinding).where(TextbookBinding.user_id == user.id)
        )
    )
    assert all(b.semester == "second" for b in bindings if b.status == "active")
    assert any(b.semester == "first" and b.status == "archived" for b in bindings)

    again = promotion.switch_semester(db, now=datetime(2027, 2, 11))
    assert again.updated == 0


def test_promote_grade_increments_once(client: TestClient, db: Session) -> None:
    user = _student(client, db, "13300000002", 3)
    before_token_version = user.token_version

    result = promotion.promote_grades(db, now=datetime(2026, 9, 1))
    assert result.school_year == "2026-2027"
    assert result.promoted >= 1

    db.refresh(user)
    assert user.grade == 4
    assert user.stage == "primary"
    assert user.grade_group == "primary_mid"
    assert user.token_version == before_token_version + 1

    histories = list(
        db.scalars(select(GradeHistory).where(GradeHistory.user_id == user.id))
    )
    assert len(histories) == 1
    assert histories[0].from_grade == 3
    assert histories[0].to_grade == 4
    assert histories[0].source == "system"

    again = promotion.promote_grades(db, now=datetime(2026, 9, 2))
    assert again.promoted == 0
    db.refresh(user)
    assert user.grade == 4


def test_promote_cross_stage_archives_bindings(client: TestClient, db: Session) -> None:
    user = _student(client, db, "13300000003", 6)
    _seed_books(db, 6, "first")
    textbook_service.auto_bind(db, user, now=datetime(2026, 9, 1))
    db.commit()

    promotion.promote_grades(db, now=datetime(2026, 9, 1))
    db.refresh(user)
    assert user.grade == 7
    assert user.stage == "junior"
    assert user.grade_group == "junior"

    bindings = list(
        db.scalars(
            select(TextbookBinding).where(TextbookBinding.user_id == user.id)
        )
    )
    assert bindings
    assert all(b.status == "archived" for b in bindings)


def test_grade_twelve_graduates(client: TestClient, db: Session) -> None:
    user = _student(client, db, "13300000004", 12)
    result = promotion.promote_grades(db, now=datetime(2026, 9, 1))
    assert result.promoted == 0
    assert result.graduated >= 1

    db.refresh(user)
    assert user.grade == 12
    assert user.graduated_at is not None


def test_promote_skips_outside_september(client: TestClient, db: Session) -> None:
    user = _student(client, db, "13300000005", 3)
    result = promotion.promote_grades(db, now=datetime(2026, 2, 10))
    assert result.skipped == "NOT_SEPTEMBER"
    assert result.promoted == 0
    db.refresh(user)
    assert user.grade == 3
