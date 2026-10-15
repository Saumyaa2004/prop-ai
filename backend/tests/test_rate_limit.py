"""
Tests for the sliding-window rate limiter that protects the Gemini quota.

A fake clock moves time forward instantly, so no test sleeps.
"""

import threading
import time
from collections import deque

import pytest

from app.services import rate_limit
from app.services.rate_limit import SlidingWindowLimiter


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_allows_up_to_the_limit_then_blocks():
    limiter = SlidingWindowLimiter(limit=3, window_seconds=60, clock=FakeClock())
    assert [limiter.hit("a") for _ in range(3)] == [None, None, None]
    assert limiter.hit("a") is not None


def test_wait_lasts_until_the_oldest_hit_leaves_the_window():
    clock = FakeClock()
    limiter = SlidingWindowLimiter(limit=2, window_seconds=60, clock=clock)
    limiter.hit("a")  # t=0
    clock.now = 10
    limiter.hit("a")
    clock.now = 20
    assert limiter.hit("a") == 40  # the t=0 hit expires at t=60


def test_window_slides_instead_of_resetting():
    clock = FakeClock()
    limiter = SlidingWindowLimiter(limit=2, window_seconds=60, clock=clock)
    limiter.hit("a")  # t=0
    clock.now = 30
    limiter.hit("a")
    clock.now = 60
    assert limiter.hit("a") is None  # the t=0 hit has left
    assert limiter.hit("a") is not None  # the t=30 one is still inside


def test_blocked_attempts_are_not_counted():
    # Otherwise a user who keeps retrying would stay blocked forever.
    clock = FakeClock()
    limiter = SlidingWindowLimiter(limit=1, window_seconds=60, clock=clock)
    limiter.hit("a")
    for t in range(1, 60):
        clock.now = t
        assert limiter.hit("a") is not None
    clock.now = 60
    assert limiter.hit("a") is None


def test_visitors_have_separate_limits():
    limiter = SlidingWindowLimiter(limit=1, window_seconds=60, clock=FakeClock())
    assert limiter.hit("a") is None
    assert limiter.hit("a") is not None
    assert limiter.hit("b") is None


def test_idle_visitors_are_forgotten():
    # Without this, every IP that ever visited would stay in memory.
    clock = FakeClock()
    limiter = SlidingWindowLimiter(limit=5, window_seconds=60, clock=clock, max_keys=2)
    limiter.hit("a")
    limiter.hit("b")
    clock.now = 61
    limiter.hit("c")
    assert limiter.tracked == 1


def test_concurrent_requests_cannot_exceed_the_limit(monkeypatch):
    # FastAPI runs sync endpoints in parallel threads: check-and-record must be atomic.
    # The race window is normally too short to hit, so widen it: after counting
    # the hits, pause 1 ms, letting other threads run between the check and the record.
    class SlowDeque(deque):
        def __len__(self):
            count = super().__len__()
            time.sleep(0.001)  # the count may now be stale
            return count

    monkeypatch.setattr(rate_limit, "deque", SlowDeque)
    limiter = SlidingWindowLimiter(limit=5, window_seconds=60)
    start = threading.Barrier(20)
    allowed = []

    def visit():
        start.wait()
        if limiter.hit("a") is None:
            allowed.append(1)

    threads = [threading.Thread(target=visit) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(allowed) == 5


@pytest.mark.parametrize("limit, window", [(0, 60), (5, 0), (-1, 60)])
def test_rejects_nonsense_settings(limit, window):
    with pytest.raises(ValueError):
        SlidingWindowLimiter(limit=limit, window_seconds=window)
