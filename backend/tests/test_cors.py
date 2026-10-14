"""
Tests for CORS: which browser origins may read API responses.

CORS is enforced by the browser. The server only decides whether to add
Access-Control-Allow-Origin; without it, the browser hides the response
from the page's JavaScript.
"""

ALLOWED = "http://localhost:5173"
OTHER = "https://evil.example"


def test_allowed_origin_gets_cors_header(client):
    response = client.get("/health", headers={"Origin": ALLOWED})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED


def test_other_origin_gets_no_cors_header(client):
    response = client.get("/health", headers={"Origin": OTHER})

    # The server still answers; the browser is what blocks the page.
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_preflight_for_get_from_allowed_origin_succeeds(client):
    # Browsers send this OPTIONS "preflight" before some cross-origin requests.
    response = client.options(
        "/properties/search",
        headers={"Origin": ALLOWED, "Access-Control-Request-Method": "GET"},
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED


def test_preflight_from_other_origin_is_rejected(client):
    response = client.options(
        "/properties/search",
        headers={"Origin": OTHER, "Access-Control-Request-Method": "GET"},
    )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_preflight_for_json_post_is_allowed(client):
    # The chat UI sends POST /chat with a JSON body.
    response = client.options(
        "/chat",
        headers={
            "Origin": ALLOWED,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED


def test_preflight_for_delete_is_rejected(client):
    # Only GET and POST are allowed cross-origin; other writes stay blocked.
    response = client.options(
        "/properties/search",
        headers={"Origin": ALLOWED, "Access-Control-Request-Method": "DELETE"},
    )

    assert response.status_code == 400
