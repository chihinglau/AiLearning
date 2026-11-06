import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.grade import (
    GradeValidationError,
    derive_grade_group,
    derive_stage,
    resolve_grade_profile,
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
