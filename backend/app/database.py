"""
Prop AI - database connection.

Creates the SQLAlchemy engine (shared connection pool) and provides
one database session per API request.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

settings = get_settings()

# One engine for the whole app. pool_pre_ping checks a pooled connection
# is still alive before using it, avoiding errors after the database restarts.
engine = create_engine(settings.database_url, pool_pre_ping=True)

# A factory that creates new Session objects bound to our engine.
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """Give one request its own database session, and always close it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()