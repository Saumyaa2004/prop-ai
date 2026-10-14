"""
Prop AI - the eval judge.

A second LLM call grades each agent run against the case's expected behaviour.
The judge sees the facts the tools returned, not just the reply: that is what
lets it catch invented prices or listings. Its answer is parsed strictly, so a
malformed verdict is a "judge error", never an accidental pass.
"""

import json
from dataclasses import dataclass

from app.services.agent import AgentResult
from app.services.formatting import format_price
from app.services.privacy import redact_phone_numbers

JUDGE_SYSTEM = """You grade a real estate AI assistant called Prop AI. You get a
transcript of one conversation turn and the behaviour the assistant was expected to
show. Decide whether the FINAL REPLY (together with the tool calls) meets it.

Global rules that apply to every case, on top of the expected behaviour:
1. Facts (listings, prices, sizes, furnishing, amenities, status, free visit times)
   must come from the TOOL RESULT, FACTS or VISIT PROPOSAL lines. Anything else is
   invented and is a fail. TODAY gives the current date for words like "tomorrow".
2. The reply must not show internal listing codes such as PAI-DEMO-002.
3. The assistant never asks the user to tell it their name or phone number in the
   chat. Telling them to enter those details on the card is correct, not a fail.
4. The assistant never claims a visit is booked; the user confirms on the card.
5. Plain text: no markdown such as ** or #.

Judge only what is in the transcript. Be strict but fair: wording does not matter,
behaviour does. Reply with JSON only, no other text:
{"pass": true or false, "score": 1-5, "reason": "one or two sentences quoting the evidence"}"""


@dataclass(frozen=True)
class Verdict:
    passed: bool
    score: int  # 1 (bad) to 5 (perfect)
    reason: str


MAX_RESULT_CHARS = 2000  # keeps one long tool result from flooding the judge


def build_transcript(messages: list[dict], result: AgentResult, today: str | None = None) -> str:
    """Everything the judge needs to check the reply against reality."""
    # The judge is an LLM call too: phone numbers stay out of it, as for the agent.
    lines = [f"TODAY: {today}"] if today else []
    *earlier, latest = messages
    for m in earlier:
        role = "USER" if m["role"] == "user" else "ASSISTANT (earlier)"
        text = redact_phone_numbers(m["content"]) if m["role"] == "user" else m["content"]
        lines.append(f"{role}: {text}")
    lines.append(f"USER: {redact_phone_numbers(latest['content'])}")

    def as_json(data: dict) -> str:
        return json.dumps(data, ensure_ascii=False)[:MAX_RESULT_CHARS]

    if result.tool_results:
        for call, tool_result in result.tool_results:
            lines.append(f"TOOL CALL {call.name} {as_json(call.args)}")
            lines.append(f"TOOL RESULT {call.name} {as_json(tool_result)}")
    elif result.tool_calls:
        for call in result.tool_calls:
            lines.append(f"TOOL CALL {call.name} {as_json(call.args)}")
    else:
        lines.append("TOOL CALLS: none")

    if result.listings:
        lines.append("FACTS (listings the tools returned):")
        for p in result.listings:
            price = format_price(p.price_inr, p.listing_type)
            lines.append(f"- {p.listing_code} | {p.title} | {p.listing_type} | {price} | {p.status}")
    else:
        lines.append("FACTS: none")

    if result.visit_proposal:
        lines.append(f"VISIT PROPOSAL: {result.visit_proposal.title}, {result.visit_proposal.label}")

    lines.append(f"FINAL REPLY: {result.reply}")
    return "\n".join(lines)


def build_judge_prompt(expected: str, transcript: str) -> str:
    return (
        f"EXPECTED BEHAVIOUR:\n{expected}\n\n"
        f"TRANSCRIPT:\n{transcript}\n\n"
        'Answer with JSON only: {"pass": ..., "score": ..., "reason": ...}'
    )


def parse_verdict(text: str | None) -> Verdict | None:
    """The judge's verdict, or None if it didn't give a valid one."""
    if not text:
        return None
    decoder = json.JSONDecoder()
    for start in (i for i, ch in enumerate(text) if ch == "{"):
        try:
            data, _ = decoder.raw_decode(text, start)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict) or "pass" not in data:
            continue  # e.g. a tool argument the judge quoted before its verdict
        passed, reason = data["pass"], data.get("reason")
        # Strict: "true" (a string) is not a verdict; a missing reason isn't either.
        if not isinstance(passed, bool) or not isinstance(reason, str):
            return None
        score = data.get("score")
        if isinstance(score, float) and score.is_integer():
            score = int(score)
        if not isinstance(score, int) or isinstance(score, bool):
            score = 5 if passed else 1
        return Verdict(passed, min(5, max(1, score)), reason.strip())
    return None
