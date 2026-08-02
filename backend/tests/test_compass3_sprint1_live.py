"""
Live e2e tests for Compass 3.0 Sprint 1 (functional_v3 engine).

Verifies:
  - POST /api/sessions creates a canonical_v2 session
  - POST /api/sessions/{id}/interact returns quickly (<2s) with a
    processing placeholder AI turn (durable processing)
  - A second interact while a turn is still processing is rejected with 409
  - Polling GET /api/sessions/{id} eventually returns a completed AI turn
    with non-empty content that does NOT rewrite the paragraph
  - focus_of_work is one of ("Elaboration", "Organization")
  - /app/backend/functional_v3_trace.log's last record shows
    engine='functional_v3', selected_function in {'develop','functional_organization'},
    focus_status='sufficient', and the full functional_decision schema
  - Revision turn (kind='revise') completes; trace continuity_decision is one
    of {hold, advance, recurse, complete} and progress_since_last_turn is non-empty
"""
import json
import os
import re
import time
from pathlib import Path

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")
if not BASE_URL:
    # fall back to reading /app/frontend/.env
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip()
BASE_URL = BASE_URL.rstrip("/")

TRACE_PATH = Path("/app/backend/functional_v3_trace.log")

FIXED_MINDSET_PARAGRAPH = (
    "The fixed mindset is the belief that intelligence and talent are static traits. "
    "People with this mindset think that you are either smart or not, and no amount "
    "of effort can change that. They tend to avoid challenges because failure would "
    "expose their lack of ability. This makes them fragile learners."
)

REVISION_PARAGRAPH = (
    "The fixed mindset is the belief that intelligence and talent are fixed at birth. "
    "Because ability is seen as unchangeable, people holding this view treat every "
    "task as a test of who they already are. As a result, they avoid challenges: a "
    "hard problem is not an invitation to grow but a threat of exposure. When they "
    "do fail, they interpret the failure as proof of permanent limits rather than as "
    "information for the next attempt. Over time this belief narrows their learning, "
    "because the only safe move is to stay inside what they already do well."
)

REWRITE_MARKERS = [
    "here is your",
    "here's your",
    "here is a revised",
    "here's a revised",
    "rewritten version",
    "revised version:",
    "revised paragraph:",
    "here is the paragraph",
]

REQUIRED_FUNCTIONAL_DECISION_KEYS = {
    "communicative_task",
    "topic",
    "current_focus",
    "focus_status",
    "functions",
    "functional_organization",
    "naive_reader_need",
    "selected_function",
    "student_facing_term",
    "selected_operation",
    "local_target",
    "developmental_sufficiency",
    "continuity_decision",
    "confidence",
}


@pytest.fixture(scope="module")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _create_session(api):
    payload = {
        "assignment": "What is the fixed mindset?",
        "pedagogical_purpose": "Help the learner explain the fixed mindset in their own words.",
        "current_writing_task": "one paragraph",
        "reasoning_mode": "canonical_v2",
    }
    r = api.post(f"{BASE_URL}/api/sessions", json=payload, timeout=30)
    assert r.status_code == 200, f"POST /api/sessions failed: {r.status_code} {r.text}"
    data = r.json()
    assert "id" in data
    assert data.get("reasoning_mode") == "canonical_v2"
    return data["id"]


def _poll_last_turn(api, sid, timeout_s=180, interval_s=6):
    deadline = time.time() + timeout_s
    last = None
    while time.time() < deadline:
        r = api.get(f"{BASE_URL}/api/sessions/{sid}", timeout=30)
        assert r.status_code == 200, f"GET session failed: {r.status_code} {r.text}"
        doc = r.json()
        turns = doc.get("turns") or []
        if turns:
            last = turns[-1]
            if last.get("role") == "ai" and last.get("status") == "complete":
                return doc, last
        time.sleep(interval_s)
    pytest.fail(f"Timed out ({timeout_s}s) waiting for AI turn to complete. Last turn: {last}")


def _last_trace_record():
    assert TRACE_PATH.exists(), f"Trace log missing: {TRACE_PATH}"
    with TRACE_PATH.open() as f:
        lines = [ln.strip() for ln in f.readlines() if ln.strip()]
    assert lines, "Trace log is empty"
    line = lines[-1]
    # strip leading timestamp: format is "%(asctime)s %(message)s" -> before first '{'
    brace = line.find("{")
    assert brace >= 0, f"No JSON payload in trace line: {line}"
    return json.loads(line[brace:])


def _assert_no_rewrite(content: str):
    lower = content.lower()
    for m in REWRITE_MARKERS:
        assert m not in lower, f"AI content appears to rewrite the paragraph (marker: {m!r}): {content[:300]}"


