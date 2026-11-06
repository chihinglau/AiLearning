from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class SchoolCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    region: str = Field(default="shenzhen", max_length=20)


class SchoolOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    region: str


class ClassCreate(BaseModel):
    school_id: Optional[int] = None
    grade: int = Field(ge=1, le=12)
    name: str = Field(min_length=1, max_length=60)
    school_year: str = Field(min_length=4, max_length=20)
    head_teacher_id: Optional[int] = None


class ClassOut(BaseModel):
    id: int
    school_id: int
    grade: int
    name: str
    head_teacher_id: Optional[int]
    school_year: str
    member_count: int = 0


class ClassMemberAdd(BaseModel):
    student_ids: List[int] = Field(min_length=1, max_length=200)


class ClassMemberAddOut(BaseModel):
    added: int
    skipped: int


class AssignmentCreate(BaseModel):
    teacher_id: int
    class_id: int
    subject: str = Field(min_length=1, max_length=20)
    role_in_class: str = Field(
        default="subject_teacher", pattern=r"^(subject_teacher|head_teacher)$"
    )


class AssignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    teacher_id: int
    class_id: int
    subject: str
    role_in_class: str
