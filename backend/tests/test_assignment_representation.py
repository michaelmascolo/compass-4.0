"""
Compass 2.0 Sprint 1 — Assignment Representation backend tests.

Covers:
- analyze (POST /sessions)
- interpret + diagnose + scaffold across 5 required learner-response variants
- 'I don't know' escalation
- operation loop (good + weak responses)
- restatement adequacy
- edit/restart (PATCH)
- confidence no-leak into student-facing text
"""
import os
import re
import pytest
import requests

def _load_backend_url():
    v = os.environ.get("REACT_APP_BACKEND_URL")
    if not v:
        env_path = "/app/frontend/.env"
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    if line.startswith("REACT_APP_BACKEND_URL="):
                        v = line.split("=", 1)[1].strip()
                        break
    if not v:
        raise RuntimeError("REACT_APP_BACKEND_URL not set")
    return v.rstrip("/")


BASE_URL = _load_backend_url()
API = f"{BASE_URL}/api/assignment"

SAMPLE = (
    "Compare fixed and growth mindsets. Explain how each mindset affects both the "
    "process and outcomes of learning. Use relevant examples to support your explanation."
)

# LLM calls are ~5-30s. Use generous timeout.
TIMEOUT = 120

_ALLOWED_STATUSES = {"understood", "developing", "needs_attention", "unconfirmed"}
_LEAK_PATTERNS = [
    re.compile(r"\bconfidence\b", re.I),
    re.compile(r"\b0?\.[0-9]{1,3}\s*(?:confidence|score)?", re.I),
    re.compile(r"\b\d{1,3}\s?%"),
]

# Forbidden phrasing that would indicate Compass wrote the answer/thesis/essay
_ANSWER_LEAK = [
    re.compile(r"\bthesis\s*statement\s*:", re.I),
    re.compile(r"\bhere('|)s\s+(a|an|the)\s+(essay|paragraph|thesis|outline)\b", re.I),
]


def _post(path, json_body=None):
    return requests.post(f"{API}{path}", json=json_body or {}, timeout=TIMEOUT)


def _patch(path, json_body):
    return requests.patch(f"{API}{path}", json=json_body, timeout=TIMEOUT)


def _get(path):
    return requests.get(f"{API}{path}", timeout=TIMEOUT)


def _leaks_confidence(scaffold: dict) -> bool:
    text = " ".join([
        str(scaffold.get("studentTask", "")),
        str(scaffold.get("expectedEvidence", "")),
        str(scaffold.get("nextIfSuccessful", "")),
        str(scaffold.get("nextIfUnsuccessful", "")),
        str(scaffold.get("relevant_wording", "")),
    ])
    return any(p.search(text) for p in _LEAK_PATTERNS)


def _contains_answer(scaffold: dict) -> bool:
    text = str(scaffold.get("studentTask", ""))
    return any(p.search(text) for p in _ANSWER_LEAK)


@pytest.fixture(scope="module")
def fresh_session():
    """Create one session for share where allowed (analyze test)."""
    r = _post("/sessions", {"assignment_text": SAMPLE})
    assert r.status_code == 200, r.text
    return r.json()


def _new_session():
    r = _post("/sessions", {"assignment_text": SAMPLE})
    assert r.status_code == 200, r.text
    return r.json()


# ---------- analyze ----------
class TestAnalyze:
    def test_create_session_analyze(self, fresh_session):
        s = fresh_session
        assert s["stage"] == "interpret"
        assert 3 <= len(s["demands"]) <= 6, f"demands count={len(s['demands'])}"
        for d in s["demands"]:
            assert d["label"]
            assert d["source"] in {"explicit", "inferred"}
            assert d["operation"]
            assert d["importance"] in {"essential", "supporting"}
            assert isinstance(d["derivable_from_assignment"], bool)
            if d["source"] == "explicit":
                assert d["supporting_wording"], f"explicit demand missing quote: {d['label']}"

    def test_empty_assignment_rejected(self):
        r = _post("/sessions", {"assignment_text": "   "})
        assert r.status_code == 400


