"""
Prop AI - Property model (the 'properties' table).

All listings seeded during development are fictional demonstration data.
"""

from datetime import date

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

# Allowed values, kept in Python so API validation can reuse them later.
LISTING_TYPES = ("sale", "rent")
PROPERTY_TYPES = ("apartment", "villa", "independent_house", "studio", "penthouse")
FURNISHING_TYPES = ("unfurnished", "semi_furnished", "fully_furnished")
PROPERTY_STATUSES = ("available", "under_offer", "sold", "rented")


def _in_list(column: str, values: tuple[str, ...]) -> str:
    """Build SQL like: listing_type IN ('sale', 'rent')"""
    quoted = ", ".join(f"'{value}'" for value in values)
    return f"{column} IN ({quoted})"


class Property(TimestampMixin, Base):
    """A property listing available for sale or rent."""

    __tablename__ = "properties"

    id: Mapped[int] = mapped_column(primary_key=True)
    listing_code: Mapped[str] = mapped_column(String(20), unique=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)

    listing_type: Mapped[str] = mapped_column(String(10))
    property_type: Mapped[str] = mapped_column(String(30))
    bedrooms: Mapped[int] = mapped_column(Integer)
    bathrooms: Mapped[int] = mapped_column(Integer)
    area_sqft: Mapped[int] = mapped_column(Integer)

    # Whole rupees. Total price when listing_type='sale', monthly rent when 'rent'.
    price_inr: Mapped[int] = mapped_column(BigInteger)

    city: Mapped[str] = mapped_column(String(100))
    locality: Mapped[str] = mapped_column(String(100))
    furnishing: Mapped[str] = mapped_column(String(20))
    amenities: Mapped[list[str]] = mapped_column(
        ARRAY(String(50)), default=list, server_default=text("'{}'")
    )
    available_from: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(
        String(20), default="available", server_default="available"
    )
    is_demo_data: Mapped[bool] = mapped_column(
        default=True, server_default=text("true")
    )

    __table_args__ = (
        CheckConstraint(_in_list("listing_type", LISTING_TYPES), name="listing_type_valid"),
        CheckConstraint(_in_list("property_type", PROPERTY_TYPES), name="property_type_valid"),
        CheckConstraint(_in_list("furnishing", FURNISHING_TYPES), name="furnishing_valid"),
        CheckConstraint(_in_list("status", PROPERTY_STATUSES), name="status_valid"),
        CheckConstraint("bedrooms >= 0", name="bedrooms_non_negative"),
        CheckConstraint("bathrooms >= 0", name="bathrooms_non_negative"),
        CheckConstraint("area_sqft > 0", name="area_positive"),
        CheckConstraint("price_inr > 0", name="price_positive"),
        Index("ix_properties_search", "listing_type", "city", "locality", "bedrooms"),
        Index("ix_properties_price_inr", "price_inr"),
        Index("ix_properties_amenities", "amenities", postgresql_using="gin"),
    )

    def __repr__(self) -> str:
        return f"<Property {self.listing_code} {self.listing_type} {self.locality}>"
    