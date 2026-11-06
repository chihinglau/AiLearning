"""P0-26 试卷生成：题型/难度/覆盖约束、seed 稳定与题量兜底。"""

from collections import Counter

from sqlalchemy.orm import Session

from app.models.content import Chapter, KnowledgePoint, Question, Textbook
from app.models.user import User
from app.services.exam_paper import generate_paper
from scripts.seed import EXAM_BLUEPRINT_SEEDS, _put_blueprint

MATH = EXAM_BLUEPRINT_SEEDS[0]


def _user(db: Session) -> User:
    user = User(phone="13800000001", password_hash="x", grade=3, role="student")
    db.add(user)
    db.commit()
    return user


def _blueprint(db: Session):
    fields = {k: v for k, v in MATH.items() if k != "code"}
    blueprint = _put_blueprint(db, code=MATH["code"], **fields)
    db.commit()
    return blueprint


def _chapter(db: Session, kp_count: int = 4) -> tuple[int, list[int]]:
    book = Textbook(subject="math", grade=3, version="北师大版", semester="first")
    db.add(book)
    db.flush()
    chapter = Chapter(textbook_id=book.id, grade=3, name="第一单元", order_index=1)
    db.add(chapter)
    db.flush()
    kp_ids = []
    for index in range(kp_count):
        kp = KnowledgePoint(
            subject="math", name=f"知识点{index + 1}", grade=3,
            node_type="point", order_index=index + 1,
        )
        db.add(kp)
        db.flush()
        kp_ids.append(kp.id)
    db.commit()
    return chapter.id, kp_ids


def _add_questions(
    db: Session,
    *,
    chapter_id: int,
    kp_ids: list[int],
    q_type: str,
    count: int,
    difficulty: int,
) -> None:
    for index in range(count):
        db.add(
            Question(
                chapter_id=chapter_id, knowledge_point_id=kp_ids[index % len(kp_ids)],
                subject="math", q_type=q_type, difficulty=difficulty,
                content={"stem": f"{q_type}-{difficulty}-{index}"},
                answer={"value": "A"},
            )
        )
    db.commit()


def _build_full_pool(db: Session, chapter_id: int, kp_ids: list[int]) -> None:
    _add_questions(db, chapter_id=chapter_id, kp_ids=kp_ids, q_type="fill", count=24, difficulty=1)
    _add_questions(db, chapter_id=chapter_id, kp_ids=kp_ids, q_type="choice", count=12, difficulty=2)
    _add_questions(db, chapter_id=chapter_id, kp_ids=kp_ids, q_type="answer", count=8, difficulty=2)


def test_generate_paper_matches_blueprint(db: Session) -> None:
    user = _user(db)
    blueprint = _blueprint(db)
    chapter_id, kp_ids = _chapter(db)
    _build_full_pool(db, chapter_id, kp_ids)

    paper = generate_paper(db, user=user, blueprint=blueprint, chapter_ids=[chapter_id], seed=5)

    assert paper.requested == 36
    assert len(paper.items) == 36
    assert paper.insufficient is False
    assert paper.total_score == 100
    assert paper.kp_coverage == 1.0
    assert paper.fallback_count == 0

    section_counts = Counter((item.section_index, item.question.q_type) for item in paper.items)
    assert section_counts[(0, "fill")] == 10
    assert section_counts[(1, "fill")] == 10
    assert section_counts[(2, "choice")] == 10
    assert section_counts[(3, "answer")] == 6


def test_generate_paper_is_deterministic_per_seed(db: Session) -> None:
    user = _user(db)
    blueprint = _blueprint(db)
    chapter_id, kp_ids = _chapter(db)
    _build_full_pool(db, chapter_id, kp_ids)

    first = generate_paper(db, user=user, blueprint=blueprint, chapter_ids=[chapter_id], seed=42)
    second = generate_paper(db, user=user, blueprint=blueprint, chapter_ids=[chapter_id], seed=42)
    assert first.seed == second.seed == 42
    assert [q.id for q in first.questions] == [q.id for q in second.questions]

    other = generate_paper(db, user=user, blueprint=blueprint, chapter_ids=[chapter_id], seed=43)
    assert other.seed == 43


def test_section_prefers_configured_difficulty(db: Session) -> None:
    user = _user(db)
    blueprint = _blueprint(db)
    chapter_id, kp_ids = _chapter(db)
    _add_questions(db, chapter_id=chapter_id, kp_ids=kp_ids, q_type="fill", count=24, difficulty=1)
    _add_questions(db, chapter_id=chapter_id, kp_ids=kp_ids, q_type="fill", count=24, difficulty=5)
    _add_questions(db, chapter_id=chapter_id, kp_ids=kp_ids, q_type="choice", count=12, difficulty=2)
    _add_questions(db, chapter_id=chapter_id, kp_ids=kp_ids, q_type="answer", count=8, difficulty=2)

    paper = generate_paper(db, user=user, blueprint=blueprint, chapter_ids=[chapter_id], seed=6)
    section0 = [item for item in paper.items if item.section_index == 0]
    assert len(section0) == 10
    assert all(item.question.difficulty <= 2 for item in section0)


def test_fallback_fills_sections_when_type_lacking(db: Session) -> None:
    user = _user(db)
    blueprint = _blueprint(db)
    chapter_id, kp_ids = _chapter(db)
    _add_questions(db, chapter_id=chapter_id, kp_ids=kp_ids, q_type="choice", count=40, difficulty=2)

    paper = generate_paper(db, user=user, blueprint=blueprint, chapter_ids=[chapter_id], seed=7)
    assert len(paper.items) == 36
    assert paper.insufficient is False
    assert paper.fallback_count == 26
    assert all(item.question.q_type == "choice" for item in paper.items)
    assert paper.total_score == 100


def test_insufficient_pool_reports_shortage(db: Session) -> None:
    user = _user(db)
    blueprint = _blueprint(db)
    chapter_id, kp_ids = _chapter(db)
    _add_questions(db, chapter_id=chapter_id, kp_ids=kp_ids, q_type="fill", count=5, difficulty=1)

    paper = generate_paper(db, user=user, blueprint=blueprint, chapter_ids=[chapter_id], seed=8)
    assert len(paper.items) == 5
    assert paper.insufficient is True
    assert paper.total_score == 15  # 5 题 × 3 分（第一节）
