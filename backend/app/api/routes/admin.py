from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.session import get_db
from app.models.content import Chapter, Question, Textbook
from app.schemas.content import (
    ChapterCreate,
    ChapterOut,
    QuestionCreate,
    QuestionOut,
    TextbookCreate,
    TextbookOut,
)

router = APIRouter(prefix="/admin", tags=["内容管理"], dependencies=[Depends(require_admin)])


@router.get("/textbooks", response_model=List[TextbookOut])
def list_textbooks(db: Session = Depends(get_db)) -> List[Textbook]:
    return list(db.scalars(select(Textbook).order_by(Textbook.id)))


@router.post("/textbooks", response_model=TextbookOut, status_code=status.HTTP_201_CREATED)
def create_textbook(payload: TextbookCreate, db: Session = Depends(get_db)) -> Textbook:
    exists = db.scalar(
        select(Textbook).where(
            Textbook.subject == payload.subject,
            Textbook.grade == payload.grade,
            Textbook.version == payload.version,
            Textbook.semester == payload.semester,
        )
    )
    if exists is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该教材已存在")
    textbook = Textbook(**payload.model_dump())
    db.add(textbook)
    db.commit()
    db.refresh(textbook)
    return textbook


@router.post("/chapters", response_model=ChapterOut, status_code=status.HTTP_201_CREATED)
def create_chapter(payload: ChapterCreate, db: Session = Depends(get_db)) -> Chapter:
    if db.get(Textbook, payload.textbook_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="教材不存在")
    chapter = Chapter(**payload.model_dump())
    db.add(chapter)
    db.commit()
    db.refresh(chapter)
    return chapter


@router.get("/questions", response_model=List[QuestionOut])
def list_questions(
    chapter_id: Optional[int] = None,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> List[Question]:
    stmt = select(Question).order_by(Question.id.desc()).limit(limit)
    if chapter_id:
        stmt = stmt.where(Question.chapter_id == chapter_id)
    return list(db.scalars(stmt))


@router.post("/questions", response_model=QuestionOut, status_code=status.HTTP_201_CREATED)
def create_question(payload: QuestionCreate, db: Session = Depends(get_db)) -> Question:
    if db.get(Chapter, payload.chapter_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="章节不存在")
    question = Question(**payload.model_dump())
    db.add(question)
    db.commit()
    db.refresh(question)
    return question
