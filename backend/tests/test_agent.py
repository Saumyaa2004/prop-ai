"""
Tests for the agent loop and its tools, using FakeLLM (no network, no quota).

Expected listings come from the fictional seed data in app/seed.py.
"""

from app.schemas.property import PropertySearchFilters
from app.services.agent import MAX_STEPS, SEARCH_TOOL, run_agent, run_tool
from app.services.llm.base import ToolCall, ToolResultMessage, UserMessage
from tests.fakes import FakeLLM, answer, tool_call


def codes(listings) -> list[str]:
    return [p.listing_code for p in listings]


def last_tool_result(llm: FakeLLM) -> dict:
    """The tool result the agent sent back on the model's latest turn."""
    message = llm.calls[-1][-1]
    assert isinstance(message, ToolResultMessage)
    return message.result


# ---------- happy path ----------


def test_search_tool_returns_real_listings(db):
    llm = FakeLLM(
        tool_call(
            "search_properties",
            listing_type="sale",
            locality="Powai",
            bedrooms=2,
            max_price=15_000_000,
            amenities=["parking"],
        ),
        answer("I found two options in Powai."),
    )

    result = run_agent(db, [UserMessage("2BHK in Powai under 1.5 crore with parking")], llm)

    assert result.reply == "I found two options in Powai."
    assert codes(result.listings) == ["PAI-DEMO-002", "PAI-DEMO-001"]
    sent = last_tool_result(llm)
    assert sent["count"] == 2
    # The model gets ready-made labels instead of doing rupee arithmetic.
    assert sent["results"][0]["price_label"] == "₹1.38 Cr"


def test_rent_search_never_returns_sale_listings(db):
    llm = FakeLLM(
        tool_call("search_properties", listing_type="rent", max_price=50_000),
        answer("Here are rentals."),
    )

    result = run_agent(db, [UserMessage("rent under 50k")], llm)

    assert codes(result.listings) == ["PAI-DEMO-014", "PAI-DEMO-012", "PAI-DEMO-015"]
    assert all(p.listing_type == "rent" for p in result.listings)


def test_chat_search_defaults_to_five_results(db):
    # 9 sale listings are available; chat answers should stay short.
    result, found = run_tool(db, ToolCall("search_properties", {"listing_type": "sale"}))

    assert result["count"] == 5
    assert len(found) == 5


def test_details_tool_returns_any_status(db):
    result, found = run_tool(db, ToolCall("get_property_details", {"listing_code": "pai-demo-011"}))

    assert result["status"] == "sold"
    assert codes(found) == ["PAI-DEMO-011"]


# ---------- bad tool calls are survivable ----------


def test_missing_listing_type_is_sent_back_as_an_error(db):
    llm = FakeLLM(
        tool_call("search_properties", locality="Powai"),
        answer("Are you looking to buy or rent?"),
    )

    result = run_agent(db, [UserMessage("something in Powai")], llm)

    error = last_tool_result(llm)["error"]
    assert "listing_type" in error
    assert result.reply == "Are you looking to buy or rent?"
    assert result.listings == []


def test_unknown_listing_code_is_an_error_not_a_crash(db):
    result, found = run_tool(db, ToolCall("get_property_details", {"listing_code": "PAI-DEMO-999"}))

    assert "No listing" in result["error"]
    assert found == []


def test_unknown_tool_is_an_error(db):
    result, found = run_tool(db, ToolCall("delete_everything", {}))

    assert "Unknown tool" in result["error"]
    assert found == []


# ---------- guardrails ----------


def test_step_limit_stops_a_looping_model(db):
    llm = FakeLLM(tool_call("search_properties", listing_type="sale"), repeat_last=True)

    result = run_agent(db, [UserMessage("loop forever")], llm)

    assert len(llm.calls) == MAX_STEPS
    assert "too many steps" in result.reply


def test_listings_only_come_from_tool_results(db):
    # The model mentions a code without calling a tool: nothing is shown as a listing.
    llm = FakeLLM(answer("Try PAI-DEMO-009, a lovely penthouse!"))

    result = run_agent(db, [UserMessage("anything nice?")], llm)

    assert result.listings == []


def test_empty_model_answer_gets_a_fallback_reply(db):
    result = run_agent(db, [UserMessage("hi")], FakeLLM(answer("")))

    assert "rephrase" in result.reply


def test_search_tool_schema_matches_the_api_filters():
    # The hand-written tool schema must not drift from PropertySearchFilters.
    properties = set(SEARCH_TOOL.parameters["properties"])

    assert properties == set(PropertySearchFilters.model_fields)
    assert SEARCH_TOOL.parameters["required"] == ["listing_type"]
