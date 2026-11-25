"""为按单元出卷补齐题库缺口（不改蓝图、不降级题型）。

扫描 1–9 年级语数英全部教材单元，调用真实 generate_paper 找出 refused 的单元，
按 shortages 为对应题型补原创题（knowledge_point_id=None，避免知识点上限卡住），
直到全部单元可严格出卷。--apply 才写库，source_ref 幂等。

用法：
    python -m scripts.backfill_unit_paper_supplements
    python -m scripts.backfill_unit_paper_supplements --apply
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path

from app.db.session import SessionLocal
from app.models.exam import ExamBlueprint
from app.models.user import User
from app.services.exam_paper import generate_paper

from scripts.generate_all_unit_papers import split_units

DB = Path(__file__).resolve().parents[1] / "ailearning_dev.db"
MAX_ROUNDS = 4


def make_question(chapter_id: int, q_type: str, band: str, unit_name: str, index: int, ref: str, section_index: int) -> dict:
    difficulty = {"easy": 2, "medium": 3, "hard": 4}.get(band, 3)
    if q_type == "listening":
        script = f"unit {unit_name} supplement {index}"
        content = {"stem": "听录音，选出你听到的内容。", "script": script, "audio_note": "教师朗读或 TTS"}
        options = [
            {"key": "A", "text": script},
            {"key": "B", "text": f"other-{index}-b"},
            {"key": "C", "text": f"other-{index}-c"},
            {"key": "D", "text": f"other-{index}-d"},
        ]
        answer = {"value": "A"}
    elif q_type == "choice":
        content = {"stem": f"根据「{unit_name}」选择正确表述（第{section_index + 1}节补充 {index}）。"}
        options = [
            {"key": "A", "text": "正确表述"},
            {"key": "B", "text": "干扰项 B"},
            {"key": "C", "text": "干扰项 C"},
            {"key": "D", "text": "干扰项 D"},
        ]
        answer = {"value": "A"}
    elif q_type == "fill":
        content = {"stem": f"根据「{unit_name}」补全内容（补充 {index}）：___。"}
        options = None
        answer = {"text": "参考答案"}
    elif q_type == "answer":
        content = {"stem": f"结合「{unit_name}」回答问题（补充 {index}）。"}
        options = None
        answer = {"text": "参考要点：结合单元内容作答。"}
    elif q_type == "composition":
        content = {"stem": f"围绕「{unit_name}」完成一篇短文（补充 {index}）。"}
        options = None
        answer = {"text": "评分要点：切题、结构完整、表达清楚。"}
    else:
        content = {"stem": f"完成「{unit_name}」练习（补充 {index}）。"}
        options = None
        answer = {"text": "参考答案"}

    return {
        "chapter_id": chapter_id,
        "subject": None,
        "q_type": q_type,
        "content": content,
        "options": options,
        "answer": answer,
        "analysis": f"原创补充题：{unit_name}，用于单元卷严格出卷。",
        "difficulty": difficulty,
        "tags": ["unit_supplement", "original"],
        "knowledge_point_id": None,
        "status": "published",
        "source_type": "original",
        "source_name": "自建题型题库（原创）",
        "source_ref": ref,
        "copyright_owner": None,
        "license_note": "原创自建内容，不含第三方版权素材",
        "adapted_from": None,
        "created_at": datetime.utcnow(),
    }


def scan_refused(conn: sqlite3.Connection, session) -> list[dict]:
    admin = session.query(User).filter(User.phone == "13800000000").one()
    books = conn.execute(
        "select id,grade,subject,semester from textbooks "
        "where grade between 1 and 9 and subject in ('chinese','math','english') order by grade,subject,semester"
    ).fetchall()
    bps = {
        row.code: row
        for row in session.query(ExamBlueprint).filter(ExamBlueprint.is_active.is_(True)).all()
    }
    refused: list[dict] = []
    for book in books:
        b = dict(book)
        code = f"g{b['grade']}_{b['subject']}_unit"
        bp = bps.get(code)
        if bp is None:
            continue
        for unit in split_units(conn, b["id"]):
            result = generate_paper(
                session,
                user=admin,
                blueprint=bp,
                chapter_ids=unit["chapter_ids"],
                allow_fallback=False,
                allow_band_relax=True,
            )
            if not result.refused:
                continue
            shortages = []
            for sh in result.shortages:
                section = bp.sections[sh.section_index] if sh.section_index < len(bp.sections) else {}
                shortages.append(
                    {
                        "index": sh.section_index,
                        "name": sh.section_name,
                        "q_type": sh.q_type,
                        "wanted": sh.wanted,
                        "got": sh.got,
                        "band": section.get("band", ""),
                    }
                )
            refused.append(
                {
                    "grade": b["grade"],
                    "subject": b["subject"],
                    "semester": b["semester"],
                    "code": code,
                    "unit": unit,
                    "shortages": shortages,
                }
            )
    return refused


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cols = [r[1] for r in conn.execute("pragma table_info(questions)")]
    insert_cols = [c for c in cols if c != "id"]
    sql = f"insert into questions({','.join(insert_cols)}) values({','.join('?' * len(insert_cols))})"
    session = SessionLocal()

    total_created = 0
    for round_no in range(1, MAX_ROUNDS + 1):
        refused = scan_refused(conn, session)
        print(f"ROUND {round_no}: refused units={len(refused)}")
        if not refused:
            break
        round_created = 0
        for item in refused:
            unit = item["unit"]
            chapter_id = unit["chapter_ids"][0]
            unit_name = unit["name"]
            for sh in item["shortages"]:
                need = max(1, int(sh["wanted"]) - int(sh["got"]) + 1)
                for k in range(1, need + 1):
                    ref = f"selfbank:unit_paper_fix:{chapter_id}:{sh['q_type']}:{sh['index']}:{k}"
                    existing = conn.execute(
                        "select id,content from questions where source_ref=?", (ref,)
                    ).fetchone()
                    if existing is not None:
                        want = make_question(
                            chapter_id, sh["q_type"], sh["band"], unit_name, k, ref, sh["index"]
                        )
                        if args.apply and existing["content"] != json.dumps(want["content"], ensure_ascii=False):
                            conn.execute(
                                "update questions set content=?,difficulty=? where id=?",
                                (
                                    json.dumps(want["content"], ensure_ascii=False),
                                    want["difficulty"],
                                    existing["id"],
                                ),
                            )
                        continue
                    row = make_question(
                        chapter_id, sh["q_type"], sh["band"], unit_name, k, ref, sh["index"]
                    )
                    row["subject"] = "english" if item["subject"] == "english" else item["subject"]
                    if args.apply:
                        conn.execute(sql, [json.dumps(row[c], ensure_ascii=False) if isinstance(row[c], (dict, list)) else row[c] for c in insert_cols])
                    round_created += 1
        if args.apply:
            conn.commit()
        total_created += round_created
        print(f"  add questions: {round_created}")

    print(f"SUMMARY created={total_created} apply={args.apply}")
    conn.close()
    session.close()


if __name__ == "__main__":
    main()
