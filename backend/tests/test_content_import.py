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


def test_same_name_point_gets_unique_suffix(db):
    data = _document()
    data["knowledge"][1]["name"] = "10以内加减法"
    for question in data["chapters"][0]["questions"]:
        question["knowledge_point"] = "10以内加减法"

    import_document(db, data)

    section = db.scalar(
        select(KnowledgePoint).where(KnowledgePoint.node_type == "section")
    )
    point = db.scalar(
        select(KnowledgePoint).where(KnowledgePoint.node_type == "point")
    )
    assert section.name == "10以内加减法"
    assert point.name == "10以内加减法（要点）"
    assert point.parent_id == section.id
    assert all(
        row.knowledge_point_id == point.id
        for row in db.scalars(select(Question))
    )


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


def test_source_fields_persisted(db):
    data = _document()
    data["knowledge"][0].update(
        {"source_type": "original", "source_name": "教研组自编"}
    )
    data["chapters"][0]["questions"][0].update(
        {
            "source_type": "adapted",
            "source_name": "人教版八年级上册",
            "source_ref": "P35 第2题",
            "copyright_owner": "人民教育出版社",
            "adapted_from": "P35 第2题",
        }
    )
    import_document(db, data)
    question = db.scalar(select(Question).where(Question.q_type == "choice"))
    assert question.source_type == "adapted"
    assert question.source_name == "人教版八年级上册"
    assert question.source_ref == "P35 第2题"
    assert question.copyright_owner == "人民教育出版社"
    assert question.adapted_from == "P35 第2题"
    point = db.scalar(select(KnowledgePoint).where(KnowledgePoint.node_type == "section"))
    assert point.source_type == "original"
    assert point.source_name == "教研组自编"


def test_licensed_requires_license_note():
    data = _document()
    data["chapters"][0]["questions"][0].update(
        {"source_type": "licensed", "source_name": "某题库授权"}
    )
    try:
        validate_document(data)
    except ValueError as exc:
        assert "license_note" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("已授权内容必须填写 license_note")


def test_adapted_requires_adapted_from():
    data = _document()
    data["chapters"][0]["questions"][0].update(
        {"source_type": "adapted", "source_name": "人教版八年级上册"}
    )
    try:
        validate_document(data)
    except ValueError as exc:
        assert "adapted_from" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("改编题必须填写 adapted_from")


def test_external_question_must_be_draft():
    data = _document()
    data["chapters"][0]["questions"][0].update(
        {"source_type": "external", "source_name": "外部题库"}
    )
    try:
        validate_document(data)
    except ValueError as exc:
        assert "draft" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("外部导入题目必须先进入待审核状态")
