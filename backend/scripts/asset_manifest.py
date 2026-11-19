"""音频资产清单与覆盖率（P0-B 交付用，只读库 + 只读文件系统）。

产出三样东西：
1. `--out` 指定的 manifest.json：每个音频文件的相对路径、大小、可选 sha256，按 kind 汇总；
2. 听力题覆盖率：库内每道 listening 题对应的音频文件是否存在，缺失清单直接打出；
3. 传输校验基线：manifest 的 sha256 在 rsync/scp 之后可用 `--verify-manifest` 复算比对。

用法（在 backend 目录）：
    python -m scripts.asset_manifest                       # 全量 + sha256
    python -m scripts.asset_manifest --no-hash              # 只出清单，快
    python -m scripts.asset_manifest --dir build/question_audio --out build/audio_manifest.json
    python -m scripts.asset_manifest --verify-manifest build/audio_manifest.json --dir /opt/ailearning-assets/question_audio
退出码：0 正常；1 听力音频有缺失或校验不一致。
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

from sqlalchemy import select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.content import Question
from app.services.question_speech import (
    listening_audio_rel_path,
    listening_cache_key,
    listening_script,
    voice_for_subject,
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _kind(rel: str) -> str:
    if rel.startswith("audio/listening/"):
        return "listening"
    if rel.startswith("audio/"):
        return "reading"
    return "other"


def _build_manifest(root: Path, with_hash: bool) -> dict:
    files = []
    totals = {"reading": [0, 0], "listening": [0, 0], "other": [0, 0]}
    for path in sorted(root.rglob("*.opus")):
        rel = path.relative_to(root).as_posix()
        size = path.stat().st_size
        kind = _kind(rel)
        entry = {"path": rel, "size": size, "kind": kind}
        if with_hash:
            entry["sha256"] = _sha256(path)
        files.append(entry)
        totals[kind][0] += 1
        totals[kind][1] += size
    return {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "root": str(root),
        "file_count": len(files),
        "total_bytes": sum(size for _n, size in totals.values()),
        "by_kind": {
            kind: {"files": count, "bytes": size}
            for kind, (count, size) in totals.items()
            if count
        },
        "files": files,
    }


def _listening_coverage(session, root: Path) -> tuple[int, list[dict]]:
    """逐题算听力音频缓存键并查文件，返回 (总题数, 缺失清单)。"""
    speed = float(settings.question_audio_default_speed)
    questions = session.scalars(
        select(Question).where(Question.q_type == "listening")
    ).all()
    missing: list[dict] = []
    for question in questions:
        text = listening_script(question)
        if not text:
            missing.append({"question_id": question.id, "reason": "empty_script"})
            continue
        key = listening_cache_key(text, voice_for_subject(str(question.subject or "")), speed)
        rel = listening_audio_rel_path(key)
        if not (root / rel).is_file():
            missing.append({"question_id": question.id, "expected": rel})
    return len(questions), missing


def _verify_manifest(root: Path, manifest_path: Path) -> int:
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    bad = 0
    for entry in data.get("files") or []:
        if "sha256" not in entry:
            continue
        path = root / entry["path"]
        if not path.is_file():
            print(f"MISSING {entry['path']}")
            bad += 1
            continue
        if _sha256(path) != entry["sha256"]:
            print(f"HASH_MISMATCH {entry['path']}")
            bad += 1
    print(f"校验 {len(data.get('files') or [])} 个文件，异常 {bad}")
    return 1 if bad else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="音频资产清单与覆盖率")
    parser.add_argument("--dir", default=None, help="音频根目录（默认 settings.question_audio_dir）")
    parser.add_argument("--out", default=None, help="manifest 输出路径")
    parser.add_argument("--no-hash", action="store_true", help="不计算 sha256（快速清单）")
    parser.add_argument("--verify-manifest", default=None, help="按已有 manifest 复算校验（传 manifest 路径）")
    parser.add_argument("--no-coverage", action="store_true", help="跳过听力题覆盖率检查")
    args = parser.parse_args()

    backend_dir = Path(__file__).resolve().parents[1]
    root = Path(args.dir) if args.dir else Path(settings.question_audio_dir)
    if not root.is_absolute():
        root = (backend_dir / root).resolve()

    if args.verify_manifest:
        return _verify_manifest(root, Path(args.verify_manifest))

    if not root.is_dir():
        print(f"❌ 音频目录不存在：{root}")
        return 2

    manifest = _build_manifest(root, with_hash=not args.no_hash)
    print(f"音频根目录：{root}")
    for kind, info in manifest["by_kind"].items():
        print(f"  {kind:<10} {info['files']:>6} 个  {info['bytes'] / 1024 / 1024:>8.1f} MB")
    print(f"  合计       {manifest['file_count']:>6} 个  {manifest['total_bytes'] / 1024 / 1024:>8.1f} MB")

    coverage_ok = True
    if not args.no_coverage:
        session = SessionLocal()
        try:
            total, missing = _listening_coverage(session, root)
        finally:
            session.close()
        manifest["listening_coverage"] = {
            "questions": total,
            "present": total - len(missing),
            "missing": len(missing),
            "missing_samples": missing[:20],
        }
        print(
            f"听力题音频覆盖：{total - len(missing)}/{total}"
            f"（{(total - len(missing)) / total * 100:.2f}%）" if total else "库内无听力题"
        )
        if missing:
            print(f"缺失样例：{json.dumps(missing[:5], ensure_ascii=False)}")
            coverage_ok = False

    out = Path(args.out) if args.out else root / "_asset_manifest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"清单已写入 {out}")
    return 0 if coverage_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
