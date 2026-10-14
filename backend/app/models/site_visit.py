"""
Prop AI - SiteVisit model (the 'site_visits' table): a booked viewing.

The partial unique index is the double-booking guard: the database itself
refuses a second 'booked' visit for the same property and slot, even when two
requests arrive at the same moment.
"""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, in_list
from app.models.lead import Lead
from app.models.property import Property

VISIT_STATUSES = ("booked", "cancelled", "completed")

# Slots start on the hour, 10:00-17:00 India time. Truncate in IST, not in the
# session timezone: IST is UTC+05:30, so an IST hour is half past in UTC.
_IST_TIME = "starts_at AT TIME ZONE 'Asia/Kolkata'"
_ON_THE_HOUR_IN_HOURS = (
    f"date_trunc('hour', {_IST_TIME}) = {_IST_TIME} "
    f"AND extract(hour FROM {_IST_TIME}) BETWEEN 10 AND 17"
)


class SiteVisit(TimestampMixin, Base):
    __tablename__ = "site_visits"

    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"))
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id"))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(
        String(20), default="booked", server_default="booked"
    )

    property: Mapped[Property] = relationship()
    lead: Mapped[Lead] = relationship()

    __table_args__ = (
        CheckConstraint(in_list("status", VISIT_STATUSES), name="status_valid"),
        CheckConstraint(_ON_THE_HOUR_IN_HOURS, name="starts_at_on_the_hour"),
        # Only active bookings must be unique; a cancelled visit frees its slot.
        Index(
            "uq_site_visits_booked_slot",
            "property_id",
            "starts_at",
            unique=True,
            postgresql_where=text("status = 'booked'"),
        ),
    )