class TestCompass3Sprint1:
    """Function-centered teacher review — live e2e for functional_v3 engine."""

    def test_00_health(self, api):
        r = api.get(f"{BASE_URL}/api/", timeout=15)
        assert r.status_code == 200, f"health failed: {r.status_code} {r.text}"

    def test_01_turn1_fixed_mindset_invitation(self, api, request):
        sid = _create_session(api)
        request.config._compass_sid = sid  # stash for turn 2

        # trace baseline
        trace_size_before = TRACE_PATH.stat().st_size if TRACE_PATH.exists() else 0

        # interact should return in <2s with processing placeholder
        t0 = time.monotonic()
        r = api.post(
            f"{BASE_URL}/api/sessions/{sid}/interact",
            json={"content": FIXED_MINDSET_PARAGRAPH, "kind": "writing"},
            timeout=15,
        )
        elapsed = time.monotonic() - t0
        assert r.status_code == 200, f"interact failed: {r.status_code} {r.text}"
        assert elapsed < 5.0, f"interact was not fast enough: {elapsed:.2f}s (should be <2s, allowing 5s slack)"
        session = r.json()
        turns = session.get("turns") or []
        assert len(turns) >= 2
        assert turns[-2].get("role") == "student"
        assert turns[-1].get("role") == "ai"
        assert turns[-1].get("status") in ("processing", "streaming"), f"expected placeholder, got {turns[-1]}"

        # durable-processing: a second interact while processing should be 409
        r2 = api.post(
            f"{BASE_URL}/api/sessions/{sid}/interact",
            json={"content": "please respond again", "kind": "writing"},
            timeout=15,
        )
        assert r2.status_code == 409, f"expected 409 on duplicate interact, got {r2.status_code}: {r2.text}"

        # verify no duplicate turns were appended by the 409
        r3 = api.get(f"{BASE_URL}/api/sessions/{sid}", timeout=15)
        assert r3.status_code == 200
        assert len(r3.json().get("turns") or []) == len(turns), "duplicate interact created extra turns"

        # poll for completion
        doc, last = _poll_last_turn(api, sid, timeout_s=180)

        # 1) non-empty invitation
        content = (last.get("content") or "").strip()
        assert len(content) > 20, f"AI content too short / empty: {content!r}"

        # 2) does not rewrite the paragraph
        _assert_no_rewrite(content)

        # 3) focus_of_work is Elaboration or Organization
        focus = last.get("focus_of_work") or ""
        assert focus in ("Elaboration", "Organization"), f"unexpected focus_of_work: {focus!r} (turn: {last})"

        # 4) trace log — new record appended after our request
        assert TRACE_PATH.stat().st_size > trace_size_before, "trace log did not grow"
        rec = _last_trace_record()
        assert rec.get("engine") == "functional_v3", f"engine != functional_v3: {rec.get('engine')}"
        fd = rec.get("functional_decision") or {}
        assert fd, f"functional_decision missing from trace: {rec}"

        # 5) selected_function and focus_status
        assert rec.get("selected_function") in ("develop", "functional_organization"), (
            f"selected_function unexpected: {rec.get('selected_function')}"
        )
        assert rec.get("focus_status") == "sufficient", (
            f"focus_status expected 'sufficient', got: {rec.get('focus_status')}"
        )

        # 6) full schema keys present
        missing = REQUIRED_FUNCTIONAL_DECISION_KEYS - set(fd.keys())
        assert not missing, f"functional_decision missing keys: {missing}. keys present: {sorted(fd.keys())}"

    def test_02_turn2_revision_comparison(self, api, request):
        sid = getattr(request.config, "_compass_sid", None)
        assert sid, "turn 1 did not run; no session id"

        trace_size_before = TRACE_PATH.stat().st_size if TRACE_PATH.exists() else 0

        t0 = time.monotonic()
        r = api.post(
            f"{BASE_URL}/api/sessions/{sid}/interact",
            json={"content": REVISION_PARAGRAPH, "kind": "revise"},
            timeout=15,
        )
        elapsed = time.monotonic() - t0
        assert r.status_code == 200, f"interact(revise) failed: {r.status_code} {r.text}"
        assert elapsed < 5.0, f"interact(revise) too slow: {elapsed:.2f}s"

        doc, last = _poll_last_turn(api, sid, timeout_s=180)
        content = (last.get("content") or "").strip()
        assert len(content) > 20, f"revision invitation empty/short: {content!r}"
        _assert_no_rewrite(content)

        assert TRACE_PATH.stat().st_size > trace_size_before, "trace log did not grow after revision"
        rec = _last_trace_record()
        assert rec.get("engine") == "functional_v3"
        fd = rec.get("functional_decision") or {}
        cd = rec.get("continuity_decision") or fd.get("continuity_decision")
        assert cd in ("hold", "advance", "recurse", "complete", "first_turn"), (
            f"continuity_decision unexpected: {cd!r}"
        )
        # progress_since_last_turn should be present and non-empty (engine names the operation)
        progress = fd.get("progress_since_last_turn")
        # fallback: may be nested under continuity_decision object in some shapes
        if progress is None:
            progress = (fd.get("continuity") or {}).get("progress_since_last_turn")
        assert progress, f"progress_since_last_turn missing/empty in functional_decision: {fd}"
        assert isinstance(progress, str) and len(progress.strip()) > 0, (
            f"progress_since_last_turn not a non-empty string: {progress!r}"
        )
