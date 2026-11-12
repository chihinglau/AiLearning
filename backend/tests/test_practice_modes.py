"""三种练习模式的组卷差异（专项突破 / 同步巩固 / 考前速练）。

回归目标：以前三个分段只改一个 mode 字符串，后端 build_plan 不消费它，
导致同一 seed 下三种模式出同一套题。
"""

from datetime import datetime, timedelta
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.content import Chapter, KnowledgePoint, Question, Textbook
from app.models.practice import MasteryScore, StudentQuestionRecord
from app.models.user import User


def _setup(client: TestClient, db: Session) -> dict[str, Any]:
    registered = client.post(
        "/api/auth/register",
        json={"phone": "13900000011", "password": "pass1234", "grade": 3},
    )
    assert registered.status_code == 201, registered.text
    user = db.scalar(select(User).where(User.phone == "13900000011"))
    assert user is not None
    login = client.post(
        "/api/auth/login",
        data={"username": "13900000011", "password": "pass1234"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    book = Textbook(subject="math", grade=3, version="北师大版", semester="first")
    db.add(book)
    db.flush()
    chapters: list[Chapter] = []
    sections: list[KnowledgePoint] = []
    for index in range(2):
        chapter = Chapter(
            textbook_id=book.id,
            grade=3,
            name=f"第{index + 1}单元",
            order_index=index + 1,
        )
        db.add(chapter)
        db.flush()
        chapters.append(chapter)
        section = KnowledgePoint(
            subject="math",
            name=f"第{index + 1}节",
            grade=3,
            node_type="section",
            order_index=index + 1,
        )
        db.add(section)
        db.flush()
        sections.append(section)

    kps: list[KnowledgePoint] = []
    questions: list[Question] = []
    q_types = ("choice", "fill", "judge", "answer")
    for chapter_index, chapter in enumerate(chapters):
        for point_index in range(2):
            kp = KnowledgePoint(
                subject="math",
                name=f"知识点{chapter_index + 1}-{point_index + 1}",
                grade=3,
                node_type="point",
                parent_id=sections[chapter_index].id,
                order_index=point_index + 1,
            )
            db.add(kp)
            db.flush()
            kps.append(kp)
            for difficulty, q_type in enumerate(q_types, start=1):
                question = Question(
                    chapter_id=chapter.id,
                    knowledge_point_id=kp.id,
                    subject="math",
                    q_type=q_type,
                    difficulty=difficulty,
                    content={"stem": f"{kp.name}-{q_type}"},
                    answer={"value": "A"},
                )
                db.add(question)
                questions.append(question)

    # 前两个知识点薄弱、后两个已掌握；另有一题昨天刚做过。
    for index, kp in enumerate(kps):
        db.add(
            MasteryScore(
                user_id=user.id,
                knowledge_point_id=kp.id,
                score=30.0 if index < 2 else 90.0,
                confidence=5,
            )
        )
    db.add(
        StudentQuestionRecord(
            user_id=user.id,
            question_id=questions[0].id,
            is_correct=True,
            attempted_at=datetime.utcnow() - timedelta(days=1),
        )
    )
    db.commit()
    return {
        "headers": headers,
        "book_id": book.id,
        "kp_ids": [kp.id for kp in kps],
        "weak_kp_ids": [kp.id for kp in kps[:2]],
        "kp_order": {kp.id: kp.order_index for kp in kps},
        "chapter_order": {chapter.id: chapter.order_index for chapter in chapters},
        "question_count": len(questions),
    }


def _payload(ids: dict[str, Any], mode: str, **extra: Any) -> dict[str, Any]:
    return {
        "scope_type": "textbook",
        "scope_ids": [ids["book_id"]],
        "count": 12,
        "seed": 42,
        "mode": mode,
        **extra,
    }


def _preview(client: TestClient, ids: dict[str, Any], mode: str) -> dict[str, Any]:
    response = client.post(
        "/api/learn/practice/preview",
        headers=ids["headers"],
        json=_payload(ids, mode),
    )
    assert response.status_code == 200, response.text
    return response.json()


def _start(client: TestClient, ids: dict[str, Any], mode: str) -> list[dict[str, Any]]:
    response = client.post(
        "/api/learn/start", headers=ids["headers"], json=_payload(ids, mode)
    )
    assert response.status_code == 200, response.text
    return response.json()["questions"]


def test_modes_expose_distinct_policies_and_scopes(client: TestClient, db: Session) -> None:
    ids = _setup(client, db)
    special = _preview(client, ids, "special")
    sync = _preview(client, ids, "sync")
    pre_exam = _preview(client, ids, "pre_exam")

    assert {special["mode"], sync["mode"], pre_exam["mode"]} == {
        "special",
        "sync",
        "pre_exam",
    }
    assert len({special["strategy"], sync["strategy"], pre_exam["strategy"]}) == 3
    assert special["mode_label"] == "专项突破"
    assert sync["mode_label"] == "同步巩固"
    assert pre_exam["mode_label"] == "考前速练"

    # 专项/同步排除近 7 天做过的题；考前速练按模拟卷不排重。
    assert special["available"] == sync["available"] == ids["question_count"] - 1
    assert pre_exam["available"] == ids["question_count"]
    # 考前速练要求知识点全覆盖。
    assert pre_exam["covered_kp_count"] == pre_exam["range_kp_count"] == 4


def test_sync_orders_questions_by_textbook(client: TestClient, db: Session) -> None:
    ids = _setup(client, db)
    questions = _start(client, ids, "sync")
    keys = [
        (
            ids["chapter_order"][q["chapter_id"]],
            ids["kp_order"][q["knowledge_point_id"]],
            q["difficulty"],
            q["id"],
        )
        for q in questions
    ]
    assert keys == sorted(keys), "同步巩固应按章 → 知识点 → 难度顺序出题"


def test_special_prioritizes_weak_knowledge_points(client: TestClient, db: Session) -> None:
    ids = _setup(client, db)
    special = _start(client, ids, "special")
    other = _start(client, ids, "pre_exam")
    weak = set(ids["weak_kp_ids"])

    # 有掌握度数据时，覆盖阶段的前几题应来自薄弱知识点。
    assert all(
        q["knowledge_point_id"] in weak for q in special[:2]
    ), "专项突破应优先取薄弱知识点"
    assert [q["id"] for q in special] != [q["id"] for q in other]


def test_preview_matches_start_for_each_mode(client: TestClient, db: Session) -> None:
    ids = _setup(client, db)
    for mode in ("special", "sync", "pre_exam"):
        preview = _preview(client, ids, mode)
        questions = _start(client, ids, mode)
        assert len(questions) == preview["count"]
        mix: dict[str, int] = {}
        for question in questions:
            mix[question["q_type"]] = mix.get(question["q_type"], 0) + 1
        assert mix == preview["q_type_mix"], f"{mode} 预览与实际题型不一致"


def test_unknown_mode_rejected(client: TestClient, db: Session) -> None:
    ids = _setup(client, db)
    response = client.post(
        "/api/learn/practice/preview",
        headers=ids["headers"],
        json=_payload(ids, "not_a_mode"),
    )
    assert response.status_code == 422
