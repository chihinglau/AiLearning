from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.grade import (
    GradeProfile,
    GradeValidationError,
    academic_year,
    derive_grade_group,
    derive_semester,
    derive_stage,
    resolve_grade_profile,
    semester_start,
    validate_elective_subjects,
)
from app.models.user import User


def test_derive_stage_and_group_boundaries() -> None:
    assert derive_stage(1) == "primary"
    assert derive_stage(6) == "primary"
    assert derive_stage(7) == "junior"
    assert derive_stage(9) == "junior"
    assert derive_stage(10) == "senior"
    assert derive_stage(12) == "senior"
    assert derive_grade_group(2) == "primary_low"
    assert derive_grade_group(3) == "primary_mid"
    assert derive_grade_group(5) == "primary_high"
    assert derive_grade_group(8) == "junior"
    assert derive_grade_group(11) == "senior"

    with pytest.raises(GradeValidationError):
        derive_stage(13)
    with pytest.raises(GradeValidationError):
        resolve_grade_profile(None)


def test_register_student_derives_grade_dimension(client: TestClient, db: Session) -> None:
    response = client.post(
        "/api/auth/register",
        json={"phone": "13700000011", "password": "pass1234", "grade": 3},
    )
    assert response.status_code == 201, response.text

    user = db.scalar(select(User).where(User.phone == "13700000011"))
    assert user is not None
    assert user.stage == "primary"
    assert user.grade_group == "primary_mid"
    assert user.grade_updated_at is not None


def test_register_student_requires_grade(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register", json={"phone": "13700000012", "password": "pass1234"}
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "GRADE_REQUIRED"


def test_register_stage_mismatch_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register",
        json={"phone": "13700000013", "password": "pass1234", "grade": 8, "stage": "primary"},
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "STAGE_MISMATCH"


def test_register_elective_subjects_only_for_senior(client: TestClient) -> None:
    rejected = client.post(
        "/api/auth/register",
        json={
            "phone": "13700000014",
            "password": "pass1234",
            "grade": 8,
            "elective_subjects": ["physics"],
        },
    )
    assert rejected.status_code == 422
    assert rejected.json()["detail"]["code"] == "ELECTIVE_ONLY_SENIOR"

    accepted = client.post(
        "/api/auth/register",
        json={
            "phone": "13700000015",
            "password": "pass1234",
            "grade": 11,
            "elective_subjects": ["physics", "chemistry"],
        },
    )
    assert accepted.status_code == 201, accepted.text


def test_parent_register_without_grade(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register",
        json={"phone": "13700000016", "password": "pass1234", "role": "parent"},
    )
    assert response.status_code == 201, response.text
    assert response.json()["stage"] is None


def test_grade_dimension_full_matrix() -> None:
    profile_by_grade = {
        1: ("primary", "primary_low"),
        2: ("primary", "primary_low"),
        3: ("primary", "primary_mid"),
        4: ("primary", "primary_mid"),
        5: ("primary", "primary_high"),
        6: ("primary", "primary_high"),
        7: ("junior", "junior"),
        8: ("junior", "junior"),
        9: ("junior", "junior"),
        10: ("senior", "senior"),
        11: ("senior", "senior"),
        12: ("senior", "senior"),
    }
    for grade, (stage, group) in profile_by_grade.items():
        assert derive_stage(grade) == stage, grade
        assert derive_grade_group(grade) == group, grade


@pytest.mark.parametrize("grade", [0, -3, 13, 100])
def test_grade_out_of_range_carries_code(grade: int) -> None:
    for derive in (derive_stage, derive_grade_group):
        with pytest.raises(GradeValidationError) as exc:
            derive(grade)
        assert exc.value.code == "GRADE_OUT_OF_RANGE"


def test_resolve_grade_profile_derives_and_validates_stage() -> None:
    profile = resolve_grade_profile(9, stage="junior")
    assert profile == GradeProfile(stage="junior", grade_group="junior")

    with pytest.raises(GradeValidationError) as exc:
        resolve_grade_profile(10, stage="junior")
    assert exc.value.code == "STAGE_MISMATCH"

    with pytest.raises(GradeValidationError) as exc:
        resolve_grade_profile(None, role="student")
    assert exc.value.code == "GRADE_REQUIRED"

    assert resolve_grade_profile(None, role="parent") is None


def test_elective_subjects_only_senior() -> None:
    validate_elective_subjects(None, grade=8)
    validate_elective_subjects([], grade=8)
    validate_elective_subjects(["physics"], grade=11)

    with pytest.raises(GradeValidationError) as exc:
        validate_elective_subjects(["physics"], grade=8)
    assert exc.value.code == "ELECTIVE_ONLY_SENIOR"

    with pytest.raises(GradeValidationError) as exc:
        validate_elective_subjects(["physics"], None)
    assert exc.value.code == "ELECTIVE_ONLY_SENIOR"


def test_academic_year_and_semester_boundaries() -> None:
    assert academic_year(datetime(2026, 9, 1)) == "2026-2027"
    assert academic_year(datetime(2026, 8, 31)) == "2025-2026"

    assert semester_start(datetime(2026, 9, 1)) == datetime(2026, 9, 1)
    assert semester_start(datetime(2026, 1, 15)) == datetime(2025, 9, 1)
    assert semester_start(datetime(2026, 2, 1)) == datetime(2026, 2, 1)

    assert derive_semester(datetime(2026, 1, 1)) == "first"
    assert derive_semester(datetime(2026, 2, 1)) == "second"
    assert derive_semester(datetime(2026, 8, 31)) == "second"
    assert derive_semester(datetime(2026, 9, 1)) == "first"
