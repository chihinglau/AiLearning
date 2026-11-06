"""P0-20 知识点学习状态机测试。"""

from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.content import Chapter, KnowledgePoint, Question, Textbook
from app.models.practice import KpStudyState, WrongQuestion
from app.models.user import User


def _setup(client: TestClient, db: Session) -> dict[str, int | str]:
    registered = client.post(
        "/api/auth/register",
        json={"phone": "13600000001", "password": "pass1234", "grade": 3},
    )
    assert registered.status_code == 201, registered.text
    user = db.scalar(select(User).where(User.phone == "13600000001"))
    assert user is not None
    login = client.post(
        "/api/auth/login", data={"username": "13600000001", "password": "pass1234"}
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    book = Textbook(subject="math", grade=3, version="北师大版", semester="first")
    db.add(book)
    db.flush()
    chapter = Chapter(textbook_id=book.id, grade=3, name="第一单元", order_index=1)
    db.add(chapter)
    db.flush()
    section = KnowledgePoint(
        subject="math", name="第1节", grade=3, node_type="section", order_index=1
    )
    db.add(section)
    db.flush()
    kp = KnowledgePoint(
        subject="math",
        name="两位数进位加法",
        grade=3,
        node_type="point",
        parent_id=section.id,
        order_index=1,
    )
    db.add(kp)
    db.flush()
    question = Question(
        chapter_id=chapter.id,
        knowledge_point_id=kp.id,
        subject="math",
        q_type="choice",
        content={"stem": "12 + 9 = ?"},
        options=[{"key": "A", "text": "20"}, {"key": "B", "text": "21"}],
        answer={"value": "B"},
    )
    db.add(question)
    db.commit()
    return {"headers": headers, "user_id": user.id, "kp_id": kp.id, "q_id": question.id}


def _state(client: TestClient, ids: dict, path: str) -> str:
    response = client.get(
        f"/api/learn/kp/{ids['kp_id']}", headers=ids["headers"]
    )
    assert response.status_code == 200, response.text
    return response.json()[path]


def test_learning_pipeline(client: TestClient, db: Session) -> None:
    ids = _setup(client, db)
    assert _state(client, ids, "state") == "未学习"
    assert _state(client, ids, "state_evidence") == 0

    read = client.post(f"/api/learn/kp/{ids['kp_id']}/read", headers=ids["headers"])
    assert read.status_code == 200, read.text
    assert read.json()["state"] == "学习中"
    assert read.json()["read_at"] is not None
    assert _state(client, ids, "state") == "学习中"

    submit = client.post(
        "/api/learn/submit",
        headers=ids["headers"],
        json={"question_id": ids["q_id"], "user_answer": {"value": "A"}, "duration_ms": 5000},
    )
    assert submit.status_code == 200, submit.text
    assert _state(client, ids, "state") == "待巩固"

    selftest = client.post(
        f"/api/learn/kp/{ids['kp_id']}/selftest",
        headers=ids["headers"],
        json={"score": 90},
    )
    assert selftest.status_code == 200, selftest.text
    assert selftest.json()["state"] == "已掌握"
    assert selftest.json()["mastered_at"] is not None
    assert _state(client, ids, "state") == "已掌握"

    again = client.post(
        f"/api/learn/kp/{ids['kp_id']}/selftest",
        headers=ids["headers"],
        json={"score": 40},
    )
    assert again.status_code == 200
    assert again.json()["state"] == "已掌握"

    rows = db.scalar(
        select(func.count(KpStudyState.id)).where(
            KpStudyState.user_id == ids["user_id"],
            KpStudyState.knowledge_point_id == ids["kp_id"],
        )
    )
    assert rows == 1
    evidence = db.scalar(
        select(KpStudyState.evidence_count).where(
            KpStudyState.user_id == ids["user_id"],
            KpStudyState.knowledge_point_id == ids["kp_id"],
        )
    )
    assert evidence == 4


def test_due_review_overrides_state(client: TestClient, db: Session) -> None:
    ids = _setup(client, db)
    client.post(f"/api/learn/kp/{ids['kp_id']}/selftest", headers=ids["headers"], json={"score": 95})
    assert _state(client, ids, "state") == "已掌握"

    db.add(
        WrongQuestion(
            user_id=ids["user_id"],
            question_id=ids["q_id"],
            status="active",
            next_review_at=datetime.utcnow() - timedelta(hours=1),
        )
    )
    db.commit()

    assert _state(client, ids, "state") == "复习中"


def test_unknown_kp_returns_404(client: TestClient, db: Session) -> None:
    ids = _setup(client, db)
    response = client.post("/api/learn/kp/999999/read", headers=ids["headers"])
    assert response.status_code == 404
