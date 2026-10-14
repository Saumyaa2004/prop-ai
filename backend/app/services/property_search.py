"""
Prop AI - property search service.

The single implementation of property search. The HTTP router calls it
today; the AI agent's search tool will call the same function later.
It has no FastAPI imports on purpose, so it works outside a web request.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Property
from app.schemas.property import PropertySearchFilters


def search_properties(db: Session, filters: PropertySearchFilters) -> list[Property]:
    """Return available listings matching every filter that was provided."""
    statement = select(Property).where(
        Property.status == "available",
        # Always required: sale prices are totals, rent prices are monthly.
        Property.listing_type == filters.listing_type,
    )

    # Case-insensitive exact match, so "powai" finds "Powai".
    if filters.city is not None:
        statement = statement.where(func.lower(Property.city) == filters.city.lower())
    if filters.locality is not None:
        statement = statement.where(
            func.lower(Property.locality) == filters.locality.lower()
        )

    if filters.property_type is not None:
        statement = statement.where(Property.property_type == filters.property_type)
    if filters.bedrooms is not None:
        statement = statement.where(Property.bedrooms == filters.bedrooms)
    if filters.min_price is not None:
        statement = statement.where(Property.price_inr >= filters.min_price)
    if filters.max_price is not None:
        statement = statement.where(Property.price_inr <= filters.max_price)
    if filters.furnishing is not None:
        statement = statement.where(Property.furnishing == filters.furnishing)

    # ARRAY "contains" compiles to PostgreSQL's @> operator: the listing
    # must have ALL requested amenities (and may have more).
    if filters.amenities:
        statement = statement.where(Property.amenities.contains(filters.amenities))

    # Cheapest first; id breaks ties so the order is always the same.
    statement = statement.order_by(Property.price_inr, Property.id).limit(filters.limit)

    return list(db.scalars(statement))
