"""
Prop AI - Lead model (the 'leads' table): a buyer who booked a visit.

One row per phone number. Booking again with the same number reuses the lead.
"""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Lead(TimestampMixin, Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    # Normalised "+91" + 10 digits, so different spellings of one number match.
    phone: Mapped[str] = mapped_column(String(13), unique=True)
