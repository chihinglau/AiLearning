"""PG-05：双向细目表、答题卡、跨卷重题去重、抽检 10% 抽样。"""

from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.content import Chapter, KnowledgePoint, Question, Textbook
from app.models.exam import Exam, ExamBlueprint
from app.models.user import User
from app.services.exam_paper import generate_paper
from app.services.exam_paper_docs import (
    build_spec_table,
    recent_question_ids,
    render_answer_sheet_html,
    sample_exams,
)


def _seed(db: Session) -> tuple[User, ExamBlueprint, list[int]]:
    user = User(phone="13900000009", password_hash="x", grade=3, role="student")
    book = Textbook(subject="math", grade=3, version="北师大版", semester="first")
    db.add_all([user, book])
    db.flush()

    chapter = Chapter(textbook_id=book.id, grade=3, name="第一单元", order_index=1)
    db.add(chapter)
    db.flush()
    kps = []
    for index in range(6):
        kp = KnowledgePoint(
            subject="math", name=f"知识点{index + 1}", grade=3,
            node_type="point", order_index=index + 1,
        )
        db.add(kp)
        kps.append(kp)
    db.flush()
    for q_type, count in (("choice", 12), ("fill", 10), ("answer", 6)):
        for index in range(count):
            db.add(
                Question(
                    chapter_id=chapter.id,
                    knowledge_point_id=kps[index % len(kps)].id,
                    subject="math",
                    q_type=q_type,
                    difficulty=1 if index < count / 2 else 2,
                    content={"stem": f"{q_type}-{index}"},
                    answer={"value": "A"},
                )
            )
    blueprint = ExamBlueprint(
        code="test_docs_unit", name="三年级数学单元测", subject="math", grade=3,
        exam_type="unit", total_score=60, time_limit_min=40,
        sections=[
            {"name": "一、选择题", "q_type": "choice", "count": 4,
             "score_each": 4, "band": "easy"},
            {"name": "二、填空题", "q_type": "fill", "count": 5,
             "score_each": 4, "band": "medium"},
            {"name": "三、解答题", "q_type": "answer", "count": 3,
             "score_each": 8, "band": "hard"},
        ],
        kp_coverage_min=0.8,
    )
    db.add(blueprint)
    db.commit()
    return user, blueprint, [chapter.id]


def test_spec_table_matches_blueprint_and_exam(db: Session) -> None:
    user, blueprint, chapter_ids = _seed(db)
    paper = generate_paper(db, user=user, blueprint=blueprint, chapter_ids=chapter_ids, seed=7)
    exam = Exam(
        title="三年级数学单元卷", subject="math", grade=3, source="generated",
        total_score=int(paper.total_score), time_limit_min=40,
        questions=[
            {"question_id": item.question.id, "score": item.score,
             "section_index": item.section_index, "section_name": item.section_name}
            for item in paper.items
        ],
        blueprint_id=blueprint.id, exam_type="unit", chapter_ids=chapter_ids,
    )
    db.add(exam)
    db.commit()

    spec = build_spec_table(db, exam, blueprint)
    assert spec["score_matches"] is True
    assert spec["actual_score_total"] == 60
    assert spec["question_count"] == 12
    assert [row["planned_count"] for row in spec["sections"]] == [4, 5, 3]
    assert [row["actual_count"] for row in spec["sections"]] == [4, 5, 3]
    assert [row["band"] for row in spec["sections"]] == ["easy", "medium", "hard"]
    assert all(row["knowledge_points"] for row in spec["sections"])
    assert all(row["chapters"] == ["第一单元"] for row in spec["sections"])


def test_answer_sheet_has_no_stem_or_answer(db: Session) -> None:
    user, blueprint, chapter_ids = _seed(db)
    paper = generate_paper(db, user=user, blueprint=blueprint, chapter_ids=chapter_ids, seed=8)
    exam = Exam(
        title="三年级数学单元卷", subject="math", grade=3, source="generated",
        total_score=60, time_limit_min=40,
        questions=[
            {"question_id": item.question.id, "score": item.score,
             "section_index": item.section_index, "section_name": item.section_name}
            for item in paper.items
        ],
        blueprint_id=blueprint.id, exam_type="unit", chapter_ids=chapter_ids,
    )
    db.add(exam)
    db.commit()

    html = render_answer_sheet_html(db, exam)
    assert "答题卡" in html
    assert "一、选择题" in html and "三、解答题" in html
    assert "60" in html
    # 不含题干与答案
    assert "choice-" not in html
    assert ">A<" not in html


