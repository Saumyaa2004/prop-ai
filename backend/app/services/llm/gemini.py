"""
Prop AI - Gemini adapter.

The only module that imports the Google SDK. Translates neutral messages to
Gemini `Content`, and Gemini responses back to `LLMReply`.
"""

from typing import Any

from google import genai
from google.genai import errors, types

from app.services.llm.base import (
    AssistantMessage,
    LLMError,
    LLMReply,
    Message,
    ToolCall,
    ToolCallTurn,
    ToolResultMessage,
    ToolSpec,
    UserMessage,
)

# Overloaded (503) or rate-limited (429): worth one retry on the fallback model.
RETRYABLE_STATUS = {429, 503}


def to_contents(history: list[Message]) -> list[types.Content]:
    """Neutral history -> Gemini contents. Consecutive tool results share one turn."""
    contents: list[types.Content] = []
    for message in history:
        if isinstance(message, UserMessage):
            contents.append(types.Content(role="user", parts=[types.Part(text=message.text)]))
        elif isinstance(message, AssistantMessage):
            contents.append(types.Content(role="model", parts=[types.Part(text=message.text)]))
        elif isinstance(message, ToolCallTurn):
            # Re-send Gemini's own turn unchanged: it carries thought signatures
            # that Gemini 3 requires to accept the follow-up request.
            contents.append(message.reply.raw)
        elif isinstance(message, ToolResultMessage):
            part = types.Part.from_function_response(
                name=message.call.name, response=message.result
            )
            if message.call.id and part.function_response is not None:
                part.function_response.id = message.call.id
            previous = contents[-1] if contents else None
            if previous is not None and previous.role == "user" and all(
                p.function_response is not None for p in previous.parts or []
            ):
                previous.parts.append(part)
            else:
                contents.append(types.Content(role="user", parts=[part]))
    return contents


def to_reply(response: types.GenerateContentResponse) -> LLMReply:
    """Gemini response -> neutral reply."""
    if not response.candidates or response.candidates[0].content is None:
        return LLMReply(text=None)  # e.g. blocked by safety filters
    content = response.candidates[0].content
    calls = [
        ToolCall(name=call.name or "", args=dict(call.args or {}), id=call.id)
        for call in response.function_calls or []
    ]
    text = "".join(p.text for p in content.parts or [] if p.text and not p.thought).strip()
    return LLMReply(text=text or None, tool_calls=calls, raw=content)


class GeminiClient:
    """LLMClient backed by the Gemini API, with a fallback model."""

    def __init__(
        self,
        api_key: str,
        model: str,
        fallback_model: str | None = None,
        client: Any = None,  # injectable for tests
    ) -> None:
        self._client = client or genai.Client(api_key=api_key)
        self._models = [model] + ([fallback_model] if fallback_model else [])

    def generate(
        self, system: str, history: list[Message], tools: list[ToolSpec]
    ) -> LLMReply:
        config = types.GenerateContentConfig(
            system_instruction=system,
            tools=[
                types.Tool(
                    function_declarations=[
                        types.FunctionDeclaration(
                            name=t.name,
                            description=t.description,
                            parameters_json_schema=t.parameters,
                        )
                        for t in tools
                    ]
                )
            ]
            # No tools (e.g. the eval judge): send no block, not an empty one.
            if tools
            else None,
            # We run tools ourselves, so we can validate arguments and cap steps.
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )
        contents = to_contents(history)

        for index, model in enumerate(self._models):
            try:
                response = self._client.models.generate_content(
                    model=model, contents=contents, config=config
                )
                return to_reply(response)
            except errors.APIError as exc:
                is_last = index == len(self._models) - 1
                if exc.code in RETRYABLE_STATUS and not is_last:
                    continue  # try the fallback model
                # Status only: never include the request, which carries the key.
                raise LLMError(f"Gemini error {exc.code} {exc.status}") from exc
            except Exception as exc:  # network failures, timeouts
                raise LLMError("Gemini request failed") from exc
        raise LLMError("No Gemini model configured")
