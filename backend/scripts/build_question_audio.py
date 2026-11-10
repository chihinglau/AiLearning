"""TT-03 开源 TTS 批量合成管线（设计 D-01 §3.9.2 / §3.9.7）。

用途：内容侧离线批量生成题干朗读音频（Opus），零 API 费用；仅覆盖
1–3 年级语文/数学/英语，音频默认不随整册包下发（TT-04 按需分发）。

依赖：
  - `pip install sherpa-onnx`（已写入 backend/requirements-audio.txt）
  - 本地模型目录（仓库外或 `.tools/`），默认 `.tools/tts-models`：
      vits-piper-zh_CN-huayan-medium/   # 中文（语文/数学）
      vits-piper-en_US-lessac-medium/   # 英文（英语）
  - `ffmpeg`（PATH 中，或通过 `FFMPEG_BIN` 指定）

示例（在 backend/ 下执行）：
  python -m scripts.build_question_audio --grade 1 --subject math --dry-run
  python -m scripts.build_question_audio --concurrency 4 --retries 2
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import shutil
import subprocess
import tempfile
import threading
import wave
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = BACKEND_DIR.parent

from sqlalchemy import select  # noqa: E402

from app import models  # noqa: E402,F401  注册全部模型
from app.core.config import settings  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models.content import Chapter, Question  # noqa: E402
from app.services import question_speech as speech  # noqa: E402

DEFAULT_MODEL_DIR = REPO_DIR / ".tools" / "tts-models"
OPUS_BITRATE = "24k"

SynthFn = Callable[[str, str, float, Path], None]
TranscodeFn = Callable[[Path, Path], None]


@dataclass(frozen=True)
class AudioJob:
    question_id: int
    subject: str
    grade: int
    text: str
    voice: str
    speed: float
    key: str
    target: Path


@dataclass
class BuildResult:
    total: int = 0
    generated: int = 0
    skipped: int = 0
    failed: list[dict] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.failed


def parse_ints(raw: Sequence[str] | None, default: Sequence[int]) -> list[int]:
    if not raw:
        return list(default)
    values: list[int] = []
    for item in raw:
        for part in str(item).split(","):
            part = part.strip()
            if part:
                values.append(int(part))
    return values


def parse_strs(raw: Sequence[str] | None, default: Sequence[str]) -> list[str]:
    if not raw:
        return list(default)
    values: list[str] = []
    for item in raw:
        for part in str(item).split(","):
            part = part.strip()
            if part:
                values.append(part)
    return values


def collect_jobs(
    session,
    *,
    grades: Sequence[int],
    subjects: Sequence[str],
    out_dir: Path,
    speed: float,
    voice_override: str | None = None,
) -> tuple[list[AudioJob], int]:
    """按范围挑选已发布题目并计算缓存键；返回 (jobs, 空文本题数)。"""
    stmt = (
        select(Question, Chapter.grade)
        .join(Chapter, Question.chapter_id == Chapter.id)
        .where(
            Question.status == "published",
            Chapter.is_placeholder == 0,
            Chapter.grade.in_(list(grades)),
            Question.subject.in_(list(subjects)),
        )
        .order_by(Chapter.grade, Question.subject, Question.id)
    )
    jobs: list[AudioJob] = []
    empty = 0
    for question, grade in session.execute(stmt):
        text = speech.text_for_question(question)
        if not text.strip():
            empty += 1
            continue
        voice = voice_override or speech.voice_for_subject(question.subject)
        key = speech.cache_key(text, voice, speed)
        jobs.append(
            AudioJob(
                question_id=question.id,
                subject=question.subject,
                grade=int(grade),
                text=text,
                voice=voice,
                speed=speed,
                key=key,
                target=out_dir / speech.audio_rel_path(key),
            )
        )
    return jobs, empty


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _load_manifest(path: Path) -> dict:
    if not path.exists():
        return {"items": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"items": {}}
    if not isinstance(data, dict) or not isinstance(data.get("items"), dict):
        return {"items": {}}
    return data


def run_build(
    jobs: Sequence[AudioJob],
    *,
    out_dir: Path,
    synth: SynthFn,
    transcode: TranscodeFn,
    retries: int = 2,
    concurrency: int = 2,
    force: bool = False,
    failed_path: Path | None = None,
    manifest_path: Path | None = None,
    log: Callable[[str], None] = print,
) -> BuildResult:
    """增量合成：已存在目标文件则跳过；失败按 `retries` 重试并写入失败清单。"""
    result = BuildResult(total=len(jobs))
    manifest_path = manifest_path or out_dir / "manifest.json"
    failed_path = failed_path or out_dir / "failed_jobs.json"
    manifest = _load_manifest(manifest_path)
    items: dict[str, dict] = manifest.setdefault("items", {})
    lock = threading.Lock()

    pending: list[AudioJob] = []
    for job in jobs:
        if not force and job.target.exists() and job.target.stat().st_size > 0:
            result.skipped += 1
            items.setdefault(
                str(job.question_id),
                {
                    "key": job.key,
                    "path": str(job.target.relative_to(out_dir)).replace("\\", "/"),
                    "subject": job.subject,
                    "grade": job.grade,
                    "text": job.text,
                    "voice": job.voice,
                    "speed": job.speed,
                    "bytes": job.target.stat().st_size,
                },
            )
        else:
            pending.append(job)

    def _work(job: AudioJob) -> dict | None:
        last_error = ""
        for attempt in range(retries + 1):
            tmp_dir = Path(tempfile.mkdtemp(prefix="qaudio-"))
            try:
                wav_path = tmp_dir / "tts.wav"
                synth(job.text, job.voice, job.speed, wav_path)
                if not wav_path.exists() or wav_path.stat().st_size == 0:
                    raise RuntimeError("合成器未生成有效 wav")
                job.target.parent.mkdir(parents=True, exist_ok=True)
                stash = tmp_dir / "out.opus"
                transcode(wav_path, stash)
                if not stash.exists() or stash.stat().st_size == 0:
                    raise RuntimeError("转码未生成有效 opus")
                shutil.move(str(stash), str(job.target))
                return {
                    "key": job.key,
                    "path": str(job.target.relative_to(out_dir)).replace("\\", "/"),
                    "subject": job.subject,
                    "grade": job.grade,
                    "text": job.text,
                    "voice": job.voice,
                    "speed": job.speed,
                    "bytes": job.target.stat().st_size,
                    "generated_at": datetime.now(timezone.utc).isoformat(
                        timespec="seconds"
                    ),
                    "attempts": attempt + 1,
                }
            except Exception as exc:  # noqa: BLE001 - 逐题容错，失败进清单
                last_error = f"{type(exc).__name__}: {exc}"
            finally:
                shutil.rmtree(tmp_dir, ignore_errors=True)
        return {"question_id": job.question_id, "error": last_error, "job": job}

    if pending:
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=max(1, concurrency)
        ) as pool:
            futures = {pool.submit(_work, job): job for job in pending}
            for done, future in enumerate(
                concurrent.futures.as_completed(futures), start=1
            ):
                outcome = future.result()
                job = futures[future]
                with lock:
                    if "question_id" in outcome:
                        result.failed.append(
                            {
                                "question_id": outcome["question_id"],
                                "subject": job.subject,
                                "grade": job.grade,
                                "voice": job.voice,
                                "speed": job.speed,
                                "text": job.text,
                                "error": outcome["error"],
                            }
                        )
                    else:
                        result.generated += 1
                        items[str(job.question_id)] = outcome
                log(
                    f"[{done}/{len(pending)}] "
                    f"q{job.question_id} {job.subject} g{job.grade} "
                    f"({'失败' if 'question_id' in outcome else '完成'})"
                )

    manifest["rules_version"] = speech.RULES_VERSION
    manifest["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    _write_json(manifest_path, manifest)
    _write_json(
        failed_path,
        {
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "total": result.total,
            "generated": result.generated,
            "skipped": result.skipped,
            "failures": result.failed,
        },
    )
    return result


class SherpaSynthesizer:
    """sherpa-onnx VITS 合成器：每个音色一个引擎，线程内串行、跨音色并行。"""

    def __init__(self, model_dir: Path, *, num_threads: int = 2) -> None:
        self.model_dir = model_dir
        self.num_threads = num_threads
        self._engines: dict[str, object] = {}
        self._locks: dict[str, threading.Lock] = {}
        self._guard = threading.Lock()

    def _engine(self, voice: str):
        if voice in self._engines:
            return self._engines[voice]
        with self._guard:
            if voice in self._engines:
                return self._engines[voice]
            import sherpa_onnx  # 延迟导入：--dry-run 不依赖该包

            voice_dir = self.model_dir / voice
            if not voice_dir.exists():
                raise FileNotFoundError(
                    f"缺少模型目录 {voice_dir}；请下载 sherpa-onnx release 中的 "
                    f"{voice}.tar.bz2 并解压到 {self.model_dir}"
                )
            onnx = next(iter(sorted(voice_dir.glob("*.onnx"))), None)
            tokens = voice_dir / "tokens.txt"
            if onnx is None or not tokens.exists():
                raise FileNotFoundError(f"模型目录结构不完整：{voice_dir}")
            config = sherpa_onnx.OfflineTtsConfig(
                model=sherpa_onnx.OfflineTtsModelConfig(
                    vits=sherpa_onnx.OfflineTtsVitsModelConfig(
                        model=str(onnx),
                        tokens=str(tokens),
                        data_dir=str(voice_dir / "espeak-ng-data"),
                    ),
                    num_threads=self.num_threads,
                ),
                max_num_sentences=1,
            )
            engine = sherpa_onnx.OfflineTts(config)
            self._engines[voice] = engine
            self._locks[voice] = threading.Lock()
            return engine

    def __call__(self, text: str, voice: str, speed: float, wav_path: Path) -> None:
        engine = self._engine(voice)
        with self._locks[voice]:
            audio = engine.generate(text, sid=0, speed=speed)
        if audio is None or len(audio.samples) == 0:
            raise RuntimeError("合成结果为空")
        _write_wav(wav_path, audio.samples, int(audio.sample_rate))


def _write_wav(path: Path, samples, sample_rate: int) -> None:
    """把 sherpa-onnx 的浮点采样写成 16 bit 单声道 wav（供 ffmpeg 转 Opus）。"""
    import numpy as np

    pcm = np.clip(np.asarray(samples, dtype=np.float32), -1.0, 1.0)
    pcm16 = (pcm * 32767).astype("<i2")
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(pcm16.tobytes())


def ffmpeg_path() -> str:
    candidate = os.environ.get("FFMPEG_BIN") or shutil.which("ffmpeg")
    if not candidate:
        raise RuntimeError(
            "未找到 ffmpeg：请安装并加入 PATH，或设置环境变量 FFMPEG_BIN"
        )
    return candidate


def transcode_opus(
    wav_path: Path, opus_path: Path, *, bitrate: str = OPUS_BITRATE
) -> None:
    cmd = [
        ffmpeg_path(),
        "-y",
        "-loglevel",
        "error",
        "-i",
        str(wav_path),
        "-c:a",
        "libopus",
        "-b:a",
        bitrate,
        "-f",
        "ogg",
        str(opus_path),
    ]
    completed = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError(f"ffmpeg 转码失败：{completed.stderr.strip()[:300]}")


def _print_plan(
    jobs: Sequence[AudioJob], empty: int, out_dir: Path, speed: float
) -> None:
    existing = sum(
        1 for job in jobs if job.target.exists() and job.target.stat().st_size > 0
    )
    print(f"输出目录：{out_dir}")
    print(f"语速：{speed:.2f}；规则版本：{speech.RULES_VERSION}")
    print(
        f"题目总数：{len(jobs)}（待生成 {len(jobs) - existing}，"
        f"已存在 {existing}，空文本 {empty}）"
    )
    by_subject: dict[str, int] = {}
    by_grade: dict[int, int] = {}
    for job in jobs:
        by_subject[job.subject] = by_subject.get(job.subject, 0) + 1
        by_grade[job.grade] = by_grade.get(job.grade, 0) + 1
    print("按学科：" + "，".join(f"{k}={v}" for k, v in sorted(by_subject.items())))
    print("按年级：" + "，".join(f"{k}={v}" for k, v in sorted(by_grade.items())))
    for job in jobs[:5]:
        print(f"  示例 q{job.question_id} [{job.subject}/g{job.grade}] {job.text[:40]}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="批量合成题干朗读音频（TT-03）")
    parser.add_argument("--grade", action="append", help="年级，可逗号分隔，默认 1,2,3")
    parser.add_argument(
        "--subject", action="append", help="学科，可逗号分隔，默认 chinese,math,english"
    )
    parser.add_argument("--dry-run", action="store_true", help="只统计与示例，不合成")
    parser.add_argument("--limit", type=int, default=0, help="最多处理 N 道（调试用）")
    parser.add_argument("--concurrency", type=int, default=2)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument(
        "--speed",
        type=float,
        default=float(settings.question_audio_default_speed),
    )
    parser.add_argument("--voice", default="", help="强制指定音色（默认按学科）")
    parser.add_argument("--force", action="store_true", help="忽略已有文件重新合成")
    parser.add_argument(
        "--model-dir", default=os.environ.get("QUESTION_AUDIO_MODEL_DIR", "")
    )
    parser.add_argument("--out-dir", default="")
    parser.add_argument("--failed-list", default="")
    parser.add_argument("--manifest", default="")
    args = parser.parse_args(argv)

    grades = parse_ints(args.grade, speech.ALLOWED_GRADES)
    subjects = parse_strs(args.subject, speech.ALLOWED_SUBJECTS)
    out_dir = Path(args.out_dir or settings.question_audio_dir).resolve()
    model_dir = Path(
        args.model_dir
        or os.environ.get("QUESTION_AUDIO_MODEL_DIR")
        or DEFAULT_MODEL_DIR
    )

    session = SessionLocal()
    try:
        jobs, empty = collect_jobs(
            session,
            grades=grades,
            subjects=subjects,
            out_dir=out_dir,
            speed=args.speed,
            voice_override=args.voice or None,
        )
    finally:
        session.close()

    if args.limit > 0:
        jobs = jobs[: args.limit]

    print(
        f"范围：grade={grades} subject={subjects}；模型目录：{model_dir}"
    )
    _print_plan(jobs, empty, out_dir, args.speed)
    if args.dry_run or not jobs:
        return 0

    result = run_build(
        jobs,
        out_dir=out_dir,
        synth=SherpaSynthesizer(model_dir),
        transcode=transcode_opus,
        retries=args.retries,
        concurrency=args.concurrency,
        force=args.force,
        failed_path=Path(args.failed_list) if args.failed_list else None,
        manifest_path=Path(args.manifest) if args.manifest else None,
    )
    print(
        f"完成：生成 {result.generated}，跳过 {result.skipped}，"
        f"失败 {len(result.failed)}"
    )
    if result.failed:
        failed_list = Path(args.failed_list or out_dir / "failed_jobs.json")
        print(f"失败清单：{failed_list}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
