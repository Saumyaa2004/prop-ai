"""
Tests for the site visit booking service.

A fixed NOW keeps slot tests deterministic. It is in January 2026, before
this feature existed: real bookings are always in the future, so none can
ever fall in the test window. Write tests use tx_db (rolled back); only the
race test commits, and it deletes its own rows.
"""

import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime

import pytest
from sqlalchemy import delete, func, select

from app.database import SessionLocal
from app.models import Lead, SiteVisit
from app.services.visits import (
    BOOKING_DAYS,
    IST,
    InvalidDetails,
    InvalidSlot,
    ListingNotBookable,
    ListingNotFound,
    SlotTaken,
    available_slots,
    book_visit,
    normalise_phone,
    parse_slot,
    slot_label,
)

NOW = datetime(2026, 1, 7, 9, 15, tzinfo=IST)  # Wednesday morning
SLOT = datetime(2026, 1, 11, 11, tzinfo=IST)  # Sunday 11:00
CODE = "PAI-DEMO-002"  # available
SOLD = "PAI-DEMO-011"


def book(db, starts_at=SLOT, name="Asha Demo", phone="98765 43210", code=CODE):
    return book_visit(db, code, starts_at, name, phone, now=NOW)


# ---------- pure helpers ----------


def test_normalise_phone():
    for raw in ("98765 43210", "+91-98765-43210", "09876543210", "919876543210"):
        assert normalise_phone(raw) == "+919876543210"
    for raw in ("12345 67890", "98765", "abc", ""):
        assert normalise_phone(raw) is None
    # Non-ASCII digits (here Devanagari) would make a second lead for one number.
    assert normalise_phone("9८७६५४३२१०") is None


def test_parse_slot_accepts_naive_offset_and_utc():
    for value in ("2026-01-11T11:00", "2026-01-11T11:00+05:30", "2026-01-11T05:30:00Z"):
        assert parse_slot(value) == SLOT
        assert parse_slot(value).utcoffset() == IST.utcoffset(None)
    with pytest.raises(InvalidSlot):
        parse_slot("soon")


def test_slot_label():
    assert slot_label(SLOT) == "Sun 11 Jan, 11:00"
    assert slot_label(datetime(2026, 11, 8, 10, tzinfo=IST)) == "Sun 8 Nov, 10:00"


# ---------- available slots ----------


def test_available_slots_window_and_hours(db):
    slots = available_slots(db, CODE, now=NOW)
    assert slots[0] == datetime(2026, 1, 7, 10, tzinfo=IST)
    assert {s.hour for s in slots} == set(range(10, 18))
    assert slots[-1].date() == date(2026, 1, 20)
    assert len(slots) == BOOKING_DAYS * 8


def test_slot_starting_now_is_not_offered(db):
    at_ten = available_slots(db, CODE, day=date(2026, 1, 7), now=NOW.replace(hour=10, minute=0))
    assert at_ten[0].hour == 11
    late = available_slots(db, CODE, day=date(2026, 1, 7), now=NOW.replace(hour=17, minute=30))
    assert late == []


def test_booked_slot_is_not_offered(tx_db):
    book(tx_db)
    assert SLOT not in available_slots(tx_db, CODE, day=SLOT.date(), now=NOW)


def test_day_outside_window_is_rejected(db):
    for day in (date(2026, 1, 6), date(2026, 1, 21)):
        with pytest.raises(InvalidSlot):
            available_slots(db, CODE, day=day, now=NOW)


# ---------- booking ----------


def test_book_visit_happy_path(tx_db):
    visit = book(tx_db)
    assert visit.status == "booked"
    assert visit.listing_code == CODE
    assert visit.title == "Hiranandani Gardens 2BHK"
    assert visit.starts_at == SLOT
    assert tx_db.get(SiteVisit, visit.id) is not None


def test_same_phone_any_format_reuses_lead(tx_db):
    book(tx_db, name="Asha", phone="98765 43210")
    book(tx_db, starts_at=SLOT.replace(hour=12), name="Asha K", phone="+91-98765-43210")
    leads = tx_db.scalars(select(Lead).where(Lead.phone == "+919876543210")).all()
    assert len(leads) == 1
    assert leads[0].name == "Asha K"


def test_taken_slot_raises(tx_db):
    book(tx_db)
    with pytest.raises(SlotTaken):
        book(tx_db, phone="91234 56789")


def test_not_bookable_and_unknown(tx_db):
    with pytest.raises(ListingNotBookable):
        book(tx_db, code=SOLD)
    with pytest.raises(ListingNotFound):
        book(tx_db, code="PAI-DEMO-999")


def test_invalid_slot_and_details(tx_db):
    bad_slots = (
        SLOT.replace(minute=30),
        SLOT.replace(hour=9),
        datetime(2026, 1, 7, 9, tzinfo=IST),  # before NOW
        datetime(2026, 1, 21, 11, tzinfo=IST),  # beyond 14 days
    )
    for bad in bad_slots:
        with pytest.raises(InvalidSlot):
            book(tx_db, starts_at=bad)
    with pytest.raises(InvalidDetails):
        book(tx_db, name=" A ")
    with pytest.raises(InvalidDetails):
        book(tx_db, phone="12345")
    assert tx_db.scalar(select(func.count()).select_from(Lead).where(Lead.name == "Asha Demo")) == 0


# ---------- concurrency ----------


def test_race_window_is_caught_by_the_index(tx_db, monkeypatch):
    """Simulate both requests passing the Python check: the index still refuses one."""
    monkeypatch.setattr("app.services.visits._booked_times", lambda *args: set())
    book(tx_db)
    with pytest.raises(SlotTaken, match="just taken"):
        book(tx_db, phone="91234 56789")


def test_two_simultaneous_bookings_one_wins():
    """Two buyers press Confirm at the same moment: exactly one gets the slot."""
    with SessionLocal() as db:
        slot = available_slots(db, CODE)[-1]  # last free slot: unlikely to be in use
    phones = ["+919000000001", "+919000000002"]
    start_together = threading.Barrier(2)

    def attempt(phone: str) -> str:
        with SessionLocal() as db:
            start_together.wait()
            try:
                book_visit(db, CODE, slot, "Race Test", phone)
                return "booked"
            except SlotTaken:
                return "taken"

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = sorted(pool.map(attempt, phones))
        assert results == ["booked", "taken"]
    finally:
        with SessionLocal() as db:
            lead_ids = select(Lead.id).where(Lead.phone.in_(phones))
            db.execute(delete(SiteVisit).where(SiteVisit.lead_id.in_(lead_ids)))
            db.execute(delete(Lead).where(Lead.phone.in_(phones)))
            db.commit()
