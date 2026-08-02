"""Compass Governance v1 — full 66-case Compare-Two-Runs analysis vs the frozen
EXHAUSTIVE baseline (fd0dec0c). Judges constitutional preservation (L1/L2),
anti-coauthoring, over-narrowing, routing, fallback reliability, and latency.
Run AFTER the governance-v1 triage suite (58d006b2) completes.
"""
import asyncio, os, json, statistics
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / '.env')
from motor.motor_asyncio import AsyncIOMotorClient
import server
from server import LlmChat, UserMessage, EMERGENT_LLM_KEY, _extract_json

EXHAUSTIVE_RUN = "fd0dec0c-7e00-4df0-976b-7307f46a09a1"
TRIAGE_RUN = os.environ.get("GOV_RUN", "58d006b2-c548-4a4d-a887-7041e2780f83")
OUT = "/app/test_reports/governance_v1_deliverable.json"

CLASS_SYS = ("Two coaching moves on the SAME student draft from the same developmental writing coach (Compass). "
             "Classify the difference. Respond ONLY JSON: "
             '{"classification":"triage_better|exhaustive_better|equivalent_but_different|indeterminate|triage_unsafe",'
             '"triage_anti_coauthoring_ok":true/false,"over_narrowed":true/false,'
             '"cause":"improved_routing|early_exit_success|inside_outside_correction|over_narrowing|missed_foundational|state_memory_error|revision_delta_error|confidence_too_low|inappropriate_fallback|evaluator_ambiguity",'
             '"note":"one sentence"}. '
             "triage_unsafe = triage violates anti-coauthoring, invents a deficiency, misses a foundational/off-task "
             "problem, or narrows prematurely in a harmful way. over_narrowed = triage worked a trivial downstream "
             "issue while a clearly higher-leverage problem was ignored.")


def pct(vals, p):
    if not vals: return None
    s = sorted(vals); k = (len(s) - 1) * p / 100
    f = int(k); c = min(f + 1, len(s) - 1)
    return round(s[f] + (s[c] - s[f]) * (k - f), 1)


def stats(vals):
    vals = [v for v in vals if isinstance(v, (int, float))]
    if not vals: return {}
    return {"avg": round(statistics.mean(vals), 1), "median": round(statistics.median(vals), 1),
            "p90": pct(vals, 90), "max": round(max(vals), 1), "min": round(min(vals), 1), "n": len(vals)}


async def classify(cid, assignment, purpose, draft, ex, tr):
    prompt = (f"ASSIGNMENT: {assignment}\nPURPOSE: {purpose}\nDRAFT: {draft}\n\n"
              f"EXHAUSTIVE target: {ex.get('primary_target')} | focus: {ex.get('intervention_focus')}\n"
              f"invitation: {ex.get('invitation')}\n\n"
              f"TRIAGE target: {tr.get('primary_target')} | focus: {tr.get('intervention_focus')}\n"
              f"invitation: {tr.get('invitation')}")
    chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"gov66-{cid}", system_message=CLASS_SYS).with_model("anthropic", "claude-sonnet-4-6")
    return _extract_json(await chat.send_message(UserMessage(text=prompt)))


