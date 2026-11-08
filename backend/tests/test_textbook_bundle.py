from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.content import KnowledgePoint, Question


def _create_textbook(client: TestClient, headers: dict[str, str]) -> int:
    response = client.post(
        "/api/admin/textbooks",
        headers=headers,
        json={"subject": "math", "grade": 1, "version": "人教版", "semester": "first"},
    )
    assert response.status_code == 201, response.text
    return int(response.json()["id"])


def _create_chapter(
    client: TestClient, headers: dict[str, str], textbook_id: int, name: str
) -> int:
    response = client.post(
        "/api/admin/chapters",
        headers=headers,
        json={
            "textbook_id": textbook_id,
            "grade": 1,
            "name": name,
            "order_index": 1,
        },
    )
    assert response.status_code == 201, response.text
    return int(response.json()["id"])


def _create_question(
    client: TestClient,
    headers: dict[str, str],
    chapter_id: int,
    kp_id: int,
    stem: str,
) -> int:
    response = client.post(
        "/api/admin/questions",
        headers=headers,
        json={
            "chapter_id": chapter_id,
            "knowledge_point_id": kp_id,
            "subject": "math",
            "q_type": "choice",
            "content": {"stem": stem},
            "options": [{"key": "A", "text": "1"}, {"key": "B", "text": "2"}],
            "answer": {"value": "A"},
            "analysis": f"{stem} 的解析",
            "difficulty": 2,
        },
    )
    assert response.status_code == 201, response.text
    return int(response.json()["id"])


def test_bundle_requires_login(client: TestClient, admin_headers: dict[str, str]) -> None:
    textbook_id = _create_textbook(client, admin_headers)
    assert client.get(f"/api/learn/textbook/{textbook_id}/bundle").status_code == 401


def test_bundle_contains_published_questions_with_answers(
    client: TestClient,
    db: Session,
    admin_headers: dict[str, str],
    student_headers: dict[str, str],
) -> None:
    textbook_id = _create_textbook(client, admin_headers)
    chapter_id = _create_chapter(client, admin_headers, textbook_id, "10以内加减法")
    kp = KnowledgePoint(subject="math", name="10以内加法", grade=1, node_type="point")
    db.add(kp)
    db.commit()
    db.refresh(kp)

    published_id = _create_question(
        client, admin_headers, chapter_id, kp.id, "3 + 4 = ?"
    )
    draft_id = _create_question(
        client, admin_headers, chapter_id, kp.id, "5 + 5 = ?"
    )
    draft = db.get(Question, draft_id)
    draft.status = "draft"
    db.commit()

    response = client.get(
        f"/api/learn/textbook/{textbook_id}/bundle", headers=student_headers
    )
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["textbook"]["id"] == textbook_id
    assert body["counts"] == {
        "units": 1,
        "knowledge_points": 1,
        "questions": 1,
    }
    assert str(chapter_id) in body["unit_details"]
    assert str(kp.id) in body["kp_details"]
    assert body["unit_details"][str(chapter_id)]["unit"]["question_count"] == 1

    question_ids = [item["id"] for item in body["questions"]]
    assert question_ids == [published_id]
    item = body["questions"][0]
    assert item["answer"] == {"value": "A"}
    assert item["analysis"] == "3 + 4 = ? 的解析"

    # 同一内容重复下载 pack_version 稳定。
    again = client.get(
        f"/api/learn/textbook/{textbook_id}/bundle", headers=student_headers
    )
    assert again.json()["pack_version"] == body["pack_version"]


def test_bundle_too_large_returns_409(
    client: TestClient,
    db: Session,
    admin_headers: dict[str, str],
    student_headers: dict[str, str],
    monkeypatch,
) -> None:
    textbook_id = _create_textbook(client, admin_headers)
    chapter_id = _create_chapter(client, admin_headers, textbook_id, "第一章")
    kp = KnowledgePoint(subject="math", name="加法", grade=1, node_type="point")
    db.add(kp)
    db.commit()
    db.refresh(kp)
    _create_question(client, admin_headers, chapter_id, kp.id, "1 + 1 = ?")

    monkeypatch.setattr(settings, "bundle_max_questions", 0)
    response = client.get(
        f"/api/learn/textbook/{textbook_id}/bundle", headers=student_headers
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "BUNDLE_TOO_LARGE"


def test_bundle_missing_textbook_returns_404(
    client: TestClient, student_headers: dict[str, str]
) -> None:
    response = client.get("/api/learn/textbook/9999/bundle", headers=student_headers)
    assert response.status_code == 404
