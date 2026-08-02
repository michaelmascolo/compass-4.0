"""Milestone 8 backend acceptance — Functional Evidence Framework.

Verifies that:
  (a) When a draft contains support (formal or embedded), theory.evidence_function.applies=True
      and evidence_function.function is populated.
  (b) Strong-evidence/weak-interpretation drafts: the AI honors the statistic and targets the
      INTERPRETATION gap (WHY it matters), NOT 'add more evidence'.
  (c) Weak-evidence/strong-interpretation drafts: interpretation honored; edge named as
      grounding — without the AI supplying evidence.
  (d) Embedded process/experiential support (explanatory process description, reflective
      sensory memory) also sets evidence_function.applies=True.
  (e) Missing/unsupported claim drafts invite the student to consider grounding —
      no invented content, focus='writing'.
  (f) NO 'add more evidence' / counting / rigid-rule phrasing on any invitation
      (no 'need three sources', 'cite at least two studies', 'add another statistic').
  (g) M5A: NO invented evidence/examples/statistics/quotations. intervention.focus=='writing'
      on ordinary drafts, writing_not_content_check non-empty.
  (h) M6 regression: theory.communicative_purpose.primary still populated.
  (i) M7 regression: when a paragraph is in focus, paragraph_function.applies=True with purpose.
  (j) M1-M5A/M7 regression: multi-turn writing->revise->answer preserves theory_history v1..vN,
      prior versions not overwritten; a real revision can produce 'consolidate';
      currently_relevant_domains stays 1-3; all turns under the streaming edge cap.

Run:  pytest /app/backend/tests/test_milestone8_evidence_function.py -v -n 0 -s
"""
import json
import os
import re
import time
from pathlib import Path

import pytest
import requests

# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------
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

# 'add more evidence' / counting / rigid-rule phrasing that M8 must AVOID.
RULE_FLAG_PATTERNS = [
    r"\badd more evidence\b",
    r"\bneed(?:s)?\s+(?:more|another|additional)\s+(?:evidence|examples?|sources?|quotes?|statistics?|data)\b",
    r"\b(?:at least|need|use|include|cite)\s+(?:two|three|3|2|several|multiple)\s+(?:sources?|examples?|quotes?|pieces of evidence|statistics?)\b",
    r"\byou\s+(?:need|should)\s+(?:cite|include|add)\s+(?:a\s+)?(?:source|statistic|quote|study)\b",
    r"\bback\s+(?:it|this|that)\s+up\s+with\s+(?:more\s+)?(?:facts|data|statistics|sources)\b",
    r"\bone\s+(?:more|additional)\s+(?:example|source|quote|statistic)\b",
]
RULE_RES = [re.compile(p, re.IGNORECASE) for p in RULE_FLAG_PATTERNS]

# Content-coaching red flags (M5A anti-coauthoring guard). The AI must not invent
# evidence/examples/content on non-brainstorming turns.
CONTENT_REDFLAGS = [
    r"\byou\s+(?:could|might|should)\s+(?:cite|mention|use the fact|add the example|include the statistic)\b",
    r"\bfor\s+(?:example|instance),?\s+(?:you could|consider|try)\b",
    r"\bconsider\s+(?:citing|adding|including|mentioning)\s+(?:the|a|an)\b",
    r"\bwhat\s+if\s+you\s+(?:cited|added|mentioned|used)\b",
    r"\ba\s+(?:study|statistic|fact)\s+(?:that|showing|about)\b",
    r"\btry\s+(?:citing|adding|using)\s+(?:a|an|the)\b",
    r"\byou may want to include\b",
]
CONTENT_RES = [re.compile(p, re.IGNORECASE) for p in CONTENT_REDFLAGS]


def _has_stage_score(text: str) -> bool:
    low = text.lower()
    return any(re.search(p, low) for p in STAGE_SCORE_PATTERNS)


def _rule_flags(text: str):
    return [p.pattern for p in RULE_RES if p.search(text)]


def _content_flags(text: str):
    return [p.pattern for p in CONTENT_RES if p.search(text)]


# --------------------------------------------------------------------------
# SSE client
# --------------------------------------------------------------------------
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


# --------------------------------------------------------------------------
# Fixtures / helpers
# --------------------------------------------------------------------------
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


def _ef(s):
    return s["theory"]["evidence_function"]


def _pf(s):
    return s["theory"]["paragraph_function"]


def _cp(s):
    return s["theory"]["communicative_purpose"]


