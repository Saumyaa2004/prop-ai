"""
Database-level guards for site visits (defense in depth).

Each test runs inside a transaction that is rolled back (tx_db), so nothing
is left behind in the development database.
"""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.models import Lead, Property, SiteVisit

IST = timezone(timedelta(hours=5, minutes=30))
SLOT = datetime(2026, 10, 18, 11, tzinfo=IST)


def make_lead(db, phone="+919000000001") -> Lead:
    lead = Lead(name="Test Buyer", phone=phone)
    db.add(lead)
    db.flush()
    return lead


def property_id(db, code="PAI-DEMO-002") -> int:
    return db.scalar(select(Property.id).where(Property.listing_code == code))


def add_visit(db, starts_at=SLOT, status="booked") -> None:
    db.add(SiteVisit(property_id=property_id(db), lead_id=make_lead_once(db).id,
                     starts_at=starts_at, status=status))
    db.flush()


def make_lead_once(db) -> Lead:
    return db.scalar(select(Lead).where(Lead.phone == "+919000000001")) or make_lead(db)


def test_one_booking_per_property_slot(tx_db):
    add_visit(tx_db)
    with pytest.raises(IntegrityError) as caught:
        add_visit(tx_db)
    assert caught.value.orig.diag.constraint_name == "uq_site_visits_booked_slot"


def test_cancelled_visit_frees_the_slot(tx_db):
    add_visit(tx_db, status="cancelled")
    add_visit(tx_db)  # no error: only 'booked' rows must be unique


def test_slot_must_be_on_the_hour_in_ist(tx_db):
    # Servers often run in UTC; the rule must not depend on the session timezone.
    tx_db.execute(text("SET LOCAL TIME ZONE 'UTC'"))
    add_visit(tx_db)  # 11:00 IST is fine

    for bad in (SLOT.replace(minute=30), SLOT.replace(hour=9), SLOT.replace(hour=18)):
        savepoint = tx_db.begin_nested()
        with pytest.raises(IntegrityError):
            add_visit(tx_db, starts_at=bad)
        savepoint.rollback()


def test_phone_is_unique(tx_db):
    make_lead(tx_db)
    with pytest.raises(IntegrityError):
        make_lead(tx_db)
