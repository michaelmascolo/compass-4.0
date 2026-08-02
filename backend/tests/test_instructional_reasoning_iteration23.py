"""
iteration_23 — Governed Canonical Instruction (Instructional-Object layer).

Backend verification:
  1. Instructional-Object governance:
       theory.instructional_reasoning populated on a fresh writing turn.
  2. Teaches + reorients + one act (qualitative on invitation text).
  3. Answer-the-assignment check (drift reorientation).
  4. Regression: durable processing + one-target + integration_calibration.applies.

LLM latency: single turn ~45-70s; poll patiently.
"""

import os
import re
import time
import json
import requests
import pytest

def _load_backend_url():
    v = os.environ.get("REACT_APP_BACKEND_URL")
    if not v:
        # Fallback: read from frontend/.env at repo root
        try:
            with open("/app/frontend/.env") as f:
                for line in f:
                    if line.startswith("REACT_APP_BACKEND_URL="):
                        v = line.split("=", 1)[1].strip()
                        break
        except Exception:
            pass
    assert v, "REACT_APP_BACKEND_URL not set"
    return v.rstrip("/")


BASE_URL = _load_backend_url()
API = f"{BASE_URL}/api"

ASSIGNMENT = "Argue whether social media improves or harms teen friendships."
ASSIGNMENT_PROMPT = (
    "Does social media improve or harm teen friendships? "
    "Take a position and defend it."
)
PEDAGOGICAL_PURPOSE = (
    "Help the student form and clarify a central claim that organizes the essay, "
    "and understand what each part of the writing is doing for the reader."
)
CURRENT_WRITING_TASK = "Draft your essay."

DRIFT_DRAFT = (
    "Social media changes teen friendships. It harms some aspects and helps in some other way. "
    "It helps keep kids connected, but also keeps them separated. It creates a sense of fomo "
    "that makes kids depressed. Its both good and bad."
)

POLL_INTERVAL_S = 3
POLL_TIMEOUT_S = 200


@pytest.fixture(scope="module")
def session_id():
    payload = {
        "assignment": f"TEST_iter23: {ASSIGNMENT}",
        "pedagogical_purpose": PEDAGOGICAL_PURPOSE,
        "current_writing_task": CURRENT_WRITING_TASK,
        "teacher_notes": "TEST_iteration23_instructional_reasoning",
        "assignment_prompt": ASSIGNMENT_PROMPT,
    }
    r = requests.post(f"{API}/sessions", json=payload, timeout=30)
    assert r.status_code in (200, 201), f"POST /sessions -> {r.status_code} {r.text}"
    sid = r.json()["id"]
    assert sid
    return sid


@pytest.fixture(scope="module")
def completed_session(session_id):
    """Submit drift draft, poll until AI turn is 'complete'. Return final session."""
    t0 = time.monotonic()
    r = requests.post(
        f"{API}/sessions/{session_id}/interact",
        json={"kind": "writing", "content": DRIFT_DRAFT},
        timeout=30,
    )
    latency = time.monotonic() - t0
    assert r.status_code == 200, f"POST /interact -> {r.status_code} {r.text}"
    # Regression: durable processing must return quickly
    assert latency < 15, f"POST /interact took {latency:.1f}s (expected <15s for durable-processing)"

    body = r.json()
    turns = body.get("turns", [])
    assert any(t.get("status") == "processing" and t.get("role") == "ai" for t in turns), \
        "Immediate response must include an AI turn with status='processing'"

    # Poll until complete
    deadline = time.monotonic() + POLL_TIMEOUT_S
    final = None
    while time.monotonic() < deadline:
        rs = requests.get(f"{API}/sessions/{session_id}", timeout=30)
        assert rs.status_code == 200, f"GET /sessions -> {rs.status_code}"
        s = rs.json()
        ai_turns = [t for t in s.get("turns", []) if t.get("role") == "ai"]
        if ai_turns and ai_turns[-1].get("status") == "complete":
            final = s
            break
        if ai_turns and ai_turns[-1].get("status") == "failed":
            pytest.fail(f"AI turn failed: {ai_turns[-1]}")
        time.sleep(POLL_INTERVAL_S)
    assert final is not None, f"Reasoning did not complete within {POLL_TIMEOUT_S}s"
    return final


