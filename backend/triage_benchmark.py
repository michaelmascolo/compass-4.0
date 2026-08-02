"""Benchmark: EXHAUSTIVE (frozen engine) vs TRIAGE (experimental) on a
representative case set. Runs both paths from the SAME starting session for each
case and captures instructional route, target, invitation, anti-coauthoring,
support level, latency, tokens, model calls — plus an LLM-judged disagreement."""
import json
import time
import asyncio

import server
import triage_experiment as TX
from server import Session, Telos, DevelopmentalObservation, InteractRequest, LlmChat, UserMessage, EMERGENT_LLM_KEY, _extract_json

CASES_PATH = "test_cases/instructional_test_cases.json"
CASE_IDS = ["TC01", "TC03", "TC07", "TC08", "TC25", "TC30"]
OUT = "/app/test_reports/triage_benchmark.json"


def load_cases():
    c = json.load(open(CASES_PATH))
    c = c if isinstance(c, list) else c.get("cases", c)
    by = {x["id"]: x for x in c}
    return [by[i] for i in CASE_IDS if i in by]


def build_session(case) -> Session:
    s = Session(
        assignment=case.get("assignment", ""),
        pedagogical_purpose=case.get("pedagogical_purpose", ""),
        current_writing_task=case.get("current_writing_task", ""),
        assignment_prompt=case.get("assignment", ""),
        telos=Telos(
            governing_pedagogical_purpose=case.get("pedagogical_purpose", ""),
            immediate_task_purpose=case.get("current_writing_task", ""),
            teacher_intentions="", assignment_context=case.get("assignment", ""),
        ),
    )
    for p in case.get("initial_profile", []) or []:
        s.developmental_profile.append(DevelopmentalObservation(
            element=p.get("element", ""), control_statement=p.get("control_statement", ""),
            trend=p.get("trend", ""), evidence=p.get("evidence", ""), episodes=p.get("episodes", 1)))
    return s


def extract(result: dict) -> dict:
    th = result["theory"]
    sc = th.scaffolding_control
    interv = result["intervention"]
    return {
        "invitation": result["invitation"],
        "primary_target": sc.primary_target,
        "instructional_mode": sc.instructional_mode,
        "cycle_status": sc.cycle_status,
        "intervention_type": interv.type,
        "intervention_focus": interv.focus,  # anti-coauthoring: must be 'writing' (unless brainstorm)
        "one_target": bool(sc.primary_target) and bool(result["invitation"]),
    }


JUDGE_SYS = ("You compare two coaching moves from the same writing coach on the same student draft. "
             "Decide if they make the SAME instructional decision. Respond ONLY JSON: "
             '{"same_target":true/false,"materially_different_decision":true/false,'
             '"both_anti_coauthoring_ok":true/false,"which_better":"exhaustive|triage|equivalent",'
             '"note":"one sentence"}. Materially different = a teacher would consider them different pedagogical choices (different target or a different developmental move), not mere wording.')


async def judge(case, ex, tr):
    prompt = (f"ASSIGNMENT: {case.get('assignment')}\nPURPOSE: {case.get('pedagogical_purpose')}\n"
              f"DRAFT: {case.get('initial_draft')}\n\n"
              f"EXHAUSTIVE — target: {ex['primary_target']} | type: {ex['intervention_type']} | focus: {ex['intervention_focus']}\n"
              f"invitation: {ex['invitation']}\n\n"
              f"TRIAGE — target: {tr['primary_target']} | type: {tr['intervention_type']} | focus: {tr['intervention_focus']}\n"
              f"invitation: {tr['invitation']}")
    chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"judge-{case['id']}", system_message=JUDGE_SYS).with_model("anthropic", "claude-sonnet-4-6")
    raw = await chat.send_message(UserMessage(text=prompt))
    return _extract_json(raw)


async def main():
    cases = load_cases()
    rows = []
    for case in cases:
        print(f"=== {case['id']} {case['name']} ===", flush=True)
        try:
            s_ex = build_session(case)
            s_tr = build_session(case)
            req = InteractRequest(content=case.get("initial_draft", ""), kind="writing")

            r_ex = await TX.run_exhaustive(s_ex.model_copy(deep=True), req)
            print(f"  exhaustive {r_ex['_exhaustive_meta']['total_latency_s']}s", flush=True)
            r_tr = await TX.run_triage_pipeline(s_tr.model_copy(deep=True), req)
            print(f"  triage {r_tr['_triage_meta']['total_latency_s']}s path={r_tr['_triage_meta']['path']}", flush=True)

            ex, tr = extract(r_ex), extract(r_tr)
            cmp = await judge(case, ex, tr)
            rows.append({
                "case_id": case["id"], "name": case["name"],
                "expected_target": case.get("expected_primary_target"),
                "exhaustive": {**ex, **r_ex["_exhaustive_meta"]},
                "triage": {**tr, "triage_decision": r_tr.get("_triage"), **r_tr["_triage_meta"]},
                "comparison": cmp,
            })
            json.dump(rows, open(OUT, "w"), indent=2)  # incremental
        except Exception as e:
            print(f"  ERROR {case['id']}: {e}", flush=True)
            rows.append({"case_id": case["id"], "error": str(e)})
            json.dump(rows, open(OUT, "w"), indent=2)

    # aggregate
    ok = [r for r in rows if "error" not in r]
    if ok:
        ex_lat = sum(r["exhaustive"]["total_latency_s"] for r in ok) / len(ok)
        tr_lat = sum(r["triage"]["total_latency_s"] for r in ok) / len(ok)
        ex_out = sum(r["exhaustive"]["output_tokens"] for r in ok) / len(ok)
        tr_out = sum(r["triage"]["output_tokens"] for r in ok) / len(ok)
        same = sum(1 for r in ok if r["comparison"].get("same_target"))
        diff = sum(1 for r in ok if r["comparison"].get("materially_different_decision"))
        agg = {
            "n": len(ok),
            "avg_latency_exhaustive_s": round(ex_lat, 1),
            "avg_latency_triage_s": round(tr_lat, 1),
            "latency_reduction_pct": round(100 * (ex_lat - tr_lat) / ex_lat, 1),
            "avg_output_tokens_exhaustive": round(ex_out),
            "avg_output_tokens_triage": round(tr_out),
            "output_token_reduction_pct": round(100 * (ex_out - tr_out) / ex_out, 1),
            "same_target": f"{same}/{len(ok)}",
            "materially_different_decisions": f"{diff}/{len(ok)}",
        }
        json.dump({"aggregate": agg, "rows": rows}, open(OUT, "w"), indent=2)
        print("AGG", json.dumps(agg, indent=2), flush=True)
    print("WROTE", OUT, flush=True)


if __name__ == "__main__":
    asyncio.run(main())
