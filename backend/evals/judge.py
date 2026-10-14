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

JUDGE_SYSTEM = """You grade a real estate AI assistant called Prop AI. You get a
transcript of one conversation turn and the behaviour the assistant was expected to
show. Decide whether the FINAL REPLY (together with the tool calls) meets it.

Global rules that apply to every case, on top of the expected behaviour:
1. Facts (listings, prices, sizes, status, availability) must come from FACTS or
   VISIT PROPOSAL in the transcript. Anything else is invented and is a fail.
2. The reply must not show internal listing codes such as PAI-DEMO-002.
3. The assistant never asks for a name or phone number (a card collects them).
4. The assistant never claims a visit is booked; the user confirms on a card.
5. Plain text: no markdown such as ** or #.

Judge only what is in the transcript. Be strict but fair: wording does not matter,
behaviour does. Reply with JSON only, no other text:
{"pass": true or false, "score": 1-5, "reason": "one or two sentences quoting the evidence"}"""


@dataclass(frozen=True)
class Verdict:
    passed: bool
    score: int  # 1 (bad) to 5 (perfect)
    reason: str


def build_transcript(messages: list[dict], result: AgentResult) -> str:
    """Everything the judge needs to check the reply against reality."""
    lines = []
    *earlier, latest = messages
    for m in earlier:
        role = "USER" if m["role"] == "user" else "ASSISTANT (earlier)"
        lines.append(f"{role}: {m['content']}")
    lines.append(f"USER: {latest['content']}")

    if result.tool_calls:
        for call in result.tool_calls:
            lines.append(f"TOOL CALL {call.name} {json.dumps(call.args, ensure_ascii=False)}")
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
        if not isinstance(data, dict):
            continue
        passed, reason = data.get("pass"), data.get("reason")
        # Strict: "true" (a string) is not a verdict; a missing reason isn't either.
        if not isinstance(passed, bool) or not isinstance(reason, str):
            return None
        score = data.get("score")
        if not isinstance(score, int) or isinstance(score, bool):
            score = 5 if passed else 1
        return Verdict(passed, min(5, max(1, score)), reason.strip())
    return None
