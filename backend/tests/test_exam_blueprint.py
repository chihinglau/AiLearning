"""P0-25 试卷蓝图表与小学语数英单元测种子。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.exam import ExamBlueprint
from scripts.seed import EXAM_BLUEPRINT_SEEDS, _put_blueprint, _seed_blueprints


def test_seed_blueprints_idempotent(db: Session) -> None:
    assert _seed_blueprints(db) == 3
    db.commit()
    first = list(db.scalars(select(ExamBlueprint)))
    assert len(first) == 3
    assert {bp.subject for bp in first} == {"math", "chinese", "english"}

    assert _seed_blueprints(db) == 3
    db.commit()
    math_rows = list(
        db.scalars(select(ExamBlueprint).where(ExamBlueprint.code == "math_primary_unit"))
    )
    assert len(math_rows) == 1


def test_blueprint_sections_sum_to_total(db: Session) -> None:
    _seed_blueprints(db)
    db.commit()
    blueprints = {bp.code: bp for bp in db.scalars(select(ExamBlueprint))}
    assert set(blueprints) == {"math_primary_unit", "chinese_primary_unit", "english_primary_unit"}

    for spec in EXAM_BLUEPRINT_SEEDS:
        bp = blueprints[spec["code"]]
        assert bp.exam_type == "unit"
        assert bp.total_score == 100
        assert bp.kp_coverage_min == 0.8
        assert bp.is_active is True
        section_score = sum(s["count"] * s["score_each"] for s in bp.sections)
        assert section_score == bp.total_score


def test_put_blueprint_updates_existing_row(db: Session) -> None:
    first = _put_blueprint(
        db,
        code="math_primary_unit",
        name="旧名称",
        subject="math",
        grade=3,
        exam_type="unit",
        total_score=100,
        time_limit_min=60,
        sections=[{"name": "一、计算", "q_type": "fill", "count": 10, "score_each": 3}],
        kp_coverage_min=0.8,
        difficulty_mix={"easy": 0.7},
    )
    db.commit()
    original_id = first.id

    second = _put_blueprint(
        db,
        code="math_primary_unit",
        name="新名称",
        subject="math",
        grade=3,
        exam_type="unit",
        total_score=120,
        time_limit_min=90,
        sections=[{"name": "一、计算", "q_type": "fill", "count": 12, "score_each": 10}],
        kp_coverage_min=0.8,
        difficulty_mix={"easy": 0.7},
    )
    db.commit()

    assert second.id == original_id
    assert second.name == "新名称"
    assert second.total_score == 120
    assert second.time_limit_min == 90