def test_recent_question_ids_returns_previous_paper_items(db: Session) -> None:
    user, blueprint, chapter_ids = _seed(db)
    first = generate_paper(db, user=user, blueprint=blueprint, chapter_ids=chapter_ids, seed=1)
    exam = Exam(
        title="卷1", subject="math", grade=3, source="generated", total_score=60,
        time_limit_min=40,
        questions=[
            {"question_id": item.question.id, "score": item.score,
             "section_index": item.section_index}
            for item in first.items
        ],
        blueprint_id=blueprint.id, exam_type="unit", chapter_ids=chapter_ids,
    )
    db.add(exam)
    db.commit()

    ids = recent_question_ids(db, subject="math", grade=3, exam_type="unit")
    assert set(ids) == {item.question.id for item in first.items}
    assert recent_question_ids(
        db, subject="math", grade=3, exam_type="unit", before_exam_id=exam.id
    ) == []


def test_sample_exams_is_deterministic_and_proportional() -> None:
    rows = [Exam(id=index, title=f"卷{index}") for index in range(1, 21)]
    first = sample_exams(rows, 0.1, seed=20261116)
    second = sample_exams(rows, 0.1, seed=20261116)
    assert [exam.id for exam in first] == [exam.id for exam in second]
    assert len(first) == 2  # 20 × 10%
    assert sample_exams(rows, 0.1, seed=99) != [] 


def test_sampling_api_and_sample_review(
    client: TestClient, db: Session, admin_headers: dict[str, str]
) -> None:
    for index in range(5):
        db.add(
            Exam(
                title=f"自建卷{index}", subject="math", grade=3, source="generated",
                total_score=60, time_limit_min=40, questions=[], exam_type="unit",
                status="published",
            )
        )
    db.commit()

    response = client.get(
        "/api/exams/review-sampling",
        headers=admin_headers,
        params={"ratio": 0.1, "seed": 42, "only_unreviewed": True},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total_candidates"] == 5
    assert body["sampled_count"] == 1  # 向上取整到至少 1 张

    target = body["items"][0]["exam_id"]
    reviewed = client.post(
        f"/api/exams/{target}/sample-review",
        headers=admin_headers,
        json={"passed": False, "note": "第 3 题分值标注与蓝图不一致"},
    )
    assert reviewed.status_code == 200, reviewed.text
    data = reviewed.json()
    assert data["status"] == "draft"
    assert data["review_note"].startswith("[抽检退回]")
    assert data["action"] == "sample_review"

    exam = db.get(Exam, target)
    assert exam is not None and exam.reviewed_at is not None
    assert exam.status == "draft"


def test_generate_excludes_recent_paper_questions(
    client: TestClient, db: Session, admin_headers: dict[str, str]
) -> None:
    user, blueprint, chapter_ids = _seed(db)
    db.add(user)
    db.commit()

    payload = {
        "blueprint_code": blueprint.code,
        "chapter_ids": chapter_ids,
        "seed": 31,
    }
    first = client.post("/api/exams/generate", headers=admin_headers, json=payload)
    assert first.status_code == 200, first.text
    second = client.post("/api/exams/generate", headers=admin_headers, json=payload)
    assert second.status_code == 200, second.text
    body = second.json()
    assert body["excluded_recent_count"] > 0

    first_exam = db.get(Exam, first.json()["exam_id"])
    second_exam = db.get(Exam, second.json()["exam_id"])
    first_ids = {item["question_id"] for item in first_exam.questions}
    second_ids = {item["question_id"] for item in second_exam.questions}
    overlap = first_ids & second_ids
    # 题库足够（28 题池 vs 12 题需求）时应当零重叠
    assert not overlap
