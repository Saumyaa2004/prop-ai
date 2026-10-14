"""
Prop AI - backend entry point.

This file creates the FastAPI application object that Uvicorn runs.
"""

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.routers import properties

# The application object. Uvicorn looks for this variable by name.
app = FastAPI(
    title="Prop AI API",
    description="Backend for Prop AI, a voice-first real estate assistant.",
    version="0.1.0",
)

# Let the frontend (a different origin, e.g. localhost:5173) read API responses.
# Exact origins only, never "*". GET only while the API is read-only, and no
# cookies until there is authentication.
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_methods=["GET"],
    allow_credentials=False,
)

# Each router adds a group of related endpoints, e.g. /properties/search.
app.include_router(properties.router)


@app.get("/health")
def health_check() -> dict[str, str]:
    """Report that the API process is running."""
    return {"status": "ok", "service": "Prop AI API"}


@app.get("/health/db")
def database_health_check(db: Session = Depends(get_db)) -> dict[str, str]:
    """Report whether the API can reach the PostgreSQL database."""
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        # Return a generic message: raw database errors can reveal
        # hostnames or usernames and should not be shown to clients.
        raise HTTPException(status_code=503, detail="Database unavailable") from exc
    return {"status": "ok", "database": "reachable"}