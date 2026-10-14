"""
Prop AI - property endpoints.

A thin HTTP layer: FastAPI validates the input, the service does the work,
and the response schema decides which fields the client sees.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.property import PropertySearchFilters, PropertySearchResponse
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
