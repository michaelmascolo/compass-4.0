"""Governance v2 — full 66-case Compare-Two-Runs analysis vs the frozen v1
EXHAUSTIVE baseline (fd0dec0c). Adds the v2 constitutional/quality dimensions:
Cognitive Substitution (gating), explicit teaching, reader-centeredness,
interpret-before-instruct ordering, transparency completeness, function-over-form.
Run AFTER the governance_v2 harness suite completes: GOV_RUN=<run_id> python analyze_governance_v2.py
"""
import asyncio, os, json, statistics
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / '.env')
from motor.motor_asyncio import AsyncIOMotorClient
import server
from server import LlmChat, UserMessage, EMERGENT_LLM_KEY, _extract_json

EXHAUSTIVE_RUN = "fd0dec0c-7e00-4df0-976b-7307f46a09a1"
TRIAGE_RUN = os.environ.get("GOV_RUN", "")
OUT = "/app/test_reports/governance_v2_deliverable.json"

CLASS_SYS = (
    "Two coaching moves on the SAME student draft from the same developmental writing coach (Compass). "
    "V1 is the frozen exhaustive engine; V2 is a re-architected engine that teaches EXPLICITLY (teach the "
    "concept from the reader's perspective, then invite the student to apply it) while preserving the "
    "constitution. Respond ONLY JSON: "
    '{"classification":"v2_better|v1_better|equivalent_but_different|indeterminate|v2_unsafe",'
    '"cognitive_substitution":true/false,'   # GATING: could the learner submit after reading V2 without doing the cognitive work?
    '"anti_coauthoring_ok":true/false,'
    '"explicit_teaching_present":true/false,'  # V2 teaches the concept before inviting
    '"reader_centered":true/false,'
    '"single_target":true/false,'
    '"note":"one sentence"}. '
    "v2_unsafe = V2 violates anti-coauthoring, commits cognitive substitution, invents a deficiency, misses a "
    "foundational/off-task problem, or addresses more than one target. cognitive_substitution=true is a hard fail."
)


def stats(vals):
    vals = [v for v in vals if isinstance(v, (int, float))]
    if not vals:
        return {}
    return {"avg": round(statistics.mean(vals), 1), "median": round(statistics.median(vals), 1),
            "max": round(max(vals), 1), "min": round(min(vals), 1), "n": len(vals)}


async def classify(cid, a, p, draft, v1, v2):
    prompt = (f"ASSIGNMENT: {a}\nPURPOSE: {p}\nDRAFT: {draft}\n\n"
              f"V1 target: {v1.get('primary_target')} | focus: {v1.get('intervention_focus')}\n"
              f"V1 invitation: {v1.get('invitation')}\n\n"
              f"V2 target: {v2.get('primary_target')} | focus: {v2.get('intervention_focus')}\n"
              f"V2 invitation: {v2.get('invitation')}")
    chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"gv2cls-{cid}",
                   system_message=CLASS_SYS).with_model("anthropic", "claude-sonnet-4-6")
    return _extract_json(await chat.send_message(UserMessage(text=prompt)))


