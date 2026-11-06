"""学生教材绑定 API（D-04 §5.5）。"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.grade import derive_semester
from app.db.session import get_db
from app.models.content import Textbook
from app.models.textbook import TextbookBinding
from app.models.user import User
from app.schemas.textbook import (
    AutoBindOut,
    BindIn,
    BindingOut,
    RecommendationOut,
    RecommendedSubject,
    TextbookBrief,
)
from app.services import textbook as service

router = APIRouter(prefix="/me/textbooks", tags=["教材绑定"])


def _require_student(current: User) -> None:
    if current.role != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "NOT_STUDENT", "message": "仅学生账号可管理教材绑定"},
        )


def _binding_out(binding: TextbookBinding, textbook) -> BindingOut:
    return BindingOut(
        id=binding.id,
        subject=binding.subject,
        semester=binding.semester,
        source=binding.source,
        is_primary=binding.is_primary,
        status=binding.status,
        bound_at=binding.bound_at,
        textbook=TextbookBrief(
            id=textbook.id,
            subject=textbook.subject,
            grade=textbook.grade,
            version=textbook.version,
            semester=textbook.semester,
        ),
    )


@router.get("", response_model=list[BindingOut])
def list_bindings(
    current: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[BindingOut]:
    _require_student(current)
    return [_binding_out(b, t) for b, t in service.active_bindings(db, current)]


@router.get("/recommend", response_model=RecommendationOut)
def recommend(
    current: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> RecommendationOut:
    _require_student(current)
    grade = current.grade or 1
    semester = current.semester or derive_semester(datetime.utcnow())
    return RecommendationOut(
        grade=grade,
        semester=semester,
        region=current.region or "shenzhen",
        subjects=[
            RecommendedSubject(
                subject=subject,
                textbook_id=textbook.id,
                version=textbook.version,
                grade=textbook.grade,
            )
            for subject, textbook in service.recommended_textbooks(
                db, grade=grade, semester=semester, region=current.region or "shenzhen"
            )
        ],
    )


@router.post("/auto-bind", response_model=AutoBindOut, status_code=status.HTTP_201_CREATED)
def auto_bind(
    current: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> AutoBindOut:
    _require_student(current)
    bindings = service.auto_bind(db, current)
    db.commit()
    out = [_binding_out(b, db.get(Textbook, b.textbook_id)) for b in bindings]
    return AutoBindOut(bound=len(out), bindings=out)


@router.post("/bind", response_model=BindingOut, status_code=status.HTTP_201_CREATED)
def bind(
    payload: BindIn,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BindingOut:
    _require_student(current)
    try:
        binding = service.manual_bind(
            db, current, subject=payload.subject, textbook_id=payload.textbook_id
        )
    except ValueError as exc:
        code = str(exc)
        message = (
            "教材不存在" if code == "TEXTBOOK_NOT_FOUND" else "学科与教材不匹配"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND
            if code == "TEXTBOOK_NOT_FOUND"
            else status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": code, "message": message},
        )
    db.commit()
    textbook = db.get(Textbook, payload.textbook_id)
    return _binding_out(binding, textbook)


@router.delete("/{binding_id}", response_model=BindingOut)
def unbind(
    binding_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BindingOut:
    _require_student(current)
    binding = db.scalar(
        select(TextbookBinding).where(
            TextbookBinding.id == binding_id, TextbookBinding.user_id == current.id
        )
    )
    if binding is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "BINDING_NOT_FOUND", "message": "绑定记录不存在"},
        )
    if binding.status != "archived":
        binding.status = "archived"
        db.commit()
        db.refresh(binding)
    textbook = db.get(Textbook, binding.textbook_id)
    return _binding_out(binding, textbook)
