"""自适应学习闭环：引擎单测 + API 集成测试。"""

from datetime import datetime, timedelta

from app.models.content import Chapter, KnowledgePoint, Question, Textbook
from app.models.practice import MasteryScore
from app.services import learning as engine


# ---------------------------------------------------------------------------
# 引擎纯函数单测
# ---------------------------------------------------------------------------


def _mk_question(qid: int, difficulty: int = 2, q_type: str = "choice") -> Question:
    q = Question(
        id=qid,
        chapter_id=1,
        knowledge_point_id=1,
        subject="math",
        q_type=q_type,
        content={"stem": "?"},
        options=[{"key": "A", "text": "x"}, {"key": "B", "text": "y"}],
        answer={"value": "A"},
        difficulty=difficulty,
    )
    return q


def test_grade_normalizes_fill_answers():
    q = _mk_question(1, q_type="fill")
    q.answer = {"value": ["3.5", "3.50"]}
    assert engine.grade_answer(q, {"value": " 3.5 "}) is True
    assert engine.grade_answer(q, {"value": "3.50"}) is True
    assert engine.grade_answer(q, {"value": "3.6"}) is False
    # 全角空格/标点容错
    q.answer = {"value": "CO2"}
    assert engine.grade_answer(q, {"value": " co2 "}) is True
    assert engine.grade_answer(q, {"value": "CO₃"}) is False


def test_mastery_ema_bands(db):
    # 首次答对 → 60 分（growing）；再答对 → 84（skilled）；第三次 → 93.6（mastered）
    engine.update_mastery(db, user_id=1, knowledge_point_id=10, is_correct=True)
    m = db.query(MasteryScore).filter_by(user_id=1, knowledge_point_id=10).one()
    assert m.score == 60.0
    assert engine.mastery_band(m.score) == "growing"

    engine.update_mastery(db, user_id=1, knowledge_point_id=10, is_correct=True)
    db.refresh(m)
    assert round(m.score, 1) == 84.0

    engine.update_mastery(db, user_id=1, knowledge_point_id=10, is_correct=True)
    db.refresh(m)
    assert round(m.score, 1) == 93.6
    assert engine.mastery_band(m.score) == "mastered"

    # 答错回落到 37.44 → weak
    engine.update_mastery(db, user_id=1, knowledge_point_id=10, is_correct=False)
    db.refresh(m)
    assert round(m.score, 2) == 37.44
    assert engine.mastery_band(m.score) == "weak"


def test_difficulty_mix_matches_mastery():
    weak = engine.pick_difficulties(20, 10)
    assert max(weak) <= 3
    assert weak.count(1) + weak.count(2) >= 6
    master = engine.pick_difficulties(95, 10)
    assert min(master) >= 4


def test_choose_questions_prioritizes_reviews():
    pool = [_mk_question(i, difficulty=1) for i in range(1, 11)]
    review_ids = [9, 10]
    chosen = engine.choose_questions(pool, [1] * 5, review_ids=review_ids, review_quota=2)
    assert chosen[0].id == 9 and chosen[1].id == 10
    assert len(chosen) == 7  # 2 复习 + 5 新题


def test_sm2_lifecycle(db):
    q = _mk_question(100, difficulty=4)
    q.id = 100
    db.add_all([q])
    db.commit()

    # 第一次答错：进错题本，1 天后到期
    item = engine.upsert_wrong_question(db, user_id=1, question=q, is_correct=False)
    db.commit()
    assert item.wrong_count == 1
    assert item.status == "active"
    assert item.interval_days == 1
    due_first = item.next_review_at
    assert due_first is not None

    # 复习答对两次：1 天 → 3 天，未消灭（streak=2）
    engine.upsert_wrong_question(db, user_id=1, question=q, is_correct=True)
    db.commit()
    db.refresh(item)
    assert item.correct_streak == 1 and item.interval_days == 1
    engine.upsert_wrong_question(db, user_id=1, question=q, is_correct=True)
    db.commit()
    db.refresh(item)
    assert item.correct_streak == 2 and item.interval_days == 3 and item.status == "active"

    # 第三次答对且难度≥3 → mastered
    engine.upsert_wrong_question(db, user_id=1, question=q, is_correct=True)
    db.commit()
    db.refresh(item)
    assert item.status == "mastered"
    assert item.next_review_at is None

    # 再次答错 → 复活，间隔重置 1 天，ease 下探
    old_ease = item.ease_factor
    engine.upsert_wrong_question(db, user_id=1, question=q, is_correct=False)
    db.commit()
    db.refresh(item)
    assert item.status == "active"
    assert item.interval_days == 1
    assert item.ease_factor < old_ease


def test_due_review_listing(db):
    q = _mk_question(200, difficulty=2)
    q.id = 200
    db.add(q)
    db.commit()
    engine.upsert_wrong_question(db, user_id=7, question=q, is_correct=False)
    db.commit()
    now = datetime.utcnow()

    # 未到期
    assert engine.due_review_question_ids(db, user_id=7, now=now) == []
    # 2 天后到期
    assert engine.due_review_question_ids(db, user_id=7, now=now + timedelta(days=2)) == [200]
    assert engine.due_review_question_ids(db, user_id=8, now=now + timedelta(days=2)) == []


