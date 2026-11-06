"""P2-05 图片作答：仅主观题、格式/大小/数量校验。"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.content import Question
from app.models.exam import Exam
from app.models.user import User

PASSWORD = "pass1234"
VALID_PNG = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="


def _student(client: TestClient, db: Session) -> dict[str, str]:
    user = User(
        phone="13900000001",
        password_hash=hash_password(PASSWORD),
        nickname="图片作答学生",
        role="student",
        grade=1,
    )
    db.add(user)
    db.commit()
    response = client.post(
        "/api/auth/login", data={"username": "13900000001", "password": PASSWORD}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _exam_with_questions(db: Session, sample_chapter: int, sample_question: int) -> int:
    subjective = Question(
        chapter_id=sample_chapter,
        subject="math",
        q_type="answer",
        content={"stem": "请用图片提交解题过程"},
        answer={"value": "参考步骤"},
        difficulty=2,
    )
    db.add(subjective)
    db.flush()
    exam = Exam(
        title="图片作答测试卷",
        subject="math",
        grade=1,
        total_score=10,
        time_limit_min=30,
        status="published",
        source="unit",
        exam_type="unit",
        questions=[
            {"question_id": subjective.id, "score": 5},
            {"question_id": sample_question, "score": 5},
        ],
    )
    db.add(exam)
    db.commit()
    db.refresh(exam)
    return exam.id


def test_image_answer_accepts_subjective_and_rejects_objective(
    client: TestClient, db: Session, sample_chapter: int, sample_question: int
) -> None:
    exam_id = _exam_with_questions(db, sample_chapter, sample_question)
    headers = _student(client, db)
    started = client.post(f"/api/exams/{exam_id}/attempts", headers=headers, json={})
    assert started.status_code == 200, started.text
    attempt_id = int(started.json()["id"])
    subjective = next(
        item["id"] for item in started.json()["exam"]["questions"] if item["q_type"] == "answer"
    )

    ok = client.patch(
        f"/api/exams/attempts/{attempt_id}",
        headers=headers,
        json={
            "answers": [
                {
                    "question_id": subjective,
                    "user_answer": {"value": "见图片", "images": [VALID_PNG]},
                }
            ]
        },
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["saved"] == 1

    # 客观题不接受图片
    rejected = client.patch(
        f"/api/exams/attempts/{attempt_id}",
        headers=headers,
        json={
            "answers": [
                {
                    "question_id": sample_question,
                    "user_answer": {"images": [VALID_PNG]},
                }
            ]
        },
    )
    assert rejected.status_code == 422
    assert rejected.json()["detail"]["code"] == "IMAGE_NOT_ALLOWED"

    # 非白名单格式
    bad_format = client.patch(
        f"/api/exams/attempts/{attempt_id}",
        headers=headers,
        json={
            "answers": [
                {
                    "question_id": subjective,
                    "user_answer": {"images": ["data:image/gif;base64,R0lGOD"]},
                }
            ]
        },
    )
    assert bad_format.status_code == 422
    assert bad_format.json()["detail"]["code"] == "IMAGE_INVALID"

    # 单张超限
    too_large = client.patch(
        f"/api/exams/attempts/{attempt_id}",
        headers=headers,
        json={
            "answers": [
                {
                    "question_id": subjective,
                    "user_answer": {
                        "images": ["data:image/png;base64," + "A" * 3_000_000]
                    },
                }
            ]
        },
    )
    assert too_large.status_code == 422
    assert too_large.json()["detail"]["code"] == "IMAGE_TOO_LARGE"

    # 数量超限
    too_many = client.patch(
        f"/api/exams/attempts/{attempt_id}",
        headers=headers,
        json={
            "answers": [
                {
                    "question_id": subjective,
                    "user_answer": {"images": [VALID_PNG, VALID_PNG, VALID_PNG]},
                }
            ]
        },
    )
    assert too_many.status_code == 422
    assert too_many.json()["detail"]["code"] == "IMAGE_TOO_MANY"
