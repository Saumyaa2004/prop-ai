"""
Prop AI - property endpoints.

A thin HTTP layer: FastAPI validates the input, the service does the work,
and the response schema decides which fields the client sees.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.property import (
    PropertyRead,
    PropertySearchFilters,
    PropertySearchResponse,
)
from app.services.property_details import get_property_by_code
from app.services.property_search import search_properties

router = APIRouter(prefix="/properties", tags=["properties"])


@router.get("/search", response_model=PropertySearchResponse)
def search(
    # Query() tells FastAPI to build the whole model from query parameters,
    # e.g. ?listing_type=sale&locality=Powai&amenities=parking&amenities=gym
    filters: Annotated[PropertySearchFilters, Query()],
    db: Session = Depends(get_db),
) -> PropertySearchResponse:
    """Search available properties. `listing_type` is required."""
    results = search_properties(db, filters)
    return PropertySearchResponse(
        count=len(results),
        results=results,
    )


# Must stay BELOW /search: routes are matched top to bottom, and this
# pattern would otherwise capture "/properties/search" as a listing code.
@router.get("/{listing_code}", response_model=PropertyRead)
def get_details(
    # Same limit as the database column; longer codes cannot exist.
    listing_code: Annotated[str, Path(min_length=1, max_length=20)],
    db: Session = Depends(get_db),
) -> PropertyRead:
    """Get one listing by its code, e.g. PAI-DEMO-002. Returns any status."""
    found = get_property_by_code(db, listing_code)
    if found is None:
        # Generic message: don't echo user input back into error responses.
        raise HTTPException(status_code=404, detail="Property not found")
    return found
