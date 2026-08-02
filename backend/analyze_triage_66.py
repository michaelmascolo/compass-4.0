"""Analyze the triage 66-case run against the exhaustive baseline (fd0dec0c) and
the frozen evaluator. Produces the full deliverable metrics + divergence
classification. Run AFTER the triage suite completes."""
import asyncio, os, json, statistics
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).parent / '.env')
from motor.motor_asyncio import AsyncIOMotorClient
import server
from server import LlmChat, UserMessage, EMERGENT_LLM_KEY, _extract_json

EXHAUSTIVE_RUN = "fd0dec0c-7e00-4df0-976b-7307f46a09a1"
TRIAGE_RUN = "2ea62af8-c148-4c19-98c7-3c03aeceb1d9"
OUT = "/app/test_reports/triage_66_deliverable.json"

CLASS_SYS = ("Two coaching moves on the SAME student draft from the same developmental writing coach (Compass). "
             "Classify the difference. Respond ONLY JSON: "
             '{"classification":"triage_better|exhaustive_better|equivalent_but_different|indeterminate|triage_unsafe",'
             '"cause":"improved_routing|early_exit_success|inside_outside_correction|over_narrowing|missed_foundational|state_memory_error|revision_delta_error|confidence_too_low|inappropriate_fallback|evaluator_ambiguity",'
             '"note":"one sentence — which is more instructionally defensible and why"}. '
             "triage_unsafe = triage violates anti-coauthoring, invents a deficiency, misses a foundational problem, or narrows prematurely in a harmful way.")


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


async def classify(case_id, assignment, purpose, draft, ex, tr):
    prompt = (f"ASSIGNMENT: {assignment}\nPURPOSE: {purpose}\nDRAFT: {draft}\n\n"
              f"EXHAUSTIVE target: {ex.get('primary_target')} | type: {ex.get('intervention_type','?')} | focus: {ex.get('intervention_focus')}\n"
              f"invitation: {ex.get('invitation')}\n\n"
              f"TRIAGE target: {tr.get('primary_target')} | type: {tr.get('intervention_type','?')} | focus: {tr.get('intervention_focus')}\n"
              f"invitation: {tr.get('invitation')}")
    chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"class-{case_id}", system_message=CLASS_SYS).with_model("anthropic", "claude-sonnet-4-6")
    raw = await chat.send_message(UserMessage(text=prompt))
    return _extract_json(raw)


