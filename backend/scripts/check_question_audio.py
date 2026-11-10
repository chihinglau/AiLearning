"""TT-07 读音抽检：每单元抽样生成试听清单、统计合格率并产出返工清单。

抽检规则（设计 D-01 §3.9.10 T6）：
  - 每单元（章节）抽样 ≥5 题；
  - 多音字、分数、单位、英文单词读音正确率 ≥95%；
  - 不达标题目回退系统 TTS，并登记返工清单（`rework.json`，TT-04 接口据此返回 404）。

用法（在 backend/ 下执行）：
  python -m scripts.check_question_audio                  # 生成报告与试听清单
  python -m scripts.check_question_audio --results qa_results.json --apply
  # qa_results.json: {"12": "ok", "13": "fail"}（题目 id -> ok/fail，人工试听后填写）
"""

from __future__ import annotations

import argparse
import json
import os
import random
import shutil
import subprocess
import sys
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]

from sqlalchemy import select  # noqa: E402

from app import models  # noqa: E402,F401  注册全部模型
from app.core.config import settings  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models.content import Chapter, Question  # noqa: E402
from app.services import question_speech as speech  # noqa: E402

PASS_RATE = 0.95
DEFAULT_SEED = 20261110


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def probe_duration(path: Path) -> float | None:
    binary = os.environ.get("FFPROBE_BIN") or shutil.which("ffprobe")
    if not binary:
        return None
    completed = subprocess.run(
        [
            binary,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=nw=1:nk=1",
            str(path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return None
    try:
        return round(float(completed.stdout.strip()), 3)
    except ValueError:
        return None


def _speech_units(text: str) -> tuple[int, str]:
    """按主要语言选择计量单位：中文计字，英文（含中英混排）折算词。"""
    letters = sum(1 for ch in text if ch.isascii() and ch.isalpha())
    han = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    if han > letters:
        return max(han, 1), "字"
    words = sum(1 for word in text.split() if any(ch.isalpha() for ch in word))
    # 混排题的中文片段按约 3 字≈1 词折算，避免只数英文词导致语速被低估。
    return max(round(words + han / 3), 1), "词"


def _suspicion(text: str, duration: float | None) -> str:
    """无人试听时的自动筛查：过短/过长/语速异常先标为待复核。"""
    if duration is None:
        return "无法读取时长，需人工试听"
    if duration < 0.4:
        return "音频过短，可能为空读"
    units, label = _speech_units(text)
    rate = units / duration
    # 中文正常朗读约 3–7 字/秒，英文约 1.5–4.5 词/秒（含选项）。
    if label == "字":
        low, high = 0.8, 10.0
    else:
        low, high = 0.8, 5.5
    if rate > high:
        return f"语速异常（{rate:.1f} {label}/秒），需人工试听"
    if rate < low:
        return f"语速过慢（{rate:.2f} {label}/秒），需人工试听"
    return ""


def sample_units(
    session,
    *,
    out_dir: Path,
    per_unit: int = 5,
    seed: int = DEFAULT_SEED,
    speed: float | None = None,
) -> list[dict]:
    """按章节抽样，返回单位列表（含抽样题与音频状态）。"""
    speed = settings.question_audio_default_speed if speed is None else speed
    stmt = (
        select(Question, Chapter)
        .join(Chapter, Question.chapter_id == Chapter.id)
        .where(
            Question.status == "published",
            Chapter.is_placeholder == 0,
            Chapter.grade.in_(list(speech.ALLOWED_GRADES)),
            Question.subject.in_(list(speech.ALLOWED_SUBJECTS)),
        )
        .order_by(Chapter.grade, Chapter.order_index, Question.id)
    )
    grouped: dict[int, dict] = {}
    for question, chapter in session.execute(stmt):
        text = speech.text_for_question(question)
        if not text.strip():
            continue
        voice = speech.voice_for_subject(question.subject)
        key = speech.cache_key(text, voice, speed)
        path = out_dir / speech.audio_rel_path(key)
        entry = grouped.setdefault(
            chapter.id,
            {
                "chapter_id": chapter.id,
                "grade": chapter.grade,
                "subject": question.subject,
                "name": chapter.name,
                "questions": [],
            },
        )
        entry["questions"].append(
            {
                "question_id": question.id,
                "subject": question.subject,
                "voice": voice,
                "text": text,
                "audio": str(path.relative_to(out_dir)).replace("\\", "/"),
                "audio_path": path,
            }
        )

    rng = random.Random(seed)
    units: list[dict] = []
    for entry in grouped.values():
        candidates = entry["questions"]
        take = min(per_unit, len(candidates))
        picked = rng.sample(candidates, take) if take else []
        items = []
        for candidate in picked:
            path: Path = candidate.pop("audio_path")
            duration = probe_duration(path) if path.exists() else None
            if not path.exists() or path.stat().st_size == 0:
                status, note = "fail", "音频文件缺失"
            else:
                note = _suspicion(candidate["text"], duration)
                status = "pending"
            items.append(
                {
                    **candidate,
                    "bytes": path.stat().st_size if path.exists() else 0,
                    "duration_s": duration,
                    "status": status,
                    "note": note,
                }
            )
        units.append(
            {
                "chapter_id": entry["chapter_id"],
                "grade": entry["grade"],
                "subject": entry["subject"],
                "name": entry["name"],
                "total": len(candidates),
                "sampled": len(items),
                "items": items,
            }
        )
    return units


def summarize(units: Sequence[dict], results: dict[str, str] | None = None) -> dict:
    """把人工结果写入 items，并统计合格率（≥95% 且无待复核为通过）。"""
    results = results or {}
    ok = fail = pending = 0
    missing_units: list[int] = []
    for unit in units:
        if unit["sampled"] < 5:
            missing_units.append(unit["chapter_id"])
        for item in unit["items"]:
            verdict = results.get(str(item["question_id"]))
            if verdict == "ok":
                item["status"] = "ok"
                ok += 1
            elif verdict == "fail":
                item["status"] = "fail"
                fail += 1
            else:
                item["status"] = "pending"
                pending += 1
    judged = ok + fail
    rate = round(ok / judged, 4) if judged else 0.0
    return {
        "units": len(units),
        "sampled": ok + fail + pending,
        "ok": ok,
        "fail": fail,
        "pending": pending,
        "qualified_rate": rate,
        "units_below_min_sample": missing_units,
        "pass": pending == 0 and judged > 0 and rate >= PASS_RATE,
    }


def rework_ids(units: Sequence[dict]) -> list[int]:
    return [
        int(item["question_id"])
        for unit in units
        for item in unit["items"]
        if item["status"] == "fail"
    ]


def render_checklist(report: dict) -> str:
    lines = [
        "# 读题音频试听清单（TT-07）",
        "",
        f"> 生成时间：{report['generated_at']}；抽样种子：{report['seed']}；"
        f"每单元抽样：{report['per_unit']} 题；合格线：{PASS_RATE:.0%}",
        "",
        "试听后把结果写入 `qa_results.json`（`{\"题目id\": \"ok\"|\"fail\"}`），"
        "再执行 `python -m scripts.check_question_audio "
        "--results qa_results.json --apply`。",
        "",
        f"当前统计：抽样 {report['summary']['sampled']}，"
        f"合格 {report['summary']['ok']}，不合格 {report['summary']['fail']}，"
        f"待试听 {report['summary']['pending']}，"
        f"合格率 {report['summary']['qualified_rate']:.2%}",
        "",
    ]
    for unit in report["units"]:
        lines.append(
            f"## {unit['grade']} 年级 · {unit['subject']} · {unit['name']}"
            f"（抽检 {unit['sampled']}/{unit['total']}）"
        )
        lines.append("")
        lines.append("| 题目 | 读法文本 | 音频 | 时长(s) | 结论 | 备注 |")
        lines.append("|---|---|---|---|---|---|")
        for item in unit["items"]:
            lines.append(
                f"| {item['question_id']} | {item['text'][:60]} | "
                f"`{item['audio']}` | {item['duration_s']} | "
                f"{item['status']} | {item['note']} |"
            )
        lines.append("")
    return "\n".join(lines)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="读题音频抽检（TT-07）")
    parser.add_argument("--out-dir", default="")
    parser.add_argument("--per-unit", type=int, default=5)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--speed",
        type=float,
        default=float(settings.question_audio_default_speed),
    )
    parser.add_argument("--report", default="")
    parser.add_argument("--checklist", default="")
    parser.add_argument("--results", default="", help="人工试听结果 JSON")
    parser.add_argument("--apply", action="store_true", help="把不合格题目写入返工清单")
    args = parser.parse_args(argv)

    out_dir = Path(args.out_dir or settings.question_audio_dir).resolve()
    report_path = Path(args.report or out_dir / "qa_audio_report.json")
    checklist_path = Path(args.checklist or out_dir / "qa_audio_checklist.md")

    results: dict[str, str] = {}
    if args.results:
        raw = json.loads(Path(args.results).read_text(encoding="utf-8"))
        results = {str(key): str(value) for key, value in raw.items()}

    session = SessionLocal()
    try:
        units = sample_units(
            session,
            out_dir=out_dir,
            per_unit=args.per_unit,
            seed=args.seed,
            speed=args.speed,
        )
    finally:
        session.close()
    summary = summarize(units, results)
    report = {
        "generated_at": _now(),
        "seed": args.seed,
        "per_unit": args.per_unit,
        "speed": args.speed,
        "pass_rate": PASS_RATE,
        "summary": summary,
        "units": units,
    }
    _write_json(report_path, report)
    checklist_path.write_text(render_checklist(report), encoding="utf-8")
    print(
        f"单元 {summary['units']} 个，抽样 {summary['sampled']} 题；"
        f"合格 {summary['ok']}，不合格 {summary['fail']}，待试听 {summary['pending']}；"
        f"合格率 {summary['qualified_rate']:.2%}；通过={summary['pass']}"
    )
    print(f"报告：{report_path}")
    print(f"清单：{checklist_path}")
    if summary["units_below_min_sample"]:
        print(f"抽样不足 5 题的单元：{summary['units_below_min_sample']}")

    if args.apply:
        ids = rework_ids(units)
        rework_path = out_dir / "rework.json"
        _write_json(rework_path, {"generated_at": _now(), "question_ids": ids})
        print(f"返工清单（{len(ids)} 题）：{rework_path}")
        return 1 if ids else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
