"""按深圳本地教材版本对齐 7-9 年级英语 / 道法内容。

背景（2026-11 教研反馈）
----------------------
库内 7-9 年级英语的章节与知识点，原先按「沪教牛津（牛津上海版）」目录建立
（7A: Trying new things / Strong mind / Jobs / Smart home / Films ...），
但深圳初中英语实际使用 **上海教育出版社「沪教牛津深圳版」2024 新教材**
（7A: Friendship / School life / The seasons / The Earth ... 每册 8 个单元），
两者单元体系完全不同 —— 章名、知识点、题目挂载全部错位。

道法（政治）章节结构本就是人教版（部编）统编新教材，问题只在 `textbooks.version`
写成「部编版」，与深圳实际用书口径不一致，另有几个游离的杂项 section 需要清理。

教材版本口径（深圳市 2025-2026 学年义务教育免费教辅材料选用目录 + 出版社书目）
-------------------------------------------------------------------------------
* 英语：上教版（沪教牛津深圳版），1-9 年级
* 道法：人教版（部编），1-9 年级
* 数学：北师大版；语文：人教版（统编）；历史：部编版；地理：湘教版；
  生物/物理/化学：人教版 —— 本脚本不改这些

用法（在 backend 目录执行）
-------------------------
    .venv\\Scripts\\python.exe -m scripts.align_sz_curriculum --dry-run
    .venv\\Scripts\\python.exe -m scripts.align_sz_curriculum --apply-versions
    .venv\\Scripts\\python.exe -m scripts.align_sz_curriculum --apply-english
    .venv\\Scripts\\python.exe -m scripts.align_sz_curriculum --apply-politics

`--apply-english` 会删除 7-9 英语旧章节、挂在这些章节上的自建题、以及这些卷
（题目是自建原创，删除不影响版权口径；试卷快照引用旧题 id，所以一起删），
随后重建 8 单元/册的章节与知识点，再由 `seed_english_by_unit.py` 重新生成题，
最后走 `/api/exams/generate` 重建试卷。**执行前务必先备份数据库。**
"""

from __future__ import annotations

import argparse

from sqlalchemy import delete, func, select, update

from app.db.session import SessionLocal
from app.models.content import Chapter, KnowledgePoint, Question, Textbook
from app.models.exam import Exam

# ---------------------------------------------------------------------------
# 教材版本口径
# ---------------------------------------------------------------------------
SZ_VERSION_ENGLISH = "上教版（沪教牛津深圳版）"
SZ_VERSION_POLITICS = "人教版（部编）"

# ---------------------------------------------------------------------------
# 上教版（沪教牛津深圳版）2024/2025 新教材单元目录
# 来源：沪教版新教材各册目录（7A 2024 秋 / 7B 2025 春 / 8A 2025 秋 /
#      8B 2026 春 / 9A 2026 秋 / 9B 2027 春待发布）
# ---------------------------------------------------------------------------
SZ_ENGLISH_UNITS: dict[tuple[int, str], list[str]] = {
    (7, "first"): [
        "Friendship", "School life", "The seasons", "The Earth",
        "Off to space", "Travelling around Asia", "Fun after school",
        "Collecting as a hobby",
    ],
    (7, "second"): [
        "People around us", "Travelling around the world", "Trees and us",
        "Our animal friends", "Water", "Electricity", "Poems",
        "From hobby to career",
    ],
    (8, "first"): [
        "Look it up!", "Amazing numbers", "Our digital lives", "Inventions",
        "Going on an exchange trip", "Wisdom counts", "The secret of memory",
        "Pets and us",
    ],
    (8, "second"): [
        "Helping those in need", "Body language", "Comics and animation",
        "Arts and heritage", "Saving animals in danger", "Learning by doing",
        "Space exploration", "Imagine that!",
    ],
    (9, "first"): [
        "Great people", "Great ideas", "Family traditions", "A better me",
        "My time, my joy", "Food and health", "Reading Mark Twain",
        "The power of love",
    ],
}

