"""重建 7–9 年级英语期中/期末卷（走真实 /api/exams/generate，不旁路组卷逻辑）。

为什么单独成脚本：书面表达题每册只有 4 道，若直接连续生成，期中与期末极易抽到
同一道写作题。这里在生成期末前，把期中已用的写作题临时置为 draft（不参与抽题），
生成完再恢复 published；试卷内是题目快照，状态变化不影响已出卷。

用法：
    python -m scripts.regen_english_papers          # 删除并重建 6 张
    python -m scripts.regen_english_papers --keep   # 只切换写作题，不重建（调试用）

前置：uvicorn 在 127.0.0.1:18080 运行，且已跑过 align_sz_curriculum / seed_english_by_unit /
seed_english_writing。
"""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.parse
import urllib.request

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.content import Question, Textbook
from app.models.exam import Exam

BASE = "http://127.0.0.1:18080"
ADMIN = ("13800000000", "LocalPg#2026Admin")
STAGE = {"midterm": "期中", "final": "期末"}


def _post(url: str, data, headers=None, as_form: bool = False) -> dict:
    body = urllib.parse.urlencode(data).encode() if as_form else json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers=headers or {})
    with urllib.request.urlopen(req, timeout=240) as resp:
        return json.loads(resp.read().decode())


def _composition_ids(db, title: str) -> list[int]:
    exam = db.scalar(select(Exam).where(Exam.title == title).order_by(Exam.id.desc()))
    if exam is None:
        return []
    ids = []
    for item in exam.questions or []:
        qid = item.get("question_id") if isinstance(item, dict) else item
        if qid is not None:
            q = db.get(Question, qid)
            if q is not None and q.q_type == "composition":
                ids.append(q.id)
    return ids


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--keep", action="store_true", help="不删旧卷，只做写作题去重校验")
    args = parser.parse_args()

    with SessionLocal() as db:
        titles = {f"{g}年级英语{s}" for g in (7, 8, 9) for s in ("期中", "期末")}
        targets = [e for e in db.scalars(select(Exam)) if e.title in titles]
        if not args.keep:
            print("删除旧卷：", [(e.id, e.title) for e in targets])
            for e in targets:
                db.delete(e)
            db.commit()
        rows = db.scalars(
            select(Textbook).where(
                Textbook.subject == "english",
                Textbook.grade.between(7, 9),
                Textbook.semester == "first",
            )
        )
        books = {b.grade: b.id for b in rows if b.version.startswith("上教版")}

    token = _post(
        f"{BASE}/api/auth/login",
        {"username": ADMIN[0], "password": ADMIN[1]},
        {"Content-Type": "application/x-www-form-urlencoded"},
        as_form=True,
    )["access_token"]
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    for grade in (7, 8, 9):
        used: list[int] = []
        for stage in ("midterm", "final"):
            if stage == "final" and used:
                with SessionLocal() as db:
                    for qid in used:
                        q = db.get(Question, qid)
                        if q is not None:
                            q.status = "draft"
                    db.commit()
            payload = {
                "blueprint_code": f"g{grade}_english_{stage}",
                "textbook_id": books[grade],
                "scope": "book",
                "title": f"{grade}年级英语{STAGE[stage]}",
                "avoid_recent_repeats": True,
            }
            try:
                body = _post(f"{BASE}/api/exams/generate", payload, headers)
                print(f"OK g{grade} {stage}: 分{body.get('total_score')}")
            except urllib.error.HTTPError as exc:
                print(f"FAIL g{grade} {stage}: {exc.read().decode()[:400]}")
                continue
            with SessionLocal() as db:
                used = _composition_ids(db, f"{grade}年级英语{STAGE[stage]}")

    with SessionLocal() as db:
        restored = 0
        for q in db.scalars(select(Question).where(Question.subject == "english", Question.q_type == "composition")):
            if q.status == "draft" and (q.source_ref or "").startswith("selfbank:en_w:"):
                q.status = "published"
                restored += 1
        db.commit()
        print(f"恢复写作题 published：{restored} 条")
        for grade in (7, 8, 9):
            mid = _composition_ids(db, f"{grade}年级英语期中")
            fin = _composition_ids(db, f"{grade}年级英语期末")
            print(f"g{grade} 期中{mid} vs 期末{fin} → {'同题' if mid == fin else '不同题'}")


if __name__ == "__main__":
    raise SystemExit(main())