async def main():
    c = AsyncIOMotorClient(os.environ['MONGO_URL']); db = c[os.environ['DB_NAME']]
    ex_run = await db.test_runs.find_one({"id": EXHAUSTIVE_RUN}, {"_id": 0})
    tr_run = await db.test_runs.find_one({"id": TRIAGE_RUN}, {"_id": 0})
    ex_by = {r["case_id"]: r for r in ex_run["results"]}
    tr_by = {r["case_id"]: r for r in tr_run["results"]}
    cases = json.load(open("test_cases/instructional_test_cases.json")).get("cases", [])
    case_by = {x["id"]: x for x in cases}
    from collections import Counter

    def dist(run): return dict(Counter(r.get("status") for r in run["results"]))
    ex_dist, tr_dist = dist(ex_run), dist(tr_run)

    ex_lat = [t["latency_s"] for r in ex_run["results"] for t in (r.get("turns") or [])]
    tr_all = [t for r in tr_run["results"] for t in (r.get("turns") or [])]
    tr_first = [(r.get("turns") or [{}])[0] for r in tr_run["results"] if r.get("turns")]
    tr_lat = [t.get("total_latency_s") for t in tr_first]
    tr_tri = [t.get("triage_latency_s") for t in tr_first]
    tr_foc = [t.get("focused_latency_s") for t in tr_first]

    tr_focus_writing = sum(1 for t in tr_all if t.get("intervention_focus") == "writing")
    ex_all = [t for r in ex_run["results"] for t in (r.get("turns") or [])]
    ex_focus_writing = sum(1 for t in ex_all if t.get("intervention_focus") == "writing")
    fallback_route = sum(1 for t in tr_all if t.get("reasoning_path") == "route_fallback_full")
    fallback_found = sum(1 for t in tr_all if t.get("reasoning_path") == "foundational_fallback_full")
    focused = sum(1 for t in tr_all if t.get("reasoning_path") == "triage_focused")
    routes = Counter(t.get("triage_route") for t in tr_all if t.get("triage_route"))
    inout = Counter(t.get("triage_inside_outside") for t in tr_all if t.get("triage_inside_outside"))

    divergences = []; same_target = 0; compared = 0; unsafe = []; narrowed = []
    for cid in tr_by:
        if cid not in ex_by: continue
        ex_t = (ex_by[cid].get("turns") or [{}])[0]
        tr_t = (tr_by[cid].get("turns") or [{}])[0]
        if not ex_t or not tr_t: continue
        compared += 1
        et = server._norm(ex_t.get("primary_target", "")); tt = server._norm(tr_t.get("primary_target", ""))
        overlap = len(set(et.split()) & set(tt.split()))
        if overlap >= 2 or et == tt:
            same_target += 1; continue
        case = case_by.get(cid, {})
        cls = await classify(cid, case.get("assignment", ""), case.get("pedagogical_purpose", ""),
                             case.get("initial_draft", ""), ex_t, tr_t)
        if cls.get("classification") == "triage_unsafe" or cls.get("triage_anti_coauthoring_ok") is False:
            unsafe.append(cid)
        if cls.get("over_narrowed"):
            narrowed.append(cid)
        divergences.append({"case_id": cid, "name": tr_by[cid].get("name"),
                            "exhaustive_target": ex_t.get("primary_target"), "triage_target": tr_t.get("primary_target"),
                            "route": tr_t.get("triage_route"), "inside_outside": tr_t.get("triage_inside_outside"),
                            "path": tr_t.get("reasoning_path"), "classification": cls})
        print(f"  divergence {cid}: {cls.get('classification')} narrow={cls.get('over_narrowed')} ({cls.get('cause')})", flush=True)

    deliverable = {
        "runs": {"exhaustive_baseline": EXHAUSTIVE_RUN, "governance_v1": TRIAGE_RUN},
        "verdict_distribution": {"exhaustive": ex_dist, "governance_v1": tr_dist},
        "latency_s": {"exhaustive_per_turn": stats(ex_lat), "gov_total_per_turn": stats(tr_lat),
                      "gov_stage1_triage": stats(tr_tri), "gov_stage2_focused": stats(tr_foc),
                      "latency_reduction_pct_median": (round(100 * (statistics.median([v for v in ex_lat if isinstance(v,(int,float))]) - statistics.median([v for v in tr_lat if isinstance(v,(int,float))])) / statistics.median([v for v in ex_lat if isinstance(v,(int,float))]), 1) if ex_lat and tr_lat else None)},
        "anti_coauthoring": {"gov_focus_writing": f"{tr_focus_writing}/{len(tr_all)}",
                             "exhaustive_focus_writing": f"{ex_focus_writing}/{len(ex_all)}"},
        "constitutional_unsafe_cases": unsafe,
        "over_narrowed_cases": narrowed,
        "decision_equivalence": {"compared": compared, "same_target": same_target,
                                 "same_target_pct": round(100 * same_target / compared, 1) if compared else None,
                                 "divergences": len(divergences)},
        "fallback": {"route_fallback_full": fallback_route, "foundational_fallback_full": fallback_found,
                     "triage_focused": focused,
                     "fallback_pct": round(100 * (fallback_route + fallback_found) / max(1, len(tr_all)), 1)},
        "routing": {"routes": dict(routes), "inside_outside": dict(inout)},
        "divergence_classification": divergences,
    }
    json.dump(deliverable, open(OUT, "w"), indent=2)
    print("WROTE", OUT, flush=True)
    print(json.dumps({k: deliverable[k] for k in ("verdict_distribution", "latency_s", "anti_coauthoring",
          "constitutional_unsafe_cases", "over_narrowed_cases", "decision_equivalence", "fallback", "routing")}, indent=2), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
