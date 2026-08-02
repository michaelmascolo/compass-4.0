"""Milestone 7 backend acceptance — Functional Paragraph Framework.

Verifies that when a paragraph is the unit under discussion the AI:
  (a) sets theory.paragraph_function.applies=True and populates .purpose
      (relative to the M6 communicative purpose) — for BOTH strong/effective
      paragraphs and weakly-organized paragraphs.
  (b) does NOT impose a rigid paragraph template (no obligatory
      topic-sentence -> evidence -> analysis -> concluding-sentence,
      no PEE/PEEL/MEAL/TEAL/RACE formula, no "must end with a concluding
      sentence").
  (c) diagnoses a weakly-organized paragraph as unclear-purpose and invites
      the student to name the paragraph's job.
  (d) coordinates M7 with M6 — for a narrative paragraph the invitation is
      about narrative meaning (not a persuasive claim), and
      theory.communicative_purpose.primary is still populated.
  (e) preserves M5A boundary on ordinary paragraph drafts:
      intervention.focus == 'writing', writing_not_content_check non-empty,
      no content-coaching red flags.
  (f) preserves M1-M6 across multi-turn writing -> revise -> answer:
      theory_history v1..vN, prior versions intact,
      currently_relevant_domains stays 1-3, no stage/rubric leaks,
      all turns under the streaming-edge cap (no 502).

Run:  pytest /app/backend/tests/test_milestone7_paragraph_function.py -v -n 0 -s
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
]

# Rigid paragraph-template phrasing that should NEVER appear on a paragraph draft.
RIGID_PARA_TEMPLATE_PATTERNS = [
    r"topic sentence.*(?:evidence|example).*(?:analysis|explanation)",
    r"topic sentence.*(?:analysis|explanation).*(?:evidence|example)",
    r"every paragraph (?:must|should|needs to) (?:have|contain|include|start with) a topic sentence",
    r"(?:begin|start) (?:every|each) paragraph with a topic sentence",
    r"\bPEE(?:L)?\b (?:paragraph|format|structure|method|formula|template)?",
    r"\bMEAL\b (?:paragraph|format|structure|method|formula|template)?",
    r"\bTEAL\b (?:paragraph|format|structure|method|formula|template)?",
    r"\bRACE\b (?:paragraph|format|structure|method|formula|template)?",
    r"must (?:end|close|finish) with a concluding sentence",
    r"follow (?:the|this) (?:paragraph )?(?:template|formula)",
    r"claim[- ]evidence[- ]analysis (?:format|template|formula|structure)",
    # whole-essay templates carried over
    r"five[-\s]paragraph",
    r"three body paragraph",
    r"hook[-,\s]+background[-,\s]+thesis",
]
RIGID_RES = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in RIGID_PARA_TEMPLATE_PATTERNS]

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
    r"one more (?:reason|point|example)",
]
CONTENT_RES = [re.compile(p, re.IGNORECASE) for p in CONTENT_REDFLAGS]


def _has_stage_score(text: str) -> bool:
    low = text.lower()
    return any(re.search(p, low) for p in STAGE_SCORE_PATTERNS)


def _rigid_flags(text: str):
    return [p.pattern for p in RIGID_RES if p.search(text)]


def _content_flags(text: str):
    return [p.pattern for p in CONTENT_RES if p.search(text)]


# ---------------------------------------------------------------------------
# SSE client
# ---------------------------------------------------------------------------
def sse_interact(client, sid, payload, timeout=180):
    started = time.time()
    with client.post(
        f"{API}/sessions/{sid}/interact",
        json=payload, stream=True, timeout=timeout,
        headers={"Accept": "text/event-stream"},
    ) as r:
        if r.status_code != 200:
            return r.status_code, None, r.text
        buf, done_payload, err_detail, saw_done = "", None, None, False
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
                    saw_done = True
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
            done_payload["_saw_done_event"] = saw_done
        return r.status_code, done_payload, err_detail


def sse_interact_with_retry(client, sid, payload, timeout=180):
    status, data, err = sse_interact(client, sid, payload, timeout)
    if status == 200 and data is None and err is None:
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


def _pf(s):
    return s["theory"]["paragraph_function"]


def _cp(s):
    return s["theory"]["communicative_purpose"]


def _assert_common_shape(s, weak_text=None):
    """Assertions applied to every /interact response in this suite."""
    assert s.get("_saw_done_event") is True, "must see event: done"
    assert s.get("_elapsed_seconds", 999) < 150, (
        f"turn took too long: {s.get('_elapsed_seconds')}s"
    )
    # last turn is ai; counts match
    ai = [t for t in s["turns"] if t["role"] == "ai"]
    student = [t for t in s["turns"] if t["role"] == "student"]
    assert s["turns"][-1]["role"] == "ai"
    assert len(ai) == len(student) == len(s["interactions"])

    inv = _last_student_facing(s)
    if weak_text is not None:
        assert weak_text not in inv, "AI appears to have echoed/rewritten the student's text"
    assert not _has_stage_score(inv), f"stage/level/rubric leaked: {inv[:200]}"

    iv = _last_intervention(s)
    assert iv["type"] in VALID_INTERVENTION_TYPES

    # M6 field must be present and populated with primary
    cp = _cp(s)
    assert cp.get("primary", "").strip() != "", (
        f"M6 communicative_purpose.primary MUST be populated, got {cp!r}"
    )

    # M7 paragraph_function must exist (may or may not apply)
    pf = _pf(s)
    assert isinstance(pf, dict)
    assert "applies" in pf and "purpose" in pf
    return iv, inv, cp, pf


# ===========================================================================
# 1. Effective paragraph — honored (not restructured), applies=true, purpose set
# ===========================================================================
class TestEffectiveParagraph:
    def test_strong_paragraph_honored_and_named(self, client):
        sid = _new_session(
            client,
            assignment="TEST_M7 Argue whether social media improves or harms teen friendships.",
            purpose="Help the student clarify what each paragraph is doing for the essay.",
            task="Draft a paragraph.",
        )
        draft = (
            "When a friend 'likes' your post but never texts back, the gesture "
            "says everything: presence without contact. That gap — being "
            "acknowledged but not reached — is what makes online closeness "
            "feel thinner than it looks."
        )
        status, data, err = sse_interact_with_retry(
            client, sid, {"kind": "writing", "content": draft}
        )
        assert status == 200 and err is None and data is not None, f"err={err}"
        iv, inv, cp, pf = _assert_common_shape(data, weak_text=draft)

        # M7 core assertions
        assert pf["applies"] is True, (
            f"strong paragraph should still have applies=True (name the function), got {pf!r}"
        )
        assert pf["purpose"].strip() != "", (
            f"paragraph_function.purpose must be populated for a paragraph draft, got {pf!r}"
        )
        # M5A regression
        assert iv["focus"] == "writing"
        assert iv["writing_not_content_check"].strip() != ""
        cflags = _content_flags(inv)
        assert not cflags, f"content-coaching phrasing: {cflags} | inv={inv!r}"
        # No rigid paragraph template phrasing
        tflags = _rigid_flags(inv)
        assert not tflags, f"rigid paragraph-template phrasing: {tflags} | inv={inv!r}"

        # Coordinates with M6 — persuasive assignment
        prim = (cp.get("primary") or "").lower()
        assert any(k in prim for k in ("persuad", "argu", "convinc", "advocat")), (
            f"persuasive assignment must yield persuade/argue primary, got {cp!r}"
        )
        print(f"STRONG pf.purpose={pf['purpose'][:80]!r} type={iv['type']} cp.primary={cp.get('primary')!r}")


# ===========================================================================
# 2. Weakly-organized paragraph — diagnosed as unclear-purpose; invited to name job
# ===========================================================================
class TestWeaklyOrganizedParagraph:
    def test_weak_paragraph_diagnosed_and_invited(self, client):
        sid = _new_session(
            client,
            assignment="TEST_M7 Argue whether social media improves or harms teen friendships.",
            purpose="Help the student clarify what each paragraph is doing for the essay.",
            task="Draft a paragraph.",
        )
        draft = (
            "Social media is bad. Also teens use it. Phones are expensive. "
            "Friendships matter."
        )
        status, data, err = sse_interact_with_retry(
            client, sid, {"kind": "writing", "content": draft}
        )
        assert status == 200 and err is None and data is not None, f"err={err}"
        iv, inv, cp, pf = _assert_common_shape(data, weak_text=draft)

        assert pf["applies"] is True, f"weak paragraph must have applies=True, got {pf!r}"
        assert pf["purpose"].strip() != "", f"purpose must be populated, got {pf!r}"

        # Should read as unclear-purpose / not-yet-cohering
        pf_blob = " ".join([
            (pf.get("purpose") or ""), (pf.get("coherence") or ""),
        ]).lower()
        unclear_markers = ["unclear", "not yet", "no single", "does not cohere",
                           "do not cohere", "multiple", "several", "indeterminate",
                           "cannot", "does not hold", "no clear", "hold together",
                           "not clear"]
        assert any(m in pf_blob for m in unclear_markers), (
            f"weak paragraph should read as unclear/incoherent purpose, got pf={pf!r}"
        )

        # Invitation asks the student to name/decide the paragraph's job — but
        # WITHOUT rigid template phrasing and WITHOUT content coaching.
        tflags = _rigid_flags(inv)
        assert not tflags, f"rigid paragraph-template phrasing: {tflags} | inv={inv!r}"
        cflags = _content_flags(inv)
        assert not cflags, f"content-coaching phrasing: {cflags} | inv={inv!r}"

        # Should invite the student to name / decide / clarify what the paragraph is trying to do
        low = inv.lower()
        job_markers = [
            "what", "which", "job", "purpose", "trying to", "point", "focus",
            "argument", "claim", "controlling", "one idea",
        ]
        assert any(m in low for m in job_markers), (
            f"invitation should invite the student to name the paragraph's job, got {inv!r}"
        )

        # M5A regression
        assert iv["focus"] == "writing"
        assert iv["writing_not_content_check"].strip() != ""
        print(f"WEAK pf.purpose={pf['purpose'][:80]!r} coherence={pf['coherence'][:80]!r} type={iv['type']}")


# ===========================================================================
# 3. M6/M7 coordination — narrative paragraph gets narrative meaning invitation
# ===========================================================================
class TestNarrativeParagraphCoordination:
    def test_narrative_paragraph_invited_about_meaning_not_thesis(self, client):
        sid = _new_session(
            client,
            assignment="TEST_M7 Write a personal narrative about a meaningful experience.",
            purpose="Help the student shape a personal narrative that communicates the meaning of an experience.",
            task="Draft a paragraph.",
        )
        draft = (
            "The kitchen still smelled like her cigarettes that morning, "
            "though she'd quit a year before she left. I stood in the doorway "
            "not going in, the way you pause at the edge of a photograph "
            "you're not ready to be inside of."
        )
        status, data, err = sse_interact_with_retry(
            client, sid, {"kind": "writing", "content": draft}
        )
        assert status == 200 and err is None and data is not None, f"err={err}"
        iv, inv, cp, pf = _assert_common_shape(data, weak_text=draft)

        # M7 paragraph_function applies + purpose populated
        assert pf["applies"] is True, f"narrative paragraph must have applies=True, got {pf!r}"
        assert pf["purpose"].strip() != ""
        # M6 communicative purpose is narrative
        prim = (cp.get("primary") or "").lower()
        assert any(k in prim for k in ("narrat", "story", "recount", "reflect")), (
            f"narrative assignment must yield narrate primary, got {cp!r}"
        )

        # Invitation MUST NOT push a persuasive thesis / claim apparatus.
        low = inv.lower()
        forbidden = [
            r"\bthesis statement\b",
            r"\bstate your (?:argument|claim|position|thesis)\b",
            r"\bmake (?:an|your) argument\b",
            r"\bmake a claim\b",
            r"\bwhat are you arguing\b",
            r"\byour argument\b",
        ]
        pushes = [p for p in forbidden if re.search(p, low)]
        assert not pushes, f"narrative got persuasive-thesis push: {pushes} | inv={inv!r}"

        # M5A + no rigid template
        assert iv["focus"] == "writing"
        assert iv["writing_not_content_check"].strip() != ""
        tflags = _rigid_flags(inv)
        assert not tflags, f"rigid paragraph-template phrasing: {tflags} | inv={inv!r}"
        cflags = _content_flags(inv)
        assert not cflags, f"content-coaching phrasing: {cflags} | inv={inv!r}"
        print(f"NARRATIVE pf.purpose={pf['purpose'][:100]!r} cp.primary={cp.get('primary')!r} type={iv['type']}")


# ===========================================================================
# 4. Multi-turn regression — theory_history preserved, paragraph_function stable
# ===========================================================================
class TestMultiTurnRegression:
    def test_paragraph_multi_turn(self, client):
        sid = _new_session(
            client,
            assignment="TEST_M7 Argue whether social media improves or harms teen friendships.",
            purpose="Help the student clarify what each paragraph is doing for the essay.",
            task="Draft a paragraph.",
        )

        # Turn 1 — weak paragraph
        d1_text = (
            "Social media is bad. Also teens use it. Phones are expensive. "
            "Friendships matter."
        )
        s1, d1, e1 = sse_interact_with_retry(
            client, sid, {"kind": "writing", "content": d1_text}
        )
        assert s1 == 200 and e1 is None and d1 is not None, f"err={e1}"
        iv1, inv1, cp1, pf1 = _assert_common_shape(d1, weak_text=d1_text)
        assert pf1["applies"] is True and pf1["purpose"].strip() != ""
        rel1 = d1["theory"]["currently_relevant_domains"]
        assert 1 <= len(rel1) <= 3

        # Turn 2 — real revision producing a focused paragraph
        revised = (
            "Constant availability weakens close friendships because it "
            "removes the small absences that used to make return meaningful; "
            "when no one is ever gone, no one is ever quite missed, and the "
            "muscle of noticing another person's absence goes slack."
        )
        s2, d2, e2 = sse_interact_with_retry(
            client, sid, {"kind": "revise", "content": revised}
        )
        assert s2 == 200 and e2 is None and d2 is not None, f"err={e2}"
        iv2, inv2, cp2, pf2 = _assert_common_shape(d2, weak_text=revised)
        assert pf2["applies"] is True and pf2["purpose"].strip() != ""

        # theory_history preserved and increasing
        assert len(d2["theory_history"]) == 2
        assert [snap["version"] for snap in d2["theory_history"]] == [1, 2]
        # v1 was pre-turn-1: empty domains
        assert d2["theory_history"][0]["theory"]["currently_relevant_domains"] == []
        # v2 preserves turn-1 domains
        assert list(d2["theory_history"][1]["theory"]["currently_relevant_domains"]) == rel1
        rel2 = d2["theory"]["currently_relevant_domains"]
        assert 1 <= len(rel2) <= 3

        # A real revision on this text SHOULD (ideally) produce a consolidate.
        # We do not hard-assert consolidate (LLM variation), but we record it.
        print(f"MULTITURN t1 iv.type={iv1['type']} pf1.applies={pf1['applies']} "
              f"pf1.purpose={pf1['purpose'][:60]!r}")
        print(f"MULTITURN t2 iv.type={iv2['type']} pf2.applies={pf2['applies']} "
              f"pf2.purpose={pf2['purpose'][:60]!r}")

        # Turn 3 — student answer
        s3, d3, e3 = sse_interact_with_retry(
            client, sid, {"kind": "answer",
                          "content": "I wanted this paragraph to name a specific mechanism, not just repeat that social media is bad."},
        )
        assert s3 == 200 and e3 is None and d3 is not None, f"err={e3}"
        iv3, inv3, cp3, pf3 = _assert_common_shape(d3)
        assert len(d3["theory_history"]) == 3
        assert [snap["version"] for snap in d3["theory_history"]] == [1, 2, 3]
        assert d3["theory_history"][0]["theory"]["currently_relevant_domains"] == []
        assert list(d3["theory_history"][1]["theory"]["currently_relevant_domains"]) == rel1
        assert list(d3["theory_history"][2]["theory"]["currently_relevant_domains"]) == rel2

        # All turns: no stage/rubric leaks, focus='writing', 1..3 domains
        for i, (d, iv) in enumerate(((d1, iv1), (d2, iv2), (d3, iv3)), start=1):
            assert not _has_stage_score(_last_student_facing(d))
            assert not _has_stage_score(json.dumps(d["interactions"]))
            assert 1 <= len(d["theory"]["currently_relevant_domains"]) <= 3
            assert iv["focus"] == "writing", f"turn {i} focus must be 'writing'"
            assert iv["writing_not_content_check"].strip() != ""
            # No rigid template on any turn
            tflags = _rigid_flags(_last_student_facing(d))
            assert not tflags, f"turn {i} rigid-template: {tflags}"

        print(f"MULTITURN rel1={rel1} rel2={rel2} rel3={d3['theory']['currently_relevant_domains']} "
              f"types={iv1['type']}->{iv2['type']}->{iv3['type']}")


# ===========================================================================
# 5. Fast smoke: session CRUD + PATCH telos still work
# ===========================================================================
class TestSessionCrud:
    def test_create_get_patch(self, client):
        sid = _new_session(
            client,
            assignment="TEST_M7 crud smoke",
            purpose="Help the student clarify a paragraph's job.",
            task="Draft a paragraph.",
        )
        g = client.get(f"{API}/sessions/{sid}", timeout=15)
        assert g.status_code == 200
        assert g.json()["id"] == sid
        # theory.paragraph_function present with applies=False by default
        pf = g.json()["theory"]["paragraph_function"]
        assert pf["applies"] is False
        assert pf["purpose"] == ""

        r = client.patch(
            f"{API}/sessions/{sid}/telos",
            json={"pedagogical_purpose": "Help the student make the paragraph do a single, clear job.",
                  "note": "TEST_M7 telos edit"},
            timeout=30,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["pedagogical_purpose"] == (
            "Help the student make the paragraph do a single, clear job."
        )
        assert body["telos"]["governing_pedagogical_purpose"] == (
            "Help the student make the paragraph do a single, clear job."
        )
        assert body["telos"]["telos_changed"].strip() != ""

    def test_get_nonexistent(self, client):
        r = client.get(f"{API}/sessions/does-not-exist-m7-{int(time.time())}", timeout=15)
        assert r.status_code == 404
