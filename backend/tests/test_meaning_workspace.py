"""Backend tests for Meaning Workspace V1 (Compass).

Covers:
  * Session creation prerequisite.
  * GET /api/meaning-maps/by-session/{session_id} idempotency.
  * PUT /api/meaning-maps/{map_id} save + reload persistence (objects / connections / groups).
  * POST /api/meaning-maps/{map_id}/events append behaviour (timestamps, ids, session_id, accumulation).
  * POST /api/meaning-maps/{map_id}/coach — appends to coach_log AND is READ-ONLY
    (never mutates objects/connections/groups).
"""
import copy
import json
import os
import uuid

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # Fallback to frontend/.env so pytest can be invoked without env exports
    try:
        with open("/app/frontend/.env") as fh:
            for line in fh:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
                    break
    except Exception:
        pass
assert BASE_URL, "REACT_APP_BACKEND_URL missing"

API = f"{BASE_URL}/api"


# --------------------------------------------------------------------------- fixtures
@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def session_id(client):
    payload = {
        "assignment": "TEST_MW assignment",
        "pedagogical_purpose": "TEST_MW purpose",
        "current_writing_task": "TEST_MW task",
    }
    r = client.post(f"{API}/sessions", json=payload, timeout=30)
    assert r.status_code == 200, r.text
    sid = r.json()["id"]
    assert isinstance(sid, str) and sid
    return sid


# --------------------------------------------------------------------------- get_or_create
class TestGetOrCreateMap:
    def test_idempotent_returns_same_map(self, client, session_id):
        r1 = client.get(f"{API}/meaning-maps/by-session/{session_id}", timeout=15)
        assert r1.status_code == 200, r1.text
        m1 = r1.json()
        assert m1["session_id"] == session_id
        assert "id" in m1 and isinstance(m1["id"], str)
        # Structural fields must be present as lists (may be empty on first call, may
        # already have data if this test runs after TestSaveMap under xdist parallelism).
        assert isinstance(m1["objects"], list)
        assert isinstance(m1["connections"], list)
        assert isinstance(m1["groups"], list)

        r2 = client.get(f"{API}/meaning-maps/by-session/{session_id}", timeout=15)
        assert r2.status_code == 200
        m2 = r2.json()
        # Idempotent — same map id on repeat calls
        assert m2["id"] == m1["id"]


# --------------------------------------------------------------------------- save & reload
class TestSaveMap:
    def test_put_persists_objects_connections_groups(self, client, session_id):
        m = client.get(f"{API}/meaning-maps/by-session/{session_id}", timeout=15).json()
        map_id = m["id"]
        objs = [
            {"id": "o1", "text": "Idea A", "color": "sage", "x": 100, "y": 120, "group_id": "g1"},
            {"id": "o2", "text": "Idea B", "color": "sky",  "x": 320, "y": 120, "notes": "some note"},
        ]
        conns = [{"id": "c1", "from_id": "o1", "to_id": "o2", "label": "supports", "directed": True}]
        groups = [{"id": "g1", "label": "Cluster One", "x": 50, "y": 60, "w": 260, "h": 200}]

        r = client.put(f"{API}/meaning-maps/{map_id}",
                       json={"objects": objs, "connections": conns, "groups": groups},
                       timeout=15)
        assert r.status_code == 200, r.text
        saved = r.json()
        assert saved["objects"] == objs
        assert saved["connections"] == conns
        assert saved["groups"] == groups

        # Reload via GET returns same data
        reloaded = client.get(f"{API}/meaning-maps/by-session/{session_id}", timeout=15).json()
        assert reloaded["id"] == map_id
        assert reloaded["objects"] == objs
        assert reloaded["connections"] == conns
        assert reloaded["groups"] == groups

    def test_put_unknown_map_returns_404(self, client):
        r = client.put(f"{API}/meaning-maps/{uuid.uuid4()}",
                       json={"objects": [], "connections": [], "groups": []}, timeout=10)
        assert r.status_code == 404


