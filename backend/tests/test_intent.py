"""
Tests for the buy-or-rent detector that gates property search.

Eval finding: told "ask first" in the prompt, the model still searched 0/3
times before asking. The check now lives in code.
"""

import pytest

from app.services.intent import states_buy_or_rent


@pytest.mark.parametrize(
    "text",
    [
        "I want to buy a 3BHK with a gym",
        "Flats to buy under 1 crore",
        "2BHK in Powai under 1.5 crore with parking",  # nobody rents in crores
        "something under 2cr",
        "A furnished studio to rent in Powai",
        "1BHK in Powai under 45k a month",
        "budget 60k per month",
        "Is Oberoi Link still for sale?",
        "rent",  # a one-word answer to "buy or rent?"
        "BUY",
        "any rentals near IIT?",
        "Powai mein 2BHK chahiye rent pe",
        "kiraye pe chahiye",
        "flat kharidna hai",
        "looking to lease a 2BHK",
    ],
)
def test_detects_buy_or_rent(text):
    assert states_buy_or_rent(text)


@pytest.mark.parametrize(
    "text",
    [
        "Show me a 2BHK in Powai",
        "Something under 50k",
        "2BHK under 80 lakh",  # luxury rents are quoted in lakhs too: still ask
        "the current price please",  # "rent" inside "current" is not a word
        "at least 3 bedrooms",  # "least" is not "lease"
        "",
    ],
)
def test_unclear_requests_are_not_buy_or_rent(text):
    assert not states_buy_or_rent(text)
