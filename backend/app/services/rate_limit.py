"""
Sliding-window rate limiter, used to protect the free Gemini quota.

"At most `limit` hits in any `window_seconds`", counted from each moment
rather than reset on the minute, so a burst at 0:59 and 1:01 still counts
as one burst.

Counts live in this process's memory: they reset on restart and aren't
shared between worker processes. Fine for one small server; a shared store
(e.g. Redis) would only be worth it once the app runs several workers.
"""

import threading
import time
from collections import deque
from collections.abc import Callable


class SlidingWindowLimiter:
    def __init__(
        self,
        limit: int,
        window_seconds: float,
        clock: Callable[[], float] = time.monotonic,  # monotonic: immune to clock changes
        max_keys: int = 10_000,
    ) -> None:
        if limit < 1 or window_seconds <= 0:
            raise ValueError("limit must be at least 1 and window_seconds positive")
        self.limit = limit
        self.window = window_seconds
        self._clock = clock
        self._max_keys = max_keys
        self._hits: dict[str, deque[float]] = {}
        # Requests run in parallel threads; without the lock two of them could
        # both see "4 of 5 used" and both get in.
        self._lock = threading.Lock()

    def hit(self, key: str) -> float | None:
        """Record a hit for `key`. None if allowed, else seconds until it would be."""
        now = self._clock()
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and hits[0] <= now - self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                return hits[0] + self.window - now  # blocked hits aren't recorded
            hits.append(now)
            if len(self._hits) > self._max_keys:
                self._forget_idle(now)
            return None

    @property
    def tracked(self) -> int:
        """How many keys (visitors) are currently held in memory."""
        return len(self._hits)

    def _forget_idle(self, now: float) -> None:
        """Drop keys whose latest hit has left the window: they have nothing to limit."""
        idle = [key for key, hits in self._hits.items() if hits[-1] <= now - self.window]
        for key in idle:
            del self._hits[key]