# 9 下：上教版新教材九年级下册预计 2027 春发布，当前无官方目录。
# 现存的 6 个旧版（牛津上海版）章节改标占位，禁止再往里挂新知识点。
UNRELEASED_BOOKS: list[tuple[int, str]] = [(9, "second")]

# 道法里游离的非单元 section（旧版残留 / 样章），需要清掉
POLITICS_JUNK_SECTIONS = {"第一课丰富的社会生活", "诚实守信", "样章·道德与法治·观点与材料"}

# 每单元的 4 个知识点骨架（与题型一一对应，组卷按节抽题时不会全落在同一节点）
POINT_SUFFIXES = ["听力与主题词汇", "语法要点", "语篇理解", "词汇填空与表达"]


def _unit_title(index: int, topic: str) -> str:
    return f"Unit {index} {topic}"


def _topic_word(topic: str) -> str:
    """知识点前缀用主题词，避免太长导致 UI 折行。"""
    return topic.strip().rstrip("!")


# ---------------------------------------------------------------------------
# 1) 版本口径
# ---------------------------------------------------------------------------
def fix_versions(db, apply: bool) -> None:
    for subject, version, grade_max, note in (
        ("english", SZ_VERSION_ENGLISH, 9, "1-9 年级"),
        ("politics", SZ_VERSION_POLITICS, 12, "1-9 年级为主"),
    ):
        rows = list(
            db.scalars(
                select(Textbook).where(
                    Textbook.subject == subject,
                    Textbook.grade <= grade_max,
                    Textbook.version != version,
                )
            )
        )
        print(f"[版本] {subject}（{note}）待改 {len(rows)} 册 → {version}")
        for book in rows:
            print(f"   g{book.grade} {book.semester:6s} {book.version} → {version}")
            if apply:
                book.version = version
    # 高中英语（10-12 外研版）、数学（人教版A版）等不属于本次范围，保持原样


# ---------------------------------------------------------------------------
# 2) 英语 7-9：重建章节 + 知识点
# ---------------------------------------------------------------------------
def _english_books(db) -> list[Textbook]:
    return list(
        db.scalars(
            select(Textbook)
            .where(Textbook.subject == "english", Textbook.grade.between(7, 9))
            .order_by(Textbook.grade, Textbook.semester)
        )
    )


def _make_section(db, grade: int, idx: int, topic: str) -> int:
    """建 section（= 一个单元）及其 4 个 point，返回 section id。"""
    section = KnowledgePoint(
        subject="english",
        name=_unit_title(idx, topic),
        parent_id=None,
        grade=grade,
        node_type="section",
        order_index=idx,
        source_type="original",
        source_name="自建知识点体系（原创）",
        license_note="原创自建内容，不含第三方版权素材",
    )
    db.add(section)
    db.flush()
    for pos, suffix in enumerate(POINT_SUFFIXES, start=1):
        db.add(
            KnowledgePoint(
                subject="english",
                name=f"{_topic_word(topic)} {suffix}",
                parent_id=section.id,
                grade=grade,
                node_type="point",
                order_index=pos,
                source_type="original",
                source_name="自建知识点体系（原创）",
                license_note="原创自建内容，不含第三方版权素材",
            )
        )
    return section.id


