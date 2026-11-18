"""批量生成 9 年级 × 3 科目 × 3 阶段 = 81 张试卷，供真机走查用。

以管理员身份走真实接口（POST /api/exams/generate），完整复用线上组卷逻辑：
blueprint → scope 章节 → 核心清单注入 → 跨带校验，不做任何旁路。
生成结果为 published 普通卷，学生端考试中心即可直接看到。

用法（先确保 uvicorn 在 127.0.0.1:18080 运行）：
    python scripts/gen_walkthrough_papers.py --apply
不加 --apply 只做 dry-run，打印计划。

卷标题统一为「<年级><科目><阶段>卷」，与面向学生的正式命名一致：
走查是内部流程词，不能出现在学生端考试中心的卷名里。批量清理请用 --clean
配合 `--title-keyword` 指定匹配串（默认「卷」用于脚本自身生成的卷时请谨慎，
建议先用数据库侧台账确认）。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx

BASE = "http://127.0.0.1:18080"
ADMIN = ("13800000000", "admin123")
SUBJECTS = ("chinese", "math", "english")
STAGES = ("unit", "midterm", "final")
SUBJECT_CN = {"chinese": "语文", "math": "数学", "english": "英语"}
STAGE_CN = {"unit": "单元", "midterm": "期中", "final": "期末"}


def login(client: httpx.Client) -> str:
    r = client.post("/api/auth/login", data={"username": ADMIN[0], "password": ADMIN[1]})
    r.raise_for_status()
    return r.json()["access_token"]


def textbooks(client: httpx.Client, token: str) -> dict[tuple[str, int, str], int]:
    r = client.get("/api/public/textbooks")
    r.raise_for_status()
    out = {}
    for b in r.json():
        out[(b["subject"], int(b["grade"]), b["semester"])] = int(b["id"])
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--semester", default="first")
    ap.add_argument("--clean", action="store_true")
    ap.add_argument("--grades", nargs="+", type=int, default=list(range(1, 10)))
    args = ap.parse_args()

    with httpx.Client(base_url=BASE, timeout=120) as c:
        token = login(c)
        h = {"Authorization": f"Bearer {token}"}
        if args.clean:
            r = c.get("/api/exams", headers=h, params={"limit": 500})
            r.raise_for_status()
            items = r.json()
            n = 0
            for it in items:
                if "走查" in (it.get("title") or ""):
                    d = c.delete(f"/api/exams/{it['id']}", headers=h)
                    if d.status_code < 400:
                        n += 1
                    else:
                        print(f"  清理失败 {it['id']}: {d.status_code} {d.text[:80]}")
            print(f"已清理 {n} 张走查卷")
            return 0

        books = textbooks(c, token)
        ok = fail = 0
        failures = []
        for g in args.grades:
            for s in SUBJECTS:
                for st in STAGES:
                    tid = books.get((s, g, args.semester))
                    if tid is None:
                        print(f"g{g} {s} {args.semester} 无教材，跳过")
                        continue
                    payload = {
                        "blueprint_code": f"g{g}_{s}_{st}",
                        "textbook_id": tid,
                        "scope": "unit" if st == "unit" else "book",
                        "unit_index": 1 if st == "unit" else None,
                        "title": f"{g}年级{SUBJECT_CN[s]}{STAGE_CN[st]}",
                        "avoid_recent_repeats": True,
                    }
                    if not args.apply:
                        print(f"  计划 g{g} {s} {st} -> {payload['title']}")
                        continue
                    r = c.post("/api/exams/generate", headers=h, json=payload)
                    if r.status_code < 400:
                        body = r.json()
                        ok += 1
                        print(f"  OK  g{g} {s:8s} {st:8s} id={body.get('exam_id')} 题={body.get('items')} 分={body.get('score')}")
                    else:
                        fail += 1
                        failures.append((g, s, st, r.status_code, r.text[:160]))
                        print(f"  FAIL g{g} {s:8s} {st:8s} {r.status_code} {r.text[:120]}")
        if args.apply:
            print(f"\n生成 OK {ok}，失败 {fail}")
            for f in failures:
                print("  失败明细", f)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
