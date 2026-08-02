"""Iteration 24 — Compass Engine revision.
Verifies:
  (A) Multi-turn Developmental Memory: seeds on turn 1, EVOLVES (same element merged,
      episodes bumped, trend refreshed) on turn 2 — not duplicated.
  (B) Profile persists (GET /sessions returns accumulated developmental_profile
      after both turns).
  (C) Instructional-network reasoning: exactly ONE primary_target/turn; the
      surrounding neighbors are reasoned WITH (invitation shows integration).
  (D) Regression — governed instruction + durable processing intact.
Reasoning is LLM-bound and SLOW (single turn 45-120s); poll patiently.
"""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/") + "/api"
POLL_TIMEOUT = 240  # seconds per turn (revise turns can exceed 120s per prompt)
POLL_INTERVAL = 3

ASSIGNMENT = "TEST_iter24: Does social media improve or harm teen friendships? Take a position and defend it."
DRAFT_1 = ("Social media changes teen friendships. It harms some aspects and helps in some "
           "other way. Its both good and bad.")
DRAFT_2 = ("Social media mostly harms teen friendships. Although it helps friends stay in "
           "contact, it replaces deep face-to-face connection with shallow likes and comments, "
           "and constant comparison damages self-esteem. On balance the harms outweigh the "
           "benefits for most teens.")


@pytest.fixture(scope="module")
def session_id():
    payload = {
        "assignment": "TEST_iter24 social-media-friendships",
        "pedagogical_purpose": "argument",
        "current_writing_task": "take a position and defend it in one paragraph",
        "assignment_prompt": ASSIGNMENT,
    }
    r = requests.post(f"{BASE_URL}/sessions", json=payload, timeout=30)
    assert r.status_code in (200, 201), f"create session failed: {r.status_code} {r.text}"
    sid = r.json().get("id")
    assert sid, f"no id in create: {r.text}"
    return sid


def _poll_until_complete(sid, prev_completed_ai_count):
    """Wait for the AI turn count of status='complete' to grow by 1."""
    start = time.time()
    last = None
    while time.time() - start < POLL_TIMEOUT:
        r = requests.get(f"{BASE_URL}/sessions/{sid}", timeout=30)
        assert r.status_code == 200, r.text
        s = r.json()
        last = s
        ai_complete = [t for t in s["turns"] if t["role"] == "ai" and t.get("status") == "complete"]
        if len(ai_complete) >= prev_completed_ai_count + 1:
            return s
        # fail fast on any 'failed' status
        failed = [t for t in s["turns"] if t.get("status") == "failed"]
        if failed:
            raise AssertionError(f"turn failed: {failed}")
        time.sleep(POLL_INTERVAL)
    raise AssertionError(f"poll timed out after {POLL_TIMEOUT}s; last session={last}")


def _submit(sid, content, kind="draft"):
    """POST /interact should return immediately with a 'processing' AI turn."""
    t0 = time.time()
    r = requests.post(
        f"{BASE_URL}/sessions/{sid}/interact",
        json={"content": content, "kind": kind},
        timeout=30,
    )
    elapsed = time.time() - t0
    assert r.status_code == 200, f"interact failed: {r.status_code} {r.text}"
    body = r.json()
    ai_processing = [t for t in body["turns"] if t["role"] == "ai" and t.get("status") == "processing"]
    assert len(ai_processing) == 1, f"expected 1 processing AI turn, got {ai_processing}"
    assert elapsed < 15, f"POST /interact took {elapsed:.1f}s; expected immediate return"
    return body


# ---------------------------------------------------------------------------
# Turn 1 — seed the developmental profile
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def turn1(session_id):
    _submit(session_id, DRAFT_1, kind="writing")
    s = _poll_until_complete(session_id, prev_completed_ai_count=0)
    return s


def test_turn1_profile_is_seeded(turn1):
    prof = turn1.get("developmental_profile") or []
    assert isinstance(prof, list), "developmental_profile must be a list"
    assert len(prof) >= 1, f"expected >=1 observation after turn 1, got {prof}"
    # each observation has the required shape
    for o in prof:
        assert isinstance(o.get("element"), str) and o["element"].strip(), f"bad element: {o}"
        assert isinstance(o.get("control_statement"), str), f"bad control_statement: {o}"
        assert o.get("trend") in {"confused", "emerging", "developing", "consolidating", "independent", ""}, (
            f"unexpected trend: {o.get('trend')}")
        assert isinstance(o.get("episodes"), int) and o["episodes"] >= 1, f"bad episodes: {o}"


def test_turn1_governed_instruction_intact(turn1):
    ir = turn1["theory"]["instructional_reasoning"]
    assert ir.get("applies") is True
    assert ir["active_instructional_element"].strip(), "active_instructional_element must be set"
    assert ir["next_student_act"].strip(), "next_student_act must be set"
    # intervention focus = writing
    intervention = turn1["theory"].get("intervention") or {}
    # intervention lives at session.interactions[-1].intervention; check there too
    last_ix = (turn1.get("interactions") or [])[-1]
    focus = (last_ix.get("intervention") or {}).get("focus") or intervention.get("focus")
    assert focus == "writing", f"intervention.focus expected 'writing', got {focus}"


def test_turn1_one_target_and_network_no_errors(turn1):
    sc = turn1["theory"]["scaffolding_control"]
    pt = sc.get("primary_target") or ""
    assert isinstance(pt, str) and pt.strip(), f"primary_target must be a single non-empty string; got {pt!r}"
    # active_instructional_element is a singular string (not a list)
    active = turn1["theory"]["instructional_reasoning"]["active_instructional_element"]
    assert isinstance(active, str) and active.strip()


