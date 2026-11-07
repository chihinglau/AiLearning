"""进程内滑动窗口限流（R-02 生产化：登录/注册防爆破）。

单实例部署适用；多实例/多进程需替换为 Redis 等共享存储。
"""

import time
from collections import deque
from threading import Lock


class SlidingWindowLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = {}
        self._lock = Lock()

    def allow(
        self,
        key: str,
        limit: int,
        window_seconds: float = 60.0,
        now: float | None = None,
    ) -> tuple[bool, int]:
        """返回 (是否放行, Retry-After 秒数)。"""
        current = time.monotonic() if now is None else now
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            boundary = current - window_seconds
            while hits and hits[0] <= boundary:
                hits.popleft()
            if len(hits) >= limit:
                retry_after = max(1, int(hits[0] + window_seconds - current) + 1)
                return False, retry_after
            hits.append(current)
            return True, 0

    def reset(self, key: str | None = None) -> None:
        with self._lock:
            if key is None:
                self._hits.clear()
            else:
                self._hits.pop(key, None)


rate_limiter = SlidingWindowLimiter()
