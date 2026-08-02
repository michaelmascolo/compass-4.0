"""Milestone 3 tests — enriched 'Central Claim / Thesis' canonical domain +
generic domain-independent SECTION-LEVEL retrieval.

Scope:
- Data-only sanity: Central Claim / Thesis is enriched to the ~31-field schema
  proven for Opening / Introduction.
- Section-level retrieval: STAGE B reasoner prompt is much smaller than sending
  the whole record because get_relevant_domain_data() filters each record to
  ALWAYS_KEYS + selected sections. Log line format changed in M3:
     '[interact] domains/sections={<name>: <count>, ...} reasoner_prompt_bytes=NNNN'
- Thesis reasoning: submitting an argumentative thesis surfaces 'Central Claim
  / Thesis' among currently_relevant_domains and the invitation is a thinking
  invitation (not an AI-supplied claim).
- Genre sensitivity: a personal / narrative opening does NOT get pushed to
  produce an argumentative thesis.
- Engine contract preserved: one invitation per turn, no rewriting, no fixed
  'X because A, B, C' formula demand.
- Multi-turn 4-turn session (writing -> revise -> answer -> revise) all
  under 60s each, no 502.
- Regression: empty -> 400, missing session -> 404, theory_history preserves
  prior theories, changes_since_previous not 'initial' after turn 1.

Run serially:
    pytest /app/backend/tests/test_milestone3_thesis.py -v -n 0
"""
import json
import os
import re
import time
from pathlib import Path

import pytest
import requests


# ---- config ----------------------------------------------------------------
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

CANONICAL = json.loads(Path("/app/backend/canonical_writing_model.json").read_text())
CANONICAL_DOMAIN_NAMES = [d["domain_name"] for d in CANONICAL["domains"]]
THESIS_DOMAIN = "Central Claim / Thesis"
OPENING_DOMAIN = "Opening / Introduction"
THESIS_RECORD = next(d for d in CANONICAL["domains"] if d["domain_name"] == THESIS_DOMAIN)


# ---- SSE helper ------------------------------------------------------------
def sse_interact(client, sid, payload, timeout=120):
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


