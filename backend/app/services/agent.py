"""
Prop AI - the AI agent.

The model never touches the database. It can only ask for read-only tools,
which wrap the same tested services as the HTTP API. Listings and visit
proposals shown to users come from tool results, never from the model's text.
The agent can propose a site visit but cannot book one: a person confirms on
a card, and the browser calls POST /visits directly.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.models import Property
from app.schemas.property import PropertySearchFilters
from app.services.formatting import format_price
from app.services.llm.base import (
    LLMClient,
    Message,
    ToolCall,
    ToolCallTurn,
    ToolResultMessage,
    ToolSpec,
    UserMessage,
)
from app.services.privacy import redact_phone_numbers
from app.services.property_details import find_listings_by_name, get_property_by_code
from app.services.property_search import search_properties
from app.services.visits import (
    IST,
    VisitError,
    available_slots,
    check_slot,
    parse_slot,
    slot_label,
)

# Model turns per user message; stops a confused model looping. Booking needs
# search -> slots -> propose -> answer, plus room for one retry.
MAX_STEPS = 6
CHAT_RESULT_LIMIT = 5

SYSTEM_PROMPT = """You are Prop AI, a friendly real estate assistant for Mumbai.
All listings are fictional demo data; say so if asked whether they are real.

Rules:
1. Only state facts (prices, sizes, amenities, availability) that come from tool
   results. Never invent listings, prices or details. If a tool returns nothing,
   say so and suggest widening the search.
2. Before searching, you must know whether the user wants to BUY or RENT. If it
   is unclear, ask first and do not search yet; never search both to hedge.
   Never guess: sale prices are totals, rent is monthly. Exception: when the user
   names a specific listing, look it up with find_listing; no need to ask.
3. Quote prices exactly as the `price_label` in tool results.
4. Convert budgets to whole rupees: 1 crore = 10000000, 1 lakh = 100000,
   "50k" = 50000. A rent budget is per month.
5. Keep answers short: a one-line summary, then the listings as a brief list
   with title, price label and one or two key facts. Never mention listing codes
   (like PAI-DEMO-002) to the user; they are internal IDs for your tools. If the
   user names a listing (now or earlier), find it with find_listing.
6. To book a site visit, find a free slot with check_visit_slots, then call
   propose_visit. The app then shows a card where the user enters their name and
   phone and taps Confirm. You cannot save bookings yourself. Never ask for a
   name or phone number. Quote slot times exactly as their `label`.
7. Write plain text only: no markdown, no ** or #. For lists, start lines with "- ".
   The app shows listing cards with full details under your reply.
8. Use a listing's status. If it is sold, under offer or rented, say so plainly
   and do not propose a visit; you may offer similar available homes. If the user
   wants to buy a listing that is only for rent, say it is only for rent (and
   the reverse for a sale listing).
9. Only propose a visit for the exact listing the user asked about. If you cannot
   find it, say so and never substitute a different home.
