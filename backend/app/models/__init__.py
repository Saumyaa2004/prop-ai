"""
Prop AI - database models.

Import every model here so Base.metadata knows about all tables.
Alembic imports this package to detect schema changes.
"""

from app.models.base import Base
from app.models.property import Property

__all__ = ["Base", "Property"]