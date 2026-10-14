"""
Prop AI - keep personal data away from the LLM provider.

The free Gemini tier may use prompts to improve Google's models, so phone
numbers a user types into the chat are removed before any LLM call.
"""

import re

# Indian mobile: optional +91 / 91 / 0, then 10 digits starting 6-9, with any
# spaces or dashes between digits ("987 654 3210", "98 76 54 32 10").
# Lookarounds stop it matching inside longer numbers (prices like 15000000
# are left alone). [0-9], not \d: Python's \d also matches non-ASCII digits.
_MOBILE = re.compile(r"(?<![0-9])(?:\+?91[\s-]*|0)?[6-9](?:[\s-]*[0-9]){9}(?![0-9])")


def redact_phone_numbers(text: str) -> str:
    return _MOBILE.sub("[phone removed]", text)
