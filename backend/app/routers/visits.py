"""
Prop AI - site visit endpoints.

Thin HTTP layer over services/visits.py: each booking error type maps to one
status code, and its message is safe to show to the user.
"""

from dataclasses import asdict
from datetime import date
from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.routers.limits import RateLimits, enforce
from app.schemas.visit import SlotsResponse, VisitCreate, VisitRead
from app.services.visits import (
    InvalidDetails,
    InvalidSlot,
    ListingNotBookable,
    ListingNotFound,
    SlotTaken,
    VisitError,
    available_slots,
    book_visit,
)
from app.services.rate_limit import SlidingWindowLimiter

router = APIRouter(tags=["visits"])

STATUS_FOR_ERROR: dict[type[VisitError], int] = {
    ListingNotFound: 404,
    ListingNotBookable: 409,  # valid request, but the listing's state forbids it
    SlotTaken: 409,
    InvalidSlot: 422,
    InvalidDetails: 422,
}


def _http_error(exc: VisitError) -> HTTPException:
    return HTTPException(status_code=STATUS_FOR_ERROR[type(exc)], detail=str(exc))


@router.get("/properties/{listing_code}/slots", response_model=SlotsResponse)
def slots(
    listing_code: Annotated[str, Path(min_length=1, max_length=20)],
    day: Annotated[date | None, Query(alias="date")] = None,
    db: Session = Depends(get_db),
) -> SlotsResponse:
    """Free hourly visit slots (IST) for one listing, on one day or the next 14 days."""
    try:
        found = available_slots(db, listing_code, day)
    except VisitError as exc:
        raise _http_error(exc) from None
    return SlotsResponse(listing_code=listing_code.upper(), slots=found)


@lru_cache
def get_booking_limits() -> RateLimits:
    """Dependency: built once, so counts persist across requests."""
    settings = get_settings()
    return RateLimits(
        per_visitor=SlidingWindowLimiter(settings.visits_per_hour, 60 * 60),
        per_site=SlidingWindowLimiter(settings.visits_per_day, 24 * 60 * 60),
    )


def rate_limit_booking(request: Request, limits: RateLimits = Depends(get_booking_limits)) -> None:
    """Dependency: refuse with 429 before anything is written. Slot lookups stay unlimited."""
    enforce(
        limits,
        request,
        too_fast="Too many bookings from you. Please try again in {wait}.",
        site_full="Prop AI has reached its daily booking limit. Please try again later.",
    )


@router.post("/visits", response_model=VisitRead, status_code=201,
             dependencies=[Depends(rate_limit_booking)])
def create_visit(request: VisitCreate, db: Session = Depends(get_db)) -> VisitRead:
    """Book a site visit. The caller is a person who pressed Confirm, never the AI."""
    try:
        visit = book_visit(
            db, request.listing_code, request.starts_at, request.name, request.phone
        )
    except VisitError as exc:
        raise _http_error(exc) from None
    return VisitRead(**asdict(visit))
