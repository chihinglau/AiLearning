"""P2-03 班级作业与教师批改的请求/响应模型。"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AssignmentCreateIn(BaseModel):
    class_id: int
    title: str = Field(min_length=1, max_length=200)
    subject: str
    chapter_ids: List[int] = Field(min_length=1, max_length=30)
    count: int = Field(default=10, ge=1, le=50)
    q_types: List[str] = Field(default_factory=lambda: ["choice"], max_length=5)
    time_limit_min: int = Field(default=30, ge=5, le=180)
    due_at: Optional[datetime] = None


class AssignmentStudentOut(BaseModel):
    student_id: int
    nickname: Optional[str] = None
    attempt_id: Optional[int] = None
    status: Optional[str] = None
    objective_score: Optional[float] = None
    subjective_score: Optional[float] = None
    total_score: Optional[float] = None
    submitted_at: Optional[datetime] = None


class AssignmentOut(BaseModel):
    id: int
    title: str
    subject: str
    class_id: int
    class_name: str
    exam_id: int
    due_at: Optional[datetime] = None
    status: str
    created_at: datetime
    student_count: int
    submitted_count: int
    pending_grading: int
    my_attempt_id: Optional[int] = None
    my_status: Optional[str] = None
    my_total_score: Optional[float] = None


class AssignmentDetailOut(AssignmentOut):
    students: List[AssignmentStudentOut] = Field(default_factory=list)


class GradingItemOut(BaseModel):
    attempt_id: int
    student_id: int
    student_name: Optional[str] = None
    question_id: int
    q_type: str
    content: Dict[str, Any]
    answer: Dict[str, Any]
    analysis: Optional[str] = None
    user_answer: Optional[Dict[str, Any]] = None
    max_score: float
    current_score: Optional[float] = None
    comment: Optional[str] = None


class GradingListOut(BaseModel):
    assignment_id: int
    items: List[GradingItemOut]


class GradeItemIn(BaseModel):
    attempt_id: int
    question_id: int
    score: float = Field(ge=0)
    comment: Optional[str] = Field(default=None, max_length=500)


class GradeBatchIn(BaseModel):
    items: List[GradeItemIn] = Field(min_length=1, max_length=100)


class GradeBatchOut(BaseModel):
    graded: int
    completed_attempts: int
    pending_attempts: int
