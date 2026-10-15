"""
Tests for the booking rate limits: per visitor per hour, and per site per day.
Without them a bot could book every slot and lock real buyers out.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.config import Settings
from app.database import get_db
from app.main import app
from app.models import SiteVisit
from app.routers.limits import RateLimits, wait_text
from app.routers.visits import get_booking_limits
from app.services.rate_limit import SlidingWindowLimiter
from app.services.visits import available_slots
from tests.test_rate_limit import FakeClock

CODE = "PAI-DEMO-002"


@pytest.fixture
def set_limits(tx_db):
    """Small limits on a fake clock; bookings go through tx_db and are rolled back."""
    clock = FakeClock()

    def install(per_hour: int, per_day: int) -> None:
        limits = RateLimits(
            per_visitor=SlidingWindowLimiter(per_hour, 60 * 60, clock=clock),
            per_site=SlidingWindowLimiter(per_day, 24 * 60 * 60, clock=clock),
        )
        app.dependency_overrides[get_booking_limits] = lambda: limits
        app.dependency_overrides[get_db] = lambda: tx_db

    yield install
    app.dependency_overrides.pop(get_booking_limits, None)
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def slots(tx_db):
    """Free slots, latest first, so tests can make several real bookings."""
    return list(reversed(available_slots(tx_db, CODE)))


def visitor(ip: str) -> TestClient:
    return TestClient(app, client=(ip, 50000))


def book(client: TestClient, slot):
    return client.post("/visits", json={"listing_code": CODE, "starts_at": slot.isoformat(),
                                        "name": "Asha Demo", "phone": "98765 43210"})


def visit_count(db) -> int:
    return db.scalar(select(func.count()).select_from(SiteVisit))


def test_a_person_can_book_3_visits_per_hour_by_default():
    # The owner's call: 3 per hour covers a real buyer, with room for a rebooking.
    assert Settings.model_fields["visits_per_hour"].default == 3


def test_fourth_booking_in_an_hour_gets_429_and_writes_nothing(set_limits, slots, tx_db):
    set_limits(per_hour=3, per_day=100)
    client = visitor("1.1.1.1")
    assert [book(client, slots[i]).status_code for i in range(3)] == [201, 201, 201]
    before = visit_count(tx_db)

    response = book(client, slots[3])

    assert response.status_code == 429
    assert response.headers["Retry-After"] == "3600"
    assert response.json()["detail"] == "Too many bookings from you. Please try again in 60 minutes."
    assert visit_count(tx_db) == before  # refused before any database write


def test_one_visitor_being_limited_does_not_block_others(set_limits, slots):
    set_limits(per_hour=1, per_day=100)
    book(visitor("1.1.1.1"), slots[0])
    assert book(visitor("1.1.1.1"), slots[1]).status_code == 429
    assert book(visitor("2.2.2.2"), slots[1]).status_code == 201


def test_daily_booking_cap_applies_across_all_visitors(set_limits, slots):
    set_limits(per_hour=3, per_day=2)
    assert book(visitor("1.1.1.1"), slots[0]).status_code == 201
    assert book(visitor("2.2.2.2"), slots[1]).status_code == 201

    response = book(visitor("3.3.3.3"), slots[2])

    assert response.status_code == 429
    assert "daily booking limit" in response.json()["detail"]


def test_checking_free_slots_is_never_limited(set_limits):
    set_limits(per_hour=1, per_day=1)
    client = visitor("1.1.1.1")
    assert [client.get(f"/properties/{CODE}/slots").status_code for _ in range(5)] == [200] * 5


@pytest.mark.parametrize(
    "seconds, text",
    [(1, "1 second"), (40, "40 seconds"), (60, "1 minute"), (61, "2 minutes"),
     (2220, "37 minutes"), (3600, "60 minutes"), (7200, "2 hours"), (7201, "3 hours")],
)
def test_wait_text_is_readable(seconds, text):
    assert wait_text(seconds) == text
