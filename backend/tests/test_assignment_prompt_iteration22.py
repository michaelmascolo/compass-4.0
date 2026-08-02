"""Iteration 22 — assignment_prompt passthrough backend tests.

Verifies:
  - POST /api/sessions accepts an optional 'assignment_prompt' and returns it
  - GET /api/sessions/{id} returns the stored assignment_prompt
  - Omitting assignment_prompt defaults to empty string
  - Prompt is display-only: it MUST NOT be fed into engine prompt build
"""
import os
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # Fallback: read frontend .env directly
    from pathlib import Path
    for line in Path("/app/frontend/.env").read_text().splitlines():
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE_URL = line.split("=", 1)[1].strip().rstrip("/")

API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def api_client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def test_health(api_client):
    r = api_client.get(f"{API}/", timeout=15)
    assert r.status_code == 200
    assert "message" in r.json()


def test_create_session_with_assignment_prompt(api_client):
    payload = {
        "assignment": "TEST_ Argue whether social media improves or harms teen friendships.",
        "assignment_prompt": "TEST_ Does social media improve or harm teen friendships? Take a clear position and defend it.",
        "pedagogical_purpose": "TEST_ Help the student form a central claim.",
        "current_writing_task": "TEST_ Draft your essay.",
        "teacher_notes": "",
    }
    r = api_client.post(f"{API}/sessions", json=payload, timeout=20)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "id" in data
    assert data["assignment_prompt"] == payload["assignment_prompt"]
    assert data["assignment"] == payload["assignment"]

    # GET verifies persistence
    sid = data["id"]
    g = api_client.get(f"{API}/sessions/{sid}", timeout=15)
    assert g.status_code == 200
    got = g.json()
    assert got["assignment_prompt"] == payload["assignment_prompt"]


def test_create_session_without_assignment_prompt(api_client):
    payload = {
        "assignment": "TEST_ Argue whether social media improves or harms teen friendships.",
        "pedagogical_purpose": "TEST_ Help the student form a central claim.",
        "current_writing_task": "TEST_ Draft your essay.",
    }
    r = api_client.post(f"{API}/sessions", json=payload, timeout=20)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("assignment_prompt", "") == ""

    # GET returns empty string too
    sid = data["id"]
    g = api_client.get(f"{API}/sessions/{sid}", timeout=15)
    assert g.status_code == 200
    got = g.json()
    assert got.get("assignment_prompt", "") == ""


def test_assignment_prompt_not_in_engine_prompt():
    """Assert the code path that builds the engine prompt does NOT include
    session.assignment_prompt. This is a static-source assertion (not a runtime
    LLM call) so it's cheap and deterministic."""
    src = open("/app/backend/server.py").read()
    # Locate _build_prompt body
    start = src.index("def _build_prompt(")
    # Take ~2500 chars which encompasses the whole function
    body = src[start:start + 2500]
    assert "assignment_prompt" not in body, (
        "assignment_prompt should NOT be referenced inside _build_prompt; "
        "it is display-only and must not be fed to the engine."
    )
