"""CR-008 听力材料播放次数限制：试卷作答内每题上限 2 次。

两处记账入口：
1. `POST /api/exams/attempts/{attempt_id}/listening-plays`（客户端每次点播放前占用额度，
   即使音频命中本地缓存也会记账）；
2. `GET /api/learn/questions/{id}/audio?kind=listening&attempt_id=...`（服务端兜底，
   直接命中音频接口也扣额度）。
"""

from fastapi.testclient import TestClient

from app.core.config import settings
from tests.conftest import TestingSessionLocal

PLAY_PATH = "/api/exams/attempts/{attempt_id}/listening-plays"


def _make_exam(question_id: int, *, grade: int = 1) -> int:
    from app.models.exam import Exam

    session = TestingSessionLocal()
    try:
        exam = Exam(
            title="听力额度测试卷",
            subject="english",
            grade=grade,
            exam_type="unit",
            status="published",
            questions=[
                {
                    "question_id": question_id,
                    "score": 5,
                    "section_index": 1,
                    "section_name": "一、听力",
                }
            ],
            total_score=100,
            time_limit_min=40,
        )
        session.add(exam)
        session.commit()
        return exam.id
    finally:
        session.close()


def _make_attempt(client: TestClient, headers: dict[str, str], exam_id: int) -> int:
    response = client.post(f"/api/exams/{exam_id}/attempts", headers=headers, json={})
    assert response.status_code in (200, 201), response.text
    return int(response.json()["id"])


def test_listening_play_limit_reached(
    client: TestClient, db, student_headers
) -> None:
    question_id = 990001
    exam_id = _make_exam(question_id)
    attempt_id = _make_attempt(client, student_headers, exam_id)

    first = client.post(
        PLAY_PATH.format(attempt_id=attempt_id),
        headers=student_headers,
        params={"question_id": question_id},
    )
    assert first.status_code == 200, first.text
    assert first.json()["remaining"] == 1
    assert first.json()["limit"] == settings.listening_play_limit_per_attempt

    second = client.post(
        PLAY_PATH.format(attempt_id=attempt_id),
        headers=student_headers,
        params={"question_id": question_id},
    )
    assert second.status_code == 200, second.text
    assert second.json()["remaining"] == 0

    third = client.post(
        PLAY_PATH.format(attempt_id=attempt_id),
        headers=student_headers,
        params={"question_id": question_id},
    )
    assert third.status_code == 429
    detail = third.json()["detail"]
    assert detail["code"] == "LISTENING_PLAY_LIMIT"
    assert detail["remaining"] == 0
    assert detail["played"] == 2


def test_listening_play_quota_is_per_question(
    client: TestClient, db, student_headers
) -> None:
    first_qid, second_qid = 990002, 990003
    exam_id = _make_exam(first_qid)
    session = TestingSessionLocal()
    try:
        from app.models.exam import Exam

        exam = session.get(Exam, exam_id)
        exam.questions = [
            {"question_id": first_qid, "score": 5, "section_index": 1},
            {"question_id": second_qid, "score": 5, "section_index": 1},
        ]
        session.commit()
    finally:
        session.close()
    attempt_id = _make_attempt(client, student_headers, exam_id)

    for _ in range(2):
        client.post(
            PLAY_PATH.format(attempt_id=attempt_id),
            headers=student_headers,
            params={"question_id": first_qid},
        )
    # 另一道题仍有自己的 2 次额度
    other = client.post(
        PLAY_PATH.format(attempt_id=attempt_id),
        headers=student_headers,
        params={"question_id": second_qid},
    )
    assert other.status_code == 200
    assert other.json()["remaining"] == 1


def test_listening_play_question_not_in_paper(
    client: TestClient, db, student_headers
) -> None:
    exam_id = _make_exam(990004)
    attempt_id = _make_attempt(client, student_headers, exam_id)

    response = client.post(
        PLAY_PATH.format(attempt_id=attempt_id),
        headers=student_headers,
        params={"question_id": 123456},
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "QUESTION_NOT_IN_PAPER"
