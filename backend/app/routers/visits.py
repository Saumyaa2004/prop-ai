"""
Prop AI - site visit endpoints.

Thin HTTP layer over services/visits.py: each booking error type maps to one
status code, and its message is safe to show to the user.
"""

from dataclasses import asdict
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from app.database import get_db
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


@router.post("/visits", response_model=VisitRead, status_code=201)
def create_visit(request: VisitCreate, db: Session = Depends(get_db)) -> VisitRead:
    """Book a site visit. The caller is a person who pressed Confirm, never the AI."""
    try:
        visit = book_visit(
            db, request.listing_code, request.starts_at, request.name, request.phone
        )
    except VisitError as exc:
        raise _http_error(exc) from None
    return VisitRead(**asdict(visit))