# ---------------------------------------------------------------------------
# Turn 2 — same element should be UPDATED (episodes bumped), not duplicated
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def turn2(session_id, turn1):
    _submit(session_id, DRAFT_2, kind="revise")
    s = _poll_until_complete(session_id, prev_completed_ai_count=1)
    return s


def test_turn2_profile_merged_not_duplicated(turn1, turn2):
    prof1 = turn1.get("developmental_profile") or []
    prof2 = turn2.get("developmental_profile") or []
    # No element should appear twice (merge-by-element contract)
    lc = [o["element"].strip().lower() for o in prof2 if o.get("element")]
    assert len(lc) == len(set(lc)), f"duplicate elements in profile: {lc}"
    # At least one element from turn 1 should still be present in turn 2 (persisted)
    els1 = {o["element"].strip().lower() for o in prof1}
    els2 = set(lc)
    assert els1 & els2, f"turn1 elements {els1} not found in turn2 profile {els2}"


def test_turn2_same_element_episodes_bumped_or_trend_advanced(turn1, turn2):
    """The same element seen across both turns must show evolution: either
    episodes incremented to >=2, or trend advanced (confused->emerging/developing)."""
    ORDER = ["confused", "emerging", "developing", "consolidating", "independent"]
    prof1 = {o["element"].strip().lower(): o for o in (turn1.get("developmental_profile") or [])}
    prof2 = {o["element"].strip().lower(): o for o in (turn2.get("developmental_profile") or [])}
    shared = set(prof1) & set(prof2)
    assert shared, f"no shared element across turns; turn1={list(prof1)}, turn2={list(prof2)}"
    movement_found = False
    for el in shared:
        o1, o2 = prof1[el], prof2[el]
        episodes_bumped = (o2.get("episodes", 0) >= 2 and o2.get("episodes", 0) > o1.get("episodes", 0))
        t1 = (o1.get("trend") or "").lower()
        t2 = (o2.get("trend") or "").lower()
        trend_advanced = (t1 in ORDER and t2 in ORDER and ORDER.index(t2) > ORDER.index(t1))
        if episodes_bumped or trend_advanced:
            movement_found = True
            break
    assert movement_found, (
        f"expected episodes>=2 OR trend advancement on a shared element; "
        f"turn1={[(k,v.get('trend'),v.get('episodes')) for k,v in prof1.items()]}, "
        f"turn2={[(k,v.get('trend'),v.get('episodes')) for k,v in prof2.items()]}")


def test_turn2_evidence_of_developmental_movement_populated(turn2):
    ir = turn2["theory"]["instructional_reasoning"]
    evd = (ir.get("evidence_of_developmental_movement") or "").strip()
    assert evd, "theory.instructional_reasoning.evidence_of_developmental_movement must be populated after turn 2"
    # Should not be a trivial 'initial' after revise turn
    assert evd.lower() != "initial", f"evidence still says 'initial' after revise turn: {evd!r}"


def test_turn2_profile_persists_via_get(session_id, turn2):
    """After turn 2, GET /sessions/{id} still returns accumulated profile."""
    r = requests.get(f"{BASE_URL}/sessions/{session_id}", timeout=30)
    assert r.status_code == 200
    s = r.json()
    prof = s.get("developmental_profile") or []
    assert len(prof) >= len(turn2.get("developmental_profile") or []), (
        f"profile shrank on refetch: {prof} vs {turn2.get('developmental_profile')}")
    # persisted structure must include episodes >=1 on every item
    for o in prof:
        assert o.get("episodes", 0) >= 1


def test_turn2_one_target_and_regression(turn2):
    sc = turn2["theory"]["scaffolding_control"]
    pt = sc.get("primary_target") or ""
    assert isinstance(pt, str) and pt.strip(), f"turn2 primary_target must be singular; got {pt!r}"
    active = turn2["theory"]["instructional_reasoning"]["active_instructional_element"]
    assert isinstance(active, str) and active.strip()
    ic = turn2["theory"]["integration_calibration"]
    assert ic.get("applies") is True
    ir = turn2["theory"]["instructional_reasoning"]
    assert ir.get("applies") is True
    # Governed instruction: intervention.focus == 'writing' on the revise turn
    last_ix = (turn2.get("interactions") or [])[-1]
    focus = (last_ix.get("intervention") or {}).get("focus")
    assert focus == "writing", f"intervention.focus expected 'writing', got {focus}"


def test_turn2_invitation_does_not_rewrite_student_text(turn2):
    ai_complete = [t for t in turn2["turns"] if t["role"] == "ai" and t.get("status") == "complete"]
    assert ai_complete, "no complete AI turn found on turn 2"
    inv = (ai_complete[-1].get("content") or "").lower()
    # co-authoring red flags
    bad_signals = [
        "here's a thesis:",
        "your thesis should be",
        "here is your thesis",
        "rewrite it as:",
        "try this thesis:",
    ]
    for sig in bad_signals:
        assert sig not in inv, f"invitation appears to co-author with signal {sig!r}: {inv[:400]}"


def test_turn2_invitation_integrates_with_network(turn2):
    """Qualitative: invitation should mention SOME network-neighbor concept
    (assignment / purpose / reader / audience / evidence / argument) — i.e.
    reason with the surrounding network, not the isolated target."""
    ai_complete = [t for t in turn2["turns"] if t["role"] == "ai" and t.get("status") == "complete"]
    inv = (ai_complete[-1].get("content") or "").lower()
    network_signals = ["assignment", "purpose", "reader", "audience", "argument",
                       "position", "claim", "evidence", "reason", "why"]
    hits = [s for s in network_signals if s in inv]
    assert hits, f"invitation does not connect to network neighbors: {inv[:400]}"
