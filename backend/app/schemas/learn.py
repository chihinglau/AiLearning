from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.content import KnowledgePointOut, QuestionPublic


class LearnStartIn(BaseModel):
    chapter_id: Optional[int] = None
    knowledge_point_id: Optional[int] = None
    subject: Optional[str] = None
    count: int = Field(default=10, ge=1, le=50)
    # 教材与年级不一致时需二次确认后继续（D-04 §13）
    confirm_mismatch: bool = False
    # P0-22：新范围方式（与 /practice/preview 共用同一组参数，seed 相同即同一套题）
    scope_type: Optional[str] = Field(default=None, pattern=r"^(kp|chapter|textbook|wrong)$")
    scope_ids: list[int] = Field(default_factory=list, max_length=50)
    q_types: list[str] = Field(default_factory=list)
    mode: str = "special"
    seed: Optional[int] = None
    duration_limit_min: Optional[int] = Field(default=None, ge=1, le=120)


class LearnStartOut(BaseModel):
    questions: list[QuestionPublic]
    seed: Optional[int] = None


class LearnSubmitIn(BaseModel):
    question_id: int
    user_answer: dict[str, Any]
    duration_ms: int = Field(default=0, ge=0)


class LearnSubmitOut(BaseModel):
    is_correct: bool
    correct_answer: dict[str, Any]
    analysis: Optional[str] = None
    mastery_score: Optional[float] = None
    in_wrong_book: bool = False


class KnowledgeNodeOut(KnowledgePointOut):
    """知识点（树节点）+ 个人掌握度。"""

    mastery_score: float = 0.0
    mastery_confidence: int = 0
    mastery_band: str = "weak"
    question_count: int = 0
    state: str = "未学习"
    last_studied_at: Optional[datetime] = None


class UnitOut(BaseModel):
    id: int
    textbook_id: int
    grade: int
    name: str
    order_index: int
    summary: Optional[str] = None
    section_count: int = 0
    kp_count: int = 0
    question_count: int = 0
    avg_mastery: float = 0.0
    mastery_band: str = "weak"
    learned_kp_count: int = 0
    progress: float = 0.0


class UnitSectionOut(BaseModel):
    id: int
    name: str
    order_index: int
    kp_count: int
    avg_mastery: float
    mastery_band: str


class UnitDetailOut(BaseModel):
    unit: UnitOut
    sections: list[UnitSectionOut] = []
    knowledge_points: list[KnowledgeNodeOut] = []


class KpBriefOut(BaseModel):
    id: int
    name: str
    subject: str
    mastery_score: float = 0.0


class KpDetailOut(BaseModel):
    id: int
    subject: str
    grade: Optional[int]
    name: str
    node_type: str
    explanation: Optional[str]
    section_id: Optional[int] = None
    section_name: Optional[str] = None
    prerequisites: list[KpBriefOut] = []
    mastery_score: float = 0.0
    mastery_confidence: int = 0
    mastery_band: str = "weak"
    question_count: int = 0
    state: str = "未学习"
    state_evidence: int = 0
    last_studied_at: Optional[datetime] = None


class KpSelfTestIn(BaseModel):
    score: float = Field(ge=0, le=100)


class KpStateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    knowledge_point_id: int
    state: str
    evidence_count: int
    last_event: Optional[str] = None
    read_at: Optional[datetime] = None
    mastered_at: Optional[datetime] = None
    updated_at: datetime


class ChapterTreeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    textbook_id: int
    grade: int
    name: str
    order_index: int
    summary: Optional[str]
    knowledge_points: list[KnowledgeNodeOut] = []


class WrongQuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question_id: int
    wrong_count: int
    correct_streak: int
    status: str
    interval_days: int
    next_review_at: Optional[datetime]
    last_wrong_at: datetime
    wrong_reason: Optional[str]
    # 联表冗余，方便错题本列表直接渲染
    subject: str = ""
    q_type: str = "choice"
    stem: str = ""
    chapter_id: int = 0
    knowledge_point_id: Optional[int] = None
    difficulty: int = 3


class WrongReasonIn(BaseModel):
    wrong_reason: str = Field(pattern=r"^(careless|concept|method|calculation|reading|other)$")


class MasteryMapOut(BaseModel):
    items: dict[str, float]


class PracticePreviewIn(BaseModel):
    scope_type: str = Field(pattern=r"^(kp|chapter|textbook|wrong)$")
    scope_ids: list[int] = Field(default_factory=list, max_length=50)
    count: int = Field(default=10, ge=1, le=50)
    q_types: list[str] = Field(default_factory=list)
    mode: str = "special"
    seed: Optional[int] = None
    duration_limit_min: Optional[int] = Field(default=None, ge=1, le=120)


class PracticePreviewOut(BaseModel):
    count: int
    available: int
    insufficient: bool
    estimated_minutes: int
    kp_coverage: float
    covered_kp_count: int
    range_kp_count: int
    q_type_mix: dict[str, int] = {}
    due_review_count: int
    seed: int


class LearnStatsOut(BaseModel):
    total_answered: int
    total_correct: int
    accuracy: float
    streak_days: int
    due_review_count: int
    active_wrong_count: int
    weak_points: list[KnowledgeNodeOut]


class HomeTextbook(BaseModel):
    subject: str
    textbook_id: int
    version: str
    grade: int
    semester: str
    mismatch: bool = False


class HomeTodayPlan(BaseModel):
    due_review: int
    practice_questions: int
    practice_minutes: int
    new_kp_target: int


class HomeContinue(BaseModel):
    subject: str
    chapter_id: Optional[int] = None
    chapter_name: Optional[str] = None
    knowledge_point_id: Optional[int] = None
    knowledge_point_name: Optional[str] = None


class HomeRecommendation(BaseModel):
    action: str
    label: str
    reason: str
    knowledge_point_id: Optional[int] = None


class HomeOut(BaseModel):
    grade: int
    stage: str
    grade_group: str
    semester: str
    region: str
    needs_binding: bool
    textbooks: list[HomeTextbook] = []
    recommended: list[HomeTextbook] = []
    mismatch_subjects: list[str] = []
    today_plan: HomeTodayPlan
    continue_learning: Optional[HomeContinue] = None
    recommendation: HomeRecommendation
    pending_exams: list[dict[str, Any]] = []