def _assert_common_shape(s, weak_text=None):
    assert s.get("_saw_done_event") is True, "must see event: done"
    assert s.get("_elapsed_seconds", 999) < 150, (
        f"turn took too long: {s.get('_elapsed_seconds')}s"
    )
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

    # M6 regression
    cp = _cp(s)
    assert cp.get("primary", "").strip() != "", (
        f"M6 communicative_purpose.primary MUST be populated, got {cp!r}"
    )

    # M7 & M8 fields present
    pf = _pf(s)
    ef = _ef(s)
    assert isinstance(pf, dict) and "applies" in pf and "purpose" in pf
    assert isinstance(ef, dict) and "applies" in ef and "function" in ef
    return iv, inv, cp, pf, ef


ARG = "TEST_M8 Argue whether social media improves or harms teen friendships."
EXPL = "TEST_M8 Explain how a chosen process or phenomenon works."
REF = "TEST_M8 Reflect on what an experience taught you."
PURP = "Help the student use evidence and support to serve the essay's purpose."
TASK = "Draft a body paragraph."


# ==========================================================================
# 1. Strong evidence, weak interpretation — must target WHY it matters,
#    NOT 'add more evidence'. evidence_function.applies=True, function populated.
# ==========================================================================
class TestStrongEvidenceWeakInterpretation:
    def test_stat_honored_interpretation_gap_named(self, client):
        sid = _new_session(client, ARG, PURP, TASK)
        draft = (
            "Teens check their phones an average of 100 times a day, according to "
            "a 2023 study. This proves social media is a problem for friendships."
        )
        status, data, err = sse_interact_with_retry(
            client, sid, {"kind": "writing", "content": draft}
        )
        assert status == 200 and err is None and data is not None, f"err={err}"
        iv, inv, cp, pf, ef = _assert_common_shape(data, weak_text=draft)

        # (a) evidence recognized
        assert ef["applies"] is True, f"strong evidence must set applies=True, got {ef!r}"
        assert ef["function"].strip() != "", f"function must be populated, got {ef!r}"

        # (b) interpretation gap named
        gap_blob = " ".join([
            (ef.get("interpretation_gap") or ""), (ef.get("quality") or ""),
        ]).lower()
        interp_markers = [
            "why", "meaning", "means", "matter", "interpret", "connect",
            "significance", "so what", "reader",
        ]
        assert any(m in gap_blob for m in interp_markers), (
            f"interpretation gap should name why-it-matters/interpretation, got ef={ef!r}"
        )

        # (c) NO 'add more evidence' / counting / rigid-rule phrasing
        rf = _rule_flags(inv)
        assert not rf, f"'add more evidence' or counting/rigid-rule phrasing: {rf} | inv={inv!r}"

        # (d) M5A + no invented content
        assert iv["focus"] == "writing"
        assert iv["writing_not_content_check"].strip() != ""
        cf = _content_flags(inv)
        assert not cf, f"content-coaching phrasing: {cf} | inv={inv!r}"
        print(
            f"STRONG_EV/WEAK_INTERP applies={ef['applies']} "
            f"function={ef['function'][:70]!r} gap={ef.get('interpretation_gap','')[:60]!r}"
        )


# ==========================================================================
# 2. Weak evidence, strong interpretation — sharp interpretation honored,
#    edge named as grounding — without the AI supplying evidence.
# ==========================================================================
class TestWeakEvidenceStrongInterpretation:
    def test_interp_honored_grounding_edge(self, client):
        sid = _new_session(client, ARG, PURP, TASK)
        draft = (
            "I think social media quietly rewires how we value friends — it teaches "
            "us to measure closeness in likes rather than time. My cousin once said "
            "she felt lonelier the more she posted."
        )
        status, data, err = sse_interact_with_retry(
            client, sid, {"kind": "writing", "content": draft}
        )
        assert status == 200 and err is None and data is not None, f"err={err}"
        iv, inv, cp, pf, ef = _assert_common_shape(data, weak_text=draft)

        assert ef["applies"] is True, f"support present -> applies=True, got {ef!r}"
        assert ef["function"].strip() != ""

        # Edge names grounding, not 'add more evidence'
        rf = _rule_flags(inv)
        assert not rf, f"rigid-rule / counting phrasing: {rf} | inv={inv!r}"
        assert iv["focus"] == "writing"
        assert iv["writing_not_content_check"].strip() != ""
        cf = _content_flags(inv)
        assert not cf, f"invented content: {cf} | inv={inv!r}"

        # The invitation should orient toward grounding / concrete moment /
        # showing / making the reader see -- NOT hand over specific evidence.
        low = inv.lower()
        grounding_markers = [
            "ground", "concrete", "specific", "moment", "example",
            "detail", "show", "see", "reader", "what would", "how would",
            "notice", "what", "which",
        ]
        assert any(m in low for m in grounding_markers), (
            f"invitation should orient toward grounding, got {inv!r}"
        )
        print(
            f"WEAK_EV/STRONG_INTERP applies={ef['applies']} "
            f"function={ef['function'][:70]!r}"
        )