# ---------------------------------------------------------------------------
# API 集成测试
# ---------------------------------------------------------------------------


def _seed_kp_question(db_session, *, kp_name="20以内加减法", difficulty=2, answer="A",
                      q_type="choice", tags=None):
    tb = Textbook(subject="math", grade=1, version="北师大版", semester="first")
    db_session.add(tb)
    db_session.flush()
    ch = Chapter(textbook_id=tb.id, grade=1, name="加与减", order_index=1)
    db_session.add(ch)
    db_session.flush()
    kp = KnowledgePoint(subject="math", grade=1, name=kp_name, explanation="20以内进退位")
    db_session.add(kp)
    db_session.flush()
    q = Question(
        chapter_id=ch.id,
        knowledge_point_id=kp.id,
        subject="math",
        q_type=q_type,
        content={"stem": "8 + 5 = ?"},
        options=[
            {"key": "A", "text": "13"},
            {"key": "B", "text": "12"},
            {"key": "C", "text": "14"},
        ],
        answer={"value": answer},
        analysis="凑十法：8+5=13。",
        difficulty=difficulty,
        tags=tags or [kp_name],
    )
    db_session.add(q)
    db_session.commit()
    return tb.id, ch.id, kp.id, q.id


def test_submit_wrong_then_right_full_flow(client, student_headers):
    from tests.conftest import TestingSessionLocal
    db = TestingSessionLocal()
    tb_id, ch_id, kp_id, q_id = _seed_kp_question(db)
    db.close()

    # 组卷
    resp = client.post(
        "/api/learn/start",
        headers=student_headers,
        json={"knowledge_point_id": kp_id, "count": 5},
    )
    assert resp.status_code == 200
    questions = resp.json()["questions"]
    assert len(questions) == 1  # 只有一道题
    assert "answer" not in questions[0]  # 学生端不带答案

    # 答错
    resp = client.post(
        "/api/learn/submit",
        headers=student_headers,
        json={"question_id": q_id, "user_answer": {"value": "B"}, "duration_ms": 3000},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_correct"] is False
    assert body["correct_answer"]["value"] == "A"
    assert body["mastery_score"] == 0.0
    assert body["in_wrong_book"] is True

    # 错题本出现
    resp = client.get("/api/learn/wrong-questions", headers=student_headers)
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    wrong_id = items[0]["id"]
    assert items[0]["stem"] == "8 + 5 = ?"

    # 标注错因
    resp = client.post(
        f"/api/learn/wrong-questions/{wrong_id}/reason",
        headers=student_headers,
        json={"wrong_reason": "calculation"},
    )
    assert resp.status_code == 200
    assert resp.json()["wrong_reason"] == "calculation"

    # 答对：掌握度上升，错题进入复习推进（仍 active，streak=1）
    resp = client.post(
        "/api/learn/submit",
        headers=student_headers,
        json={"question_id": q_id, "user_answer": {"value": "A"}, "duration_ms": 2000},
    )
    assert resp.json()["is_correct"] is True
    assert resp.json()["mastery_score"] == 60.0

    # 知识树挂掌握度
    resp = client.get(
        f"/api/learn/knowledge-tree?textbook_id={tb_id}", headers=student_headers
    )
    tree = resp.json()
    kps = [kp for ch in tree for kp in ch["knowledge_points"]]
    assert kps[0]["mastery_score"] == 60.0
    assert kps[0]["mastery_band"] == "growing"
    assert kps[0]["question_count"] == 1


def test_review_today_and_stats(client, student_headers):
    from tests.conftest import TestingSessionLocal
    db = TestingSessionLocal()
    _, _, _, q_id = _seed_kp_question(db)
    db.close()

    # 学情初始
    resp = client.get("/api/learn/stats", headers=student_headers)
    assert resp.json()["total_answered"] == 0
    assert resp.json()["accuracy"] == 0.0

    # 答错一道 → 明天到期，今天无复习题；统计 1 答 0 对 + 1 待消灭
    client.post(
        "/api/learn/submit",
        headers=student_headers,
        json={"question_id": q_id, "user_answer": {"value": "C"}, "duration_ms": 1000},
    )
    resp = client.get("/api/learn/review/today", headers=student_headers)
    assert resp.json()["questions"] == []
    stats = client.get("/api/learn/stats", headers=student_headers).json()
    assert stats["total_answered"] == 1
    assert stats["total_correct"] == 0
    assert stats["active_wrong_count"] == 1
    assert len(stats["weak_points"]) == 1


def test_start_404_on_empty_scope(client, student_headers):
    resp = client.post(
        "/api/learn/start",
        headers=student_headers,
        json={"subject": "physics", "count": 5},
    )
    assert resp.status_code == 404


def test_submit_requires_auth(client):
    resp = client.post(
        "/api/learn/submit",
        json={"question_id": 1, "user_answer": {"value": "A"}, "duration_ms": 0},
    )
    assert resp.status_code == 401