def rebuild_english(db, apply: bool) -> None:
    """按年级整体重建：章节、知识点、题目、试卷四者必须同源，否则快照对不上。

    幂等：重复执行会把该年级英语的章节/知识点/题/卷整体清掉再按目录重建。
    """
    books = _english_books(db)
    by_grade: dict[int, list[Textbook]] = {}
    for book in books:
        by_grade.setdefault(book.grade, []).append(book)

    for grade, grade_books in sorted(by_grade.items()):
        book_ids = [b.id for b in grade_books]
        chapters = list(
            db.scalars(select(Chapter).where(Chapter.textbook_id.in_(book_ids)))
        )
        chapter_ids = [c.id for c in chapters]
        q_count = 0
        if chapter_ids:
            q_count = db.execute(
                select(func.count(Question.id)).where(Question.chapter_id.in_(chapter_ids))
            ).scalar_one()
        exam_rows = list(
            db.scalars(
                select(Exam).where(
                    Exam.subject == "english",
                    Exam.grade == grade,
                    Exam.class_id.is_(None),
                )
            )
        )

        plan = [(b, SZ_ENGLISH_UNITS.get((grade, b.semester))) for b in grade_books]
        desc = " / ".join(
            f"{b.semester}:{len(u) if u else '未发布→占位'}" for b, u in plan
        )
        print(
            f"[英语] g{grade} 旧章节 {len(chapters)} / 旧题 {q_count} / 旧卷 {len(exam_rows)} "
            f"→ {desc}"
        )
        if not apply:
            continue

        # 1) 先删卷（快照引用旧题 id），再删题、删章节
        for exam in exam_rows:
            db.delete(exam)
        if chapter_ids:
            db.execute(delete(Question).where(Question.chapter_id.in_(chapter_ids)))
        for c in chapters:
            db.delete(c)
        db.flush()

        # 2) 删该年级英语全部知识点（先断题目引用，再子后父）
        all_kps = list(
            db.scalars(
                select(KnowledgePoint).where(
                    KnowledgePoint.subject == "english",
                    KnowledgePoint.grade == grade,
                )
            )
        )
        if all_kps:
            kp_ids = [k.id for k in all_kps]
            db.execute(
                update(Question)
                .where(Question.knowledge_point_id.in_(kp_ids))
                .values(knowledge_point_id=None)
            )
            child_ids = [k.id for k in all_kps if k.parent_id is not None]
            parent_ids = [k.id for k in all_kps if k.parent_id is None]
            if child_ids:
                db.execute(delete(KnowledgePoint).where(KnowledgePoint.id.in_(child_ids)))
            db.flush()
            if parent_ids:
                db.execute(delete(KnowledgePoint).where(KnowledgePoint.id.in_(parent_ids)))
            db.flush()

        # 3) 按册重建章节 + 单元 section/point
        built = 0
        for book, units in plan:
            if not units:
                # 未发布册：留一条占位章节，防止误挂内容
                db.add(
                    Chapter(
                        textbook_id=book.id,
                        grade=grade,
                        name="待发布·上教版新教材九年级下册",
                        order_index=1,
                        summary="上教版新教材九年级下册预计 2027 春发布，暂无官方目录",
                        is_placeholder=1,
                        placeholder_note=(
                            "上教版新教材九年级下册预计 2027 春发布，官方目录未公布，"
                            "禁止挂知识点与题目"
                        ),
                    )
                )
                db.flush()
                continue
            for idx, topic in enumerate(units, start=1):
                db.add(
                    Chapter(
                        textbook_id=book.id,
                        grade=grade,
                        name=_unit_title(idx, topic),
                        order_index=idx,
                        summary=(
                            f"上教版（沪教牛津深圳版）{grade} 年级"
                            f"{'上' if book.semester == 'first' else '下'}册 Unit {idx}"
                        ),
                        is_placeholder=0,
                    )
                )
                db.flush()
                _make_section(db, grade, idx, topic)
                built += 1
        db.flush()
        print(f"   已重建 {built} 个单元（章节 + section + 4 point/单元）")


# ---------------------------------------------------------------------------
# 3) 英语：把按单元生成的题挂到对应单元知识点（题型 → 第 N 个 point）
# ---------------------------------------------------------------------------
KIND_TO_POINT_ORDER = {"listening": 1, "grammar": 2, "reading": 3, "fill": 4}


