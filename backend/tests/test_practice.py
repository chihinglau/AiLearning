from fastapi.testclient import TestClient


def test_public_content(
    client: TestClient, sample_chapter: int
) -> None:
    textbooks = client.get("/api/public/textbooks", params={"subject": "math", "grade": 1})
    assert textbooks.status_code == 200
    assert len(textbooks.json()) == 1

    chapters = client.get("/api/public/chapters", params={"textbook_id": textbooks.json()[0]["id"]})
    assert chapters.status_code == 200
    assert chapters.json()[0]["name"] == "10以内加减法"

    assert client.get("/api/public/knowledge-points", params={"subject": "math"}).status_code == 200


def test_student_cannot_access_admin(client: TestClient, student_headers: dict[str, str]) -> None:
    assert client.get("/api/admin/textbooks", headers=student_headers).status_code == 403


def test_practice_flow(
    client: TestClient,
    student_headers: dict[str, str],
    sample_chapter: int,
    sample_question: int,
) -> None:
    started = client.post(
        "/api/practice/start",
        headers=student_headers,
        json={"chapter_id": sample_chapter, "count": 5},
    )
    assert started.status_code == 200, started.text
    question = started.json()["questions"][0]
    assert "answer" not in question
    assert "analysis" not in question

    correct = client.post(
        "/api/practice/submit",
        headers=student_headers,
        json={"question_id": sample_question, "user_answer": {"value": "B"}, "duration_ms": 3500},
    )
    assert correct.status_code == 200
    assert correct.json()["is_correct"] is True

    wrong = client.post(
        "/api/practice/submit",
        headers=student_headers,
        json={"question_id": sample_question, "user_answer": {"value": "A"}, "duration_ms": 2000},
    )
    assert wrong.status_code == 200
    assert wrong.json()["is_correct"] is False

    history = client.get("/api/practice/history", headers=student_headers)
    assert history.status_code == 200
    assert len(history.json()) == 2


def test_practice_start_without_content(
    client: TestClient, student_headers: dict[str, str]
) -> None:
    response = client.post(
        "/api/practice/start", headers=student_headers, json={"chapter_id": 999, "count": 5}
    )
    assert response.status_code == 404