# ---------- interpret variants ----------
INTERPRETATIONS = {
    "omits_outcomes": (
        "The assignment wants me to explain what fixed and growth mindsets are and how "
        "they change the way we learn day to day."
    ),
    "confuses_process_outcome": (
        "I need to describe the process of learning for each mindset — like, the outcomes "
        "and the process are basically the same thing, the steps you take when learning."
    ),
    "only_growth": (
        "The task is about how a growth mindset helps students learn better and how "
        "believing you can improve leads to more success in school."
    ),
    "accurate": (
        "It asks me to compare fixed and growth mindsets side by side, and separately explain "
        "how each mindset shapes both the process of learning (effort, how you handle setbacks) "
        "and the outcomes (what you actually achieve). I also need to give real examples."
    ),
    "misunderstands_compare": (
        "Compare means to list the two mindsets and describe each one, so I'll write a "
        "paragraph on fixed mindset and a paragraph on growth mindset with the definitions."
    ),
}


class TestInterpretVariants:
    @pytest.mark.parametrize("key", list(INTERPRETATIONS.keys()))
    def test_variant(self, key):
        sess = _new_session()
        r = _post(f"/sessions/{sess['id']}/interpret", {"text": INTERPRETATIONS[key]})
        assert r.status_code == 200, r.text
        s = r.json()
        # every demand normalized to allowed status
        for d in s["demands"]:
            assert d["status"] in _ALLOWED_STATUSES
        # exactly one active_target OR moved to restatement
        if s["stage"] == "restatement":
            assert s["active_target_id"] == ""
            assert s["current_scaffold"] is None
            # only allow this for accurate variant
            assert key == "accurate", f"variant {key} unexpectedly skipped scaffolding"
        else:
            assert s["stage"] == "mapping"
            assert s["active_target_id"]
            sc = s["current_scaffold"]
            assert sc is not None
            # structured fields
            for f in (
                "instructionType", "targetOperation", "concepts", "studentTask",
                "expectedEvidence", "nextIfSuccessful", "nextIfUnsuccessful",
                "requires_reconstruction",
            ):
                assert f in sc, f"scaffold missing field {f}"
            assert sc["instructionType"] in {
                "independent", "attention_cue", "guided_construction", "direct_teaching"
            }
            assert sc["studentTask"]
            assert not _leaks_confidence(sc), f"confidence leak in scaffold text: {sc}"
            assert not _contains_answer(sc), f"scaffold seems to write the answer: {sc}"
            # highest-leverage selection: needs_attention outranks unconfirmed
            statuses = {d["id"]: d["status"] for d in s["demands"]}
            active_status = statuses[s["active_target_id"]]
            if "needs_attention" in statuses.values():
                assert active_status == "needs_attention", (
                    f"variant {key}: active target status {active_status} but "
                    f"needs_attention exists in {statuses}"
                )


# ---------- 'I don't know' escalation ----------
class TestIDontKnow:
    def test_i_dont_know_on_non_derivable_escalates_to_direct_teaching(self):
        sess = _new_session()
        # use a variant likely to yield a needs_attention target with an inferred demand
        r = _post(f"/sessions/{sess['id']}/interpret",
                  {"text": INTERPRETATIONS["misunderstands_compare"]})
        assert r.status_code == 200
        s = r.json()
        if s["stage"] != "mapping":
            pytest.skip("scenario didn't produce a scaffold to escalate")
        prior_level = s["current_scaffold"]["level"]
        target = next(d for d in s["demands"] if d["id"] == s["active_target_id"])

        r2 = _post(f"/sessions/{s['id']}/operation", {"text": "I dont know."})
        assert r2.status_code == 200, r2.text
        s2 = r2.json()
        # same target (we didn't move on)
        assert s2["active_target_id"] == s["active_target_id"], "should stay on same demand"
        sc = s2["current_scaffold"]
        assert sc is not None
        # scaffold level must escalate (or already be at cap)
        assert sc["level"] >= min(3, prior_level + 1), (
            f"level did not escalate: {prior_level} -> {sc['level']}"
        )
        # if the target is non-derivable, level should be 3 with reconstruction
        if not target["derivable_from_assignment"]:
            assert sc["level"] == 3, "non-derivable demand should escalate to direct teaching"
            assert sc["requires_reconstruction"] is True
            assert sc["instructionType"] == "direct_teaching"
        # scaffold must NOT hand over the finished answer
        assert not _contains_answer(sc)
        assert not _leaks_confidence(sc)


