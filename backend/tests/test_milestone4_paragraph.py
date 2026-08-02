"""Milestone 4 tests — enriched 'Paragraph Purpose' canonical domain.

Scope:
- Data-only sanity: 'Paragraph Purpose' record enriched to the ~31-field schema
  proven for Opening / Introduction and Central Claim / Thesis. Engine code
  UNCHANGED (still uses generic section-level retrieval).
- Paragraph reasoning: submitting a body paragraph for an argumentative
  assignment surfaces 'Paragraph Purpose' among currently_relevant_domains
  and the invitation is a THINKING invitation that does NOT rewrite the
  student's paragraph, does NOT demand a first-sentence topic sentence, does
  NOT force claim-evidence-analysis structure.
- No-formula imposition: narrative and reflective paragraphs must NOT be
  pushed into claim-evidence-analysis.
- Alternative interpretations preserved.
- Multi-turn 4-turn session (writing -> revise -> answer -> revise) each
  under 60s, all return HTTP 200 + 'event: done'.
- Section-level retrieval still active/bounded — log line
  '[interact] domains/sections={...} reasoner_prompt_bytes=NNNN' present.
- Regression: empty -> 400, missing session -> 404, theory_history grows,
  changes_since_previous moves off 'initial' after turn 1.

Run serially:
    pytest /app/backend/tests/test_milestone4_paragraph.py -v -n 0
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
PARAGRAPH_DOMAIN = "Paragraph Purpose"
THESIS_DOMAIN = "Central Claim / Thesis"
OPENING_DOMAIN = "Opening / Introduction"
PARAGRAPH_RECORD = next(d for d in CANONICAL["domains"] if d["domain_name"] == PARAGRAPH_DOMAIN)


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
def paragraph_session(client):
    """Argumentative body-paragraph session where Paragraph Purpose surfaces."""
    payload = {
        "assignment": (
            "TEST_M4 Write an argumentative essay about whether cities should "
            "reduce car traffic downtown."
        ),
        "pedagogical_purpose": (
            "Help students clarify what each paragraph is doing for the essay "
            "and coordinate its purpose with the whole."
        ),
        "current_writing_task": "Draft a body paragraph for your argument.",
        "teacher_notes": (
            "TEST_M4 student often submits topic-listing paragraphs without an "
            "explicit purpose."
        ),
    }
    r = client.post(f"{API}/sessions", json=payload, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture(scope="module")
def narrative_session(client):
    """Narrative session — argumentative claim-evidence-analysis must NOT be forced."""
    payload = {
        "assignment": "TEST_M4 Write a narrative about a morning commute.",
        "pedagogical_purpose": (
            "Students learn to compose narrative paragraphs that establish "
            "scene, motion, and stakes without argumentative structure."
        ),
        "current_writing_task": "Draft a paragraph for your narrative.",
        "teacher_notes": "TEST_M4 narrative genre — no argumentative structure required.",
    }
    r = client.post(f"{API}/sessions", json=payload, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture(scope="module")
def reflective_session(client):
    """Reflective session — claim-evidence-analysis must NOT be imposed."""
    payload = {
        "assignment": "TEST_M4 Write a reflective essay about how you move through your city.",
        "pedagogical_purpose": (
            "Students learn to compose reflective paragraphs that hold contradiction "
            "and uncertainty productively."
        ),
        "current_writing_task": "Draft a reflective paragraph.",
        "teacher_notes": "TEST_M4 reflective genre — uncertainty is honored.",
    }
    r = client.post(f"{API}/sessions", json=payload, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()


# ---- Data-only sanity ------------------------------------------------------
class TestParagraphRecordShape:
    def test_paragraph_record_has_enrichment_fields(self):
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
        missing = [k for k in expected if k not in PARAGRAPH_RECORD]
        assert not missing, f"Paragraph Purpose record missing enrichment fields: {missing}"
        assert len(PARAGRAPH_RECORD.keys()) >= 28, (
            f"Paragraph Purpose record only has {len(PARAGRAPH_RECORD.keys())} keys; expected ~31"
        )

    def test_observable_organizations_populated(self):
        obs = PARAGRAPH_RECORD.get("observable_organizations", [])
        assert isinstance(obs, list) and len(obs) >= 20, (
            f"observable_organizations should have ~22 entries (A-V); got {len(obs)}"
        )

    def test_other_domains_untouched_by_m4(self):
        """Milestone 4 should ONLY enrich Paragraph Purpose. Other unenriched
        domains stay at ~9 keys; Opening and Thesis remain at ~31 keys."""
        enriched = {OPENING_DOMAIN, THESIS_DOMAIN, PARAGRAPH_DOMAIN}
        for dom in CANONICAL["domains"]:
            n = len(dom.keys())
            if dom["domain_name"] in enriched:
                assert n >= 28, f"{dom['domain_name']} should be enriched (~31 keys); got {n}"
            else:
                # Untouched domains should stay at their lightweight schema
                assert n <= 15, (
                    f"{dom['domain_name']} unexpectedly enriched to {n} keys — M4 was data-only "
                    f"for Paragraph Purpose."
                )


# ---- Paragraph reasoning: 4-turn flow --------------------------------------
class TestParagraphReasoningFlow:
    def test_turn1_writing_selects_paragraph_domain(self, client, paragraph_session):
        # Topic-listing paragraph with no clear purpose (Case 1 in eval).
        para_draft = (
            "There are many things about traffic downtown. Traffic is a big "
            "topic. Downtown areas have a lot of cars and people and stores "
            "and buses."
        )
        status, data, err = sse_interact(
            client, paragraph_session["id"],
            {"kind": "writing", "content": para_draft},
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
        assert PARAGRAPH_DOMAIN in rel, (
            f"'{PARAGRAPH_DOMAIN}' should surface for a body paragraph submission; got {rel}"
        )

        alt = data["theory"].get("alternative_interpretations", [])
        assert isinstance(alt, list) and len(alt) >= 1, (
            "alternative_interpretations should be populated"
        )

        # Exactly ONE student-facing invitation per turn
        ai_turns = [t for t in data["turns"] if t["role"] == "ai"]
        assert len(ai_turns) == 1
        invitation = ai_turns[-1]["content"].strip()
        assert invitation

        low = invitation.lower()

        # Engine must NOT rewrite the paragraph
        banned_rewrite = [
            "here is your paragraph",
            "here's your paragraph",
            "here is a revised paragraph",
            "let me rewrite",
            "i will rewrite",
        ]
        for b in banned_rewrite:
            assert b not in low, f"AI rewrote the student's paragraph: {invitation!r}"

        # Engine must NOT demand topic-sentence-first formula
        banned_formula = [
            "must start with a topic sentence",
            "must begin with a topic sentence",
            "need a topic sentence at the start",
            "topic sentence must be first",
            "every paragraph must have claim, evidence, and analysis",
            "claim-evidence-analysis is required",
            "must follow claim, evidence, analysis",
        ]
        for b in banned_formula:
            assert b not in low, f"AI imposed a rigid paragraph formula: {invitation!r}"

        pytest.m4_turn1 = data

    def test_turn2_revise_theory_shifts(self, client, paragraph_session):
        prev = getattr(pytest, "m4_turn1", None)
        assert prev is not None
        revised = (
            "The clearest cost of downtown car traffic is space. Private cars "
            "occupy the majority of road area while carrying a minority of "
            "travelers, which means that every lane devoted to them is a lane "
            "not serving the buses, deliveries, and emergency vehicles the "
            "city actually depends on."
        )
        status, data, err = sse_interact(
            client, paragraph_session["id"],
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
        pytest.m4_turn2 = data

    def test_turn3_answer_history_grows(self, client, paragraph_session):
        prev = getattr(pytest, "m4_turn2", None)
        assert prev is not None
        status, data, err = sse_interact(
            client, paragraph_session["id"],
            {"kind": "answer", "content": (
                "I want this paragraph to establish that space, not emissions, "
                "is the strongest argument for reducing car traffic. It sets "
                "up the opportunity-cost frame the rest of the essay develops."
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
        pytest.m4_turn3 = data

    def test_turn4_revise_reliability(self, client, paragraph_session):
        prev = getattr(pytest, "m4_turn3", None)
        assert prev is not None
        revised_again = (
            "The clearest cost of downtown car traffic is space. Private cars "
            "occupy the majority of road area while carrying a minority of "
            "travelers, which means every lane devoted to them is a lane not "
            "serving buses, deliveries, and emergency vehicles. This "
            "opportunity-cost logic, not emissions alone, is what this essay "
            "will develop across the next three sections."
        )
        status, data, err = sse_interact(
            client, paragraph_session["id"],
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

        assert len(data["interactions"]) == 4
        for ir in data["interactions"]:
            assert 2 <= len(ir["candidate_invitations"]) <= 3
            assert ir["selected_invitation"]["invitation"].strip()


# ---- Genre sensitivity: no forced claim-evidence-analysis ------------------
class TestGenreSensitivity:
    def test_narrative_paragraph_not_forced_into_argument(self, client, narrative_session):
        narrative = (
            "The 7:14 was already packed when I squeezed on. A man's umbrella "
            "dripped onto my shoe. Somewhere near the bridge the train "
            "stopped, the lights flickered, and for a moment the whole car "
            "went silent and still."
        )
        status, data, err = sse_interact(
            client, narrative_session["id"],
            {"kind": "writing", "content": narrative},
        )
        assert status == 200, f"status={status} err={err}"
        assert err is None
        assert data is not None
        elapsed = data.get("_elapsed_seconds")
        assert elapsed is not None and elapsed < 60

        invitation = data["turns"][-1]["content"].strip()
        low = invitation.lower()

        # Must NOT demand a topic sentence or claim/evidence/analysis for narrative
        banned = [
            "state your claim",
            "add a claim",
            "you need a claim",
            "claim, evidence, and analysis",
            "claim-evidence-analysis",
            "must start with a topic sentence",
            "topic sentence must be first",
            "add a thesis to this paragraph",
            "state your argument",
        ]
        for b in banned:
            assert b not in low, (
                f"Narrative was forced into argumentative claim-evidence structure: {invitation!r}"
            )

    def test_reflective_paragraph_uncertainty_honored(self, client, reflective_session):
        reflective = (
            "I am not sure whether I hate the traffic or depend on it. The "
            "jams are maddening, yet the car is the only place all day where "
            "no one asks anything of me. Maybe what I resent is not the "
            "congestion but the fact that I need it."
        )
        status, data, err = sse_interact(
            client, reflective_session["id"],
            {"kind": "writing", "content": reflective},
        )
        assert status == 200, f"status={status} err={err}"
        assert err is None
        assert data is not None
        elapsed = data.get("_elapsed_seconds")
        assert elapsed is not None and elapsed < 60

        invitation = data["turns"][-1]["content"].strip()
        low = invitation.lower()
        banned = [
            "claim, evidence, and analysis",
            "claim-evidence-analysis",
            "resolve the contradiction",  # reflective paragraphs may hold contradiction
            "you must pick a side",
        ]
        for b in banned:
            assert b not in low, (
                f"Reflective paragraph was pushed to resolve uncertainty: {invitation!r}"
            )


# ---- Section-level retrieval bounded (regression M3) -----------------------
class TestSectionLevelRetrievalLog:
    """The M4 log line stays the same as M3: '[interact] domains/sections={...}
    reasoner_prompt_bytes=NNNN'. Prompt should remain bounded even now that a
    third domain (Paragraph Purpose) is enriched to ~31 fields."""

    def test_recent_prompt_bytes_bounded(self):
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
            "M3 section-level retrieval log format may have regressed."
        )
        recent = entries[-10:]
        for domains_str, size in recent:
            # Even with 3 enriched domains, section filter should keep prompts
            # well below the ~50KB whole-model dump. Empirical M3 ceiling was
            # ~26KB; keeping a slightly looser M4 ceiling of 32KB to account
            # for turns where Paragraph Purpose + Thesis + Opening co-occur
            # (each still filtered to sections rather than the full record).
            assert size <= 32000, (
                f"reasoner_prompt_bytes={size} for {domains_str} exceeds 32KB "
                f"— section-level retrieval may not be filtering as intended."
            )
        sizes = [s for _, s in recent]
        median = sorted(sizes)[len(sizes) // 2]
        assert median <= 22000, (
            f"median reasoner_prompt_bytes={median} across recent turns is too high; "
            f"section-level retrieval expected to keep median <= 22KB. sizes={sizes}"
        )
        print(f"recent domains/sections + sizes: {recent}")

    def test_log_reports_per_domain_section_counts(self):
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
        assert entries, "No M4 domains/sections log lines found"
        import ast
        latest = entries[-1]
        try:
            parsed = ast.literal_eval(latest)
        except Exception as e:  # noqa: BLE001
            pytest.fail(f"Could not parse domains/sections payload {latest!r}: {e}")
        assert isinstance(parsed, dict) and parsed, f"payload is not a non-empty dict: {parsed!r}"
        for name, count in parsed.items():
            assert name in CANONICAL_DOMAIN_NAMES, f"unknown domain in log: {name!r}"
            assert isinstance(count, int) and count >= 0


# ---- Regression: validation ------------------------------------------------
class TestValidationRegression:
    def test_empty_content_returns_400(self, client, paragraph_session):
        r = client.post(
            f"{API}/sessions/{paragraph_session['id']}/interact",
            json={"kind": "writing", "content": "   "},
            timeout=15,
        )
        assert r.status_code == 400

    def test_missing_session_returns_404(self, client):
        missing = f"nope-m4-{int(time.time())}"
        r = client.get(f"{API}/sessions/{missing}", timeout=15)
        assert r.status_code == 404
        r2 = client.post(
            f"{API}/sessions/{missing}/interact",
            json={"kind": "writing", "content": "hello"},
            timeout=15,
        )
        assert r2.status_code == 404


# ---- Section-filter helper (unit, no LLM) ----------------------------------
class TestSectionFilterHelperOnParagraph:
    def test_get_relevant_domain_data_filters_paragraph_sections(self):
        import importlib
        import sys
        sys.path.insert(0, "/app/backend")
        srv = importlib.import_module("server")
        selections = [
            {"domain_name": PARAGRAPH_DOMAIN, "sections": [
                "candidate_developmental_invitations",
                "observable_organizations",
                "genre_sensitivity",
            ]},
        ]
        recs = srv.get_relevant_domain_data(selections)
        assert len(recs) == 1
        rec = recs[0]
        for k in srv.ALWAYS_KEYS:
            if k in PARAGRAPH_RECORD:
                assert k in rec, f"ALWAYS key {k!r} missing"
        for k in [
            "candidate_developmental_invitations",
            "observable_organizations",
            "genre_sensitivity",
        ]:
            assert k in rec
        # Unrequested sections excluded
        for k in ("possible_differentiations", "common_misunderstandings"):
            assert k not in rec, f"unrequested section {k!r} leaked in"
