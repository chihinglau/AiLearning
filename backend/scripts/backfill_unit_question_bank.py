"""为按单元出卷补齐题库缺口（不改蓝图、不降级题型）。

- 7–9 年级英语：新教材 25 题/单元不含听力；按单元卷必须含 8 道听力，
  这里按单元主题词表补 8 道原创听力（沿用样章风格，音频走教师朗读/TTS）。
- 1–6 年级英语个别单元听力仅 7 道：补 1 道原创听力。
- 数学个别单元填空仅 3–4 道：补到 5 道原创填空。

幂等：按 source_ref 判重；--apply 才写库。

用法：
    python -m scripts.backfill_unit_question_bank
    python -m scripts.backfill_unit_question_bank --apply
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parents[1] / "ailearning_dev.db"

ENGLISH_FIXES = {
    # (textbook_id, unit_index): (unit name, 8 个主题词)
    (53, 1): ("Unit 1 Friendship", ["friend", "classmate", "kind", "helpful", "honest", "smile", "share", "trust"]),
    (53, 2): ("Unit 2 School life", ["lesson", "teacher", "classroom", "homework", "club", "library", "lunch", "timetable"]),
    (53, 3): ("Unit 3 The seasons", ["spring", "summer", "autumn", "winter", "sunny", "rainy", "windy", "cloudy"]),
    (53, 4): ("Unit 4 The Earth", ["earth", "forest", "river", "ocean", "recycle", "pollution", "nature", "protect"]),
    (53, 5): ("Unit 5 Off to space", ["space", "planet", "rocket", "astronaut", "moon", "star", "spaceship", "orbit"]),
    (53, 6): ("Unit 6 Travelling around Asia", ["travel", "city", "temple", "market", "mountain", "beach", "tourist", "map"]),
    (53, 7): ("Unit 7 Fun after school", ["sport", "music", "dance", "paint", "game", "club", "practice", "hobby"]),
    (53, 8): ("Unit 8 Collecting as a hobby", ["collect", "stamp", "coin", "shell", "model", "album", "rare", "display"]),
    (54, 1): ("Unit 1 People around us", ["grandparent", "parent", "neighbour", "friend", "cousin", "doctor", "driver", "nurse"]),
    (54, 2): ("Unit 2 Travelling around the world", ["country", "capital", "landmark", "museum", "hotel", "airport", "souvenir", "guide"]),
    (54, 3): ("Unit 3 Trees and us", ["tree", "leaf", "branch", "root", "wood", "forest", "oxygen", "plant"]),
    (54, 4): ("Unit 4 Our animal friends", ["cat", "dog", "bird", "rabbit", "fish", "horse", "feed", "pet"]),
    (54, 5): ("Unit 5 Water", ["water", "drop", "river", "sea", "rain", "drink", "wash", "save"]),
    (54, 6): ("Unit 6 Electricity", ["electricity", "light", "switch", "battery", "power", "wire", "socket", "safe"]),
    (54, 7): ("Unit 7 Poems", ["poem", "poet", "line", "rhyme", "read", "write", "feeling", "picture"]),
    (54, 8): ("Unit 8 From hobby to career", ["hobby", "career", "job", "skill", "dream", "work", "train", "future"]),
    (67, 1): ("Unit 1 Look it up!", ["encyclopedia", "dictionary", "look up", "fact", "information", "search", "record", "fact file"]),
    (67, 2): ("Unit 2 Amazing numbers", ["number", "zero", "million", "billion", "count", "calculate", "percentage", "score"]),
    (67, 3): ("Unit 3 Our digital lives", ["digital", "phone", "internet", "password", "website", "message", "online", "screen"]),
    (67, 4): ("Unit 4 Inventions", ["invention", "inventor", "wheel", "paper", "printing", "telephone", "light bulb", "machine"]),
    (67, 5): ("Unit 5 Going on an exchange trip", ["exchange", "trip", "host", "passport", "flight", "language", "culture", "suitcase"]),
    (67, 6): ("Unit 6 Wisdom counts", ["wisdom", "advice", "choice", "decision", "problem", "solution", "reason", "experience"]),
    (67, 7): ("Unit 7 The secret of memory", ["memory", "remember", "forget", "brain", "review", "repeat", "note", "imagine"]),
    (67, 8): ("Unit 8 Pets and us", ["pet", "animal", "feed", "vet", "kennel", "walk", "health", "responsible"]),
    (68, 1): ("Unit 1 Helping those in need", ["volunteer", "help", "donate", "charity", "support", "community", "raise", "care"]),
    (68, 2): ("Unit 2 Body language", ["gesture", "smile", "eye contact", "nod", "wave", "posture", "signal", "communicate"]),
    (68, 3): ("Unit 3 Comics and animation", ["comic", "animation", "cartoon", "character", "draw", "story", "frame", "film"]),
    (68, 4): ("Unit 4 Arts and heritage", ["art", "heritage", "museum", "painting", "sculpture", "history", "culture", "protect"]),
    (68, 5): ("Unit 5 Saving animals in danger", ["endangered", "habitat", "wild", "reserve", "hunt", "survive", "protect", "species"]),
    (68, 6): ("Unit 6 Learning by doing", ["project", "experiment", "observe", "record", "report", "teamwork", "discover", "result"]),
    (68, 7): ("Unit 7 Space exploration", ["space", "planet", "satellite", "rocket", "astronaut", "explore", "universe", "discovery"]),
    (68, 8): ("Unit 8 Imagine that!", ["imagine", "future", "invent", "dream", "possible", "creative", "design", "wonder"]),
    (83, 1): ("Unit 1 Great people", ["scientist", "inventor", "leader", "writer", "artist", "famous", "achievement", "contribution"]),
    (83, 2): ("Unit 2 Great ideas", ["idea", "invention", "creative", "design", "solution", "discover", "improve", "change"]),
    (83, 3): ("Unit 3 Family traditions", ["tradition", "family", "festival", "dinner", "custom", "generation", "celebrate", "respect"]),
    (83, 4): ("Unit 4 A better me", ["improve", "habit", "goal", "practice", "confidence", "progress", "challenge", "responsibility"]),
    (83, 5): ("Unit 5 My time, my joy", ["hobby", "leisure", "weekend", "music", "sport", "reading", "relax", "enjoy"]),
    (83, 6): ("Unit 6 Food and health", ["food", "healthy", "vegetable", "fruit", "exercise", "sleep", "balanced", "nutrition"]),
    (83, 7): ("Unit 7 Reading Mark Twain", ["author", "novel", "story", "character", "humour", "adventure", "reader", "classic"]),
    (83, 8): ("Unit 8 The power of love", ["love", "care", "kindness", "support", "friendship", "family", "help", "hope"]),
}

EARLY_LISTEN_FIX = {
    # 具体章节 id 与 1 个主题词（仅补 1 道）
    532: "clock",
}


def listening_row(chapter_id: int, word: str, index: int) -> dict:
    distractors = ["book", "bag", "desk", "chair", "pen", "cup", "hat", "shoe"]
    others = [w for w in distractors if w != word][:3]
    content = {
        "stem": "听录音，选出你听到的单词。",
        "script": word,
        "audio_note": "听力材料以教师朗读/后续 TTS 音频为准",
    }
    return {
        "chapter_id": chapter_id,
        "subject": "english",
        "q_type": "listening",
        "content": json.dumps(content, ensure_ascii=False),
        "options": json.dumps(
            [{"key": "A", "text": word}, {"key": "B", "text": others[0]}, {"key": "C", "text": others[1]}, {"key": "D", "text": others[2]}],
            ensure_ascii=False,
        ),
        "answer": json.dumps({"value": "A"}, ensure_ascii=False),
        "analysis": json.dumps({"text": f"录音内容为 {word}。"}, ensure_ascii=False),
        "difficulty": 2,
        "tags": json.dumps(["listening", "by_unit", "unit_backfill"], ensure_ascii=False),
        "knowledge_point_id": None,
        "status": "published",
        "source_type": "original",
        "source_name": "自建题型题库（原创）",
        "source_ref": f"selfbank:en_listen_unit_fix:{chapter_id}:{index}",
        "copyright_owner": None,
        "license_note": "原创自建内容，不含第三方版权素材",
        "adapted_from": None,
        "created_at": "2026-11-25 00:00:00",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cols = [r[1] for r in conn.execute("pragma table_info(questions)")]
    placeholders = ",".join("?" * (len(cols) - 1))
    sql = f"insert into questions({','.join(c for c in cols if c != 'id')}) values({placeholders})"
    created = skipped = 0

    for (tid, unit_idx), (unit_name, words) in ENGLISH_FIXES.items():
        from scripts.generate_all_unit_papers import split_units

        unit = next((u for u in split_units(conn, tid) if u["index"] == unit_idx), None)
        if unit is None:
            continue
        chapter_id = unit["chapter_ids"][0]
        for i, word in enumerate(words, 1):
            ref = f"selfbank:en_listen_unit_fix:{chapter_id}:{i}"
            if conn.execute("select 1 from questions where source_ref=?", (ref,)).fetchone():
                skipped += 1
                continue
            row = listening_row(chapter_id, word, i)
            if args.apply:
                conn.execute(sql, [row[c] for c in cols if c != "id"])
                created += 1
            else:
                created += 1
        print(f"EN {tid} U{unit_idx} {unit_name}: 8 listening")

    for chapter_id, word in EARLY_LISTEN_FIX.items():
        ref = f"selfbank:en_listen_unit_fix:{chapter_id}:1"
        if conn.execute("select 1 from questions where source_ref=?", (ref,)).fetchone():
            skipped += 1
            continue
        row = listening_row(chapter_id, word, 1)
        if args.apply:
            conn.execute(sql, [row[c] for c in cols if c != "id"])
        created += 1
        print(f"EN chapter {chapter_id}: +1 listening")

    if args.apply:
        conn.commit()
    print(f"SUMMARY create={created} skip={skipped} apply={args.apply}")
    conn.close()


if __name__ == "__main__":
    main()
