"""
Shared pytest fixtures.

These tests run against the development database and expect the fictional
demo listings from app/seed.py to be present (run `python -m app.seed`).
Tests that write use tx_db / tx_client: everything they write is rolled back.
"""

import pytest
from fastapi.testclient import TestClient

from sqlalchemy.orm import Session

from app.database import SessionLocal, engine, get_db
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


@pytest.fixture
def tx_db():
    """A session inside a transaction that is always rolled back.

    create_savepoint: the code under test can still call commit() (it commits a
    savepoint), but the outer transaction is undone after the test.
    """
    with engine.connect() as connection:
        outer = connection.begin()
        session = Session(
            bind=connection,
            join_transaction_mode="create_savepoint",
            autoflush=False,
            expire_on_commit=False,
        )
        try:
            yield session
        finally:
            session.close()
            outer.rollback()


@pytest.fixture
def tx_client(tx_db):
    """An HTTP client whose requests use tx_db, so API writes are rolled back too."""
    app.dependency_overrides[get_db] = lambda: tx_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)
