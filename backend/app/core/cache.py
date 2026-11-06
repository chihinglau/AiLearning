"""P1-13 进程内 TTL 缓存：首页聚合与学情统计热点读，写入后按用户失效。

单实例部署使用进程内缓存；多实例部署时可将本模块替换为 Redis 实现，
调用方接口（get_or_set/invalidate_user/clear）保持不变。
"""

import time
from dataclasses import dataclass
from threading import Lock
from typing import Any, Callable, TypeVar

DEFAULT_TTL_SECONDS = 30.0

_T = TypeVar("_T")


@dataclass
class _Entry:
    value: Any
    expires_at: float


_lock = Lock()
_store: dict[str, _Entry] = {}
_hits = 0
_misses = 0


def get(key: str) -> Any:
    global _hits, _misses
    with _lock:
        entry = _store.get(key)
        if entry is None or entry.expires_at <= time.monotonic():
            _store.pop(key, None)
            _misses += 1
            return None
        _hits += 1
        return entry.value


def set(key: str, value: Any, ttl: float = DEFAULT_TTL_SECONDS) -> None:
    with _lock:
        _store[key] = _Entry(value=value, expires_at=time.monotonic() + ttl)


def get_or_set(
    key: str, loader: Callable[[], _T], ttl: float = DEFAULT_TTL_SECONDS
) -> _T:
    cached = get(key)
    if cached is not None:
        return cached
    value = loader()
    set(key, value, ttl)
    return value


def invalidate(key: str) -> None:
    with _lock:
        _store.pop(key, None)


def invalidate_prefix(prefix: str) -> None:
    with _lock:
        for key in [key for key in _store if key.startswith(prefix)]:
            _store.pop(key, None)


def invalidate_user(user_id: int) -> None:
    """练习/考试/教材变更后清理该用户的首页与学情缓存。"""
    invalidate_prefix(f"home:{user_id}:")
    invalidate(f"stats:{user_id}")


def clear() -> None:
    global _hits, _misses
    with _lock:
        _store.clear()
        _hits = 0
        _misses = 0


def stats() -> dict[str, int]:
    """缓存观测指标，便于压测与后续监控接入。"""
    with _lock:
        return {
            "entries": len(_store),
            "hits": _hits,
            "misses": _misses,
        }
