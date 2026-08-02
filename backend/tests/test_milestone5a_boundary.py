"""Milestone 5A backend acceptance: Writing Instruction Boundary & Anti-Coauthoring.

Verifies the 5A prompt-tightening changes to /app/backend/server.py:
- Intervention model now carries `focus` ('writing'|'content') and
  `writing_not_content_check` self-check fields.
- For an ordinary argumentative draft (no brainstorming permission), the AI's
  focus is 'writing' and writing_not_content_check is non-empty.
- Anti-coauthoring: for a three-reason argumentative thesis, the student-facing
  invitation must teach a WRITING function (thesis controlling-idea/function)
  and must NOT contain content-coaching phrasing (e.g. "what's at stake",
  "another reason", "you could add", etc.).
- Brainstorming exception: when teacher_notes explicitly enables brainstorming,
  intervention.focus may be 'content' (AI helps generate ideas while leaving
  substantive ownership with the student).
- Regression M1-M5: session CRUD (create + GET + PATCH telos), SSE streaming
  ending in `event: done` with full session JSON, exactly ONE student-facing
  turn per /interact, AI never rewrites the student's text, no stage/grade/
  score language, multi-turn writing->revise->answer with theory_history v1..vN
  preserved and currently_relevant_domains staying in 1..3, all turns under the
  streaming edge cap.

Run:  pytest /app/backend/tests/test_milestone5a_boundary.py -v -n 0
"""
import json
import os
import re
import time
from pathlib import Path

import pytest
import requests


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
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

STAGE_SCORE_PATTERNS = [
    r"\bstage\s*\d\b", r"\blevel\s*\d\b", r"\bgrade\s*\d\b",
    r"\b\d+\s*/\s*10\b", r"\b\d+\s*out\s*of\s*10\b",
    r"\bscore[sd]?\b\s*\d", r"\brubric\b",
    r"\btrait\s*score\b", r"\bdevelopmental\s*stage\s*\d\b",
]

# Content-coaching red flags: phrasing that PRESUPPOSES an idea the essay
# ought to contain rather than teaching a writing function.
CONTENT_REDFLAGS = [
    r"what(?:'s| is| are)?\s+(?:really\s+)?at stake",
    r"have you considered (?:adding|mentioning|including)",
    r"you (?:could|might|should) add",
    r"you (?:could|might|should) (?:mention|include|bring in|talk about)",
    r"another (?:reason|argument|example|point|perspective)",
    r"a (?:stronger|better|more compelling) (?:argument|reason|claim|example)",
    r"what would make your (?:argument|essay|point|claim) stronger",
    r"consider (?:adding|including|mentioning)",
    r"for example,? you could",
    r"what (?:other|else|more) (?:evidence|reasons|examples|arguments)",
    r"you may want to include",
    r"try adding",
    r"think about (?:adding|including)",
    r"one more (?:reason|point|example)",
]
CONTENT_REDFLAG_RES = [re.compile(p, re.IGNORECASE) for p in CONTENT_REDFLAGS]


def _has_stage_score(text: str) -> bool:
    low = text.lower()
    return any(re.search(p, low) for p in STAGE_SCORE_PATTERNS)


def _content_flags(text: str):
    return [p.pattern for p in CONTENT_REDFLAG_RES if p.search(text)]


# ---------------------------------------------------------------------------
# SSE client
# ---------------------------------------------------------------------------
def sse_interact(client, sid, payload, timeout=180):
    """POST /api/sessions/{sid}/interact and parse the SSE stream.

    Returns (status_code, full_session_dict_or_None, error_detail_or_None).
    The final `event: done` frame carries the full updated session JSON.
    """
    started = time.time()
    with client.post(
        f"{API}/sessions/{sid}/interact",
        json=payload, stream=True, timeout=timeout,
        headers={"Accept": "text/event-stream"},
    ) as r:
        if r.status_code != 200:
            return r.status_code, None, r.text
        buf, done_payload, err_detail, saw_done_event = "", None, None, False
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
                if ev == "done":
                    saw_done_event = True
                    if data:
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
            done_payload["_saw_done_event"] = saw_done_event
        return r.status_code, done_payload, err_detail


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


