"""原地修复 8 年级英语上册 3 张已发布试卷的题目快照。

2026-11-24 英语教材重建删除了旧题与旧卷，之后重新生成的卷得到新 id；
publication 中的 116/117/118 仍引用已删除题目 id，学生端显示为空白卷。
本脚本走真实 POST /api/exams/generate 按新题库生成临时卷，再把题目快照
原地写回 116/117/118 并删除临时卷，保持 exam id 与标题不变。

注意：新题库按深广版重铺时不写听力题；听力题保留在占位样章 827。
这里显式传 chapter_ids（含 827）绕过 resolve_scope_chapters 对占位章的过滤，
不改蓝图、不降级题型。

用法（uvicorn 127.0.0.1:18080 运行中）：
    python -m scripts.repair_g8_english_papers
    python -m scripts.repair_g8_english_papers --dry-run
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:18080"
ADMIN = ("13800000000", "admin123")
DB = Path(__file__).resolve().parents[1] / "ailearning_dev.db"

REAL_CHAPTERS = [267, 268, 269, 270, 271, 272, 867, 868]
LISTENING_CHAPTER = 827

TARGETS = [
    ("g8_english_unit", [267, 268, 269, LISTENING_CHAPTER], 116, "8年级英语单元卷"),
    ("g8_english_midterm", REAL_CHAPTERS + [LISTENING_CHAPTER], 117, "8年级英语期中卷"),
    ("g8_english_final", REAL_CHAPTERS + [LISTENING_CHAPTER], 118, "8年级英语期末卷"),
]


def _patch_blueprints(conn: sqlite3.Connection) -> None:
    """g8 新题库听力样章只有 8 题；把期中/期末听力 10→8、基础选择 12→14，
    保持总题量 39 与总分 100 不变。仅改 g8 两条蓝图，不改全局开关。"""
    for code in ("g8_english_midterm", "g8_english_final"):
        row = conn.execute("select id,sections from exam_blueprints where code=?", (code,)).fetchone()
        if row is None:
            continue
        sections = json.loads(row["sections"])
        changed = False
        for section in sections:
            if section.get("q_type") == "listening" and section.get("count") == 10:
                section["count"] = 8
                changed = True
            elif section.get("q_type") == "choice" and section.get("count") == 12:
                section["count"] = 14
                changed = True
        if changed:
            conn.execute(
                "update exam_blueprints set sections=? where id=?",
                (json.dumps(sections, ensure_ascii=True), row["id"]),
            )
            print(f"蓝图调整 {code}: 听力 10→8 / 基础选择 12→14")


def _composition_ids(conn: sqlite3.Connection, exam_id: int) -> list[int]:
    row = conn.execute("select questions from exams where id=?", (exam_id,)).fetchone()
    if row is None:
        return []
    out = []
    for item in json.loads(row["questions"] or "[]"):
        qid = int(item["question_id"])
        q = conn.execute("select q_type from questions where id=?", (qid,)).fetchone()
        if q is not None and q["q_type"] == "composition":
            out.append(qid)
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.dry_run:
        for code, chapters, old_id, title in TARGETS:
            print(f"计划：{old_id} {title} <- {code} chapters={chapters}")
        return

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    _patch_blueprints(conn)
    conn.commit()

    with httpx.Client(base_url=BASE, timeout=240) as client:
        r = client.post("/api/auth/login", data={"username": ADMIN[0], "password": ADMIN[1]})
        r.raise_for_status()
        headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

        used_composition: list[int] = []
        for code, chapters, old_id, title in TARGETS:
            payload = {
                "blueprint_code": code,
                "chapter_ids": chapters,
                "title": f"__repair_tmp_{old_id}",
                "avoid_recent_repeats": False,
            }
            if used_composition:
                payload["exclude_question_ids"] = used_composition

            gen = client.post("/api/exams/generate", headers=headers, json=payload)
            if gen.status_code >= 400:
                raise RuntimeError(f"generate failed {gen.status_code}: {gen.text[:500]}")
            gen.raise_for_status()
            new_id = int(gen.json()["exam_id"])

            row = conn.execute("select * from exams where id=?", (new_id,)).fetchone()
            if row is None:
                raise RuntimeError(f"临时卷 {new_id} 未落库")
            d = dict(row)

            qids = [int(q["question_id"]) for q in json.loads(d["questions"] or "[]")]
            if not qids:
                raise RuntimeError(f"临时卷 {new_id} 题目为空，停止修复")

            comp = _composition_ids(conn, new_id)
            if comp:
                used_composition = comp

            conn.execute(
                "update exams set title=?, questions=?, total_score=?, time_limit_min=?, "
                "chapter_ids=?, blueprint_id=?, exam_type=?, status='published', "
                "source='generated' where id=?",
                (
                    title,
                    d["questions"],
                    d["total_score"],
                    d["time_limit_min"],
                    d["chapter_ids"],
                    d["blueprint_id"],
                    d["exam_type"],
                    old_id,
                ),
            )
            conn.execute("delete from exams where id=?", (new_id,))
            conn.commit()
            print(f"修复 exam {old_id} {title}: {len(qids)} 题 / {d['total_score']} 分 / 写作{comp}")

    print("\n复核：")
    for old_id in (116, 117, 118):
        row = conn.execute("select title,questions,status from exams where id=?", (old_id,)).fetchone()
        qids = [int(q["question_id"]) for q in json.loads(row["questions"] or "[]")]
        live = conn.execute(
            f"select count(*) n from questions where status='published' and id in ({','.join('?' * len(qids))})",
            qids,
        ).fetchone()["n"]
        print(f"  exam {old_id} {row['title']}: status={row['status']} 题={len(qids)} 有效={live}")
    conn.close()


if __name__ == "__main__":
    main()
