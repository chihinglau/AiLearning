"""教材推荐与绑定（D-04 §4、§5）。"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.grade import derive_stage, derive_semester
from app.models.content import Textbook
from app.models.textbook import TextbookBinding
from app.models.user import User

STAGE_SUBJECTS = {
    "primary": ["chinese", "math", "english"],
    "junior": [
        "chinese",
        "math",
        "english",
        "physics",
        "chemistry",
        "biology",
        "history",
        "geography",
        "politics",
    ],
    "senior": [
        "chinese",
        "math",
        "english",
        "physics",
        "chemistry",
        "biology",
        "history",
        "geography",
        "politics",
    ],
}

# 深圳本地化优先：版本名含"深圳"的教材排在最前（如小学英语牛津深圳版）
_SHENZHEN_KEYWORD = "深圳"


def _subject_textbook(db: Session, *, subject: str, grade: int, semester: str) -> Textbook | None:
    candidates = list(
        db.scalars(
            select(Textbook).where(
                Textbook.subject == subject,
                Textbook.grade == grade,
                Textbook.semester == semester,
                Textbook.is_active.is_(True),
            )
        )
    )
    if not candidates:
        return None
    candidates.sort(
        key=lambda t: (0 if _SHENZHEN_KEYWORD in t.version else 1, t.id)
    )
    return candidates[0]


def recommended_textbooks(
    db: Session, *, grade: int, semester: str, region: str = "shenzhen"
) -> list[tuple[str, Textbook]]:
    """按学段开课科目返回每科推荐教材（深圳版本优先）。"""
    subjects = STAGE_SUBJECTS.get(derive_stage(grade), STAGE_SUBJECTS["primary"])
    result: list[tuple[str, Textbook]] = []
    for subject in subjects:
        textbook = _subject_textbook(db, subject=subject, grade=grade, semester=semester)
        if textbook is not None:
            result.append((subject, textbook))
    return result


def _upsert_binding(
    db: Session,
    *,
    user_id: int,
    subject: str,
    semester: str,
    textbook_id: int,
    source: str,
) -> TextbookBinding:
    binding = db.scalar(
        select(TextbookBinding).where(
            TextbookBinding.user_id == user_id,
            TextbookBinding.subject == subject,
            TextbookBinding.semester == semester,
            TextbookBinding.textbook_id == textbook_id,
        )
    )
    if binding is None:
        binding = TextbookBinding(
            user_id=user_id,
            subject=subject,
            semester=semester,
            textbook_id=textbook_id,
            source=source,
            is_primary=True,
            status="active",
        )
        db.add(binding)
    else:
        binding.status = "active"
        binding.is_primary = True
        binding.source = source
    return binding


def _archive_others(
    db: Session, *, user_id: int, subject: str, semester: str, keep_textbook_id: int
) -> None:
    rows = db.scalars(
        select(TextbookBinding).where(
            TextbookBinding.user_id == user_id,
            TextbookBinding.subject == subject,
            TextbookBinding.semester == semester,
            TextbookBinding.textbook_id != keep_textbook_id,
            TextbookBinding.status == "active",
        )
    )
    for row in rows:
        row.status = "archived"


def auto_bind(db: Session, user: User, *, now: datetime | None = None) -> list[TextbookBinding]:
    """按年级+学期自动绑定推荐教材，幂等。"""
    moment = now or datetime.utcnow()
    semester = derive_semester(moment)
    user.semester = semester
    grade = user.grade or 1
    bindings: list[TextbookBinding] = []
    for subject, textbook in recommended_textbooks(
        db, grade=grade, semester=semester, region=user.region or "shenzhen"
    ):
        _archive_others(
            db, user_id=user.id, subject=subject, semester=semester, keep_textbook_id=textbook.id
        )
        bindings.append(
            _upsert_binding(
                db,
                user_id=user.id,
                subject=subject,
                semester=semester,
                textbook_id=textbook.id,
                source="auto",
            )
        )
    db.flush()
    return bindings


def manual_bind(
    db: Session, user: User, *, subject: str, textbook_id: int
) -> TextbookBinding:
    textbook = db.get(Textbook, textbook_id)
    if textbook is None:
        raise ValueError("TEXTBOOK_NOT_FOUND")
    if textbook.subject != subject:
        raise ValueError("SUBJECT_MISMATCH")
    semester = user.semester or derive_semester(datetime.utcnow())
    _archive_others(
        db, user_id=user.id, subject=subject, semester=semester, keep_textbook_id=textbook_id
    )
    binding = _upsert_binding(
        db,
        user_id=user.id,
        subject=subject,
        semester=semester,
        textbook_id=textbook_id,
        source="manual",
    )
    db.flush()
    return binding


def active_bindings(db: Session, user: User) -> list[tuple[TextbookBinding, Textbook]]:
    rows = db.execute(
        select(TextbookBinding, Textbook)
        .join(Textbook, Textbook.id == TextbookBinding.textbook_id)
        .where(
            TextbookBinding.user_id == user.id,
            TextbookBinding.status == "active",
        )
        .order_by(TextbookBinding.subject)
    ).all()
    return [(binding, textbook) for binding, textbook in rows]


def mismatched_subjects(db: Session, user: User) -> list[str]:
    """绑定的教材年级与用户年级不一致的学科（D-04 §13 冲突检测）。"""
    grade = user.grade
    if grade is None:
        return []
    rows = db.execute(
        select(TextbookBinding, Textbook)
        .join(Textbook, Textbook.id == TextbookBinding.textbook_id)
        .where(
            TextbookBinding.user_id == user.id,
            TextbookBinding.status == "active",
        )
    ).all()
    return sorted({b.subject for b, t in rows if t.grade != grade})


def has_mismatch(db: Session, user: User, subject: str) -> bool:
    """指定学科的当前教材是否与年级不一致。"""
    if user.grade is None:
        return False
    row = db.execute(
        select(TextbookBinding, Textbook)
        .join(Textbook, Textbook.id == TextbookBinding.textbook_id)
        .where(
            TextbookBinding.user_id == user.id,
            TextbookBinding.subject == subject,
            TextbookBinding.status == "active",
        )
    ).first()
    return bool(row and row[1].grade != user.grade)
