"""TT-04 读题音频接口：304、404 AUDIO_NOT_READY、403、限流与返工清单。"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.rate_limit import rate_limiter
from app.core.security import hash_password
from app.models.content import Chapter, Question
from app.models.user import User
from app.services import question_audio as audio_service
from app.services import question_speech as speech
from tests.conftest import TestingSessionLocal

AUDIO_PATH = "/api/learn/questions/{question_id}/audio"


def _create_user(phone: str, password: str, role: str) -> None:
    session = TestingSessionLocal()
    try:
        session.add(
            User(
                phone=phone,
                password_hash=hash_password(password),
                nickname=role,
                role=role,
            )
        )
        session.commit()
    finally:
        session.close()


def _login(client: TestClient, phone: str, password: str) -> dict[str, str]:
    response = client.post(
        "/api/auth/login", data={"username": phone, "password": password}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _write_audio(
    db, out_dir: Path, question_id: int, *, voice: str | None = None, speed: float = 1.0
) -> str:
    question = db.get(Question, question_id)
    text = speech.text_for_question(question)
    key = speech.cache_key(
        text, voice or speech.voice_for_subject(question.subject), speed
    )
    path = out_dir / speech.audio_rel_path(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"OggS-test")
    return key


@pytest.fixture
def audio_dir(monkeypatch, tmp_path: Path) -> Path:
    monkeypatch.setattr(settings, "question_audio_dir", str(tmp_path))
    return tmp_path


def test_audio_served_with_etag_and_304(
    client, db, student_headers, sample_question, audio_dir: Path
) -> None:
    key = _write_audio(db, audio_dir, sample_question)

    response = client.get(
        AUDIO_PATH.format(question_id=sample_question), headers=student_headers
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/ogg"
    assert response.headers["etag"] == f'"{key}"'
    assert "max-age=2592000" in response.headers["cache-control"]
    assert response.content == b"OggS-test"

    cached = client.get(
        AUDIO_PATH.format(question_id=sample_question),
        headers={**student_headers, "If-None-Match": f'"{key}"'},
    )
    assert cached.status_code == 304
    assert cached.headers["etag"] == f'"{key}"'


def test_audio_missing_returns_404(
    client, student_headers, sample_question, audio_dir: Path
) -> None:
    response = client.get(
        AUDIO_PATH.format(question_id=sample_question), headers=student_headers
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "AUDIO_NOT_READY"


def test_audio_rework_listed_returns_404(
    client, db, student_headers, sample_question, audio_dir: Path
) -> None:
    _write_audio(db, audio_dir, sample_question)
    (audio_dir / "rework.json").write_text(
        f'{{"question_ids": [{sample_question}]}}', encoding="utf-8"
    )

    response = client.get(
        AUDIO_PATH.format(question_id=sample_question), headers=student_headers
    )
    assert response.status_code == 404
    assert audio_service.rework_ids() == {sample_question}


def test_audio_grade_out_of_range_returns_404(
    client, db, student_headers, sample_chapter, audio_dir: Path
) -> None:
    chapter = Chapter(
        textbook_id=db.get(Chapter, sample_chapter).textbook_id,
        grade=4,
        name="四年级单元",
        order_index=1,
    )
    db.add(chapter)
    db.flush()
    question = Question(
        chapter_id=chapter.id,
        subject="math",
        q_type="choice",
        content={"stem": "4 年级题目"},
        options=[{"key": "A", "text": "1"}],
        answer={"value": "A"},
        status="published",
    )
    db.add(question)
    db.commit()
    _write_audio(db, audio_dir, question.id)

    response = client.get(
        AUDIO_PATH.format(question_id=question.id), headers=student_headers
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "AUDIO_NOT_READY"


def test_audio_draft_question_returns_404(
    client, db, student_headers, sample_question, audio_dir: Path
) -> None:
    _write_audio(db, audio_dir, sample_question)
    question = db.get(Question, sample_question)
    question.status = "draft"
    db.commit()

    response = client.get(
        AUDIO_PATH.format(question_id=sample_question), headers=student_headers
    )
    assert response.status_code == 404


def test_audio_permission_denied_returns_403(
    client, db, sample_question, audio_dir: Path
) -> None:
    _write_audio(db, audio_dir, sample_question)
    _create_user("13900000009", "restricted123", "restricted")
    headers = _login(client, "13900000009", "restricted123")

    response = client.get(
        AUDIO_PATH.format(question_id=sample_question), headers=headers
    )
    assert response.status_code == 403


def test_audio_rate_limited(
    client, db, student_headers, sample_question, audio_dir: Path, monkeypatch
) -> None:
    _write_audio(db, audio_dir, sample_question)
    monkeypatch.setattr(settings, "question_audio_rate_limit_per_minute", 2)
    rate_limiter.reset()

    for _ in range(2):
        allowed = client.get(
            AUDIO_PATH.format(question_id=sample_question), headers=student_headers
        )
        assert allowed.status_code == 200

    limited = client.get(
        AUDIO_PATH.format(question_id=sample_question), headers=student_headers
    )
    assert limited.status_code == 429
    assert limited.json()["detail"]["code"] == "RATE_LIMITED"
    assert int(limited.headers["retry-after"]) >= 1


def test_etag_matching_variants() -> None:
    assert audio_service.etag_matches('"abc"', '"abc"') is True
    assert audio_service.etag_matches("abc", '"abc"') is True
    assert audio_service.etag_matches('"x", "abc"', '"abc"') is True
    assert audio_service.etag_matches("*", '"abc"') is True
    assert audio_service.etag_matches('W/"abc"', '"abc"') is False
    assert audio_service.etag_matches(None, '"abc"') is False
