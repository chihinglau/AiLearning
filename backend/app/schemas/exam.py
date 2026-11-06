from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.schemas.content import QuestionPublic


class ExamAttemptBriefOut(BaseModel):
    """考试列表中的作答摘要。"""

    id: int
    status: str
    seed: int
    started_at: datetime
    submitted_at: Optional[datetime] = None
    duration_ms: int = 0
    objective_score: float = 0.0
    subjective_score: Optional[float] = None
    total_score: Optional[float] = None
    remaining_seconds: int = 0


class ExamSummaryOut(BaseModel):
    id: int
    title: str
    subject: str
    grade: int
    year: Optional[int] = None
    exam_type: str
    total_score: int
    time_limit_min: int
    question_count: int
    category: str  # available | in_progress | completed
    window_start: Optional[datetime] = None
    window_end: Optional[datetime] = None
    window_state: str = "unscheduled"  # open | scheduled | closed | unscheduled
    attempt: Optional[ExamAttemptBriefOut] = None


class ExamQuestionOut(QuestionPublic):
    """试卷题目：学生端不含答案，附分值与分节信息。"""

    score: float = 0.0
    section_index: int = 0
    section_name: Optional[str] = None
    order_index: int = 0


class ExamDetailOut(BaseModel):
    id: int
    title: str
    subject: str
    grade: int
    year: Optional[int] = None
    source: str
    exam_type: str
    total_score: int
    time_limit_min: int
    status: str
    question_count: int
    window_start: Optional[datetime] = None
    window_end: Optional[datetime] = None
    window_state: str = "unscheduled"
    questions: list[ExamQuestionOut]


class ExamAnswerOut(BaseModel):
    question_id: int
    user_answer: Optional[dict[str, Any]] = None
    is_correct: Optional[bool] = None
    score: Optional[float] = None
    self_score: Optional[float] = None
    updated_at: Optional[datetime] = None


class ExamAttemptOut(BaseModel):
    id: int
    exam_id: int
    status: str
    seed: int
    started_at: datetime
    submitted_at: Optional[datetime] = None
    duration_ms: int = 0
    objective_score: float = 0.0
    subjective_score: Optional[float] = None
    total_score: Optional[float] = None
    submit_token: Optional[str] = None
    remaining_seconds: int = 0
    server_now: datetime
    exam: ExamDetailOut
    answers: list[ExamAnswerOut] = Field(default_factory=list)
    next_index: int = 0


class ExamAttemptStartIn(BaseModel):
    seed: Optional[int] = None


class ExamAnswerSaveIn(BaseModel):
    question_id: int
    user_answer: Optional[dict[str, Any]] = None


class ExamSaveIn(BaseModel):
    answers: list[ExamAnswerSaveIn] = Field(default_factory=list)


class ExamSaveOut(BaseModel):
    attempt_id: int
    saved: int
    saved_at: datetime
    status: str
    remaining_seconds: int
    answers: list[ExamAnswerOut] = Field(default_factory=list)


class ExamSubmitIn(BaseModel):
    submit_token: str = Field(min_length=1, max_length=64)
    answers: list[ExamAnswerSaveIn] = Field(default_factory=list)
    duration_ms: Optional[int] = Field(default=None, ge=0)


class ExamSubmitOut(BaseModel):
    attempt_id: int
    status: str
    duplicate: bool = False
    objective_score: float = 0.0
    subjective_score: Optional[float] = None
    total_score: Optional[float] = None
    correct_count: int = 0
    question_count: int = 0
    pending_grading: bool = False
    submitted_at: Optional[datetime] = None


class ExamGenerateIn(BaseModel):
    blueprint_code: str = Field(min_length=1, max_length=80)
    chapter_ids: list[int] = Field(min_length=1, max_length=50)
    title: Optional[str] = Field(default=None, max_length=200)
    seed: Optional[int] = None
    window_start: Optional[datetime] = None
    window_end: Optional[datetime] = None


