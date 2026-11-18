"""EX-11 / R-07：存量真题来源补录与隔离（不猜测来源）。

在 ``backend/`` 目录执行：

    python -m scripts.backfill_exam_sources --report
    python -m scripts.backfill_exam_sources --apply --source-map sources.json
    python -m scripts.backfill_exam_sources --quarantine

``--report`` 只读取出缺 ``source_name`` 的真题清单；``--apply`` 仅接受
``--source-map`` 里显式给出的映射（来源名称 + 授权依据均必填），缺映射的卷
跳过并在报告中列出，**脚本不推断来源**；``--quarantine`` 把仍未补录且处于
``published`` 的真题隔离为 ``draft``，避免无来源卷对外发布。

映射格式::

    {"<exam_id>": {"source_name": "...", "license_note": "...",
                   "adapted_from": "..."}}

真实公开真题须先由内容运营取得授权并登记到
``release/content-compliance/license-ledger.md`` §1，再逐卷补录。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.exam import Exam

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT = (
    REPO_ROOT / "release" / "content-compliance" / "exam-source-backfill.json"
)


def _has_source(exam: Exam) -> bool:
    return bool(exam.source_name and exam.source_name.strip())


def missing_source_exams(db: Session) -> list[Exam]:
    """列出所有缺来源的真题（含草稿/待复核/已发布）。"""
    return list(
        db.scalars(
            select(Exam)
            .where(Exam.is_past_paper.is_(True))
            .order_by(Exam.id)
        ).all()
    )


def report(db: Session) -> list[dict[str, Any]]:
    return [
        {
            "exam_id": exam.id,
            "title": exam.title,
            "year": exam.year,
            "region": exam.region,
            "status": exam.status,
            "source_name": exam.source_name,
            "has_source": _has_source(exam),
        }
        for exam in missing_source_exams(db)
        if not _has_source(exam)
    ]


def validate_source_map(raw: dict[str, Any]) -> dict[int, dict[str, Any]]:
    """校验显式映射；任何不合法项直接报错，不做猜测或补全。"""
    result: dict[int, dict[str, Any]] = {}
    for key, value in raw.items():
        try:
            exam_id = int(key)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"映射键必须是试卷 ID：{key!r}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"exam {exam_id}: 映射值必须是对象")
        source_name = str(value.get("source_name") or "").strip()
        license_note = str(value.get("license_note") or "").strip()
        if not source_name or not license_note:
            raise ValueError(
                f"exam {exam_id}: source_name 与 license_note 均必填（R-07 台账）"
            )
        adapted_from = str(value.get("adapted_from") or "").strip() or None
        result[exam_id] = {
            "source_name": source_name,
            "license_note": license_note,
            "adapted_from": adapted_from,
        }
    return result


def apply_source_map(
    db: Session, mapping: dict[int, dict[str, Any]], *, commit: bool = True
) -> dict[str, Any]:
    """只写显式映射；已有来源的卷不覆盖，非真题/不存在的 ID 跳过。"""
    applied: list[int] = []
    skipped: list[int] = []
    for exam_id, values in mapping.items():
        exam = db.get(Exam, exam_id)
        if exam is None or not exam.is_past_paper or _has_source(exam):
            skipped.append(exam_id)
            continue
        exam.source_name = values["source_name"]
        exam.license_note = values["license_note"]
        exam.adapted_from = values["adapted_from"]
        applied.append(exam_id)
    if commit:
        db.commit()
    return {"applied": applied, "skipped": skipped}


def quarantine(db: Session, *, commit: bool = True) -> list[int]:
    """未补录来源的 published 真题隔离为 draft（须复核后才可再发布）。"""
    changed: list[int] = []
    for exam in db.scalars(
        select(Exam).where(
            Exam.is_past_paper.is_(True), Exam.status == "published"
        )
    ).all():
        if _has_source(exam):
            continue
        exam.status = "draft"
        exam.review_note = "R-07 来源待补录，按 EX-11 隔离，复核前不得发布"
        changed.append(exam.id)
    if commit:
        db.commit()
    return changed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="存量真题来源补录（不猜测来源）")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--report", action="store_true", help="只读取出缺来源清单")
    group.add_argument("--apply", action="store_true", help="按显式映射补录")
    group.add_argument("--quarantine", action="store_true", help="隔离无来源已发布卷")
    parser.add_argument("--source-map", type=Path, help="--apply 用的显式映射 JSON")
    parser.add_argument(
        "--report-file", type=Path, default=DEFAULT_REPORT, help="--report 输出路径"
    )
    args = parser.parse_args(argv)

    db = SessionLocal()
    try:
        if args.report:
            rows = report(db)
            args.report_file.parent.mkdir(parents=True, exist_ok=True)
            args.report_file.write_text(
                json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(f"缺来源真题 {len(rows)} 张，清单：{args.report_file}")
            for row in rows:
                print(
                    f"  exam={row['exam_id']} status={row['status']} "
                    f"{row['title']}"
                )
            return 0
        if args.apply:
            if args.source_map is None or not args.source_map.is_file():
                parser.error("--apply 必须提供存在的 --source-map 文件")
            raw = json.loads(args.source_map.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                parser.error("--source-map 必须是 JSON 对象")
            result = apply_source_map(db, validate_source_map(raw))
            print(
                f"已补录 {len(result['applied'])} 张，跳过 "
                f"{len(result['skipped'])} 张（已有来源 / 非真题 / 不存在）"
            )
            return 0
        changed = quarantine(db)
        print(f"已隔离 {len(changed)} 张无来源已发布真题：{changed}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
