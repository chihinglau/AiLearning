"""P0-27 exams 扩展与 exam_attempts/exam_answers 表。"""

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.content import Chapter, KnowledgePoint, Question, Textbook
from app.models.exam import Exam, ExamAnswer, ExamAttempt
from app.models.user import User


def _fixtures(db: Session) -> dict:
    user = User(phone="13800000002", password_hash="x", grade=3, role="student")
    db.add(user)
    book = Textbook(subject="math", grade=3, version="北师大版", semester="first")
    db.add(book)
    db.flush()
    chapter = Chapter(textbook_id=book.id, grade=3, name="第一单元", order_index=1)
    db.add(chapter)
    db.flush()
    kp = KnowledgePoint(
        subject="math", name="分数的认识", grade=3, node_type="point", order_index=1
    )
    db.add(kp)
    db.flush()
    question = Question(
        chapter_id=chapter.id, knowledge_point_id=kp.id, subject="math",
        q_type="choice", difficulty=1, content={"stem": "1/2"}, answer={"value": "A"},
    )
    db.add(question)
    exam = Exam(
        title="三年级数学第一单元测", subject="math", grade=3, exam_type="unit",
        chapter_ids=[chapter.id], questions=[{"question_id": 0}],
    )
    db.add(exam)
    db.commit()
    return {"user": user, "exam": exam, "question": question}


def test_exam_extension_defaults(db: Session) -> None:
    data = _fixtures(db)
    exam = data["exam"]
    assert exam.exam_type == "unit"
    assert exam.status == "published"
    assert exam.blueprint_id is None
    assert exam.chapter_ids


def test_attempt_and_answer_roundtrip(db: Session) -> None:
    data = _fixtures(db)
    attempt = ExamAttempt(user_id=data["user"].id, exam_id=data["exam"].id, seed=7)
    db.add(attempt)
    db.flush()
    assert attempt.status == "in_progress"
    assert attempt.objective_score == 0.0
    assert attempt.total_score is None

    answer = ExamAnswer(
        attempt_id=attempt.id, question_id=data["question"].id,
        user_answer={"value": "A"}, is_correct=True, score=3,
    )
    db.add(answer)
    db.commit()

    stored = db.get(ExamAnswer, answer.id)
    assert stored is not None
    assert stored.user_answer == {"value": "A"}
    assert stored.is_correct is True
    assert stored.score == 3.0
    assert stored.self_score is None


def test_attempt_unique_per_user_exam_seed(db: Session) -> None:
    data = _fixtures(db)
    db.add(ExamAttempt(user_id=data["user"].id, exam_id=data["exam"].id, seed=7))
    db.commit()
    db.add(ExamAttempt(user_id=data["user"].id, exam_id=data["exam"].id, seed=7))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_answer_unique_per_attempt_question(db: Session) -> None:
    data = _fixtures(db)
    attempt = ExamAttempt(user_id=data["user"].id, exam_id=data["exam"].id, seed=8)
    db.add(attempt)
    db.flush()
    db.add(ExamAnswer(attempt_id=attempt.id, question_id=data["question"].id))
    db.commit()
    db.add(ExamAnswer(attempt_id=attempt.id, question_id=data["question"].id))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
