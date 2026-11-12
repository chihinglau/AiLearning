"""整册离线 bundle：一次性下发教材目录、知识点与含答案解析的题库。"""

import hashlib
import json
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.content import Chapter, KnowledgePoint, Question, Textbook
from app.schemas.learn import (
    BundleCountsOut,
    KpBriefOut,
    KpDetailOut,
    KnowledgeNodeOut,
    QuestionBundleOut,
    TextbookBundleOut,
    UnitDetailOut,
    UnitOut,
    UnitSectionOut,
)
from app.services import learning as engine


class BundleTooLarge(Exception):
    """整册内容超过配置上限。"""


def _chapter_kp_counts(
    db: Session, chapter_ids: list[int]
) -> dict[int, dict[int, int]]:
    if not chapter_ids:
        return {}
    rows = db.execute(
        select(
            Question.chapter_id,
            Question.knowledge_point_id,
            func.count(Question.id),
        )
        .where(
            Question.chapter_id.in_(chapter_ids),
            Question.knowledge_point_id.is_not(None),
            Question.status == "published",
        )
        .group_by(Question.chapter_id, Question.knowledge_point_id)
    ).all()
    agg: dict[int, dict[int, int]] = {}
    for chapter_id, kp_id, count in rows:
        agg.setdefault(int(chapter_id), {})[int(kp_id)] = int(count)
    return agg


def _unit_out(chapter: Chapter, kps: dict[int, KnowledgePoint], counts: dict[int, int]) -> UnitOut:
    kp_ids = list(counts)
    parents = {kps[kp_id].parent_id for kp_id in kp_ids if kps[kp_id].parent_id}
    return UnitOut(
        id=chapter.id,
        textbook_id=chapter.textbook_id,
        grade=chapter.grade,
        name=chapter.name,
        order_index=chapter.order_index,
        summary=chapter.summary,
        section_count=len(parents),
        kp_count=len(kp_ids),
        question_count=sum(counts.values()),
        avg_mastery=0.0,
        mastery_band=engine.mastery_band(0.0),
        learned_kp_count=0,
        progress=0.0,
    )


def _node(kp: KnowledgePoint, question_count: int) -> KnowledgeNodeOut:
    node = KnowledgeNodeOut.model_validate(kp)
    node.mastery_score = 0.0
    node.mastery_confidence = 0
    node.mastery_band = engine.mastery_band(0.0)
    node.question_count = question_count
    node.state = engine.derive_study_state(
        mastery=0.0, attempted=False, due_review=False
    )
    node.last_studied_at = None
    return node


def _ordered_prerequisites(
    kp: KnowledgePoint,
    pool: dict[int, KnowledgePoint],
    sections: dict[int, KnowledgePoint],
) -> list[KnowledgePoint]:
    """只取该知识点自己声明的前置，并按教材顺序（节 → KP → 声明顺序）排列。

    修复：此前把整册所有前置知识点都塞进每一个详情，离线包里前置列表
    既乱序又超长；线上 /learn/kp/{id} 的排序口径与此保持一致。
    """
    ids = list(kp.prerequisites or [])
    position = {pid: index for index, pid in enumerate(ids)}
    rows = [pool[pid] for pid in ids if pid in pool]
    return sorted(
        rows,
        key=lambda item: (
            sections[item.parent_id].order_index
            if item.parent_id in sections
            else 10**9,
            item.order_index,
            position.get(item.id, 10**9),
        ),
    )


def _kp_detail(
    kp: KnowledgePoint,
    *,
    question_count: int,
    sections: dict[int, KnowledgePoint],
    prerequisites: list[KnowledgePoint],
) -> KpDetailOut:
    section = sections.get(kp.parent_id) if kp.parent_id else None
    return KpDetailOut(
        id=kp.id,
        subject=kp.subject,
        grade=kp.grade,
        name=kp.name,
        node_type=kp.node_type,
        explanation=kp.explanation,
        section_id=section.id if section else None,
        section_name=section.name if section else None,
        prerequisites=[
            KpBriefOut(
                id=item.id,
                name=item.name,
                subject=item.subject,
                order_index=item.order_index,
                section_order=(
                    sections[item.parent_id].order_index
                    if item.parent_id in sections
                    else 0
                ),
                section_name=(
                    sections[item.parent_id].name
                    if item.parent_id in sections
                    else None
                ),
                has_explanation=bool((item.explanation or "").strip()),
            )
            for item in prerequisites
        ],
        mastery_score=0.0,
        mastery_confidence=0,
        mastery_band=engine.mastery_band(0.0),
        question_count=question_count,
        state=engine.derive_study_state(
            mastery=0.0, attempted=False, due_review=False
        ),
        state_evidence=0,
        last_studied_at=None,
    )


