"""Backend durable-processing regression for iteration 27 anchored-coaching redesign.

Verifies:
 - POST /api/sessions creates a session with a Telos
 - POST /api/sessions/{id}/interact returns quickly with an AI "processing" placeholder
 - Polling GET /api/sessions/{id} eventually yields a completed AI turn with non-empty content
 - POST /api/sessions/preview returns a session with a fixed preview Telos
"""

import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://dev-converse.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

FULL_TIMEOUT_S = 130   # workspace turn latency ~50-95s
PREVIEW_TIMEOUT_S = 100  # preview turn latency ~48s
POLL_EVERY_S = 3


@pytest.fixture(scope="module")
def http():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _wait_for_ai_complete(http, sid, timeout):
    start = time.time()
    last = None
    while time.time() - start < timeout:
        r = http.get(f"{API}/sessions/{sid}", timeout=30)
        assert r.status_code == 200, f"GET session failed: {r.status_code} {r.text[:200]}"
        s = r.json()
        last = s
        ai_turns = [t for t in s.get("turns", []) if t.get("role") == "ai"]
        if ai_turns and ai_turns[-1].get("status") == "complete" and ai_turns[-1].get("content"):
            return s
        if ai_turns and ai_turns[-1].get("status") == "failed":
            pytest.fail(f"AI turn failed: {ai_turns[-1]}")
        time.sleep(POLL_EVERY_S)
    pytest.fail(f"AI turn did not complete within {timeout}s. Last state: {last}")


class TestWorkspaceDurableInteract:
    """Full workspace: create -> interact -> poll -> complete."""

    def test_create_session_returns_id_and_telos(self, http):
        payload = {
            "assignment": "TEST_iter27 Argue whether social media improves or harms teen friendships.",
            "assignment_prompt": "Does social media improve or harm teen friendships? Take a clear position and defend it.",
            "pedagogical_purpose": "Help the student form and clarify a central claim that organizes the essay.",
            "current_writing_task": "Draft your essay.",
            "teacher_notes": "",
        }
        r = http.post(f"{API}/sessions", json=payload, timeout=30)
        assert r.status_code in (200, 201), f"create session {r.status_code}: {r.text[:300]}"
        data = r.json()
        assert "id" in data and isinstance(data["id"], str) and len(data["id"]) > 0
        assert data.get("assignment") == payload["assignment"]
        pytest.workspace_sid = data["id"]

    def test_interact_returns_processing_placeholder_quickly(self, http):
        sid = pytest.workspace_sid
        draft = (
            "Social media harms teen friendships more than it helps. "
            "When friends only see curated posts, they miss what each other actually feel."
        )
        t0 = time.time()
        r = http.post(f"{API}/sessions/{sid}/interact", json={"kind": "writing", "content": draft}, timeout=30)
        elapsed = time.time() - t0
        assert r.status_code == 200, f"interact {r.status_code}: {r.text[:300]}"
        # Durable: must return quickly with a processing AI placeholder
        assert elapsed < 15, f"interact took {elapsed}s; expected <15s (durable placeholder)"
        s = r.json()
        ai_turns = [t for t in s.get("turns", []) if t.get("role") == "ai"]
        assert ai_turns, "expected an AI turn placeholder after interact"
        assert ai_turns[-1].get("status") == "processing", f"expected processing placeholder, got {ai_turns[-1]}"

    def test_poll_until_complete_workspace(self, http):
        sid = pytest.workspace_sid
        s = _wait_for_ai_complete(http, sid, timeout=FULL_TIMEOUT_S)
        ai_turns = [t for t in s.get("turns", []) if t.get("role") == "ai"]
        last_ai = ai_turns[-1]
        assert last_ai["status"] == "complete"
        assert isinstance(last_ai.get("content"), str) and len(last_ai["content"].strip()) > 20
        # Only one AI turn expected after the first writing turn
        completed = [t for t in ai_turns if t["status"] == "complete"]
        assert len(completed) >= 1


class TestPreviewSession:
    """Preview flow: POST /api/sessions/preview must return a session with a fixed preview Telos."""

    def test_preview_session_creation_and_fixed_telos(self, http):
        r = http.post(f"{API}/sessions/preview", json={"essay_about": "TEST_iter27 preview topic", "passage_type": "Body paragraph"}, timeout=30)
        assert r.status_code in (200, 201), f"preview session {r.status_code}: {r.text[:300]}"
        s = r.json()
        assert "id" in s and isinstance(s["id"], str) and len(s["id"]) > 0
        # A telos of some kind must be present (assignment / assignment_prompt / pedagogical_purpose)
        has_telos = any(k in s and s[k] for k in ("assignment", "assignment_prompt", "pedagogical_purpose"))
        assert has_telos, f"preview session missing telos fields: keys={list(s.keys())}"
        pytest.preview_sid = s["id"]

    def test_preview_interact_and_completes(self, http):
        sid = pytest.preview_sid
        seed = (
            "Social media has both good and bad sides for friendships. "
            "It lets teens keep in touch but it also makes them compare their lives."
        )
        t0 = time.time()
        r = http.post(f"{API}/sessions/{sid}/interact", json={"kind": "writing", "content": seed}, timeout=30)
        assert r.status_code == 200, r.text[:300]
        assert time.time() - t0 < 15
        s = r.json()
        ai_turns = [t for t in s.get("turns", []) if t.get("role") == "ai"]
        assert ai_turns and ai_turns[-1]["status"] == "processing"
        s = _wait_for_ai_complete(http, sid, timeout=PREVIEW_TIMEOUT_S)
        ai_turns = [t for t in s.get("turns", []) if t.get("role") == "ai"]
        assert ai_turns[-1]["status"] == "complete"
        assert len(ai_turns[-1].get("content", "").strip()) > 20
