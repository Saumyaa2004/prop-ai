"""
Shared pytest fixtures.

These tests run against the development database and expect the fictional
demo listings from app/seed.py to be present (run `python -m app.seed`).
They only read data; nothing is written.
"""

import pytest
from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app


@pytest.fixture
def client():
    """An in-process HTTP client: no running server needed."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db():
    """A database session for calling services directly, like an AI tool would."""
    with SessionLocal() as session:
        yield session
