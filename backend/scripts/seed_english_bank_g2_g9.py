"""把 g1 英语的题型建设套路推广到 g2–g9：听力 + 客观题 + 阅读理解 + 书面表达。

数据放在同目录的 english_seeds_g2_g9.py，按章节 id 组织，结构：
    chapter_id: (中文话题, [6 个词], [4 个句子], [(问句, 应答), (问句, 应答)])

生成规则（每章 8 听力 + 2 填空 + 2 高区分单选 + 2 阅读 = 14 题）：
    听力：词辨识 ×2、句中关键词 ×2、问句应答 ×2、对话话题 ×2
    填空：句中关键词挖空
    单选：按情景选句（hard 带）
    阅读：两句短文 + 话题/词汇理解各 1 题（medium 带）

用法：
    python scripts/seed_english_bank_g2_g9.py --grades 2 3 --dry-run
    python scripts/seed_english_bank_g2_g9.py --grades 2 3 --apply
"""

from __future__ import annotations

import argparse

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.content import Chapter, Question, Textbook
from scripts.english_seeds_g2_g9 import COMPOSITIONS, SEEDS

SOURCE_NAME = "自建题型题库（原创）"
LICENSE_NOTE = "原创自建内容，不含第三方版权素材"

REPLY_POOL = [
    "I'm fine, thank you.", "It's a book.", "Yes, I do.", "No, I don't.",
    "It's Monday.", "I like apples.", "She is my sister.", "By bus.",
    "At seven o'clock.", "Because it is fun.", "There are five.", "In the park.",
]
TOPIC_POOL = [
    "天气", "运动", "节日", "家庭", "食物", "学校", "动物",
    "旅行", "环保", "职业", "音乐", "科技", "购物", "健康",
]


def _distractors(pool: list[str], correct: str, count: int, start: int) -> list[str]:
    others = [item for item in pool if item != correct]
    if not others:
        return []
    offset = start % len(others)
    rotated = others[offset:] + others[:offset]
    return rotated[:count]


def _choice(correct: str, distractors: list[str], start: int) -> tuple[list[dict], dict]:
    others = [item for item in dict.fromkeys(distractors) if item != correct]
    if others:
        offset = start % len(others)
        others = others[offset:] + others[:offset]
    picked = others[:3]
    if len(picked) < 3:
        for filler in ("以上都不是", "与题目无关", "信息不足"):
            if len(picked) >= 3:
                break
            if filler != correct and filler not in picked:
                picked.append(filler)
    texts = [correct] + picked
    pivot = start % len(texts)
    texts = texts[pivot:] + texts[:pivot]
    keys = "ABCD"
    options = [{"key": keys[i], "text": text} for i, text in enumerate(texts)]
    return options, {"value": keys[texts.index(correct)]}


def _listening(topic_zh: str, words: list[str], sentences: list[str],
               qa: list[tuple[str, str]]) -> list[dict]:
    items: list[dict] = []
    idx = 0
    for word in words[:2]:
        options, answer = _choice(word, _distractors(words, word, 3, idx), idx)
        items.append({
            "stem": "听录音，选出你听到的单词。",
            "script": word, "options": options, "answer": answer,
            "analysis": f"录音朗读的是 {word}，其余为同单元干扰词。",
            "difficulty": 1,
        })
        idx += 1
    for sentence in sentences[:2]:
        key = next((word for word in words if word in sentence), words[0])
        options, answer = _choice(key, _distractors(words, key, 3, idx), idx)
        items.append({
            "stem": "听录音，选出句子中出现的单词。",
            "script": sentence, "options": options, "answer": answer,
            "analysis": f"录音句子为 “{sentence}”，其中含 {key}。",
            "difficulty": 2,
        })
        idx += 1
    for question, reply in qa:
        pool = [r for _, r in qa if r != reply] + REPLY_POOL
        options, answer = _choice(reply, pool, idx)
        items.append({
            "stem": "听录音，选出最合适的应答。",
            "script": question, "options": options, "answer": answer,
            "analysis": f"问句 “{question}” 的合适应答是 “{reply}”。",
            "difficulty": 2,
        })
        idx += 1
    for question, reply in qa:
        options, answer = _choice(topic_zh, TOPIC_POOL, idx)
        items.append({
            "stem": "听对话，选出两人最可能在谈论的内容。",
            "script": f"A: {question} B: {reply}",
            "options": options, "answer": answer,
            "analysis": f"对话关键词落在「{topic_zh}」上。",
            "difficulty": 2,
        })
        idx += 1
    return items


def _extras(topic_zh: str, words: list[str], sentences: list[str],
            situation: str) -> list[dict]:
    items: list[dict] = []
    for sentence in sentences[:2]:
        key = next((word for word in words if word in sentence), words[0])
        blanked = sentence.replace(key, "____", 1)
        items.append({
            "q_type": "fill",
            "stem": f"根据句意补全句子：{blanked}",
            "options": None, "answer": {"value": key},
            "analysis": f"原句为 “{sentence}”，空格处填 {key}。",
            "difficulty": 3,
        })
    for index, correct in enumerate(sentences[1:3]):
        options, answer = _choice(correct, _distractors(sentences, correct, 3, index), index)
        items.append({
            "q_type": "choice",
            "stem": f"根据情景选择最合适的句子：{situation}",
            "options": options, "answer": answer,
            "analysis": f"该情景最贴切的表达是 “{correct}”。",
            "difficulty": 5,
        })
    return items


