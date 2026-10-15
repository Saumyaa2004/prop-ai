"""
Test doubles.

FakeLLM replays scripted replies and records what the agent sent, so agent
tests are fast, deterministic and spend no real LLM quota.
"""

from app.services.llm.base import LLMReply, Message, ToolCall, ToolSpec


class FakeLLM:
    def __init__(self, *replies: LLMReply | Exception, repeat_last: bool = False):
        self._replies = list(replies)
        self._repeat_last = repeat_last
        self.calls: list[list[Message]] = []  # history snapshot per generate()
        self.tools_seen: list[list[ToolSpec]] = []
        self.systems: list[str] = []  # system prompt per generate()

    def generate(self, system: str, history: list[Message], tools: list[ToolSpec]) -> LLMReply:
        self.systems.append(system)
        self.calls.append(list(history))
        self.tools_seen.append(tools)
        if not self._replies:
            raise AssertionError("FakeLLM ran out of scripted replies")
        reply = self._replies[0] if (self._repeat_last and len(self._replies) == 1) else self._replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


def tool_call(name: str, /, **args) -> LLMReply:
    """A model turn that requests one tool. (`/`: a tool argument may be called "name".)"""
    return LLMReply(text=None, tool_calls=[ToolCall(name=name, args=args, id=f"call-{name}")])


def answer(text: str) -> LLMReply:
    """A final text answer."""
    return LLMReply(text=text)
