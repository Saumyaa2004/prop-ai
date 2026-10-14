"""
Prop AI - database models.

Import every model here so Base.metadata knows about all tables.
Alembic imports this package to detect schema changes.
"""

from app.models.base import Base
from app.models.lead import Lead
from app.models.property import Property
from app.models.site_visit import SiteVisit

__all__ = ["Base", "Lead", "Property", "SiteVisit"]