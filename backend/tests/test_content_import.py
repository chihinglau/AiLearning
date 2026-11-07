from sqlalchemy import select

from app.models.content import Chapter, KnowledgePoint, Question, Textbook
from app.services.content_import import import_document, validate_document


def _document():
    return {
        "subject": "math",
        "grade": 1,
        "version": "北师大版",
        "semester": "first",
        "knowledge": [
            {"node_type": "section", "name": "10以内加减法"},
            {
                "node_type": "point",
                "name": "10以内加法",
                "parent": "10以内加减法",
                "explanation": "理解加法的含义。",
            },
        ],
        "chapters": [
            {
                "name": "加与减（一）",
                "order_index": 3,
                "questions": [
                    {
                        "q_type": "choice",
                        "stem": "3 + 4 = ?",
                        "options": ["5", "6", "7", "8"],
                        "answer": {"value": "C"},
                        "analysis": "3 加 4 得 7。",
                        "knowledge_point": "10以内加法",
                    },
                    {
                        "q_type": "fill",
                        "stem": "5 + 2 = （  ）",
                        "answer": {"value": ["7", "七"]},
                        "knowledge_point": "10以内加法",
                    },
                ],
            }
        ],
    }


def test_import_is_idempotent(db):
    first = import_document(db, _document())
    assert first == {
        "textbook_created": 1,
        "chapters_created": 1,
        "chapters_updated": 0,
        "knowledge_created": 2,
        "knowledge_updated": 0,
        "questions_created": 2,
        "questions_skipped": 0,
    }
    textbook = db.scalar(select(Textbook))
    assert textbook.version == "北师大版"
    assert db.scalar(select(Chapter).where(Chapter.textbook_id == textbook.id)).name == "加与减（一）"
    point = db.scalar(
        select(KnowledgePoint).where(KnowledgePoint.name == "10以内加法")
    )
    assert point.node_type == "point"
    questions = list(db.scalars(select(Question)))
    assert len(questions) == 2
    assert {row.q_type for row in questions} == {"choice", "fill"}
    assert all(row.subject == "math" for row in questions)

    second = import_document(db, _document())
    assert second["questions_created"] == 0
    assert second["questions_skipped"] == 2
    assert second["chapters_created"] == 0
    assert second["knowledge_created"] == 0
    assert len(list(db.scalars(select(Question)))) == 2


def test_invalid_answer_key_rejected(db):
    data = _document()
    data["chapters"][0]["questions"][0]["answer"] = {"value": "Z"}
    try:
        import_document(db, data)
    except ValueError as exc:
        assert "不在选项" in str(exc)
    else:  # pragma: no cover - 断言失败时给出明确信息
        raise AssertionError("非法选项键应被拒绝")
    assert db.scalar(select(Textbook)) is None


def test_multiple_requires_list_answer():
    data = _document()
    data["chapters"][0]["questions"][0]["q_type"] = "multiple"
    try:
        validate_document(data)
    except ValueError as exc:
        assert "必须是列表" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("多选题答案必须是列表")
