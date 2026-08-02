"""Milestone 5 backend regression: Developmental Instruction Layer + RESTRAINT rule.

Verifies:
- Every interaction returned by /interact carries an `intervention` object with a
  valid `type` (one of interpretation_only | instruct_then_invite | invite_only |
  consolidate | postpone_instruction) and a `cultural_resource` field.
- RESTRAINT: a bare topic-announcement thesis ("My essay is about X and Y.")
  triggers `instruct_then_invite` (instruction still fires when genuinely
  needed).
- RESTRAINT: an already-arguable, sophisticated thesis is NOT over-instructed —
  intervention.type is `invite_only` or `interpretation_only`.
- After a real revision, theory_history grows (prior version preserved) and can
  produce a `consolidate` intervention.
- Multi-turn reliability: 3 sequential interact calls all complete under the
  streaming edge cap without 502/timeout.
- AI never rewrites the student text and never emits stage/grade/level language.
- PATCH /api/sessions/{id}/telos updates the pedagogical purpose.

Run:  pytest /app/backend/tests/test_milestone5_instruction_layer.py -v -n 0
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

VALID_INTERVENTION_TYPES = {
    "interpretation_only",
    "instruct_then_invite",
    "invite_only",
    "consolidate",
    "postpone_instruction",
}
RESTRAINT_OK = {"invite_only", "interpretation_only", "postpone_instruction"}

STAGE_SCORE_PATTERNS = [
    r"\bstage\s*\d\b", r"\blevel\s*\d\b", r"\bgrade\s*\d\b",
    r"\b\d+\s*/\s*10\b", r"\b\d+\s*out\s*of\s*10\b",
    r"\bscore[sd]?\b\s*\d", r"\brubric\b",
    r"\btrait\s*score\b", r"\bdevelopmental\s*stage\s*\d\b",
]


def _has_stage_score(text: str) -> bool:
    low = text.lower()
    return any(re.search(p, low) for p in STAGE_SCORE_PATTERNS)


def sse_interact(client, sid, payload, timeout=180):
    started = time.time()
    with client.post(
        f"{API}/sessions/{sid}/interact",
        json=payload, stream=True, timeout=timeout,
        headers={"Accept": "text/event-stream"},
    ) as r:
        if r.status_code != 200:
            return r.status_code, None, r.text
        buf, done_payload, err_detail = "", None, None
        for chunk in r.iter_content(chunk_size=None, decode_unicode=True):
            if chunk is None:
                continue
            buf += chunk
            while "\n\n" in buf:
                raw, buf = buf.split("\n\n", 1)
                ev, data_lines = "message", []
                for line in raw.split("\n"):
                    if not line or line.startswith(":"):
                        continue
                    if line.startswith("event:"):
                        ev = line[len("event:"):].strip()
                    elif line.startswith("data:"):
                        data_lines.append(line[len("data:"):].strip())
                data = "".join(data_lines)
                if ev == "done" and data:
                    done_payload = json.loads(data)
                elif ev == "error" and data:
                    try:
                        err_detail = json.loads(data).get("detail")
                    except Exception:
                        err_detail = data
            if done_payload is not None or err_detail is not None:
                break
        if done_payload is not None:
            done_payload["_elapsed_seconds"] = time.time() - started
        return r.status_code, done_payload, err_detail


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _new_session(client, purpose, task, assignment=None):
    payload = {
        "assignment": assignment or "TEST_M5 Argue whether social media improves or harms teen friendships.",
        "pedagogical_purpose": purpose,
        "current_writing_task": task,
        "teacher_notes": "",
    }
    r = client.post(f"{API}/sessions", json=payload, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["id"]


THESIS_PURPOSE = "Help the student form and clarify a central claim that organizes the essay."
THESIS_TASK = "Draft your thesis."


# ---------------------------------------------------------------------------
# 1. Intervention object shape on every turn
# ---------------------------------------------------------------------------
class TestInterventionShape:
    def test_intervention_has_valid_type_and_cultural_resource_field(self, client):
        sid = _new_session(client, THESIS_PURPOSE, THESIS_TASK)
        status, data, err = sse_interact(
            client, sid,
            {"kind": "writing",
             "content": "Social media is a big part of teen life today and it affects friendships in many ways."},
        )
        assert status == 200 and err is None and data is not None, f"err={err}"
        ir = data["interactions"][-1]
        iv = ir["intervention"]
        # required keys
        for k in ["type", "interpretation", "instruction", "consolidation",
                  "cultural_resource", "timing_rationale"]:
            assert k in iv, f"intervention missing key {k}: {iv}"
        assert iv["type"] in VALID_INTERVENTION_TYPES, (
            f"intervention.type={iv['type']!r} not in {VALID_INTERVENTION_TYPES}"
        )
        # cultural_resource must be a string field (may be empty for
        # interpretation_only / invite_only)
        assert isinstance(iv["cultural_resource"], str)


# ---------------------------------------------------------------------------
# 2. RESTRAINT — bare topic-announcement thesis SHOULD instruct
# ---------------------------------------------------------------------------
class TestInstructionFiresWhenNeeded:
    def test_bare_topic_announcement_thesis_gets_instruct_then_invite(self, client):
        sid = _new_session(client, THESIS_PURPOSE, THESIS_TASK)
        status, data, err = sse_interact(
            client, sid,
            {"kind": "writing",
             "content": "My essay is about social media and friendship."},
        )
        assert status == 200 and err is None and data is not None, f"err={err}"
        iv = data["interactions"][-1]["intervention"]
        # Instruction should still fire when the student's move is a bare
        # topic announcement (not yet doing what the cultural resource makes
        # possible).
        assert iv["type"] == "instruct_then_invite", (
            f"bare topic-announcement thesis should trigger instruct_then_invite, "
            f"got {iv['type']!r}. cultural_resource={iv.get('cultural_resource')!r}"
        )
        # When instructing, the instruction field should be non-empty and a
        # cultural_resource should be named.
        assert iv["instruction"].strip() != "", (
            "instruct_then_invite must include a non-empty instruction field"
        )
        assert iv["cultural_resource"].strip() != "", (
            "instruct_then_invite must name a cultural_resource"
        )
        # AI still emits ONE student-facing invitation, not a rewritten thesis
        student_facing = data["turns"][-1]["content"]
        assert student_facing.strip()
        assert not _has_stage_score(student_facing)


# ---------------------------------------------------------------------------
# 3. RESTRAINT — sophisticated already-arguable thesis should NOT over-instruct
# ---------------------------------------------------------------------------
class TestRestraintOnCapableStudent:
    def test_sophisticated_thesis_avoids_over_instruction(self, client):
        sid = _new_session(client, THESIS_PURPOSE, THESIS_TASK)
        sophisticated = (
            "Social media strengthens weak-tie friendships while quietly "
            "eroding the close ones, because it rewards breadth over depth."
        )
        status, data, err = sse_interact(
            client, sid,
            {"kind": "writing", "content": sophisticated},
        )
        assert status == 200 and err is None and data is not None, f"err={err}"
        iv = data["interactions"][-1]["intervention"]
        assert iv["type"] in RESTRAINT_OK, (
            f"capable student with an already-arguable thesis should NOT "
            f"trigger instruct_then_invite (restraint rule). "
            f"got type={iv['type']!r} instruction={iv['instruction']!r}"
        )
        # AI must not rewrite the student's thesis
        student_facing = data["turns"][-1]["content"]
        assert sophisticated not in student_facing, (
            "AI appears to have echoed/rewritten the student's thesis"
        )
        assert not _has_stage_score(student_facing)
        # Domain-independent contract still holds
        rel = data["theory"]["currently_relevant_domains"]
        assert isinstance(rel, list) and 1 <= len(rel) <= 3


# ---------------------------------------------------------------------------
# 4. Multi-turn reliability + theory_history preservation + revise -> consolidate possible
# ---------------------------------------------------------------------------
class TestMultiTurnAndConsolidate:
    def test_three_turns_all_under_edge_cap_and_history_preserved(self, client):
        sid = _new_session(client, THESIS_PURPOSE, THESIS_TASK)

        # Turn 1: bare topic thesis
        s1, d1, e1 = sse_interact(client, sid, {
            "kind": "writing",
            "content": "My essay is about social media and friendship.",
        })
        assert s1 == 200 and e1 is None and d1 is not None
        assert d1["_elapsed_seconds"] < 90, f"turn 1 took {d1['_elapsed_seconds']:.1f}s"
        v1_domains = list(d1["theory"]["currently_relevant_domains"])
        iv1 = d1["interactions"][-1]["intervention"]
        assert iv1["type"] in VALID_INTERVENTION_TYPES

        # Turn 2: real revision — arguable thesis
        revised = (
            "Social media strengthens weak-tie friendships while quietly "
            "eroding the close ones, because it rewards breadth over depth."
        )
        s2, d2, e2 = sse_interact(client, sid, {"kind": "revise", "content": revised})
        assert s2 == 200 and e2 is None and d2 is not None
        assert d2["_elapsed_seconds"] < 90, f"turn 2 took {d2['_elapsed_seconds']:.1f}s"

        # theory_history grew: v1 preserved (with v1_domains), v2 = state
        # BEFORE turn 2 applied its update, so v2 preserves turn-1 theory.
        assert len(d2["theory_history"]) == 2
        assert d2["theory_history"][0]["version"] == 1
        assert d2["theory_history"][1]["version"] == 2
        # prior versions preserved, not overwritten:
        assert d2["theory_history"][0]["theory"]["currently_relevant_domains"] == [], (
            "v1 should be the empty initial theory (snapshot pre-turn-1)"
        )
        assert list(d2["theory_history"][1]["theory"]["currently_relevant_domains"]) == v1_domains, (
            "v2 should preserve turn-1 domains (snapshot pre-turn-2)"
        )

        iv2 = d2["interactions"][-1]["intervention"]
        assert iv2["type"] in VALID_INTERVENTION_TYPES
        # AI never rewrites revised text
        student_facing_2 = d2["turns"][-1]["content"]
        assert revised not in student_facing_2

        # Turn 3: student answer explaining the revision
        s3, d3, e3 = sse_interact(client, sid, {
            "kind": "answer",
            "content": (
                "I split the effect by relationship type — weak ties benefit "
                "because breadth is what they need, close ties suffer because "
                "depth is what they need and social media doesn't supply it."
            ),
        })
        assert s3 == 200 and e3 is None and d3 is not None
        assert d3["_elapsed_seconds"] < 90, f"turn 3 took {d3['_elapsed_seconds']:.1f}s"
        assert len(d3["theory_history"]) == 3
        assert [s["version"] for s in d3["theory_history"]] == [1, 2, 3]
        iv3 = d3["interactions"][-1]["intervention"]
        assert iv3["type"] in VALID_INTERVENTION_TYPES

        # After a real revision + articulation, `consolidate` is a legitimate
        # option (Milestone 5 acceptance says the flow CAN produce it — not
        # must). Just record for the report; do not hard-fail if the model
        # chose invite_only or interpretation_only instead.
        types_seen = [iv1["type"], iv2["type"], iv3["type"]]
        print(f"INTERVENTION_TYPES over 3 turns: {types_seen}")

        # Domains should be drawn from the canonical model on every turn
        for d in (d1, d2, d3):
            rel = d["theory"]["currently_relevant_domains"]
            assert 1 <= len(rel) <= 3

        # No stage/score language anywhere
        for d in (d1, d2, d3):
            assert not _has_stage_score(d["turns"][-1]["content"])
            assert not _has_stage_score(json.dumps(d["theory"]))
            assert not _has_stage_score(json.dumps(d["interactions"]))


# ---------------------------------------------------------------------------
# 5. PATCH /api/sessions/{id}/telos
# ---------------------------------------------------------------------------
class TestTelosPatch:
    def test_patch_telos_updates_pedagogical_purpose(self, client):
        sid = _new_session(client, THESIS_PURPOSE, THESIS_TASK)
        new_purpose = (
            "Help the student make the thesis do argumentative work rather "
            "than announce a topic."
        )
        r = client.patch(
            f"{API}/sessions/{sid}/telos",
            json={"pedagogical_purpose": new_purpose,
                  "note": "TEST_M5 narrowing purpose"},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["pedagogical_purpose"] == new_purpose
        assert data["telos"]["governing_pedagogical_purpose"] == new_purpose
        assert data["telos"]["telos_changed"].strip() != ""

        # Persistence check
        g = client.get(f"{API}/sessions/{sid}", timeout=15)
        assert g.status_code == 200
        assert g.json()["telos"]["governing_pedagogical_purpose"] == new_purpose
