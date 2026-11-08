# -*- coding: utf-8 -*-
"""把「没有任何章节」的教材置为 is_active=0（默认 dry-run），避免 App 里出现空目录。

只影响无章节的教材，本次即 高中数学 10-12 全学科 + 数学北师大版九年级上下（共 56 本）。
每个被改动的教材 id 会写进清单文件，--rollback 可原样恢复。

用法（在 content-templates 目录）：
  python _deactivate_empty_textbooks.py                # 预览
  python _deactivate_empty_textbooks.py --apply         # 执行
  python _deactivate_empty_textbooks.py --rollback      # 按清单恢复
"""
import argparse
import json
import sqlite3
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2] / "backend"
LEDGER = Path(__file__).resolve().parent / "baseline" / "_deactivated_textbooks_20261107.json"
DBS = ["ailearning_dev.db", "ailearning_device.db"]

EMPTY_SQL = """
select t.id, t.subject, t.grade, t.version, t.semester
from textbooks t
where not exists (select 1 from chapters ch where ch.textbook_id = t.id)
order by t.grade, t.subject, t.version, t.semester
"""


def load_ledger() -> dict:
    if LEDGER.exists():
        return json.loads(LEDGER.read_text(encoding="utf-8"))
    return {}


def save_ledger(data: dict) -> None:
    LEDGER.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run(db_path: Path, mode: str, ledger: dict) -> tuple[bool, list[dict]]:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    try:
        if mode == "rollback":
            ids = [r["id"] for r in ledger.get(db_path.name, [])]
            if not ids:
                print(f"\n== {db_path.name}: 清单里没有记录，无需恢复")
                return True, []
            cur.execute(
                "update textbooks set is_active=1 where id in (%s)" % ",".join(map(str, ids))
            )
            conn.commit()
            changed = cur.rowcount
            print(f"\n== {db_path.name}: 已恢复 {changed} 本教材为 is_active=1")
            active = cur.execute("select count(*) from textbooks where is_active=1").fetchone()[0]
            print(f"   当前启用教材 {active} / 146")
            return True, []

        rows = cur.execute(EMPTY_SQL).fetchall()
        print(f"\n== {db_path.name}: 无章节教材 {len(rows)} 本")
        for r in rows:
            print(f"     id={r[0]:>3} {r[1]} g{r[2]} {r[3]} {r[4]}")
        if not rows:
            return True, []
        if mode == "apply":
            ids = [r[0] for r in rows]
            cur.execute(
                "update textbooks set is_active=0 where id in (%s)" % ",".join(map(str, ids))
            )
            conn.commit()
            active = cur.execute("select count(*) from textbooks where is_active=1").fetchone()[0]
            print(f"   [done] 已停用 {len(ids)} 本，当前启用 {active} / 146")
        else:
            print("   [dry-run] 未写库，加 --apply 执行")
        return True, [
            {"id": r[0], "subject": r[1], "grade": r[2], "version": r[3], "semester": r[4]}
            for r in rows
        ]
    finally:
        conn.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--apply", action="store_true")
    g.add_argument("--rollback", action="store_true")
    args = ap.parse_args()
    mode = "apply" if args.apply else "rollback" if args.rollback else "dry"
    ledger = load_ledger()

    ok = True
    for name in DBS:
        path = BACKEND / name
        if not path.exists():
            print(f"[skip] {name} 不存在")
            continue
        ok_run, picked = run(path, mode, ledger)
        ok = ok and ok_run
        if picked:
            ledger[path.name] = picked
    if mode != "rollback" and ledger:
        save_ledger(ledger)
        print(f"\n清单已写入 {LEDGER}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
