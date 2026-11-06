"""P1-11 首页推荐规则：复习→薄弱→单元测→进度→每日一练。"""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.content import Chapter, KnowledgePoint, Question, Textbook
from app.models.exam import Exam
from app.models.practice import MasteryScore
from app.models.textbook import TextbookBinding
from app.models.user import User


def _student(
    client: TestClient, db: Session, phone: str, grade: int = 3
) -> tuple[dict[str, str], int]:
    registered = client.post(
        "/api/auth/register",
        json={"phone": phone, "password": "pass1234", "grade": grade},
    )
    assert registered.status_code == 201, registered.text
    login = client.post(
        "/api/auth/login", data={"username": phone, "password": "pass1234"}
    )
    assert login.status_code == 200, login.text
    user = db.scalar(select(User).where(User.phone == phone))
    assert user is not None
    return {"Authorization": f"Bearer {login.json()['access_token']}"}, user.id


def _bound_book(db: Session, user_id: int, name: str = "推荐测试教材") -> Textbook:
    book = Textbook(subject="math", grade=3, version=name, semester="first")
    db.add(book)
    db.flush()
    db.add(
        TextbookBinding(
            user_id=user_id, subject="math", textbook_id=book.id, semester="first"
        )
    )
    db.commit()
    return book


def _chapter(
    db: Session, book: Textbook, name: str, order_index: int, kp_name: str | None = None
) -> tuple[int, int | None]:
    chapter = Chapter(
        textbook_id=book.id, grade=3, name=name, order_index=order_index
    )
    db.add(chapter)
    db.flush()
    kp_id = None
    if kp_name is not None:
        kp = KnowledgePoint(subject="math", name=kp_name, grade=3)
        db.add(kp)
        db.flush()
        db.add(
            Question(
                chapter_id=chapter.id,
                knowledge_point_id=kp.id,
                subject="math",
                q_type="choice",
                content={"stem": f"{kp_name} 练习"},
                answer={"value": "A"},
            )
        )
        kp_id = kp.id
    db.commit()
    return chapter.id, kp_id


def _unit_exam(db: Session, chapter_id: int, title: str = "单元测") -> int:
    exam = Exam(
        title=title,
        subject="math",
        grade=3,
        exam_type="unit",
        total_score=100,
        time_limit_min=45,
        questions=[],
        chapter_ids=[chapter_id],
        status="published",
    )
    db.add(exam)
    db.commit()
    return exam.id


def test_recommends_unit_test_when_unit_mastered(
    client: TestClient, db: Session
) -> None:
    headers, user_id = _student(client, db, "13621000011")
    book = _bound_book(db, user_id)
    chapter_id, kp_id = _chapter(db, book, "第一单元", 1, "分数应用")
    assert kp_id is not None
    db.add(MasteryScore(user_id=user_id, knowledge_point_id=kp_id, score=85))
    exam_id = _unit_exam(db, chapter_id)
    db.commit()

    body = client.get("/api/learn/home", headers=headers).json()
    rec = body["recommendation"]
    assert rec["action"] == "unit_test"
    assert rec["label"] == "单元测试"
    assert rec["chapter_id"] == chapter_id
    assert rec["exam_id"] == exam_id
    assert [item["exam_id"] for item in body["pending_exams"]] == [exam_id]


def test_recommends_learn_for_weak_kp_in_current_unit(
    client: TestClient, db: Session
) -> None:
    headers, user_id = _student(client, db, "13621000012")
    # 当前单元外的高分知识点不影响当前单元判断
    other_kp = KnowledgePoint(subject="math", name="单元外知识点", grade=3)
    db.add(other_kp)
    db.flush()
    db.add(MasteryScore(user_id=user_id, knowledge_point_id=other_kp.id, score=60))
    book = _bound_book(db, user_id)
    _, kp_id = _chapter(db, book, "第二单元", 1, "乘法口诀")
    assert kp_id is not None
    db.add(MasteryScore(user_id=user_id, knowledge_point_id=kp_id, score=25))
    db.commit()

    body = client.get("/api/learn/home", headers=headers).json()
    rec = body["recommendation"]
    assert rec["action"] == "learn_kp"
    assert rec["knowledge_point_id"] == kp_id


def test_recommends_continue_when_progress_behind(
    client: TestClient, db: Session
) -> None:
    headers, user_id = _student(client, db, "13621000013")
    book = _bound_book(db, user_id)
    first_id, _ = _chapter(db, book, "第一单元", 1)
    _chapter(db, book, "第二单元", 2)

    body = client.get("/api/learn/home", headers=headers).json()
    rec = body["recommendation"]
    assert rec["action"] == "continue"
    assert rec["chapter_id"] == first_id
    assert "学期进度落后" in rec["reason"]
    assert body["pending_exams"] == []


def test_falls_back_to_daily_when_no_data(client: TestClient, db: Session) -> None:
    headers, _ = _student(client, db, "13621000014")

    body = client.get("/api/learn/home", headers=headers).json()
    assert body["recommendation"]["action"] == "daily"
    assert body["pending_exams"] == []
