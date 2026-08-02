"""Milestone 12 backend acceptance — Reader Construction Framework.

Verifies (per review request):
  (a) Whenever a draft exists, theory.reader_construction.applies==true and
      reader_understanding is non-empty.
  (b) Misunderstandings are flagged in the reader model:
        - hidden-assumption draft populates assumed_knowledge (distinguishing
          reasonable inference vs unsupported assumption).
        - ambiguous draft populates precision_risk.
        - inferential-gap draft populates elaboration_needed OR clarification_needed.
  (c) Precision is taught as shared reader understanding, NOT grammar — the
      invitation for an ambiguous draft must NOT mention grammar/punctuation/
      spelling/comma-splices. Elaboration must NOT be framed as 'add more words'.
  (d) M11 still governs: every turn scaffolding_control.primary_target is
      non-empty (exactly ONE target) even though reader_construction adds a lens.
  (e) The reader model EVOLVES: in a two-turn writing->revise where the revision
      adds detail, reader_construction.reader_understanding changes between turns.
  (f) M6-M11 regression: on a supported body paragraph, cp.primary is populated;
      pf/ef/cf.applies=true; scaffolding_control populated; reader_construction
      also populated (applies + reader_understanding).
  (g) M1-M5A regression: multi-turn writing->revise preserves theory_history
      v1..vN (prior versions not overwritten); currently_relevant_domains 1-3;
      intervention.focus='writing'; writing_not_content_check non-empty; no
      invented content ('you could add', 'another reason'); no stage/grade/level.
  (h) CRUD: POST returns id; GET persists; PATCH /telos updates pedagogical_purpose;
      GET nonexistent -> 404. Default GET has reader_construction empty shape.

Run:  pytest /app/backend/tests/test_milestone12_reader_construction.py -v -n 0 -s
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
    "interpretation_only", "instruct_then_invite", "invite_only",
    "consolidate", "postpone_instruction",
}
VALID_MODES = {
    "developmental_question", "explicit_instruction", "brief_demonstration",
    "guided_revision", "reflection", "consolidation",
}
VALID_CYCLE_STATUSES = {"continue", "consolidate_and_return", "stop"}

STAGE_SCORE_PATTERNS = [
    r"\bstage\s*\d\b", r"\blevel\s*\d\b", r"\bgrade\s*\d\b",
    r"\b\d+\s*/\s*10\b", r"\b\d+\s*out\s*of\s*10\b",
    r"\bscore[sd]?\b\s*\d", r"\brubric\b",
]

# Content-coaching red flags (M5A): the AI must not invent content.
CONTENT_FLAGS = [
    r"you (?:could|might|should) add (?:a|an|the|another) (?:point|idea|argument|reason|example|fact)",
    r"another (?:reason|argument|point|idea|example|fact)",
    r"consider (?:adding|including|mentioning) (?:the|a|an)",
    r"for example,? you could",
    r"try adding (?:a|an|the)",
]

# Grammar-correctness phrasing (precision must NOT reduce to grammar).
GRAMMAR_FLAGS = [
    r"grammatically (?:correct|incorrect)",
    r"fix the grammar",
    r"comma splice",
    r"subject[- ]verb agreement",
    r"punctuation error",
    r"correct the tense",
    r"spelling (?:error|mistake)",
]

# Word-count / more-words framing (elaboration must NOT reduce to length).
WORDCOUNT_FLAGS = [
    r"\badd more words\b",
    r"\bmake it longer\b",
    r"\bwrite more\b(?! about)",  # allow "write more about X"
    r"\bincrease (?:the )?length\b",
    r"\bwrite a longer\b",
]

def _flags(text, patterns):
    low = text.lower()
    return [p for p in patterns if re.search(p, low)]


def _has_stage_score(text):
    return bool(_flags(text, STAGE_SCORE_PATTERNS))


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
    for _ in range(2):
        if status == 200 and data is None and err is None:
            time.sleep(3)
            status, data, err = sse_interact(client, sid, payload, timeout)
        else:
            break
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


def _rc(s):
    return s["theory"].get("reader_construction", {}) or {}


def _sc(s):
    return s["theory"].get("scaffolding_control", {}) or {}


def _cp(s):
    return s["theory"].get("communicative_purpose", {}) or {}


def _last_ai(s):
    return s["turns"][-1]["content"]


def _last_iv(s):
    return s["interactions"][-1]["intervention"]


def _assert_common(s, weak_text=None):
    assert s.get("_saw_done_event") is True, "must see event: done"
    assert s.get("_elapsed_seconds", 999) < 180, f"turn too long: {s.get('_elapsed_seconds')}s"
    ai = [t for t in s["turns"] if t["role"] == "ai"]
    stu = [t for t in s["turns"] if t["role"] == "student"]
    assert s["turns"][-1]["role"] == "ai"
    assert len(ai) == len(stu) == len(s["interactions"]), "exactly one AI turn per interact"
    inv = _last_ai(s)
    if weak_text is not None:
        assert weak_text not in inv, "AI must not echo/rewrite student's text"
    assert not _has_stage_score(inv), f"stage/level/rubric leaked: {inv[:200]}"
    assert _last_iv(s)["type"] in VALID_INTERVENTION_TYPES
    return inv


def _assert_scaffolding_ok(s):
    sc = _sc(s)
    assert (sc.get("primary_target") or "").strip(), f"primary_target must be non-empty (M11): {sc!r}"
    assert (sc.get("instructional_mode") or "").strip() in VALID_MODES, sc
    assert (sc.get("cycle_status") or "").strip() in VALID_CYCLE_STATUSES, sc
    return sc


def _assert_reader_applies(s):
    rc = _rc(s)
    assert rc.get("applies") is True, f"reader_construction.applies must be True when draft exists: {rc!r}"
    assert (rc.get("reader_understanding") or "").strip(), f"reader_understanding must be non-empty: {rc!r}"
    return rc


# --------------------------------------------------------------------------
# 1) CRUD smoke — POST returns id, GET persists (with empty reader_construction),
#    PATCH /telos updates pedagogical_purpose, GET nonexistent -> 404.
# --------------------------------------------------------------------------
class TestCRUDAndDefaults:
    def test_crud_and_default_reader_construction(self, client):
        sid = _new_session(
            client,
            assignment="TEST_M12 assignment — argue whether social media harms teen friendships.",
            purpose="TEST_M12 — help the student communicate clearly to a naive reader.",
            task="TEST_M12 — draft your essay.",
        )
        # GET persists
        r = client.get(f"{API}/sessions/{sid}", timeout=15)
        assert r.status_code == 200
        s = r.json()
        assert s["id"] == sid
        # Default reader_construction shape (empty)
        rc = s["theory"].get("reader_construction")
        assert isinstance(rc, dict), rc
        assert rc.get("applies") is False
        for k in ("reader_understanding", "assumed_knowledge", "clarification_needed",
                  "elaboration_needed", "precision_risk", "next_reader_need"):
            assert rc.get(k) == "" or rc.get(k) is None, f"{k!r} should default empty: {rc.get(k)!r}"
        assert rc.get("likely_reader_questions") in ([], None)

        # PATCH /telos updates pedagogical_purpose
        new_purpose = "TEST_M12 UPDATED purpose — communicate a clear claim to a naive reader."
        r = client.patch(f"{API}/sessions/{sid}/telos", json={"pedagogical_purpose": new_purpose}, timeout=15)
        assert r.status_code == 200, r.text
        assert r.json()["pedagogical_purpose"] == new_purpose
        # Verify persisted
        r2 = client.get(f"{API}/sessions/{sid}", timeout=15)
        assert r2.json()["pedagogical_purpose"] == new_purpose

    def test_get_nonexistent_returns_404(self, client):
        r = client.get(f"{API}/sessions/does-not-exist-m12", timeout=15)
        assert r.status_code == 404


# --------------------------------------------------------------------------
# 2) Hidden-assumption draft (Gatsby / green light) — assumed_knowledge populated.
# --------------------------------------------------------------------------
class TestHiddenAssumption:
    def test_hidden_assumption_populates_assumed_knowledge(self, client):
        sid = _new_session(
            client,
            assignment="TEST_M12 — Analyze how a text produces its effect.",
            purpose="Help the student communicate to a reader who knows only what the text has said.",
            task="Draft your essay.",
        )
        draft = ("As everyone knows, the green light obviously symbolizes what Gatsby was "
                 "reaching for, which proves the novel's whole point about America.")
        status, s, err = sse_interact_with_retry(client, sid, {"kind": "writing", "content": draft})
        assert status == 200 and s is not None, f"SSE failed: err={err}"

        inv = _assert_common(s, weak_text=draft)
        sc = _assert_scaffolding_ok(s)  # M11 still governs
        rc = _assert_reader_applies(s)  # M12 applies + reader_understanding

        # Hidden-assumption case: assumed_knowledge must be populated.
        ak = (rc.get("assumed_knowledge") or "").strip()
        assert ak, f"assumed_knowledge must be non-empty for hidden-assumption draft: rc={rc!r}"

        # M5A intact — focus=writing, writing_not_content_check populated, no content invention.
        iv = _last_iv(s)
        assert iv.get("focus") == "writing", iv
        assert (iv.get("writing_not_content_check") or "").strip(), iv
        cf = _flags(inv, CONTENT_FLAGS)
        assert not cf, f"content-coaching flag(s) in invitation: {cf} | {inv[:300]}"

        print(f"\n[hidden-assumption] target={sc.get('primary_target')[:50]!r} "
              f"assumed_knowledge={ak[:80]!r}")


# --------------------------------------------------------------------------
# 3) Ambiguous draft — precision_risk populated; invitation NOT framed as grammar.
# --------------------------------------------------------------------------
class TestAmbiguousPrecision:
    def test_ambiguous_populates_precision_risk_and_not_grammar(self, client):
        sid = _new_session(
            client,
            assignment="TEST_M12 — Argue whether social media improves or harms teen friendships.",
            purpose="Help the student communicate clearly to a naive reader.",
            task="Draft your essay.",
        )
        draft = "Social media makes people feel connected, which is the problem."
        status, s, err = sse_interact_with_retry(client, sid, {"kind": "writing", "content": draft})
        assert status == 200 and s is not None, f"SSE failed: err={err}"

        inv = _assert_common(s, weak_text=draft)
        sc = _assert_scaffolding_ok(s)
        rc = _assert_reader_applies(s)

        pr = (rc.get("precision_risk") or "").strip()
        assert pr, f"precision_risk must be non-empty for ambiguous draft: rc={rc!r}"

        # Invitation must NOT be framed as grammar/punctuation/spelling.
        gf = _flags(inv, GRAMMAR_FLAGS)
        assert not gf, f"grammar-framing leaked in ambiguous-precision invitation: {gf} | {inv[:300]}"

        # M5A intact
        iv = _last_iv(s)
        assert iv.get("focus") == "writing", iv
        assert (iv.get("writing_not_content_check") or "").strip(), iv

        print(f"\n[ambiguous] target={sc.get('primary_target')[:50]!r} "
              f"precision_risk={pr[:80]!r}")


# --------------------------------------------------------------------------
# 4) Inferential-gap draft — elaboration_needed OR clarification_needed populated;
#    invitation NOT framed as 'add more words'.  Also spot-checks M11 + M5A.
# --------------------------------------------------------------------------
class TestInferentialGap:
    def test_inferential_gap_populates_elaboration_or_clarification(self, client):
        sid = _new_session(
            client,
            assignment="TEST_M12 — Argue whether social media improves or harms teen friendships.",
            purpose="Help the student communicate clearly to a naive reader.",
            task="Draft your essay.",
        )
        draft = "Teens check their phones constantly. Therefore they no longer value their close friends."
        status, s, err = sse_interact_with_retry(client, sid, {"kind": "writing", "content": draft})
        assert status == 200 and s is not None, f"SSE failed: err={err}"

        inv = _assert_common(s, weak_text=draft)
        sc = _assert_scaffolding_ok(s)
        rc = _assert_reader_applies(s)

        el = (rc.get("elaboration_needed") or "").strip()
        cl = (rc.get("clarification_needed") or "").strip()
        assert el or cl, f"elaboration_needed OR clarification_needed must be non-empty: rc={rc!r}"

        # Elaboration must NOT be framed as 'add more words'.
        wf = _flags(inv, WORDCOUNT_FLAGS)
        assert not wf, f"elaboration was framed as word-count/length: {wf} | {inv[:300]}"

        # No invented content.
        cf = _flags(inv, CONTENT_FLAGS)
        assert not cf, f"content-coaching flag(s) in invitation: {cf} | {inv[:300]}"

        # M5A intact
        iv = _last_iv(s)
        assert iv.get("focus") == "writing", iv

        print(f"\n[inferential-gap] target={sc.get('primary_target')[:50]!r} "
              f"elaboration_needed={el[:60]!r} clarification_needed={cl[:60]!r}")


# --------------------------------------------------------------------------
# 5) Multi-turn evolving reader model + theory_history + M1-M5A regression.
#    writing -> revise (adds detail); reader_understanding must change; theory
#    history v1 + v2 preserved (v1 not overwritten); domains 1-3; focus=writing.
# --------------------------------------------------------------------------
class TestEvolvingReaderModel:
    def test_reader_model_evolves_across_turns(self, client):
        sid = _new_session(
            client,
            assignment="TEST_M12 — Explain how a chosen process works to a naive reader.",
            purpose="Help the student communicate clearly to a reader who knows only what the text says.",
            task="Draft your essay.",
        )
        draft1 = "Photosynthesis is how plants make food."
        status1, s1, err1 = sse_interact_with_retry(client, sid, {"kind": "writing", "content": draft1})
        assert status1 == 200 and s1 is not None, f"turn1 SSE failed: err={err1}"
        _assert_common(s1, weak_text=draft1)
        sc1 = _assert_scaffolding_ok(s1)
        rc1 = _assert_reader_applies(s1)
        ru1 = rc1["reader_understanding"].strip()

        draft2 = ("Photosynthesis is how plants make food. Inside the leaf, chloroplasts "
                  "capture sunlight and use it to combine water and carbon dioxide into "
                  "sugar, releasing oxygen as a byproduct.")
        status2, s2, err2 = sse_interact_with_retry(client, sid, {"kind": "revise", "content": draft2})
        assert status2 == 200 and s2 is not None, f"turn2 SSE failed: err={err2}"
        _assert_common(s2, weak_text=draft2)
        sc2 = _assert_scaffolding_ok(s2)
        rc2 = _assert_reader_applies(s2)
        ru2 = rc2["reader_understanding"].strip()

        # (e) Reader model EVOLVES — reader_understanding changes between turns.
        assert ru1 != ru2, (
            f"reader_understanding must evolve when the revision adds new content.\n"
            f"turn1: {ru1!r}\nturn2: {ru2!r}"
        )

        # M1-M5A regression: theory_history v1..vN preserved (v1 not overwritten).
        th = s2.get("theory_history", [])
        assert len(th) >= 2, f"theory_history must have v1..vN across turns: len={len(th)}"
        # Each history entry is {version, telos, theory, created_at}
        v_first, v_last = th[0], th[-1]
        assert isinstance(v_first, dict) and "theory" in v_first and "version" in v_first, v_first
        assert v_first["version"] == 1, f"first history entry should be v1: {v_first.get('version')}"
        assert v_last["version"] >= 2, f"last history entry should be >= v2: {v_last.get('version')}"
        assert "communicative_purpose" in v_first["theory"], v_first["theory"].keys()
        # verify v1 is not literally == v_last (i.e., not overwritten with current state)
        assert v_first["theory"] != v_last["theory"], "theory_history v1 appears overwritten to v_last (identical theory)"

        # currently_relevant_domains 1..3
        dom2 = s2["theory"].get("currently_relevant_domains", []) or []
        assert 1 <= len(dom2) <= 3, f"currently_relevant_domains must be 1..3, got {len(dom2)}: {dom2!r}"

        # M5A on both turns
        for turn_s in (s1, s2):
            iv = _last_iv(turn_s)
            assert iv.get("focus") == "writing", iv
            assert (iv.get("writing_not_content_check") or "").strip(), iv
            inv = _last_ai(turn_s)
            cf = _flags(inv, CONTENT_FLAGS)
            assert not cf, f"content-coaching flag in invitation: {cf} | {inv[:300]}"

        print(f"\n[evolving] ru1={ru1[:80]!r}\n            ru2={ru2[:80]!r}\n"
              f"  target1={sc1.get('primary_target')[:40]!r}  target2={sc2.get('primary_target')[:40]!r}")


# --------------------------------------------------------------------------
# 6) M6-M11 regression on a supported body paragraph: cp.primary populated;
#    paragraph_function/evidence_function/coherence_function .applies=True;
#    scaffolding_control populated; reader_construction also populated.
# --------------------------------------------------------------------------
class TestM6toM11Regression:
    def test_supported_body_paragraph_preserves_all_frameworks(self, client):
        sid = _new_session(
            client,
            assignment="TEST_M12 — Argue whether social media improves or harms teen friendships.",
            purpose="Help the student communicate clearly to a naive reader.",
            task="Draft a body paragraph.",
        )
        # Supported body paragraph — enough substance to trigger pf/ef/cf.applies.
        draft = (
            "Social media damages close friendships because it optimizes for breadth of "
            "contact over depth of attention. For example, a teen may exchange twenty "
            "quick reactions with different acquaintances in a single hour, yet spend no "
            "sustained time with a single close friend that same day. This matters because "
            "close friendship, unlike acquaintance, is built through the kind of focused "
            "attention that quick reactions cannot substitute for; when a platform's "
            "design rewards constant shallow contact, the deep attention that intimate "
            "friendship depends on is quietly displaced."
        )
        status, s, err = sse_interact_with_retry(client, sid, {"kind": "writing", "content": draft})
        assert status == 200 and s is not None, f"SSE failed: err={err}"
        _assert_common(s, weak_text=draft)

        # M6
        cp = _cp(s)
        assert (cp.get("primary") or "").strip(), f"cp.primary must be populated: {cp!r}"
        # M7 / M8 / M9 applies
        th = s["theory"]
        assert th.get("paragraph_function", {}).get("applies") is True, th.get("paragraph_function")
        assert th.get("evidence_function", {}).get("applies") is True, th.get("evidence_function")
        assert th.get("coherence_function", {}).get("applies") is True, th.get("coherence_function")
        # M11
        _assert_scaffolding_ok(s)
        # M12
        rc = _assert_reader_applies(s)

        # M5A intact
        iv = _last_iv(s)
        assert iv.get("focus") == "writing", iv
        assert (iv.get("writing_not_content_check") or "").strip(), iv
        cf = _flags(_last_ai(s), CONTENT_FLAGS)
        assert not cf, f"content-coaching flag in invitation: {cf}"

        print(f"\n[M6-M12 regression] cp.primary={cp.get('primary')!r} "
              f"pf.applies=True ef.applies=True cf.applies=True "
              f"reader_understanding={rc['reader_understanding'][:80]!r}")
