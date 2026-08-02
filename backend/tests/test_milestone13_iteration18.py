"""Milestone 13 — Revision as Development — Iteration 18 lean acceptance.

Focused on exactly the 5 flows the review request specifies:
  Session A (2 interacts):
    1. Create session (POST /api/sessions -> id).
    2. FIRST DRAFT (writing) 'Social media is bad for friends.':
       - revision_development.applies == False
       - scaffolding_control.primary_target non-empty (M11 one-target)
       - intervention.focus == 'writing' (M5A preserved)
       - primary_target/mode/cycle_status validity
    3. REVISE with growth: 'Social media harms close friendships because ...':
       - revision_development.applies == True
       - development_detected non-empty AND starts with 'yes' (growth)
       - primary_growth non-empty
       - transfer_message non-empty
       - theory_history has >=2 versions (v1 preserved distinct from v_last)
       - intervention.focus == 'writing' (M5A)
       - invitation does NOT rewrite student's text
       - invitation does NOT count edits (no 'you made N changes' / 'you revised a lot')
       - REGRESSION SANITY on same response:
         * cp.primary non-empty
         * reader_construction.applies == True (M12 preserved)
         * scaffolding_control.instructional_mode in valid set
         * cycle_status in {continue, consolidate_and_return, stop}
         * no 502 / SSE completes cleanly

  Session B (2 interacts):
    4. FIRST DRAFT 'Social media is bad for teen friendships.'
    5. REVISE (superficial) 'Social media is really bad for teenage friendships.':
       - revision_development.applies == True
       - development_detected is 'no' or 'partial' (no fabricated growth)
       - remaining_opportunity non-empty
       - invitation does NOT count edits

Total: 4 interact calls across 2 sessions (~5 within budget).
Run: pytest /app/backend/tests/test_milestone13_iteration18.py -v -s
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

# Edit-counting / scorekeeping phrasing (revision must NOT be measured in edits).
EDIT_COUNTING_FLAGS = [
    r"you made \d+ (?:changes|edits|revisions)",
    r"you made (?:many|several|a lot of|lots of|numerous) (?:changes|edits|revisions)",
    r"\d+ (?:changes|edits|revisions) made",
    r"you revised a lot",
    r"you did a lot of revising",
    r"lots of edits",
    r"nice (?:job )?(?:on )?(?:the )?(?:many|several) (?:changes|edits|revisions)",
    r"great (?:number|amount) of (?:changes|edits|revisions)",
]


def _has_edit_counting(text):
    low = (text or "").lower()
    return [p for p in EDIT_COUNTING_FLAGS if re.search(p, low)]


def sse_interact(client, sid, payload, timeout=180):
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


def sse_with_retry(client, sid, payload, retries=3, timeout=180):
    last = (None, None, None)
    for attempt in range(retries):
        status, data, err = sse_interact(client, sid, payload, timeout)
        last = (status, data, err)
        if status == 200 and data is not None:
            return status, data, err
        if err is not None:
            break
        time.sleep(4)  # empty-done frame retry
    return last


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _new_session(client):
    payload = {
        "assignment": "Argue whether social media improves or harms teen friendships.",
        "pedagogical_purpose": "Help the student grow as a writer across drafts.",
        "current_writing_task": "Work on your draft.",
        "teacher_notes": "",
    }
    r = client.post(f"{API}/sessions", json=payload, timeout=30)
    assert r.status_code == 200, r.text
    b = r.json()
    assert "id" in b and b["id"], b
    return b["id"]


def _rd(s): return s["theory"].get("revision_development", {}) or {}
def _sc(s): return s["theory"].get("scaffolding_control", {}) or {}
def _cp(s): return s["theory"].get("communicative_purpose", {}) or {}
def _rc(s): return s["theory"].get("reader_construction", {}) or {}
def _iv(s): return s["interactions"][-1]["intervention"]
def _ai(s): return s["turns"][-1]["content"]


class TestGrowthSessionA:
    """Session A: FIRST DRAFT (applies=false) then REVISE growth (applies=true + transfer_message)."""

    @pytest.fixture(scope="class")
    def session_state(self, client):
        # Create session ONCE for the whole class, and pass the running session across turns.
        sid = _new_session(client)
        return {"sid": sid, "s1": None, "s2": None}

    def test_a1_first_draft_applies_false(self, client, session_state):
        sid = session_state["sid"]
        draft = "Social media is bad for friends."
        status, s, err = sse_with_retry(client, sid, {"kind": "writing", "content": draft})
        assert status == 200 and s is not None, f"turn1 SSE failed: err={err}"
        assert s.get("_saw_done_event") is True
        assert s.get("_elapsed_seconds", 999) < 180

        # AI must not echo student's exact text.
        assert draft not in _ai(s), "AI must not rewrite / echo the student's text"

        # M13 first-submission control: revision_development MUST NOT apply.
        rd = _rd(s)
        assert rd.get("applies") is False, f"first-draft rd.applies must be False, got {rd!r}"
        for k in ("development_detected", "primary_growth", "communication_change",
                  "reader_change", "remaining_opportunity", "transfer_message"):
            assert not (rd.get(k) or "").strip(), f"{k!r} should be empty on first submission: {rd.get(k)!r}"

        # M11: single primary_target, valid mode + cycle_status.
        sc = _sc(s)
        assert (sc.get("primary_target") or "").strip(), f"primary_target must be non-empty: {sc!r}"
        assert sc.get("instructional_mode") in VALID_MODES, sc
        assert sc.get("cycle_status") in VALID_CYCLES, sc

        # M5A: focus=='writing'.
        iv = _iv(s)
        assert iv.get("focus") == "writing", iv

        session_state["s1"] = s
        print(f"\n[A1 first-draft] applies={rd.get('applies')} target={sc.get('primary_target')[:60]!r} mode={sc.get('instructional_mode')} cycle={sc.get('cycle_status')}")

    def test_a2_revise_growth_triggers_primary_growth_and_transfer(self, client, session_state):
        assert session_state.get("s1") is not None, "test_a1 must run first"
        sid = session_state["sid"]
        draft = (
            "Social media harms close friendships because constant, shallow contact "
            "crowds out the focused attention deep friendship needs."
        )
        status, s, err = sse_with_retry(client, sid, {"kind": "revise", "content": draft})
        assert status == 200 and s is not None, f"turn2 SSE failed: err={err}"
        assert s.get("_saw_done_event") is True
        assert s.get("_elapsed_seconds", 999) < 180

        # AI must NOT rewrite student text.
        assert draft not in _ai(s), "AI invitation must not echo the student's exact revised text"

        # M13 growth: applies + development_detected startswith 'yes' + primary_growth + transfer_message.
        rd = _rd(s)
        assert rd.get("applies") is True, f"revise rd.applies must be True, got {rd!r}"
        dd = (rd.get("development_detected") or "").strip().lower()
        assert dd, f"development_detected non-empty: {rd!r}"
        assert dd.startswith("yes"), (
            f"substantial-growth revise must yield development_detected startswith 'yes': got {dd!r}"
        )
        pg = (rd.get("primary_growth") or "").strip()
        assert pg, f"primary_growth must be non-empty for growth: {rd!r}"
        tm = (rd.get("transfer_message") or "").strip()
        assert tm, f"transfer_message must be non-empty for growth: {rd!r}"

        # No edit-counting language.
        inv = _ai(s)
        ec = _has_edit_counting(inv)
        assert not ec, f"edit-counting leaked: {ec} | {inv[:250]}"

        # theory_history must now have >=2 versions AND v1 preserved distinct.
        hist = s.get("theory_history", [])
        assert len(hist) >= 2, f"theory_history should have >=2, got {len(hist)}"
        assert hist[0].get("version") == 1, f"first history entry must be v1: {hist[0].get('version')}"
        assert hist[-1].get("version") >= 2, f"last history entry version >=2: {hist[-1].get('version')}"
        assert hist[0].get("theory") != hist[-1].get("theory"), (
            "theory_history v1 appears overwritten (identical to v_last)"
        )

        # M5A preserved: focus='writing'.
        iv = _iv(s)
        assert iv.get("focus") == "writing", iv

        # REGRESSION SANITY: cp.primary + reader_construction.applies + mode + cycle_status.
        cp = _cp(s)
        assert (cp.get("primary") or "").strip(), f"cp.primary must be non-empty: {cp!r}"
        rc = _rc(s)
        assert rc.get("applies") is True, f"reader_construction.applies must be True: {rc!r}"
        sc = _sc(s)
        assert sc.get("instructional_mode") in VALID_MODES, sc
        assert sc.get("cycle_status") in VALID_CYCLES, sc
        assert (sc.get("primary_target") or "").strip(), f"primary_target still non-empty: {sc!r}"

        session_state["s2"] = s
        print(
            f"\n[A2 growth] dd={dd[:40]!r} pg={pg[:50]!r} tm={tm[:50]!r} "
            f"hist_versions={[h.get('version') for h in hist]} cp.primary={cp.get('primary')!r} "
            f"rc.applies=True target={sc.get('primary_target')[:50]!r}"
        )


class TestSuperficialSessionB:
    """Session B: FIRST DRAFT then REVISE (superficial edit) — no fabricated growth."""

    @pytest.fixture(scope="class")
    def session_state(self, client):
        sid = _new_session(client)
        return {"sid": sid, "s1": None, "s2": None}

    def test_b1_first_draft(self, client, session_state):
        sid = session_state["sid"]
        draft = "Social media is bad for teen friendships."
        status, s, err = sse_with_retry(client, sid, {"kind": "writing", "content": draft})
        assert status == 200 and s is not None, f"turn1 SSE failed: err={err}"
        assert _rd(s).get("applies") is False, f"first draft rd.applies must be False: {_rd(s)!r}"
        iv = _iv(s)
        assert iv.get("focus") == "writing"
        session_state["s1"] = s

    def test_b2_superficial_revise_yields_no_or_partial_and_remaining_opportunity(self, client, session_state):
        assert session_state.get("s1") is not None, "b1 must run first"
        sid = session_state["sid"]
        draft = "Social media is really bad for teenage friendships."
        status, s, err = sse_with_retry(client, sid, {"kind": "revise", "content": draft})
        assert status == 200 and s is not None, f"turn2 SSE failed: err={err}"
        assert draft not in _ai(s), "AI must not echo student text"

        rd = _rd(s)
        assert rd.get("applies") is True, f"revise rd.applies True: {rd!r}"
        dd = (rd.get("development_detected") or "").strip().lower()
        assert dd, f"development_detected must be non-empty on revise: {rd!r}"
        assert dd.startswith("no") or dd.startswith("partial"), (
            f"superficial edit must yield 'no' or 'partial' (no fabricated growth), got {dd!r}"
        )
        ro = (rd.get("remaining_opportunity") or "").strip()
        assert ro, f"remaining_opportunity must be non-empty for superficial: {rd!r}"

        # No edit-counting language.
        inv = _ai(s)
        ec = _has_edit_counting(inv)
        assert not ec, f"edit-counting leaked in superficial invitation: {ec} | {inv[:250]}"

        # M11 + M5A still enforced.
        sc = _sc(s)
        assert (sc.get("primary_target") or "").strip(), f"primary_target must be non-empty: {sc!r}"
        assert sc.get("instructional_mode") in VALID_MODES
        assert sc.get("cycle_status") in VALID_CYCLES
        iv = _iv(s)
        assert iv.get("focus") == "writing"

        session_state["s2"] = s
        print(f"\n[B2 superficial] dd={dd[:40]!r} ro={ro[:70]!r} target={sc.get('primary_target')[:50]!r}")
