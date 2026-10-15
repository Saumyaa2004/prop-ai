"""
Tests for GET /properties/{listing_code} and the details service.

Expected values come from the fictional seed data in app/seed.py.
"""

import pytest

from app.services.property_details import get_property_by_code


# ---------- happy path ----------


def test_returns_full_listing_details(client):
    response = client.get("/properties/PAI-DEMO-002")

    assert response.status_code == 200
    body = response.json()
    assert body["listing_code"] == "PAI-DEMO-002"
    assert body["title"] == "Hiranandani Gardens 2BHK"
    assert body["listing_type"] == "sale"
    assert body["price_inr"] == 13_800_000
    assert body["locality"] == "Powai"
    assert body["is_demo_data"] is True
    # Internal columns are not exposed.
    assert "id" not in body
    assert "created_at" not in body


def test_code_lookup_ignores_case_and_spaces(client):
    response = client.get("/properties/%20pai-demo-002%20")

    assert response.status_code == 200
    assert response.json()["listing_code"] == "PAI-DEMO-002"


@pytest.mark.parametrize(
    ("code", "status"),
    [("PAI-DEMO-011", "sold"), ("PAI-DEMO-017", "rented"), ("PAI-DEMO-010", "under_offer")],
)
def test_unavailable_listings_are_returned_with_their_status(client, code, status):
    # Search hides these, but asking for a specific code gets the truth.
    response = client.get(f"/properties/{code}")

    assert response.status_code == 200
    assert response.json()["status"] == status


# ---------- missing record ----------


def test_unknown_code_returns_404(client):
    response = client.get("/properties/PAI-DEMO-999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Property not found"}


# ---------- invalid input ----------


def test_code_longer_than_column_is_rejected_with_422(client):
    response = client.get("/properties/" + "X" * 21)

    assert response.status_code == 422


# ---------- route order ----------


def test_search_route_is_not_captured_as_a_listing_code(client):
    response = client.get("/properties/search", params={"listing_type": "sale"})

    assert response.status_code == 200
    assert "results" in response.json()


# ---------- service reuse ----------


def test_service_returns_listing_or_none(db):
    assert get_property_by_code(db, "PAI-DEMO-014").title == "IIT Gate Studio Rental"
    assert get_property_by_code(db, "PAI-DEMO-999") is None


# ---------- find by name (for the AI agent) ----------


def titles(found) -> list[str]:
    return [p.title for p in found]


def test_find_by_name_exact_and_partial(db):
    from app.services.property_details import find_listings_by_name

    assert titles(find_listings_by_name(db, "Hiranandani Gardens 2BHK")) == ["Hiranandani Gardens 2BHK"]
    assert titles(find_listings_by_name(db, "hiranandani gardens")) == ["Hiranandani Gardens 2BHK"]


def test_find_by_name_ignores_filler_and_accepts_the_locality(db):
    from app.services.property_details import find_listings_by_name

    # People add words the title doesn't have: "the", "flat", "in Powai".
    found = find_listings_by_name(db, "the Lakeview Residency flat in Powai")
    assert titles(found) == ["Lakeview Residency 2BHK"]


def test_find_by_name_returns_any_status(db):
    from app.services.property_details import find_listings_by_name

    # Search hides these; a buyer asking about them deserves "it's sold".
    assert [p.status for p in find_listings_by_name(db, "Oberoi Link")] == ["sold"]
    assert [p.status for p in find_listings_by_name(db, "Sun Hills Villa")] == ["under_offer"]
    assert [p.status for p in find_listings_by_name(db, "Chembur Greens 2BHK")] == ["rented"]


def test_find_by_name_unknown_or_empty(db):
    from app.services.property_details import find_listings_by_name

    assert find_listings_by_name(db, "Antilia") == []
    assert find_listings_by_name(db, "   ") == []
    assert find_listings_by_name(db, "the flat in") == []  # only filler words