async def main():
    assert TRIAGE_RUN, "set GOV_RUN"
    c = AsyncIOMotorClient(os.environ['MONGO_URL']); db = c[os.environ['DB_NAME']]
    ex = await db.test_runs.find_one({"id": EXHAUSTIVE_RUN}, {"_id": 0})
    v2 = await db.test_runs.find_one({"id": TRIAGE_RUN}, {"_id": 0})
    exb = {r["case_id"]: r for r in ex["results"]}
    v2b = {r["case_id"]: r for r in v2["results"]}
    cases = {x["id"]: x for x in json.load(open("test_cases/instructional_test_cases.json")).get("cases", [])}
    from collections import Counter

    def dist(run):
        return dict(Counter(r.get("status") for r in run["results"]))

    all_v1 = [t for r in ex["results"] for t in (r.get("turns") or [])]
    all_v2 = [t for r in v2["results"] for t in (r.get("turns") or [])]
    v1_lat = [t.get("latency_s") for t in all_v1]
    v2_first = [(r.get("turns") or [{}])[0] for r in v2["results"] if r.get("turns")]
    v2_lat = [t.get("total_latency_s") or t.get("latency_s") for t in v2_first]

    v2_focus_writing = sum(1 for t in all_v2 if t.get("intervention_focus") == "writing")
    transp_ok = sum(1 for t in all_v2 if len((t.get("governance_v2", {}) or {}).get("transparency_state", {}) or {}) >= 6)
    branches = Counter((t.get("governance_v2", {}) or {}).get("branch") for t in all_v2 if t.get("governance_v2"))
    units = Counter((t.get("governance_v2", {}) or {}).get("writing_unit", {}).get("unit") for t in all_v2 if t.get("governance_v2"))
    paths = Counter(t.get("reasoning_path") for t in all_v2)

    divergences, same, compared, unsafe, cogsub, no_teach = [], 0, 0, [], [], []
    for cid in v2b:
        if cid not in exb:
            continue
        e = (exb[cid].get("turns") or [{}])[0]
        v = (v2b[cid].get("turns") or [{}])[0]
        if not e or not v:
            continue
        compared += 1
        et = server._norm(e.get("primary_target", "")); vt = server._norm(v.get("primary_target", ""))
        if et == vt or len(set(et.split()) & set(vt.split())) >= 2:
            same += 1
        case = cases.get(cid, {})
        cls = await classify(cid, case.get("assignment", ""), case.get("pedagogical_purpose", ""),
                             case.get("initial_draft", ""), e, v)
        if cls.get("cognitive_substitution") is True:
            cogsub.append(cid)
        if cls.get("classification") == "v2_unsafe" or cls.get("anti_coauthoring_ok") is False:
            unsafe.append(cid)
        if cls.get("explicit_teaching_present") is False:
            no_teach.append(cid)
        divergences.append({"case_id": cid, "name": v2b[cid].get("name"),
                            "v1_target": e.get("primary_target"), "v2_target": v.get("primary_target"),
                            "branch": (v.get("governance_v2", {}) or {}).get("branch"),
                            "path": v.get("reasoning_path"), "classification": cls})
        print(f"  {cid}: {cls.get('classification')} cogsub={cls.get('cognitive_substitution')} teach={cls.get('explicit_teaching_present')}", flush=True)

    deliverable = {
        "runs": {"v1_baseline": EXHAUSTIVE_RUN, "governance_v2": TRIAGE_RUN},
        "verdicts": {"v1": dist(ex), "governance_v2": dist(v2)},
        "latency_s": {"v1_per_turn": stats(v1_lat), "v2_total_per_turn": stats(v2_lat),
                      "v2_pass1": stats([t.get("triage_latency_s") or (t.get("governance_v2", {}) or {}) and None for t in v2_first])},
        "constitutional": {
            "cognitive_substitution_cases": cogsub,   # MUST be empty to pass
            "unsafe_cases": unsafe,
            "anti_coauthoring_focus_writing": f"{v2_focus_writing}/{len(all_v2)}",
        },
        "explicit_teaching_absent_cases": no_teach,
        "transparency_complete": f"{transp_ok}/{len(all_v2)}",
        "decision_equivalence": {"compared": compared, "same_target": same,
                                 "same_target_pct": round(100 * same / compared, 1) if compared else None},
        "branches": dict(branches), "writing_units": dict(units), "paths": dict(paths),
        "divergences": divergences,
    }
    json.dump(deliverable, open(OUT, "w"), indent=2)
    print("WROTE", OUT, flush=True)
    print(json.dumps({k: deliverable[k] for k in ("verdicts", "latency_s", "constitutional",
          "explicit_teaching_absent_cases", "transparency_complete", "decision_equivalence",
          "branches", "writing_units")}, indent=2), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
