"""按教材单元章节批量生成单元卷（全年级 / 全科目 / 上下册）。

口径：
- 单元由章节名解析（第N单元 / 第N章 / Unit N / 中文数字开头的章名），
  从该章开始到下一单元前的所有章节作为该单元范围。
- 每个单元生成一张卷，标题带年级、科目、册别与单元名。
- 默认 dry-run；--apply 才写入 exams。
- 已存在同标题的卷会跳过（幂等）。

用法：
    python -m scripts.generate_all_unit_papers
    python -m scripts.generate_all_unit_papers --apply
    python -m scripts.generate_all_unit_papers --apply --grade 8 --subject english --semester first
"""

from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal  # noqa: E402
from app.models.exam import ExamBlueprint  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.exam_blueprint_matrix import build_specs  # noqa: E402
from app.services.exam_paper import generate_paper  # noqa: E402

DB = Path(__file__).resolve().parents[1] / "ailearning_dev.db"
BASE = "http://127.0.0.1:18080"
ADMIN = ("13800000000", "admin123")
CN_NUM = {c: i for i, c in enumerate("零一二三四五六七八九十")}

UNIT_PATTERNS = [
    re.compile(r"^第\s*(\d+|[一二三四五六七八九十]+)\s*(单元|章)"),
    re.compile(r"^Unit\s+(\d+)", re.I),
    re.compile(r"^([一二三四五六七八九十]+)\s+\S"),
]
SUBJECT_CN = {"chinese": "语文", "math": "数学", "english": "英语"}
SEMESTER_CN = {"first": "上册", "second": "下册"}


def cn_to_int(s: str) -> int:
    if s.isdigit():
        return int(s)
    if s == "十":
        return 10
    if "十" in s:
        a, b = s.split("十", 1)
        return (CN_NUM[a] if a else 1) * 10 + (CN_NUM[b] if b else 0)
    return CN_NUM.get(s, 0)


def unit_index_of(name: str) -> int | None:
    for pattern in UNIT_PATTERNS:
        m = pattern.match(name or "")
        if m:
            return cn_to_int(m.group(1))
    return None


def split_units(conn: sqlite3.Connection, textbook_id: int) -> list[dict]:
    chapters = conn.execute(
        "select id,name,is_placeholder from chapters where textbook_id=? order by order_index,id",
        (textbook_id,),
    ).fetchall()
    groups: dict[int, dict] = {}
    current: dict | None = None
    for ch in chapters:
        if ch["is_placeholder"]:
            continue
        idx = unit_index_of(ch["name"])
        if idx:
            if idx not in groups:
                groups[idx] = {"index": idx, "name": ch["name"], "chapter_ids": []}
                current = groups[idx]
            else:
                current = groups[idx]
        if current is not None:
            current["chapter_ids"].append(ch["id"])
    return [groups[k] for k in sorted(groups)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--grade", type=int)
    ap.add_argument("--subject")
    ap.add_argument("--semester", choices=("first", "second"))
    args = ap.parse_args()

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    bp = {spec["code"]: spec for spec in build_specs()}
    session = SessionLocal()
    admin = session.query(User).filter(User.phone == ADMIN[0]).one()
    bp_models = {
        row.code: row
        for row in session.query(ExamBlueprint).filter(ExamBlueprint.is_active.is_(True)).all()
    }

    q = (
        "select id,grade,subject,semester,version from textbooks "
        "where subject in ('chinese','math','english') and grade between 1 and 9"
    )
    params: list = []
    if args.grade:
        q += " and grade=?"
        params.append(args.grade)
    if args.subject:
        q += " and subject=?"
        params.append(args.subject)
    if args.semester:
        q += " and semester=?"
        params.append(args.semester)
    q += " order by grade,subject,semester"
    books = conn.execute(q, params).fetchall()

    token_headers = None
    if args.apply:
        with httpx.Client(base_url=BASE, timeout=60) as client:
            r = client.post("/api/auth/login", data={"username": ADMIN[0], "password": ADMIN[1]})
            r.raise_for_status()
            token_headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    planned = succeeded = skipped = failed = 0
    failures: list[str] = []

    for book in books:
        b = dict(book)
        code = f"g{b['grade']}_{b['subject']}_unit"
        spec = bp.get(code)
        if spec is None:
            failures.append(f"missing blueprint {code}")
            continue
        units = split_units(conn, b["id"])
        print(f"[{b['grade']}年级{SUBJECT_CN[b['subject']]}{SEMESTER_CN[b['semester']]}] {len(units)} 单元")

        for unit in units:
            title = (
                f"{b['grade']}年级{SUBJECT_CN[b['subject']]}{SEMESTER_CN[b['semester']]} "
                f"第{unit['index']}单元卷（{unit['name']}）"
            )
            exists = conn.execute("select id from exams where title=?", (title,)).fetchone()
            if exists:
                skipped += 1
                continue
            planned += 1

            bp_model = bp_models.get(code)
            if bp_model is None:
                failures.append(f"missing active blueprint row {code}")
                failed += 1
                continue
            base_seed = b["id"] * 1000 + unit["index"] + 1
            result = None
            seed = base_seed
            for attempt in range(8):
                candidate_seed = base_seed + attempt * 100000
                candidate = generate_paper(
                    session,
                    user=admin,
                    blueprint=bp_model,
                    chapter_ids=unit["chapter_ids"],
                    seed=candidate_seed,
                    allow_fallback=False,
                    allow_band_relax=True,
                )
                if not candidate.refused and candidate.questions:
                    result = candidate
                    seed = candidate_seed
                    break
            if result is None:
                result = candidate
            if result.refused or not result.questions:
                msg = result.refuse_reason or "; ".join(str(s) for s in result.shortages) or "unknown"
                failed += 1
                failures.append(f"{title}: {msg}")
                print(f"  REFUSED {title}: {msg}")
                continue

            p = result
            if not args.apply:
                print(f"  OK {title}: {len(p.questions)} 题 / {p.total_score} 分")
                continue

            with httpx.Client(base_url=BASE, timeout=120) as client:
                payload = {
                    "blueprint_code": code,
                    "chapter_ids": unit["chapter_ids"],
                    "title": title,
                    "seed": seed,
                    "avoid_recent_repeats": False,
                }
                gen = client.post("/api/exams/generate", headers=token_headers, json=payload)
                if gen.status_code >= 400:
                    failed += 1
                    failures.append(f"{title}: API {gen.status_code} {gen.text[:200]}")
                    print(f"  API FAIL {title}: {gen.status_code}")
                    continue
                succeeded += 1
                print(f"  PUBLISHED {title}: {len(p.questions)} 题")

    print(
        f"\nSUMMARY planned={planned} skipped={skipped} succeeded={succeeded} "
        f"failed={failed} dry_run={not args.apply}"
    )
    if failures:
        print("\nFAILURES")
        for f in failures:
            print(" -", f)
    conn.close()


if __name__ == "__main__":
    main()
