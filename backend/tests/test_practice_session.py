"""P0-23 练习会话：断点续答与结算。"""

from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.content import Chapter, KnowledgePoint, Question, Textbook
from app.models.user import User


def _setup(client: TestClient, db: Session) -> dict[str, Any]:
    registered = client.post(
        "/api/auth/register",
        json={"phone": "13700000003", "password": "pass1234", "grade": 3},
    )
    assert registered.status_code == 201, registered.text
    login = client.post(
        "/api/auth/login", data={"username": "13700000003", "password": "pass1234"}
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    book = Textbook(subject="math", grade=3, version="北师大版", semester="first")
    db.add(book)
    db.flush()
    chapter = Chapter(textbook_id=book.id, grade=3, name="第一单元", order_index=1)
    db.add(chapter)
    db.flush()
    for kp_index in range(2):
        kp = KnowledgePoint(
            subject="math", name=f"知识点{kp_index + 1}", grade=3,
            node_type="point", order_index=kp_index + 1,
        )
        db.add(kp)
        db.flush()
        for i in range(2):
            db.add(
                Question(
                    chapter_id=chapter.id, knowledge_point_id=kp.id, subject="math",
                    q_type="choice", difficulty=1,
                    content={"stem": f"{kp.name}-{i}"}, answer={"value": "A"},
                )
            )
    db.commit()
    return {"headers": headers, "chapter_id": chapter.id}


def _start(client: TestClient, ids: dict[str, Any], count: int = 3, seed: int = 11) -> dict[str, Any]:
    response = client.post(
        "/api/learn/start", headers=ids["headers"],
        json={
            "scope_type": "chapter", "scope_ids": [ids["chapter_id"]],
            "count": count, "seed": seed,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def _submit(client: TestClient, ids: dict[str, Any], question_id: int, value: str) -> None:
    response = client.post(
        "/api/learn/submit", headers=ids["headers"],
        json={"question_id": question_id, "user_answer": {"value": value}},
    )
    assert response.status_code == 200, response.text


def test_start_creates_session_and_resume_state(client: TestClient, db: Session) -> None:
    ids = _setup(client, db)
    started = _start(client, ids, count=3, seed=11)
    assert started["seed"] == 11
    session_id = started["session_id"]
    assert session_id is not None

    resumed = client.get(f"/api/learn/sessions/{session_id}", headers=ids["headers"])
    assert resumed.status_code == 200, resumed.text
    body = resumed.json()
    assert body["total_count"] == 3
    assert len(body["questions"]) == 3
    assert body["answered_count"] == 0
    assert body["next_index"] == 0
    assert body["finished_at"] is None
    assert all(a["answered"] is False for a in body["answers"])


def test_get_session_after_partial_answers(client: TestClient, db: Session) -> None:
    ids = _setup(client, db)
    started = _start(client, ids)
    session_id = started["session_id"]
    questions = started["questions"]
    _submit(client, ids, questions[0]["id"], "A")
    _submit(client, ids, questions[1]["id"], "B")

    resumed = client.get(f"/api/learn/sessions/{session_id}", headers=ids["headers"])
    body = resumed.json()
    assert body["answered_count"] == 2
    assert body["correct_count"] == 1
    assert body["next_index"] == 2
    assert body["answers"][0]["is_correct"] is True
    assert body["answers"][1]["is_correct"] is False


def test_finish_session_is_idempotent(client: TestClient, db: Session) -> None:
    ids = _setup(client, db)
    started = _start(client, ids)
    session_id = started["session_id"]
    _submit(client, ids, started["questions"][0]["id"], "A")
    _submit(client, ids, started["questions"][1]["id"], "B")

    first = client.post(f"/api/learn/sessions/{session_id}/finish", headers=ids["headers"])
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["session"]["answered_count"] == 2
    assert body["session"]["correct_count"] == 1
    assert body["accuracy"] == 0.5
    assert body["wrong_count"] == 1
    assert body["session"]["finished_at"] is not None
    assert body["kp_stats"] and body["kp_stats"][0]["answered"] >= 1

    second = client.post(f"/api/learn/sessions/{session_id}/finish", headers=ids["headers"])
    assert second.status_code == 200
    assert second.json()["session"]["finished_at"] == body["session"]["finished_at"]
    assert second.json()["accuracy"] == body["accuracy"]


def test_session_is_private_to_owner(client: TestClient, db: Session) -> None:
    ids = _setup(client, db)
    session_id = _start(client, ids)["session_id"]

    other = client.post(
        "/api/auth/register",
        json={"phone": "13700000004", "password": "pass1234", "grade": 3},
    )
    assert other.status_code == 201, other.text
    login = client.post(
        "/api/auth/login", data={"username": "13700000004", "password": "pass1234"}
    )
    other_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    assert client.get(
        f"/api/learn/sessions/{session_id}", headers=other_headers
    ).status_code == 404
    assert client.post(
        f"/api/learn/sessions/{session_id}/finish", headers=other_headers
    ).status_code == 404


def test_finish_unknown_session_returns_404(client: TestClient, db: Session) -> None:
    ids = _setup(client, db)
    response = client.post("/api/learn/sessions/9999/finish", headers=ids["headers"])
    assert response.status_code == 404
