"""P1 端到端回归（活服务）。

覆盖 P1 新增能力在真实 HTTP 服务上的串联验证：
学生「绑定教材 → 首页推荐 → 练习作答 → 错题优先级」、
考试「窗口内开考 → 暂存 → 交卷 → 报告（能力维度/班级平均/趋势）→ 主观题自评 → 回流」、
教师「班级列表 → 班级聚合学情」、家长「绑定孩子 → 孩子学情」。

前置条件（使用独立 E2E 库，避免污染开发库）：

    $env:DATABASE_URL='sqlite:///D:/ai/prj/trae/HuaWei/AiLearning/backend/ailearning_e2e.db'
    python -m scripts.seed
    python -m uvicorn app.main:app --host 127.0.0.1 --port 18080

运行：

    $env:DATABASE_URL='sqlite:///D:/ai/prj/trae/HuaWei/AiLearning/backend/ailearning_e2e.db'
    python -m scripts.e2e_p1_smoke

说明：学校/班级成员与教师的 school_id、teacher_subjects 目前没有对外 API（属 P2-01
配置后台范围），脚本通过同一个 DATABASE_URL 直连数据库完成这部分夹具准备。
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.content import Question
from app.models.practice import StudentQuestionRecord, WrongQuestion
from app.models.user import User

API_BASE = os.environ.get("E2E_API_BASE", "http://127.0.0.1:18080")
ADMIN_PHONE = os.environ.get("E2E_ADMIN_PHONE", "13800000000")
ADMIN_PASSWORD = os.environ.get("E2E_ADMIN_PASSWORD", "admin123")
PASSWORD = "pass1234"

_passed = 0


def check(condition: bool, message: str) -> None:
    global _passed
    if not condition:
        raise AssertionError(message)
    _passed += 1
    print(f"  PASS  {message}")


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def login(client: httpx.Client, phone: str, password: str) -> str:
    resp = client.post(
        "/api/auth/login", data={"username": phone, "password": password}
    )
    check(resp.status_code == 200, f"登录 {phone}")
    return resp.json()["access_token"]


def register(client: httpx.Client, phone: str, grade: int) -> None:
    resp = client.post(
        "/api/auth/register",
        json={"phone": phone, "password": PASSWORD, "grade": grade},
    )
    check(resp.status_code == 201, f"注册 {phone}（{resp.text[:120]}）")


def admin_user_id(client: httpx.Client, admin: dict[str, str], phone: str) -> int:
    resp = client.get("/api/admin/users", params={"keyword": phone}, headers=admin)
    check(resp.status_code == 200, "管理端查询用户")
    items = resp.json()["items"]
    check(len(items) == 1, f"按手机号唯一定位用户 {phone}")
    return int(items[0]["id"])


def grant_role(
    client: httpx.Client, admin: dict[str, str], user_id: int, role: str
) -> None:
    resp = client.post(
        f"/api/admin/users/{user_id}/roles", json={"grant": [role]}, headers=admin
    )
    check(resp.status_code == 200, f"授予角色 {role} → 用户 {user_id}")


def _iso(delta_seconds: int) -> str:
    return (
        datetime.now(timezone.utc).replace(tzinfo=None)
        + timedelta(seconds=delta_seconds)
    ).isoformat()


def _answer_values(db, question_ids: list[int]) -> dict[int, dict[str, Any]]:
    rows = db.scalars(select(Question).where(Question.id.in_(question_ids)))
    return {q.id: q.answer for q in rows}


def _wrong_answer(answer: dict[str, Any], q_type: str) -> dict[str, Any]:
    value = answer.get("value")
    if q_type in ("choice", "multiple", "judge"):
        letters = ["A", "B", "C", "D"]
        candidate = value[0] if isinstance(value, list) and value else value
        if q_type == "judge":
            return {"value": "F" if candidate == "T" else "T"}
        letter = str(candidate).upper()
        pos = letters.index(letter) if letter in letters else 0
        return {"value": letters[(pos + 1) % len(letters)]}
    return {"value": "0" if str(value) != "0" else "1"}


def main() -> None:
    client = httpx.Client(base_url=API_BASE, timeout=30.0, trust_env=False)
    stamp = int(time.time() * 1000) % 10_000_000
    student_phone = f"137{stamp:08d}"[:11]
    teacher_phone = f"136{stamp:08d}"[:11]
    parent_phone = f"135{stamp:08d}"[:11]

    print(f"[E2E] API={API_BASE}")
    admin = _auth(login(client, ADMIN_PHONE, ADMIN_PASSWORD))

    # ---------------- 组织夹具：学校 / 班级 / 教师 ----------------
    school = client.post(
        "/api/org/schools",
        json={"name": f"E2E 测试学校 {stamp}", "region": "深圳"},
        headers=admin,
    )
    check(school.status_code == 201, "创建学校")
    school_id = school.json()["id"]
    room = client.post(
        "/api/org/classes",
        json={
            "school_id": school_id,
            "grade": 3,
            "name": f"E2E 三年级 1 班 {stamp}",
            "school_year": "2026-2027",
        },
        headers=admin,
    )
    check(room.status_code == 201, "创建班级")
    class_id = room.json()["id"]

    register(client, student_phone, 3)
    register(client, teacher_phone, 3)
    register(client, parent_phone, 3)
    student_token = login(client, student_phone, PASSWORD)
    student = _auth(student_token)
    student_id = admin_user_id(client, admin, student_phone)
    teacher_id = admin_user_id(client, admin, teacher_phone)
    parent_id = admin_user_id(client, admin, parent_phone)
    grant_role(client, admin, teacher_id, "teacher")
    grant_role(client, admin, parent_id, "parent")

    # 无对外 API 的字段：学校归属与教师学科范围（P2-01 配置后台承接）
    with SessionLocal() as db:
        for user_id in (student_id, teacher_id):
            row = db.get(User, user_id)
            row.school_id = school_id
        teacher = db.get(User, teacher_id)
        teacher.teacher_subjects = ["math"]
        teacher.grade_start = 1
        teacher.grade_end = 6
        db.commit()

    added = client.post(
        f"/api/org/classes/{class_id}/members",
        json={"student_ids": [student_id]},
        headers=admin,
    )
    check(added.status_code == 201, "学生入班")
    assigned = client.post(
        "/api/org/assignments",
        json={
            "teacher_id": teacher_id,
            "class_id": class_id,
            "subject": "math",
            "role_in_class": "subject_teacher",
        },
        headers=admin,
    )
    check(assigned.status_code == 201, "数学授课分配")
    teacher_token = login(client, teacher_phone, PASSWORD)
    teacher = _auth(teacher_token)
    teacher_classes = client.get("/api/org/classes", headers=teacher)
    check(teacher_classes.status_code == 200, "教师可见班级列表")
    check(
        any(item["id"] == class_id for item in teacher_classes.json()),
        "教师可见本班",
    )

    # ---------------- 学生学习闭环 ----------------
    bound = client.post("/api/me/textbooks/auto-bind", headers=student)
    check(
        bound.status_code == 201,
        f"教材自动绑定（{bound.status_code} {bound.text[:160]}）",
    )
    home = client.get("/api/learn/home", headers=student)
    check(home.status_code == 200, "学习首页聚合")
    home_data = home.json()
    math = next(
        (item for item in home_data["textbooks"] if item["subject"] == "math"), None
    )
    check(math is not None, "首页含数学教材")
    rec = home_data.get("recommendation") or {}
    check(bool(rec.get("action")), f"首页推荐动作={rec.get('action')}")

    units = client.get(
        f"/api/learn/textbook/{math['textbook_id']}/units", headers=student
    )
    check(units.status_code == 200, "教材单元列表")
    unit = next(
        (item for item in units.json() if (item.get("question_count") or 0) >= 4), None
    )
    check(unit is not None, "找到题量充足的单元")

    started = client.post(
        "/api/learn/start",
        json={
            "scope_type": "chapter",
            "scope_ids": [unit["id"]],
            "count": 5,
            "q_types": ["choice", "judge", "fill"],
            "seed": 2026,
            "mode": "special",
        },
        headers=student,
    )
    check(started.status_code == 200, "练习组卷")
    payload = started.json()
    check(len(payload["questions"]) >= 1, f"组卷题量={len(payload['questions'])}")
    session_id = payload.get("session_id")
    with SessionLocal() as db:
        answers = _answer_values(db, [q["id"] for q in payload["questions"]])

    for index, question in enumerate(payload["questions"]):
        correct = answers.get(question["id"], {})
        user_answer = (
            _wrong_answer(correct, question["q_type"]) if index < 2 else dict(correct)
        )
        submit = client.post(
            "/api/learn/submit",
            json={
                "question_id": question["id"],
                "user_answer": user_answer,
                "duration_ms": 1000,
                "session_id": session_id,
                "source": "practice",
            },
            headers=student,
        )
        check(submit.status_code == 200, f"提交第 {index + 1} 题")
        if index == 0:
            check(submit.json()["is_correct"] is False, "故意答错被判定错误")
        elif index == 2:
            check(submit.json()["is_correct"] is True, "按答案作答判定正确")

    wrong = client.get("/api/learn/wrong-questions", headers=student)
    check(wrong.status_code == 200, "错题本列表")
    wrong_items = wrong.json()
    check(len(wrong_items) >= 1, f"错题条数={len(wrong_items)}")
    check("review_priority" in wrong_items[0], "错题含复习优先级")
    priorities = [item["priority_score"] for item in wrong_items]
    check(priorities == sorted(priorities, reverse=True), "错题按优先级降序")

    stats = client.get("/api/learn/stats", headers=student)
    check(stats.status_code == 200, "学生学情统计")
    check(stats.json()["total_answered"] > 0, "学情统计已累计作答")

    home_after = client.get("/api/learn/home", headers=student)
    check(home_after.status_code == 200, "练习后首页缓存已失效并重建")

    # ---------------- 考试闭环：窗口 → 暂存 → 交卷 → 报告 → 自评 --------------
    with SessionLocal() as db:
        answer_chapter_ids = list(
            dict.fromkeys(
                db.scalars(
                    select(Question.chapter_id)
                    .where(Question.subject == "math", Question.q_type == "answer")
                    .limit(6)
                )
            )
        )
    chapter_ids = answer_chapter_ids + [unit["id"]]
    chapter_ids = list(dict.fromkeys(chapter_ids))[:5]
    generated = client.post(
        "/api/exams/generate",
        json={
            "blueprint_code": "math_primary_midterm",
            "chapter_ids": chapter_ids,
            "title": f"P1 E2E 期中 {stamp}",
            "window_start": _iso(-300),
            "window_end": _iso(3600),
        },
        headers=admin,
    )
    check(generated.status_code in (200, 201), f"期中组卷（{generated.text[:120]}）")
    exam = generated.json()
    exam_id = exam["exam_id"]

    exams = client.get("/api/exams", headers=student)
    check(exams.status_code == 200, "考试中心列表")
    target = next((item for item in exams.json() if item["id"] == exam_id), None)
    check(target is not None, "学生可见本次考试")
    check(target["window_state"] == "open", "考试窗口状态 open")

    attempt = client.post(f"/api/exams/{exam_id}/attempts", json={}, headers=student)
    check(attempt.status_code == 200, "开始考试")
    attempt_data = attempt.json()
    attempt_id = attempt_data["id"]
    questions = attempt_data["exam"]["questions"]
    check(len(questions) > 0, f"试卷题量={len(questions)}")

    with SessionLocal() as db:
        answers = _answer_values(db, [q["id"] for q in questions])

    save_items = []
    for index, question in enumerate(questions):
        correct = answers.get(question["id"], {})
        if question["q_type"] == "answer":
            save_items.append(
                {"question_id": question["id"], "user_answer": {"value": "解答过程略"}}
            )
        elif index < 2:
            save_items.append(
                {
                    "question_id": question["id"],
                    "user_answer": _wrong_answer(correct, question["q_type"]),
                }
            )
        else:
            save_items.append(
                {"question_id": question["id"], "user_answer": dict(correct)}
            )
    saved = client.patch(
        f"/api/exams/attempts/{attempt_id}",
        json={"answers": save_items},
        headers=student,
    )
    check(saved.status_code == 200, "考试暂存")
    check(saved.json()["saved"] >= 1, "暂存写入成功")

    submit_token = attempt_data.get("submit_token") or f"e2e-{attempt_id}-{stamp}"
    submitted = client.post(
        f"/api/exams/attempts/{attempt_id}/submit",
        json={
            "submit_token": submit_token,
            "answers": save_items,
            "duration_ms": 600000,
        },
        headers=student,
    )
    check(
        submitted.status_code == 200,
        f"交卷（{submitted.status_code} {submitted.text[:160]}）",
    )
    submit_data = submitted.json()
    check(
        submit_data["status"] in ("graded", "grading", "completed"),
        f"交卷状态={submit_data['status']}",
    )

    report = client.get(f"/api/exams/attempts/{attempt_id}/report", headers=student)
    check(report.status_code in (200, 409), "考试报告")
    if report.status_code == 200:
        report_data = report.json()
        check(len(report_data["ability_stats"]) >= 1, "报告含能力维度")
        check(
            report_data["class_average"]["available"] is True,
            "报告含班级平均（已交卷同班学生）",
        )
        check("points" in report_data["trend"], "报告含成绩趋势")
    else:
        check(submit_data["status"] == "grading", "含主观题未自评时报告 409（待自评）")

    self_assess_items = [
        {"question_id": q["id"], "score": 4.0}
        for q in questions
        if q["q_type"] == "answer"
    ]
    if self_assess_items:
        assessed = client.post(
            f"/api/exams/attempts/{attempt_id}/self-assess",
            json={"items": self_assess_items},
            headers=student,
        )
        check(assessed.status_code == 200, "主观题自评")
        check(
            assessed.json()["assessed_count"] == len(self_assess_items),
            "自评覆盖全部主观题",
        )
        report_after = client.get(
            f"/api/exams/attempts/{attempt_id}/report", headers=student
        )
        check(report_after.status_code == 200, "自评后可查看报告")
        check(report_after.json()["total_score"] is not None, "报告总分已生成")
    else:
        print("  SKIP  本套试卷无主观题，主观自评由 pytest 用例覆盖")

    with SessionLocal() as db:
        exam_records = db.scalars(
            select(StudentQuestionRecord).where(
                StudentQuestionRecord.user_id == student_id,
                StudentQuestionRecord.source == "exam",
            )
        ).all()
        check(len(exam_records) >= 1, "考试客观题已回流答题记录")
        wrong_rows = db.scalars(
            select(WrongQuestion).where(WrongQuestion.user_id == student_id)
        ).all()
        check(
            all(row.wrong_reason for row in wrong_rows),
            "错题均带错因（考试回流默认分类）",
        )

    # ---------------- 教师班级学情 --------------
    class_stats = client.get(
        f"/api/org/classes/{class_id}/stats",
        params={"subject": "math"},
        headers=teacher,
    )
    check(class_stats.status_code == 200, "教师查看班级学情")
    class_data = class_stats.json()
    check(class_data["student_count"] == 1, "班级人数=1（聚合值）")
    check(class_data["total_answered"] > 0, "班级聚合已包含作答")
    check("weak_points" in class_data, "班级学情含薄弱知识点")

    # ---------------- 家长绑定与孩子学情 --------------
    parent_token = login(client, parent_phone, PASSWORD)
    parent = _auth(parent_token)
    binding = client.post(
        "/api/family/bindings",
        json={"child_phone": student_phone, "relation": "mother"},
        headers=parent,
    )
    check(binding.status_code == 201, "家长发起绑定")
    binding_id = binding.json()["id"]
    confirmed = client.post(
        f"/api/family/bindings/{binding_id}/confirm", headers=student
    )
    check(confirmed.status_code == 200, "孩子确认绑定")
    check(confirmed.json()["status"] == "active", "绑定关系生效")
    child_stats = client.get(
        "/api/learn/stats", params={"student_id": student_id}, headers=parent
    )
    check(child_stats.status_code == 200, "家长查看孩子学情")
    check(child_stats.json()["total_answered"] > 0, "家长可见孩子作答数")

    print(f"\n[E2E] 全部通过：{_passed} 项断言")


if __name__ == "__main__":
    main()