def bind_english_points(db, apply: bool) -> None:
    total = 0
    for grade in (7, 8, 9):
        chapters = list(
            db.scalars(
                select(Chapter)
                .join(Textbook, Chapter.textbook_id == Textbook.id)
                .where(
                    Textbook.subject == "english",
                    Textbook.grade == grade,
                    Chapter.is_placeholder == 0,
                )
            )
        )
        for chapter in chapters:
            section = db.scalar(
                select(KnowledgePoint).where(
                    KnowledgePoint.subject == "english",
                    KnowledgePoint.grade == grade,
                    KnowledgePoint.node_type == "section",
                    KnowledgePoint.name == chapter.name,
                )
            )
            if section is None:
                continue
            points = list(
                db.scalars(
                    select(KnowledgePoint)
                    .where(KnowledgePoint.parent_id == section.id)
                    .order_by(KnowledgePoint.order_index)
                )
            )
            if len(points) < 4:
                continue
            qs = list(
                db.scalars(
                    select(Question).where(
                        Question.chapter_id == chapter.id,
                        Question.source_ref.like("selfbank:en_u:%"),
                    )
                )
            )
            for q in qs:
                is_reading = (q.content or {}).get("section_hint") == "reading"
                if is_reading:
                    kind = "reading"
                else:
                    kind = next(
                        (k for k in ("listening", "grammar", "fill") if k in (q.tags or [])),
                        None,
                    )
                if kind is None:
                    continue
                order = KIND_TO_POINT_ORDER[kind]
                if apply:
                    q.knowledge_point_id = points[order - 1].id
                total += 1
    print(f"[绑定] 英语题 → 单元知识点 {total} 题")


# ---------------------------------------------------------------------------
# 4) 道法：版本改名 + 清理杂项 section
# ---------------------------------------------------------------------------
def rebuild_politics(db, apply: bool) -> None:
    junk = list(
        db.scalars(
            select(KnowledgePoint).where(
                KnowledgePoint.subject == "politics",
                KnowledgePoint.node_type == "section",
                KnowledgePoint.name.in_(POLITICS_JUNK_SECTIONS),
            )
        )
    )
    print(f"[道法] 待清理游离 section {len(junk)} 个：{[k.name for k in junk]}")
    if apply and junk:
        ids = [k.id for k in junk]
        # 其下 point 一并清掉，并解除题目引用
        children = list(
            db.scalars(select(KnowledgePoint).where(KnowledgePoint.parent_id.in_(ids)))
        )
        child_ids = [c.id for c in children]
        all_ids = ids + child_ids
        db.execute(
            update(Question)
            .where(Question.knowledge_point_id.in_(all_ids))
            .values(knowledge_point_id=None)
        )
        for child in children:
            db.delete(child)
        db.flush()
        for parent in junk:
            db.delete(parent)
        db.flush()

    # 章节名规范化：补齐「单元」后的空格
    fixes = 0
    for chapter in db.scalars(
        select(Chapter).join(Textbook, Chapter.textbook_id == Textbook.id).where(
            Textbook.subject == "politics", Textbook.grade.between(7, 9)
        )
    ):
        if "单元" in chapter.name and "单元 " not in chapter.name:
            new = chapter.name.replace("单元", "单元 ", 1).strip()
            print(f"   章节名规范：{chapter.name} → {new}")
            if apply:
                chapter.name = new
            fixes += 1
    print(f"[道法] 章节名规范化 {fixes} 处")


# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description="按深圳教材版本对齐 7-9 英语/道法")
    parser.add_argument("--dry-run", action="store_true", help="只打印计划")
    parser.add_argument("--apply-versions", action="store_true")
    parser.add_argument("--apply-english", action="store_true")
    parser.add_argument("--apply-politics", action="store_true")
    parser.add_argument("--bind-points", action="store_true", help="把英语题挂到单元知识点")
    args = parser.parse_args()

    apply_any = (
        args.apply_versions or args.apply_english or args.apply_politics or args.bind_points
    )
    dry_run = args.dry_run or not apply_any

    with SessionLocal() as db:
        fix_versions(db, args.apply_versions)
        rebuild_english(db, args.apply_english)
        bind_english_points(db, args.bind_points)
        rebuild_politics(db, args.apply_politics)
        if dry_run:
            db.rollback()
            print("\n干跑完成，未写入。")
        else:
            db.commit()
            print("\n已提交。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
