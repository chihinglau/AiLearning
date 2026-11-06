"""年级 / 学段派生规则（服务端唯一实现，见 D-03 §4.1）。"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


class GradeValidationError(Exception):
    """年级校验失败，携带稳定错误码供前端分支处理。"""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class GradeProfile:
    stage: str
    grade_group: str


def derive_stage(grade: int) -> str:
    if not 1 <= grade <= 12:
        raise GradeValidationError("GRADE_OUT_OF_RANGE", "年级必须在 1-12 之间")
    if grade <= 6:
        return "primary"
    if grade <= 9:
        return "junior"
    return "senior"


def derive_grade_group(grade: int) -> str:
    if not 1 <= grade <= 12:
        raise GradeValidationError("GRADE_OUT_OF_RANGE", "年级必须在 1-12 之间")
    if grade <= 2:
        return "primary_low"
    if grade <= 4:
        return "primary_mid"
    if grade <= 6:
        return "primary_high"
    if grade <= 9:
        return "junior"
    return "senior"


def resolve_grade_profile(
    grade: Optional[int], stage: Optional[str] = None, role: str = "student"
) -> Optional[GradeProfile]:
    """学生必须提供年级；服务端派生 stage/grade_group，并校验客户端学段声明。"""
    if grade is None:
        if role == "student":
            raise GradeValidationError("GRADE_REQUIRED", "学生账号必须选择年级")
        return None

    derived_stage = derive_stage(grade)
    if stage is not None and stage != derived_stage:
        raise GradeValidationError(
            "STAGE_MISMATCH", f"学段 {stage} 与年级 {grade}（{derived_stage}）不一致"
        )
    return GradeProfile(stage=derived_stage, grade_group=derive_grade_group(grade))


def validate_elective_subjects(subjects: Optional[list], grade: Optional[int]) -> None:
    """选科仅高中（10-12 年级）可填。"""
    if not subjects:
        return
    if grade is None or derive_stage(grade) != "senior":
        raise GradeValidationError("ELECTIVE_ONLY_SENIOR", "选科仅在高中年级（10-12）可选")


def academic_year(dt: datetime) -> str:
    """学年标识：9 月及以后属于新学年。"""
    start = dt.year if dt.month >= 9 else dt.year - 1
    return f"{start}-{start + 1}"


def semester_start(dt: datetime) -> datetime:
    """当前学期起点（9/1 或 2/1），用于自助改年级的每学期频率限制。"""
    if dt.month >= 9:
        return datetime(dt.year, 9, 1)
    if dt.month == 1:
        return datetime(dt.year - 1, 9, 1)
    return datetime(dt.year, 2, 1)

