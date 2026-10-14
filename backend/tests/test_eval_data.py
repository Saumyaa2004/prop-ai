"""
The eval data must be valid before it is worth spending quota on.
"""

import json
from collections import Counter
from pathlib import Path

EVALS = Path(__file__).resolve().parents[1] / "evals"
CATEGORIES = {"search", "clarify", "honesty", "booking", "safety", "out_of_context", "not_for_sale"}


def load(name: str) -> list[dict]:
    return json.loads((EVALS / name).read_text(encoding="utf-8"))


def test_case_ids_are_unique_and_categories_known():
    cases = load("cases.json")
    ids = [c["id"] for c in cases]
    assert len(ids) == len(set(ids))
    assert {c["category"] for c in cases} == CATEGORIES


def test_every_category_is_covered_enough():
    counts = Counter(c["category"] for c in load("cases.json"))
    assert all(n >= 2 for n in counts.values())
    assert counts["out_of_context"] >= 4  # owner request
    assert counts["not_for_sale"] >= 6  # owner request


def test_conversations_are_valid_chat_requests():
    for case in load("cases.json"):
        messages = case["messages"]
        assert messages[-1]["role"] == "user", case["id"]
        assert len(messages) <= 20, case["id"]
        for i, m in enumerate(messages):
            # Turns alternate, starting with the user (as the chat UI sends them).
            assert m["role"] == ("user" if i % 2 == 0 else "assistant"), case["id"]
            assert 1 <= len(m["content"]) <= 1000, case["id"]
        assert case["expected"].strip(), case["id"]


def test_calibration_set_is_balanced():
    items = load("calibration.json")
    assert len({i["id"] for i in items}) == len(items)
    verdicts = [i["verdict"] for i in items]
    assert verdicts.count(True) >= 3 and verdicts.count(False) >= 3  # both kinds checked
    for item in items:
        assert item["expected"].strip() and "FINAL REPLY:" in item["transcript"], item["id"]
