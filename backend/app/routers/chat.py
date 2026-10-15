"""
Prop AI - chat endpoint for the AI agent.
"""

from dataclasses import dataclass
from functools import lru_cache
from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.schemas.chat import ChatRequest, ChatResponse, VisitProposalRead
from app.services.agent import run_agent
from app.services.llm.base import (
    AssistantMessage,
    LLMClient,
    LLMError,
    Message,
    UserMessage,
)
from app.services.llm.gemini import GeminiClient
from app.services.rate_limit import SlidingWindowLimiter

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


@dataclass(frozen=True)
class ChatLimits:
    per_visitor: SlidingWindowLimiter  # keyed by IP, per minute
    per_site: SlidingWindowLimiter  # one key for everyone, per day


@lru_cache
def get_chat_limits() -> ChatLimits:
    """Dependency: built once, so counts persist across requests."""
    settings = get_settings()
    return ChatLimits(
        per_visitor=SlidingWindowLimiter(settings.chat_per_minute, 60),
        per_site=SlidingWindowLimiter(settings.chat_per_day, 24 * 60 * 60),
    )


def _too_many(detail: str, wait: float) -> HTTPException:
    seconds = max(1, ceil(wait))
    return HTTPException(status_code=429, detail=detail.format(seconds=seconds),
                         headers={"Retry-After": str(seconds)})


def rate_limit_chat(request: Request, limits: ChatLimits = Depends(get_chat_limits)) -> None:
    """Dependency: refuse with 429 before any Gemini call is made.

    Per-visitor first: a flooder's blocked requests then never count toward
    the site's daily cap, so one person can't use it up for everyone.
    Behind a hosting proxy, request.client is the proxy unless uvicorn runs
    with --proxy-headers (set at deploy time).
    """
    visitor = request.client.host if request.client else "unknown"
    wait = limits.per_visitor.hit(visitor)
    if wait is not None:
        raise _too_many("You're sending messages too quickly. "
                        "Please wait {seconds} seconds and try again.", wait)
    wait = limits.per_site.hit("site")
    if wait is not None:
        raise _too_many("Prop AI has reached its daily chat limit. Please try again later; "
                        "search and listings still work.", wait)


@router.post("/chat", response_model=ChatResponse, dependencies=[Depends(rate_limit_chat)])
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
    proposal = result.visit_proposal
    return ChatResponse(
        reply=result.reply,
        listings=result.listings,
        visit_proposal=VisitProposalRead(**vars(proposal)) if proposal else None,
    )
