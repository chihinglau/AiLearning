"""EX-11 / L29：存量真题来源补录脚本（不猜测来源，R-07 台账）。"""

import pytest
from sqlalchemy.orm import Session

from app.models.exam import Exam
from scripts.backfill_exam_sources import (
    apply_source_map,
    quarantine,
    report,
    validate_source_map,
)


def _paper(
    db: Session,
    *,
    title: str,
    source_name: str | None = None,
    status: str = "published",
) -> Exam:
    row = Exam(
        title=title,
        subject="math",
        grade=1,
        source="past_paper",
        exam_type="mock",
        total_score=100,
        time_limit_min=60,
        questions=[],
        is_past_paper=True,
        year=2020,
        status=status,
        source_name=source_name,
    )
    db.add(row)
    db.flush()
    db.commit()
    return row


def test_report_only_lists_missing_source(db: Session) -> None:
    missing = _paper(db, title="缺来源卷")
    _paper(db, title="有来源卷", source_name="已登记来源")

    rows = report(db)
    assert [row["exam_id"] for row in rows] == [missing.id]
    assert rows[0]["has_source"] is False
    assert rows[0]["status"] == "published"


def test_validate_source_map_rejects_incomplete_entries() -> None:
    with pytest.raises(ValueError, match="license_note"):
        validate_source_map({"1": {"source_name": "某来源"}})
    with pytest.raises(ValueError, match="试卷 ID"):
        validate_source_map({"not-an-id": {"source_name": "x", "license_note": "y"}})

    parsed = validate_source_map(
        {
            "1": {
                "source_name": "深圳市教育考试院公开真题",
                "license_note": "R-07 台账第 N 条授权凭证",
                "adapted_from": "公开卷改写",
            }
        }
    )
    assert parsed[1]["source_name"] == "深圳市教育考试院公开真题"
    assert parsed[1]["adapted_from"] == "公开卷改写"


def test_apply_writes_only_explicit_mapping(db: Session) -> None:
    target = _paper(db, title="待补录卷")
    untouched = _paper(db, title="未给映射卷")
    existing = _paper(db, title="已有来源卷", source_name="已登记来源")

    result = apply_source_map(
        db,
        validate_source_map(
            {
                str(target.id): {
                    "source_name": "已核验来源",
                    "license_note": "授权凭证已登记",
                }
            }
        ),
    )
    assert result["applied"] == [target.id]
    db.expire_all()
    assert db.get(Exam, target.id).source_name == "已核验来源"
    assert db.get(Exam, target.id).license_note == "授权凭证已登记"
    assert db.get(Exam, untouched.id).source_name is None
    assert db.get(Exam, existing.id).source_name == "已登记来源"


def test_quarantine_hides_published_without_source(db: Session) -> None:
    missing = _paper(db, title="无来源已发布卷")
    sourced = _paper(db, title="有来源已发布卷", source_name="已登记来源")
    draft = _paper(db, title="无来源草稿", status="draft")

    changed = quarantine(db)
    assert changed == [missing.id]
    db.expire_all()
    assert db.get(Exam, missing.id).status == "draft"
    assert db.get(Exam, sourced.id).status == "published"
    assert db.get(Exam, draft.id).status == "draft"
