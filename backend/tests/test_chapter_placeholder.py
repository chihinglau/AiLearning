"""占位章节清理立项 · 阶段 3 回归测试。

覆盖三件事：
1. 导入层别名：旧样章名重定向到教材真实章节（不再重建占位章）；
2. R-C 旧样章名：导入时建成占位章（is_placeholder=1、序沉底），重导不被覆盖；
3. app 端：占位章不出现在教材目录视图（/api/chapters）。
"""

from sqlalchemy import select

from app.models.content import Chapter, KnowledgePoint, Question, Textbook
from app.services.content_import import import_document


def _doc(chapter_name: str, order_index: int = 1):
    """章节名与知识点板块名同名（与线上 11-07 旧样章的实际结构一致）。"""
    return {
        "subject": "math",
        "grade": 1,
        "version": "北师大版",
        "semester": "first",
        "knowledge": [
            {"node_type": "section", "name": chapter_name},
            {
                "node_type": "point",
                "name": chapter_name + "（要点）",
                "parent": chapter_name,
            },
        ],
        "chapters": [
            {
                "name": chapter_name,
                "order_index": order_index,
                "questions": [
                    {
                        "q_type": "choice",
                        "stem": f"{chapter_name} 的题目",
                        "options": ["A", "B"],
                        "answer": {"value": "A"},
                        "analysis": "解析",
                        "knowledge_point": chapter_name + "（要点）",
                    }
                ],
            }
        ],
    }


def test_legacy_chapter_name_redirects_to_canonical(db):
    """R-B 旧样章名 → 教材真实章节名，导入后库里只有真实章节。"""
    import_document(db, _doc("加与减（一）", order_index=3))

    names = [row.name for row in db.scalars(select(Chapter))]
    assert names == ["第四单元 10以内数加与减"]
    chapter = db.scalar(select(Chapter))
    assert chapter.is_placeholder == 0
    assert chapter.placeholder_note is None
    # 题目挂到重定向后的章节上
    assert all(q.chapter_id == chapter.id for q in db.scalars(select(Question)))


def test_r_c_chapter_name_is_discarded(db):
    """R-C 旧版数据章名 → 整章丢弃：不建章、不挂题、不建知识点。"""
    report = import_document(db, _doc("比较与位置", order_index=2))

    assert report["chapters_created"] == 0
    assert report["chapters_discarded"] == 1
    assert report["questions_discarded"] == 1
    assert report["questions_created"] == 0
    assert list(db.scalars(select(Chapter))) == []
    assert list(db.scalars(select(Question))) == []
    # 对应的知识点也不应被重建
    assert list(db.scalars(select(KnowledgePoint))) == []


def test_discarded_chapter_stays_discarded_on_reimport(db):
    """重导旧 JSON 时，旧版数据章依旧被丢弃，不会复活。"""
    import_document(db, _doc("比较与位置", order_index=2))
    report = import_document(db, _doc("比较与位置", order_index=2))

    assert report["chapters_created"] == 0
    assert report["chapters_discarded"] == 1
    assert report["questions_created"] == 0
    assert list(db.scalars(select(Chapter))) == []
    assert list(db.scalars(select(Question))) == []


def test_canonical_order_not_reset_by_legacy_import(db):
    """旧 JSON 重定向到教材真实章节时，不能用旧 JSON 的序号覆盖教材目录序。"""
    import_document(db, _doc("第四单元 10以内数加与减", order_index=4))
    canonical = db.scalar(select(Chapter))
    assert canonical.order_index == 4

    import_document(db, _doc("加与减（一）", order_index=3))

    db.refresh(canonical)
    assert canonical.order_index == 4
    assert canonical.is_placeholder == 0


def test_placeholder_hidden_from_public_chapters(client, db):
    """app 端教材目录视图不返回占位章。"""
    textbook = Textbook(subject="math", grade=1, version="北师大版", semester="first")
    db.add(textbook)
    db.flush()
    db.add(Chapter(textbook_id=textbook.id, grade=1, name="第一单元 生活中的数", order_index=1))
    db.add(
        Chapter(
            textbook_id=textbook.id,
            grade=1,
            name="比较与位置",
            order_index=2,
            is_placeholder=1,
            placeholder_note="R-C 保留",
        )
    )
    db.commit()

    response = client.get("/api/public/chapters", params={"textbook_id": textbook.id})
    assert response.status_code == 200, response.text
    names = [item["name"] for item in response.json()]
    assert names == ["第一单元 生活中的数"]