# --------------------------------------------------------------------------- events
class TestEventLog:
    def test_events_append_with_timestamp_and_session_id(self, client, session_id):
        m = client.get(f"{API}/meaning-maps/by-session/{session_id}", timeout=15).json()
        map_id = m["id"]
        before_count = len(m.get("events", []))

        batch1 = {"events": [
            {"type": "created_object", "object_id": "o1"},
            {"type": "edited_object", "object_id": "o1", "field": "text"},
        ]}
        r = client.post(f"{API}/meaning-maps/{map_id}/events", json=batch1, timeout=10)
        assert r.status_code == 200, r.text
        assert r.json() == {"logged": 2}

        # Second batch — must append, not replace
        batch2 = {"events": [{"type": "moved_object", "object_id": "o1"},
                             {"type": "created_connection", "connection_id": "c1"}]}
        r2 = client.post(f"{API}/meaning-maps/{map_id}/events", json=batch2, timeout=10)
        assert r2.status_code == 200
        assert r2.json() == {"logged": 2}

        reloaded = client.get(f"{API}/meaning-maps/by-session/{session_id}", timeout=15).json()
        events = reloaded.get("events", [])
        assert len(events) == before_count + 4
        types = [e.get("type") for e in events[-4:]]
        assert types == ["created_object", "edited_object", "moved_object", "created_connection"]
        for e in events[-4:]:
            assert e.get("id") and isinstance(e["id"], str)
            assert e.get("session_id") == session_id
            assert e.get("logged_at") and isinstance(e["logged_at"], str)

    def test_events_empty_batch_ok(self, client, session_id):
        m = client.get(f"{API}/meaning-maps/by-session/{session_id}", timeout=15).json()
        r = client.post(f"{API}/meaning-maps/{m['id']}/events", json={"events": []}, timeout=10)
        assert r.status_code == 200
        assert r.json() == {"logged": 0}

    def test_events_unknown_map_404(self, client):
        r = client.post(f"{API}/meaning-maps/{uuid.uuid4()}/events",
                        json={"events": [{"type": "x"}]}, timeout=10)
        assert r.status_code == 404


# --------------------------------------------------------------------------- coach read-only guarantee
class TestCoachReadOnly:
    def test_coach_appends_note_and_never_mutates_map(self, client, session_id):
        # Seed the map with concrete data so we can compare byte-for-byte
        m = client.get(f"{API}/meaning-maps/by-session/{session_id}", timeout=15).json()
        map_id = m["id"]
        objs = [
            {"id": "a", "text": "Photosynthesis converts light", "color": "sage",
             "x": 100, "y": 100, "notes": "cells", "group_id": "gA"},
            {"id": "b", "text": "Plants need sunlight", "color": "sky", "x": 300, "y": 100},
            {"id": "c", "text": "Ocean plants and shade tolerance?", "color": "paper",
             "x": 500, "y": 100},
        ]
        conns = [{"id": "e1", "from_id": "a", "to_id": "b", "label": "supports", "directed": True},
                 {"id": "e2", "from_id": "b", "to_id": "c", "label": "raises", "directed": False}]
        groups = [{"id": "gA", "label": "Core Idea", "x": 60, "y": 60, "w": 260, "h": 200}]
        put = client.put(f"{API}/meaning-maps/{map_id}",
                         json={"objects": objs, "connections": conns, "groups": groups}, timeout=15)
        assert put.status_code == 200

        before = client.get(f"{API}/meaning-maps/by-session/{session_id}", timeout=15).json()
        before_objs = copy.deepcopy(before["objects"])
        before_conns = copy.deepcopy(before["connections"])
        before_groups = copy.deepcopy(before["groups"])
        before_coach_len = len(before.get("coach_log", []))
        before_events = copy.deepcopy(before.get("events", []))

        # Call coach (Claude via Emergent LLM key — may take up to 30s)
        r = client.post(f"{API}/meaning-maps/{map_id}/coach",
                        json={"trigger": "on_demand"}, timeout=60)
        assert r.status_code == 200, r.text
        note = r.json()
        assert note.get("id") and isinstance(note["id"], str)
        assert note.get("kind") in ("observation", "question")
        assert note.get("text") and isinstance(note["text"], str) and len(note["text"]) > 0
        assert note.get("trigger") == "on_demand"
        assert note.get("created_at")

        after = client.get(f"{API}/meaning-maps/by-session/{session_id}", timeout=15).json()

        # CRITICAL: structural fields must be byte-identical
        assert after["objects"] == before_objs, "coach mutated objects!"
        assert after["connections"] == before_conns, "coach mutated connections!"
        assert after["groups"] == before_groups, "coach mutated groups!"
        # Events must not be touched by the coach endpoint (only the client's own log_events does)
        assert after.get("events", []) == before_events, "coach mutated events log!"
        # coach_log grew by exactly 1
        after_log = after.get("coach_log", [])
        assert len(after_log) == before_coach_len + 1
        assert after_log[-1]["id"] == note["id"]
        assert after_log[-1]["text"] == note["text"]

    def test_coach_on_empty_map_returns_prompt_without_llm(self, client):
        # Fresh session -> fresh empty map
        r = client.post(f"{API}/sessions",
                        json={"assignment": "TEST_MW empty", "pedagogical_purpose": "p",
                              "current_writing_task": "t"}, timeout=30)
        assert r.status_code == 200
        sid = r.json()["id"]
        m = client.get(f"{API}/meaning-maps/by-session/{sid}", timeout=15).json()
        r2 = client.post(f"{API}/meaning-maps/{m['id']}/coach", json={"trigger": "on_demand"},
                         timeout=15)
        assert r2.status_code == 200
        note = r2.json()
        assert note["kind"] == "observation"
        assert "meaning object" in note["text"].lower() or "canvas" in note["text"].lower()

    def test_coach_unknown_map_404(self, client):
        r = client.post(f"{API}/meaning-maps/{uuid.uuid4()}/coach",
                        json={"trigger": "on_demand"}, timeout=10)
        assert r.status_code == 404
