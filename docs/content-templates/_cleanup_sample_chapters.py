# -*- coding: utf-8 -*-
"""清理库内占位/样例章节（默认 dry-run，不加 --apply 不会写库）。

两个目标：
  second-samples  下册 g1-g3 语数英里 2026-11-07 之前的早期样例章节（27 章 / 108 题）
  placeholders    名称含「样章」的模板占位章节（1-12 年级全学科，64 章 / 384 题）

删除前会检查引用：若这些题目已被错题本 / 答题记录 / 考卷答案引用，则中止。
两个库（ailearning_dev.db、ailearning_device.db）都会处理，可用 --db 只处理一个。

用法（在 content-templates 目录）：
  python _cleanup_sample_chapters.py --target second-samples              # 预览
  python _cleanup_sample_chapters.py --target second-samples --apply      # 执行
"""
import argparse
import sqlite3
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2] / "backend"
DBS = ["ailearning_dev.db", "ailearning_device.db"]

SECOND_SAMPLES_SQL = """
select q.id from questions q
join chapters ch on ch.id = q.chapter_id
join textbooks t on t.id = ch.textbook_id
where t.semester = 'second'
  and t.subject in ('math', 'chinese', 'english')
  and t.grade in (1, 2, 3)
"""
SECOND_SAMPLES_CH_SQL = """
select ch.id from chapters ch join textbooks t on t.id = ch.textbook_id
where t.semester = 'second' and t.subject in ('math','chinese','english') and t.grade in (1,2,3)
"""
PLACEHOLDER_CH_SQL = "select id from chapters where name like '%样章%'"
PLACEHOLDER_Q_SQL = "select id from questions where chapter_id in (%s)"

REF_TABLES = ("wrong_questions", "student_question_records", "exam_answers")


def collect(cur, target: str) -> tuple[list[int], list[int]]:
    if target == "second-samples":
        ch = [r[0] for r in cur.execute(SECOND_SAMPLES_CH_SQL)]
        q = [r[0] for r in cur.execute(SECOND_SAMPLES_SQL)]
        return ch, q
    ch = [r[0] for r in cur.execute(PLACEHOLDER_CH_SQL)]
    if not ch:
        return [], []
    q = [r[0] for r in cur.execute(PLACEHOLDER_Q_SQL % ",".join(map(str, ch)))]
    return ch, q


def run(db_path: Path, target: str, apply: bool) -> bool:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    try:
        ch_ids, q_ids = collect(cur, target)
        print(f"\n== {db_path.name} / {target}")
        print(f"   待删章节 {len(ch_ids)} 个，待删题目 {len(q_ids)} 道")
        if not ch_ids:
            print("   无需处理")
            return True
        if q_ids:
            ids_sql = ",".join(map(str, q_ids))
            blocked = False
            for t in REF_TABLES:
                n = cur.execute(f"select count(*) from {t} where question_id in ({ids_sql})").fetchone()[0]
                if n:
                    print(f"   [中止] {t} 有 {n} 条引用，请先人工确认")
                    blocked = True
            if blocked:
                return False
        for r in cur.execute(
            "select t.subject, t.grade, ch.name from chapters ch join textbooks t on t.id=ch.textbook_id "
            "where ch.id in (" + ",".join(map(str, ch_ids)) + ") order by t.subject, t.grade, ch.order_index"
        ):
            print(f"     - {r[0]} g{r[1]}: {r[2]}")
        if not apply:
            print("   [dry-run] 未写库，加 --apply 执行")
            return True
        cur.execute("delete from questions where id in (%s)" % ",".join(map(str, q_ids))) if q_ids else None
        cur.execute("delete from chapters where id in (%s)" % ",".join(map(str, ch_ids)))
        conn.commit()
        left_ch = cur.execute("select count(*) from chapters").fetchone()[0]
        left_q = cur.execute("select count(*) from questions").fetchone()[0]
        print(f"   [done] 剩余章节 {left_ch} / 题目 {left_q}")
        return True
    finally:
        conn.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True, choices=["second-samples", "placeholders"])
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--db", help="只处理指定库文件名")
    args = ap.parse_args()

    dbs = [d for d in DBS if not args.db or d == args.db]
    ok = True
    for name in dbs:
        path = BACKEND / name
        if not path.exists():
            print(f"[skip] {name} 不存在")
            continue
        ok = run(path, args.target, args.apply) and ok
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
