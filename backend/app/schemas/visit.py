"""
Prop AI - site visit API schemas.

Only types and size limits here; the booking rules (phone format, slot hours)
live in services/visits.py, the one implementation shared with the AI tools.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SlotsResponse(BaseModel):
    listing_code: str
    slots: list[datetime]  # IST, e.g. 2026-10-18T11:00:00+05:30


class VisitCreate(BaseModel):
    # forbid: a client can't sneak in fields like "status": "completed".
    model_config = ConfigDict(extra="forbid")

    listing_code: str = Field(min_length=1, max_length=20)
    starts_at: datetime  # without an offset it is taken as IST
    name: str = Field(max_length=100)
    phone: str = Field(max_length=20)


class VisitRead(BaseModel):
    """What the browser gets back. The phone is deliberately not included."""

    id: int
    listing_code: str
    title: str
    starts_at: datetime
    status: str
