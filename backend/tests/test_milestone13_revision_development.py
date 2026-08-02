"""Milestone 13 backend acceptance — Revision as Development Framework.

Verifies (per review request):
  (a) First submission (no prior draft) -> theory.revision_development.applies==false.
  (b) Substantial-growth revise (writing then a clearly-improved revise) ->
      revision_development.applies==true, development_detected indicates growth
      (starts with "yes"), primary_growth non-empty, transfer_message non-empty.
  (c) Superficial edit (mere word-swap between drafts) -> development_detected
      indicates no/partial (no fabricated growth); remaining_opportunity is
      populated; invitation MUST NOT count edits or praise quantity of revision
      ("you made N changes", "you revised a lot", etc.).
  (d) Regression revise (a strong claim replaced by vague text) -> caught
      (development_detected=='no'), single remaining_opportunity named, invitation
      does NOT re-teach every prior concept.
  (e) M11 still governs: every turn scaffolding_control.primary_target is
      non-empty (one target); intervention.focus=='writing'; no invented content
      or rewritten versions in the invitation.
  (f) M6-M12 preserved on a supported revise turn (cp.primary + pf/ef/cf.applies
      + scaffolding_control + reader_construction populated).
  (g) M1-M5A preserved: multi-turn writing->revise preserves theory_history
      v1..vN (v1 not overwritten); currently_relevant_domains 1-3; every SSE
      turn under 180s cap; writing_not_content_check non-empty.
  (h) CRUD: POST returns id; GET persists; PATCH /telos updates
      pedagogical_purpose; GET nonexistent -> 404. Default revision_development
      empty shape.

Run: pytest /app/backend/tests/test_milestone13_revision_development.py -v -s
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

CONTENT_FLAGS = [
    r"you (?:could|might|should) add (?:a|an|the|another) (?:point|idea|argument|reason|example|fact)",
    r"another (?:reason|argument|point|idea|example|fact)",
    r"consider (?:adding|including|mentioning) (?:the|a|an)",
    r"for example,? you could",
    r"try adding (?:a|an|the)",
]

# Edit-counting / scorekeeping phrasing (revision must NOT be measured in edits).
EDIT_COUNTING_FLAGS = [
    r"you made \d+ (?:changes|edits|revisions)",
    r"you made (?:many|several|a lot of|lots of|numerous) (?:changes|edits|revisions)",
    r"\d+ (?:changes|edits|revisions) made",
    r"you revised a lot",
    r"you did a lot of revising",
    r"lots of edits",
    r"nice (?:job )?(?:on )?(?:the )?(?:many|several) (?:changes|edits|revisions)",
    r"great (?:number|amount) of (?:changes|edits|revisions)",
]


def _flags(text, patterns):
    low = (text or "").lower()
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


def _rd(s):
    return s["theory"].get("revision_development", {}) or {}


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


def _assert_m5a(s):
    iv = _last_iv(s)
    assert iv.get("focus") == "writing", iv
    assert (iv.get("writing_not_content_check") or "").strip(), iv
    cf = _flags(_last_ai(s), CONTENT_FLAGS)
    assert not cf, f"content-coaching flag in invitation: {cf} | {_last_ai(s)[:300]}"


# --------------------------------------------------------------------------
# 1) CRUD + default revision_development shape + first-submission control.
# --------------------------------------------------------------------------
class TestCRUDAndFirstSubmission:
    def test_crud_and_default_revision_development(self, client):
        sid = _new_session(
            client,
            assignment="TEST_M13 — argue whether social media harms teen friendships.",
            purpose="TEST_M13 — help the student communicate to a naive reader.",
            task="TEST_M13 — draft your essay.",
        )
        r = client.get(f"{API}/sessions/{sid}", timeout=15)
        assert r.status_code == 200
        s = r.json()
        assert s["id"] == sid
        rd = s["theory"].get("revision_development")
        assert isinstance(rd, dict), rd
        assert rd.get("applies") is False
        for k in ("development_detected", "primary_growth", "communication_change",
                  "reader_change", "remaining_opportunity", "transfer_message"):
            assert rd.get(k) in ("", None), f"{k!r} should default empty: {rd.get(k)!r}"

        # PATCH /telos
        new_purpose = "TEST_M13 UPDATED — read revisions as developmental change."
        r = client.patch(f"{API}/sessions/{sid}/telos", json={"pedagogical_purpose": new_purpose}, timeout=15)
        assert r.status_code == 200, r.text
        assert r.json()["pedagogical_purpose"] == new_purpose
        assert client.get(f"{API}/sessions/{sid}", timeout=15).json()["pedagogical_purpose"] == new_purpose

    def test_get_nonexistent_returns_404(self, client):
        r = client.get(f"{API}/sessions/does-not-exist-m13", timeout=15)
        assert r.status_code == 404

    def test_first_submission_revision_development_not_applies(self, client):
        """On the FIRST draft (no prior draft), revision_development.applies==false."""
        sid = _new_session(
            client,
            assignment="TEST_M13 — argue whether social media harms teen friendships.",
            purpose="Help student communicate a clear developmental claim.",
            task="Draft your essay.",
        )
        draft = "Social media is bad for friends."
        status, s, err = sse_interact_with_retry(client, sid, {"kind": "writing", "content": draft})
        assert status == 200 and s is not None, f"SSE failed: err={err}"
        _assert_common(s, weak_text=draft)
        _assert_scaffolding_ok(s)
        _assert_m5a(s)

        rd = _rd(s)
        assert rd.get("applies") is False, (
            f"First draft (no prior) must have revision_development.applies=False, got: {rd!r}"
        )
        # Fields should be empty on first submission.
        for k in ("development_detected", "primary_growth", "communication_change",
                  "reader_change", "remaining_opportunity", "transfer_message"):
            assert not (rd.get(k) or "").strip(), (
                f"{k!r} should be empty on first submission: {rd.get(k)!r}"
            )
        print(f"\n[first-submission] rd.applies={rd.get('applies')} (correctly False)")


# --------------------------------------------------------------------------
# 2) Substantial growth: writing -> revise that clearly improves. Expect
#    applies=True, development_detected~yes/growth, primary_growth+transfer non-empty.
# --------------------------------------------------------------------------
class TestSubstantialGrowth:
    def test_substantial_growth_triggers_primary_growth_and_transfer(self, client):
        sid = _new_session(
            client,
            assignment="TEST_M13 — argue whether social media harms teen friendships.",
            purpose="Help student develop a claim a naive reader can grasp.",
            task="Draft your essay.",
        )
        # Turn 1: bare claim
        draft1 = "Social media is bad for friends."
        st1, s1, e1 = sse_interact_with_retry(client, sid, {"kind": "writing", "content": draft1})
        assert st1 == 200 and s1 is not None, f"turn1 SSE failed: err={e1}"
        _assert_common(s1, weak_text=draft1)
        _assert_scaffolding_ok(s1)
        _assert_m5a(s1)
        # First draft: rd.applies must be False.
        assert _rd(s1).get("applies") is False, f"turn1 (first draft) rd.applies should be False: {_rd(s1)!r}"

        # Turn 2: clearly-improved revise
        draft2 = (
            "Social media harms close friendships because constant shallow contact "
            "crowds out the focused attention deep friendship needs."
        )
        st2, s2, e2 = sse_interact_with_retry(client, sid, {"kind": "revise", "content": draft2})
        assert st2 == 200 and s2 is not None, f"turn2 SSE failed: err={e2}"
        _assert_common(s2, weak_text=draft2)
        _assert_scaffolding_ok(s2)
        _assert_m5a(s2)

        rd = _rd(s2)
        assert rd.get("applies") is True, f"revise turn should set rd.applies=True: {rd!r}"
        dd = (rd.get("development_detected") or "").strip().lower()
        assert dd, f"development_detected must be non-empty on revise: {rd!r}"
        assert dd.startswith("yes"), (
            f"substantial-growth revise must yield development_detected starting with 'yes', got {dd!r} | rd={rd!r}"
        )
        pg = (rd.get("primary_growth") or "").strip()
        assert pg, f"primary_growth must be non-empty for growth revise: {rd!r}"
        tm = (rd.get("transfer_message") or "").strip()
        assert tm, f"transfer_message must be non-empty for growth revise: {rd!r}"

        # No edit-counting/scorekeeping in the invitation.
        inv = _last_ai(s2)
        ec = _flags(inv, EDIT_COUNTING_FLAGS)
        assert not ec, f"edit-counting/scorekeeping leaked in growth invitation: {ec} | {inv[:300]}"

        print(f"\n[growth] dd={dd[:60]!r} primary_growth={pg[:60]!r} transfer={tm[:60]!r}")


# --------------------------------------------------------------------------
# 3) Superficial edit: mere word swaps between drafts. Expect development_detected
#    == no/partial (no fabricated growth), remaining_opportunity populated, and
#    NO edit-counting/scorekeeping in the invitation.
# --------------------------------------------------------------------------
class TestSuperficialEdit:
    def test_superficial_edit_yields_no_or_partial_and_names_remaining_opportunity(self, client):
        sid = _new_session(
            client,
            assignment="TEST_M13 — argue whether social media harms teen friendships.",
            purpose="Help student develop a claim a naive reader can grasp.",
            task="Draft your essay.",
        )
        draft1 = "Social media is bad for teen friendships."
        st1, s1, e1 = sse_interact_with_retry(client, sid, {"kind": "writing", "content": draft1})
        assert st1 == 200 and s1 is not None, f"turn1 SSE failed: err={e1}"
        _assert_common(s1, weak_text=draft1)
        _assert_scaffolding_ok(s1)
        _assert_m5a(s1)

        # Superficial edit — just an intensifier + synonym; no developmental change.
        draft2 = "Social media is really bad for teenage friendships."
        st2, s2, e2 = sse_interact_with_retry(client, sid, {"kind": "revise", "content": draft2})
        assert st2 == 200 and s2 is not None, f"turn2 SSE failed: err={e2}"
        _assert_common(s2, weak_text=draft2)
        _assert_scaffolding_ok(s2)
        _assert_m5a(s2)

        rd = _rd(s2)
        assert rd.get("applies") is True, f"revise turn should set rd.applies=True: {rd!r}"
        dd = (rd.get("development_detected") or "").strip().lower()
        assert dd, f"development_detected must be non-empty on revise: {rd!r}"
        assert dd.startswith("no") or dd.startswith("partial"), (
            f"superficial-edit revise must yield development_detected 'no' or 'partial' "
            f"(no fabricated growth), got {dd!r} | rd={rd!r}"
        )
        ro = (rd.get("remaining_opportunity") or "").strip()
        assert ro, f"remaining_opportunity must be non-empty for superficial edit: {rd!r}"

        # Invitation must NOT count edits or praise quantity of revision.
        inv = _last_ai(s2)
        ec = _flags(inv, EDIT_COUNTING_FLAGS)
        assert not ec, f"edit-counting/scorekeeping leaked in invitation: {ec} | {inv[:300]}"

        print(f"\n[superficial] dd={dd[:60]!r} remaining_opportunity={ro[:80]!r}")


# --------------------------------------------------------------------------
# 4) Regression: strong claim replaced by vague text. Expect development_detected=='no'
#    and remaining_opportunity populated.
# --------------------------------------------------------------------------
class TestRegression:
    def test_regression_detected_and_single_opportunity_named(self, client):
        sid = _new_session(
            client,
            assignment="TEST_M13 — argue whether social media harms teen friendships.",
            purpose="Help student develop a communicative claim.",
            task="Draft your essay.",
        )
        # Turn 1: reasonably strong claim
        draft1 = (
            "Social media harms close teen friendships because it substitutes many quick "
            "shallow exchanges for the sustained attention deep friendships require."
        )
        st1, s1, e1 = sse_interact_with_retry(client, sid, {"kind": "writing", "content": draft1})
        assert st1 == 200 and s1 is not None, f"turn1 SSE failed: err={e1}"
        _assert_common(s1, weak_text=draft1)
        _assert_scaffolding_ok(s1)
        _assert_m5a(s1)

        # Turn 2: vague replacement — communication is WORSE.
        draft2 = "Social media is a thing that impacts people in various ways."
        st2, s2, e2 = sse_interact_with_retry(client, sid, {"kind": "revise", "content": draft2})
        assert st2 == 200 and s2 is not None, f"turn2 SSE failed: err={e2}"
        _assert_common(s2, weak_text=draft2)
        _assert_scaffolding_ok(s2)
        _assert_m5a(s2)

        rd = _rd(s2)
        assert rd.get("applies") is True, f"revise turn should set rd.applies=True: {rd!r}"
        dd = (rd.get("development_detected") or "").strip().lower()
        assert dd.startswith("no"), (
            f"regression revise must yield development_detected 'no', got {dd!r} | rd={rd!r}"
        )
        ro = (rd.get("remaining_opportunity") or "").strip()
        assert ro, f"remaining_opportunity must be non-empty for regression: {rd!r}"

        # No edit-counting in invitation.
        inv = _last_ai(s2)
        ec = _flags(inv, EDIT_COUNTING_FLAGS)
        assert not ec, f"edit-counting leaked in regression invitation: {ec} | {inv[:300]}"

        print(f"\n[regression] dd={dd[:60]!r} remaining_opportunity={ro[:80]!r}")


# --------------------------------------------------------------------------
# 5) M6-M12 preserved on a substantial revise + M1-M5A history intact.
# --------------------------------------------------------------------------
class TestM6toM12RegressionAndHistory:
    def test_supported_revise_preserves_m6_to_m12_and_history(self, client):
        sid = _new_session(
            client,
            assignment="TEST_M13 — argue whether social media harms teen friendships.",
            purpose="Help student develop a communicative claim.",
            task="Draft a body paragraph.",
        )
        # Turn 1: thin body paragraph
        draft1 = "Social media is bad for teen friends because they use it a lot."
        st1, s1, e1 = sse_interact_with_retry(client, sid, {"kind": "writing", "content": draft1})
        assert st1 == 200 and s1 is not None, f"turn1 SSE failed: err={e1}"
        _assert_common(s1, weak_text=draft1)

        # Turn 2: supported body paragraph
        draft2 = (
            "Social media damages close friendships because it optimizes for breadth of "
            "contact over depth of attention. For example, a teen may exchange twenty "
            "quick reactions with different acquaintances in a single hour, yet spend no "
            "sustained time with a single close friend that same day. This matters because "
            "close friendship, unlike acquaintance, is built through the kind of focused "
            "attention that quick reactions cannot substitute for; when a platform's "
            "design rewards constant shallow contact, the deep attention that intimate "
            "friendship depends on is quietly displaced."
        )
        st2, s2, e2 = sse_interact_with_retry(client, sid, {"kind": "revise", "content": draft2})
        assert st2 == 200 and s2 is not None, f"turn2 SSE failed: err={e2}"
        _assert_common(s2, weak_text=draft2)

        # M6
        cp = _cp(s2)
        assert (cp.get("primary") or "").strip(), f"cp.primary must be populated: {cp!r}"
        # M7 / M8 / M9 applies
        th = s2["theory"]
        assert th.get("paragraph_function", {}).get("applies") is True, th.get("paragraph_function")
        assert th.get("evidence_function", {}).get("applies") is True, th.get("evidence_function")
        assert th.get("coherence_function", {}).get("applies") is True, th.get("coherence_function")
        # M11
        _assert_scaffolding_ok(s2)
        # M12
        rc = _rc(s2)
        assert rc.get("applies") is True, f"reader_construction.applies must be True: {rc!r}"
        assert (rc.get("reader_understanding") or "").strip(), f"reader_understanding empty: {rc!r}"
        # M13
        rd = _rd(s2)
        assert rd.get("applies") is True, f"rd.applies must be True on revise: {rd!r}"

        # M5A
        _assert_m5a(s2)

        # theory_history preserved (v1..vN, v1 not overwritten).
        hist = s2.get("theory_history", [])
        assert len(hist) >= 2, f"theory_history should have >=2 entries: len={len(hist)}"
        v_first, v_last = hist[0], hist[-1]
        assert v_first.get("version") == 1, f"first history entry must be v1: {v_first.get('version')}"
        assert v_last.get("version") >= 2, f"last history entry must be >= v2: {v_last.get('version')}"
        assert v_first.get("theory") != v_last.get("theory"), (
            "theory_history v1 appears overwritten to v_last (identical theory)"
        )

        # currently_relevant_domains 1..3
        dom = s2["theory"].get("currently_relevant_domains", []) or []
        assert 1 <= len(dom) <= 3, f"currently_relevant_domains 1..3, got {len(dom)}: {dom!r}"

        print(
            f"\n[M6-M13 regression] cp.primary={cp.get('primary')!r} "
            f"pf/ef/cf.applies=True rd.applies=True rc.applies=True "
            f"hist versions={[h.get('version') for h in hist]}"
        )