ARG_ASSIGNMENT = "TEST_M5A Argue whether social media improves or harms teen friendships."
THESIS_PURPOSE = "Help the student form and clarify a central claim that organizes the essay."
THESIS_TASK = "Draft your thesis."


def _new_session(client, purpose=THESIS_PURPOSE, task=THESIS_TASK,
                 assignment=ARG_ASSIGNMENT, teacher_notes=""):
    payload = {
        "assignment": assignment,
        "pedagogical_purpose": purpose,
        "current_writing_task": task,
        "teacher_notes": teacher_notes,
    }
    r = client.post(f"{API}/sessions", json=payload, timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "id" in body and body["id"]
    return body["id"]


def _last_intervention(session_json):
    return session_json["interactions"][-1]["intervention"]


def _last_student_facing(session_json):
    return session_json["turns"][-1]["content"]


# ===========================================================================
# 1. Session CRUD — create returns id, GET returns persisted session
# ===========================================================================
class TestSessionCrud:
    def test_create_and_get_session(self, client):
        sid = _new_session(client)
        g = client.get(f"{API}/sessions/{sid}", timeout=15)
        assert g.status_code == 200
        body = g.json()
        assert body["id"] == sid
        assert body["assignment"] == ARG_ASSIGNMENT
        assert body["pedagogical_purpose"] == THESIS_PURPOSE
        assert body["current_writing_task"] == THESIS_TASK
        # telos initialized from creation payload
        assert body["telos"]["governing_pedagogical_purpose"] == THESIS_PURPOSE
        assert body["telos"]["assignment_context"] == ARG_ASSIGNMENT

    def test_get_nonexistent_session_returns_404(self, client):
        r = client.get(f"{API}/sessions/does-not-exist-{int(time.time())}", timeout=15)
        assert r.status_code == 404


# ===========================================================================
# 2. SSE contract + intervention.focus + writing_not_content_check
#    (normal argumentative draft, no brainstorming permission)
# ===========================================================================
class TestSSEAndInterventionFields:
    def test_writing_turn_streams_done_with_focus_writing(self, client):
        sid = _new_session(client)
        weak_thesis = "My essay is about social media and friendship."
        status, data, err = sse_interact(
            client, sid,
            {"kind": "writing", "content": weak_thesis},
        )
        assert status == 200, f"HTTP {status}"
        assert err is None, f"stream error: {err}"
        assert data is not None, "no `event: done` payload received"
        assert data.get("_saw_done_event") is True
        assert data.get("_elapsed_seconds", 999) < 120

        # Exactly ONE ai turn appended for this /interact (student + ai)
        ai_turns = [t for t in data["turns"] if t["role"] == "ai"]
        assert len(ai_turns) == 1, f"expected exactly ONE ai turn, got {len(ai_turns)}"
        student_turns = [t for t in data["turns"] if t["role"] == "student"]
        assert len(student_turns) == 1

        # AI never rewrites the student's text
        student_facing = _last_student_facing(data)
        assert weak_thesis not in student_facing, (
            "AI appears to have echoed/rewritten the student's thesis"
        )
        assert not _has_stage_score(student_facing), (
            f"stage/grade/level language leaked: {student_facing[:200]}"
        )
        # AI turn is a single invitation, not a lecture (soft bound)
        assert len(student_facing.split()) < 250, (
            f"AI response too long ({len(student_facing.split())} words), "
            f"may indicate rewriting/lecturing"
        )

        # Intervention: valid type + Milestone 5A fields present
        iv = _last_intervention(data)
        assert iv["type"] in VALID_INTERVENTION_TYPES, (
            f"invalid intervention.type={iv.get('type')!r}"
        )
        # Milestone 5A: focus field must be present and default to 'writing'
        assert "focus" in iv, f"intervention missing `focus` field: {iv}"
        assert iv["focus"] == "writing", (
            f"expected focus='writing' for a normal argumentative draft "
            f"(no brainstorming permission), got {iv['focus']!r}"
        )
        # Milestone 5A: writing_not_content_check must be present and non-empty
        assert "writing_not_content_check" in iv, (
            f"intervention missing `writing_not_content_check`: {iv}"
        )
        assert iv["writing_not_content_check"].strip() != "", (
            "writing_not_content_check must be a non-empty self-check string"
        )


# ===========================================================================
# 3. Anti-coauthoring: three-reason argumentative thesis
# ===========================================================================
class TestAntiCoauthoring:
    def test_three_reason_thesis_teaches_writing_not_content(self, client):
        sid = _new_session(client)
        three_reason = (
            "Social media harms teen friendships because it is distracting, "
            "because it is fake, and because it is addictive."
        )
        status, data, err = sse_interact(
            client, sid,
            {"kind": "writing", "content": three_reason},
        )
        assert status == 200 and err is None and data is not None, f"err={err}"

        iv = _last_intervention(data)
        student_facing = _last_student_facing(data)

        # Focus must remain 'writing' — no teacher brainstorming permission
        assert iv["focus"] == "writing", (
            f"three-reason thesis (no brainstorming) must stay focus='writing', "
            f"got {iv['focus']!r}. student_facing={student_facing!r}"
        )
        # writing_not_content_check must be a non-empty self-check
        assert iv["writing_not_content_check"].strip() != ""

        # Anti-coauthoring: no content-coaching red-flag phrasing
        flags = _content_flags(student_facing)
        assert not flags, (
            f"anti-coauthoring VIOLATION — student_facing contains content-"
            f"coaching phrasing {flags}. student_facing={student_facing!r}"
        )
        # AI must not rewrite the student's thesis
        assert three_reason not in student_facing
        assert not _has_stage_score(student_facing)

        # Sanity: student-facing invitation should reference thesis/claim/
        # argument as a WRITING function (weak but useful smoke check).
        low = student_facing.lower()
        teaches_writing_function = any(
            kw in low for kw in (
                "thesis", "claim", "argument", "reader", "reason",
                "position", "central idea", "controlling idea",
                "paragraph", "essay", "purpose", "function",
            )
        )
        assert teaches_writing_function, (
            f"invitation does not appear to teach a writing function: "
            f"{student_facing!r}"
        )


# ===========================================================================
# 4. Brainstorming exception — teacher explicitly enables idea generation
# ===========================================================================
class TestBrainstormingException:
    def test_brainstorming_permission_allows_content_focus(self, client):
        sid = _new_session(
            client,
            teacher_notes=(
                "Brainstorming mode is ON: help the student generate and "
                "explore possible ideas before drafting."
            ),
        )
        status, data, err = sse_interact(
            client, sid,
            {"kind": "writing",
             "content": "I don't know what to argue about social media and friendships yet."},
        )
        assert status == 200 and err is None and data is not None, f"err={err}"
        iv = _last_intervention(data)
        # Brainstorming permission means focus MAY be 'content' (but 'writing'
        # is still acceptable if the AI decided instruction-first was apt).
        # The test asserts the field exists and is one of the two valid values.
        assert iv["focus"] in {"writing", "content"}, (
            f"invalid focus={iv['focus']!r}"
        )
        # Milestone 5A output field always present
        assert iv["writing_not_content_check"].strip() != ""

        # AI does not rewrite / grade / stage
        student_facing = _last_student_facing(data)
        assert not _has_stage_score(student_facing)
        # AI keeps ownership: the student's own experience should be invoked
        # rather than the AI naming ideas for them. This is a soft check on
        # the presence of student-ownership language OR content-generation
        # framing — both are acceptable under brainstorming.
        assert student_facing.strip() != ""


# ===========================================================================
# 5. Regression M1-M5: multi-turn writing -> revise -> answer + telos patch
# ===========================================================================
class TestMultiTurnRegression:
    def test_three_turns_history_and_domains(self, client):
        sid = _new_session(client)

        # Turn 1: weak thesis
        s1, d1, e1 = sse_interact(client, sid, {
            "kind": "writing",
            "content": "My essay is about social media and friendship.",
        })
        assert s1 == 200 and e1 is None and d1 is not None
        assert d1["_elapsed_seconds"] < 120, f"turn1 {d1['_elapsed_seconds']:.1f}s"

        iv1 = _last_intervention(d1)
        assert iv1["type"] in VALID_INTERVENTION_TYPES
        assert iv1["focus"] == "writing"
        assert iv1["writing_not_content_check"].strip() != ""
        rel1 = d1["theory"]["currently_relevant_domains"]
        assert 1 <= len(rel1) <= 3

        # Turn 2: real revision
        revised = (
            "Social media strengthens weak-tie friendships while quietly "
            "eroding the close ones, because it rewards breadth over depth."
        )
        s2, d2, e2 = sse_interact(client, sid, {"kind": "revise", "content": revised})
        assert s2 == 200 and e2 is None and d2 is not None
        assert d2["_elapsed_seconds"] < 120, f"turn2 {d2['_elapsed_seconds']:.1f}s"

        # theory_history: v1..v2 present, prior versions preserved
        assert len(d2["theory_history"]) == 2
        versions_2 = [snap["version"] for snap in d2["theory_history"]]
        assert versions_2 == [1, 2]
        # v1 is pre-turn-1 initial theory (empty domains)
        assert d2["theory_history"][0]["theory"]["currently_relevant_domains"] == []
        # v2 preserves the turn-1 domains (snapshot pre-turn-2)
        assert list(d2["theory_history"][1]["theory"]["currently_relevant_domains"]) == rel1

        iv2 = _last_intervention(d2)
        assert iv2["type"] in VALID_INTERVENTION_TYPES
        assert iv2["focus"] == "writing"
        assert iv2["writing_not_content_check"].strip() != ""
        # AI does not rewrite the revised text
        assert revised not in _last_student_facing(d2)
        rel2 = d2["theory"]["currently_relevant_domains"]
        assert 1 <= len(rel2) <= 3

        # Turn 3: student answer (explains the revision) — consolidate is a
        # legitimate option here but NOT required.
        s3, d3, e3 = sse_interact(client, sid, {
            "kind": "answer",
            "content": (
                "I split the effect by relationship type — weak ties benefit "
                "from breadth, close ones need depth that social media does "
                "not supply."
            ),
        })
        assert s3 == 200 and e3 is None and d3 is not None
        assert d3["_elapsed_seconds"] < 120, f"turn3 {d3['_elapsed_seconds']:.1f}s"
        assert len(d3["theory_history"]) == 3
        assert [snap["version"] for snap in d3["theory_history"]] == [1, 2, 3]
        # prior versions must be preserved (not overwritten by later state)
        assert d3["theory_history"][0]["theory"]["currently_relevant_domains"] == []
        assert list(d3["theory_history"][1]["theory"]["currently_relevant_domains"]) == rel1
        assert list(d3["theory_history"][2]["theory"]["currently_relevant_domains"]) == rel2

        iv3 = _last_intervention(d3)
        assert iv3["type"] in VALID_INTERVENTION_TYPES
        assert iv3["focus"] in {"writing", "content"}
        assert iv3["writing_not_content_check"].strip() != ""

        # Domains shifted appropriately and no stage/score language leaked
        for d in (d1, d2, d3):
            assert 1 <= len(d["theory"]["currently_relevant_domains"]) <= 3
            assert not _has_stage_score(_last_student_facing(d))
            assert not _has_stage_score(json.dumps(d["interactions"]))

        # Record intervention type trajectory for the report
        print(
            "M5A INTERVENTION TYPES: "
            f"t1={iv1['type']} t2={iv2['type']} t3={iv3['type']} | "
            f"FOCUS: t1={iv1['focus']} t2={iv2['focus']} t3={iv3['focus']}"
        )

    def test_patch_telos_updates_pedagogical_purpose(self, client):
        sid = _new_session(client)
        new_purpose = (
            "Help the student make the thesis do argumentative work rather "
            "than announce a topic."
        )
        r = client.patch(
            f"{API}/sessions/{sid}/telos",
            json={"pedagogical_purpose": new_purpose,
                  "note": "TEST_M5A narrowing purpose"},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["pedagogical_purpose"] == new_purpose
        assert body["telos"]["governing_pedagogical_purpose"] == new_purpose
        assert body["telos"]["telos_changed"].strip() != ""
        # Persistence check
        g = client.get(f"{API}/sessions/{sid}", timeout=15)
        assert g.status_code == 200
        assert g.json()["telos"]["governing_pedagogical_purpose"] == new_purpose
