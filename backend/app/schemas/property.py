"""
Prop AI - API schemas for properties.

Schemas define the shape of data entering and leaving the API.
They are separate from database models on purpose: the API exposes
only what clients should see, and validates what clients send.
"""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ListingType = Literal["sale", "rent"]
PropertyType = Literal["apartment", "villa", "independent_house", "studio", "penthouse"]
FurnishingType = Literal["unfurnished", "semi_furnished", "fully_furnished"]


class PropertySearchFilters(BaseModel):
    """Structured filters for searching available properties."""

    # Reject unknown parameters, e.g. a typo like 'max_prise'.
    model_config = ConfigDict(extra="forbid")

    listing_type: ListingType = Field(
        description="'sale' (price is total) or 'rent' (price is monthly). Required."
    )
    city: str | None = Field(default=None, max_length=100)
    locality: str | None = Field(default=None, max_length=100)
    property_type: PropertyType | None = None
    bedrooms: int | None = Field(default=None, ge=0, le=20)
    min_price: int | None = Field(default=None, ge=0, description="Whole rupees")
    max_price: int | None = Field(default=None, ge=0, description="Whole rupees")
    furnishing: FurnishingType | None = None
    amenities: list[str] = Field(
        default_factory=list, description="Listings must have ALL of these"
    )
    limit: int = Field(default=20, ge=1, le=50)

    @field_validator("city", "locality")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        """Treat blank text as 'no filter' and trim stray spaces."""
        if value is None:
            return None
        value = value.strip()
        return value or None

    @field_validator("amenities")
    @classmethod
    def normalize_amenities(cls, values: list[str]) -> list[str]:
        """'Parking ' and 'parking' should mean the same thing."""
        return sorted({v.strip().lower() for v in values if v.strip()})

    @model_validator(mode="after")
    def check_price_range(self) -> "PropertySearchFilters":
        if (
            self.min_price is not None
            and self.max_price is not None
            and self.min_price > self.max_price
        ):
            raise ValueError("min_price cannot be greater than max_price")
        return self


class PropertyRead(BaseModel):
    """A property as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    listing_code: str
    title: str
    description: str
    listing_type: ListingType
    property_type: str
    bedrooms: int
    bathrooms: int
    area_sqft: int
    price_inr: int
    city: str
    locality: str
    furnishing: str
    amenities: list[str]
    status: str
    available_from: date | None
    is_demo_data: bool


class PropertySearchResponse(BaseModel):
    """Search results plus a count.

    `count` is the number of results returned (at most `limit`),
    not the total number of matching listings in the database.
    """

    count: int
    results: list[PropertyRead]