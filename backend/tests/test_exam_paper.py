"""PG-01 组卷契约：分位难度带、严格拒绝（不降级）、知识点上限、scope 解析、seed 稳定。"""

from collections import Counter

from sqlalchemy.orm import Session

from app.models.content import Chapter, KnowledgePoint, Question, Textbook
from app.models.exam import ExamBlueprint
from app.models.user import User
from app.services.exam_paper import (
    BAND_QUANTILES,
    KP_CAP_PER_PAPER,
    generate_paper,
    resolve_scope_chapters,
)
from scripts.seed import EXAM_BLUEPRINT_SEEDS

MATH = EXAM_BLUEPRINT_SEEDS[0]


def _user(db: Session) -> User:
    user = User(phone="13800000001", password_hash="x", grade=3, role="student")
    db.add(user)
    db.commit()
    return user


def _blueprint(db: Session, sections: list[dict] | None = None) -> ExamBlueprint:
    blueprint = ExamBlueprint(
        code=MATH["code"],
        name=MATH["name"],
        subject="math",
        grade=3,
        exam_type="unit",
        total_score=100,
        time_limit_min=60,
        sections=sections or MATH["sections"],
        kp_coverage_min=0.4,
    )
    db.add(blueprint)
    db.commit()
    return blueprint


def _chapter(db: Session, kp_count: int = 90) -> tuple[int, list[int]]:
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
    status: str = "published",
    kp_offset: int = 0,
) -> None:
    for index in range(count):
        db.add(
            Question(
                chapter_id=chapter_id,
                knowledge_point_id=kp_ids[(kp_offset + index) % len(kp_ids)],
                subject="math", q_type=q_type, difficulty=difficulty, status=status,
                content={"stem": f"{q_type}-{difficulty}-{index}"},
                answer={"value": "A"},
            )
        )
    db.commit()


def _build_full_pool(db: Session, chapter_id: int, kp_ids: list[int]) -> None:
    _add_questions(db, chapter_id=chapter_id, kp_ids=kp_ids, q_type="fill", count=24, difficulty=1, kp_offset=0)
    _add_questions(db, chapter_id=chapter_id, kp_ids=kp_ids, q_type="choice", count=12, difficulty=2, kp_offset=24)
    _add_questions(db, chapter_id=chapter_id, kp_ids=kp_ids, q_type="answer", count=8, difficulty=2, kp_offset=36)


def test_generate_paper_matches_blueprint(db: Session) -> None:
    user = _user(db)
    blueprint = _blueprint(db)
    chapter_id, kp_ids = _chapter(db)
    _build_full_pool(db, chapter_id, kp_ids)

    paper = generate_paper(db, user=user, blueprint=blueprint, chapter_ids=[chapter_id], seed=5)

    assert paper.requested == 36
    assert len(paper.items) == 36
    assert paper.refused is False
    assert paper.insufficient is False
    assert paper.total_score == 100

    section_counts = Counter((item.section_index, item.question.q_type) for item in paper.items)
    assert section_counts[(0, "fill")] == 10
    assert section_counts[(1, "fill")] == 10
    assert section_counts[(2, "choice")] == 10
    assert section_counts[(3, "answer")] == 6

    # 同卷同一知识点不超过 2 题
    per_kp = Counter(item.question.knowledge_point_id for item in paper.items)
    assert max(per_kp.values()) <= KP_CAP_PER_PAPER


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


def test_band_sections_use_quantiles_not_hardcoded_difficulty(db: Session) -> None:
    """band=easy 应取册内低分位，而不是写死的 difficulty==1（题库无 1 分题也能出卷）。"""
    user = _user(db)
    sections = [
        {"name": "一、基础", "q_type": "fill", "count": 10, "score_each": 4, "band": "easy"},
        {"name": "二、提升", "q_type": "fill", "count": 6, "score_each": 10, "band": "hard"},
    ]
    blueprint = _blueprint(db, sections=sections)
    chapter_id, kp_ids = _chapter(db)
    _add_questions(db, chapter_id=chapter_id, kp_ids=kp_ids, q_type="fill", count=40, difficulty=3)
    _add_questions(db, chapter_id=chapter_id, kp_ids=kp_ids, q_type="fill", count=10, difficulty=4)
    _add_questions(db, chapter_id=chapter_id, kp_ids=kp_ids, q_type="fill", count=10, difficulty=5)

    paper = generate_paper(db, user=user, blueprint=blueprint, chapter_ids=[chapter_id], seed=9)
    assert paper.refused is False
    assert paper.total_score == 100
    easy_items = [i for i in paper.items if i.section_index == 0]
    assert all(i.question.difficulty <= 3 for i in easy_items)
    assert BAND_QUANTILES["easy"] == (0.0, 0.6)


