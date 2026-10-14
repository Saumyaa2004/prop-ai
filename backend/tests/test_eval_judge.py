"""
Tests for the eval judge: what it sees, what it is asked, how its answer is read.
"""

from datetime import datetime

from app.services.agent import AgentResult, VisitProposal
from app.services.llm.base import ToolCall
from app.services.property_details import get_property_by_code
from app.services.visits import IST
from evals.judge import JUDGE_SYSTEM, Verdict, build_judge_prompt, build_transcript, parse_verdict


def sample_result(db) -> AgentResult:
    listing = get_property_by_code(db, "PAI-DEMO-002")
    return AgentResult(
        reply="Hiranandani Gardens 2BHK is ₹1.38 Cr. Tap Confirm on the card to book Sunday 11:00.",
        listings=[listing],
        tool_calls=[ToolCall("search_properties", {"listing_type": "sale", "locality": "Powai"})],
        visit_proposal=VisitProposal(
            "PAI-DEMO-002", listing.title, datetime(2026, 1, 11, 11, tzinfo=IST), "Sun 11 Jan, 11:00"
        ),
    )


MESSAGES = [
    {"role": "user", "content": "Show me a 2BHK in Powai"},
    {"role": "assistant", "content": "Are you looking to buy or rent?"},
    {"role": "user", "content": "buy, and book a visit on Sunday at 11"},
]


def test_transcript_shows_everything_the_judge_needs(db):
    transcript = build_transcript(MESSAGES, sample_result(db))

    assert "USER: Show me a 2BHK in Powai" in transcript
    assert "ASSISTANT (earlier): Are you looking to buy or rent?" in transcript
    assert 'TOOL CALL search_properties {"listing_type": "sale", "locality": "Powai"}' in transcript
    # The facts the reply must be checked against:
    assert "Hiranandani Gardens 2BHK" in transcript
    assert "₹1.38 Cr" in transcript
    assert "available" in transcript
    assert "VISIT PROPOSAL: Hiranandani Gardens 2BHK, Sun 11 Jan, 11:00" in transcript
    assert "FINAL REPLY: Hiranandani Gardens 2BHK is ₹1.38 Cr." in transcript


def test_transcript_says_when_no_tools_ran(db):
    result = AgentResult(reply="I can only help with property.")
    transcript = build_transcript([{"role": "user", "content": "weather?"}], result)
    assert "TOOL CALLS: none" in transcript
    assert "FACTS: none" in transcript


def test_prompt_has_expected_behaviour_transcript_and_rules():
    prompt = build_judge_prompt("Asks whether the user wants to buy or rent.", "USER: hi")
    assert "Asks whether the user wants to buy or rent." in prompt
    assert "USER: hi" in prompt
    assert "never asks the user to tell it their name or phone number" in JUDGE_SYSTEM
    assert "pass" in prompt and "score" in prompt and "reason" in prompt


def test_parse_plain_fenced_and_prose_json():
    plain = '{"pass": true, "score": 5, "reason": "Correct filters."}'
    assert parse_verdict(plain) == Verdict(True, 5, "Correct filters.")
    fenced = '```json\n{"pass": false, "score": 2, "reason": "Invented a price."}\n```'
    assert parse_verdict(fenced) == Verdict(False, 2, "Invented a price.")
    prose = 'Here is my verdict: {"pass": true, "score": 4, "reason": "ok"} Thanks.'
    assert parse_verdict(prose) == Verdict(True, 4, "ok")


def test_parse_is_strict_about_pass():
    assert parse_verdict('{"pass": "true", "score": 5, "reason": "x"}') is None
    assert parse_verdict('{"score": 5, "reason": "x"}') is None
    assert parse_verdict('{"pass": true, "score": 5}') is None


def test_parse_rejects_garbage():
    assert parse_verdict("I think it passed.") is None
    assert parse_verdict("") is None
    assert parse_verdict(None) is None
    assert parse_verdict("{not json}") is None


def test_parse_clamps_or_defaults_the_score():
    assert parse_verdict('{"pass": true, "score": 9, "reason": "x"}').score == 5
    assert parse_verdict('{"pass": false, "score": 0, "reason": "x"}').score == 1
    assert parse_verdict('{"pass": true, "reason": "x"}').score == 5
    assert parse_verdict('{"pass": false, "reason": "x"}').score == 1


def test_parse_skips_quoted_json_before_the_verdict():
    # Judges quote tool arguments; that object is not the verdict.
    text = 'The call {"listing_type": "rent"} was wrong. {"pass": false, "score": 2, "reason": "rent for a buy"}'
    assert parse_verdict(text) == Verdict(False, 2, "rent for a buy")


def test_parse_accepts_whole_number_float_scores():
    assert parse_verdict('{"pass": true, "score": 4.0, "reason": "x"}').score == 4


def test_transcript_shows_full_tool_results_today_and_hides_phones(db):
    listing = get_property_by_code(db, "PAI-DEMO-001")
    details = {"listing_code": "PAI-DEMO-001", "title": listing.title, "area_sqft": 780,
               "furnishing": "semi_furnished", "amenities": ["parking", "lift"]}
    call = ToolCall("get_property_details", {"listing_code": "PAI-DEMO-001"})
    result = AgentResult(reply="780 sq ft, semi furnished.", listings=[listing],
                         tool_calls=[call], tool_results=[(call, details)])
    messages = [{"role": "user", "content": "Tell me about Lakeview, call me on 98765 43210"}]

    transcript = build_transcript(messages, result, today="Wednesday 7 Jan 2026 (IST)")

    assert "TODAY: Wednesday 7 Jan 2026 (IST)" in transcript
    assert 'TOOL RESULT get_property_details {"listing_code": "PAI-DEMO-001"' in transcript
    assert '"area_sqft": 780' in transcript and "semi_furnished" in transcript
    assert "98765" not in transcript and "[phone removed]" in transcript


def test_rubric_allows_pointing_to_the_card():
    assert "on the card" in JUDGE_SYSTEM
    assert "TOOL RESULT" in JUDGE_SYSTEM
