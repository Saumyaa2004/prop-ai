"""
Tests for the /chat rate limits: per visitor per minute, and per site per day.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers.chat import ChatLimits, get_chat_limits, get_llm
from app.services.rate_limit import SlidingWindowLimiter
from tests.fakes import FakeLLM, answer
from tests.test_rate_limit import FakeClock


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def set_limits(clock):
    """Install small limits on a fake clock, plus a FakeLLM that counts calls."""
    llm = FakeLLM(answer("Hi!"), repeat_last=True)

    def install(per_minute: int, per_day: int) -> FakeLLM:
        limits = ChatLimits(
            per_visitor=SlidingWindowLimiter(per_minute, 60, clock=clock),
            per_site=SlidingWindowLimiter(per_day, 24 * 60 * 60, clock=clock),
        )
        app.dependency_overrides[get_chat_limits] = lambda: limits
        app.dependency_overrides[get_llm] = lambda: llm
        return llm

    yield install
    app.dependency_overrides.pop(get_chat_limits, None)
    app.dependency_overrides.pop(get_llm, None)


def visitor(ip: str) -> TestClient:
    return TestClient(app, client=(ip, 50000))


def say_hi(client: TestClient):
    return client.post("/chat", json={"messages": [{"role": "user", "content": "hi"}]})


def test_too_many_messages_in_a_minute_get_429_without_calling_gemini(set_limits):
    llm = set_limits(per_minute=2, per_day=100)
    client = visitor("1.1.1.1")

    assert [say_hi(client).status_code for _ in range(2)] == [200, 200]
    response = say_hi(client)

    assert response.status_code == 429
    assert response.headers["Retry-After"] == "60"
    assert "too quickly" in response.json()["detail"]
    assert len(llm.calls) == 2  # the blocked message never reached the LLM


def test_visitor_can_chat_again_after_the_window(set_limits, clock):
    set_limits(per_minute=1, per_day=100)
    client = visitor("1.1.1.1")
    say_hi(client)
    assert say_hi(client).status_code == 429

    clock.now = 60
    assert say_hi(client).status_code == 200


def test_one_visitor_being_limited_does_not_block_others(set_limits):
    set_limits(per_minute=1, per_day=100)
    say_hi(visitor("1.1.1.1"))
    assert say_hi(visitor("1.1.1.1")).status_code == 429
    assert say_hi(visitor("2.2.2.2")).status_code == 200


def test_daily_cap_applies_across_all_visitors(set_limits):
    # Switching IPs gets past the per-visitor limit, but not the site's daily cap.
    set_limits(per_minute=10, per_day=2)
    assert say_hi(visitor("1.1.1.1")).status_code == 200
    assert say_hi(visitor("2.2.2.2")).status_code == 200

    response = say_hi(visitor("3.3.3.3"))

    assert response.status_code == 429
    assert "daily chat limit" in response.json()["detail"]
    assert int(response.headers["Retry-After"]) > 0


def test_a_blocked_flooder_does_not_use_up_the_daily_cap(set_limits):
    # Per-visitor is checked first, so blocked requests never count toward the day.
    set_limits(per_minute=1, per_day=2)
    flooder = visitor("6.6.6.6")
    statuses = [say_hi(flooder).status_code for _ in range(5)]
    assert statuses == [200, 429, 429, 429, 429]

    assert say_hi(visitor("7.7.7.7")).status_code == 200  # 2nd of 2 for the day