# ==========================================================================
# 3. Embedded support recognized — explanatory process description AND
#    reflective sensory memory both set evidence_function.applies=True.
# ==========================================================================
class TestEmbeddedSupportRecognition:
    def test_explanatory_process_description(self, client):
        sid = _new_session(client, EXPL, PURP, TASK)
        draft = (
            "When you flip the switch, current flows through the filament, "
            "which heats until it glows. The glowing filament is what produces "
            "the light you see."
        )
        status, data, err = sse_interact_with_retry(
            client, sid, {"kind": "writing", "content": draft}
        )
        assert status == 200 and err is None and data is not None, f"err={err}"
        iv, inv, cp, pf, ef = _assert_common_shape(data, weak_text=draft)

        assert ef["applies"] is True, (
            f"embedded process description must set applies=True, got {ef!r}"
        )
        assert ef["function"].strip() != ""
        rf = _rule_flags(inv)
        assert not rf, f"rigid-rule phrasing: {rf} | inv={inv!r}"
        assert iv["focus"] == "writing"
        assert iv["writing_not_content_check"].strip() != ""
        print(f"EMBEDDED_EXPL applies={ef['applies']} function={ef['function'][:70]!r}")

    def test_reflective_sensory_memory(self, client):
        sid = _new_session(client, REF, PURP, TASK)
        draft = (
            "The scar on my thumb reminds me of the summer I learned that fixing "
            "things and breaking them use the same tools."
        )
        status, data, err = sse_interact_with_retry(
            client, sid, {"kind": "writing", "content": draft}
        )
        assert status == 200 and err is None and data is not None, f"err={err}"
        iv, inv, cp, pf, ef = _assert_common_shape(data, weak_text=draft)

        assert ef["applies"] is True, (
            f"reflective sensory memory must set applies=True, got {ef!r}"
        )
        assert ef["function"].strip() != ""
        rf = _rule_flags(inv)
        assert not rf, f"rigid-rule phrasing: {rf} | inv={inv!r}"
        assert iv["focus"] == "writing"
        print(f"EMBEDDED_REF applies={ef['applies']} function={ef['function'][:70]!r}")


# ==========================================================================
# 4. Missing/unsupported claims — read as claim-without-grounding.
#    Student invited toward what would ground the point — not handed content.
# ==========================================================================
class TestUnsupportedClaims:
    def test_unsupported_claim_invited_to_ground(self, client):
        sid = _new_session(client, ARG, PURP, TASK)
        draft = (
            "Everyone knows social media ruins friendships. It obviously makes "
            "people fake."
        )
        status, data, err = sse_interact_with_retry(
            client, sid, {"kind": "writing", "content": draft}
        )
        assert status == 200 and err is None and data is not None, f"err={err}"
        iv, inv, cp, pf, ef = _assert_common_shape(data, weak_text=draft)

        # Missing evidence -> applies may legitimately be False (no support present).
        # But NO 'add more evidence' / counting / rigid-rule phrasing.
        rf = _rule_flags(inv)
        assert not rf, f"rigid-rule / counting phrasing: {rf} | inv={inv!r}"

        # M5A: focus='writing', no invented content
        assert iv["focus"] == "writing"
        assert iv["writing_not_content_check"].strip() != ""
        cf = _content_flags(inv)
        assert not cf, f"invented content: {cf} | inv={inv!r}"

        # Invitation should orient toward grounding / what would help the reader see /
        # what would support the point — never handing content.
        low = inv.lower()
        markers = [
            "ground", "support", "specific", "what would", "how would",
            "reader", "concrete", "example", "detail", "how do you know",
            "what makes", "which", "point",
        ]
        assert any(m in low for m in markers), (
            f"invitation should orient toward grounding the claim, got {inv!r}"
        )
        print(f"UNSUPPORTED_CLAIM applies={ef['applies']} focus={iv['focus']}")


