"""
Prop AI - site visit booking.

The single implementation used by the REST API and the AI agent's tools.
Slots are fixed hours, 10:00-17:00 India time, from today to 13 days ahead.
Double-booking is prevented by the database's unique index, not by a
check-then-insert in Python (which two simultaneous requests could both pass).
"""

import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Lead, Property, SiteVisit
from app.services.property_details import get_property_by_code

# India has no daylight saving, so a fixed offset is exact (no tz database needed).
IST = timezone(timedelta(hours=5, minutes=30), "IST")
SLOT_HOURS = range(10, 18)  # start hours: 10:00 ... 17:00
BOOKING_DAYS = 14  # today plus 13 days
SLOT_INDEX = "uq_site_visits_booked_slot"


class VisitError(Exception):
    """A booking problem with a message that is safe to show to the user."""


class ListingNotFound(VisitError):
    pass


class ListingNotBookable(VisitError):
    pass


class InvalidSlot(VisitError):
    pass


class InvalidDetails(VisitError):
    pass


class SlotTaken(VisitError):
    pass


@dataclass(frozen=True)
class BookedVisit:
    id: int
    listing_code: str
    title: str
    starts_at: datetime
    status: str


# [0-9], not \d: Python's \d also matches non-ASCII digits.
_PHONE = re.compile(r"(?:\+?91|0)?([6-9][0-9]{9})")


def normalise_phone(raw: str) -> str | None:
    """An Indian mobile number as '+91XXXXXXXXXX', or None if it isn't one."""
    digits = re.sub(r"[\s-]", "", raw)
    match = _PHONE.fullmatch(digits)
    return f"+91{match.group(1)}" if match else None


def parse_slot(value: str | datetime) -> datetime:
    """A slot time in IST. Times without an offset are taken as IST."""
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.strip())
        except ValueError:
            raise InvalidSlot("Please give the visit time as a date and hour.") from None
    if value.tzinfo is None:
        value = value.replace(tzinfo=IST)
    return value.astimezone(IST)


def slot_label(starts_at: datetime) -> str:
    """How a slot is shown and spoken, e.g. 'Sun 18 Oct, 11:00'."""
    local = starts_at.astimezone(IST)
    return f"{local:%a} {local.day} {local:%b}, {local:%H:%M}"


def _now(now: datetime | None) -> datetime:
    return (now or datetime.now(IST)).astimezone(IST)


def _window(now: datetime) -> tuple[date, date]:
    first = now.date()
    return first, first + timedelta(days=BOOKING_DAYS - 1)


def _bookable_listing(db: Session, listing_code: str) -> Property:
    listing = get_property_by_code(db, listing_code)
    if listing is None:
        raise ListingNotFound(f"No listing with code {listing_code}.")
    if listing.status != "available":
        raise ListingNotBookable("This listing is no longer available for visits.")
    return listing


def _booked_times(db: Session, property_id: int, start: datetime, end: datetime) -> set[datetime]:
    rows = db.scalars(
        select(SiteVisit.starts_at).where(
            SiteVisit.property_id == property_id,
            SiteVisit.status == "booked",
            SiteVisit.starts_at >= start,
            SiteVisit.starts_at < end,
        )
    )
    return {t.astimezone(IST) for t in rows}


def available_slots(
    db: Session, listing_code: str, day: date | None = None, now: datetime | None = None
) -> list[datetime]:
    """Free future slots for a listing: on one day, or across the whole window."""
    now = _now(now)
    listing = _bookable_listing(db, listing_code)
    first, last = _window(now)
    if day is not None and not first <= day <= last:
        raise InvalidSlot(f"Visits can be booked from {first:%d %b} to {last:%d %b}.")

    days = [day] if day else [first + timedelta(days=i) for i in range(BOOKING_DAYS)]
    candidates = [
        datetime.combine(d, time(hour), tzinfo=IST) for d in days for hour in SLOT_HOURS
    ]
    candidates = [c for c in candidates if c > now]
    if not candidates:
        return []
    taken = _booked_times(db, listing.id, candidates[0], candidates[-1] + timedelta(hours=1))
    return [c for c in candidates if c not in taken]


def check_slot(
    db: Session, listing_code: str, starts_at: datetime, now: datetime | None = None
) -> Property:
    """Raise a VisitError unless this slot can be booked right now."""
    now = _now(now)
    listing = _bookable_listing(db, listing_code)
    slot = parse_slot(starts_at)
    first, last = _window(now)

    if slot.minute or slot.second or slot.microsecond or slot.hour not in SLOT_HOURS:
        raise InvalidSlot("Visits start on the hour, between 10:00 and 17:00.")
    if slot <= now:
        raise InvalidSlot("That time has already passed. Please pick a later slot.")
    if slot.date() > last:
        raise InvalidSlot(f"Visits can be booked up to {last:%d %b}.")
    if slot in _booked_times(db, listing.id, slot, slot + timedelta(hours=1)):
        raise SlotTaken("That slot is already taken. Please pick another time.")
    return listing


def book_visit(
    db: Session,
    listing_code: str,
    starts_at: datetime,
    name: str,
    phone: str,
    now: datetime | None = None,
) -> BookedVisit:
    """Book a visit and return it as stored. Raises a VisitError on any problem."""
    clean_name = " ".join(name.split())
    if not 2 <= len(clean_name) <= 100:
        raise InvalidDetails("Please enter a name of 2 to 100 characters.")
    clean_phone = normalise_phone(phone)
    if clean_phone is None:
        raise InvalidDetails("Please enter a 10-digit Indian mobile number.")

    slot = parse_slot(starts_at)
    listing = check_slot(db, listing_code, slot, now)

    # One atomic statement: create the lead, or update the name if the phone exists.
    lead_id = db.scalar(
        insert(Lead)
        .values(name=clean_name, phone=clean_phone)
        .on_conflict_do_update(
            index_elements=[Lead.phone],
            set_={"name": clean_name, "updated_at": func.now()},
        )
        .returning(Lead.id)
    )
    visit = SiteVisit(property_id=listing.id, lead_id=lead_id, starts_at=slot)
    db.add(visit)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        # Another booking won the race between check_slot and this insert.
        if getattr(exc.orig.diag, "constraint_name", None) == SLOT_INDEX:
            raise SlotTaken("Sorry, that slot was just taken. Please pick another time.") from None
        raise

    # Post-write verification: answer from what the database actually stored.
    stored = db.scalars(
        select(SiteVisit).where(SiteVisit.id == visit.id).execution_options(populate_existing=True)
    ).one()
    return BookedVisit(
        id=stored.id,
        listing_code=listing.listing_code,
        title=listing.title,
        starts_at=stored.starts_at.astimezone(IST),
        status=stored.status,
    )
