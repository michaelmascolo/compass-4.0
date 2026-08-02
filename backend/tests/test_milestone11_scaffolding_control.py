"""Milestone 11 backend acceptance — Recursive Developmental Scaffolding Controller.

Verifies:
  (a) Every interact populates theory.scaffolding_control with:
        - primary_target (NON-EMPTY),
        - instructional_mode in the valid set,
        - cycle_status in {continue, consolidate_and_return, stop}.
  (b) SINGLE TARGET on a multi-weakness draft:
        - exactly ONE primary_target,
        - NON-EMPTY postponed list,
        - the AI's single student-facing invitation addresses only that one target
          (does not try to fix everything).
  (c) MODE ADAPTS:
        - a student MISSING a concept tends toward explicit_instruction.
        - a capable student NEAR insight tends toward developmental_question.
  (d) STOPPING RULE:
        - explicit independence signal ("let me take it from here...") forces
          cycle_status in {stop, consolidate_and_return} with a stopping_reason
          about independence, and does NOT open a new instructional target.
  (e) CONSOLIDATION + NO ENDLESS RECURSION:
        - a two-turn writing->revise where the revision clearly improves triggers
          consolidation (mode=consolidation OR intervention.type=consolidate OR
          cycle_status=consolidate_and_return).
        - across repeated revisions on the same point, the controller does not
          keep re-teaching the same target endlessly.
  (f) M6-M10 REGRESSION: cp.primary populated; pf/ef/cf applies=true on a
      supported body paragraph; concl.applies=true on an ending draft.
  (g) M1-M5A REGRESSION: theory_history v1..vN preserved; currently_relevant_domains
      1..3; intervention.focus='writing' + writing_not_content_check non-empty on
      ordinary drafts; no stage/level/grade/rubric leaks.

Run:  pytest /app/backend/tests/test_milestone11_scaffolding_control.py -v -n 0 -s
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

VALID_MODES = {
    "developmental_question",
    "explicit_instruction",
    "brief_demonstration",
    "guided_revision",
    "reflection",
    "consolidation",
}

VALID_CYCLE_STATUSES = {"continue", "consolidate_and_return", "stop"}

STAGE_SCORE_PATTERNS = [
    r"\bstage\s*\d\b", r"\blevel\s*\d\b", r"\bgrade\s*\d\b",
    r"\b\d+\s*/\s*10\b", r"\b\d+\s*out\s*of\s*10\b",
    r"\bscore[sd]?\b\s*\d", r"\brubric\b",
]


def _has_stage_score(text: str) -> bool:
    low = text.lower()
    return any(re.search(p, low) for p in STAGE_SCORE_PATTERNS)


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


def _sc(s):
    return s["theory"]["scaffolding_control"]


def _cp(s):
    return s["theory"]["communicative_purpose"]


def _assert_scaffolding_control_populated(s):
    """Every interact MUST populate scaffolding_control with required fields."""
    sc = _sc(s)
    assert isinstance(sc, dict), f"scaffolding_control missing/wrong shape: {sc!r}"
    pt = (sc.get("primary_target") or "").strip()
    assert pt != "", f"primary_target MUST be non-empty, got {sc!r}"
    mode = (sc.get("instructional_mode") or "").strip()
    assert mode in VALID_MODES, (
        f"instructional_mode must be one of {VALID_MODES}, got {mode!r} | sc={sc!r}"
    )
    cs = (sc.get("cycle_status") or "").strip()
    assert cs in VALID_CYCLE_STATUSES, (
        f"cycle_status must be one of {VALID_CYCLE_STATUSES}, got {cs!r} | sc={sc!r}"
    )
    return sc


def _assert_common_shape(s, weak_text=None):
    assert s.get("_saw_done_event") is True, "must see event: done"
    assert s.get("_elapsed_seconds", 999) < 180, (
        f"turn took too long: {s.get('_elapsed_seconds')}s"
    )
    ai = [t for t in s["turns"] if t["role"] == "ai"]
    student = [t for t in s["turns"] if t["role"] == "student"]
    assert s["turns"][-1]["role"] == "ai"
    # exactly ONE new ai turn per interact
    assert len(ai) == len(student) == len(s["interactions"])

    inv = _last_student_facing(s)
    if weak_text is not None:
        assert weak_text not in inv, "AI appears to have echoed/rewritten the student's text"
    assert not _has_stage_score(inv), f"stage/level/rubric leaked: {inv[:200]}"

    iv = _last_intervention(s)
    assert iv["type"] in VALID_INTERVENTION_TYPES

    sc = _assert_scaffolding_control_populated(s)
    return iv, inv, sc


ARG = "TEST_M11 Argue whether social media improves or harms teen friendships."
PA_ESSAY = "Develop the student as a writer of an argumentative essay."
TASK_DRAFT = "Draft your essay."


# ==========================================================================
# 1. Every interact populates scaffolding_control (single primary_target,
#    valid mode, valid cycle_status) on an ordinary draft.
# ==========================================================================
class TestScaffoldingControlPopulatedEveryTurn:
    def test_ordinary_draft_populates_scaffolding_control(self, client):
        sid = _new_session(client, ARG, PA_ESSAY, TASK_DRAFT)
        draft = (
            "Social media is a big topic today. Many teens use it every day and "
            "it affects their friendships in some way. I think it is harmful."
        )
        status, data, err = sse_interact_with_retry(
            client, sid, {"kind": "writing", "content": draft}
        )
        assert status == 200 and err is None and data is not None, f"err={err}"
        iv, inv, sc = _assert_common_shape(data, weak_text=draft)

        # M6 still populated
        assert _cp(data).get("primary", "").strip() != ""

        # M5A intact on ordinary draft
        assert iv["focus"] == "writing"
        assert iv["writing_not_content_check"].strip() != ""

        print(
            f"BASIC pt={sc['primary_target'][:60]!r} mode={sc['instructional_mode']!r} "
            f"cycle={sc['cycle_status']!r} postponed={len(sc.get('postponed', []))}"
        )


# ==========================================================================
# 2. SINGLE TARGET on a multi-weakness draft — one primary_target,
#    NON-EMPTY postponed, and the invitation addresses ONE target only.
# ==========================================================================
class TestSingleTargetOnMultiWeakness:
    def test_multi_weakness_draft_yields_one_target_and_postponed(self, client):
        sid = _new_session(client, ARG, PA_ESSAY, TASK_DRAFT)
        # Weaknesses simultaneously: fragmentary thesis, informal register, spelling
        # ("alot"), narrative-tangent (Sarah), formulaic conclusion + numbered reasons.
        draft = (
            "social media bad for friends. teens use phones alot. also my friend "
            "sarah posts alot. in conclusion social media harmful and thats my "
            "three reasons distraction and fake and addiction"
        )
        status, data, err = sse_interact_with_retry(
            client, sid, {"kind": "writing", "content": draft}
        )
        assert status == 200 and err is None and data is not None, f"err={err}"
        iv, inv, sc = _assert_common_shape(data, weak_text=draft)

        # NON-EMPTY postponed — controller must not try to fix everything.
        postponed = sc.get("postponed") or []
        assert isinstance(postponed, list) and len(postponed) >= 1, (
            f"postponed must contain at least one deferred opportunity, got {sc!r}"
        )
        # diagnosed_opportunities should generally exceed 1 given the draft.
        diagnosed = sc.get("diagnosed_opportunities") or []
        assert isinstance(diagnosed, list), f"diagnosed_opportunities must be a list, got {sc!r}"

        # Exactly ONE primary_target (a single string).
        assert isinstance(sc.get("primary_target"), str)

        # A rough heuristic: the single student-facing invitation should not
        # attempt to enumerate multiple simultaneous fixes. Count how many of
        # the coaching bullet-verbs it uses in imperative form.
        inv_low = inv.lower()
        multi_target_signals = [
            "first,", "second,", "third,", "next,", "additionally,",
            "1)", "2)", "3)", "also,", "furthermore,",
        ]
        hits = [s for s in multi_target_signals if s in inv_low]
        # Allow up to 1 (a stray "also,") — more than 1 suggests multi-target teaching.
        assert len(hits) <= 1, (
            f"invitation appears to teach multiple targets simultaneously: hits={hits} "
            f"| inv={inv[:300]!r}"
        )

        print(
            f"MULTI_WEAK pt={sc['primary_target'][:80]!r} mode={sc['instructional_mode']!r} "
            f"postponed={len(postponed)} diagnosed={len(diagnosed)}"
        )


# ==========================================================================
# 3. MODE ADAPTS — missing-concept vs near-insight.
# ==========================================================================
class TestModeAdapts:
    def test_missing_concept_tends_to_explicit_instruction(self, client):
        sid = _new_session(client, ARG, PA_ESSAY, TASK_DRAFT)
        # Meta-announcement / no claim — student is missing the concept of an
        # arguable thesis.
        draft = "My essay is about social media and friendship."
        status, data, err = sse_interact_with_retry(
            client, sid, {"kind": "writing", "content": draft}
        )
        assert status == 200 and err is None and data is not None, f"err={err}"
        iv, inv, sc = _assert_common_shape(data, weak_text=draft)

        # Prefer explicit_instruction, but accept brief_demonstration as a close
        # kin (both are teach-then-invite modes for missing concepts).
        assert sc["instructional_mode"] in {
            "explicit_instruction", "brief_demonstration",
        }, (
            f"missing-concept draft should tend toward explicit_instruction, "
            f"got mode={sc['instructional_mode']!r} | pt={sc['primary_target']!r}"
        )
        print(
            f"MISSING_CONCEPT mode={sc['instructional_mode']!r} "
            f"pt={sc['primary_target'][:60]!r}"
        )

    def test_capable_near_insight_tends_to_developmental_question(self, client):
        sid = _new_session(client, ARG, PA_ESSAY, TASK_DRAFT)
        # A capable student close to insight.
        draft = (
            "Social media strengthens weak-tie friendships while quietly eroding "
            "the close ones — every notification is a chance to feel connected "
            "without the cost of being fully present."
        )
        status, data, err = sse_interact_with_retry(
            client, sid, {"kind": "writing", "content": draft}
        )
        assert status == 200 and err is None and data is not None, f"err={err}"
        iv, inv, sc = _assert_common_shape(data, weak_text=draft)

        # Prefer developmental_question, but accept reflection as a close kin
        # (both are inquiry modes for capable students near insight).
        assert sc["instructional_mode"] in {
            "developmental_question", "reflection",
        }, (
            f"capable-near-insight draft should tend toward developmental_question, "
            f"got mode={sc['instructional_mode']!r} | pt={sc['primary_target']!r}"
        )
        print(
            f"NEAR_INSIGHT mode={sc['instructional_mode']!r} "
            f"pt={sc['primary_target'][:60]!r}"
        )


# ==========================================================================
# 4. STOPPING — explicit independence request stops the cycle.
# ==========================================================================
class TestIndependenceStops:
    def test_independence_request_stops_or_consolidates(self, client):
        sid = _new_session(client, ARG, PA_ESSAY, TASK_DRAFT)
        # First turn: an ordinary draft so the controller has something to consolidate.
        d0 = (
            "Social media harms teen friendships because it replaces presence "
            "with performance."
        )
        s0, data0, e0 = sse_interact_with_retry(
            client, sid, {"kind": "writing", "content": d0}
        )
        assert s0 == 200 and e0 is None and data0 is not None, f"err={e0}"
        _assert_common_shape(data0, weak_text=d0)

        # Second turn: explicit independence signal via 'answer' kind.
        indep = "Got it, let me take it from here and keep writing myself."
        s1, data1, e1 = sse_interact_with_retry(
            client, sid, {"kind": "answer", "content": indep}
        )
        assert s1 == 200 and e1 is None and data1 is not None, f"err={e1}"
        iv, inv, sc = _assert_common_shape(data1)

        # Must set stop or consolidate_and_return.
        assert sc["cycle_status"] in {"stop", "consolidate_and_return"}, (
            f"independence request MUST set cycle_status stop/consolidate_and_return, "
            f"got {sc['cycle_status']!r} | sc={sc!r}"
        )

        # Stopping reason should reference independence.
        reason_low = (sc.get("stopping_reason") or "").lower()
        indep_markers = [
            "independence", "independent", "on their own", "on your own",
            "hand back", "hand it back", "take it from here", "wants to proceed",
            "requests independence", "student requests",
        ]
        assert any(m in reason_low for m in indep_markers), (
            f"stopping_reason should reference independence, got "
            f"stopping_reason={reason_low!r}"
        )

        # The mode should reflect consolidation/reflection or an explicit hand-back;
        # accept the safer set here.
        assert sc["instructional_mode"] in {
            "consolidation", "reflection", "developmental_question",
        }, (
            f"independence turn mode unexpected: {sc['instructional_mode']!r}"
        )

        # Intervention type should not be instruct_then_invite (would be opening
        # a new instructional target).
        assert iv["type"] != "instruct_then_invite", (
            f"independence turn should NOT open a new instructional target, got "
            f"iv.type={iv['type']!r}"
        )

        print(
            f"INDEP cycle={sc['cycle_status']!r} reason={reason_low[:80]!r} "
            f"mode={sc['instructional_mode']!r} iv.type={iv['type']!r}"
        )


# ==========================================================================
# 5. CONSOLIDATION + NO ENDLESS RECURSION.
# ==========================================================================
class TestConsolidationNoRecursion:
    def test_revision_triggers_consolidation_and_no_endless_recursion(self, client):
        sid = _new_session(client, ARG, PA_ESSAY, TASK_DRAFT)
        # Turn 1 — weak claim; controller likely targets thesis/claim.
        d1 = "Social media is bad. Teens use it too much."
        s1, data1, e1 = sse_interact_with_retry(
            client, sid, {"kind": "writing", "content": d1}
        )
        assert s1 == 200 and e1 is None and data1 is not None, f"err={e1}"
        iv1, inv1, sc1 = _assert_common_shape(data1, weak_text=d1)
        target1 = sc1["primary_target"]

        # Turn 2 — a clear revision that absorbs the target: from
        # observation to arguable claim.
        revised = (
            "Social media harms teen friendships because it replaces the slow "
            "attention that intimacy requires with the constant performance of "
            "being available."
        )
        s2, data2, e2 = sse_interact_with_retry(
            client, sid, {"kind": "revise", "content": revised}
        )
        assert s2 == 200 and e2 is None and data2 is not None, f"err={e2}"
        iv2, inv2, sc2 = _assert_common_shape(data2, weak_text=revised)

        # Consolidation signal: mode==consolidation OR intervention.type==consolidate
        # OR cycle_status==consolidate_and_return OR the primary_target has shifted
        # (progressive scaffolding — not endless recursion on the same target).
        consolidated = (
            sc2["instructional_mode"] == "consolidation"
            or iv2["type"] == "consolidate"
            or sc2["cycle_status"] == "consolidate_and_return"
            or sc2["primary_target"].strip().lower() != target1.strip().lower()
        )
        assert consolidated, (
            f"revision should consolidate OR shift target; "
            f"target1={target1!r} target2={sc2['primary_target']!r} "
            f"mode2={sc2['instructional_mode']!r} iv.type={iv2['type']!r} "
            f"cycle2={sc2['cycle_status']!r}"
        )

        # Turn 3 — a further revision on the SAME point. The controller must not
        # keep re-teaching the very same target endlessly.
        revised2 = (
            "Social media harms teen friendships because it replaces sustained "
            "attention — the raw material of intimacy — with the constant, "
            "shallow performance of being available. What looks like closeness "
            "is often just proximity of signals."
        )
        s3, data3, e3 = sse_interact_with_retry(
            client, sid, {"kind": "revise", "content": revised2}
        )
        assert s3 == 200 and e3 is None and data3 is not None, f"err={e3}"
        iv3, inv3, sc3 = _assert_common_shape(data3, weak_text=revised2)

        # No endless recursion: either the target shifted OR the controller has
        # consolidated / is preparing to consolidate.
        no_recursion = (
            sc3["primary_target"].strip().lower() != target1.strip().lower()
            or sc3["instructional_mode"] == "consolidation"
            or iv3["type"] == "consolidate"
            or sc3["cycle_status"] in {"consolidate_and_return", "stop"}
        )
        assert no_recursion, (
            f"controller keeps re-teaching same target — endless recursion. "
            f"target1={target1!r} target3={sc3['primary_target']!r} "
            f"mode3={sc3['instructional_mode']!r} iv.type={iv3['type']!r} "
            f"cycle3={sc3['cycle_status']!r}"
        )

        # theory_history preserved
        assert len(data3["theory_history"]) == 3
        assert [snap["version"] for snap in data3["theory_history"]] == [1, 2, 3]

        # M5A intact throughout
        for i, (d, iv) in enumerate(((data1, iv1), (data2, iv2), (data3, iv3)), start=1):
            assert iv["focus"] == "writing", f"turn {i} focus must be 'writing'"
            assert iv["writing_not_content_check"].strip() != ""
            assert 1 <= len(d["theory"]["currently_relevant_domains"]) <= 3
            assert not _has_stage_score(_last_student_facing(d))

        print(
            f"CONSOL t1 pt={target1[:40]!r} t2 pt={sc2['primary_target'][:40]!r} "
            f"mode2={sc2['instructional_mode']!r} iv2={iv2['type']!r} "
            f"t3 pt={sc3['primary_target'][:40]!r} mode3={sc3['instructional_mode']!r} "
            f"cycle3={sc3['cycle_status']!r}"
        )


# ==========================================================================
# 6. M6-M10 preservation on a supported body paragraph.
# ==========================================================================
class TestM6toM10Regression:
    def test_supported_paragraph_preserves_prior_frameworks(self, client):
        sid = _new_session(
            client, ARG,
            "Help the student develop a supported paragraph.",
            "Draft a body paragraph.",
        )
        draft = (
            "Teens check their phones an average of 100 times a day, according "
            "to a 2023 study. That constant checking matters because it turns "
            "friendships into a habit of monitoring rather than sustained "
            "attention. Because attention builds intimacy, and monitoring "
            "interrupts it, friendships that live only through phones grow thin."
        )
        status, data, err = sse_interact_with_retry(
            client, sid, {"kind": "writing", "content": draft}
        )
        assert status == 200 and err is None and data is not None, f"err={err}"
        iv, inv, sc = _assert_common_shape(data, weak_text=draft)

        cp = data["theory"]["communicative_purpose"]
        pf = data["theory"]["paragraph_function"]
        ef = data["theory"]["evidence_function"]
        cf = data["theory"]["coherence_function"]

        assert cp["primary"].strip() != "", f"M6 primary empty: {cp!r}"
        assert pf["applies"] is True, f"M7 applies must be True, got {pf!r}"
        assert pf["purpose"].strip() != "", f"M7 purpose empty: {pf!r}"
        assert ef["applies"] is True, f"M8 applies must be True, got {ef!r}"
        assert ef["function"].strip() != "", f"M8 function empty: {ef!r}"
        assert cf["applies"] is True, f"M9 applies expected True, got {cf!r}"

        # Scaffolding controller populated even here.
        assert sc["primary_target"].strip() != ""
        assert sc["instructional_mode"] in VALID_MODES
        assert sc["cycle_status"] in VALID_CYCLE_STATUSES

        print(
            f"REG_M6-M9 cp={cp['primary'][:30]!r} pf={pf['applies']} "
            f"ef={ef['applies']} cf={cf['applies']} "
            f"sc.mode={sc['instructional_mode']!r} sc.cycle={sc['cycle_status']!r}"
        )

    def test_ending_draft_activates_m10_and_populates_sc(self, client):
        sid = _new_session(
            client, ARG,
            "Help the student write a conclusion that completes the essay's communicative purpose.",
            "Draft your conclusion.",
        )
        draft = (
            "So the danger was never that teens would stop talking — it's that "
            "constant contact can feel like closeness while quietly replacing it. "
            "What's worth protecting isn't the number of friends onscreen, but "
            "the few we still make time to be fully present with."
        )
        status, data, err = sse_interact_with_retry(
            client, sid, {"kind": "writing", "content": draft}
        )
        assert status == 200 and err is None and data is not None, f"err={err}"
        iv, inv, sc = _assert_common_shape(data, weak_text=draft)

        concl = data["theory"]["conclusion_function"]
        assert concl["applies"] is True, f"M10 applies must be True, got {concl!r}"
        assert (concl.get("completes_purpose") or "").strip() != ""

        assert sc["primary_target"].strip() != ""
        assert sc["instructional_mode"] in VALID_MODES
        assert sc["cycle_status"] in VALID_CYCLE_STATUSES

        print(
            f"REG_M10 concl.applies={concl['applies']} "
            f"sc.mode={sc['instructional_mode']!r} sc.cycle={sc['cycle_status']!r} "
            f"pt={sc['primary_target'][:50]!r}"
        )


# ==========================================================================
# 7. CRUD smoke — POST/GET/PATCH + default scaffolding_control shape.
# ==========================================================================
class TestSessionCrud:
    def test_create_get_patch_and_default_scaffolding_control(self, client):
        sid = _new_session(
            client,
            assignment="TEST_M11 crud smoke",
            purpose="Develop the writer.",
            task="Draft your essay.",
        )
        g = client.get(f"{API}/sessions/{sid}", timeout=15)
        assert g.status_code == 200
        body = g.json()
        assert body["id"] == sid

        sc = body["theory"]["scaffolding_control"]
        assert sc["current_unit"] == ""
        assert sc["diagnosed_opportunities"] == []
        assert sc["primary_target"] == ""
        assert sc["prioritization_rationale"] == ""
        assert sc["instructional_mode"] == ""
        assert sc["postponed"] == []
        assert sc["cycle_status"] == ""
        assert sc["stopping_reason"] == ""
        assert sc["future_opportunity"] == ""

        r = client.patch(
            f"{API}/sessions/{sid}/telos",
            json={
                "pedagogical_purpose": "Develop the writer of an argument.",
                "note": "TEST_M11 telos edit",
            },
            timeout=30,
        )
        assert r.status_code == 200
        body2 = r.json()
        assert body2["pedagogical_purpose"] == "Develop the writer of an argument."
        assert body2["telos"]["governing_pedagogical_purpose"] == (
            "Develop the writer of an argument."
        )

    def test_get_nonexistent(self, client):
        r = client.get(f"{API}/sessions/does-not-exist-m11-{int(time.time())}", timeout=15)
        assert r.status_code == 404
