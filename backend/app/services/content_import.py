"""题库 / 知识库 JSON 导入（供教研手动补题使用）。

模板见 `docs/content-templates/`，导入命令：
    python -m scripts.import_content --path ..\\docs\\content-templates\\math.json
    python -m scripts.import_content --path ..\\docs\\content-templates --dry-run

约定：
- 以教材（subject + grade + version + semester）为作用域，幂等导入；
- 知识点按「节(section) → 点(point)」两级，父节点用名称引用；
- 题目按「章节名 + 知识点名」挂载，同一章节同一题干同题型默认跳过，`--overwrite` 时覆盖；
- 校验失败直接抛 `ValueError`，不写库。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.content import Chapter, KnowledgePoint, Question, Textbook

SUBJECTS = {
    "chinese": "语文",
    "math": "数学",
    "english": "英语",
    "physics": "物理",
    "chemistry": "化学",
    "biology": "生物",
    "history": "历史",
    "geography": "地理",
    "politics": "道德与法治",
}
Q_TYPES = {"choice", "multiple", "judge", "fill", "answer"}
OPTION_REQUIRED = {"choice", "multiple"}
SEMESTERS = {"first", "second"}
MAX_DIFFICULTY = 5
SOURCE_TYPES = {"original", "adapted", "licensed", "public", "external"}


def load_document(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path.name}: 顶层必须是 JSON 对象")
    validate_document(data)
    return data


def validate_document(data: dict[str, Any]) -> None:
    subject = data.get("subject")
    if subject not in SUBJECTS:
        raise ValueError(f"subject 必须是 {sorted(SUBJECTS)} 之一，当前为 {subject!r}")
    grade = data.get("grade")
    if not isinstance(grade, int) or not 1 <= grade <= 12:
        raise ValueError("grade 必须是 1~12 的整数")
    if not str(data.get("version") or "").strip():
        raise ValueError("version（教材版本）不能为空")
    if data.get("semester", "first") not in SEMESTERS:
        raise ValueError("semester 只能是 first 或 second")

    knowledge = data.get("knowledge") or []
    if not isinstance(knowledge, list):
        raise ValueError("knowledge 必须是数组")
    chapters = data.get("chapters") or []
    if not isinstance(chapters, list):
        raise ValueError("chapters 必须是数组")
    if not knowledge and not chapters:
        raise ValueError("knowledge 与 chapters 不能同时为空")
    section_names: set[str] = set()
    point_names: set[str] = set()
    for item in knowledge:
        name = str(item.get("name") or "").strip()
        if not name:
            raise ValueError("knowledge 中存在空名称")
        _validate_source(item, f"知识点「{name}」", allow_adapted_from=False)
        node_type = item.get("node_type", "point")
        if node_type not in {"section", "point"}:
            raise ValueError(f"知识点「{name}」node_type 只能是 section 或 point")
        if node_type == "section":
            if name in section_names:
                raise ValueError(f"节名称重复：{name}")
            section_names.add(name)
        else:
            if name in point_names:
                raise ValueError(f"知识点名称重复：{name}")
            point_names.add(name)
            parent = str(item.get("parent") or "").strip()
            if not parent:
                raise ValueError(f"知识点「{name}」缺少 parent（所属节）")
    for item in knowledge:
        if item.get("node_type", "point") == "point":
            parent = str(item.get("parent") or "").strip()
            if parent not in section_names:
                raise ValueError(f"知识点「{item.get('name')}」的 parent「{parent}」未在同文件 knowledge 中定义")

    chapter_names: set[str] = set()
    for chapter in chapters:
        chapter_name = str(chapter.get("name") or "").strip()
        if not chapter_name:
            raise ValueError("chapters 中存在空名称")
        if chapter_name in chapter_names:
            raise ValueError(f"章节名称重复：{chapter_name}")
        chapter_names.add(chapter_name)
        questions = chapter.get("questions") or []
        if not isinstance(questions, list):
            raise ValueError(f"章节「{chapter_name}」questions 必须是数组")
        for question in questions:
            _validate_question(question, chapter_name)


def _validate_question(question: dict[str, Any], chapter_name: str) -> None:
    q_type = question.get("q_type")
    if q_type not in Q_TYPES:
        raise ValueError(f"章节「{chapter_name}」题目题型非法：{q_type!r}，可选 {sorted(Q_TYPES)}")
    stem = str(question.get("stem") or "").strip()
    if not stem:
        raise ValueError(f"章节「{chapter_name}」存在空题干")
    answer = question.get("answer")
    if not isinstance(answer, dict) or answer.get("value") in (None, ""):
        raise ValueError(f"题目「{stem}」缺少 answer.value")
    if q_type in ("choice", "multiple"):
        options = question.get("options") or []
        keys = []
        for index, option in enumerate(options):
            if isinstance(option, dict):
                key = str(option.get("key") or "").strip()
                text = str(option.get("text") or "").strip()
            else:
                key, text = chr(ord("A") + index), str(option).strip()
            if not key or not text:
                raise ValueError(f"题目「{stem}」选项需包含 key 与 text")
            keys.append(key)
        if len(keys) < 2 or len(set(keys)) != len(keys):
            raise ValueError(f"题目「{stem}」至少需要 2 个不重复选项")
        value = answer.get("value")
        picked = value if isinstance(value, list) else [value]
        if q_type == "choice" and isinstance(value, list):
            raise ValueError(f"题目「{stem}」单选题 answer.value 不能是列表，多选请用 multiple")
        if q_type == "multiple" and not isinstance(value, list):
            raise ValueError(f"题目「{stem}」多选题 answer.value 必须是列表")
        unknown = [str(item) for item in picked if str(item) not in keys]
        if unknown:
            raise ValueError(f"题目「{stem}」答案 {unknown} 不在选项 {keys} 中")
    if q_type == "judge":
        value = str(answer.get("value"))
        if value not in {"T", "F"}:
            raise ValueError(f"题目「{stem}」判断题 answer.value 只能是 T 或 F")
    difficulty = question.get("difficulty", 2)
    if not isinstance(difficulty, int) or not 1 <= difficulty <= MAX_DIFFICULTY:
        raise ValueError(f"题目「{stem}」difficulty 必须是 1~{MAX_DIFFICULTY}")
    _validate_source(
        question,
        f"题目「{stem}」",
        status=str(question.get("status", "published")),
    )


def _validate_source(
    item: dict[str, Any],
    label: str,
    *,
    status: str | None = None,
    allow_adapted_from: bool = True,
) -> None:
    """来源字段校验：非原创必须可溯源，授权必须写授权说明，外部导入必须待审。"""
    source_type = item.get("source_type", "original")
    if source_type not in SOURCE_TYPES:
        raise ValueError(
            f"{label}的 source_type 非法：{source_type!r}，可选 {sorted(SOURCE_TYPES)}"
        )
    if source_type != "original" and not str(item.get("source_name") or "").strip():
        raise ValueError(f"{label}的 source_type 为 {source_type}，必须填写 source_name")
    if source_type == "licensed" and not str(item.get("license_note") or "").strip():
        raise ValueError(
            f"{label}的 source_type 为 licensed，必须填写 license_note（授权说明或协议编号）"
        )
    if (
        allow_adapted_from
        and source_type == "adapted"
        and not str(item.get("adapted_from") or "").strip()
    ):
        raise ValueError(f"{label}的 source_type 为 adapted，必须填写 adapted_from")
    if source_type == "external" and status is not None and status != "draft":
        raise ValueError(f"{label}为外部导入（external），status 必须为 draft，复核后再发布")


def import_document(db: Session, data: dict[str, Any], *, overwrite: bool = False) -> dict[str, int]:
    """导入一份模板数据；调用方负责 commit/rollback。"""
    validate_document(data)
    subject = data["subject"]
    grade = data["grade"]
    version = str(data["version"]).strip()
    semester = data.get("semester", "first")

    textbook = db.scalar(
        select(Textbook).where(
            Textbook.subject == subject,
            Textbook.grade == grade,
            Textbook.version == version,
            Textbook.semester == semester,
        )
    )
    textbook_created = textbook is None
    if textbook is None:
        textbook = Textbook(
            subject=subject, grade=grade, version=version, semester=semester
        )
        db.add(textbook)
        db.flush()

    chapter_map: dict[str, Chapter] = {}
    chapters_created = 0
    chapters_updated = 0
    for chapter in data["chapters"]:
        name = str(chapter["name"]).strip()
        row = db.scalar(
            select(Chapter).where(
                Chapter.textbook_id == textbook.id, Chapter.name == name
            )
        )
        if row is None:
            row = Chapter(
                textbook_id=textbook.id,
                grade=grade,
                name=name,
                order_index=int(chapter.get("order_index", 0)),
                summary=chapter.get("summary"),
            )
            db.add(row)
            chapters_created += 1
        else:
            row.order_index = int(chapter.get("order_index", row.order_index))
            if chapter.get("summary"):
                row.summary = chapter["summary"]
            chapters_updated += 1
        chapter_map[name] = row
    db.flush()

    section_map: dict[str, KnowledgePoint] = {}
    point_map: dict[str, KnowledgePoint] = {}
    taken_names = set(
        db.scalars(
            select(KnowledgePoint.name).where(
                KnowledgePoint.subject == subject,
                KnowledgePoint.grade == grade,
            )
        )
    )
    kp_created = 0
    kp_updated = 0
    for item in data["knowledge"]:
        node_type = item.get("node_type", "point")
        item_name = item["name"]
        if node_type == "section":
            row = db.scalar(
                select(KnowledgePoint).where(
                    KnowledgePoint.subject == subject,
                    KnowledgePoint.grade == grade,
                    KnowledgePoint.node_type == "section",
                    KnowledgePoint.parent_id.is_(None),
                    KnowledgePoint.name == item["name"],
                )
            )
        else:
            parent = section_map[str(item["parent"]).strip()]
            row = db.scalar(
                select(KnowledgePoint).where(
                    KnowledgePoint.parent_id == parent.id,
                    KnowledgePoint.name == item_name,
                )
            )
            if row is None and item_name in taken_names:
                # 与库内 section/point 重名时给 point 加「（要点）」后缀，
                # 保证同学科同年级内名称唯一，题目仍可按模板原名挂载。
                index = 0
                while True:
                    index += 1
                    candidate = (
                        f"{item_name}（要点）"
                        if index == 1
                        else f"{item_name}（要点{index}）"
                    )
                    found = db.scalar(
                        select(KnowledgePoint).where(
                            KnowledgePoint.parent_id == parent.id,
                            KnowledgePoint.name == candidate,
                        )
                    )
                    if found is not None:
                        row = found
                        item_name = candidate
                        break
                    if candidate not in taken_names:
                        item_name = candidate
                        break
        if row is None:
            row = KnowledgePoint(
                subject=subject,
                grade=grade,
                name=item_name,
                parent_id=None if node_type == "section" else section_map[item["parent"]].id,
                node_type=node_type,
                order_index=int(item.get("order_index", 0)),
                weight=float(item.get("weight", 1.0)),
                explanation=item.get("explanation"),
            )
            _apply_source(row, item)
            db.add(row)
            db.flush()
            kp_created += 1
        else:
            row.order_index = int(item.get("order_index", row.order_index))
            row.weight = float(item.get("weight", row.weight))
            if item.get("explanation"):
                row.explanation = item["explanation"]
            for field in (
                "source_type",
                "source_name",
                "source_ref",
                "copyright_owner",
                "license_note",
            ):
                if field in item:
                    setattr(row, field, item[field])
            kp_updated += 1
        taken_names.add(row.name)
        if node_type == "section":
            section_map[item["name"]] = row
        else:
            point_map[item["name"]] = row

    # 前置知识按名称回填（仅解析本文件内引用）
    for item in data["knowledge"]:
        if item.get("node_type", "point") != "point":
            continue
        names = [str(name).strip() for name in item.get("prerequisites") or []]
        if not names:
            continue
        ids: list[int] = []
        for name in names:
            target = point_map.get(name) or section_map.get(name)
            if target is None:
                raise ValueError(
                    f"知识点「{item['name']}」的前置知识「{name}」未在同文件 knowledge 中定义"
                )
            ids.append(target.id)
        point_map[item["name"]].prerequisites = ids

    questions_created = 0
    questions_skipped = 0
    for chapter_data in data["chapters"]:
        chapter = chapter_map[str(chapter_data["name"]).strip()]
        existing_rows = list(
            db.scalars(select(Question).where(Question.chapter_id == chapter.id))
        )
        for question in chapter_data.get("questions") or []:
            kp_name = str(question.get("knowledge_point") or "").strip()
            kp = point_map.get(kp_name) or section_map.get(kp_name)
            if kp is None:
                candidates = list(
                    db.scalars(
                        select(KnowledgePoint).where(
                            KnowledgePoint.subject == subject,
                            KnowledgePoint.grade == grade,
                            KnowledgePoint.name == kp_name,
                        )
                    )
                )
                if len(candidates) > 1:
                    raise ValueError(
                        f"题目「{question['stem']}」引用的知识点「{kp_name}」在库中有多个同名节点，"
                        "请在模板 knowledge 中显式定义并保持名称唯一"
                    )
                kp = candidates[0] if candidates else None
            if kp is None:
                raise ValueError(f"题目「{question['stem']}」引用的知识点「{kp_name}」不存在")
            stem = str(question["stem"]).strip()
            duplicate = next(
                (
                    row
                    for row in existing_rows
                    if row.q_type == question["q_type"]
                    and str((row.content or {}).get("stem", "")).strip() == stem
                ),
                None,
            )
            if duplicate is not None:
                if overwrite:
                    _fill_question(duplicate, question, subject, chapter.id, kp.id)
                questions_skipped += 1
                continue
            row = Question(
                chapter_id=chapter.id,
                knowledge_point_id=kp.id,
                subject=subject,
                q_type=question["q_type"],
                status=question.get("status", "published"),
            )
            _fill_question(row, question, subject, chapter.id, kp.id)
            db.add(row)
            existing_rows.append(row)
            questions_created += 1
    db.flush()
    return {
        "textbook_created": int(textbook_created),
        "chapters_created": chapters_created,
        "chapters_updated": chapters_updated,
        "knowledge_created": kp_created,
        "knowledge_updated": kp_updated,
        "questions_created": questions_created,
        "questions_skipped": questions_skipped,
    }


def _fill_question(
    row: Question,
    question: dict[str, Any],
    subject: str,
    chapter_id: int,
    kp_id: int,
) -> None:
    q_type = question["q_type"]
    options = question.get("options") or []
    if q_type == "judge" and not options:
        options = [{"key": "T", "text": "正确"}, {"key": "F", "text": "错误"}]
    row.q_type = q_type
    row.content = {"stem": str(question["stem"]).strip()}
    row.options = _normalize_options(options)
    row.answer = {"value": question["answer"]["value"]}
    row.analysis = question.get("analysis")
    row.difficulty = int(question.get("difficulty", 2))
    row.tags = question.get("tags") or []
    row.status = question.get("status", "published")
    _apply_source(row, question, include_adapted_from=True)
    row.subject = subject
    row.chapter_id = chapter_id
    row.knowledge_point_id = kp_id


def _apply_source(
    row: Question | KnowledgePoint,
    item: dict[str, Any],
    *,
    include_adapted_from: bool = False,
) -> None:
    row.source_type = item.get("source_type", "original")
    row.source_name = item.get("source_name")
    row.source_ref = item.get("source_ref")
    row.copyright_owner = item.get("copyright_owner")
    row.license_note = item.get("license_note")
    if include_adapted_from:
        row.adapted_from = item.get("adapted_from")


def _normalize_options(options: list[Any]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for index, option in enumerate(options):
        if isinstance(option, dict):
            normalized.append(
                {"key": str(option["key"]).strip(), "text": str(option["text"]).strip()}
            )
        else:
            normalized.append(
                {"key": chr(ord("A") + index), "text": str(option).strip()}
            )
    return normalized