def build_textbook_bundle(db: Session, textbook_id: int) -> TextbookBundleOut:
    textbook = db.get(Textbook, textbook_id)
    if textbook is None:
        raise LookupError("教材不存在")

    chapters = list(
        db.scalars(
            select(Chapter)
            .where(
                Chapter.textbook_id == textbook_id,
                Chapter.is_placeholder == 0,  # 占位/旧样章不进教材目录视图
            )
            .order_by(Chapter.order_index, Chapter.id)
        )
    )
    chapter_ids = [chapter.id for chapter in chapters]
    counts_by_chapter = _chapter_kp_counts(db, chapter_ids)
    all_kp_ids = sorted(
        {kp_id for counts in counts_by_chapter.values() for kp_id in counts}
    )

    kps = {
        kp.id: kp
        for kp in db.scalars(
            select(KnowledgePoint).where(KnowledgePoint.id.in_(all_kp_ids))
        )
    } if all_kp_ids else {}

    parent_ids = sorted({kp.parent_id for kp in kps.values() if kp.parent_id})
    section_kps = {
        kp.id: kp
        for kp in db.scalars(
            select(KnowledgePoint).where(KnowledgePoint.id.in_(parent_ids))
        )
    } if parent_ids else {}

    prerequisite_ids = sorted(
        {
            int(pid)
            for kp in list(kps.values()) + list(section_kps.values())
            for pid in (kp.prerequisites or [])
        }
    )
    prerequisite_kps = {
        kp.id: kp
        for kp in db.scalars(
            select(KnowledgePoint).where(KnowledgePoint.id.in_(prerequisite_ids))
        )
    } if prerequisite_ids else {}

    # 全量已发布题库（含答案与解析），按章节归属过滤。
    question_rows = list(
        db.scalars(
            select(Question)
            .where(
                Question.chapter_id.in_(chapter_ids),
                Question.status == "published",
            )
            .order_by(Question.id)
        )
    ) if chapter_ids else []
    question_count_by_kp: dict[int, int] = {}
    for counts in counts_by_chapter.values():
        for kp_id, count in counts.items():
            question_count_by_kp[kp_id] = question_count_by_kp.get(kp_id, 0) + count

    units = [
        _unit_out(chapter, kps, counts_by_chapter.get(chapter.id, {}))
        for chapter in chapters
    ]

    unit_details: dict[str, UnitDetailOut] = {}
    for chapter in chapters:
        counts = counts_by_chapter.get(chapter.id, {})
        nodes = [
            _node(kp, counts.get(kp.id, 0)) for kp in kps.values()
            if kp.id in counts
        ]
        nodes.sort(key=lambda node: (node.order_index, node.id))

        chapter_parent_ids = sorted({n.parent_id for n in nodes if n.parent_id})
        sections: list[UnitSectionOut] = []
        for parent_id in chapter_parent_ids:
            parent = section_kps.get(parent_id)
            if parent is None:
                continue
            children = [n for n in nodes if n.parent_id == parent_id]
            sections.append(
                UnitSectionOut(
                    id=parent.id,
                    name=parent.name,
                    order_index=parent.order_index,
                    kp_count=len(children),
                    avg_mastery=0.0,
                    mastery_band=engine.mastery_band(0.0),
                )
            )
        sections.sort(key=lambda item: (item.order_index, item.id))

        unit_details[str(chapter.id)] = UnitDetailOut(
            unit=_unit_out(chapter, kps, counts),
            sections=sections,
            knowledge_points=nodes,
        )

    all_details = {**kps, **section_kps, **prerequisite_kps}
    detail_sections = {**section_kps, **prerequisite_kps}
    kp_details = {
        str(kp_id): _kp_detail(
            kp,
            question_count=question_count_by_kp.get(kp_id, 0),
            sections=detail_sections,
            prerequisites=_ordered_prerequisites(kp, prerequisite_kps, detail_sections),
        )
        for kp_id, kp in all_details.items()
    }

    questions = [
        QuestionBundleOut(
            id=row.id,
            chapter_id=row.chapter_id,
            knowledge_point_id=row.knowledge_point_id,
            subject=row.subject,
            q_type=row.q_type,
            content=row.content or {},
            options=row.options,
            answer=row.answer or {},
            analysis=row.analysis,
            difficulty=row.difficulty,
            tags=row.tags,
        )
        for row in question_rows
    ]

    if len(questions) > settings.bundle_max_questions:
        raise BundleTooLarge(
            f"该教材题目数量 {len(questions)} 超过上限 "
            f"{settings.bundle_max_questions}"
        )

    generated_at = datetime.utcnow()
    bundle = TextbookBundleOut(
        textbook={
            "id": textbook.id,
            "name": f"{textbook.subject} · {textbook.version}",
            "subject": textbook.subject,
            "grade": textbook.grade,
            "version": textbook.version,
            "semester": textbook.semester,
        },
        units=units,
        unit_details=unit_details,
        kp_details=kp_details,
        questions=questions,
        counts=BundleCountsOut(
            units=len(units),
            knowledge_points=len(kp_details),
            questions=len(questions),
        ),
        pack_version="",
        generated_at=generated_at,
    )
    payload = bundle.model_dump(mode="json", exclude={"generated_at", "pack_version"})
    digest = hashlib.sha1(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    bundle.pack_version = digest

    size = len(
        json.dumps(
            bundle.model_dump(mode="json"), ensure_ascii=False
        ).encode("utf-8")
    )
    if size > settings.bundle_max_bytes:
        raise BundleTooLarge(
            f"该教材离线包体积 {size} 字节超过上限 {settings.bundle_max_bytes}"
        )
    return bundle