# ---------------------------------------------------------------------------
# 1. Instructional-Object governance
# ---------------------------------------------------------------------------
class TestInstructionalReasoning:
    def test_ir_block_present_and_applies(self, completed_session):
        ir = completed_session["theory"]["instructional_reasoning"]
        assert ir is not None, "theory.instructional_reasoning missing"
        # applies default is True; must not be False
        assert ir.get("applies", True) is not False

    def test_ir_current_unit_of_writing(self, completed_session):
        ir = completed_session["theory"]["instructional_reasoning"]
        v = (ir.get("current_unit_of_writing") or "").strip()
        assert v, "current_unit_of_writing empty"

    def test_ir_active_instructional_element_is_canonical(self, completed_session):
        ir = completed_session["theory"]["instructional_reasoning"]
        el = (ir.get("active_instructional_element") or "").strip().lower()
        assert el, "active_instructional_element empty"
        # For a drift-with-no-position draft answering a "take a position" prompt,
        # the relevant canonical element should be Thesis / Central Claim / Position
        # (aliases exist in instructional_objects.json).
        expected_tokens = ["thesis", "central claim", "position", "main idea", "controlling idea"]
        assert any(tok in el for tok in expected_tokens), (
            f"active_instructional_element='{el}' — expected canonical thesis/central-claim element"
        )

    def test_ir_qualitative_fields_populated(self, completed_session):
        ir = completed_session["theory"]["instructional_reasoning"]
        for k in (
            "element_communicative_purpose",
            "student_current_organization",
            "canonical_performance_structure",
            "primary_developmental_tension",
            "next_student_act",
            "degree_of_student_control",
            "continue_consolidate_release_or_shift",
        ):
            v = (ir.get(k) or "").strip()
            assert v, f"instructional_reasoning.{k} empty"

    def test_ir_selected_resources_non_empty_and_not_only_focused_question(self, completed_session):
        ir = completed_session["theory"]["instructional_reasoning"]
        res = ir.get("selected_developmental_resources") or []
        assert isinstance(res, list) and len(res) >= 1, f"resources: {res!r}"
        # Must not be ONLY 'focused question' — the whole point of the governed
        # instruction revision is that the AI teaches, not merely asks questions.
        normalized = [r.strip().lower() for r in res if isinstance(r, str)]
        assert normalized != ["focused question"], (
            "selected_developmental_resources must not be only 'focused question' — the "
            "engine must also teach, e.g. 'brief direct explanation', 'introduction of "
            f"canonical terminology'. Got: {res!r}"
        )

    def test_ir_degree_of_student_control_valid(self, completed_session):
        ir = completed_session["theory"]["instructional_reasoning"]
        v = (ir.get("degree_of_student_control") or "").strip().lower()
        assert v, "degree_of_student_control empty"
        # Loose match — allow synonyms
        assert any(tok in v for tok in ["scaffold", "emerg", "increas", "independent"]), (
            f"degree_of_student_control='{v}' unexpected"
        )

    def test_ir_continue_decision_valid(self, completed_session):
        ir = completed_session["theory"]["instructional_reasoning"]
        v = (ir.get("continue_consolidate_release_or_shift") or "").strip().lower()
        assert v, "continue_consolidate_release_or_shift empty"
        assert any(
            tok in v for tok in ["continue", "consolidate", "release", "shift"]
        ), f"decision='{v}' unexpected"

    def test_intervention_focus_is_writing(self, completed_session):
        interactions = completed_session.get("interactions", [])
        assert interactions, "no interactions recorded"
        last = interactions[-1]
        focus = (last.get("intervention", {}).get("focus") or "").strip().lower()
        assert focus == "writing", f"intervention.focus='{focus}' (expected 'writing')"


