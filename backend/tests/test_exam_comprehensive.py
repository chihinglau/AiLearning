"""P1-07 期中/期末蓝图：章节集合组卷、6:3:1 分数配比与知识点覆盖。"""

from collections import Counter

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.content import Chapter, KnowledgePoint, Question, Textbook
from app.models.exam import Exam
from app.models.user import User
from app.services.exam_paper import generate_paper
from scripts.seed import EXAM_BLUEPRINT_SEEDS, _put_blueprint

COMPREHENSIVE_CODES = [
    f"{subject}_primary_{exam_type}"
    for subject in ("math", "chinese", "english")
    for exam_type in ("midterm", "final")
]


def _spec(code: str) -> dict:
    return next(spec for spec in EXAM_BLUEPRINT_SEEDS if spec["code"] == code)


def _blueprint(db: Session, code: str):
    fields = {k: v for k, v in _spec(code).items() if k != "code"}
    blueprint = _put_blueprint(db, code=code, **fields)
    db.commit()
    return blueprint


def _chapters(db: Session, kp_count: int = 3) -> tuple[list[int], list[int]]:
    book = Textbook(subject="math", grade=3, version="北师大版", semester="first")
    db.add(book)
    db.flush()
    chapter_ids: list[int] = []
    kp_ids: list[int] = []
    for order in (1, 2):
        chapter = Chapter(
            textbook_id=book.id, grade=3, name=f"第{order}单元", order_index=order
        )
        db.add(chapter)
        db.flush()
        chapter_ids.append(chapter.id)
        for index in range(kp_count):
            kp = KnowledgePoint(
                subject="math",
                name=f"第{order}单元知识点{index + 1}",
                grade=3,
                node_type="point",
                order_index=index + 1,
            )
            db.add(kp)
            db.flush()
            kp_ids.append(kp.id)
    db.commit()
    return chapter_ids, kp_ids


def _add_questions(
    db: Session,
    *,
    chapter_id: int,
    chapter_kps: list[int],
    q_type: str,
    difficulty: int,
    count: int,
) -> None:
    for index in range(count):
        db.add(
            Question(
                chapter_id=chapter_id,
                knowledge_point_id=chapter_kps[index % len(chapter_kps)],
                subject="math",
                q_type=q_type,
                difficulty=difficulty,
                content={"stem": f"{q_type}-{difficulty}-{index}"},
                answer={"value": "A"},
            )
        )
    db.commit()


def _build_pool(db: Session, chapter_ids: list[int], kp_ids: list[int]) -> None:
    """按 6:3:1 分带题型准备两章题库，保证每节题量充足。"""
    per_chapter_kps = [
        kp_ids[index * 3 : index * 3 + 3] for index in range(len(chapter_ids))
    ]
    for chapter_id, chapter_kps in zip(chapter_ids, per_chapter_kps):
        _add_questions(
            db, chapter_id=chapter_id, chapter_kps=chapter_kps,
            q_type="fill", difficulty=1, count=10,
        )
        _add_questions(
            db, chapter_id=chapter_id, chapter_kps=chapter_kps,
            q_type="choice", difficulty=1, count=10,
        )
        _add_questions(
            db, chapter_id=chapter_id, chapter_kps=chapter_kps,
            q_type="fill", difficulty=2, count=10,
        )
        _add_questions(
            db, chapter_id=chapter_id, chapter_kps=chapter_kps,
            q_type="answer", difficulty=2, count=4,
        )
        _add_questions(
            db, chapter_id=chapter_id, chapter_kps=chapter_kps,
            q_type="answer", difficulty=4, count=2,
        )


def _user(db: Session) -> User:
    user = User(phone="13800000002", password_hash="x", grade=3, role="student")
    db.add(user)
    db.commit()
    return user


def test_comprehensive_blueprints_cover_midterm_and_final() -> None:
    specs = {spec["code"]: spec for spec in EXAM_BLUEPRINT_SEEDS}
    for code in COMPREHENSIVE_CODES:
        spec = specs[code]
        assert spec["exam_type"] in {"midterm", "final"}
        assert spec["total_score"] == 100

        bands = Counter(section["band"] for section in spec["sections"])
        assert set(bands) == {"easy", "medium", "hard"}
        assert bands["easy"] >= bands["medium"] >= bands["hard"]

        score_by_band: dict[str, float] = {"easy": 0, "medium": 0, "hard": 0}
        for section in spec["sections"]:
            score_by_band[section["band"]] += section["count"] * section["score_each"]
        assert score_by_band == {"easy": 60, "medium": 30, "hard": 10}
        assert spec["kp_coverage_min"] == 0.8


def test_generate_midterm_paper_from_chapter_set(db: Session) -> None:
    user = _user(db)
    blueprint = _blueprint(db, "math_primary_midterm")
    chapter_ids, kp_ids = _chapters(db)
    _build_pool(db, chapter_ids, kp_ids)

    paper = generate_paper(
        db, user=user, blueprint=blueprint, chapter_ids=chapter_ids, seed=11
    )

    assert paper.requested == 28
    assert len(paper.items) == 28
    assert paper.insufficient is False
    assert paper.fallback_count == 0
    assert paper.total_score == 100
    assert paper.kp_coverage == 1.0
    assert {item.question.chapter_id for item in paper.items} == set(chapter_ids)

    score_by_band: dict[str, float] = {"easy": 0, "medium": 0, "hard": 0}
    for item in paper.items:
        band = "easy" if item.question.difficulty <= 1 else (
            "medium" if item.question.difficulty <= 3 else "hard"
        )
        score_by_band[band] += item.score
    assert score_by_band == {"easy": 60, "medium": 30, "hard": 10}

    section_counts = Counter(item.section_index for item in paper.items)
    assert section_counts == {0: 10, 1: 10, 2: 5, 3: 2, 4: 1}


def test_generate_final_paper_is_deterministic(db: Session) -> None:
    user = _user(db)
    blueprint = _blueprint(db, "math_primary_final")
    chapter_ids, kp_ids = _chapters(db)
    _build_pool(db, chapter_ids, kp_ids)

    first = generate_paper(
        db, user=user, blueprint=blueprint, chapter_ids=chapter_ids, seed=12
    )
    second = generate_paper(
        db, user=user, blueprint=blueprint, chapter_ids=chapter_ids, seed=12
    )

    assert [item.question.id for item in first.items] == [
        item.question.id for item in second.items
    ]
    assert first.difficulty_mix == {"easy": 20, "medium": 7, "hard": 1}


def test_generate_api_publishes_midterm_exam(
    client: TestClient, db: Session, admin_headers: dict[str, str]
) -> None:
    _blueprint(db, "math_primary_midterm")
    chapter_ids, kp_ids = _chapters(db)
    _build_pool(db, chapter_ids, kp_ids)

    response = client.post(
        "/api/exams/generate",
        headers=admin_headers,
        json={
            "blueprint_code": "math_primary_midterm",
            "chapter_ids": chapter_ids,
            "title": "三年级数学期中",
            "seed": 21,
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["question_count"] == 28
    assert body["total_score"] == 100
    assert body["kp_coverage"] >= 0.8
    assert body["difficulty_mix"] == {"easy": 20, "medium": 7, "hard": 1}
    assert body["fallback_count"] == 0

    exam = db.get(Exam, body["exam_id"])
    assert exam is not None
    assert exam.exam_type == "midterm"
    assert exam.status == "published"
    assert exam.grade == 3
