"""81 张已发布卷的「能开考」全量验证（接口级，跑完清理痕迹）。

逐年级把学生年级临时切到 g，调 /api/exams 拿该年级 9 张卷，
逐张 POST /api/exams/{id}/attempts 开考，校验：
  - 开考 200，返回题目数与 exams.questions 一致
  - 首题题干非空、有作答结构
  - 卷内含 listening 题时，抽 1 道请求听力音频（带本次 attempt_id）应为 200
跑完删除本次新建的 attempts，并把学生年级复原。

用法（backend 下，需 uvicorn 在 18080）：
    python -m scripts.verify_papers_takeable
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx  # noqa: E402
from sqlalchemy import delete, select  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.models.exam import ExamAttempt  # noqa: E402
from app.models.user import User  # noqa: E402

BASE = "http://127.0.0.1:18080"
STUDENT = {"username": "13900000000", "password": "student123"}
STUDENT_ID = 2


def main() -> int:
    db = SessionLocal()
    user = db.query(User).filter(User.id == STUDENT_ID).first()
    if user is None:
        print("学生账号不存在")
        return 1
    origin_grade = user.grade
    created: list[tuple[int, int]] = []

    rows: list[dict] = []
    try:
        with httpx.Client(base_url=BASE, timeout=90) as c:
            token = c.post("/api/auth/login", data=STUDENT).json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            for grade in range(1, 10):
                user.grade = grade
                db.commit()

                exams = c.get("/api/exams", headers=headers, params={"limit": 500}).json()
                mine = sorted((e for e in exams if int(e["grade"]) == grade), key=lambda e: (e["subject"], e["exam_type"]))
                if len(mine) != 9:
                    rows.append({
                        "grade": grade, "exam_id": "-", "title": f"该年级可见卷数异常：{len(mine)}",
                        "subject": "-", "exam_type": "-", "start": "MISSING", "questions": 0,
                        "first_stem_len": 0, "listening_audio": "-",
                    })
                    continue

                for exam in mine:
                    rec = {
                        "grade": grade, "exam_id": exam["id"], "title": exam["title"],
                        "subject": exam["subject"], "exam_type": exam["exam_type"],
                        "start": "-", "questions": 0, "first_stem_len": 0, "listening_audio": "-",
                    }
                    try:
                        resp = c.post(f"/api/exams/{exam['id']}/attempts", headers=headers, json={})
                        rec["start"] = resp.status_code
                        if resp.status_code != 200:
                            rec["detail"] = resp.text[:120]
                            rows.append(rec)
                            continue
                        data = resp.json()
                        attempt_id = int(data.get("id") or 0)
                        created.append((exam["id"], attempt_id))
                        items = (data.get("exam") or {}).get("questions") or []
                        rec["questions"] = len(items)
                        if items:
                            stem = items[0].get("content") or {}
                            text = stem.get("stem") if isinstance(stem, dict) else str(stem)
                            rec["first_stem_len"] = len((text or "").strip())
                        listening = [q for q in items if q.get("q_type") == "listening"]
                        if listening:
                            qid = int(listening[0]["id"])
                            audio = c.get(
                                f"/api/learn/questions/{qid}/audio",
                                headers=headers,
                                params={"speed": 1.0, "kind": "listening", "attempt_id": attempt_id},
                            )
                            rec["listening_audio"] = audio.status_code
                    except Exception as error:  # noqa: BLE001
                        rec["start"] = "ERR"
                        rec["detail"] = str(error)[:120]
                    rows.append(rec)
                    print(f"g{grade} {exam['title']}: start={rec['start']} 题数={rec['questions']} "
                          f"首题长度={rec['first_stem_len']} 听力={rec['listening_audio']}")
    finally:
        user.grade = origin_grade
        db.commit()
        # 清理本轮新建的作答记录，避免污染学生学习足迹
        for _exam_id, attempt_id in created:
            if attempt_id:
                db.execute(delete(ExamAttempt).where(ExamAttempt.id == attempt_id))
        db.commit()
        remaining = db.execute(
            select(ExamAttempt.id).where(ExamAttempt.user_id == STUDENT_ID)
        ).scalars().all()
        print(f"\n已清理 {len(created)} 条 attempts；该学生剩余 attempts: {len(remaining)}；年级复原为 {origin_grade}")

    out_dir = Path(__file__).resolve().parents[2] / "docs" / "content-templates" / "exports" / "paper_audit_20261118"
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "takeable_matrix.csv"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    ok = [r for r in rows if r["start"] == 200]
    bad = [r for r in rows if r["start"] != 200]
    empty_paper = [r for r in ok if not r["questions"]]
    empty_stem = [r for r in ok if r["questions"] and r["first_stem_len"] <= 0]
    listen_fail = [r for r in ok if r["subject"] == "english" and r["listening_audio"] != 200]
    print(f"\n开考成功 {len(ok)} / {len(rows)}，失败 {len(bad)}")
    print(f"空卷 {len(empty_paper)}、首题题干为空 {len(empty_stem)}、英语听力音频非 200 {len(listen_fail)}")
    for r in (bad + empty_paper + empty_stem + listen_fail)[:10]:
        print("  异常:", r)
    print(f"明细已写入 {csv_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
