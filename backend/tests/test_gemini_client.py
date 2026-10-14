"""
Tests for the Gemini adapter: message translation and the fallback rule.
A fake SDK client is injected, so nothing touches the network.
"""

import pytest
from google.genai import errors, types

from app.services.llm.base import (
    AssistantMessage,
    LLMError,
    LLMReply,
    ToolCall,
    ToolCallTurn,
    ToolResultMessage,
    UserMessage,
)
from app.services.llm.gemini import GeminiClient, to_contents, to_reply


def api_error(code: int) -> errors.APIError:
    return errors.APIError(code, {"error": {"code": code, "status": "X", "message": "test"}})


def text_response(text: str) -> types.GenerateContentResponse:
    return types.GenerateContentResponse(
        candidates=[
            types.Candidate(content=types.Content(role="model", parts=[types.Part(text=text)]))
        ]
    )


class FakeModels:
    """Stands in for client.models; replays results and records model names."""

    def __init__(self, *results):
        self.results = list(results)
        self.models_called: list[str] = []

    def generate_content(self, *, model, contents, config):
        self.models_called.append(model)
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class FakeSdkClient:
    def __init__(self, *results):
        self.models = FakeModels(*results)


def make_client(*results) -> tuple[GeminiClient, FakeModels]:
    sdk = FakeSdkClient(*results)
    client = GeminiClient(api_key="unused", model="main", fallback_model="backup", client=sdk)
    return client, sdk.models


# ---------- translation ----------


def test_to_contents_maps_roles_and_merges_tool_results():
    raw_model_turn = types.Content(role="model", parts=[types.Part(text="calling tools")])
    history = [
        UserMessage("hi"),
        AssistantMessage("hello"),
        ToolCallTurn(LLMReply(text=None, raw=raw_model_turn)),
        ToolResultMessage(ToolCall("search_properties", {}, id="a"), {"count": 0}),
        ToolResultMessage(ToolCall("get_property_details", {}, id="b"), {"error": "x"}),
    ]

    contents = to_contents(history)

    assert [c.role for c in contents] == ["user", "model", "model", "user"]
    # Gemini's own turn is re-sent unchanged (it may carry thought signatures).
    assert contents[2] is raw_model_turn
    # Both tool results travel together in one user turn, with their call ids.
    responses = [p.function_response for p in contents[3].parts]
    assert [r.name for r in responses] == ["search_properties", "get_property_details"]
    assert [r.id for r in responses] == ["a", "b"]


def test_to_reply_reads_function_calls():
    response = types.GenerateContentResponse(
        candidates=[
            types.Candidate(
                content=types.Content(
                    role="model",
                    parts=[
                        types.Part(
                            function_call=types.FunctionCall(
                                name="search_properties", args={"listing_type": "rent"}, id="c1"
                            )
                        )
                    ],
                )
            )
        ]
    )

    reply = to_reply(response)

    assert reply.tool_calls == [ToolCall("search_properties", {"listing_type": "rent"}, "c1")]
    assert reply.text is None
    assert reply.raw is response.candidates[0].content


def test_to_reply_handles_a_blocked_response():
    assert to_reply(types.GenerateContentResponse(candidates=[])).text is None


# ---------- fallback ----------


def test_overloaded_model_falls_back_once():
    client, models = make_client(api_error(503), text_response("from backup"))

    reply = client.generate("system", [UserMessage("hi")], [])

    assert reply.text == "from backup"
    assert models.models_called == ["main", "backup"]


def test_rate_limit_also_falls_back():
    client, models = make_client(api_error(429), text_response("ok"))

    assert client.generate("system", [UserMessage("hi")], []).text == "ok"


def test_both_models_failing_raises_llm_error():
    client, _ = make_client(api_error(503), api_error(503))

    with pytest.raises(LLMError):
        client.generate("system", [UserMessage("hi")], [])


def test_non_retryable_error_does_not_fall_back():
    client, models = make_client(api_error(400))

    with pytest.raises(LLMError):
        client.generate("system", [UserMessage("hi")], [])
    assert models.models_called == ["main"]


def test_error_message_never_contains_the_api_key():
    sdk = FakeSdkClient(api_error(403))
    client = GeminiClient(api_key="SECRET-KEY-123", model="main", client=sdk)

    with pytest.raises(LLMError) as info:
        client.generate("system", [UserMessage("hi")], [])
    assert "SECRET-KEY-123" not in str(info.value)
