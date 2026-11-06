from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.content import Textbook
from app.models.textbook import TextbookBinding
from app.models.user import User


def _students(client: TestClient, phone: str, grade: int = 3) -> dict[str, str]:
    response = client.post(
        "/api/auth/register", json={"phone": phone, "password": "pass1234", "grade": grade}
    )
    assert response.status_code == 201, response.text
    login = client.post("/api/auth/login", data={"username": phone, "password": "pass1234"})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _seed_books(db: Session) -> dict[tuple[str, str, str], int]:
    specs = [
        ("chinese", "人教版", "first"),
        ("chinese", "人教版", "second"),
        ("math", "北师大版", "first"),
        ("math", "北师大版", "second"),
        ("english", "牛津深圳版", "first"),
        ("english", "牛津深圳版", "second"),
        ("english", "人教版", "first"),
    ]
    books: dict[tuple[str, str, str], int] = {}
    for subject, version, semester in specs:
        book = Textbook(
            subject=subject, grade=3, version=version, semester=semester, is_active=True
        )
        db.add(book)
        db.flush()
        books[(subject, version, semester)] = book.id
    db.commit()
    return books


def test_recommend_prefers_shenzhen_edition(client: TestClient, db: Session) -> None:
    books = _seed_books(db)
    headers = _students(client, "13100000001")

    response = client.get("/api/me/textbooks/recommend", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["semester"] == "first"
    subjects = {item["subject"]: item for item in body["subjects"]}
    assert set(subjects) == {"chinese", "math", "english"}
    assert subjects["english"]["version"] == "牛津深圳版"
    assert subjects["english"]["textbook_id"] == books[("english", "牛津深圳版", "first")]


def test_auto_bind_is_idempotent(client: TestClient, db: Session) -> None:
    _seed_books(db)
    headers = _students(client, "13100000002")

    first = client.post("/api/me/textbooks/auto-bind", headers=headers)
    assert first.status_code == 201, first.text
    assert first.json()["bound"] == 3

    second = client.post("/api/me/textbooks/auto-bind", headers=headers)
    assert second.status_code == 201
    assert second.json()["bound"] == 3

    listed = client.get("/api/me/textbooks", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 3

    student = db.scalar(select(User).where(User.phone == "13100000002"))
    assert student.semester == "first"
    assert db.scalar(
        select(TextbookBinding).where(TextbookBinding.user_id == student.id)
    ) is not None


def test_manual_bind_archives_previous(client: TestClient, db: Session) -> None:
    books = _seed_books(db)
    headers = _students(client, "13100000003")
    client.post("/api/me/textbooks/auto-bind", headers=headers)

    response = client.post(
        "/api/me/textbooks/bind",
        json={"subject": "english", "textbook_id": books[("english", "人教版", "first")]},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    assert response.json()["textbook"]["version"] == "人教版"
    assert response.json()["source"] == "manual"

    listed = client.get("/api/me/textbooks", headers=headers).json()
    english = [item for item in listed if item["subject"] == "english"]
    assert len(english) == 1
    assert english[0]["textbook"]["version"] == "人教版"

    student = db.scalar(select(User).where(User.phone == "13100000003"))
    archived = db.scalar(
        select(TextbookBinding).where(
            TextbookBinding.user_id == student.id,
            TextbookBinding.textbook_id == books[("english", "牛津深圳版", "first")],
        )
    )
    assert archived.status == "archived"


def test_unbind_removes_from_active_list(client: TestClient, db: Session) -> None:
    _seed_books(db)
    headers = _students(client, "13100000004")
    client.post("/api/me/textbooks/auto-bind", headers=headers)
    bindings = client.get("/api/me/textbooks", headers=headers).json()
    target = bindings[0]["id"]

    response = client.delete(f"/api/me/textbooks/{target}", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "archived"

    remaining = client.get("/api/me/textbooks", headers=headers).json()
    assert target not in [item["id"] for item in remaining]


def test_bind_rejects_subject_mismatch(client: TestClient, db: Session) -> None:
    books = _seed_books(db)
    headers = _students(client, "13100000005")
    response = client.post(
        "/api/me/textbooks/bind",
        json={"subject": "math", "textbook_id": books[("english", "人教版", "first")]},
        headers=headers,
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "SUBJECT_MISMATCH"


def test_bind_unknown_textbook(client: TestClient, db: Session) -> None:
    headers = _students(client, "13100000006")
    response = client.post(
        "/api/me/textbooks/bind", json={"subject": "math", "textbook_id": 999999}, headers=headers
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "TEXTBOOK_NOT_FOUND"


def test_parent_cannot_manage_bindings(client: TestClient) -> None:
    client.post(
        "/api/auth/register",
        json={"phone": "13100000007", "password": "pass1234", "role": "parent"},
    )
    login = client.post(
        "/api/auth/login", data={"username": "13100000007", "password": "pass1234"}
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    response = client.get("/api/me/textbooks", headers=headers)
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "NOT_STUDENT"