# ---------------------------------------------------------------------------
# 2. Teaches + reorients + one act (qualitative on invitation)
# ---------------------------------------------------------------------------
class TestInvitationQualitative:
    def _invitation(self, session):
        # The student-facing invitation is the latest AI turn's content.
        ai_turns = [t for t in session.get("turns", []) if t.get("role") == "ai"]
        assert ai_turns, "no AI turn"
        return ai_turns[-1].get("content", "")

    def test_invitation_teaches_concept(self, completed_session):
        inv = self._invitation(completed_session).lower()
        assert inv, "empty invitation"
        # The invitation must name/teach a canonical concept relevant to the
        # missing thesis/position in a "take a position" argument prompt.
        concept_signals = [
            "thesis",
            "position",
            "central claim",
            "claim",
            "argument",
            "argue",
            "one side",
            "which side",
            "side you're landing",
            "landing on",
            "assert",
            "stance",
        ]
        assert any(k in inv for k in concept_signals), (
            f"Invitation does not name/teach the canonical concept:\n{inv!r}"
        )

    def test_invitation_reorients_to_assignment(self, completed_session):
        """The engine must notice the 'both good and bad' drift and point back to the
        assignment (which asks for a position). Look for language about taking/choosing
        a position, or that the writing doesn't answer the prompt/take a side."""
        inv = self._invitation(completed_session).lower()
        reorienting_signals = [
            "take a position",
            "taking a position",
            "your position",
            "single position",
            "one position",
            " position",  # generic "position" mention
            "pick a side",
            "choose a side",
            "one side",
            "which side",
            "both sides",
            "sits on both",
            "landing anywhere",
            "decide",
            "commit to",
            "answer the",
            "the prompt",
            "the assignment",
            "the question",
            "both good and bad",
            "both harms and helps",
            "mostly help",
            "mostly harm",
            "doesn't answer",
            "does not answer",
            "doesn't take",
            "does not take",
            "haven't taken",
            "have not taken",
            "no clear",
            "no position",
            "without landing",
        ]
        assert any(sig in inv for sig in reorienting_signals), (
            f"Invitation does not reorient to the assignment / no-position issue:\n{inv!r}"
        )

    def test_invitation_asks_for_one_act(self, completed_session):
        inv = self._invitation(completed_session)
        assert inv.strip(), "empty invitation"
        # A single next act should be present — accept either an imperative sentence
        # or a directive question ("write ...", "decide ...", "revise ...", "choose ...").
        act_signals = [
            "write ",
            "revise",
            "rewrite",
            "decide",
            "choose",
            "pick",
            "state",
            "commit",
            "identify",
            "draft",
            "try ",
        ]
        low = inv.lower()
        assert any(sig in low for sig in act_signals), (
            f"Invitation does not appear to ask the student to perform one act:\n{inv!r}"
        )

    def test_invitation_does_not_rewrite_thesis(self, completed_session):
        """M5A anti-coauthoring — the invitation must not supply a finished thesis
        the student could copy. We check the AI didn't quote a full 'social media
        improves/harms teen friendships because ...' style thesis."""
        inv = self._invitation(completed_session).lower()
        # Heuristic: forbid patterns that read as the AI supplying a finished thesis
        # like "your thesis could be: <full sentence>" or "for example: social media harms ..."
        forbidden = [
            "here's a thesis",
            "here is a thesis",
            "your thesis should be",
            "your thesis is",
            "try this thesis:",
            "for example, your thesis",
        ]
        for f in forbidden:
            assert f not in inv, f"Invitation appears to co-author a thesis ({f!r}):\n{inv!r}"


# ---------------------------------------------------------------------------
# 3. Regression: one-target + integration_calibration + no 500
# ---------------------------------------------------------------------------
class TestRegression:
    def test_scaffolding_primary_target_present_single(self, completed_session):
        sc = completed_session["theory"]["scaffolding_control"]
        pt = (sc.get("primary_target") or "").strip()
        assert pt, f"scaffolding_control.primary_target empty: {sc}"

    def test_integration_calibration_applies(self, completed_session):
        ic = completed_session["theory"]["integration_calibration"]
        assert ic.get("applies") is True, f"integration_calibration.applies={ic.get('applies')}"

    def test_no_500s_and_status_complete(self, completed_session):
        ai_turns = [t for t in completed_session.get("turns", []) if t.get("role") == "ai"]
        assert ai_turns[-1]["status"] == "complete"

    def test_assignment_prompt_persisted(self, completed_session):
        assert completed_session.get("assignment_prompt") == ASSIGNMENT_PROMPT
