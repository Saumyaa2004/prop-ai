"""
Prop AI - chat API schemas.

Stateless for now: the client sends the conversation so far on every request.
Limits protect the free LLM quota and keep prompts small.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.property import PropertyRead


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=1000)


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    messages: list[ChatMessage] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def last_message_is_from_user(self) -> "ChatRequest":
        if self.messages[-1].role != "user":
            raise ValueError("The last message must be from the user")
        return self


class VisitProposalRead(BaseModel):
    """A slot the agent proposed. Nothing is booked until the user confirms."""

    listing_code: str
    title: str
    starts_at: datetime
    label: str


class ChatResponse(BaseModel):
    """`listings` and `visit_proposal` come from tool results only, never from the model's text."""

    reply: str
    listings: list[PropertyRead]
    visit_proposal: VisitProposalRead | None = None
