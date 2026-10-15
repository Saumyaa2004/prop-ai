"""
Has the user said whether they want to buy or rent?

Search needs listing_type, and guessing it mixes total prices with monthly
rents. The prompt tells the model to ask first, but evals showed it searched
anyway, so the agent loop checks this in code before running a search.

Deliberately simple: a false "no" only makes the assistant ask one extra
question, which is far cheaper than showing the wrong kind of listing.
"""

import re

_BUY_OR_RENT = re.compile(
    r"\b(?:buy\w*|purchas\w*|sale|sell\w*|kharid\w*"  # buy (kharidna: Hindi)
    r"|rent\w*|leas(?:e|ed|es|ing)|kiray\w*|kiraay\w*)\b"  # rent (kiraya: Hindi)
    r"|\d\s*cr\b|\bcrores?\b"  # nobody pays rent in crores
    r"|\b(?:per|a)\s+month\b|/\s*month\b|\bmonthly\b",  # rent is quoted monthly
    re.IGNORECASE,
)


def states_buy_or_rent(text: str) -> bool:
    """True if `text` says buy or rent. "Lakh" alone doesn't count: luxury rents are in lakhs."""
    return bool(_BUY_OR_RENT.search(text))
