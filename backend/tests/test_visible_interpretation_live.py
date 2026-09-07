"""
Live e2e tests for Compass 3.0 Visible Interpretation + Negotiated Understanding.

Verifies:
  - After a 'writing' interact, the completed AI turn exposes
    focus_of_work, non-empty focus_region, focus_portion (verbatim
    substrings of the learner's paragraph) and function_spans (dict
    mapping structural names to verbatim quotes).
  - After a 'answer' interact carrying a learner challenge, the challenge
    does NOT overwrite the draft, the coaching content is not a
    verbatim repeat of the prior invitation, and the last trace record
    shows functional_decision.reconsideration.outcome in
    {revised, explained, narrowed} with a non-empty reread.
  - Coaching content is content-neutral (does not literally ask a
    domain/psychology question about the fixed mindset).
"""
import json
import os
import time
from pathlib import Path

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")
if not BASE_URL:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip()
BASE_URL = BASE_URL.rstrip("/")

TRACE_PATH = Path("/app/backend/functional_v3_trace.log")

FIXED_MINDSET_PARAGRAPH = (
    "The fixed mindset is the belief that abilities are carved in stone. "
    "People with a fixed mindset believe their intelligence and talent cannot change. "
    "For example, a student who thinks they are bad at math will not try harder because "
    "they believe effort cannot change their ability. The same goes for sports: someone "
    "who thinks they are not athletic will avoid trying new sports."
)

CHALLENGE = (
    "I already elaborated on that — I explained it with the carved-in-stone example "
    "and the math and sports examples."
)

DOMAIN_QUESTION_MARKERS = [
    "why do people with a fixed mindset",
    "why do people with fixed mindset",
    "why does the fixed mindset",
    "why is the fixed mindset",
    "what causes people with a fixed mindset",
    "what makes people with a fixed mindset",
]

REWRITE_MARKERS = [
    "here is your",
    "here's your",
    "here is a revised",
    "rewritten version",
    "revised version:",
    "revised paragraph:",
]


@pytest.fixture(scope="module")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _create_session(api):
    payload = {
        "assignment": "What is the fixed mindset?",
        "pedagogical_purpose": "Help the learner explain the fixed mindset in their own words.",
        "current_writing_task": "one paragraph",
        "reasoning_mode": "canonical_v2",
    }
    r = api.post(f"{BASE_URL}/api/sessions", json=payload, timeout=30)
    assert r.status_code == 200, f"POST /api/sessions failed: {r.status_code} {r.text}"
    data = r.json()
    assert "id" in data
    return data["id"]


def _poll_last_turn(api, sid, timeout_s=180, interval_s=6):
    deadline = time.time() + timeout_s
    last = None
    doc = None
    while time.time() < deadline:
        r = api.get(f"{BASE_URL}/api/sessions/{sid}", timeout=30)
        assert r.status_code == 200
        doc = r.json()
        turns = doc.get("turns") or []
        if turns:
            last = turns[-1]
            if last.get("role") == "ai" and last.get("status") == "complete":
                return doc, last
        time.sleep(interval_s)
    pytest.fail(f"Timed out ({timeout_s}s). Last turn: {last}")


def _last_trace_record():
    assert TRACE_PATH.exists()
    with TRACE_PATH.open() as f:
        lines = [ln.strip() for ln in f.readlines() if ln.strip()]
    assert lines
    line = lines[-1]
    brace = line.find("{")
    assert brace >= 0, line
    return json.loads(line[brace:])


def _norm(s: str) -> str:
    """Normalize whitespace for verbatim comparison."""
    return " ".join((s or "").split())


