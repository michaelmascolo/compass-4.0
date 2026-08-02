"""Milestone 14 — Developmental Integration & Calibration — Iteration 19 lean regression.

FOCUSED verification per review request (M14 30/30 already passed in a prior eval).
Confirms no M6-M13 regression + M14 fields/UI populate.

Session (2 interact calls):
  Turn 1: FIRST DRAFT (messy, many problems) via kind='writing'
    - theory.integration_calibration.applies == True
    - primary_framework non-empty
    - supporting_frameworks list (may be empty but must be a list)
    - calibration_check + consistency_check + integration_notes present
    - scaffolding_control.primary_target non-empty (M11 ONE target)
    - intervention.focus == 'writing' (M5A)
    - AI invitation contains only ONE ask (no 'also', 'secondly', 'another thing',
      and at most one '?' -- soft check: not >2)
    - theory.reader_construction.applies == True (drafted text present, M12)
    - theory.revision_development.applies == False (first submission, M13)

  Turn 2: REVISE via kind='revise' (growth revision)
    - integration_calibration remains applies=True + primary_framework populated
    - revision_development.applies == True (M13)
    - scaffolding_control.primary_target still ONE non-empty target
    - intervention.focus == 'writing' (M5A) preserved

Total: 2 SSE calls (~90-130s). Well within review budget.

Run:  pytest /app/backend/tests/test_milestone14_iteration19.py -v -s
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
    _envp = Path("/app/frontend/.env")
    if _envp.exists():
        for _line in _envp.read_text().splitlines():
            if _line.strip().startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = _line.split("=", 1)[1].strip()
                break
assert BASE_URL, "REACT_APP_BACKEND_URL must be set"
BASE_URL = BASE_URL.rstrip("/")
API = f"{BASE_URL}/api"

VALID_MODES = {
    "developmental_question", "explicit_instruction", "brief_demonstration",
    "guided_revision", "reflection", "consolidation",
}
VALID_CYCLES = {"continue", "consolidate_and_return", "stop"}

# Multi-ask flags: invitation must ask ONLY one thing.
MULTI_ASK_FLAGS = [
    r"\balso[,: ]",
    r"\bsecondly\b",
    r"\banother (?:thing|question|point)\b",
    r"\bin addition\b",
    r"\bfurthermore\b",
    r"\bmoreover\b",
    r"\bas well as\b.*\?",
]


def _multi_ask_flags(text):
    low = (text or "").lower()
    hits = [p for p in MULTI_ASK_FLAGS if re.search(p, low)]
    return hits


def sse_interact(client, sid, payload, timeout=200):
    started = time.time()
    with client.post(
        f"{API}/sessions/{sid}/interact",
        json=payload, stream=True, timeout=timeout,
        headers={"Accept": "text/event-stream"},
    ) as r:
        if r.status_code != 200:
            return r.status_code, None, r.text
        buf, done, err, saw_done = "", None, None, False
        for chunk in r.iter_content(chunk_size=None, decode_unicode=True):
            if not chunk:
                continue
            buf += chunk
            while "\n\n" in buf:
                raw, buf = buf.split("\n\n", 1)
                ev, data_parts = "message", []
                for line in raw.split("\n"):
                    if not line or line.startswith(":"):
                        continue
                    if line.startswith("event:"):
                        ev = line[6:].strip()
                    elif line.startswith("data:"):
                        data_parts.append(line[5:].strip())
                data = "".join(data_parts)
                if ev == "done":
                    saw_done = True
                    if data:
                        done = json.loads(data)
                elif ev == "error" and data:
                    try:
                        err = json.loads(data).get("detail")
                    except Exception:
                        err = data
            if done is not None or err is not None:
                break
        if done is not None:
            done["_elapsed_seconds"] = time.time() - started
            done["_saw_done_event"] = saw_done
        return r.status_code, done, err


def sse_with_retry(client, sid, payload, retries=3, timeout=200):
    last = (None, None, None)
    for attempt in range(retries):
        status, data, err = sse_interact(client, sid, payload, timeout)
        last = (status, data, err)
        if status == 200 and data is not None:
            return status, data, err
        if err is not None:
            break
        time.sleep(4)
    return last


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _new_session(client):
    payload = {
        "assignment": "Argue whether social media improves or harms teen friendships. Provide a clear thesis with reasons and evidence.",
        "pedagogical_purpose": "Help the student form and clarify a central claim that organizes the essay.",
        "current_writing_task": "Draft your essay.",
        "teacher_notes": "",
    }
    r = client.post(f"{API}/sessions", json=payload, timeout=30)
    assert r.status_code == 200, r.text
    b = r.json()
    assert "id" in b and b["id"], b
    return b["id"]


def _ic(s): return s["theory"].get("integration_calibration", {}) or {}
def _sc(s): return s["theory"].get("scaffolding_control", {}) or {}
def _rc(s): return s["theory"].get("reader_construction", {}) or {}
def _rd(s): return s["theory"].get("revision_development", {}) or {}
def _iv(s): return s["interactions"][-1]["intervention"]
def _ai(s): return s["turns"][-1]["content"]


# ---------------------------------------------------------------------------
# One session, two turns: writing then revise. Class-scoped shared state.
# ---------------------------------------------------------------------------
class TestM14IntegrationCalibration:

    @pytest.fixture(scope="class")
    def state(self, client):
        sid = _new_session(client)
        return {"sid": sid}

    def test_t1_messy_first_draft_populates_integration_calibration(self, client, state):
        # A draft with MANY problems: no thesis, messy order, no evidence, abrupt ending.
        draft = (
            "Social media. Teens use it. Some good some bad. "
            "My cousin is on it a lot. Anyway thats what I think. The end."
        )
        status, s, err = sse_with_retry(client, state["sid"], {"kind": "writing", "content": draft})
        assert status == 200 and s is not None, f"turn1 SSE failed: err={err}"
        assert s.get("_saw_done_event") is True

        # ---- M14: integration_calibration populated ----
        ic = _ic(s)
        assert ic.get("applies") is True, f"integration_calibration.applies must be True, got {ic!r}"
        assert (ic.get("primary_framework") or "").strip(), f"primary_framework must be non-empty: {ic!r}"
        assert isinstance(ic.get("supporting_frameworks"), list), f"supporting_frameworks must be list: {ic!r}"
        assert (ic.get("calibration_check") or "").strip(), f"calibration_check must be non-empty: {ic!r}"
        assert (ic.get("consistency_check") or "").strip(), f"consistency_check must be non-empty: {ic!r}"
        assert (ic.get("integration_notes") or "").strip(), f"integration_notes must be non-empty: {ic!r}"

        # ---- M11: single primary_target, valid mode + cycle_status ----
        sc = _sc(s)
        pt = (sc.get("primary_target") or "").strip()
        assert pt, f"M11 primary_target must be non-empty: {sc!r}"
        assert sc.get("instructional_mode") in VALID_MODES, sc
        assert sc.get("cycle_status") in VALID_CYCLES, sc

        # ---- M5A: intervention.focus == writing; AI must not echo student's exact text ----
        iv = _iv(s)
        assert iv.get("focus") == "writing", f"M5A focus must be 'writing', got {iv.get('focus')!r}"
        assert draft not in _ai(s), "AI must not rewrite / echo the student's exact text (M5A)"

        # ---- Single-ask check on the student-facing invitation ----
        ai_text = _ai(s)
        flags = _multi_ask_flags(ai_text)
        assert not flags, f"invitation contains multi-ask flags {flags}: {ai_text!r}"
        # Loose count: not more than 2 question marks (one primary ask; a clarifying sub-clause is ok).
        qcount = ai_text.count("?")
        assert qcount <= 2, f"invitation has too many questions ({qcount}): {ai_text!r}"

        # ---- M12: reader_construction.applies True (drafted text exists) ----
        rc = _rc(s)
        assert rc.get("applies") is True, f"M12 reader_construction.applies must be True: {rc!r}"

        # ---- M13: revision_development.applies False on first submission ----
        rd = _rd(s)
        assert rd.get("applies") is False, f"first-draft rd.applies must be False, got {rd!r}"

        # Save some info for the revise turn's regression sanity.
        state["t1_pt"] = pt
        state["t1_pf"] = ic.get("primary_framework", "")

    def test_t2_revise_growth_maintains_integration_calibration(self, client, state):
        # A substantive revision that adds a claim + causal mechanism.
        revised = (
            "Social media harms close teen friendships because constant, shallow "
            "contact crowds out the focused, in-person attention that deep friendship "
            "needs to grow. When teens replace long conversations with quick likes and "
            "comments, they lose the practice of listening carefully to one person over time."
        )
        status, s, err = sse_with_retry(client, state["sid"], {"kind": "revise", "content": revised})
        assert status == 200 and s is not None, f"turn2 SSE failed: err={err}"
        assert s.get("_saw_done_event") is True

        # ---- M14 remains populated on revise turn ----
        ic = _ic(s)
        assert ic.get("applies") is True, f"integration_calibration.applies must be True: {ic!r}"
        assert (ic.get("primary_framework") or "").strip(), f"primary_framework must be non-empty: {ic!r}"
        assert isinstance(ic.get("supporting_frameworks"), list)
        assert (ic.get("calibration_check") or "").strip()
        assert (ic.get("consistency_check") or "").strip()
        assert (ic.get("integration_notes") or "").strip()

        # ---- M11: still one target ----
        sc = _sc(s)
        assert (sc.get("primary_target") or "").strip(), f"M11 primary_target must be non-empty: {sc!r}"
        assert sc.get("instructional_mode") in VALID_MODES, sc
        assert sc.get("cycle_status") in VALID_CYCLES, sc

        # ---- M13: revision_development.applies True after revise ----
        rd = _rd(s)
        assert rd.get("applies") is True, f"revise rd.applies must be True: {rd!r}"

        # ---- M5A intact ----
        iv = _iv(s)
        assert iv.get("focus") == "writing", f"M5A focus must be 'writing': {iv!r}"
        assert revised not in _ai(s), "AI must not echo the student's revised text"

        # ---- Single-ask check ----
        ai_text = _ai(s)
        flags = _multi_ask_flags(ai_text)
        assert not flags, f"revise invitation has multi-ask flags {flags}: {ai_text!r}"

        # ---- M12 still applies (there is drafted text) ----
        rc = _rc(s)
        assert rc.get("applies") is True, f"M12 reader_construction.applies must be True: {rc!r}"
