"""
Prop AI - provider-neutral LLM types.

The agent only uses these types, never a provider SDK directly.
"""

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class ToolSpec:
    """A function the model may ask us to run. `parameters` is a JSON Schema."""

    name: str
    description: str
    parameters: dict[str, Any]


@dataclass(frozen=True)
class ToolCall:
    """The model asking us to run a tool with these arguments."""

    name: str
    args: dict[str, Any]
    id: str | None = None


@dataclass
class LLMReply:
    """One model turn: either tool calls, or a final text answer."""

    text: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)
    # The provider's own representation of this turn. Some providers (Gemini 3)
    # require it to be sent back unchanged. The agent never looks inside it.
    raw: Any = None


@dataclass(frozen=True)
class UserMessage:
    text: str


@dataclass(frozen=True)
class AssistantMessage:
    text: str


@dataclass(frozen=True)
class ToolCallTurn:
    """A past model turn that requested tools."""

    reply: LLMReply


@dataclass(frozen=True)
class ToolResultMessage:
    """What we send back after running a tool."""

    call: ToolCall
    result: dict[str, Any]


Message = UserMessage | AssistantMessage | ToolCallTurn | ToolResultMessage


class LLMError(Exception):
    """The provider failed (overloaded, rate-limited, network). Safe to show generically."""


class LLMClient(Protocol):
    """Anything with this method can power the agent (Gemini, a test fake, ...)."""

    def generate(
        self, system: str, history: list[Message], tools: list[ToolSpec]
    ) -> LLMReply: ...
