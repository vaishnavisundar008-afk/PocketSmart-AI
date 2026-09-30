import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app import database
from app.config import settings
from app.main import app
from app.services.gemini import generate_plan


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test-pocket.db")
    database.initialize_database()
    with TestClient(app) as test_client:
        yield test_client


def register(client):
    client.get("/register")
    response = client.post(
        "/register",
        data={"name": "Taylor Quinn", "email": "taylor@example.com", "password": "correct-horse-battery"},
    )
    assert response.status_code == 200
    assert client.cookies.get("pocketsmart_session")
    return client.cookies["pocketsmart_csrf"]


def test_registration_authentication_and_session_endpoints(client):
    csrf = register(client)
    session = client.get("/session-info")
    assert session.json()["authenticated"] is True
    assert session.json()["user_id"]

    token = client.post(
        "/token",
        data={"username": "taylor@example.com", "password": "correct-horse-battery"},
    )
    assert token.status_code == 200
    assert token.json()["token_type"] == "bearer"
    assert client.get("/session-data").json()["recommendation_count"] == 0

    logout = client.post("/logout", data={"csrf_token": csrf}, follow_redirects=False)
    assert logout.status_code == 303
    assert client.get("/session-info").json()["authenticated"] is False


def test_all_planners_save_budget_limited_history(client):
    csrf = register(client)
    headers = {"X-CSRF-Token": csrf}
    home = client.post(
        "/generate-home",
        headers=headers,
        json={
            "budget": 1200,
            "currency": "USD",
            "style": "Warm modern",
            "rooms": [{"room_type": "Bedroom", "items": [{"name": "Reading lights", "quantity": 2}]}],
        },
    )
    party = client.post(
        "/generate-party",
        headers=headers,
        json={
            "budget": 1200,
            "currency": "USD",
            "event_type": "Birthday",
            "guests": 24,
            "city": "Austin",
            "venue": "Outdoor",
            "food_style": "Mixed menu",
        },
    )
    jewelry = client.post(
        "/generate-jewelry",
        headers=headers,
        data={"budget": "800", "currency": "USD", "occasion": "Wedding", "style": "Modern minimal"},
        files={"image": ("", b"", "application/octet-stream")},
    )

    for response in (home, party, jewelry):
        assert response.status_code == 200, response.text
        plan = response.json()
        assert plan["source"] == "fallback"
        assert sum(item["price"] * item["quantity"] for item in plan["recommendations"]) <= plan["budget"]
        assert plan["id"]

    history = client.get("/api/history").json()["items"]
    assert len(history) == 3
    assert {entry["planner"] for entry in history} == {"home", "party", "jewelry"}


def test_planners_require_authentication_and_csrf(client):
    assert client.post("/generate-party", json={"budget": 100, "event_type": "Dinner", "guests": 5, "city": "Rome"}).status_code == 401
    csrf = register(client)
    response = client.post(
        "/generate-party",
        json={"budget": 100, "event_type": "Dinner", "guests": 5, "city": "Rome"},
    )
    assert response.status_code == 403

    response = client.post(
        "/generate-party",
        headers={"X-CSRF-Token": csrf},
        json={"budget": 0, "event_type": "Dinner", "guests": 5, "city": "Rome"},
    )
    assert response.status_code == 422


def test_gemini_structured_response_and_image_are_supported(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")
    model_result = {
        "summary": "A balanced bedroom refresh with room for finishing touches.",
        "allocations": [{"category": "Lighting", "amount": 70, "rationale": "Keep the room comfortable."}],
        "recommendations": [
            {"name": "Warm bedside lamps", "category": "Lighting", "price": 70, "quantity": 1, "platform": "IKEA", "reason": "Soft task lighting."}
        ],
        "insights": ["Verify current prices before ordering."],
    }
    api_response = SimpleNamespace(
        raise_for_status=lambda: None,
        json=lambda: {"candidates": [{"content": {"parts": [{"text": json.dumps(model_result)}]}}]},
    )
    with patch("app.services.gemini.httpx.post", return_value=api_response) as post:
        result = generate_plan(
            "jewelry",
            {"occasion": "Wedding", "style": "Classic"},
            100,
            "USD",
            image_bytes=b"image-bytes",
            image_mime="image/png",
        )

    assert result["source"] == "gemini"
    assert result["recommendations"][0]["url"].startswith("https://www.ikea.com/search/")
    request = post.call_args.kwargs["json"]
    sent_parts = request["contents"][0]["parts"]
    assert len(sent_parts) == 2
    assert sent_parts[1]["inlineData"]["mimeType"] == "image/png"