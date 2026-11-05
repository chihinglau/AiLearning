from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401  注册全部模型
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.user import User

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture(autouse=True)
def prepare_schema() -> Generator[None, None, None]:
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db() -> Generator[Session, None, None]:
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _create_user(phone: str, password: str, role: str) -> None:
    session = TestingSessionLocal()
    try:
        session.add(
            User(phone=phone, password_hash=hash_password(password), nickname=role, role=role)
        )
        session.commit()
    finally:
        session.close()


def _login(client: TestClient, phone: str, password: str) -> dict[str, str]:
    response = client.post("/api/auth/login", data={"username": phone, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def admin_headers(client: TestClient) -> dict[str, str]:
    _create_user("13800000000", "admin123", "admin")
    return _login(client, "13800000000", "admin123")


@pytest.fixture
def student_headers(client: TestClient) -> dict[str, str]:
    _create_user("13900000000", "student123", "student")
    return _login(client, "13900000000", "student123")


@pytest.fixture
def sample_chapter(client: TestClient, admin_headers: dict[str, str]) -> int:
    textbook = client.post(
        "/api/admin/textbooks",
        headers=admin_headers,
        json={"subject": "math", "grade": 1, "version": "人教版", "semester": "first"},
    )
    assert textbook.status_code == 201, textbook.text
    chapter = client.post(
        "/api/admin/chapters",
        headers=admin_headers,
        json={
            "textbook_id": textbook.json()["id"],
            "grade": 1,
            "name": "10以内加减法",
            "order_index": 1,
            "summary": "掌握 10 以内口算",
        },
    )
    assert chapter.status_code == 201, chapter.text
    return int(chapter.json()["id"])


@pytest.fixture
def sample_question(client: TestClient, admin_headers: dict[str, str], sample_chapter: int) -> int:
    question = client.post(
        "/api/admin/questions",
        headers=admin_headers,
        json={
            "chapter_id": sample_chapter,
            "subject": "math",
            "q_type": "choice",
            "content": {"stem": "3 + 4 = ?"},
            "options": [
                {"key": "A", "text": "6"},
                {"key": "B", "text": "7"},
                {"key": "C", "text": "8"},
            ],
            "answer": {"value": "B"},
            "analysis": "3 + 4 = 7",
            "difficulty": 1,
            "tags": ["10以内加法"],
        },
    )
    assert question.status_code == 201, question.text
    return int(question.json()["id"])
