"""PG-02 蓝图矩阵：g1–g9 × 语数英 × 单元/期中/期末 = 81 条，分值与题量自洽。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.exam import ExamBlueprint
from app.services.exam_blueprint_matrix import (
    LEGACY_CODES,
    apply_matrix,
    build_specs,
)


def test_matrix_covers_nine_grades_three_subjects_three_types() -> None:
    specs = build_specs()
    assert len(specs) == 81

    codes = {spec["code"] for spec in specs}
    assert len(codes) == 81
    for grade in range(1, 10):
        for subject in ("chinese", "math", "english"):
            for exam_type in ("unit", "midterm", "final"):
                assert f"g{grade}_{subject}_{exam_type}" in codes


def test_matrix_sections_sum_to_declared_total() -> None:
    for spec in build_specs():
        total = sum(s["count"] * s["score_each"] for s in spec["sections"])
        assert total == spec["total_score"], spec["code"]
        assert spec["total_score"] in (60, 100)


def test_olympiad_types_are_declared_strict() -> None:
    """语文必须含习作（composition）、英语必须含听力（listening）——缺则不降级。"""
    specs = {spec["code"]: spec for spec in build_specs()}
    chinese_types = {
        s["q_type"] for s in specs["g1_chinese_final"]["sections"]
    }
    english_types = {
        s["q_type"] for s in specs["g1_english_final"]["sections"]
    }
    assert "composition" in chinese_types
    assert "listening" in english_types
    assert "composition" not in {s["q_type"] for s in specs["g1_math_final"]["sections"]}


def test_apply_matrix_is_idempotent_and_deactivates_legacy(db: Session) -> None:
    first = apply_matrix(db)
    assert first["created"] == 81
    assert first["deactivated"] == 0  # 测试库里没有旧蓝图

    second = apply_matrix(db)
    assert second["created"] == 0
    assert second["updated"] == 81

    rows = list(db.scalars(select(ExamBlueprint)))
    assert len(rows) == 81
    assert all(row.is_active for row in rows)


def test_apply_matrix_deactivates_legacy_rows(db: Session) -> None:
    legacy = ExamBlueprint(
        code=LEGACY_CODES[0], name="旧蓝图", subject="math", grade=3,
        exam_type="unit", total_score=100, time_limit_min=60,
        sections=[{"name": "一", "q_type": "fill", "count": 1, "score_each": 100}],
        kp_coverage_min=0.8, is_active=True,
    )
    db.add(legacy)
    db.commit()

    result = apply_matrix(db)
    assert result["deactivated"] == 1

    db.refresh(legacy)
    assert legacy.is_active is False
