"""TT-03 合成管线：范围筛选、增量跳过、失败清单与清单文件。"""

import json
from pathlib import Path

from app.models.content import Chapter, Question, Textbook
from scripts import build_question_audio as bqa


def _chapter(db, grade: int, *, placeholder: int = 0) -> Chapter:
    textbook = db.query(Textbook).first()
    if textbook is None:
        textbook = Textbook(
            subject="math", grade=grade, version="人教版", semester="first"
        )
        db.add(textbook)
        db.flush()
    chapter = Chapter(
        textbook_id=textbook.id,
        grade=grade,
        name=f"单元{grade}",
        order_index=1,
        is_placeholder=placeholder,
    )
    db.add(chapter)
    db.flush()
    return chapter


def _question(
    db,
    chapter: Chapter,
    *,
    subject: str = "math",
    stem: str = "3 + 4 = ?",
    status: str = "published",
) -> Question:
    question = Question(
        chapter_id=chapter.id,
        subject=subject,
        q_type="choice",
        content={"stem": stem},
        options=[{"key": "A", "text": "6"}, {"key": "B", "text": "7"}],
        answer={"value": "B"},
        status=status,
    )
    db.add(question)
    db.flush()
    return question


def _fake_synth(text, voice, speed, wav_path: Path) -> None:
    wav_path.write_bytes(b"RIFF-fake-wav")


def _fake_transcode(wav_path: Path, opus_path: Path) -> None:
    assert wav_path.stat().st_size > 0
    opus_path.write_bytes(b"OggS-fake-opus")


def test_collect_jobs_filters_grade_subject_status_and_placeholder(
    db, tmp_path: Path
) -> None:
    unit1 = _chapter(db, 1)
    unit4 = _chapter(db, 4)
    placeholder = _chapter(db, 1, placeholder=1)
    math_q = _question(db, unit1, subject="math")
    english_q = _question(db, unit1, subject="english", stem="How many apples?")
    _question(db, unit4, subject="math")
    _question(db, placeholder, subject="math", stem="占位题")
    _question(db, unit1, subject="math", stem="草稿题", status="draft")
    _question(db, unit1, subject="science", stem="科学题")

    jobs, empty = bqa.collect_jobs(
        db,
        grades=(1, 2, 3),
        subjects=("chinese", "math", "english"),
        out_dir=tmp_path,
        speed=1.0,
    )

    assert empty == 0
    assert sorted(job.question_id for job in jobs) == sorted([math_q.id, english_q.id])
    math_job = next(job for job in jobs if job.question_id == math_q.id)
    english_job = next(job for job in jobs if job.question_id == english_q.id)
    assert math_job.text.startswith("3 + 4 等于 ?")
    assert english_job.voice == "vits-piper-en_US-lessac-medium"
    expected = tmp_path / "audio" / math_job.key[:2] / f"{math_job.key}.opus"
    assert math_job.target == expected


def test_run_build_is_incremental_and_writes_manifest(db, tmp_path: Path) -> None:
    chapter = _chapter(db, 1)
    _question(db, chapter, subject="math")
    _question(db, chapter, subject="chinese", stem="3/4 是多少")
    jobs, _ = bqa.collect_jobs(
        db, grades=(1,), subjects=("math", "chinese"), out_dir=tmp_path, speed=1.0
    )

    first = bqa.run_build(
        jobs,
        out_dir=tmp_path,
        synth=_fake_synth,
        transcode=_fake_transcode,
        concurrency=2,
        log=lambda _: None,
    )
    assert (first.generated, first.skipped, first.failed) == (2, 0, [])
    assert all(job.target.exists() for job in jobs)

    second = bqa.run_build(
        jobs,
        out_dir=tmp_path,
        synth=_fake_synth,
        transcode=_fake_transcode,
        concurrency=2,
        log=lambda _: None,
    )
    assert (second.generated, second.skipped) == (0, 2)

    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["rules_version"] == 1
    assert len(manifest["items"]) == 2
    failure = json.loads((tmp_path / "failed_jobs.json").read_text(encoding="utf-8"))
    assert failure["failures"] == []


def test_run_build_retries_then_records_failure(db, tmp_path: Path) -> None:
    chapter = _chapter(db, 1)
    ok_q = _question(db, chapter, subject="math", stem="2 + 2 = ?")
    bad_q = _question(db, chapter, subject="math", stem="必错题")
    jobs, _ = bqa.collect_jobs(
        db, grades=(1,), subjects=("math",), out_dir=tmp_path, speed=1.0
    )
    attempts: dict[str, int] = {}

    def flaky(text, voice, speed, wav_path: Path) -> None:
        attempts[text] = attempts.get(text, 0) + 1
        if "必错" in text:
            raise RuntimeError("合成失败")
        _fake_synth(text, voice, speed, wav_path)

    result = bqa.run_build(
        jobs,
        out_dir=tmp_path,
        synth=flaky,
        transcode=_fake_transcode,
        retries=2,
        concurrency=1,
        log=lambda _: None,
    )

    assert result.generated == 1
    assert [item["question_id"] for item in result.failed] == [bad_q.id]
    assert "合成失败" in result.failed[0]["error"]
    assert sum(count for text, count in attempts.items() if "必错题" in text) == 3
    ok_job = next(job for job in jobs if job.question_id == ok_q.id)
    assert ok_job.target.exists()

    failure = json.loads((tmp_path / "failed_jobs.json").read_text(encoding="utf-8"))
    assert len(failure["failures"]) == 1
    assert failure["failures"][0]["subject"] == "math"


def test_run_build_force_regenerates_existing(db, tmp_path: Path) -> None:
    chapter = _chapter(db, 1)
    _question(db, chapter, subject="math")
    jobs, _ = bqa.collect_jobs(
        db, grades=(1,), subjects=("math",), out_dir=tmp_path, speed=1.0
    )
    jobs[0].target.parent.mkdir(parents=True, exist_ok=True)
    jobs[0].target.write_bytes(b"old")

    result = bqa.run_build(
        jobs,
        out_dir=tmp_path,
        synth=_fake_synth,
        transcode=_fake_transcode,
        force=True,
        log=lambda _: None,
    )
    assert result.generated == 1
    assert jobs[0].target.read_bytes() == b"OggS-fake-opus"


def test_parse_cli_lists() -> None:
    assert bqa.parse_ints(["1,2", "3"], (1, 2, 3)) == [1, 2, 3]
    assert bqa.parse_strs(None, ("chinese",)) == ["chinese"]
    assert bqa.parse_strs(["math,english"], ()) == ["math", "english"]
