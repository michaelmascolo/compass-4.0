"""Milestone 9 backend acceptance — Functional Transitions and Coherence Framework.

Verifies that:
  (a) When continuity/flow/connection is in focus, theory.coherence_function.applies=True
      and coherence_function.intended_relationship is populated.
  (b) STRONG-flow-few-transition-words drafts are HONORED — the engine names the
      relationship (cause-effect/logical progression) rather than telling the student to
      add transition words.
  (c) MANY-transition-words-WEAK-coherence drafts: the engine sees through the connective
      vocabulary and names the relationship as unclear.
  (d) Level identification: weak paragraph-to-paragraph pairs yield level that mentions
      "paragraph-to-paragraph"; scattered sentence set yields "sentence-to-sentence".
  (e) NO rigid transition-rule phrasing: no "add transition words", "use words like
      however/therefore", "start each paragraph with a transition", "insert a transition"
      on any invitation.
  (f) M5A: NO invented ideas/content. intervention.focus=='writing'.
  (g) M6 regression: theory.communicative_purpose.primary populated.
  (h) M7 regression: when a paragraph is in focus paragraph_function.applies=True.
  (i) M8 regression: when support is present evidence_function.applies=True.
  (j) M1-M5A regression: multi-turn writing->revise->answer preserves theory_history
      v1..vN (prior versions not overwritten); real revision may produce 'consolidate';
      currently_relevant_domains stays 1-3; all turns under streaming edge cap;
      intervention.writing_not_content_check non-empty on every turn.

Run:  pytest /app/backend/tests/test_milestone9_coherence_function.py -v -n 0 -s
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

# Rigid-transition-rule phrasing that M9 must AVOID.
RULE_FLAG_PATTERNS = [
    r"\badd\s+(?:more\s+)?transition(?:al)?\s+words?\b",
    r"\buse\s+(?:more\s+)?transition(?:al)?\s+words?\b",
    r"\b(?:start|begin)\s+(?:each|every|the)\s+(?:sentence|paragraph)\s+with\s+(?:a\s+)?transition",
    r"\binsert\s+(?:a\s+)?transition(?:al)?\s+(?:word|phrase)\b",
    r"\bwords?\s+like\s+['\"]?(?:however|therefore|furthermore|moreover|additionally|consequently|firstly|secondly)",
    r"\b(?:need|should)\s+(?:more|some)\s+transition",
    r"\bsprinkle\s+in\s+(?:some\s+)?transitions?\b",
    r"\buse\s+connective\s+words\b",
]
RULE_RES = [re.compile(p, re.IGNORECASE) for p in RULE_FLAG_PATTERNS]

# Content-coaching red flags (M5A anti-coauthoring).
CONTENT_REDFLAGS = [
    r"\byou\s+(?:could|might|should)\s+add\s+(?:a|an|the|another)\s+(?:point|idea|argument|reason|example)\b",
    r"\banother\s+(?:reason|argument|point|idea|example)\b",
    r"\bconsider\s+(?:adding|including|mentioning)\s+(?:the|a|an)\b",
    r"\bfor\s+example,?\s+you\s+could\b",
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


def _cf(s):
    return s["theory"]["coherence_function"]


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

    # Structural fields present
    cf = _cf(s)
    assert isinstance(cf, dict) and "applies" in cf and "intended_relationship" in cf
    return iv, inv, cp, cf


ARG = "TEST_M9 Argue whether social media improves or harms teen friendships."
ARG2 = "TEST_M9 Argue whether your city should reduce car traffic downtown."
EXPL = "TEST_M9 Explain how a chosen process or phenomenon works."
ANL = "TEST_M9 Analyze how a text or space produces its effect."
PURP = "Help the student create coherence and communicate relationships among ideas clearly."
TASK = "Draft this section of your writing."


# ==========================================================================
# 1. Strong flow, few transition words — honored; relationship named;
#    invitation must NOT tell the student to add transition words.
# ==========================================================================
class TestStrongFlowFewTransitionWords:
    def test_strong_flow_relationship_named_not_add_transitions(self, client):
        sid = _new_session(client, ARG, PURP, TASK)
        draft = (
            "Constant availability removes the small absences that used to make "
            "return meaningful. When no one is ever gone, no one is ever quite missed. "
            "The friendship stays lit but stops being felt."
        )
        status, data, err = sse_interact_with_retry(
            client, sid, {"kind": "writing", "content": draft}
        )
        assert status == 200 and err is None and data is not None, f"err={err}"
        iv, inv, cp, cf = _assert_common_shape(data, weak_text=draft)

        # (a) coherence recognized as in focus
        assert cf["applies"] is True, (
            f"strong-flow draft must set coherence_function.applies=True, got {cf!r}"
        )
        rel = (cf.get("intended_relationship") or "").strip()
        assert rel != "", f"intended_relationship must be populated, got {cf!r}"

        # (b) relationship should read as cause-effect / logical progression / elaboration
        rel_low = rel.lower()
        rel_markers = ["cause", "effect", "logical", "progression", "elaboration",
                       "contrast", "concession", "consequen"]
        assert any(m in rel_low for m in rel_markers), (
            f"expected the engine to name cause-effect/progression, got rel={rel!r}"
        )

        # (c) invitation must NOT tell the student to add transition words
        rf = _rule_flags(inv)
        assert not rf, (
            f"'add transition words' / rigid-rule phrasing found: {rf} | inv={inv!r}"
        )

        # (d) M5A + no invented content
        assert iv["focus"] == "writing"
        assert iv["writing_not_content_check"].strip() != ""
        contf = _content_flags(inv)
        assert not contf, f"content-coaching phrasing: {contf} | inv={inv!r}"
        print(
            f"STRONG_FLOW applies={cf['applies']} rel={rel!r} level={cf.get('level','')!r}"
        )


# ==========================================================================
# 2. Many transition words but WEAK coherence — engine must see through
#    the connective vocabulary and name the relationship as unclear.
# ==========================================================================
class TestManyWordsWeakCoherence:
    def test_engine_sees_through_connective_words(self, client):
        sid = _new_session(client, ARG, PURP, TASK)
        draft = (
            "Firstly social media is popular. However phones are expensive. Moreover "
            "teens are busy. Therefore in conclusion friendships are a topic."
        )
        status, data, err = sse_interact_with_retry(
            client, sid, {"kind": "writing", "content": draft}
        )
        assert status == 200 and err is None and data is not None, f"err={err}"
        iv, inv, cp, cf = _assert_common_shape(data, weak_text=draft)

        assert cf["applies"] is True, (
            f"transition-word-heavy draft must engage coherence, got {cf!r}"
        )
        rel = (cf.get("intended_relationship") or "").strip()
        assert rel != "", f"intended_relationship must be populated, got {cf!r}"

        # Engine must NOT praise the transition words as evidence of coherence.
        # Instead it should flag the relationship as unclear/undetermined.
        rel_low = rel.lower()
        unclear_markers = ["unclear", "unknown", "cannot", "not clear", "undetermined",
                           "no discernible", "no clear", "no readable", "no relationship",
                           "cannot be determined", "hard to tell", "difficult to"]
        # Accept the engine either explicitly flagging unclarity in intended_relationship,
        # OR in reader_can_follow.
        reader_low = (cf.get("reader_can_follow") or "").lower()
        blob = rel_low + " || " + reader_low
        assert any(m in blob for m in unclear_markers), (
            f"engine should flag unclear relationship, got rel={rel!r} reader_can_follow={cf.get('reader_can_follow','')!r}"
        )

        # No rigid transition rules
        rf = _rule_flags(inv)
        assert not rf, f"rigid-rule phrasing: {rf} | inv={inv!r}"
        assert iv["focus"] == "writing"
        assert iv["writing_not_content_check"].strip() != ""
        contf = _content_flags(inv)
        assert not contf, f"content-coaching phrasing: {contf} | inv={inv!r}"
        print(
            f"MANY_WORDS_WEAK applies={cf['applies']} rel={rel!r} "
            f"reader_can_follow={cf.get('reader_can_follow','')[:60]!r}"
        )


# ==========================================================================
# 3. Level identification — weak paragraph-to-paragraph pair yields level
#    mentioning paragraph-to-paragraph.
# ==========================================================================
class TestParagraphToParagraphLevel:
    def test_paragraph_to_paragraph_level_identified(self, client):
        sid = _new_session(client, ARG, PURP, TASK)
        draft = (
            "Paragraph one argues social media distracts teens during homework.\n\n"
            "Paragraph two suddenly describes the history of the printing press in "
            "the 1400s with no link back."
        )
        status, data, err = sse_interact_with_retry(
            client, sid, {"kind": "writing", "content": draft}
        )
        assert status == 200 and err is None and data is not None, f"err={err}"
        iv, inv, cp, cf = _assert_common_shape(data, weak_text=draft)

        assert cf["applies"] is True, f"applies must be True, got {cf!r}"
        level = (cf.get("level") or "").lower()
        assert "paragraph-to-paragraph" in level or "paragraph to paragraph" in level, (
            f"level must mention paragraph-to-paragraph, got {cf.get('level')!r}"
        )
        rf = _rule_flags(inv)
        assert not rf, f"rigid-rule phrasing: {rf} | inv={inv!r}"
        assert iv["focus"] == "writing"
        print(f"P2P_LEVEL level={cf.get('level')!r}")


# ==========================================================================
# 4. Level identification — scattered sentence set yields sentence-to-sentence.
# ==========================================================================
class TestSentenceToSentenceLevel:
    def test_sentence_to_sentence_level_identified(self, client):
        sid = _new_session(client, ARG, PURP, TASK)
        draft = (
            "Teens post a lot. My phone is blue. Friendship matters to society. "
            "The cafeteria was crowded yesterday."
        )
        status, data, err = sse_interact_with_retry(
            client, sid, {"kind": "writing", "content": draft}
        )
        assert status == 200 and err is None and data is not None, f"err={err}"
        iv, inv, cp, cf = _assert_common_shape(data, weak_text=draft)

        assert cf["applies"] is True, f"applies must be True, got {cf!r}"
        level = (cf.get("level") or "").lower()
        assert "sentence-to-sentence" in level or "sentence to sentence" in level, (
            f"level must mention sentence-to-sentence, got {cf.get('level')!r}"
        )
        rf = _rule_flags(inv)
        assert not rf, f"rigid-rule phrasing: {rf} | inv={inv!r}"
        assert iv["focus"] == "writing"
        print(f"S2S_LEVEL level={cf.get('level')!r}")


# ==========================================================================
# 5. Multi-turn regression — M1-M8 preserved with M9 wired in.
#    theory_history v1..vN preserved, currently_relevant_domains 1..3,
#    focus='writing' on all turns.
# ==========================================================================
class TestMultiTurnRegression:
    def test_multi_turn_theory_history_and_domains(self, client):
        sid = _new_session(client, ARG, PURP, TASK)

        # Turn 1 — a paragraph with support and coherence in play
        d1_text = (
            "Firstly social media is popular. However phones are expensive. "
            "Moreover teens are busy. Therefore in conclusion friendships are a topic."
        )
        s1, d1, e1 = sse_interact_with_retry(
            client, sid, {"kind": "writing", "content": d1_text}
        )
        assert s1 == 200 and e1 is None and d1 is not None, f"err={e1}"
        iv1, inv1, cp1, cf1 = _assert_common_shape(d1, weak_text=d1_text)
        assert cf1["applies"] is True
        rel1_dom = d1["theory"]["currently_relevant_domains"]
        assert 1 <= len(rel1_dom) <= 3

        # Turn 2 — real revision that makes the relationships legible
        revised = (
            "Teens live on their phones — that constant availability changes what "
            "friendship feels like. Because being always-on removes the small "
            "absences that used to make return meaningful, friendships stay lit "
            "but stop being felt. The connection continues; the presence weakens."
        )
        s2, d2, e2 = sse_interact_with_retry(
            client, sid, {"kind": "revise", "content": revised}
        )
        assert s2 == 200 and e2 is None and d2 is not None, f"err={e2}"
        iv2, inv2, cp2, cf2 = _assert_common_shape(d2, weak_text=revised)

        # theory_history preserved and increasing
        assert len(d2["theory_history"]) == 2
        assert [snap["version"] for snap in d2["theory_history"]] == [1, 2]
        assert d2["theory_history"][0]["theory"]["currently_relevant_domains"] == []
        assert list(d2["theory_history"][1]["theory"]["currently_relevant_domains"]) == rel1_dom
        rel2_dom = d2["theory"]["currently_relevant_domains"]
        assert 1 <= len(rel2_dom) <= 3

        # Turn 3 — student answer
        s3, d3, e3 = sse_interact_with_retry(
            client, sid, {"kind": "answer",
                          "content": "I rewrote it so the causal relationship between constant availability and weakened presence is clear, instead of using transition words to fake it."},
        )
        assert s3 == 200 and e3 is None and d3 is not None, f"err={e3}"
        iv3, inv3, cp3, cf3 = _assert_common_shape(d3)
        assert len(d3["theory_history"]) == 3
        assert [snap["version"] for snap in d3["theory_history"]] == [1, 2, 3]
        assert d3["theory_history"][0]["theory"]["currently_relevant_domains"] == []
        assert list(d3["theory_history"][1]["theory"]["currently_relevant_domains"]) == rel1_dom
        assert list(d3["theory_history"][2]["theory"]["currently_relevant_domains"]) == rel2_dom

        for i, (d, iv) in enumerate(((d1, iv1), (d2, iv2), (d3, iv3)), start=1):
            assert not _has_stage_score(_last_student_facing(d))
            assert 1 <= len(d["theory"]["currently_relevant_domains"]) <= 3
            assert iv["focus"] == "writing", f"turn {i} focus must be 'writing'"
            assert iv["writing_not_content_check"].strip() != ""
            rf = _rule_flags(_last_student_facing(d))
            assert not rf, f"turn {i} rigid-rule phrasing: {rf}"

        print(
            f"MULTITURN t1 type={iv1['type']} cf1.applies={cf1['applies']} "
            f"t2 type={iv2['type']} cf2.applies={cf2['applies']} "
            f"t3 type={iv3['type']} cf3.applies={cf3['applies']}"
        )
        print(
            f"MULTITURN rel_dom1={rel1_dom} rel_dom2={rel2_dom} "
            f"rel_dom3={d3['theory']['currently_relevant_domains']}"
        )


# ==========================================================================
# 6. M6/M7/M8 regression on a supported paragraph draft.
# ==========================================================================
class TestM6M7M8Regression:
    def test_paragraph_with_support_preserves_prior_frameworks(self, client):
        sid = _new_session(client, ARG, PURP, "Draft a body paragraph.")
        draft = (
            "Teens check their phones an average of 100 times a day, according to "
            "a 2023 study. That constant checking matters because it turns "
            "friendships into a habit of monitoring rather than sustained attention. "
            "Because attention builds intimacy, and monitoring interrupts it, "
            "friendships that live only through phones grow thin."
        )
        status, data, err = sse_interact_with_retry(
            client, sid, {"kind": "writing", "content": draft}
        )
        assert status == 200 and err is None and data is not None, f"err={err}"
        iv, inv, cp, cf = _assert_common_shape(data, weak_text=draft)

        # M6
        assert cp["primary"].strip() != ""
        # M7 — paragraph in focus
        pf = _pf(data)
        assert pf["applies"] is True, f"M7 paragraph_function.applies must be True, got {pf!r}"
        assert pf["purpose"].strip() != "", f"M7 purpose must be populated, got {pf!r}"
        # M8 — support present
        ef = _ef(data)
        assert ef["applies"] is True, f"M8 evidence_function.applies must be True, got {ef!r}"
        assert ef["function"].strip() != "", f"M8 function must be populated, got {ef!r}"

        # M9 too — coherence should be recognized as a feature of this draft
        assert cf["applies"] is True, f"M9 coherence_function.applies expected True on flowing draft, got {cf!r}"

        rf = _rule_flags(inv)
        assert not rf, f"rigid-rule phrasing: {rf}"
        assert iv["focus"] == "writing"
        print(
            f"REG_M6/M7/M8/M9 cp={cp['primary'][:30]!r} pf.applies={pf['applies']} "
            f"ef.applies={ef['applies']} cf.applies={cf['applies']}"
        )


# ==========================================================================
# 7. Fast smoke — CRUD + PATCH telos + default coherence_function shape.
# ==========================================================================
class TestSessionCrud:
    def test_create_get_patch_default_cf(self, client):
        sid = _new_session(
            client,
            assignment="TEST_M9 crud smoke",
            purpose="Help the student communicate relationships among ideas.",
            task="Draft a paragraph.",
        )
        g = client.get(f"{API}/sessions/{sid}", timeout=15)
        assert g.status_code == 200
        assert g.json()["id"] == sid
        cf = g.json()["theory"]["coherence_function"]
        assert cf["applies"] is False
        assert cf["intended_relationship"] == ""
        assert cf["level"] == ""
        assert cf["resources_in_use"] == []
        assert cf["reader_can_follow"] == ""

        r = client.patch(
            f"{API}/sessions/{sid}/telos",
            json={"pedagogical_purpose": "Help the student communicate clear relationships among ideas.",
                  "note": "TEST_M9 telos edit"},
            timeout=30,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["pedagogical_purpose"] == (
            "Help the student communicate clear relationships among ideas."
        )
        assert body["telos"]["governing_pedagogical_purpose"] == (
            "Help the student communicate clear relationships among ideas."
        )

    def test_get_nonexistent(self, client):
        r = client.get(f"{API}/sessions/does-not-exist-m9-{int(time.time())}", timeout=15)
        assert r.status_code == 404
