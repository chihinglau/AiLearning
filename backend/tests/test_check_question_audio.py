"""TT-07 抽检脚本：抽样规则、合格率阈值与返工清单。"""

from pathlib import Path

from app.models.content import Chapter, Question, Textbook
from app.services import question_speech as speech
from scripts import check_question_audio as qa


def _unit(
    db, *, grade: int = 1, subject: str = "math", count: int = 7
) -> list[Question]:
    textbook = db.query(Textbook).first()
    if textbook is None:
        textbook = Textbook(
            subject=subject, grade=grade, version="人教版", semester="first"
        )
        db.add(textbook)
        db.flush()
    chapter = Chapter(
        textbook_id=textbook.id, grade=grade, name="第一单元", order_index=1
    )
    db.add(chapter)
    db.flush()
    questions = []
    for index in range(count):
        question = Question(
            chapter_id=chapter.id,
            subject=subject,
            q_type="choice",
            content={"stem": f"{index + 1} + 2 = ?"},
            options=[{"key": "A", "text": "3"}],
            answer={"value": "A"},
            status="published",
        )
        db.add(question)
        questions.append(question)
    db.flush()
    return questions


def _touch_audio(out_dir: Path, question: Question) -> Path:
    text = speech.text_for_question(question)
    key = speech.cache_key(text, speech.voice_for_subject(question.subject), 1.0)
    path = out_dir / speech.audio_rel_path(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"OggS")
    return path


def test_sample_units_takes_five_and_is_deterministic(
    db, tmp_path: Path, monkeypatch
) -> None:
    questions = _unit(db, count=7)
    for question in questions:
        _touch_audio(tmp_path, question)
    monkeypatch.setattr(qa, "probe_duration", lambda path: 3.0)

    first = qa.sample_units(db, out_dir=tmp_path, per_unit=5)
    second = qa.sample_units(db, out_dir=tmp_path, per_unit=5)

    assert len(first) == 1
    assert first[0]["sampled"] == 5
    assert first[0]["total"] == 7
    assert [item["question_id"] for item in first[0]["items"]] == [
        item["question_id"] for item in second[0]["items"]
    ]
    assert all(item["status"] == "pending" for item in first[0]["items"])


def test_sample_units_marks_missing_audio_failed(
    db, tmp_path: Path, monkeypatch
) -> None:
    _unit(db, count=5)
    monkeypatch.setattr(qa, "probe_duration", lambda path: None)

    units = qa.sample_units(db, out_dir=tmp_path, per_unit=5)

    assert units[0]["items"][0]["status"] == "fail"
    assert units[0]["items"][0]["note"] == "音频文件缺失"


def _unit_report(count: int, sampled: int = 5) -> dict:
    return {
        "chapter_id": 1,
        "grade": 1,
        "subject": "math",
        "name": "第一单元",
        "total": count,
        "sampled": sampled,
        "items": [
            {
                "question_id": index,
                "text": f"{index} 加 2 等于 ？",
                "audio": f"audio/00/{index}.opus",
                "duration_s": 2.0,
                "status": "pending",
                "note": "",
            }
            for index in range(1, sampled + 1)
        ],
    }


def test_summarize_thresholds() -> None:
    units = [_unit_report(6, 5), _unit_report(6, 5)]
    all_ok = {str(index): "ok" for index in range(1, 6)}
    all_ok["1"] = "fail"
    result = qa.summarize(units, all_ok)
    assert (result["ok"], result["fail"], result["pending"]) == (8, 2, 0)
    assert result["qualified_rate"] == 0.8
    assert result["pass"] is False

    mostly_ok = {str(index): "ok" for index in range(1, 6)}
    result = qa.summarize([_unit_report(6, 5)], mostly_ok)
    assert result["qualified_rate"] == 1.0
    assert result["pass"] is True

    pending = qa.summarize(units, {})
    assert pending["pending"] == 10
    assert pending["pass"] is False


def test_summarize_flags_units_below_min_sample() -> None:
    result = qa.summarize([_unit_report(3, sampled=3)], {"1": "ok"})
    assert result["units_below_min_sample"] == [1]


def test_rework_ids_and_checklist() -> None:
    units = [_unit_report(6, 5)]
    summary = qa.summarize(units, {"1": "fail"})
    report = {
        "generated_at": "2026-11-10T00:00:00+00:00",
        "seed": 1,
        "per_unit": 5,
        "summary": summary,
        "units": units,
    }
    assert qa.rework_ids(units) == [1]
    text = qa.render_checklist(report)
    assert "读题音频试听清单" in text
    assert "第一单元" in text
