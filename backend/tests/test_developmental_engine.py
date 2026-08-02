"""Backend tests for the Developmental Guide Engine (iteration_4).

Milestone under test:
- /api/sessions/{id}/interact is now an SSE StreamingResponse (text/event-stream).
  Heartbeats keep the connection warm past Cloudflare's ~60s edge cap. A final
  `event: done` line carries the full session JSON (or `event: error` on
  failure). Prompts have been slimmed and a BREVITY rule added so all turns
  finish comfortably under 60s.
- Domain-independent reasoning engine + domain-specific Canonical Writing
  Model (13 domains loaded as DATA).
- Session persists: telos (A), interactions (B, with candidate_invitations +
  selected_invitation + observed_reorganization), theory (C, one evolving
  provisional working theory with currently_relevant_domains), theory_history
  (previous theories preserved, not overwritten), turns.
- No stages / levels / scores anywhere.
- Teacher can revise the telos via PATCH /api/sessions/{id}/telos.

Run serially:  pytest /app/backend/tests/test_developmental_engine.py -v -n 0
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
    # fall back to the frontend .env so the tests can be run from the backend
    _envp = Path("/app/frontend/.env")
    if _envp.exists():
        for _line in _envp.read_text().splitlines():
            if _line.strip().startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = _line.split("=", 1)[1].strip()
                break
assert BASE_URL, "REACT_APP_BACKEND_URL must be set (in env or frontend/.env)"
BASE_URL = BASE_URL.rstrip("/")
API = f"{BASE_URL}/api"
LLM_TIMEOUT = 120  # stream should complete well under this


def sse_interact(client, sid, payload, timeout=LLM_TIMEOUT):
    """POST to /interact and consume the SSE stream.

    Returns a tuple (status_code, done_json_or_none, error_detail_or_none).
    """
    started = time.time()
    with client.post(
        f"{API}/sessions/{sid}/interact",
        json=payload,
        stream=True,
        timeout=timeout,
        headers={"Accept": "text/event-stream"},
    ) as r:
        if r.status_code != 200:
            # try to read a body for context but don't blow up on binary
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
                        continue  # heartbeat comment
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
        # attach elapsed to done payload for downstream inspection if useful
        if done_payload is not None:
            done_payload.setdefault("_elapsed_seconds", elapsed)
        return r.status_code, done_payload, error_detail


# Load the 13 canonical domain names once
CANONICAL_PATH = Path("/app/backend/canonical_writing_model.json")
with open(CANONICAL_PATH, "r") as f:
    CANONICAL = json.load(f)
CANONICAL_DOMAIN_NAMES = [d["domain_name"] for d in CANONICAL["domains"]]
assert len(CANONICAL_DOMAIN_NAMES) == 13, (
    f"Expected 13 canonical domains, got {len(CANONICAL_DOMAIN_NAMES)}"
)

# Stage / score language that must NOT leak into student-facing text
STAGE_SCORE_PATTERNS = [
    r"\bstage\s*\d\b",
    r"\blevel\s*\d\b",
    r"\bgrade\s*\d\b",
    r"\b\d+\s*/\s*10\b",
    r"\b\d+\s*out\s*of\s*10\b",
    r"\bscore[sd]?\b\s*\d",
    r"\brubric\b",
    r"\btrait\s*score\b",
    r"\bdevelopmental\s*stage\s*\d\b",
]


def _has_stage_or_score_language(text: str) -> bool:
    low = text.lower()
    for pat in STAGE_SCORE_PATTERNS:
        if re.search(pat, low):
            return True
    return False


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def created_session(client):
    payload = {
        "assignment": "TEST_ Write an argumentative essay on whether cities should ban cars from downtown cores.",
        "pedagogical_purpose": (
            "Students should learn to organize an argument so each paragraph "
            "advances a single claim toward the thesis."
        ),
        "current_writing_task": "Draft the opening two paragraphs establishing your position.",
        "teacher_notes": "TEST_ student tends to list ideas rather than connect them.",
    }
    r = client.post(f"{API}/sessions", json=payload, timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    assert isinstance(data.get("id"), str) and data["id"]
    assert data["assignment"] == payload["assignment"]
    assert data["pedagogical_purpose"] == payload["pedagogical_purpose"]
    assert data["current_writing_task"] == payload["current_writing_task"]
    assert data["turns"] == []
    assert data["interactions"] == []
    assert data["theory_history"] == []

    telos = data["telos"]
    assert telos["governing_pedagogical_purpose"] == payload["pedagogical_purpose"]
    assert telos["immediate_task_purpose"] == payload["current_writing_task"]
    assert telos["assignment_context"] == payload["assignment"]
    assert telos["teacher_intentions"] == payload["teacher_notes"]

    theory = data["theory"]
    for k in [
        "current_telos", "current_organization",
        "observed_differentiations", "observed_integrations",
        "observed_coordinations", "emerging_intentional_control",
        "unresolved_tensions", "cultural_resources_in_use",
        "potential_cultural_resources", "possible_reorganizations",
        "current_uncertainty", "supporting_evidence",
        "complicating_evidence", "currently_relevant_domains",
        "changes_since_previous",
    ]:
        assert k in theory, f"theory missing key {k}"
    assert theory["currently_relevant_domains"] == []
    return data


# ---------------------------------------------------------------------------
# Session creation (A — telos seeded from teacher inputs)
# ---------------------------------------------------------------------------
class TestSessionCreation:
    def test_session_created_with_seeded_telos(self, created_session):
        assert created_session["turns"] == []
        assert isinstance(created_session["telos"], dict)
        assert created_session["telos"]["governing_pedagogical_purpose"].strip() != ""
        assert created_session["telos"]["assignment_context"].strip() != ""


# ---------------------------------------------------------------------------
# First writing turn (SSE): 200 + done event with full session,
# currently_relevant_domains from canonical model, 2-3 candidate invitations,
# one selected, observed_reorganization present, theory_history preserves
# the empty initial theory as v1.
# ---------------------------------------------------------------------------
class TestFirstInteract:
    def test_first_writing_populates_theory_and_history(self, client, created_session):
        payload = {
            "kind": "writing",
            "content": (
                "Cars are bad. They cause pollution. Also they cause traffic. "
                "Also they are noisy. I think downtown should ban them because "
                "of these reasons. Downtown is where people live and work so "
                "it is important to make it nice."
            ),
        }
        status, data, err = sse_interact(client, created_session["id"], payload)
        assert status == 200, f"Expected 200, got {status}. err={err}"
        assert err is None, f"SSE emitted error: {err}"
        assert data is not None, "SSE completed without a done event"

        elapsed = data.get("_elapsed_seconds")
        assert elapsed is not None and elapsed < 60, (
            f"Turn 1 took {elapsed:.1f}s (must be <60s to stay under edge cap)"
        )
        pytest.first_interact_response = data

        assert len(data["turns"]) == 2
        assert data["turns"][0]["role"] == "student" and data["turns"][0]["kind"] == "writing"
        assert data["turns"][1]["role"] == "ai" and data["turns"][1]["kind"] == "invitation"
        invitation = data["turns"][1]["content"].strip()
        assert invitation, "AI invitation is empty"

        # AI must NOT rewrite the student text
        assert "Cars are bad. They cause pollution." not in invitation, (
            "AI appears to have rewritten the student's paragraph"
        )
        assert not (invitation.startswith("1.") and "2." in invitation and "3." in invitation), (
            "AI produced a numbered list of errors instead of a single invitation"
        )
        assert not _has_stage_or_score_language(invitation), (
            f"Invitation leaks stage/score language: {invitation!r}"
        )

        theory = data["theory"]
        rel = theory["currently_relevant_domains"]
        assert isinstance(rel, list) and len(rel) >= 1, (
            f"currently_relevant_domains empty after first turn: {rel!r}"
        )
        for name in rel:
            assert name in CANONICAL_DOMAIN_NAMES, (
                f"'{name}' is not one of the 13 canonical domains {CANONICAL_DOMAIN_NAMES}"
            )
        assert theory["current_organization"].strip() != ""

        assert len(data["interactions"]) == 1
        ir = data["interactions"][-1]
        assert 2 <= len(ir["candidate_invitations"]) <= 3, (
            f"expected 2-3 candidate_invitations, got {len(ir['candidate_invitations'])}"
        )
        assert ir["selected_invitation"]["invitation"].strip() != ""
        assert ir["observed_reorganization"].strip() != ""

        assert len(data["theory_history"]) == 1
        snap0 = data["theory_history"][0]
        assert snap0["version"] == 1
        assert snap0["theory"]["currently_relevant_domains"] == [], (
            "theory_history[0] should preserve the empty initial theory, not the new one"
        )

        theory_blob = json.dumps(theory)
        assert not _has_stage_or_score_language(theory_blob), (
            "Stage/score language leaked into theory"
        )


# ---------------------------------------------------------------------------
# Second interact (revise) — this was the CRITICAL 502 case in iteration_3.
# With SSE + slimmed prompts, this must return 200 with a done event well
# under 60s. theory_history grows to 2 preserving the FIRST theory,
# changes_since_previous is not 'initial'.
# ---------------------------------------------------------------------------
class TestSecondInteract:
    def test_second_interact_revises_theory_and_history(self, client, created_session):
        first = getattr(pytest, "first_interact_response", None)
        assert first is not None, "First interact must run before this test"
        first_invitation = first["turns"][1]["content"].strip()
        first_domains = set(first["theory"]["currently_relevant_domains"])

        revised_draft = (
            "Banning cars from downtown would make the core dramatically more "
            "livable, and every part of my argument hangs from that single "
            "claim. First, air quality: without tailpipe exhaust concentrated "
            "in a few blocks, the people who work and live downtown breathe "
            "cleaner air, which is the basic condition of a livable place.\n\n"
            "Second, foot traffic and small shops: when streets are for "
            "people, walkers linger, and local businesses that depend on "
            "casual browsing — bookstores, cafes, produce stands — actually "
            "survive. Each of these follows from the livability claim; I am "
            "no longer just listing complaints about cars."
        )
        status, data, err = sse_interact(
            client, created_session["id"],
            {"kind": "revise", "content": revised_draft},
        )
        assert status == 200, f"Expected 200, got {status}. err={err}"
        assert err is None, f"SSE emitted error on turn 2: {err}"
        assert data is not None, "SSE completed without a done event"

        elapsed = data.get("_elapsed_seconds")
        assert elapsed is not None and elapsed < 60, (
            f"Turn 2 took {elapsed:.1f}s (must be <60s — this is the regression case)"
        )
        pytest.second_interact_response = data

        assert len(data["turns"]) == 4
        assert data["turns"][2]["kind"] == "revise"
        assert data["turns"][3]["role"] == "ai"

        second_invitation = data["turns"][3]["content"].strip()
        assert second_invitation != first_invitation
        assert not _has_stage_or_score_language(second_invitation)

        low = second_invitation.lower()
        for phrase in [
            "haven't revised", "have not revised", "you didn't revise",
            "no revision", "still the same draft", "same as before",
            "identical to your previous",
        ]:
            assert phrase not in low, (
                f"Coach denied the revision with {phrase!r}: {second_invitation!r}"
            )

        assert len(data["theory_history"]) == 2
        assert data["theory_history"][0]["version"] == 1
        assert data["theory_history"][1]["version"] == 2
        v2_domains = set(data["theory_history"][1]["theory"]["currently_relevant_domains"])
        assert v2_domains == first_domains, (
            "theory_history[1] should preserve the first-turn theory's currently_relevant_domains"
        )

        changes = data["theory"]["changes_since_previous"].strip().lower()
        assert changes != "" and changes != "initial", (
            f"changes_since_previous should reflect revision, got {changes!r}"
        )

        rel = data["theory"]["currently_relevant_domains"]
        assert len(rel) >= 1
        for name in rel:
            assert name in CANONICAL_DOMAIN_NAMES

        assert len(data["interactions"]) == 2
        latest = data["interactions"][-1]
        assert 2 <= len(latest["candidate_invitations"]) <= 3
        assert latest["selected_invitation"]["invitation"].strip() != ""

        assert isinstance(data["theory"], dict)
        assert not _has_stage_or_score_language(json.dumps(data["theory"]))
        assert not _has_stage_or_score_language(json.dumps(data["interactions"]))


# ---------------------------------------------------------------------------
# Third interact (answer) — validates a 3-turn conversation completes without
# 502 (writing -> revise -> answer). theory_history grows to 3.
# ---------------------------------------------------------------------------
class TestThirdInteract:
    def test_third_interact_answer_turn(self, client, created_session):
        second = getattr(pytest, "second_interact_response", None)
        assert second is not None, "Second interact must run before this test"

        answer_content = (
            "The single claim that ties everything together is that banning "
            "cars downtown makes the core more livable. Air quality, "
            "walkability, and small-business survival are all consequences "
            "of that livability claim rather than separate reasons."
        )
        status, data, err = sse_interact(
            client, created_session["id"],
            {"kind": "answer", "content": answer_content},
        )
        assert status == 200, f"Expected 200, got {status}. err={err}"
        assert err is None, f"SSE emitted error on turn 3: {err}"
        assert data is not None, "SSE completed without a done event"

        elapsed = data.get("_elapsed_seconds")
        assert elapsed is not None and elapsed < 60, (
            f"Turn 3 took {elapsed:.1f}s (must be <60s)"
        )
        pytest.third_interact_response = data

        assert len(data["turns"]) == 6
        assert data["turns"][4]["kind"] == "answer"
        assert data["turns"][5]["role"] == "ai"

        third_invitation = data["turns"][5]["content"].strip()
        assert third_invitation
        assert not _has_stage_or_score_language(third_invitation)

        assert len(data["theory_history"]) == 3
        versions = [s["version"] for s in data["theory_history"]]
        assert versions == [1, 2, 3]

        # v3 preserves the SECOND theory (not the third)
        v3_snap = data["theory_history"][2]
        assert set(v3_snap["theory"]["currently_relevant_domains"]) == set(
            second["theory"]["currently_relevant_domains"]
        ), "theory_history[2] should preserve the second-turn theory"

        assert len(data["interactions"]) == 3
        latest = data["interactions"][-1]
        assert 2 <= len(latest["candidate_invitations"]) <= 3
        assert latest["selected_invitation"]["invitation"].strip() != ""


# ---------------------------------------------------------------------------
# Fourth interact (revise) — validates the full 4-turn flow required by
# iteration_5 (writing -> revise -> answer -> revise). theory_history grows
# to 4. Also asserts the two-stage domain-selection ceiling: no turn should
# report more than 3 currently_relevant_domains.
# ---------------------------------------------------------------------------
class TestFourthInteract:
    def test_fourth_interact_second_revise(self, client, created_session):
        third = getattr(pytest, "third_interact_response", None)
        assert third is not None, "Third interact must run before this test"

        revised_again = (
            "Banning cars from downtown makes the core dramatically more "
            "livable — that single livability claim now governs every "
            "paragraph. First, cleaner air: with tailpipe exhaust removed "
            "from the densest blocks, the people who actually live and work "
            "downtown breathe air that is not a daily hazard, and livability "
            "starts with breathable air.\n\n"
            "Second, walkable streets: when the roadbed belongs to people, "
            "walkers linger, browse, and stop, and the small businesses "
            "that depend on that lingering — the independent bookstores, "
            "cafes, and produce stands — actually survive the decade. "
            "Livability, in other words, is not decoration; it is the "
            "condition that lets a downtown remain a downtown, and every "
            "reason below serves that claim rather than standing beside it."
        )
        status, data, err = sse_interact(
            client, created_session["id"],
            {"kind": "revise", "content": revised_again},
        )
        assert status == 200, f"Expected 200, got {status}. err={err}"
        assert err is None, f"SSE emitted error on turn 4: {err}"
        assert data is not None, "SSE completed without a done event"

        elapsed = data.get("_elapsed_seconds")
        assert elapsed is not None and elapsed < 60, (
            f"Turn 4 took {elapsed:.1f}s (must be <60s to stay under edge cap)"
        )
        pytest.fourth_interact_response = data

        assert len(data["turns"]) == 8
        assert data["turns"][6]["kind"] == "revise"
        assert data["turns"][7]["role"] == "ai" and data["turns"][7]["kind"] == "invitation"

        fourth_invitation = data["turns"][7]["content"].strip()
        assert fourth_invitation
        assert not _has_stage_or_score_language(fourth_invitation)
        low = fourth_invitation.lower()
        for phrase in [
            "haven't revised", "have not revised", "you didn't revise",
            "no revision", "still the same draft", "same as before",
        ]:
            assert phrase not in low, (
                f"Coach denied the revision on turn 4 with {phrase!r}: {fourth_invitation!r}"
            )
        # AI must NOT rewrite the student's revised paragraph
        assert "Banning cars from downtown makes the core dramatically more livable" not in fourth_invitation, (
            "AI appears to have echoed/rewritten the student's revised paragraph on turn 4"
        )

        # theory_history grows to 4, versions preserved
        assert len(data["theory_history"]) == 4
        versions = [s["version"] for s in data["theory_history"]]
        assert versions == [1, 2, 3, 4]

        # v4 preserves the THIRD theory (snapshot BEFORE the update)
        v4_snap = data["theory_history"][3]
        assert set(v4_snap["theory"]["currently_relevant_domains"]) == set(
            third["theory"]["currently_relevant_domains"]
        ), "theory_history[3] should preserve the third-turn theory"

        # Two-stage selection ceiling: every turn's currently_relevant_domains
        # is a non-empty subset of the 13 canonical names, at most 3.
        for i, snap in enumerate(data["theory_history"]):
            rel = snap["theory"]["currently_relevant_domains"]
            if i == 0:
                # v1 is the empty initial theory
                continue
            assert 1 <= len(rel) <= 3, (
                f"theory_history[{i}] currently_relevant_domains has {len(rel)} entries (must be 1-3): {rel}"
            )
            for name in rel:
                assert name in CANONICAL_DOMAIN_NAMES

        current_rel = data["theory"]["currently_relevant_domains"]
        assert 1 <= len(current_rel) <= 3, (
            f"Turn 4 currently_relevant_domains has {len(current_rel)} entries: {current_rel}"
        )

        # Sanity: domains across the 4 turns are not mechanically identical on
        # every single turn — expect at least SOME movement over 4 turns.
        turn1_domains = tuple(sorted(data["theory_history"][1]["theory"]["currently_relevant_domains"]))
        turn2_domains = tuple(sorted(data["theory_history"][2]["theory"]["currently_relevant_domains"]))
        turn3_domains = tuple(sorted(data["theory_history"][3]["theory"]["currently_relevant_domains"]))
        turn4_domains = tuple(sorted(current_rel))
        all_same = (turn1_domains == turn2_domains == turn3_domains == turn4_domains)
        # Soft assertion — if the model does keep them identical every turn we
        # only warn (the primary correctness contract is that the LLM MAY
        # change them). We flag if truly identical every turn.
        if all_same:
            print(
                f"WARN: currently_relevant_domains identical across all 4 turns: {turn1_domains}"
            )

        assert len(data["interactions"]) == 4
        latest = data["interactions"][-1]
        assert 2 <= len(latest["candidate_invitations"]) <= 3
        assert latest["selected_invitation"]["invitation"].strip() != ""

        assert not _has_stage_or_score_language(json.dumps(data["theory"]))
        assert not _has_stage_or_score_language(json.dumps(data["interactions"]))


# ---------------------------------------------------------------------------
# Two-stage domain selection: verify from backend logs that the reasoner
# prompt (STAGE B) stays small (roughly <=7KB), proving only the selected
# domains' full records are being sent — not the whole 13-domain model.
# ---------------------------------------------------------------------------
class TestTwoStageSelection:
    def test_reasoner_prompt_bytes_within_budget(self):
        log_paths = sorted(Path("/var/log/supervisor").glob("backend.*.log"))
        assert log_paths, "No backend supervisor logs found at /var/log/supervisor"
        # Milestone 3 changed the log format to '[interact] domains/sections={...} reasoner_prompt_bytes=NNNN'
        pat = re.compile(r"\[interact\]\s+domains/sections=(\{[^}]*\})\s+reasoner_prompt_bytes=(\d+)")
        entries = []
        for p in log_paths:
            try:
                text = p.read_text(errors="ignore")
            except Exception:
                continue
            for m in pat.finditer(text):
                entries.append((m.group(1), int(m.group(2))))
        assert entries, (
            "No '[interact] turn domains=... reasoner_prompt_bytes=NNNN' lines found in backend logs"
        )
        # Consider only the most recent entries from this test run
        recent = entries[-4:] if len(entries) >= 4 else entries
        # NOTE: Milestone 2 enriched the 'Opening / Introduction' domain to ~31
        # fields (~15KB). When that domain is selected in STAGE A, the STAGE B
        # reasoner prompt grows to ~22-24KB even though only 1-3 domains are
        # included. This budget accommodates that enrichment while still
        # ensuring the two-stage selection is NOT sending the whole 13-domain
        # model (which would be ~35KB+).
        for domains_str, size in recent:
            assert size <= 32000, (
                f"reasoner_prompt_bytes={size} for domains={domains_str} — "
                f"expected <=32KB (multiple enriched domains, e.g. Thesis + Paragraph Purpose, may co-occur). "
                f"Two-stage selection may not be limiting payload as intended."
            )
        print(f"reasoner_prompt_bytes over recent turns: {recent}")


# ---------------------------------------------------------------------------
# Teacher can revise the telos (PATCH /api/sessions/{id}/telos)
# ---------------------------------------------------------------------------
class TestTelosEdit:
    def test_patch_telos_updates_session_and_appends_teacher_edit(self, client, created_session):
        sid = created_session["id"]
        new_purpose = (
            "Students should learn to make every paragraph coordinate with a "
            "single governing claim about livability."
        )
        new_task = "Revise the opening two paragraphs so each supports the livability claim."
        r = client.patch(
            f"{API}/sessions/{sid}/telos",
            json={
                "pedagogical_purpose": new_purpose,
                "current_writing_task": new_task,
                "note": "TEST_ narrowing purpose after seeing first revision.",
            },
            timeout=30,
        )
        assert r.status_code == 200, r.text
        data = r.json()

        assert data["pedagogical_purpose"] == new_purpose
        assert data["current_writing_task"] == new_task
        assert data["telos"]["governing_pedagogical_purpose"] == new_purpose
        assert data["telos"]["immediate_task_purpose"] == new_task
        assert data["telos"]["telos_changed"].strip() != ""

        assert len(data["teacher_edits"]) >= 1
        latest_edit = data["teacher_edits"][-1]
        assert "changes" in latest_edit
        assert "pedagogical_purpose" in latest_edit["changes"]
        assert latest_edit["changes"]["pedagogical_purpose"]["to"] == new_purpose

        g = client.get(f"{API}/sessions/{sid}", timeout=15)
        assert g.status_code == 200
        gdata = g.json()
        assert gdata["pedagogical_purpose"] == new_purpose
        assert gdata["current_writing_task"] == new_task
        assert gdata["telos"]["governing_pedagogical_purpose"] == new_purpose


# ---------------------------------------------------------------------------
# Persistence: GET returns session with turns, theory, theory_history, interactions
# ---------------------------------------------------------------------------
class TestPersistence:
    def test_get_session_returns_full_state(self, client, created_session):
        r = client.get(f"{API}/sessions/{created_session['id']}", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["id"] == created_session["id"]
        assert len(data["turns"]) == 8
        assert len(data["interactions"]) == 4
        assert len(data["theory_history"]) == 4
        assert data["turns"][1]["role"] == "ai"
        assert data["turns"][3]["role"] == "ai"
        assert data["turns"][5]["role"] == "ai"
        assert data["turns"][7]["role"] == "ai"
        assert len(data["theory"]["currently_relevant_domains"]) >= 1


# ---------------------------------------------------------------------------
# Regression: empty -> 400, missing session -> 404
# ---------------------------------------------------------------------------
class TestValidation:
    def test_empty_content_returns_400(self, client, created_session):
        r = client.post(
            f"{API}/sessions/{created_session['id']}/interact",
            json={"kind": "writing", "content": "   "},
            timeout=15,
        )
        assert r.status_code == 400, r.text

    def test_missing_session_returns_404(self, client):
        missing = f"nope-{int(time.time())}"
        r = client.get(f"{API}/sessions/{missing}", timeout=15)
        assert r.status_code == 404

        r2 = client.post(
            f"{API}/sessions/{missing}/interact",
            json={"kind": "writing", "content": "hello"},
            timeout=15,
        )
        assert r2.status_code == 404

        r3 = client.patch(
            f"{API}/sessions/{missing}/telos",
            json={"pedagogical_purpose": "x"},
            timeout=15,
        )
        assert r3.status_code == 404