class ExamGenerateOut(BaseModel):
    exam_id: int
    title: str
    seed: int
    question_count: int
    total_score: float
    kp_coverage: float
    difficulty_mix: dict[str, int] = Field(default_factory=dict)
    fallback_count: int = 0
    insufficient: bool = False


class ExamTypeStatOut(BaseModel):
    q_type: str
    question_count: int
    answered: int
    correct: int
    score: float
    full_score: float
    score_rate: float


class ExamKpStatOut(BaseModel):
    knowledge_point_id: Optional[int] = None
    name: str
    question_count: int
    correct: int
    score: float
    full_score: float
    score_rate: float


class ExamWrongItemOut(BaseModel):
    question_id: int
    q_type: str
    stem: str
    user_answer: Optional[dict[str, Any]] = None
    correct_answer: dict[str, Any]
    analysis: Optional[str] = None
    score: float
    full_score: float


class ExamNextActionOut(BaseModel):
    action: str
    label: str
    knowledge_point_ids: list[int] = Field(default_factory=list)
    count: int = 0


class ExamSubjectiveItemOut(BaseModel):
    question_id: int
    q_type: str
    stem: str
    full_score: float
    user_answer: Optional[dict[str, Any]] = None
    reference_answer: Optional[dict[str, Any]] = None
    scoring_points: list[str] = Field(default_factory=list)
    analysis: Optional[str] = None
    self_score: Optional[float] = None


class SelfAssessItemIn(BaseModel):
    question_id: int
    score: float = Field(ge=0)


class ExamSelfAssessIn(BaseModel):
    items: list[SelfAssessItemIn] = Field(min_length=1, max_length=50)


class ExamSelfAssessOut(BaseModel):
    attempt_id: int
    status: str
    objective_score: float = 0.0
    subjective_score: float = 0.0
    total_score: float = 0.0
    assessed_count: int = 0
    pending_count: int = 0


class ExamAbilityStatOut(BaseModel):
    """能力维度统计：理解/计算/应用/分析（按学科题型配置聚合）。"""

    ability: str
    label: str
    question_count: int = 0
    score: float = 0.0
    full_score: float = 0.0
    score_rate: float = 0.0


class ExamClassAverageOut(BaseModel):
    """班级平均（仅聚合值；无班级或班级无人参加时不提供）。"""

    available: bool = False
    class_name: Optional[str] = None
    student_count: int = 0
    average_score: Optional[float] = None
    average_rate: Optional[float] = None


class ExamTrendPointOut(BaseModel):
    attempt_id: int
    exam_id: int
    exam_title: str
    exam_type: str
    score_rate: float
    total_score: Optional[float] = None
    submitted_at: Optional[datetime] = None


class ExamTrendOut(BaseModel):
    points: list[ExamTrendPointOut] = Field(default_factory=list)
    delta_rate: Optional[float] = None


class ExamReportOut(BaseModel):
    attempt_id: int
    exam_id: int
    exam_title: str
    exam_type: str
    status: str
    total_score: Optional[float] = None
    full_score: float = 0.0
    objective_score: float = 0.0
    subjective_score: Optional[float] = None
    correct_count: int = 0
    question_count: int = 0
    answered_count: int = 0
    accuracy: float = 0.0
    duration_ms: int = 0
    submitted_at: Optional[datetime] = None
    type_stats: list[ExamTypeStatOut] = Field(default_factory=list)
    kp_stats: list[ExamKpStatOut] = Field(default_factory=list)
    ability_stats: list[ExamAbilityStatOut] = Field(default_factory=list)
    class_average: ExamClassAverageOut = Field(default_factory=ExamClassAverageOut)
    trend: ExamTrendOut = Field(default_factory=ExamTrendOut)
    wrong_questions: list[ExamWrongItemOut] = Field(default_factory=list)
    pending_subjective: list[ExamSubjectiveItemOut] = Field(default_factory=list)
    next_actions: list[ExamNextActionOut] = Field(default_factory=list)

