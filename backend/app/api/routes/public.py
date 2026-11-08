from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.content import Chapter, KnowledgePoint, Textbook
from app.schemas.content import ChapterOut, KnowledgePointOut, TextbookOut

router = APIRouter(prefix="/public", tags=["公开内容"])


@router.get("/textbooks", response_model=List[TextbookOut])
def list_textbooks(
    subject: Optional[str] = None,
    grade: Optional[int] = Query(default=None, ge=1, le=12),
    db: Session = Depends(get_db),
) -> List[Textbook]:
    stmt = select(Textbook).where(Textbook.is_active.is_(True))
    if subject:
        stmt = stmt.where(Textbook.subject == subject)
    if grade:
        stmt = stmt.where(Textbook.grade == grade)
    return list(db.scalars(stmt.order_by(Textbook.grade, Textbook.subject)))


@router.get("/chapters", response_model=List[ChapterOut])
def list_chapters(
    textbook_id: int, db: Session = Depends(get_db)
) -> List[Chapter]:
    # 占位章节（历史占位/旧样章）不对外暴露：教材目录只出现教材真实章节
    stmt = select(Chapter).where(
        Chapter.textbook_id == textbook_id,
        Chapter.is_placeholder == 0,
    )
    return list(db.scalars(stmt.order_by(Chapter.order_index, Chapter.id)))


@router.get("/knowledge-points", response_model=List[KnowledgePointOut])
def list_knowledge_points(
    subject: Optional[str] = None,
    grade: Optional[int] = Query(default=None, ge=1, le=12),
    db: Session = Depends(get_db),
) -> List[KnowledgePoint]:
    stmt = select(KnowledgePoint)
    if subject:
        stmt = stmt.where(KnowledgePoint.subject == subject)
    if grade:
        stmt = stmt.where(KnowledgePoint.grade == grade)
    return list(db.scalars(stmt.order_by(KnowledgePoint.id)))