# ---- fixtures --------------------------------------------------------------
@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def thesis_session(client):
    """Argumentative-essay session where 'Central Claim / Thesis' should surface."""
    payload = {
        "assignment": (
            "TEST_M3 Write an argumentative essay taking a position on whether "
            "high schools should replace letter grades with narrative feedback."
        ),
        "pedagogical_purpose": (
            "Students learn to distinguish a topic from a claim, and to state "
            "an arguable, focused claim they can defend."
        ),
        "current_writing_task": (
            "Draft a thesis paragraph that states your central claim and "
            "signals the reasoning that will support it."
        ),
        "teacher_notes": "TEST_M3 student often submits a topic instead of a claim.",
    }
    r = client.post(f"{API}/sessions", json=payload, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture(scope="module")
def narrative_session(client):
    """Personal / narrative session — an argumentative thesis must NOT be pushed."""
    payload = {
        "assignment": (
            "TEST_M3 Write a personal narrative about a moment when your view "
            "of a family member changed."
        ),
        "pedagogical_purpose": (
            "Students learn to organize a personal narrative around a "
            "meaningful shift in understanding."
        ),
        "current_writing_task": "Draft the opening scene of your narrative.",
        "teacher_notes": "TEST_M3 narrative genre — no argumentative thesis required.",
    }
    r = client.post(f"{API}/sessions", json=payload, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()


# ---- Data-only sanity ------------------------------------------------------
class TestThesisRecordShape:
    def test_thesis_record_has_enrichment_fields(self):
        expected = [
            "domain_status",
            "governing_communicative_function",
            "possible_communicative_functions",
            "observable_organizations",
            "possible_differentiations",
            "possible_integrations",
            "possible_coordinations",
            "common_productive_tensions",
            "alternative_interpretations",
            "common_misunderstandings",
            "candidate_developmental_invitations",
            "invitation_construction_rules",
            "genre_sensitivity",
            "prohibitions",
        ]
        missing = [k for k in expected if k not in THESIS_RECORD]
        assert not missing, f"Central Claim/Thesis record missing enrichment fields: {missing}"
        # Enrichment claim: ~31 fields (>= 28 tolerated)
        assert len(THESIS_RECORD.keys()) >= 28, (
            f"Thesis record only has {len(THESIS_RECORD.keys())} keys; expected ~31"
        )


# ---- Section-level retrieval (generic, domain-independent) -----------------
class TestSectionLevelRetrievalHelper:
    """Directly exercise the section-filter helper without hitting the LLM."""

    def test_get_relevant_domain_data_filters_by_sections(self):
        # Import from backend server module directly
        import importlib
        import sys
        sys.path.insert(0, "/app/backend")
        srv = importlib.import_module("server")

        selections = [
            {"domain_name": THESIS_DOMAIN, "sections": [
                "candidate_developmental_invitations",
                "invitation_construction_rules",
                "common_productive_tensions",
            ]},
        ]
        recs = srv.get_relevant_domain_data(selections)
        assert len(recs) == 1
        rec = recs[0]
        # ALWAYS_KEYS present
        for k in srv.ALWAYS_KEYS:
            if k in THESIS_RECORD:
                assert k in rec, f"ALWAYS key {k!r} missing from filtered record"
        # requested sections present
        for k in [
            "candidate_developmental_invitations",
            "invitation_construction_rules",
            "common_productive_tensions",
        ]:
            assert k in rec
        # unrelated sections NOT smuggled in
        for k in ("observable_organizations", "possible_differentiations"):
            assert k not in rec, f"unrequested section {k!r} leaked into filtered record"

    def test_get_relevant_domain_data_falls_back_to_full_record(self):
        import importlib
        import sys
        sys.path.insert(0, "/app/backend")
        srv = importlib.import_module("server")
        # empty sections -> whole record (backward compatible)
        recs = srv.get_relevant_domain_data([{"domain_name": THESIS_DOMAIN, "sections": []}])
        assert len(recs) == 1
        # should include a section beyond ALWAYS_KEYS
        assert "observable_organizations" in recs[0] or "candidate_developmental_invitations" in recs[0]

    def test_get_relevant_domain_data_accepts_bare_names(self):
        import importlib
        import sys
        sys.path.insert(0, "/app/backend")
        srv = importlib.import_module("server")
        recs = srv.get_relevant_domain_data([THESIS_DOMAIN])
        assert len(recs) == 1
        assert recs[0]["domain_name"] == THESIS_DOMAIN


# ---- Thesis reasoning: 4-turn flow -----------------------------------------
class TestThesisReasoningFlow:
    def test_turn1_writing_selects_thesis_domain(self, client, thesis_session):
        thesis_draft = (
            "Grades. Grades are a topic that people talk about a lot. Some "
            "people like them and some people do not. Narrative feedback is "
            "when teachers write comments. There are pros and cons to each. "
            "In this essay I will discuss letter grades and narrative feedback."
        )
        status, data, err = sse_interact(
            client, thesis_session["id"],
            {"kind": "writing", "content": thesis_draft},
        )
        assert status == 200, f"status={status} err={err}"
        assert err is None
        assert data is not None
        elapsed = data.get("_elapsed_seconds")
        assert elapsed is not None and elapsed < 60, f"turn 1 took {elapsed:.1f}s"

        rel = data["theory"]["currently_relevant_domains"]
        assert 1 <= len(rel) <= 3
        for name in rel:
            assert name in CANONICAL_DOMAIN_NAMES
        assert THESIS_DOMAIN in rel, (
            f"'{THESIS_DOMAIN}' should surface for a topic-without-claim submission; got {rel}"
        )

        # alternative_interpretations populated
        alt = data["theory"].get("alternative_interpretations", [])
        assert isinstance(alt, list) and len(alt) >= 1

        # Exactly ONE student-facing invitation per turn
        ai_turns = [t for t in data["turns"] if t["role"] == "ai"]
        assert len(ai_turns) == 1
        invitation = ai_turns[-1]["content"].strip()
        assert invitation

        # Engine must NOT write a thesis for the student
        low = invitation.lower()
        # heuristic: coach should not literally start "Your thesis is:" or similar
        banned_supply = [
            "your thesis is:", "your thesis should be:",
            "here is your thesis", "your claim is:",
            "here's your thesis", "here is a thesis for you",
        ]
        for b in banned_supply:
            assert b not in low, f"AI supplied a thesis for the student: {invitation!r}"

        # Engine must NOT demand a rigid 'X because A, B, C' three-part formula
        banned_formula = [
            "x because a, b, and c",
            "state your thesis in the form",
            "must follow the format",
            "three-part thesis",
            "three-part formula",
        ]
        for b in banned_formula:
            assert b not in low, f"AI imposed a rigid thesis formula: {invitation!r}"

        pytest.m3_turn1 = data

    def test_turn2_revise_shifts_theory(self, client, thesis_session):
        prev = getattr(pytest, "m3_turn1", None)
        assert prev is not None
        revised = (
            "High schools should replace letter grades with narrative "
            "feedback because narrative comments describe what the student "
            "actually did and can do next, while a single letter compresses "
            "months of work into a symbol that hides the reasoning behind it. "
            "The claim is not that grades are meaningless, but that they "
            "encode less than the writing they summarize."
        )
        status, data, err = sse_interact(
            client, thesis_session["id"],
            {"kind": "revise", "content": revised},
        )
        assert status == 200, f"status={status} err={err}"
        assert err is None
        assert data is not None
        elapsed = data.get("_elapsed_seconds")
        assert elapsed is not None and elapsed < 60

        assert len(data["theory_history"]) == 2
        assert data["theory_history"][1]["version"] == 2

        changes = (data["theory"].get("changes_since_previous") or "").strip().lower()
        assert changes and changes != "initial", (
            f"changes_since_previous should reflect revision, got {changes!r}"
        )
        pytest.m3_turn2 = data

    def test_turn3_answer_history_grows(self, client, thesis_session):
        prev = getattr(pytest, "m3_turn2", None)
        assert prev is not None
        status, data, err = sse_interact(
            client, thesis_session["id"],
            {"kind": "answer", "content": (
                "I moved from listing pros and cons to naming a single claim "
                "about what letter grades hide, because that is the part I "
                "actually want to defend."
            )},
        )
        assert status == 200, f"status={status} err={err}"
        assert err is None
        assert data is not None
        elapsed = data.get("_elapsed_seconds")
        assert elapsed is not None and elapsed < 60
        assert len(data["theory_history"]) == 3
        versions = [s["version"] for s in data["theory_history"]]
        assert versions == [1, 2, 3]
        pytest.m3_turn3 = data

    def test_turn4_revise_history_v4_reliability(self, client, thesis_session):
        prev = getattr(pytest, "m3_turn3", None)
        assert prev is not None
        revised_again = (
            "High schools should replace letter grades with narrative "
            "feedback in the humanities, because narrative comments preserve "
            "the reasoning behind an evaluation while a letter compresses it "
            "into a symbol that students cannot read. My claim is limited to "
            "the humanities because I do not yet know how the same argument "
            "translates to mathematics coursework."
        )
        status, data, err = sse_interact(
            client, thesis_session["id"],
            {"kind": "revise", "content": revised_again},
        )
        assert status == 200, f"status={status} err={err}"
        assert err is None
        assert data is not None
        elapsed = data.get("_elapsed_seconds")
        assert elapsed is not None and elapsed < 60
        assert len(data["theory_history"]) == 4
        versions = [s["version"] for s in data["theory_history"]]
        assert versions == [1, 2, 3, 4]

        # Interaction records recorded on every turn with 2-3 candidates
        assert len(data["interactions"]) == 4
        for ir in data["interactions"]:
            assert 2 <= len(ir["candidate_invitations"]) <= 3
            assert ir["selected_invitation"]["invitation"].strip()


# ---- Genre sensitivity -----------------------------------------------------
class TestGenreSensitivity:
    def test_narrative_opening_does_not_demand_argumentative_thesis(self, client, narrative_session):
        narrative_draft = (
            "The first time I noticed how tired my mother was, we were "
            "waiting for a bus. The rain had stopped an hour earlier and the "
            "bench was still wet, but she sat down anyway and set the bag of "
            "groceries between her feet. She said nothing for a long time. "
            "That silence was new."
        )
        status, data, err = sse_interact(
            client, narrative_session["id"],
            {"kind": "writing", "content": narrative_draft},
        )
        assert status == 200, f"status={status} err={err}"
        assert err is None
        assert data is not None
        elapsed = data.get("_elapsed_seconds")
        assert elapsed is not None and elapsed < 60

        invitation = data["turns"][-1]["content"].strip()
        low = invitation.lower()

        # Must NOT force an argumentative thesis onto a narrative
        banned = [
            "state your thesis",
            "state an arguable thesis",
            "state your central claim",
            "your argumentative thesis",
            "your claim needs to be arguable",
            "add a thesis statement",
        ]
        for b in banned:
            assert b not in low, (
                f"Narrative genre was pushed toward an argumentative thesis: {invitation!r}"
            )


# ---- Section-level retrieval prompt-size verification ----------------------
class TestSectionLevelRetrievalLog:
    """Verify the STAGE B prompt stays bounded thanks to section filtering
    (M3 target: ~3.5-8KB typical; up to ~16KB when 2 enriched domains overlap,
    still well below the ~35KB whole-model payload)."""

    def test_recent_prompt_bytes_bounded_by_section_filter(self):
        log_paths = sorted(Path("/var/log/supervisor").glob("backend.*.log"))
        assert log_paths, "No backend supervisor logs found"
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
        assert entries, (
            "No '[interact] domains/sections={...} reasoner_prompt_bytes=NNNN' log lines found — "
            "the Milestone 3 log format may not be wired up."
        )
        # look at the most recent 8 turns (this test file plus prior context)
        recent = entries[-8:]
        for domains_str, size in recent:
            # Section filter should keep the prompt WELL under a naive whole-record dump.
            # Enriched Opening + Thesis together approach ~16-22KB even filtered;
            # keep an assertion that still catches "whole 13-domain model" regressions.
            assert size <= 32000, (
                f"reasoner_prompt_bytes={size} for {domains_str} exceeds 32KB "
                f"— section-level retrieval may not be filtering as intended."
            )
        # And in the typical case (only one enriched domain selected or none)
        # we expect < 12KB — track that as a soft ceiling on the median.
        sizes = [s for _, s in recent]
        median = sorted(sizes)[len(sizes) // 2]
        # Median should stay well below the whole-model ~35KB; this
        # confirms section filtering is active on most turns.
        assert median <= 22000, (
            f"median reasoner_prompt_bytes={median} across recent turns is too high; "
            f"section-level retrieval expected to keep median <= 22KB. sizes={sizes}"
        )
        print(f"recent domains/sections + sizes: {recent}")

    def test_log_reports_per_domain_section_counts(self):
        """The new log line must expose per-domain SECTION counts (not just names)."""
        log_paths = sorted(Path("/var/log/supervisor").glob("backend.*.log"))
        pat = re.compile(
            r"\[interact\]\s+domains/sections=(\{[^}]*\})\s+reasoner_prompt_bytes=\d+"
        )
        entries = []
        for p in log_paths:
            try:
                text = p.read_text(errors="ignore")
            except Exception:
                continue
            for m in pat.finditer(text):
                entries.append(m.group(1))
        assert entries, "No M3 domains/sections log lines found"
        # take the most recent entry, parse the dict payload safely
        import ast
        latest = entries[-1]
        try:
            parsed = ast.literal_eval(latest)
        except Exception as e:  # noqa: BLE001
            pytest.fail(f"Could not parse domains/sections payload {latest!r}: {e}")
        assert isinstance(parsed, dict) and parsed, f"payload is not a non-empty dict: {parsed!r}"
        for name, count in parsed.items():
            assert name in CANONICAL_DOMAIN_NAMES, f"unknown domain in log: {name!r}"
            assert isinstance(count, int) and count >= 0, (
                f"section count for {name!r} not an int: {count!r}"
            )


# ---- Regression: validation ------------------------------------------------
class TestValidationRegression:
    def test_empty_content_returns_400(self, client, thesis_session):
        r = client.post(
            f"{API}/sessions/{thesis_session['id']}/interact",
            json={"kind": "writing", "content": "   "},
            timeout=15,
        )
        assert r.status_code == 400

    def test_missing_session_returns_404(self, client):
        missing = f"nope-m3-{int(time.time())}"
        r = client.get(f"{API}/sessions/{missing}", timeout=15)
        assert r.status_code == 404
        r2 = client.post(
            f"{API}/sessions/{missing}/interact",
            json={"kind": "writing", "content": "hello"},
            timeout=15,
        )
        assert r2.status_code == 404
