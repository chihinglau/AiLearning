"""SQLAlchemy 模型统一出口，Alembic 依赖此处的导入顺序。"""

from app.db.base import Base
from app.models.assignment import Assignment
from app.models.content import Chapter, KnowledgePoint, Question, Textbook
from app.models.content_report import ContentReport
from app.models.content_review import ContentReview
from app.models.exam import Exam, ExamAnswer, ExamAttempt, ExamBlueprint, ExamSubmission
from app.models.legal import ConsentRecord
from app.models.org import ClassMember, School, SchoolClass, TeacherClassAssignment
from app.models.practice import (
    KpStudyState,
    MasteryScore,
    PracticeSession,
    StudentQuestionRecord,
    WrongQuestion,
)
from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.textbook import TextbookBinding
from app.models.user import AuditLog, GradeHistory, ParentChildBinding, User

__all__ = [
    "Base",
    "User",
    "GradeHistory",
    "ParentChildBinding",
    "AuditLog",
    "Textbook",
    "Chapter",
    "Question",
    "KnowledgePoint",
    "TextbookBinding",
    "StudentQuestionRecord",
    "MasteryScore",
    "WrongQuestion",
    "KpStudyState",
    "PracticeSession",
    "Exam",
    "ExamBlueprint",
    "ExamAttempt",
    "ExamAnswer",
    "ExamSubmission",
    "School",
    "SchoolClass",
    "ClassMember",
    "TeacherClassAssignment",
    "Assignment",
    "Role",
    "Permission",
    "RolePermission",
    "UserRole",
    "ContentReview",
    "ContentReport",
    "ConsentRecord",
]
