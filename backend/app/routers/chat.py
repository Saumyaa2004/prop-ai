"""
Prop AI - chat endpoint for the AI agent.
"""

from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.agent import run_agent
from app.services.llm.base import (
    AssistantMessage,
    LLMClient,
    LLMError,
    Message,
    UserMessage,
)
from app.services.llm.gemini import GeminiClient

router = APIRouter(tags=["chat"])


@lru_cache
def _gemini_client() -> GeminiClient:
    """Built once and reused (it holds an HTTP connection pool)."""
    settings = get_settings()
    return GeminiClient(
        api_key=settings.gemini_api_key.get_secret_value(),
        model=settings.gemini_model,
        fallback_model=settings.gemini_fallback_model,
    )


def get_llm() -> LLMClient:
    """Dependency: the configured LLM. Tests override this with a fake."""
    key = get_settings().gemini_api_key
    if key is None or not key.get_secret_value().strip():
        raise HTTPException(status_code=503, detail="The AI assistant is not configured.")
    return _gemini_client()


@router.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    llm: LLMClient = Depends(get_llm),
) -> ChatResponse:
    """Answer the latest user message using only real listings from the database."""
    history: list[Message] = [
        UserMessage(m.content) if m.role == "user" else AssistantMessage(m.content)
        for m in request.messages
    ]
    try:
        result = run_agent(db, history, llm)
    except LLMError as exc:
        # Generic message: provider details stay in server logs, not the client.
        raise HTTPException(
            status_code=503,
            detail="The AI assistant is temporarily unavailable. Please try again.",
        ) from exc
    return ChatResponse(reply=result.reply, listings=result.listings)
