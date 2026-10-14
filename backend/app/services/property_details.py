"""
Prop AI - property details service.

Looks up one listing by its public code. Shared by the HTTP router and,
later, the AI agent's "get property details" tool.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Property


def get_property_by_code(db: Session, listing_code: str) -> Property | None:
    """Return the listing with this code, or None if it does not exist.

    Any status is returned (sold, rented, ...): when someone asks about a
    specific listing, "it's sold" is a true answer; "not found" would not be.
    """
    # Codes are stored upper-case, so "pai-demo-002 " finds "PAI-DEMO-002".
    code = listing_code.strip().upper()
    return db.scalar(select(Property).where(Property.listing_code == code))
