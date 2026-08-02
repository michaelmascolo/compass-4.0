"""Milestone 6 backend acceptance — Communicative Purpose Framework.

Verifies that the AI, BEFORE evaluating any writing, infers the writing's
communicative PURPOSE (persuade / inform / explain / interpret / analyze /
narrate / reflect / evaluate / compare / propose — communicative functions,
NOT rigid genres) and records it in theory.communicative_purpose
(primary + secondary + inferred_from + uncertainty).

Coverage:
- theory.communicative_purpose.primary is populated with a plausible purpose
  matching the writing's actual function across:
    * persuasive assignment  -> 'persuade' / 'argue'
    * explanatory assignment -> 'explain'
    * narrative assignment   -> 'narrate'
    * analytical assignment  -> 'analyze' / 'interpret'
- Mixed-purpose assignment (explain + argue) yields a primary AND at least
  one secondary purpose (holds multiple purposes, does not collapse to one).
- Purpose-adaptive teaching:
    * narrative draft => invitation focuses on narrative meaning / experience
      (NOT a persuasive thesis) and contains NO rigid-template phrasing
      ('five-paragraph', 'topic sentence/evidence/analysis' formula,
      'three body paragraphs', 'hook-background-thesis').
- M5A regression: intervention.focus == 'writing' on ordinary drafts;
  intervention.writing_not_content_check is non-empty; no content-coaching
  red flags on a persuasive draft.
- M1-M5 regression (multi-turn): writing -> revise -> answer preserves
  theory_history v1..vN (prior versions not overwritten); currently_relevant
  _domains stays 1..3 every turn; no stage/grade/level language; all turns
  complete under 120s (no 502).

Run:  pytest /app/backend/tests/test_milestone6_communicative_purpose.py -v -n 0
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

# Rigid-template phrasing that should NEVER appear regardless of purpose
RIGID_TEMPLATE_PATTERNS = [
    r"five[-\s]paragraph",
    r"three body paragraph",
    r"hook[-,\s]+background[-,\s]+thesis",
    # "topic sentence + evidence + analysis" three-part formula
    r"topic sentence.*evidence.*analysis",
    r"topic sentence.*analysis.*evidence",
    r"must contain three body",
]
RIGID_TEMPLATE_RES = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in RIGID_TEMPLATE_PATTERNS]

# Content-coaching red flags (M5A anti-coauthoring guard)
CONTENT_REDFLAGS = [
    r"what(?:'s| is| are)?\s+(?:really\s+)?at stake",
    r"have you considered (?:adding|mentioning|including)",
    r"you (?:could|might|should) add",
    r"you (?:could|might|should) (?:mention|include|bring in)",
    r"another (?:reason|argument|example|point)",
    r"a (?:stronger|better|more compelling) (?:argument|reason|claim)",
    r"what would make your (?:argument|essay|point|claim) stronger",
    r"consider (?:adding|including|mentioning)",
    r"for example,? you could",
    r"you may want to include",
    r"try adding",
    r"think about (?:adding|including)",
    r"one more (?:reason|point|example)",
]
CONTENT_REDFLAG_RES = [re.compile(p, re.IGNORECASE) for p in CONTENT_REDFLAGS]


def _has_stage_score(text: str) -> bool:
    low = text.lower()
    return any(re.search(p, low) for p in STAGE_SCORE_PATTERNS)


def _rigid_template_flags(text: str):
    return [p.pattern for p in RIGID_TEMPLATE_RES if p.search(text)]


def _content_flags(text: str):
    return [p.pattern for p in CONTENT_REDFLAG_RES if p.search(text)]


# ---------------------------------------------------------------------------
# SSE client (identical pattern to test_milestone5a_boundary.py)
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


def sse_interact_with_retry(client, sid, payload, timeout=180):
    """Run sse_interact with a single retry on empty-stream flakiness."""
    status, data, err = sse_interact(client, sid, payload, timeout)
    if status == 200 and data is None and err is None:
        # Rare stream-boundary flake — retry once
        time.sleep(2)
        status, data, err = sse_interact(client, sid, payload, timeout)
    return status, data, err


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _new_session(client, assignment, purpose, task, teacher_notes=""):
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


def _last_intervention(s):
    return s["interactions"][-1]["intervention"]


def _last_student_facing(s):
    return s["turns"][-1]["content"]


def _cp(s):
    return s["theory"]["communicative_purpose"]


def _primary_lower(s):
    return (_cp(s).get("primary") or "").lower()


def _all_purpose_text_lower(s):
    """All purpose-related text (primary + secondary) as lowercase blob."""
    cp = _cp(s)
    parts = [cp.get("primary", "")]
    parts.extend(cp.get("secondary") or [])
    return " ".join(parts).lower()


def _assert_common_shape(s, weak_text=None):
    """Common assertions applied to every /interact response in this suite."""
    assert s.get("_saw_done_event") is True
    assert s.get("_elapsed_seconds", 999) < 120

    # Per /interact: last turn is ai; ai_count == student_count == interactions_count
    ai = [t for t in s["turns"] if t["role"] == "ai"]
    student = [t for t in s["turns"] if t["role"] == "student"]
    assert s["turns"][-1]["role"] == "ai", "last turn must be the ai invitation"
    assert len(ai) == len(student) == len(s["interactions"]), (
        f"turn/interaction counts inconsistent: ai={len(ai)} student={len(student)} "
        f"interactions={len(s['interactions'])}"
    )

    inv = _last_student_facing(s)
    if weak_text is not None:
        assert weak_text not in inv, "AI appears to have echoed the student's text"
    assert not _has_stage_score(inv), f"stage/level/rubric leaked: {inv[:200]}"

    iv = _last_intervention(s)
    assert iv["type"] in VALID_INTERVENTION_TYPES

    # M6: communicative_purpose must be present and populated
    cp = _cp(s)
    assert "primary" in cp, f"theory.communicative_purpose missing primary: {cp}"
    assert (cp.get("primary") or "").strip() != "", (
        f"communicative_purpose.primary MUST be populated, got {cp!r}"
    )
    assert "secondary" in cp
    assert isinstance(cp["secondary"], list)
    assert "inferred_from" in cp
    return iv, inv, cp


# ===========================================================================
# 1. Communicative purpose across 4 canonical purposes
# ===========================================================================
class TestPurposeInference:
    def test_persuade_purpose_inferred(self, client):
        sid = _new_session(
            client,
            assignment="TEST_M6 Argue whether your school should require uniforms.",
            purpose="Help the student form and defend a clear position with reasons.",
            task="Draft an argumentative opening that states your position.",
        )
        draft = (
            "Schools should not require uniforms because they limit students' "
            "self-expression and do not actually improve behavior."
        )
        status, data, err = sse_interact_with_retry(
            client, sid, {"kind": "writing", "content": draft}
        )
        assert status == 200 and err is None and data is not None, f"err={err}"

        iv, inv, cp = _assert_common_shape(data, weak_text=draft)
        prim = _primary_lower(data)
        assert any(k in prim for k in ("persuad", "argu", "convinc", "advocat")), (
            f"persuasive assignment must yield persuade/argue primary, got {cp!r}"
        )
        # M5A regression on persuasive draft: focus='writing', no red flags
        assert iv["focus"] == "writing", f"focus should be 'writing', got {iv['focus']!r}"
        assert iv["writing_not_content_check"].strip() != ""
        flags = _content_flags(inv)
        assert not flags, f"content-coaching phrasing leaked: {flags} | inv={inv!r}"
        # No rigid template imposition
        tflags = _rigid_template_flags(inv)
        assert not tflags, f"rigid-template phrasing: {tflags} | inv={inv!r}"
        print(f"PERSUADE cp={cp} | focus={iv['focus']} type={iv['type']}")

    def test_explain_purpose_inferred(self, client):
        sid = _new_session(
            client,
            assignment="TEST_M6 Explain how a bill becomes a law.",
            purpose="Help the student explain a process clearly for a reader unfamiliar with it.",
            task="Draft the opening of your explanation.",
        )
        draft = (
            "A bill becomes a law by moving through several steps. First a "
            "member of Congress introduces the bill. Then it goes to committee."
        )
        status, data, err = sse_interact_with_retry(
            client, sid, {"kind": "writing", "content": draft}
        )
        assert status == 200 and err is None and data is not None, f"err={err}"

        iv, inv, cp = _assert_common_shape(data, weak_text=draft)
        prim = _primary_lower(data)
        # 'explain' or 'inform' are both defensible for a process-explanation
        assert any(k in prim for k in ("explain", "inform")), (
            f"process explanation must yield explain/inform primary, got {cp!r}"
        )
        assert iv["focus"] == "writing"
        assert iv["writing_not_content_check"].strip() != ""
        tflags = _rigid_template_flags(inv)
        assert not tflags, f"rigid-template phrasing: {tflags} | inv={inv!r}"
        print(f"EXPLAIN cp={cp} | focus={iv['focus']} type={iv['type']}")

    def test_narrate_purpose_and_no_persuasive_thesis_push(self, client):
        sid = _new_session(
            client,
            assignment="TEST_M6 Write a personal narrative about a turning point in your life.",
            purpose="Help the student shape a personal narrative that communicates the meaning of an experience.",
            task="Draft the opening of your narrative.",
        )
        draft = (
            "The first time I stood on the diving board at swim tryouts, my "
            "hands would not stop shaking. I looked down at the water and "
            "everything I thought I knew about myself felt uncertain."
        )
        status, data, err = sse_interact_with_retry(
            client, sid, {"kind": "writing", "content": draft}
        )
        assert status == 200 and err is None and data is not None, f"err={err}"

        iv, inv, cp = _assert_common_shape(data, weak_text=draft)
        prim = _primary_lower(data)
        assert any(k in prim for k in ("narrat", "story", "recount")), (
            f"narrative assignment must yield narrate primary, got {cp!r}"
        )
        assert iv["focus"] == "writing"
        assert iv["writing_not_content_check"].strip() != ""

        # Purpose-adaptive teaching: narrative invitation must NOT push a
        # persuasive thesis or claim-making apparatus.
        low = inv.lower()
        # If the invitation contains 'thesis' or 'claim' or 'argument' as
        # the primary framing, that's a purpose mismatch. Allow the word
        # if wrapped in a narrative-appropriate way — but flag pure
        # thesis/claim vocabulary pushed as the main move.
        forbidden_persuasive = [
            r"\bthesis statement\b",
            r"\bstate your (?:argument|claim|position|thesis)\b",
            r"\bmake (?:an|your) argument\b",
            r"\bmake a claim\b",
            r"\bwhat are you arguing\b",
            r"\byour argument\b",
        ]
        pushes_persuasive = [p for p in forbidden_persuasive if re.search(p, low)]
        assert not pushes_persuasive, (
            f"narrative draft got persuasive-thesis push: {pushes_persuasive} | inv={inv!r}"
        )
        tflags = _rigid_template_flags(inv)
        assert not tflags, f"rigid-template phrasing: {tflags} | inv={inv!r}"
        print(f"NARRATE cp={cp} | focus={iv['focus']} type={iv['type']}")

    def test_analyze_purpose_inferred(self, client):
        sid = _new_session(
            client,
            assignment="TEST_M6 Analyze how imagery creates mood in a poem you have read.",
            purpose="Help the student interpret how specific textual choices create meaning.",
            task="Draft your analytical opening.",
        )
        draft = (
            "In Robert Frost's 'Stopping by Woods on a Snowy Evening,' the "
            "repeated images of dark, deep, and quiet woods create a mood of "
            "solitary contemplation that pulls against the speaker's obligations."
        )
        status, data, err = sse_interact_with_retry(
            client, sid, {"kind": "writing", "content": draft}
        )
        assert status == 200 and err is None and data is not None, f"err={err}"

        iv, inv, cp = _assert_common_shape(data, weak_text=draft)
        prim = _primary_lower(data)
        assert any(k in prim for k in ("analy", "interpret")), (
            f"analytical assignment must yield analyze/interpret primary, got {cp!r}"
        )
        assert iv["focus"] == "writing"
        assert iv["writing_not_content_check"].strip() != ""
        tflags = _rigid_template_flags(inv)
        assert not tflags, f"rigid-template phrasing: {tflags} | inv={inv!r}"
        print(f"ANALYZE cp={cp} | focus={iv['focus']} type={iv['type']}")


# ===========================================================================
# 2. Mixed-purpose assignment must hold MULTIPLE purposes
# ===========================================================================
class TestMixedPurpose:
    def test_mixed_purpose_holds_multiple(self, client):
        sid = _new_session(
            client,
            assignment=(
                "TEST_M6 Explain how social media algorithms work AND argue "
                "whether they should be regulated."
            ),
            purpose="Help the student both explain a system and argue about its regulation.",
            task="Draft your opening covering both parts.",
        )
        draft = (
            "Social media algorithms rank posts based on engagement signals "
            "like clicks and dwell time. Because they concentrate attention on "
            "outrage-provoking content, they should be regulated the same way "
            "we regulate broadcast media."
        )
        status, data, err = sse_interact_with_retry(
            client, sid, {"kind": "writing", "content": draft}
        )
        assert status == 200 and err is None and data is not None, f"err={err}"

        iv, inv, cp = _assert_common_shape(data, weak_text=draft)

        prim = _primary_lower(data)
        purpose_blob = _all_purpose_text_lower(data)
        # Must reference BOTH explain-ish AND persuade-ish purpose somewhere
        has_explain = any(k in purpose_blob for k in ("explain", "inform"))
        has_argue = any(k in purpose_blob for k in ("persuad", "argu", "advocat", "propose"))
        assert has_explain and has_argue, (
            f"mixed-purpose assignment must hold BOTH explain/inform AND "
            f"persuade/argue across primary+secondary, got {cp!r}"
        )
        # Must NOT collapse to a single-purpose classification: there must be
        # at least one secondary purpose recorded.
        secondary = cp.get("secondary") or []
        assert len(secondary) >= 1, (
            f"mixed-purpose assignment must record at least one SECONDARY "
            f"purpose (does not collapse to one), got {cp!r}"
        )
        assert iv["focus"] == "writing"
        assert iv["writing_not_content_check"].strip() != ""
        tflags = _rigid_template_flags(inv)
        assert not tflags, f"rigid-template phrasing: {tflags} | inv={inv!r}"
        print(f"MIXED cp={cp}")


# ===========================================================================
# 3. Multi-turn regression: theory_history preserved, purpose stable, M5A
# ===========================================================================
class TestMultiTurnRegression:
    def test_multi_turn_writing_revise_answer(self, client):
        sid = _new_session(
            client,
            assignment="TEST_M6 Argue whether your school should require uniforms.",
            purpose="Help the student form and defend a clear position with reasons.",
            task="Draft an argumentative opening that states your position.",
        )

        # Turn 1
        d1_text = (
            "My essay is about uniforms in schools."
        )
        s1, d1, e1 = sse_interact_with_retry(
            client, sid, {"kind": "writing", "content": d1_text}
        )
        assert s1 == 200 and e1 is None and d1 is not None
        iv1, inv1, cp1 = _assert_common_shape(d1, weak_text=d1_text)
        rel1 = d1["theory"]["currently_relevant_domains"]
        assert 1 <= len(rel1) <= 3
        prim1 = _primary_lower(d1)
        assert any(k in prim1 for k in ("persuad", "argu", "convinc", "advocat")), (
            f"turn1 persuasive purpose expected, got {cp1!r}"
        )

        # Turn 2 — real revision
        revised = (
            "Schools should not require uniforms because dress choice teaches "
            "students to make daily decisions about how they present themselves "
            "to the world, and taking that away replaces judgment with obedience."
        )
        s2, d2, e2 = sse_interact_with_retry(
            client, sid, {"kind": "revise", "content": revised}
        )
        assert s2 == 200 and e2 is None and d2 is not None
        iv2, inv2, cp2 = _assert_common_shape(d2, weak_text=revised)
        # theory_history v1..v2 present, prior versions preserved
        assert len(d2["theory_history"]) == 2
        assert [snap["version"] for snap in d2["theory_history"]] == [1, 2]
        # v1 was pre-turn-1: empty domains
        assert d2["theory_history"][0]["theory"]["currently_relevant_domains"] == []
        # v2 preserves the turn-1 domains
        assert list(d2["theory_history"][1]["theory"]["currently_relevant_domains"]) == rel1
        rel2 = d2["theory"]["currently_relevant_domains"]
        assert 1 <= len(rel2) <= 3
        # Purpose remains persuasive (or persuade + secondary)
        prim2 = _primary_lower(d2)
        assert any(k in prim2 for k in ("persuad", "argu", "convinc", "advocat")), (
            f"turn2 persuasive purpose expected, got {cp2!r}"
        )

        # Turn 3 — student answer
        s3, d3, e3 = sse_interact_with_retry(
            client, sid, {"kind": "answer",
                          "content": "I focused on why dress choice is itself a skill worth practicing."},
        )
        assert s3 == 200 and e3 is None and d3 is not None
        iv3, inv3, cp3 = _assert_common_shape(d3)
        assert len(d3["theory_history"]) == 3
        assert [snap["version"] for snap in d3["theory_history"]] == [1, 2, 3]
        assert d3["theory_history"][0]["theory"]["currently_relevant_domains"] == []
        assert list(d3["theory_history"][1]["theory"]["currently_relevant_domains"]) == rel1
        assert list(d3["theory_history"][2]["theory"]["currently_relevant_domains"]) == rel2

        # No stage/rubric leaks anywhere across all three turns
        for d in (d1, d2, d3):
            assert not _has_stage_score(_last_student_facing(d))
            assert not _has_stage_score(json.dumps(d["interactions"]))
            assert 1 <= len(d["theory"]["currently_relevant_domains"]) <= 3

        # All turns had focus='writing' + writing_not_content_check populated
        for i, iv in enumerate((iv1, iv2, iv3), start=1):
            assert iv["focus"] == "writing", (
                f"turn {i} focus must remain 'writing' (no brainstorming), got {iv['focus']!r}"
            )
            assert iv["writing_not_content_check"].strip() != ""

        # Domains selected are sensible; log for the report
        print(
            f"M6 MULTITURN t1={iv1['type']}/{iv1['focus']} "
            f"t2={iv2['type']}/{iv2['focus']} "
            f"t3={iv3['type']}/{iv3['focus']} "
            f"| primary t1={cp1.get('primary')!r} t2={cp2.get('primary')!r} t3={cp3.get('primary')!r} "
            f"| rel1={rel1} rel2={rel2}"
        )


# ===========================================================================
# 4. Fast smoke: session CRUD + PATCH telos still work
# ===========================================================================
class TestSessionCrud:
    def test_create_get_patch(self, client):
        sid = _new_session(
            client,
            assignment="TEST_M6 crud smoke",
            purpose="Help the student form and clarify a claim.",
            task="Draft your thesis.",
        )
        g = client.get(f"{API}/sessions/{sid}", timeout=15)
        assert g.status_code == 200
        assert g.json()["id"] == sid

        r = client.patch(
            f"{API}/sessions/{sid}/telos",
            json={"pedagogical_purpose": "Help the student make the thesis do argumentative work.",
                  "note": "TEST_M6 telos edit"},
            timeout=30,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["pedagogical_purpose"] == (
            "Help the student make the thesis do argumentative work."
        )
        assert body["telos"]["governing_pedagogical_purpose"] == (
            "Help the student make the thesis do argumentative work."
        )
        assert body["telos"]["telos_changed"].strip() != ""

    def test_get_nonexistent(self, client):
        r = client.get(f"{API}/sessions/does-not-exist-m6-{int(time.time())}", timeout=15)
        assert r.status_code == 404
