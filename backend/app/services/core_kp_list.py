"""期末卷「必考核心考点清单」。

一张期末卷只能放 25-28 题，一册却有 40-66 个知识点——按「覆盖全部知识点」衡量
期末卷，数学上不可能达标（要 0.8 得数学 47-53 题、语文 38 题、英语 54 题，远超
小学期末卷的合理长度）。所以改用教研口径：每册先定一份核心考点清单（默认 18 个），
期末卷只要覆盖这份清单即可达标。

清单的三条选取规则：
    1. 只看真实章节（is_placeholder=0），占位/旧样章一律不进；
    2. 先保证「每章至少 1 个代表考点」（该章题量最多的那个），再按全册题量降序
       补齐到 limit——章节维度不漏，数量又受卷面题量约束；
    3. 同一考点家族（去掉「·变式N」「（要点）」后缀）只占一个名额。变式一~四
       本质是同一个考点，各占名额会把清单稀释掉。

知识点表没有 chapter_id，章节归属只能由「该章题目挂的 KP」反推。这在数学/英语
上基本准确（题按单元建），在语文上会出现「同一 KP 横跨所有章节」的情况——所以
阶段一必须按 family 去重，否则每章都会选出同一个 KP。
"""

from __future__ import annotations

import re

from sqlalchemy import func, select

from app.models.content import Chapter, KnowledgePoint, Question, Textbook

CORE_LIMIT = 18

_VARIANT_SUFFIX = re.compile(r"·变式[一二三四五六七八九十\d]+$")
_POINT_SUFFIX = re.compile(r"（要点）$")


def family_of(name: str) -> str:
    """考点家族名：去掉「·变式N」与「（要点）」后缀。"""
    text = _VARIANT_SUFFIX.sub("", name or "")
    text = _POINT_SUFFIX.sub("", text)
    return text.strip()


def _kp_pool(db, chapter_ids: list[int]):
    """返回 (KP 总题量, 章节->{KP: 题量}, KP->主章节与题量, KP 元信息)。"""
    rows = db.execute(
        select(
            Question.chapter_id,
            Question.knowledge_point_id,
            func.count(Question.id),
        )
        .where(
            Question.chapter_id.in_(chapter_ids),
            Question.knowledge_point_id.isnot(None),
        )
        .group_by(Question.chapter_id, Question.knowledge_point_id)
    ).all()

    total: dict[int, int] = {}
    by_chapter: dict[int, dict[int, int]] = {cid: {} for cid in chapter_ids}
    primary: dict[int, dict] = {}
    for chapter_id, kp_id, count in rows:
        kp_id = int(kp_id)
        chapter_id = int(chapter_id)
        count = int(count)
        total[kp_id] = total.get(kp_id, 0) + count
        by_chapter.setdefault(chapter_id, {})[kp_id] = count
        if kp_id not in primary or count > primary[kp_id]["q_count"]:
            primary[kp_id] = {"chapter_id": chapter_id, "q_count": count}

    kp_ids = list(total.keys()) or [0]
    meta: dict[int, dict] = {}
    for kp in db.scalars(
        select(KnowledgePoint).where(KnowledgePoint.id.in_(kp_ids))
    ).all():
        meta[kp.id] = {"name": kp.name, "order": (kp.order_index or 0, kp.id)}
    return total, by_chapter, primary, meta


def build_core_list(db, textbook: Textbook, limit: int = CORE_LIMIT) -> list[dict]:
    """生成某册的期末必考核心考点清单（按 rank 升序）。"""
    chapters = db.scalars(
        select(Chapter)
        .where(Chapter.textbook_id == textbook.id, Chapter.is_placeholder == 0)
        .order_by(Chapter.order_index, Chapter.id)
    ).all()
    if not chapters:
        return []

    chapter_ids = [c.id for c in chapters]
    chapter_names = {c.id: c.name for c in chapters}
    total, by_chapter, primary, meta = _kp_pool(db, chapter_ids)

    def order_of(kp_id: int) -> tuple:
        return meta.get(kp_id, {}).get("order", (0, kp_id))

    picks: list[tuple[int, int, int]] = []
    seen: set[int] = set()
    seen_family: set[str] = set()

    def add(kp_id: int, chapter_id: int, count: int) -> bool:
        family = family_of(meta.get(kp_id, {}).get("name", ""))
        if kp_id in seen or family in seen_family:
            return False
        picks.append((kp_id, chapter_id, count))
        seen.add(kp_id)
        seen_family.add(family)
        return True

    # 阶段一：每章至少一个代表考点
    for chapter in chapters:
        candidates = sorted(
            by_chapter.get(chapter.id, {}).items(),
            key=lambda pair: (-pair[1], order_of(pair[0])),
        )
        for kp_id, count in candidates:
            if add(kp_id, chapter.id, count):
                break

    # 阶段二：按全册题量补齐到 limit
    rest = sorted(
        (kp_id for kp_id in total if kp_id not in seen),
        key=lambda kp_id: (-total[kp_id], order_of(kp_id)),
    )
    for kp_id in rest:
        if len(picks) >= limit:
            break
        add(kp_id, primary[kp_id]["chapter_id"], total[kp_id])

    return [
        {
            "textbook_id": textbook.id,
            "grade": textbook.grade,
            "subject": textbook.subject,
            "semester": textbook.semester,
            "chapter_id": chapter_id,
            "chapter_name": chapter_names.get(chapter_id, ""),
            "rank": rank,
            "kp_id": kp_id,
            "kp_name": meta.get(kp_id, {}).get("name", ""),
            "q_count": count,
        }
        for rank, (kp_id, chapter_id, count) in enumerate(picks, start=1)
    ]


def core_kps_for_textbook(db, textbook_id: int, limit: int = CORE_LIMIT) -> set[int]:
    textbook = db.get(Textbook, textbook_id)
    if textbook is None:
        return set()
    return {row["kp_id"] for row in build_core_list(db, textbook, limit=limit)}


def core_kps_for_scope(
    db,
    *,
    textbook_id: int,
    chapter_ids: list[int],
    limit: int = CORE_LIMIT,
) -> set[int]:
    """按册出清单，再收敛到本次实际组卷范围内（单元卷只取该单元的核心考点）。"""
    core = core_kps_for_textbook(db, textbook_id, limit=limit)
    if not core:
        return set()
    in_scope = set(
        db.scalars(
            select(Question.knowledge_point_id).where(
                Question.chapter_id.in_(chapter_ids),
                Question.knowledge_point_id.isnot(None),
            )
        ).all()
    )
    return core & in_scope
