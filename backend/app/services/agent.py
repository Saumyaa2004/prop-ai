"""
Prop AI - the AI agent.

The model never touches the database. It can only ask for two tools, which
wrap the same tested services as the HTTP API. Every argument is validated by
the same Pydantic schema the API uses, and listings shown to users come from
tool results, never from the model's text.
"""

from dataclasses import dataclass, field
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
)
from app.services.property_details import get_property_by_code
from app.services.property_search import search_properties

MAX_STEPS = 4  # model turns per user message; stops a confused model looping
CHAT_RESULT_LIMIT = 5

SYSTEM_PROMPT = """You are Prop AI, a friendly real estate assistant for Mumbai.
All listings are fictional demo data; say so if asked whether they are real.

Rules:
1. Only state facts (prices, sizes, amenities, availability) that come from tool
   results. Never invent listings, prices or details. If a tool returns nothing,
   say so and suggest widening the search.
2. Before searching, you must know whether the user wants to BUY or RENT. If it
   is unclear, ask. Never guess: sale prices are totals, rent is monthly.
3. Quote prices exactly as the `price_label` in tool results.
4. Convert budgets to whole rupees: 1 crore = 10000000, 1 lakh = 100000,
   "50k" = 50000. A rent budget is per month.
5. Keep answers short: a one-line summary, then the listings as a brief list
   with title, price label and one or two key facts. Never mention listing codes
   (like PAI-DEMO-002) to the user; they are internal IDs for your tools. If the
   user asks about a listing from earlier, search again to find its code.
6. You cannot book visits or save details yet; say that this is coming soon.
7. Write plain text only: no markdown, no ** or #. For lists, start lines with "- ".
   The app shows listing cards with full details under your reply."""

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

TOOLS = [SEARCH_TOOL, DETAILS_TOOL]


@dataclass
class AgentResult:
    reply: str
    listings: list[Property] = field(default_factory=list)
    tool_calls: list[ToolCall] = field(default_factory=list)


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


def run_tool(db: Session, call: ToolCall) -> tuple[dict[str, Any], list[Property]]:
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

    return {"error": f"Unknown tool {call.name}."}, []


def run_agent(db: Session, history: list[Message], llm: LLMClient) -> AgentResult:
    """Answer the latest user message, calling tools as the model requests."""
    messages = list(history)
    listings: dict[str, Property] = {}  # insertion-ordered, de-duplicated
    calls_made: list[ToolCall] = []

    for _ in range(MAX_STEPS):
        reply = llm.generate(SYSTEM_PROMPT, messages, TOOLS)

        if not reply.tool_calls:
            text = reply.text or "Sorry, I couldn't come up with an answer. Please rephrase."
            return AgentResult(text, list(listings.values()), calls_made)

        messages.append(ToolCallTurn(reply))
        for call in reply.tool_calls:
            calls_made.append(call)
            result, found = run_tool(db, call)
            for p in found:
                listings.setdefault(p.listing_code, p)
            messages.append(ToolResultMessage(call, result))

    return AgentResult(
        "Sorry, that took too many steps. Could you rephrase or narrow your request?",
        list(listings.values()),
        calls_made,
    )
