"""
Tests for the agent's visit tools: it can check and propose, never book.
"""

from datetime import datetime

from sqlalchemy import func, select

from app.main import app
from app.models import SiteVisit
from app.routers.chat import get_llm
from app.services.agent import TOOLS, run_agent
from app.services.llm.base import ToolResultMessage, UserMessage
from app.services.privacy import redact_phone_numbers
from app.services.visits import IST, available_slots, book_visit
from tests.fakes import FakeLLM, answer, tool_call

NOW = datetime(2026, 10, 14, 12, tzinfo=IST)  # Wednesday noon
CODE = "PAI-DEMO-002"


def visit_count(db) -> int:
    return db.scalar(select(func.count()).select_from(SiteVisit))


def last_tool_result(llm: FakeLLM) -> dict:
    message = llm.calls[-1][-1]
    assert isinstance(message, ToolResultMessage)
    return message.result


def test_propose_visit_returns_proposal_from_tool_result(tx_db):
    before = visit_count(tx_db)
    llm = FakeLLM(
        tool_call("propose_visit", listing_code=CODE, starts_at="2026-10-18T11:00"),
        answer("Sunday at 11 is free. Tap Confirm on the card to book it."),
    )

    result = run_agent(tx_db, [UserMessage("Book the Powai one on Sunday at 11")], llm, now=NOW)

    proposal = result.visit_proposal
    assert proposal is not None
    assert proposal.listing_code == CODE
    assert proposal.title == "Hiranandani Gardens 2BHK"
    assert proposal.starts_at == datetime(2026, 10, 18, 11, tzinfo=IST)
    assert proposal.label == "Sun 18 Oct, 11:00"
    assert visit_count(tx_db) == before  # proposing writes nothing


def test_taken_or_invalid_proposal_is_an_error_for_the_model(tx_db):
    book_visit(tx_db, CODE, datetime(2026, 10, 18, 11, tzinfo=IST), "Asha Demo", "98765 43210", now=NOW)
    for starts_at in ("2026-10-18T11:00", "2026-10-18T20:00", "whenever"):
        llm = FakeLLM(
            tool_call("propose_visit", listing_code=CODE, starts_at=starts_at),
            answer("That time doesn't work."),
        )
        result = run_agent(tx_db, [UserMessage("Sunday please")], llm, now=NOW)
        assert "error" in last_tool_result(llm)
        assert result.visit_proposal is None


def test_no_proposal_when_model_only_mentions_a_time(db):
    llm = FakeLLM(answer("I've booked Sunday 11:00 for you."))  # a model lying about a write
    result = run_agent(db, [UserMessage("Book Sunday at 11")], llm, now=NOW)
    assert result.visit_proposal is None


def test_check_visit_slots_lists_labels(db):
    llm = FakeLLM(tool_call("check_visit_slots", listing_code=CODE), answer("Here are times."))
    run_agent(db, [UserMessage("When can I visit?")], llm, now=NOW)

    result = last_tool_result(llm)
    assert result["listing_code"] == CODE
    assert len(result["slots"]) == 8
    first = result["slots"][0]
    assert first["label"] == "Wed 14 Oct, 13:00"  # next free hour after noon
    assert first["starts_at"].startswith("2026-10-14T13:00")


def test_check_visit_slots_for_one_day(db):
    llm = FakeLLM(tool_call("check_visit_slots", listing_code=CODE, date="2026-10-18"), answer("ok"))
    run_agent(db, [UserMessage("Sunday?")], llm, now=NOW)
    labels = [s["label"] for s in last_tool_result(llm)["slots"]]
    assert labels[0] == "Sun 18 Oct, 10:00"
    assert all(label.startswith("Sun 18 Oct") for label in labels)


def test_agent_has_no_write_tool():
    assert {t.name for t in TOOLS} == {
        "search_properties",
        "get_property_details",
        "check_visit_slots",
        "propose_visit",
    }


def test_phone_numbers_never_reach_the_llm(db):
    llm = FakeLLM(answer("Thanks!"))
    run_agent(db, [UserMessage("call me on +91 98765 43210 or 9123456789")], llm, now=NOW)

    sent = llm.calls[0][0].text
    assert "[phone removed]" in sent
    assert "98765" not in sent and "9123456789" not in sent


def test_redact_keeps_prices_and_codes():
    for text in ("under 15000000", "₹1.38 Cr", "PAI-DEMO-002", "2BHK under 50000 a month"):
        assert redact_phone_numbers(text) == text


def test_today_is_in_the_system_prompt(db):
    llm = FakeLLM(answer("Hi"))
    run_agent(db, [UserMessage("hello")], llm, now=NOW)
    assert "Today is Wednesday 14 Oct 2026 (IST)." in llm.systems[0]


def test_chat_endpoint_returns_visit_proposal(client, db):
    slot = available_slots(db, CODE)[-1]
    llm = FakeLLM(
        tool_call("propose_visit", listing_code=CODE, starts_at=slot.isoformat()),
        answer("Tap Confirm to book."),
    )
    app.dependency_overrides[get_llm] = lambda: llm
    try:
        response = client.post("/chat", json={"messages": [{"role": "user", "content": "book it"}]})
    finally:
        app.dependency_overrides.pop(get_llm, None)

    assert response.status_code == 200
    proposal = response.json()["visit_proposal"]
    assert proposal["listing_code"] == CODE
    assert datetime.fromisoformat(proposal["starts_at"]) == slot


def test_chat_without_proposal_returns_null(client):
    llm = FakeLLM(answer("Hello!"))
    app.dependency_overrides[get_llm] = lambda: llm
    try:
        response = client.post("/chat", json={"messages": [{"role": "user", "content": "hi"}]})
    finally:
        app.dependency_overrides.pop(get_llm, None)
    assert response.json()["visit_proposal"] is None
