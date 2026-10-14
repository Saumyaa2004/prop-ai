"""
Tests for GET /properties/search and the search service.

Expected listing codes come from the fictional seed data in app/seed.py.
"""

import pytest

from app.schemas.property import PropertySearchFilters
from app.services.property_search import search_properties

SEARCH_URL = "/properties/search"


def codes(response) -> list[str]:
    return [p["listing_code"] for p in response.json()["results"]]


# ---------- happy path ----------


def test_buyer_query_returns_matching_listings_cheapest_first(client):
    # "2BHK in Powai under 1.5 crore with parking"
    response = client.get(
        SEARCH_URL,
        params={
            "listing_type": "sale",
            "locality": "Powai",
            "bedrooms": 2,
            "max_price": 15_000_000,
            "amenities": "parking",
        },
    )

    assert response.status_code == 200
    body = response.json()
    # PAI-DEMO-004 is in Powai and in budget but has no parking.
    assert codes(response) == ["PAI-DEMO-002", "PAI-DEMO-001"]
    assert [p["price_inr"] for p in body["results"]] == [13_800_000, 14_500_000]
    assert body["count"] == 2


def test_results_are_available_demo_listings_only(client):
    response = client.get(SEARCH_URL, params={"listing_type": "sale"})

    results = response.json()["results"]
    assert results, "expected seeded sale listings"
    assert all(p["status"] == "available" for p in results)
    assert all(p["is_demo_data"] is True for p in results)
    # Sold (011) and under-offer (010) listings are never returned.
    assert {"PAI-DEMO-010", "PAI-DEMO-011"}.isdisjoint(codes(response))


def test_text_filters_are_case_insensitive(client):
    lower = client.get(SEARCH_URL, params={"listing_type": "rent", "locality": "powai"})
    upper = client.get(SEARCH_URL, params={"listing_type": "rent", "locality": "POWAI "})

    assert codes(lower) == codes(upper)
    assert len(codes(lower)) == 4


def test_amenities_must_all_be_present(client):
    response = client.get(
        SEARCH_URL,
        params={"listing_type": "sale", "amenities": ["parking", "swimming_pool"]},
    )

    results = response.json()["results"]
    assert codes(response) == ["PAI-DEMO-003", "PAI-DEMO-005", "PAI-DEMO-009"]
    assert all({"parking", "swimming_pool"} <= set(p["amenities"]) for p in results)


def test_limit_caps_number_of_results(client):
    response = client.get(SEARCH_URL, params={"listing_type": "sale", "limit": 2})

    assert response.json()["count"] == 2
    assert codes(response) == ["PAI-DEMO-008", "PAI-DEMO-007"]


# ---------- sale vs rent never mix ----------


def test_rent_search_returns_only_rentals(client):
    response = client.get(SEARCH_URL, params={"listing_type": "rent", "max_price": 50_000})

    assert codes(response) == ["PAI-DEMO-014", "PAI-DEMO-012", "PAI-DEMO-015"]
    assert all(p["listing_type"] == "rent" for p in response.json()["results"])


def test_rent_sized_budget_on_sale_search_finds_nothing(client):
    # A 50k budget is a monthly rent; it must not match any sale listing.
    response = client.get(SEARCH_URL, params={"listing_type": "sale", "max_price": 50_000})

    assert response.status_code == 200
    assert response.json() == {"count": 0, "results": []}


# ---------- empty results ----------


@pytest.mark.parametrize("locality", ["Goregaon East", "Thane West", "Nowhere"])
def test_locality_without_available_listings_returns_empty(client, locality):
    # Goregaon East has only a sold listing; Thane West only one under offer.
    response = client.get(SEARCH_URL, params={"listing_type": "sale", "locality": locality})

    assert response.status_code == 200
    assert response.json() == {"count": 0, "results": []}


# ---------- invalid input ----------


@pytest.mark.parametrize(
    "params",
    [
        {},  # listing_type is required
        {"listing_type": "lease"},
        {"listing_type": "sale", "min_price": 2_000_000, "max_price": 1_000_000},
        {"listing_type": "sale", "max_prise": 1_000_000},  # typo must not be ignored
        {"listing_type": "sale", "limit": 0},
        {"listing_type": "sale", "limit": 51},
        {"listing_type": "sale", "max_price": -1},
        {"listing_type": "sale", "bedrooms": "two"},
        {"listing_type": "sale", "property_type": "castle"},
    ],
)
def test_invalid_input_is_rejected_with_422(client, params):
    response = client.get(SEARCH_URL, params=params)

    assert response.status_code == 422


# ---------- service reuse ----------


def test_service_works_without_http(db):
    # The AI agent's search tool will call this function directly.
    filters = PropertySearchFilters(listing_type="rent", locality="Powai", bedrooms=0)

    results = search_properties(db, filters)

    assert [p.listing_code for p in results] == ["PAI-DEMO-014"]
