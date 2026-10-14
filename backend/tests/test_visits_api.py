"""
Tests for the slots and booking endpoints. tx_client rolls back every write.
"""

from datetime import date, datetime, timedelta

import pytest

from app.services.visits import IST, available_slots

CODE = "PAI-DEMO-002"
SOLD = "PAI-DEMO-011"
PHONE = "98765 43210"


@pytest.fixture
def free_slot(tx_db) -> datetime:
    return available_slots(tx_db, CODE)[-1]


def booking(slot: datetime, **overrides) -> dict:
    return {"listing_code": CODE, "starts_at": slot.isoformat(), "name": "Asha Demo",
            "phone": PHONE, **overrides}


# ---------- GET /properties/{code}/slots ----------


def test_slots_for_available_listing(tx_client):
    response = tx_client.get(f"/properties/{CODE}/slots")

    assert response.status_code == 200
    body = response.json()
    assert body["listing_code"] == CODE
    assert body["slots"]
    for slot in body["slots"]:
        assert slot.endswith("+05:30")
        assert 10 <= datetime.fromisoformat(slot).hour <= 17


def test_slots_unknown_and_not_bookable(tx_client):
    assert tx_client.get("/properties/PAI-DEMO-999/slots").status_code == 404
    assert tx_client.get(f"/properties/{SOLD}/slots").status_code == 409


def test_slots_date_outside_window(tx_client):
    too_late = date.today() + timedelta(days=30)
    response = tx_client.get(f"/properties/{CODE}/slots", params={"date": str(too_late)})
    assert response.status_code == 422


# ---------- POST /visits ----------


def test_book_visit_201_and_no_phone_in_response(tx_client, free_slot):
    response = tx_client.post("/visits", json=booking(free_slot))

    assert response.status_code == 201
    body = response.json()
    assert body["listing_code"] == CODE
    assert body["status"] == "booked"
    assert datetime.fromisoformat(body["starts_at"]) == free_slot
    # Nothing in the response needs the phone, so it is never sent back.
    assert "phone" not in body
    assert "43210" not in response.text


def test_book_taken_slot_409(tx_client, free_slot):
    assert tx_client.post("/visits", json=booking(free_slot)).status_code == 201

    response = tx_client.post("/visits", json=booking(free_slot, phone="91234 56789"))

    assert response.status_code == 409
    assert "taken" in response.json()["detail"]


def test_book_invalid_phone_422(tx_client, free_slot):
    response = tx_client.post("/visits", json=booking(free_slot, phone="12345"))
    assert response.status_code == 422
    assert "mobile" in response.json()["detail"]


def test_book_off_hours_slot_422(tx_client, free_slot):
    response = tx_client.post("/visits", json=booking(free_slot.replace(hour=20)))
    assert response.status_code == 422


def test_book_sold_listing_409(tx_client, free_slot):
    response = tx_client.post("/visits", json=booking(free_slot, listing_code=SOLD))
    assert response.status_code == 409


def test_book_unknown_listing_404(tx_client, free_slot):
    response = tx_client.post("/visits", json=booking(free_slot, listing_code="PAI-DEMO-999"))
    assert response.status_code == 404


def test_book_rejects_unknown_fields(tx_client, free_slot):
    response = tx_client.post("/visits", json=booking(free_slot, status="completed"))
    assert response.status_code == 422


def test_cors_allows_post_visits_preflight(tx_client):
    response = tx_client.options(
        "/visits",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_slot_times_are_ist(free_slot):
    assert free_slot.utcoffset() == IST.utcoffset(None)