10. You only help with property in this app. Politely decline anything else
   (weather, poems, investment or stock tips) and offer property help instead."""

SEARCH_TOOL = ToolSpec(
    name="search_properties",
    description=(
        "Search AVAILABLE listings. listing_type is required: 'sale' (price is the "
        "total price) or 'rent' (price is MONTHLY rent). Only include filters the "
        "user actually asked for. Results are cheapest first."
    ),
    parameters={
        "type": "object",
        "properties": {
            "listing_type": {"type": "string", "enum": ["sale", "rent"]},
            "city": {"type": "string", "description": "e.g. Mumbai"},
            "locality": {"type": "string", "description": "e.g. Powai, Andheri West"},
            "property_type": {
                "type": "string",
                "enum": ["apartment", "villa", "independent_house", "studio", "penthouse"],
            },
            "bedrooms": {"type": "integer", "description": "Exact count; 0 = studio"},
            "min_price": {"type": "integer", "description": "Whole rupees"},
            "max_price": {
                "type": "integer",
                "description": "Whole rupees. 1 crore = 10000000. For rent: per month.",
            },
            "furnishing": {
                "type": "string",
                "enum": ["unfurnished", "semi_furnished", "fully_furnished"],
            },
            "amenities": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Must have ALL, e.g. parking, gym, swimming_pool, lift",
            },
            "limit": {"type": "integer", "description": "Max results, default 5"},
        },
        "required": ["listing_type"],
    },
)

DETAILS_TOOL = ToolSpec(
    name="get_property_details",
    description="Full details of one listing by its code, e.g. PAI-DEMO-002. Any status.",
    parameters={
        "type": "object",
        "properties": {"listing_code": {"type": "string"}},
        "required": ["listing_code"],
    },
)

FIND_TOOL = ToolSpec(
    name="find_listing",
    description=(
        "Find listings by name, e.g. 'Oberoi Link' or 'Hiranandani Gardens'. Returns "
        "any status (available, under_offer, sold, rented). Use it whenever the user "
        "names a listing instead of describing what they want."
    ),
    parameters={
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"],
    },
)

SLOTS_TOOL = ToolSpec(
    name="check_visit_slots",
    description=(
        "Free site-visit slots for one listing (hourly, 10:00-17:00 IST, next 14 days). "
        "With a date: that day's free slots. Without: the next 8 free slots."
    ),
    parameters={
        "type": "object",
        "properties": {
            "listing_code": {"type": "string"},
            "date": {"type": "string", "description": "YYYY-MM-DD"},
        },
        "required": ["listing_code"],
    },
)

PROPOSE_TOOL = ToolSpec(
    name="propose_visit",
    description=(
        "Propose one visit slot to the user. Does NOT book: the app shows a card "
        "where the user enters name and phone and taps Confirm."
    ),
    parameters={
        "type": "object",
        "properties": {
            "listing_code": {"type": "string"},
            "starts_at": {"type": "string", "description": "YYYY-MM-DDTHH:MM in IST"},
        },
        "required": ["listing_code", "starts_at"],
    },
)

# Read-only on purpose: no tool writes. Bookings need a person's click.
TOOLS = [SEARCH_TOOL, DETAILS_TOOL, FIND_TOOL, SLOTS_TOOL, PROPOSE_TOOL]
SLOTS_WITHOUT_DATE = 8


@dataclass(frozen=True)
class VisitProposal:
    """A slot the agent suggests; the user confirms it on a card in the app."""

    listing_code: str
    title: str
    starts_at: datetime
    label: str


@dataclass
class AgentResult:
    reply: str
    listings: list[Property] = field(default_factory=list)
    tool_calls: list[ToolCall] = field(default_factory=list)
    visit_proposal: VisitProposal | None = None
    # Every (call, result) the model saw: lets the eval judge check facts.
    tool_results: list[tuple[ToolCall, dict[str, Any]]] = field(default_factory=list)


def _summary(p: Property) -> dict[str, Any]:
    """Compact listing facts for the model (fewer tokens than the full row)."""
    return {
        "listing_code": p.listing_code,
        "title": p.title,
        "listing_type": p.listing_type,
        "price_label": format_price(p.price_inr, p.listing_type),
        "locality": p.locality,
        "bedrooms": p.bedrooms,
        "area_sqft": p.area_sqft,
        "furnishing": p.furnishing,
        "amenities": p.amenities,
        "status": p.status,
    }


def _validation_message(exc: ValidationError) -> str:
    """Short, model-readable reasons, e.g. 'listing_type: Field required'."""
    reasons = [
        f"{'.'.join(str(x) for x in err['loc']) or 'filters'}: {err['msg']}"
        for err in exc.errors()
    ]
    return "Invalid arguments. " + "; ".join(reasons)


def _slot(starts_at: datetime) -> dict[str, str]:
    return {"starts_at": starts_at.isoformat(), "label": slot_label(starts_at)}


def run_tool(
    db: Session, call: ToolCall, now: datetime | None = None
) -> tuple[dict[str, Any], list[Property]]:
    """Execute one tool call. Returns (result for the model, listings found)."""
    if call.name == SEARCH_TOOL.name:
        args = {"limit": CHAT_RESULT_LIMIT, **call.args}
        try:
            filters = PropertySearchFilters.model_validate(args)
        except ValidationError as exc:
            # Sent back to the model so it can fix the call or ask the user.
            return {"error": _validation_message(exc)}, []
        found = search_properties(db, filters)
        return {"count": len(found), "results": [_summary(p) for p in found]}, found

    if call.name == DETAILS_TOOL.name:
        code = str(call.args.get("listing_code", "")).strip()
        listing = get_property_by_code(db, code) if code else None
        if listing is None:
            return {"error": f"No listing with code {code or '(empty)'}."}, []
        return {**_summary(listing), "description": listing.description,
                "bathrooms": listing.bathrooms,
                "available_from": str(listing.available_from or "not specified")}, [listing]

    if call.name == FIND_TOOL.name:
        found = find_listings_by_name(db, str(call.args.get("name", "")))
        # Only available homes become cards: a sold one would look like an offer.
        cards = [p for p in found if p.status == "available"]
        return {"count": len(found), "results": [_summary(p) for p in found]}, cards

    if call.name in (SLOTS_TOOL.name, PROPOSE_TOOL.name):
        code = str(call.args.get("listing_code", "")).strip()
        try:
            if call.name == SLOTS_TOOL.name:
                raw_day = call.args.get("date")
                day = date.fromisoformat(str(raw_day)) if raw_day else None
                slots = available_slots(db, code, day, now)
                if day is None:
                    slots = slots[:SLOTS_WITHOUT_DATE]
                listing = get_property_by_code(db, code)
                return {"listing_code": listing.listing_code, "title": listing.title,
                        "slots": [_slot(s) for s in slots]}, []

            starts_at = parse_slot(str(call.args.get("starts_at", "")))
            listing = check_slot(db, code, starts_at, now)
            proposal = {"listing_code": listing.listing_code, "title": listing.title,
                        **_slot(starts_at)}
            return {"proposal": proposal,
                    "note": "Not booked yet. Tell the user to enter their name and "
                            "phone on the card and tap Confirm."}, []
        except VisitError as exc:
            return {"error": str(exc)}, []
        except ValueError:
            return {"error": "Dates must look like 2026-10-18."}, []

    return {"error": f"Unknown tool {call.name}."}, []


def system_prompt(now: datetime) -> str:
    """The model doesn't know today's date; without it, "Saturday" means nothing."""
    today = now.astimezone(IST)
    return f"{SYSTEM_PROMPT}\n\nToday is {today:%A} {today.day} {today:%b %Y} (IST)."


def run_agent(
    db: Session, history: list[Message], llm: LLMClient, now: datetime | None = None
) -> AgentResult:
    """Answer the latest user message, calling tools as the model requests."""
    now = now or datetime.now(IST)
    system = system_prompt(now)
    # Phone numbers typed into the chat never leave our server.
    messages: list[Message] = [
        UserMessage(redact_phone_numbers(m.text)) if isinstance(m, UserMessage) else m
        for m in history
    ]
    listings: dict[str, Property] = {}  # insertion-ordered, de-duplicated
    calls_made: list[ToolCall] = []
    results_seen: list[tuple[ToolCall, dict[str, Any]]] = []
    proposal: VisitProposal | None = None

    for _ in range(MAX_STEPS):
        reply = llm.generate(system, messages, TOOLS)

        if not reply.tool_calls:
            text = reply.text or "Sorry, I couldn't come up with an answer. Please rephrase."
            return AgentResult(text, list(listings.values()), calls_made, proposal, results_seen)

        messages.append(ToolCallTurn(reply))
        for call in reply.tool_calls:
            calls_made.append(call)
            result, found = run_tool(db, call, now)
            for p in found:
                listings.setdefault(p.listing_code, p)
            if "proposal" in result:  # from the tool result, never from the model's text
                offer = result["proposal"]
                proposal = VisitProposal(
                    offer["listing_code"],
                    offer["title"],
                    datetime.fromisoformat(offer["starts_at"]),
                    offer["label"],
                )
            elif call.name == PROPOSE_TOOL.name:
                proposal = None  # the latest proposal failed; a stale card would contradict the reply
            results_seen.append((call, result))
            messages.append(ToolResultMessage(call, result))

    return AgentResult(
        "Sorry, that took too many steps. Could you rephrase or narrow your request?",
        list(listings.values()),
        calls_made,
        proposal,
        results_seen,
    )