def test_refuses_when_question_type_missing(db: Session) -> None:
    """不接受降级卷：缺题型时拒绝出卷，不拿别的题型顶上。"""
    user = _user(db)
    sections = [
        {"name": "一、基础", "q_type": "fill", "count": 10, "score_each": 3},
        {"name": "二、习作", "q_type": "composition", "count": 1, "score_each": 70},
    ]
    blueprint = _blueprint(db, sections=sections)
    chapter_id, kp_ids = _chapter(db)
    _add_questions(db, chapter_id=chapter_id, kp_ids=kp_ids, q_type="fill", count=40, difficulty=2)

    paper = generate_paper(db, user=user, blueprint=blueprint, chapter_ids=[chapter_id], seed=7)
    assert paper.refused is True
    assert "composition" in (paper.refuse_reason or "")
    assert paper.shortages and paper.shortages[0].q_type == "composition"
    assert any(i.q_type == "composition" for i in paper.shortages)


def test_refuses_when_pool_short_but_legacy_fallback_available(db: Session) -> None:
    """题量不足默认拒绝；显式 allow_fallback=True 才回退到旧兜底行为。"""
    user = _user(db)
    blueprint = _blueprint(db)
    chapter_id, kp_ids = _chapter(db)
    _add_questions(db, chapter_id=chapter_id, kp_ids=kp_ids, q_type="choice", count=40, difficulty=2)

    strict = generate_paper(db, user=user, blueprint=blueprint, chapter_ids=[chapter_id], seed=7)
    assert strict.refused is True
    assert strict.insufficient is True

    legacy = generate_paper(
        db, user=user, blueprint=blueprint, chapter_ids=[chapter_id], seed=7, allow_fallback=True,
    )
    assert legacy.refused is False
    assert len(legacy.items) == 36


def test_short_pool_reports_items_and_refusal(db: Session) -> None:
    user = _user(db)
    blueprint = _blueprint(db)
    chapter_id, kp_ids = _chapter(db)
    _add_questions(db, chapter_id=chapter_id, kp_ids=kp_ids, q_type="fill", count=5, difficulty=1)

    paper = generate_paper(db, user=user, blueprint=blueprint, chapter_ids=[chapter_id], seed=8)
    assert len(paper.items) == 5
    assert paper.refused is True
    assert paper.insufficient is True
    assert paper.total_score == 15  # 5 题 × 3 分（第一节）


def test_offline_and_empty_answer_questions_are_excluded(db: Session) -> None:
    user = _user(db)
    blueprint = _blueprint(db)
    chapter_id, kp_ids = _chapter(db)
    _add_questions(db, chapter_id=chapter_id, kp_ids=kp_ids, q_type="fill", count=20,
                   difficulty=1, status="offline")
    for index in range(20):
        db.add(Question(
            chapter_id=chapter_id, knowledge_point_id=kp_ids[index % len(kp_ids)],
            subject="math", q_type="fill", difficulty=1,
            content={"stem": f"empty-{index}"}, answer={},
        ))
    db.commit()

    paper = generate_paper(db, user=user, blueprint=blueprint, chapter_ids=[chapter_id], seed=3)
    assert paper.available == 0
    assert paper.refused is True


def test_resolve_scope_chapters_book_half_and_unit(db: Session) -> None:
    book = Textbook(subject="math", grade=3, version="北师大版", semester="first")
    db.add(book)
    db.flush()
    for index in range(1, 7):
        db.add(Chapter(textbook_id=book.id, grade=3, name=f"第{index}单元", order_index=index))
    db.commit()

    assert len(resolve_scope_chapters(db, textbook_id=book.id, scope="book")) == 6
    assert len(resolve_scope_chapters(db, textbook_id=book.id, scope="half_book")) == 3
    unit_two = resolve_scope_chapters(db, textbook_id=book.id, scope="unit", unit_index=2)
    assert len(unit_two) == 1


def test_resolve_scope_matches_chinese_numeral_unit_names(db: Session) -> None:
    """教材常用「第一单元」等中文数字命名，必须能被 unit_index=1 命中。"""
    book = Textbook(subject="math", grade=1, version="北师大版", semester="first")
    db.add(book)
    db.flush()
    db.add_all([
        Chapter(textbook_id=book.id, grade=1, name="开篇", order_index=1),
        Chapter(textbook_id=book.id, grade=1, name="10以内加减法", order_index=1),
        Chapter(textbook_id=book.id, grade=1, name="第一单元 生活中的数", order_index=2),
        Chapter(textbook_id=book.id, grade=1, name="第二单元 5以内数加与减", order_index=3),
    ])
    db.commit()

    unit_one = resolve_scope_chapters(db, textbook_id=book.id, scope="unit", unit_index=1)
    names = [db.get(Chapter, cid).name for cid in unit_one]
    assert names == ["第一单元 生活中的数"]

    # 未命中的单元号退回「3 章折算」，但绝不再把「开篇」当成第一单元
    unit_three = resolve_scope_chapters(db, textbook_id=book.id, scope="unit", unit_index=3)
    assert unit_three and "开篇" not in [db.get(Chapter, cid).name for cid in unit_three]
