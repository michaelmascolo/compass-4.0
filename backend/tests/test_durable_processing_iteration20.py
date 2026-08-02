"""Iteration 20 — Durable Revision Processing (Infrastructure Phase 1).

Verifies the new async processing model where POST /interact returns immediately
with a placeholder AI turn (status='processing') and a background task fills it in.
"""
import os
import time
import pytest
import requests

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"

PRESET = {
    "assignment": "Argue whether social media improves or harms teen friendships.",
    "pedagogical_purpose": "Help the student form and clarify a central claim that organizes the essay.",
    "current_writing_task": "Draft your essay.",
    "teacher_notes": "TEST_iteration20",
}

FIRST_DRAFT = (
    "I think social media is kind of good and kind of bad. Some people say it makes friends closer "
    "but other people say it makes people feel lonely. My friend Sara uses TikTok a lot. She sometimes "
    "feels bad after scrolling. But she also uses it to talk to friends who moved away. So it depends. "
    "There is a lot to say about this topic and I am not sure exactly where I stand yet."
)

REVISE_DRAFT = (
    "Social media harms teen friendships more than it helps them, because the kinds of connection it "
    "offers are shallow and comparison-driven. My friend Sara uses TikTok every night; even when she is "
    "messaging friends who moved away, she reports feeling worse afterward because she keeps comparing "
    "her ordinary life to curated highlight reels. Real friendship requires attention that platforms "
    "engineered for engagement systematically fragment. The problem is not that teens use social media; "
    "the problem is that the medium reshapes what counts as being with someone."
)


@pytest.fixture(scope="module")
def session_id():
    r = requests.post(f"{BASE}/sessions", json=PRESET, timeout=30)
    assert r.status_code in (200, 201), r.text
    sid = r.json()["id"]
    yield sid


def _wait_until_idle(sid, max_wait=220, interval=2.5):
    """Poll until no turn is 'processing'. Returns the final session dict."""
    start = time.time()
    while time.time() - start < max_wait:
        r = requests.get(f"{BASE}/sessions/{sid}", timeout=15)
        assert r.status_code == 200
        s = r.json()
        if not any(t.get("status") == "processing" for t in s.get("turns", [])):
            return s
        time.sleep(interval)
    pytest.fail(f"Session {sid} still had processing turn after {max_wait}s")


# --- Test 1: immediate return + placeholder + background completion --------

class TestImmediateReturnAndBackgroundCompletion:
    def test_interact_returns_immediately_with_processing_placeholder(self, session_id):
        t0 = time.time()
        r = requests.post(
            f"{BASE}/sessions/{session_id}/interact",
            json={"kind": "writing", "content": FIRST_DRAFT},
            timeout=30,
        )
        dt = time.time() - t0
        assert r.status_code == 200, r.text
        assert dt < 10.0, f"POST took {dt:.1f}s — should return immediately"
        s = r.json()
        turns = s["turns"]
        # last two turns: student (complete) + ai (processing)
        assert turns[-2]["role"] == "student"
        assert turns[-2]["status"] == "complete"
        assert turns[-2]["content"].startswith("I think social media")
        assert turns[-1]["role"] == "ai"
        assert turns[-1]["status"] == "processing"
        assert turns[-1]["kind"] == "pending"
        assert turns[-1]["content"] == ""
        # save the ai turn id for the concurrency test
        pytest.processing_ai_id = turns[-1]["id"]
        pytest.turn_count_after_first_post = len(turns)

    def test_concurrent_post_returns_409(self, session_id):
        """While a turn is processing, a second interact must return 409."""
        r = requests.post(
            f"{BASE}/sessions/{session_id}/interact",
            json={"kind": "writing", "content": "another attempt"},
            timeout=15,
        )
        assert r.status_code == 409, f"expected 409, got {r.status_code}: {r.text}"
        assert "already being prepared" in r.json().get("detail", "").lower()

    def test_polling_shows_completion_with_populated_fields(self, session_id):
        s = _wait_until_idle(session_id, max_wait=220)
        turns = s["turns"]
        ai = turns[-1]
        assert ai["role"] == "ai"
        assert ai["status"] == "complete", f"final AI turn status={ai['status']}"
        assert ai["content"].strip(), "AI turn content must be non-empty"
        assert ai["kind"] in ("invitation", "message"), ai["kind"]
        # interactions/theory_history each grew by exactly 1
        assert len(s["interactions"]) == 1, s["interactions"]
        assert len(s["theory_history"]) == 1, s["theory_history"]

    def test_m1_m14_regression_after_writing_turn(self, session_id):
        r = requests.get(f"{BASE}/sessions/{session_id}", timeout=15)
        s = r.json()
        theory = s["theory"]
        last_interaction = s["interactions"][-1]
        # M5A intervention.focus='writing'
        assert last_interaction["intervention"]["focus"] == "writing"
        # M11 scaffolding_control.primary_target present
        assert theory["scaffolding_control"]["primary_target"].strip(), theory["scaffolding_control"]
        # M12 reader_construction present
        assert "reader_construction" in theory
        assert theory["reader_construction"].get("applies") is True or bool(theory["reader_construction"].get("current_orientation"))
        # M13 revision_development.applies=False on first submission
        assert theory["revision_development"]["applies"] is False
        # M14 integration_calibration.applies=True with primary_framework
        ic = theory["integration_calibration"]
        assert ic["applies"] is True, ic
        assert ic["primary_framework"].strip(), ic
        # AI must not rewrite the student's draft — it must not echo the exact submission
        ai_content = s["turns"][-1]["content"]
        assert FIRST_DRAFT not in ai_content, "AI echoed student's full draft"


