"""Milestone 10 backend acceptance — Functional Conclusion Framework.

Verifies:
  (a) When an ending is submitted, theory.conclusion_function.applies=True and
      completes_purpose is populated (functions_in_play may be present).
  (b) Effective conclusion — honored; the invitation does NOT prescribe restructuring
      into 'In conclusion...' / 'restate your thesis' / 'summarize all your points'.
  (c) Merely-stops ending — diagnosed as stopping-not-completing (completes_purpose
      names the gap).
  (d) Only-summarizes — treated as NOT completion; engine does NOT tell the student
      to restate the thesis / start with 'In conclusion'.
  (e) Introduces-new-idea — flagged as a completion problem; AI does NOT supply
      or encourage the new content (M5A).
  (f) NO formulaic-conclusion phrasing in any invitation.
  (g) intervention.focus=='writing' + writing_not_content_check populated.
  (h) M6/M7/M8/M9 regression fields populated when applicable.
  (i) Multi-turn writing->revise->answer preserves theory_history v1..vN.

Run:  pytest /app/backend/tests/test_milestone10_conclusion_function.py -v -n 0 -s
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

# Formulaic-conclusion phrasing the engine must AVOID prescribing.
RULE_FLAG_PATTERNS = [
    r"start (?:it |the conclusion |your conclusion )?with ['\"]?in conclusion",
    r"use ['\"]?in conclusion['\"]?",
    r"begin (?:it |the conclusion |your conclusion )?with ['\"]?(?:in conclusion|to conclude|in summary|in closing)",
    r"\brestate (?:your |the )?thesis\b",
    r"\brepeat (?:your |the )?thesis\b",
    r"\bsummarize (?:all |each of )?your (?:points|reasons|paragraphs)\b",
    r"\brestate (?:all |each of )?your (?:points|main points|reasons)\b",
    r"\byou (?:need|should|must) (?:to )?summarize\b",
    r"\bremind the reader of (?:all )?your (?:points|reasons)\b",
]
RULE_RES = [re.compile(p, re.IGNORECASE) for p in RULE_FLAG_PATTERNS]

# Content-coaching red flags (M5A anti-coauthoring).
CONTENT_REDFLAGS = [
    r"\byou\s+(?:could|might|should)\s+add\s+(?:a|an|the|another)\s+(?:point|idea|argument|reason|example|claim)\b",
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


def _concl(s):
    return s["theory"]["conclusion_function"]


def _cf(s):
    return s["theory"]["coherence_function"]


def _pf(s):
    return s["theory"]["paragraph_function"]


def _ef(s):
    return s["theory"]["evidence_function"]


def _cp(s):
    return s["theory"]["communicative_purpose"]


def _assert_common_shape(s, weak_text=None):
    assert s.get("_saw_done_event") is True, "must see event: done"
    assert s.get("_elapsed_seconds", 999) < 180, (
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
    cp = _cp(s)
    assert cp.get("primary", "").strip() != ""

    concl = _concl(s)
    assert isinstance(concl, dict) and "applies" in concl and "completes_purpose" in concl
    return iv, inv, cp, concl


ARG = "TEST_M10 Argue whether social media improves or harms teen friendships."
PA = "Help the student write a conclusion that completes the essay's communicative purpose."
TASK_CONCL = "Draft your conclusion."


# ==========================================================================
# 1. Effective conclusion — honored; completion move recognized;
#    invitation must NOT prescribe restate-thesis / 'In conclusion'.
# ==========================================================================
class TestEffectiveConclusion:
    def test_effective_conclusion_honored_no_formulaic_rules(self, client):
        sid = _new_session(client, ARG, PA, TASK_CONCL)
        draft = (
            "So the danger was never that teens would stop talking — it's that "
            "constant contact can feel like closeness while quietly replacing it. "
            "What's worth protecting isn't the number of friends onscreen, but the "
            "few we still make time to be fully present with."
        )
        status, data, err = sse_interact_with_retry(
            client, sid, {"kind": "writing", "content": draft}
        )
        assert status == 200 and err is None and data is not None, f"err={err}"
        iv, inv, cp, concl = _assert_common_shape(data, weak_text=draft)

        # applies + completes_purpose populated
        assert concl["applies"] is True, (
            f"conclusion_function.applies MUST be True on ending submission, got {concl!r}"
        )
        cp_str = (concl.get("completes_purpose") or "").strip()
        assert cp_str != "", f"completes_purpose MUST be populated, got {concl!r}"

        # No formulaic-rule phrasing
        rf = _rule_flags(inv)
        assert not rf, f"formulaic phrasing found: {rf} | inv={inv!r}"

        # M5A boundary
        assert iv["focus"] == "writing"
        assert iv["writing_not_content_check"].strip() != ""
        contf = _content_flags(inv)
        assert not contf, f"content-coaching phrasing: {contf} | inv={inv!r}"

        print(
            f"EFFECTIVE applies={concl['applies']} cp={cp_str[:60]!r} "
            f"funcs={concl.get('functions_in_play')!r}"
        )


# ==========================================================================
# 2. Merely-stops — diagnosed as stopping-not-completing.
# ==========================================================================
class TestMerelyStops:
    def test_merely_stops_diagnosed(self, client):
        sid = _new_session(client, ARG, PA, TASK_CONCL)
        draft = "And that is my third reason why social media harms friendships. The end."
        status, data, err = sse_interact_with_retry(
            client, sid, {"kind": "writing", "content": draft}
        )
        assert status == 200 and err is None and data is not None, f"err={err}"
        iv, inv, cp, concl = _assert_common_shape(data, weak_text=draft)

        assert concl["applies"] is True
        cp_str = (concl.get("completes_purpose") or "").strip().lower()
        assert cp_str != "", f"completes_purpose empty, got {concl!r}"

        # Should recognize it stops rather than completes.
        stop_markers = ["stop", "does not complete", "not complete",
                        "doesn't complete", "no synthesis", "no completion",
                        "merely mark", "ends without", "no insight",
                        "not synthes", "without complet"]
        assert any(m in cp_str for m in stop_markers), (
            f"engine should diagnose stopping-not-completing, got completes_purpose={cp_str!r}"
        )

        rf = _rule_flags(inv)
        assert not rf, f"formulaic phrasing: {rf} | inv={inv!r}"
        assert iv["focus"] == "writing"
        assert iv["writing_not_content_check"].strip() != ""
        contf = _content_flags(inv)
        assert not contf, f"content-coaching: {contf} | inv={inv!r}"
        print(f"MERELY_STOPS cp={cp_str[:80]!r}")


# ==========================================================================
# 3. Only-summarizes — treated as NOT completion; engine does NOT tell the
#    student to restate the thesis or start with 'In conclusion'.
# ==========================================================================
class TestOnlySummarizes:
    def test_only_summarizes_treated_as_not_completion(self, client):
        sid = _new_session(client, ARG, PA, TASK_CONCL)
        draft = (
            "In conclusion, social media is distracting, it is fake, and it is "
            "addictive. As I said, these are my three reasons that social media "
            "harms friendships."
        )
        status, data, err = sse_interact_with_retry(
            client, sid, {"kind": "writing", "content": draft}
        )
        assert status == 200 and err is None and data is not None, f"err={err}"
        iv, inv, cp, concl = _assert_common_shape(data, weak_text=draft)

        assert concl["applies"] is True
        cp_str = (concl.get("completes_purpose") or "").strip().lower()
        assert cp_str != "", f"completes_purpose empty, got {concl!r}"

        # Restating points must NOT be treated as completion.
        not_completion_markers = ["not complete", "does not complete", "doesn't complete",
                                  "restat", "lists", "summar", "without complet",
                                  "no synthesis", "not synthes", "does not synth",
                                  "stops rather than", "recap", "does not integrate",
                                  "not comple"]
        assert any(m in cp_str for m in not_completion_markers), (
            f"engine should treat summary as NOT completion, got completes_purpose={cp_str!r}"
        )

        # The invitation MUST NOT tell the student to restate the thesis or use 'In conclusion'.
        rf = _rule_flags(inv)
        assert not rf, f"formulaic phrasing found: {rf} | inv={inv!r}"

        assert iv["focus"] == "writing"
        assert iv["writing_not_content_check"].strip() != ""
        contf = _content_flags(inv)
        assert not contf, f"content-coaching: {contf} | inv={inv!r}"
        print(f"ONLY_SUMMARIZES cp={cp_str[:100]!r}")


# ==========================================================================
# 4. Introduces-new-idea — flagged as completion problem; AI does NOT supply
#    or encourage the new content (M5A).
# ==========================================================================
class TestIntroducesNewIdea:
    def test_new_idea_flagged_ai_does_not_encourage_new_content(self, client):
        sid = _new_session(client, ARG, PA, TASK_CONCL)
        draft = (
            "In the end, social media harms friendships. Also, we should talk "
            "about how it affects sleep, and the economy, and whether phones "
            "cause bad eyesight, which are big topics too."
        )
        status, data, err = sse_interact_with_retry(
            client, sid, {"kind": "writing", "content": draft}
        )
        assert status == 200 and err is None and data is not None, f"err={err}"
        iv, inv, cp, concl = _assert_common_shape(data, weak_text=draft)

        assert concl["applies"] is True
        cp_str = (concl.get("completes_purpose") or "").strip().lower()
        assert cp_str != "", f"completes_purpose empty, got {concl!r}"

        # Should recognize the fracture (new material introduced at the end).
        new_markers = ["new", "unrelated", "opens", "introduces", "fracture",
                       "unfinished", "outside", "beyond", "off-topic",
                       "off topic", "expands", "veer", "digress",
                       "doesn't complete", "does not complete", "different topic"]
        assert any(m in cp_str for m in new_markers), (
            f"engine should flag new-idea introduction, got completes_purpose={cp_str!r}"
        )

        # M5A — the AI must NOT elaborate on sleep/economy/eyesight or encourage them.
        inv_low = inv.lower()
        # If the AI mentioned any of the new topics, it should only be to name them as
        # off-topic — not to elaborate. A hard test: don't let the AI encourage
        # developing sleep/economy/eyesight as a next step.
        bad_encouragements = [
            r"\b(?:you (?:could|should|might) (?:explore|develop|discuss|write about))\s+(?:sleep|economy|eyesight)",
            r"\bmore about (?:sleep|the economy|eyesight)\b",
            r"\bexpand on (?:sleep|the economy|eyesight)\b",
        ]
        for pat in bad_encouragements:
            assert not re.search(pat, inv_low), (
                f"AI encouraged NEW content — pattern {pat!r} found in inv={inv[:200]!r}"
            )

        rf = _rule_flags(inv)
        assert not rf, f"formulaic phrasing: {rf} | inv={inv!r}"

        assert iv["focus"] == "writing"
        assert iv["writing_not_content_check"].strip() != ""
        contf = _content_flags(inv)
        assert not contf, f"content-coaching: {contf} | inv={inv!r}"
        print(f"NEW_IDEA cp={cp_str[:100]!r}")


# ==========================================================================
# 5. Multi-turn regression — theory_history v1..vN preserved,
#    currently_relevant_domains stays 1..3, focus='writing' every turn.
# ==========================================================================
class TestMultiTurnRegression:
    def test_multi_turn_theory_history_and_domains(self, client):
        sid = _new_session(client, ARG, PA, TASK_CONCL)

        # Turn 1 — merely-stops ending
        d1_text = "And that is my third reason. The end."
        s1, d1, e1 = sse_interact_with_retry(
            client, sid, {"kind": "writing", "content": d1_text}
        )
        assert s1 == 200 and e1 is None and d1 is not None, f"err={e1}"
        iv1, inv1, cp1, concl1 = _assert_common_shape(d1, weak_text=d1_text)
        assert concl1["applies"] is True
        rel1_dom = d1["theory"]["currently_relevant_domains"]
        assert 1 <= len(rel1_dom) <= 3

        # Turn 2 — a real revision that completes the piece
        revised = (
            "The bigger point is not that phones ruin every friendship, but that "
            "constant contact can feel like closeness while quietly replacing it. "
            "What's worth protecting is the few we still make time to be fully "
            "present with — the ones we choose to be gone from, so we can return."
        )
        s2, d2, e2 = sse_interact_with_retry(
            client, sid, {"kind": "revise", "content": revised}
        )
        assert s2 == 200 and e2 is None and d2 is not None, f"err={e2}"
        iv2, inv2, cp2, concl2 = _assert_common_shape(d2, weak_text=revised)

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
                          "content": "I rewrote the ending to complete the argument rather than just stop it — the last sentence names what the reader should be left with."},
        )
        assert s3 == 200 and e3 is None and d3 is not None, f"err={e3}"
        iv3, inv3, cp3, concl3 = _assert_common_shape(d3)
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
            assert not rf, f"turn {i} formulaic phrasing: {rf}"

        print(
            f"MULTITURN t1 type={iv1['type']} c1.applies={concl1['applies']} "
            f"t2 type={iv2['type']} c2.applies={concl2['applies']} "
            f"t3 type={iv3['type']} c3.applies={concl3['applies']}"
        )


# ==========================================================================
# 6. M6/M7/M8/M9 regression on a supported paragraph draft (non-conclusion task).
# ==========================================================================
class TestM6M7M8M9Regression:
    def test_paragraph_with_support_preserves_prior_frameworks(self, client):
        sid = _new_session(
            client, ARG,
            "Help the student develop a supported paragraph.",
            "Draft a body paragraph.",
        )
        draft = (
            "Teens check their phones an average of 100 times a day, according to "
            "a 2023 study. That constant checking matters because it turns "
            "friendships into a habit of monitoring rather than sustained "
            "attention. Because attention builds intimacy, and monitoring "
            "interrupts it, friendships that live only through phones grow thin."
        )
        status, data, err = sse_interact_with_retry(
            client, sid, {"kind": "writing", "content": draft}
        )
        assert status == 200 and err is None and data is not None, f"err={err}"
        iv, inv, cp, concl = _assert_common_shape(data, weak_text=draft)

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
        # M9 — coherence should be recognized as a feature of this draft
        cf = _cf(data)
        assert cf["applies"] is True, f"M9 coherence_function.applies expected True, got {cf!r}"

        # M10 conclusion_function should NOT apply on a body-paragraph draft.
        # (A body paragraph is not an ending — engine should keep applies=false.)
        # Soft assertion: warn if applies=true here.
        if concl["applies"]:
            print(f"WARN: conclusion_function.applies=True on body-paragraph draft: {concl!r}")

        rf = _rule_flags(inv)
        assert not rf, f"formulaic phrasing: {rf}"
        assert iv["focus"] == "writing"
        print(
            f"REG_M6/M7/M8/M9 cp={cp['primary'][:30]!r} pf.applies={pf['applies']} "
            f"ef.applies={ef['applies']} cf.applies={cf['applies']} "
            f"concl.applies={concl['applies']}"
        )


# ==========================================================================
# 7. Fast smoke — CRUD + PATCH telos + default conclusion_function shape.
# ==========================================================================
class TestSessionCrud:
    def test_create_get_patch_default_concl(self, client):
        sid = _new_session(
            client,
            assignment="TEST_M10 crud smoke",
            purpose="Help the student complete the essay.",
            task="Draft your conclusion.",
        )
        g = client.get(f"{API}/sessions/{sid}", timeout=15)
        assert g.status_code == 200
        assert g.json()["id"] == sid
        concl = g.json()["theory"]["conclusion_function"]
        assert concl["applies"] is False
        assert concl["completes_purpose"] == ""
        assert concl["functions_in_play"] == []
        assert concl["relationship_to_opening"] == ""
        assert concl["final_understanding"] == ""

        r = client.patch(
            f"{API}/sessions/{sid}/telos",
            json={"pedagogical_purpose": "Help the student complete the essay's purpose.",
                  "note": "TEST_M10 telos edit"},
            timeout=30,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["pedagogical_purpose"] == (
            "Help the student complete the essay's purpose."
        )
        assert body["telos"]["governing_pedagogical_purpose"] == (
            "Help the student complete the essay's purpose."
        )

    def test_get_nonexistent(self, client):
        r = client.get(f"{API}/sessions/does-not-exist-m10-{int(time.time())}", timeout=15)
        assert r.status_code == 404