# ---------- operation loop ----------
class TestOperationLoop:
    def test_weak_response_stays_and_escalates(self):
        sess = _new_session()
        r = _post(f"/sessions/{sess['id']}/interpret",
                  {"text": INTERPRETATIONS["confuses_process_outcome"]})
        s = r.json()
        if s["stage"] != "mapping":
            pytest.skip("no scaffold produced")
        prior_target = s["active_target_id"]
        prior_level = s["current_scaffold"]["level"]

        r2 = _post(f"/sessions/{s['id']}/operation", {"text": "idk"})
        assert r2.status_code == 200
        s2 = r2.json()
        assert s2["active_target_id"] == prior_target
        assert s2["current_scaffold"]["level"] >= min(3, prior_level + 1)

    def test_good_response_advances(self):
        sess = _new_session()
        r = _post(f"/sessions/{sess['id']}/interpret",
                  {"text": INTERPRETATIONS["only_growth"]})
        s = r.json()
        if s["stage"] != "mapping":
            pytest.skip("no scaffold produced")
        target = next(d for d in s["demands"] if d["id"] == s["active_target_id"])

        good = (
            "A fixed mindset means someone believes ability is set and unchangeable, so they "
            "avoid hard tasks. A growth mindset means they believe ability grows with effort, "
            "so they try harder and treat setbacks as learning. The key difference is what they "
            "think effort DOES: for fixed it exposes low ability, for growth it builds ability. "
            "Example: a student getting a low math grade — fixed thinks 'I'm bad at math'; "
            "growth thinks 'I need a different strategy'."
        )
        r2 = _post(f"/sessions/{s['id']}/operation", {"text": good})
        assert r2.status_code == 200, r2.text
        s2 = r2.json()
        updated = next(d for d in s2["demands"] if d["id"] == target["id"])
        # target either advanced or session moved on to a different target/restatement
        moved_on = (
            s2["active_target_id"] != target["id"]
            or s2["stage"] == "restatement"
            or updated["status"] in {"developing", "understood"}
        )
        assert moved_on, f"good response didn't advance: {updated}"


# ---------- restatement / adequate ----------
class TestRestatement:
    def test_adequate_restatement(self):
        sess = _new_session()
        # accurate interpretation may go straight to restatement
        r = _post(f"/sessions/{sess['id']}/interpret", {"text": INTERPRETATIONS["accurate"]})
        s = r.json()
        # if still mapping, push through with strong responses is expensive; just try restatement
        # only when stage is restatement.
        if s["stage"] != "restatement":
            pytest.skip("did not reach restatement from accurate variant")
        good_restatement = (
            "This assignment asks me to do three linked things: compare fixed and growth mindsets "
            "by naming their core beliefs about ability; explain how each mindset shapes the "
            "process of learning (effort, response to setbacks); and explain how each shapes the "
            "outcomes of learning (achievement, long-term development). I must ground both "
            "explanations in concrete examples that show the mindset in action."
        )
        r2 = _post(f"/sessions/{s['id']}/restatement", {"text": good_restatement})
        assert r2.status_code == 200, r2.text
        s2 = r2.json()
        # either adequate or bounced to mapping — both must be well-formed
        assert s2["stage"] in {"adequate", "mapping", "restatement"}
        if s2["stage"] == "adequate":
            assert s2["representation_adequate"] is True
            assert s2["active_target_id"] == ""


# ---------- edit / restart ----------
class TestEditRestart:
    def test_patch_resets(self):
        sess = _new_session()
        # do an interpretation so there's state to clear
        _post(f"/sessions/{sess['id']}/interpret", {"text": INTERPRETATIONS["only_growth"]})
        new_text = "Explain the causes of the French Revolution using at least two examples."
        r = _patch(f"/sessions/{sess['id']}", {"assignment_text": new_text})
        assert r.status_code == 200, r.text
        s = r.json()
        assert s["assignment_text"] == new_text
        assert s["stage"] == "interpret"
        assert s["student_interpretation"] == ""
        assert s["interactions"] == []
        assert s["active_target_id"] == ""
        assert s["current_scaffold"] is None
        assert 3 <= len(s["demands"]) <= 6


# ---------- confidence no-leak (aggregated) ----------
class TestNoLeak:
    def test_no_confidence_in_scaffold_text(self):
        sess = _new_session()
        r = _post(f"/sessions/{sess['id']}/interpret",
                  {"text": INTERPRETATIONS["misunderstands_compare"]})
        s = r.json()
        if s["stage"] == "mapping":
            sc = s["current_scaffold"]
            assert not _leaks_confidence(sc)
            assert not _contains_answer(sc)