# --- Test 2: resubmit-when-idle + revise turn regression --------------------

class TestResubmitAndReviseRegression:
    def test_resubmit_when_idle_returns_200(self, session_id):
        # no processing turn should exist now
        r0 = requests.get(f"{BASE}/sessions/{session_id}", timeout=15)
        assert not any(t["status"] == "processing" for t in r0.json()["turns"])
        t0 = time.time()
        r = requests.post(
            f"{BASE}/sessions/{session_id}/interact",
            json={"kind": "revise", "content": REVISE_DRAFT},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        assert time.time() - t0 < 10.0
        s = r.json()
        # placeholder AI turn should be present as last
        assert s["turns"][-1]["status"] == "processing"
        assert s["turns"][-1]["role"] == "ai"

    def test_revise_completes_and_m13_m14_regression(self, session_id):
        # revise can take 60-180s
        s = _wait_until_idle(session_id, max_wait=260)
        theory = s["theory"]
        ai_last = s["turns"][-1]
        assert ai_last["status"] == "complete"
        assert ai_last["content"].strip()
        # interactions grew to 2
        assert len(s["interactions"]) == 2
        # M13 revision_development.applies=True after revise
        assert theory["revision_development"]["applies"] is True, theory["revision_development"]
        # M14 still populated
        assert theory["integration_calibration"]["applies"] is True
        assert theory["integration_calibration"]["primary_framework"].strip()
        # M11 scaffolding still has a primary target
        assert theory["scaffolding_control"]["primary_target"].strip()
        # M5A focus stays 'writing'
        assert s["interactions"][-1]["intervention"]["focus"] == "writing"


# --- Test 3: durability across simulated disconnect -------------------------

class TestDurabilityAcrossDisconnect:
    def test_disconnect_still_persists(self):
        # brand new session so we don't collide with prior processing state
        r = requests.post(f"{BASE}/sessions", json={**PRESET, "teacher_notes": "TEST_iter20_disconnect"}, timeout=30)
        sid = r.json()["id"]
        # kick off the interact and immediately abandon (POST already returns fast)
        t0 = time.time()
        r2 = requests.post(
            f"{BASE}/sessions/{sid}/interact",
            json={"kind": "writing", "content": FIRST_DRAFT},
            timeout=30,
        )
        assert r2.status_code == 200
        assert time.time() - t0 < 10.0
        # Do NOT poll. Sleep as if the client vanished.
        time.sleep(80)
        # Now check — the background task must have completed and persisted.
        r3 = requests.get(f"{BASE}/sessions/{sid}", timeout=15)
        s = r3.json()
        # if still processing, give it another 60s (revise-style prompts sometimes take longer)
        if any(t["status"] == "processing" for t in s["turns"]):
            time.sleep(60)
            s = requests.get(f"{BASE}/sessions/{sid}", timeout=15).json()
        ai = s["turns"][-1]
        assert ai["status"] == "complete", f"disconnect lost work — status={ai['status']}"
        assert ai["content"].strip(), "disconnect produced empty AI turn"
        assert len(s["interactions"]) == 1
        # no duplicate student turn
        student_turns = [t for t in s["turns"] if t["role"] == "student"]
        assert len(student_turns) == 1


# --- Test 4: empty submission guard remains ---------------------------------

class TestGuards:
    def test_empty_submission_400(self, session_id):
        r = requests.post(
            f"{BASE}/sessions/{session_id}/interact",
            json={"kind": "writing", "content": "   "},
            timeout=15,
        )
        assert r.status_code == 400
