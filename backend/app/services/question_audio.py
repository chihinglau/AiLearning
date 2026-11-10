"""TT-04 读题音频分发辅助：目录解析、未就绪响应、ETag 与返工清单。"""

from __future__ import annotations

import json
from pathlib import Path

from app.core.config import settings

BACKEND_DIR = Path(__file__).resolve().parents[2]

AUDIO_NOT_READY = {
    "code": "AUDIO_NOT_READY",
    "message": "该题朗读音频尚未生成，请使用系统朗读",
}


def audio_dir() -> Path:
    """生成目录：相对路径按 backend/ 解析，便于脚本与接口共用同一配置。"""
    path = Path(settings.question_audio_dir)
    return path if path.is_absolute() else BACKEND_DIR / path


def rework_ids() -> set[int]:
    """TT-07 返工清单：试听不达标的题目回退系统 TTS（接口返回 404）。"""
    path = audio_dir() / "rework.json"
    if not path.is_file():
        return set()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return {int(item) for item in raw.get("question_ids", [])}
    except (OSError, ValueError, TypeError):
        return set()


def etag_matches(header: str | None, etag: str) -> bool:
    if not header:
        return False
    tokens = {token.strip() for token in header.split(",") if token.strip()}
    return "*" in tokens or etag in tokens or etag.strip('"') in tokens
