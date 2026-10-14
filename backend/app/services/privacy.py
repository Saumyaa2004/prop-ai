"""
Prop AI - keep personal data away from the LLM provider.

The free Gemini tier may use prompts to improve Google's models, so phone
numbers a user types into the chat are removed before any LLM call.
"""

import re

# Indian mobile: optional +91 / 91 / 0, then 10 digits starting 6-9, with
# optional space or dash in the middle. Lookarounds stop it matching inside
# longer numbers (prices like 15000000 are left alone).
_MOBILE = re.compile(r"(?<!\d)(?:\+?91[\s-]?|0)?[6-9]\d{4}[\s-]?\d{5}(?!\d)")


def redact_phone_numbers(text: str) -> str:
    return _MOBILE.sub("[phone removed]", text)