def _reading(topic_zh: str, words: list[str], sentences: list[str]) -> list[dict]:
    text = " ".join(sentences[:2])
    items: list[dict] = []
    options, answer = _choice(topic_zh, TOPIC_POOL, 0)
    items.append({
        "q_type": "choice",
        "stem": f"阅读短文，选择短文主要谈论的内容。\n短文：{text}",
        "options": options, "answer": answer,
        "analysis": f"短文围绕「{topic_zh}」展开。",
        "difficulty": 4,
    })
    correct = next((word for word in words if word in text), words[0])
    options, answer = _choice(correct, _distractors(words, correct, 3, 1), 1)
    items.append({
        "q_type": "choice",
        "stem": f"阅读短文，选出短文中出现过的单词。\n短文：{text}",
        "options": options, "answer": answer,
        "analysis": f"短文中出现了 {correct}。",
        "difficulty": 4,
    })
    return items


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--grades", nargs="+", type=int, required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    plan: list[Question] = []
    with SessionLocal() as db:
        chapter_rows = {
            c.id: c for c in db.scalars(
                select(Chapter).where(Chapter.id.in_(list(SEEDS)))
            )
        }
        book_of: dict[int, int] = {}
        for book in db.scalars(
            select(Textbook).where(Textbook.subject == "english", Textbook.grade.in_(args.grades))
        ):
            for chapter in db.scalars(select(Chapter).where(Chapter.textbook_id == book.id)):
                book_of[chapter.id] = book.id
        kps: dict[int, list[int]] = {}
        for chapter_id in chapter_rows:
            rows = list(db.scalars(
                select(Question.knowledge_point_id)
                .where(Question.chapter_id == chapter_id, Question.knowledge_point_id.is_not(None))
                .distinct()
            ))
            kps[chapter_id] = [kp for kp in rows if kp]

        for chapter_id, seed in SEEDS.items():
            book_id = book_of.get(chapter_id)
            if book_id is None:
                continue
            grade = next(
                (b.grade for b in db.scalars(select(Textbook).where(Textbook.id == book_id))
                 if b.id == book_id), None
            )
            if grade is None or grade not in args.grades:
                continue
            topic_zh, words, sentences, qa = seed
            kp_pool = kps.get(chapter_id) or [None]

            for index, item in enumerate(_listening(topic_zh, words, sentences, qa), start=1):
                plan.append(Question(
                    chapter_id=chapter_id,
                    knowledge_point_id=kp_pool[(index - 1) % len(kp_pool)],
                    subject="english", q_type="listening",
                    content={"stem": item["stem"], "script": item["script"],
                             "audio_note": "听力材料以教师朗读/后续 TTS 音频为准"},
                    options=item["options"], answer=item["answer"], analysis=item["analysis"],
                    difficulty=item["difficulty"],
                    tags=["listening", f"grade{grade}", chapter_rows[chapter_id].name],
                    status="published", source_type="original", source_name=SOURCE_NAME,
                    source_ref=f"selfbank:en_listen:{chapter_id}:{index}",
                    license_note=LICENSE_NOTE,
                ))

            for index, item in enumerate(
                _extras(topic_zh, words, sentences, sentences[0])
                + _reading(topic_zh, words, sentences), start=1
            ):
                plan.append(Question(
                    chapter_id=chapter_id,
                    knowledge_point_id=kp_pool[(index - 1) % len(kp_pool)],
                    subject="english", q_type=item["q_type"],
                    content={"stem": item["stem"]},
                    options=item["options"], answer=item["answer"], analysis=item["analysis"],
                    difficulty=item["difficulty"],
                    tags=[item["q_type"], f"grade{grade}", chapter_rows[chapter_id].name],
                    status="published", source_type="original", source_name=SOURCE_NAME,
                    source_ref=f"selfbank:en_extra:{chapter_id}:{index}",
                    license_note=LICENSE_NOTE,
                ))

        for book_id, comps in COMPOSITIONS.items():
            if book_id not in book_of.values():
                continue
            first_chapter = next(
                (cid for cid, bid in book_of.items() if bid == book_id), None
            )
            if first_chapter is None:
                continue
            for index, comp in enumerate(comps, start=1):
                plan.append(Question(
                    chapter_id=first_chapter, knowledge_point_id=None,
                    subject="english", q_type="composition",
                    content={"stem": comp["prompt"], "title": comp["title"],
                             "min_words": comp.get("min_words", 40),
                             "scoring_points": comp["points"], "sample": comp["sample"]},
                    options=None,
                    answer={"value": comp["sample"], "scoring_points": comp["points"],
                            "open_ended": True},
                    analysis="参考范文：" + comp["sample"], difficulty=4,
                    tags=["composition", "selfbank", comp["title"]],
                    status="published", source_type="original", source_name=SOURCE_NAME,
                    source_ref=f"selfbank:en_comp:{book_id}:{index}",
                    license_note=LICENSE_NOTE,
                ))

    print(f"计划写入 {len(plan)} 题：listening "
          f"{sum(1 for q in plan if q.q_type=='listening')} / "
          f"composition {sum(1 for q in plan if q.q_type=='composition')} / 其他 "
          f"{sum(1 for q in plan if q.q_type not in ('listening','composition'))}")
    if not args.apply:
        print("干跑模式：未写库（加 --apply 落库）")
        return 0

    created = skipped = 0
    with SessionLocal() as db:
        for question in plan:
            if db.scalar(select(Question.id).where(Question.source_ref == question.source_ref)):
                skipped += 1
                continue
            db.add(question)
            created += 1
        db.commit()
    print(f"入库完成：created={created} skipped={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
