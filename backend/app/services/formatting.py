"""
Prop AI - human-readable labels.

Prices are given to the AI agent pre-formatted: models are unreliable at
arithmetic, so they quote these labels instead of converting rupees themselves.
Mirrors frontend/src/lib/format.ts.
"""

CRORE = 10_000_000
LAKH = 100_000


def _indian_grouping(value: int) -> str:
    """1250000 -> '12,50,000' (last 3 digits, then groups of 2)."""
    digits = str(value)
    if len(digits) <= 3:
        return digits
    head, tail = digits[:-3], digits[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    groups.insert(0, head)
    return ",".join(groups) + "," + tail


def _trim(value: float) -> str:
    """1.40 -> '1.4', 2.00 -> '2'"""
    return f"{value:.2f}".rstrip("0").rstrip(".")


def format_price(price_inr: int, listing_type: str) -> str:
    """13_800_000 sale -> '₹1.38 Cr'; 9_800_000 sale -> '₹98 L'; 42_000 rent -> '₹42,000/month'"""
    if listing_type == "rent":
        return f"₹{_indian_grouping(price_inr)}/month"
    if price_inr >= CRORE:
        return f"₹{_trim(price_inr / CRORE)} Cr"
    if price_inr >= LAKH:
        return f"₹{_trim(price_inr / LAKH)} L"
    return f"₹{_indian_grouping(price_inr)}"
