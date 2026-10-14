"""Tests for price labels given to the AI agent."""

import pytest

from app.services.formatting import format_price


@pytest.mark.parametrize(
    ("price", "listing_type", "label"),
    [
        (13_800_000, "sale", "₹1.38 Cr"),
        (125_000_000, "sale", "₹12.5 Cr"),
        (20_000_000, "sale", "₹2 Cr"),
        (9_800_000, "sale", "₹98 L"),
        (42_000, "rent", "₹42,000/month"),
        (125_000, "rent", "₹1,25,000/month"),
        # A large rent is still monthly, never shown in crore.
        (12_000_000, "rent", "₹1,20,00,000/month"),
    ],
)
def test_format_price(price, listing_type, label):
    assert format_price(price, listing_type) == label