async def main():
    c = AsyncIOMotorClient(os.environ['MONGO_URL']); db = c[os.environ['DB_NAME']]
    ex_run = await db.test_runs.find_one({"id": EXHAUSTIVE_RUN}, {"_id": 0})
    tr_run = await db.test_runs.find_one({"id": TRIAGE_RUN}, {"_id": 0})
    ex_by = {r["case_id"]: r for r in ex_run["results"]}
    tr_by = {r["case_id"]: r for r in tr_run["results"]}
    cases = json.load(open("test_cases/instructional_test_cases.json")).get("cases", [])
    case_by = {x["id"]: x for x in cases}

    # verdict distributions
    def dist(run): 
        from collections import Counter
        return dict(Counter(r.get("status") for r in run["results"]))
    ex_dist, tr_dist = dist(ex_run), dist(tr_run)

    # latency + tokens + operational
    ex_lat = [t["latency_s"] for r in ex_run["results"] for t in (r.get("turns") or [])]
    tr_first = [(r.get("turns") or [{}])[0] for r in tr_run["results"] if r.get("turns")]
    tr_lat = [t.get("total_latency_s") for t in tr_first]
    tr_tri = [t.get("triage_latency_s") for t in tr_first]
    tr_foc = [t.get("focused_latency_s") for t in tr_first]
    tr_ptok = [t.get("prompt_tokens") for t in tr_first]
    tr_otok = [t.get("output_tokens") for t in tr_first]

    # anti-coauthoring across ALL turns
    tr_all = [t for r in tr_run["results"] for t in (r.get("turns") or [])]
    ex_all = [t for r in ex_run["results"] for t in (r.get("turns") or [])]
    tr_focus_writing = sum(1 for t in tr_all if t.get("intervention_focus") == "writing")
    # fallback frequency
    fallback = sum(1 for t in tr_all if t.get("reasoning_path") == "foundational_fallback_full")
    focused = sum(1 for t in tr_all if t.get("reasoning_path") == "triage_focused")
    # inside/outside + route
    from collections import Counter
    routes = Counter(t.get("triage_route") for t in tr_all if t.get("triage_route"))
    inout = Counter(t.get("triage_inside_outside") for t in tr_all if t.get("triage_inside_outside"))
    confs = [t.get("triage_confidence") for t in tr_all if isinstance(t.get("triage_confidence"), (int, float))]

    # divergence classification (compare FIRST turn target per case)
    divergences = []
    same_target = 0; compared = 0
    for cid in tr_by:
        if cid not in ex_by: continue
        ex_t = (ex_by[cid].get("turns") or [{}])[0]
        tr_t = (tr_by[cid].get("turns") or [{}])[0]
        if not ex_t or not tr_t: continue
        compared += 1
        et = server._norm(ex_t.get("primary_target", "")); tt = server._norm(tr_t.get("primary_target", ""))
        # crude same-target: token overlap
        overlap = len(set(et.split()) & set(tt.split()))
        if overlap >= 2 or et == tt:
            same_target += 1
            continue
        case = case_by.get(cid, {})
        cls = await classify(cid, case.get("assignment", ""), case.get("pedagogical_purpose", ""),
                             case.get("initial_draft", ""), ex_t, tr_t)
        divergences.append({"case_id": cid, "name": tr_by[cid].get("name"),
                            "exhaustive_target": ex_t.get("primary_target"), "triage_target": tr_t.get("primary_target"),
                            "triage_route": tr_t.get("triage_route"), "inside_outside": tr_t.get("triage_inside_outside"),
                            "foundational": tr_t.get("triage_foundational"), "classification": cls})
        print(f"  divergence {cid}: {cls.get('classification')} ({cls.get('cause')})", flush=True)

    deliverable = {
        "runs": {"exhaustive_baseline": EXHAUSTIVE_RUN, "triage": TRIAGE_RUN},
        "verdict_distribution": {"exhaustive": ex_dist, "triage": tr_dist},
        "latency_s": {"exhaustive_per_turn": stats(ex_lat), "triage_total_per_turn": stats(tr_lat),
                      "triage_stage1_triage": stats(tr_tri), "triage_stage2_focused": stats(tr_foc)},
        "tokens": {"triage_prompt": stats(tr_ptok), "triage_output": stats(tr_otok)},
        "decision_equivalence": {"compared": compared, "same_target": same_target,
                                 "same_target_pct": round(100 * same_target / compared, 1) if compared else None,
                                 "divergences": len(divergences)},
        "anti_coauthoring": {"triage_focus_writing": f"{tr_focus_writing}/{len(tr_all)}",
                             "exhaustive_focus_writing": f"{sum(1 for t in ex_all if t.get('intervention_focus')=='writing')}/{len(ex_all)}"},
        "fallback": {"foundational_fallback_full": fallback, "triage_focused": focused,
                     "fallback_pct": round(100 * fallback / max(1, len(tr_all)), 1)},
        "routing": {"routes": dict(routes), "inside_outside": dict(inout),
                    "confidence": stats(confs)},
        "divergence_classification": divergences,
    }
    json.dump(deliverable, open(OUT, "w"), indent=2)
    print("WROTE", OUT, flush=True)
    print(json.dumps({k: deliverable[k] for k in ("verdict_distribution", "latency_s", "decision_equivalence", "anti_coauthoring", "fallback", "routing")}, indent=2), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