# ==========================================================================
# 5. Multi-turn regression — M1-M7 preserved with M8 wired in.
#    theory_history v1..vN preserved, currently_relevant_domains 1..3,
#    all turns under the streaming edge cap, focus='writing'.
# ==========================================================================
class TestMultiTurnRegression:
    def test_multi_turn_theory_history_and_domains(self, client):
        sid = _new_session(client, ARG, PURP, TASK)

        # Turn 1 — strong-evidence/weak-interpretation
        d1_text = (
            "Teens check their phones an average of 100 times a day, according to "
            "a 2023 study. This proves social media is a problem for friendships."
        )
        s1, d1, e1 = sse_interact_with_retry(
            client, sid, {"kind": "writing", "content": d1_text}
        )
        assert s1 == 200 and e1 is None and d1 is not None, f"err={e1}"
        iv1, inv1, cp1, pf1, ef1 = _assert_common_shape(d1, weak_text=d1_text)
        assert ef1["applies"] is True and ef1["function"].strip() != ""
        rel1 = d1["theory"]["currently_relevant_domains"]
        assert 1 <= len(rel1) <= 3

        # Turn 2 — real revision that adds the missing interpretation
        revised = (
            "Teens check their phones an average of 100 times a day, according to "
            "a 2023 study. That constant checking matters because it turns "
            "friendships into a habit of monitoring rather than a practice of "
            "sustained attention — every glance is a small choice to be somewhere "
            "other than in the conversation you are already in."
        )
        s2, d2, e2 = sse_interact_with_retry(
            client, sid, {"kind": "revise", "content": revised}
        )
        assert s2 == 200 and e2 is None and d2 is not None, f"err={e2}"
        iv2, inv2, cp2, pf2, ef2 = _assert_common_shape(d2, weak_text=revised)

        # theory_history preserved and increasing
        assert len(d2["theory_history"]) == 2
        assert [snap["version"] for snap in d2["theory_history"]] == [1, 2]
        assert d2["theory_history"][0]["theory"]["currently_relevant_domains"] == []
        assert list(d2["theory_history"][1]["theory"]["currently_relevant_domains"]) == rel1
        rel2 = d2["theory"]["currently_relevant_domains"]
        assert 1 <= len(rel2) <= 3

        # Turn 3 — student answer
        s3, d3, e3 = sse_interact_with_retry(
            client, sid, {"kind": "answer",
                          "content": "I added the interpretation to name why the number matters, not just quote it."},
        )
        assert s3 == 200 and e3 is None and d3 is not None, f"err={e3}"
        iv3, inv3, cp3, pf3, ef3 = _assert_common_shape(d3)
        assert len(d3["theory_history"]) == 3
        assert [snap["version"] for snap in d3["theory_history"]] == [1, 2, 3]
        assert d3["theory_history"][0]["theory"]["currently_relevant_domains"] == []
        assert list(d3["theory_history"][1]["theory"]["currently_relevant_domains"]) == rel1
        assert list(d3["theory_history"][2]["theory"]["currently_relevant_domains"]) == rel2

        for i, (d, iv) in enumerate(((d1, iv1), (d2, iv2), (d3, iv3)), start=1):
            assert not _has_stage_score(_last_student_facing(d))
            assert 1 <= len(d["theory"]["currently_relevant_domains"]) <= 3
            assert iv["focus"] == "writing", f"turn {i} focus must be 'writing'"
            assert iv["writing_not_content_check"].strip() != ""
            rf = _rule_flags(_last_student_facing(d))
            assert not rf, f"turn {i} rigid-rule phrasing: {rf}"

        # A real revision (adding interpretation) SHOULD ideally produce 'consolidate'.
        # We do not hard-assert (LLM variation) but record it.
        print(
            f"MULTITURN t1 type={iv1['type']} ef1.applies={ef1['applies']} "
            f"t2 type={iv2['type']} ef2.applies={ef2['applies']} "
            f"t3 type={iv3['type']} ef3.applies={ef3['applies']}"
        )
        print(
            f"MULTITURN rel1={rel1} rel2={rel2} "
            f"rel3={d3['theory']['currently_relevant_domains']}"
        )


# ==========================================================================
# 6. Fast smoke — CRUD + PATCH telos + default evidence_function shape.
# ==========================================================================
class TestSessionCrud:
    def test_create_get_patch_default_ef(self, client):
        sid = _new_session(
            client,
            assignment="TEST_M8 crud smoke",
            purpose="Help the student use evidence to serve purpose.",
            task="Draft a paragraph.",
        )
        g = client.get(f"{API}/sessions/{sid}", timeout=15)
        assert g.status_code == 200
        assert g.json()["id"] == sid
        ef = g.json()["theory"]["evidence_function"]
        assert ef["applies"] is False
        assert ef["function"] == ""
        assert ef["interpretation_gap"] == ""
        assert ef["forms"] == []

        r = client.patch(
            f"{API}/sessions/{sid}/telos",
            json={"pedagogical_purpose": "Help the student make evidence serve the reader's understanding.",
                  "note": "TEST_M8 telos edit"},
            timeout=30,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["pedagogical_purpose"] == (
            "Help the student make evidence serve the reader's understanding."
        )
        assert body["telos"]["governing_pedagogical_purpose"] == (
            "Help the student make evidence serve the reader's understanding."
        )

    def test_get_nonexistent(self, client):
        r = client.get(f"{API}/sessions/does-not-exist-m8-{int(time.time())}", timeout=15)
        assert r.status_code == 404