class TestVisibleInterpretation:
    """Sprint N: visible interpretation + negotiated understanding."""

    def test_00_health(self, api):
        r = api.get(f"{BASE_URL}/api/", timeout=15)
        assert r.status_code == 200

    def test_01_visible_interpretation_spans(self, api, request):
        sid = _create_session(api)
        request.config._vi_sid = sid
        request.config._vi_paragraph = FIXED_MINDSET_PARAGRAPH

        r = api.post(
            f"{BASE_URL}/api/sessions/{sid}/interact",
            json={"content": FIXED_MINDSET_PARAGRAPH, "kind": "writing"},
            timeout=15,
        )
        assert r.status_code == 200, r.text

        doc, last = _poll_last_turn(api, sid, timeout_s=180)

        # focus_of_work
        focus = last.get("focus_of_work") or ""
        assert focus in ("Elaboration", "Organization", "Thesis"), (
            f"unexpected focus_of_work: {focus!r}"
        )

        # focus_region / focus_portion: verbatim substrings of learner paragraph
        normalized_paragraph = _norm(FIXED_MINDSET_PARAGRAPH)
        focus_region = (last.get("focus_region") or "").strip()
        focus_portion = (last.get("focus_portion") or "").strip()
        assert focus_region, f"focus_region empty. turn={last}"
        assert focus_portion, f"focus_portion empty. turn={last}"
        assert _norm(focus_region) in normalized_paragraph, (
            f"focus_region not a verbatim substring of paragraph.\n"
            f"focus_region={focus_region!r}"
        )
        assert _norm(focus_portion) in normalized_paragraph, (
            f"focus_portion not a verbatim substring of paragraph.\n"
            f"focus_portion={focus_portion!r}"
        )

        # function_spans: dict of structural name -> verbatim quote
        spans = last.get("function_spans")
        assert isinstance(spans, dict) and spans, (
            f"function_spans missing / not a dict: {spans!r}"
        )
        allowed_tokens = {"thesis", "elaboration", "evidence", "example", "opening", "conclusion"}
        for name, quote in spans.items():
            name_lc = (name or "").lower()
            assert any(tok in name_lc for tok in allowed_tokens), (
                f"unexpected span name: {name!r}"
            )
            assert isinstance(quote, str) and quote.strip(), (
                f"span quote empty for {name!r}"
            )
            assert _norm(quote) in normalized_paragraph, (
                f"span {name!r} is not a verbatim substring.\nquote={quote!r}"
            )

        # content-neutrality: coaching invitation must not literally ask a
        # discipline/psychology question about the topic
        content = (last.get("content") or "").strip().lower()
        assert len(content) > 20
        for m in DOMAIN_QUESTION_MARKERS:
            assert m not in content, (
                f"coaching content asked a content-loaded question (marker: {m!r}).\n"
                f"content: {content[:400]}"
            )
        for rw in REWRITE_MARKERS:
            assert rw not in content, f"content appears to rewrite (marker: {rw!r})"

        # stash the invitation for the challenge test
        request.config._vi_prev_invitation = last.get("content") or ""

    def test_02_reconsideration_on_challenge(self, api, request):
        sid = getattr(request.config, "_vi_sid", None)
        paragraph = getattr(request.config, "_vi_paragraph", None)
        prev_inv = getattr(request.config, "_vi_prev_invitation", "") or ""
        assert sid and paragraph, "prerequisite test_01 did not run"

        # snapshot turns before challenge
        r0 = api.get(f"{BASE_URL}/api/sessions/{sid}", timeout=15)
        assert r0.status_code == 200
        turns_before = r0.json().get("turns") or []
        # find the draft student turn (kind == 'writing')
        draft_before = None
        for t in turns_before:
            if t.get("role") == "student" and (
                t.get("kind") == "writing" or _norm(paragraph) in _norm(t.get("content") or "")
            ):
                draft_before = t
        assert draft_before is not None, "could not locate draft student turn before challenge"

        # send answer (challenge)
        r = api.post(
            f"{BASE_URL}/api/sessions/{sid}/interact",
            json={"content": CHALLENGE, "kind": "answer"},
            timeout=15,
        )
        assert r.status_code == 200, r.text

        doc, last = _poll_last_turn(api, sid, timeout_s=180)

        # (a) draft must still be present, unchanged
        turns_after = doc.get("turns") or []
        found_draft = False
        for t in turns_after:
            if t.get("role") == "student" and _norm(paragraph) in _norm(t.get("content") or ""):
                found_draft = True
                break
        assert found_draft, (
            "The fixed-mindset draft is no longer present in the session turns — "
            "an 'answer' turn should NOT overwrite the draft."
        )

        # (b) new coaching content should not verbatim-repeat previous invitation
        new_content = (last.get("content") or "").strip()
        assert len(new_content) > 20, f"empty reconsideration: {new_content!r}"
        assert _norm(new_content) != _norm(prev_inv), (
            "Reconsideration content is a verbatim repeat of the previous invitation."
        )

        # (c) trace record: reconsideration outcome + reread
        rec = _last_trace_record()
        fd = rec.get("functional_decision") or {}
        recon = fd.get("reconsideration") or rec.get("reconsideration") or {}
        assert isinstance(recon, dict) and recon, (
            f"reconsideration missing from trace. functional_decision keys: {sorted(fd.keys())}"
        )
        outcome = recon.get("outcome")
        assert outcome in ("revised", "explained", "narrowed"), (
            f"reconsideration.outcome unexpected: {outcome!r} (full: {recon})"
        )
        reread = recon.get("reread")
        assert isinstance(reread, str) and reread.strip(), (
            f"reconsideration.reread empty: {reread!r}"
        )
