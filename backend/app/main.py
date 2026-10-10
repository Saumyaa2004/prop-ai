"""
Prop AI - backend entry point.

This file creates the FastAPI application object that Uvicorn runs.
For now it exposes only a health-check endpoint.
"""

from fastapi import FastAPI

# The application object. Uvicorn looks for this variable by name.
app = FastAPI(
    title="Prop AI API",
    description="Backend for Prop AI, a voice-first real estate assistant.",
    version="0.1.0",
)


@app.get("/health")
def health_check() -> dict[str, str]:
    """Report that the API process is running.

    Deployment platforms and monitoring tools call this endpoint
    to confirm the service is alive.
    """
    return {"status": "ok", "service": "Prop AI API"}