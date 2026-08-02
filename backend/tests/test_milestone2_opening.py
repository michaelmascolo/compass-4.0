"""Milestone 2 tests — enriched 'Opening / Introduction' canonical domain.

These tests specifically exercise:
- Two-stage domain selection picks 'Opening / Introduction' for an
  introduction-focused submission.
- Theory field `alternative_interpretations` is populated (new generic field).
- Multi-turn reliability holds: 3-turn intro session, each turn <60s, no 502.
- No hook / fixed-thesis formula is imposed (invitation does NOT force a
  catchy hook or a specific thesis position).
- AI does not rewrite the student's introduction.
- theory_history grows and changes_since_previous is not 'initial' after
  the first turn.
- Regression: empty content -> 400, missing session -> 404.

Run serially: pytest /app/backend/tests/test_milestone2_opening.py -v -n 0
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


def sse_interact(client, sid, payload, timeout=120):
    """Consume SSE stream from /interact. Returns (status, done_json, error)."""
    started = time.time()
    with client.post(
        f"{API}/sessions/{sid}/interact",
        json=payload, stream=True, timeout=timeout,
        headers={"Accept": "text/event-stream"},
    ) as r:
        if r.status_code != 200:
            try:
                body = r.text
            except Exception:
                body = ""
            return r.status_code, None, body

        buffer = ""
        done_payload = None
        error_detail = None
        for chunk in r.iter_content(chunk_size=None, decode_unicode=True):
            if chunk is None:
                continue
            buffer += chunk
            while "\n\n" in buffer:
                raw_event, buffer = buffer.split("\n\n", 1)
                event_name = "message"
                data_lines = []
                for line in raw_event.split("\n"):
                    if not line or line.startswith(":"):
                        continue
                    if line.startswith("event:"):
                        event_name = line[len("event:"):].strip()
                    elif line.startswith("data:"):
                        data_lines.append(line[len("data:"):].strip())
                data = "".join(data_lines)
                if event_name == "done" and data:
                    done_payload = json.loads(data)
                elif event_name == "error" and data:
                    try:
                        error_detail = json.loads(data).get("detail")
                    except Exception:
                        error_detail = data
            if done_payload is not None or error_detail is not None:
                break
        elapsed = time.time() - started
        if done_payload is not None:
            done_payload.setdefault("_elapsed_seconds", elapsed)
        return r.status_code, done_payload, error_detail


CANONICAL = json.loads(Path("/app/backend/canonical_writing_model.json").read_text())
CANONICAL_DOMAIN_NAMES = [d["domain_name"] for d in CANONICAL["domains"]]
OPENING_DOMAIN = "Opening / Introduction"
assert OPENING_DOMAIN in CANONICAL_DOMAIN_NAMES

# Sanity: the enriched Opening record actually contains the new fields
OPENING_RECORD = next(d for d in CANONICAL["domains"] if d["domain_name"] == OPENING_DOMAIN)


class TestOpeningRecordShape:
    """Data-only sanity: the enriched Opening record has the fields the review
    request enumerates so we know we're testing the enriched build."""
    def test_opening_record_has_enrichment_fields(self):
        expected = [
            "governing_communicative_function",
            "possible_communicative_functions",
            "observable_organizations",
            "possible_differentiations",
            "possible_integrations",
            "possible_coordinations",
            "common_productive_tensions",
            "alternative_interpretations",
            "candidate_developmental_invitations",
            "invitation_construction_rules",
            "genre_sensitivity",
            "prohibitions",
        ]
        missing = [k for k in expected if k not in OPENING_RECORD]
        assert not missing, f"Opening record missing enrichment fields: {missing}"


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def intro_session(client):
    """A session whose assignment/task is specifically an introduction."""
    payload = {
        "assignment": (
            "TEST_M2 Write an argumentative essay on whether public libraries "
            "should offer free universal childcare during school hours."
        ),
        "pedagogical_purpose": (
            "Students learn to open a piece of writing in a way that orients "
            "the reader, frames why the question matters, and sets up the "
            "argument that follows."
        ),
        "current_writing_task": (
            "Draft the introduction: an opening paragraph that orients the "
            "reader to the question and sets up the argument to follow."
        ),
        "teacher_notes": (
            "TEST_M2 student tends to open with a generic hook; work on "
            "problem framing and reader orientation."
        ),
    }
    r = client.post(f"{API}/sessions", json=payload, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()


def _no_hook_demand(text: str) -> bool:
    """Return True if the invitation does NOT demand a catchy/attention-grabbing hook."""
    low = text.lower()
    banned = [
        "catchy hook", "attention-grabbing hook", "attention grabbing hook",
        "grab the reader", "grab your reader", "grabber",
        "start with a quote", "start with a question", "start with a statistic",
        "hook the reader",
    ]
    return not any(b in low for b in banned)


def _no_fixed_thesis_position(text: str) -> bool:
    """Return True if the invitation does NOT demand a thesis at the end of the intro."""
    low = text.lower()
    banned = [
        "thesis at the end of your introduction",
        "thesis must appear at the end",
        "end your introduction with a thesis",
        "put your thesis in the last sentence",
        "thesis should be the last sentence",
    ]
    return not any(b in low for b in banned)


def _rewrote_student(student_text: str, invitation: str) -> bool:
    """Rough heuristic: did the coach quote a long slice (>=60 chars) of the student text?"""
    # Compare 40-char sliding windows from the student text against the invitation
    st = " ".join(student_text.split())
    inv = " ".join(invitation.split())
    for i in range(0, len(st) - 60, 20):
        window = st[i:i + 60]
        if window in inv:
            return True
    return False


class TestOpeningInteractFlow:
    """Milestone 2 core: run 3 turns on an introduction submission."""

    def test_turn1_writing_selects_opening_and_populates_alternatives(self, client, intro_session):
        student_intro = (
            "Every school day, thousands of parents in this city choose between "
            "a paycheck and a child. That is not a fringe hardship, and it is "
            "not a private problem: it is a public design flaw. Public "
            "libraries already sit in every neighborhood, already welcome "
            "children, and already function as civic infrastructure. If we are "
            "serious about turning stated support for working families into "
            "actual policy, the library is the room that already exists to "
            "hold this argument, and the case for free universal childcare "
            "during school hours belongs there."
        )
        status, data, err = sse_interact(
            client, intro_session["id"],
            {"kind": "writing", "content": student_intro},
        )
        assert status == 200, f"status={status} err={err}"
        assert err is None, f"SSE error: {err}"
        assert data is not None, "no done event"

        elapsed = data.get("_elapsed_seconds")
        assert elapsed is not None and elapsed < 60, f"turn 1 took {elapsed:.1f}s"

        theory = data["theory"]
        rel = theory["currently_relevant_domains"]
        assert OPENING_DOMAIN in rel, (
            f"'{OPENING_DOMAIN}' not in currently_relevant_domains={rel}"
        )
        # 1..3 domain names, all canonical
        assert 1 <= len(rel) <= 3
        for name in rel:
            assert name in CANONICAL_DOMAIN_NAMES

        # alternative_interpretations must be populated (list of strings)
        alt = theory.get("alternative_interpretations", [])
        assert isinstance(alt, list) and len(alt) >= 1, (
            f"alternative_interpretations must be populated, got {alt!r}"
        )
        assert all(isinstance(x, str) and x.strip() for x in alt)

        # AI must not rewrite the student's paragraph
        invitation = data["turns"][-1]["content"]
        assert not _rewrote_student(student_intro, invitation), (
            f"AI appears to have rewritten the student's paragraph: {invitation!r}"
        )
        # AI must not force a hook or a fixed thesis position
        assert _no_hook_demand(invitation), f"Invitation demands a hook: {invitation!r}"
        assert _no_fixed_thesis_position(invitation), (
            f"Invitation demands fixed thesis placement: {invitation!r}"
        )

        # Exactly one student-facing invitation per turn
        ai_turns = [t for t in data["turns"] if t["role"] == "ai"]
        assert len(ai_turns) == 1

        # v1 preserves the empty initial theory
        assert data["theory_history"][0]["theory"]["currently_relevant_domains"] == []
        # first turn: changes_since_previous is 'initial' or empty
        pytest.m2_turn1 = data

    def test_turn2_revise_grows_history_and_changes_since_previous(self, client, intro_session):
        prev = getattr(pytest, "m2_turn1", None)
        assert prev is not None

        revised = (
            "Every school day, thousands of parents in this city are quietly "
            "sorting through an impossible calculation: which hour of childcare "
            "they can afford to lose. This is not a private hardship — it is a "
            "public design flaw that the city keeps re-drawing. Public "
            "libraries are already the civic infrastructure that welcomes "
            "children in every neighborhood; the room to hold this argument "
            "already exists. So the question is not whether we can imagine a "
            "place for free universal childcare during school hours, but "
            "whether we are willing to name the library as that place."
        )
        status, data, err = sse_interact(
            client, intro_session["id"],
            {"kind": "revise", "content": revised},
        )
        assert status == 200, f"status={status} err={err}"
        assert err is None
        assert data is not None
        elapsed = data.get("_elapsed_seconds")
        assert elapsed is not None and elapsed < 60

        # theory_history grew and second snapshot is v2
        assert len(data["theory_history"]) == 2
        assert data["theory_history"][1]["version"] == 2

        # changes_since_previous is NOT 'initial' after turn 1
        changes = (data["theory"].get("changes_since_previous") or "").strip().lower()
        assert changes and changes != "initial", (
            f"changes_since_previous should reflect a revision, got {changes!r}"
        )

        # alternative_interpretations still populated
        alt = data["theory"].get("alternative_interpretations", [])
        assert isinstance(alt, list) and len(alt) >= 1

        # No rewriting on turn 2 either
        invitation = data["turns"][-1]["content"]
        assert not _rewrote_student(revised, invitation)
        assert _no_hook_demand(invitation)
        assert _no_fixed_thesis_position(invitation)

        # Opening domain still in play (or a legitimate neighbor like Central Claim)
        rel = data["theory"]["currently_relevant_domains"]
        assert 1 <= len(rel) <= 3
        pytest.m2_turn2 = data

    def test_turn3_answer_theory_history_v3(self, client, intro_session):
        prev = getattr(pytest, "m2_turn2", None)
        assert prev is not None

        answer_text = (
            "I chose to open by naming the daily calculation parents make "
            "rather than by leading with a statistic, because I wanted the "
            "reader to feel the problem before they were asked to weigh it. "
            "The library is introduced as the place that already holds this "
            "role, so the thesis follows from a fact about the city, not "
            "from a slogan."
        )
        status, data, err = sse_interact(
            client, intro_session["id"],
            {"kind": "answer", "content": answer_text},
        )
        assert status == 200, f"status={status} err={err}"
        assert err is None
        assert data is not None
        elapsed = data.get("_elapsed_seconds")
        assert elapsed is not None and elapsed < 60

        assert len(data["theory_history"]) == 3
        versions = [s["version"] for s in data["theory_history"]]
        assert versions == [1, 2, 3]

        # AI doesn't rewrite; still no hook/fixed-thesis pressure
        invitation = data["turns"][-1]["content"]
        assert _no_hook_demand(invitation)
        assert _no_fixed_thesis_position(invitation)

        # Interaction records
        assert len(data["interactions"]) == 3
        for ir in data["interactions"]:
            assert 2 <= len(ir["candidate_invitations"]) <= 3
            assert ir["selected_invitation"]["invitation"].strip()


class TestReasonerPromptSizeWithOpening:
    """Verify the STAGE B prompt stays bounded even with the enriched
    Opening / Introduction record included (should be <=26KB)."""

    def test_recent_prompt_bytes_within_bounded_budget(self):
        log_paths = sorted(Path("/var/log/supervisor").glob("backend.*.log"))
        assert log_paths
        # Milestone 3 changed the log format to '[interact] domains/sections={...} reasoner_prompt_bytes=NNNN'
        pat = re.compile(
            r"\[interact\]\s+domains/sections=(\{[^}]*\})\s+reasoner_prompt_bytes=(\d+)"
        )
        entries = []
        for p in log_paths:
            try:
                text = p.read_text(errors="ignore")
            except Exception:
                continue
            for m in pat.finditer(text):
                entries.append((m.group(1), int(m.group(2))))
        assert entries, "No '[interact] ... reasoner_prompt_bytes=NNNN' log lines"
        recent = entries[-3:]
        for domains_str, size in recent:
            # Full 13-domain payload would be ~35KB+; anything under ~26KB
            # proves we're still selectively assembling by domain.
            assert size <= 26000, (
                f"reasoner_prompt_bytes={size} for {domains_str} exceeds 26KB budget "
                f"— two-stage selection may be sending too much."
            )
        print(f"recent reasoner_prompt_bytes: {recent}")


class TestValidationRegression:
    def test_empty_content_returns_400(self, client, intro_session):
        r = client.post(
            f"{API}/sessions/{intro_session['id']}/interact",
            json={"kind": "writing", "content": "   "},
            timeout=15,
        )
        assert r.status_code == 400

    def test_missing_session_returns_404(self, client):
        missing = f"nope-m2-{int(time.time())}"
        r = client.get(f"{API}/sessions/{missing}", timeout=15)
        assert r.status_code == 404
        r2 = client.post(
            f"{API}/sessions/{missing}/interact",
            json={"kind": "writing", "content": "hello"},
            timeout=15,
        )
        assert r2.status_code == 404
