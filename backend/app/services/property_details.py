"""
Prop AI - property details service.

Looks up listings by public code (HTTP router and AI agent) or by name (AI
agent only).
"""

import re

from sqlalchemy import or_, select
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


# Words people add that never appear in a listing's name.
_FILLER = {"a", "an", "the", "in", "at", "on", "of", "for", "to", "near", "flat",
           "apartment", "home", "house", "property", "listing", "one", "that", "this"}


def find_listings_by_name(db: Session, name: str, limit: int = 5) -> list[Property]:
    """Listings whose title or locality contains every meaningful word of `name`.

    For the AI agent: "Is Oberoi Link still for sale?" names a listing, not a
    locality. Any status is returned, like get_property_by_code.
    """
    words = [w for w in re.findall(r"[a-z0-9]+", name.lower()) if w not in _FILLER]
    if not words:
        return []
    # Each word must appear in the title or the locality ("... in Powai").
    # autoescape: a "%" or "_" typed by the user is text, not a LIKE wildcard.
    conditions = [
        or_(Property.title.icontains(w, autoescape=True), Property.locality.icontains(w, autoescape=True))
        for w in words
    ]
    query = select(Property).where(*conditions).order_by(Property.listing_code).limit(limit)
    return list(db.scalars(query))
