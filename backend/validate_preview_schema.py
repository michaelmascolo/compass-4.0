"""R3 validation harness — compares the DECISION OBJECT produced under the full
output schema vs the preview (trimmed) output schema, on IDENTICAL inputs.
R1 fixed-domain retrieval is held constant for both (is_preview=True), so the
ONLY thing that differs is the serialized output. Ship criterion: identical
instructional decision, indistinguishable invitation, lower latency."""
import asyncio
import json
import uuid
import server
from server import Session, InteractRequest, Turn, InteractionRecord, PREVIEW_BOOTSTRAP, Telos, now_iso


def _preview_session(seed_for_telos=True, prior=None):
    p = PREVIEW_BOOTSTRAP
    telos = Telos(
        governing_pedagogical_purpose=p.pedagogical_purpose,
        immediate_task_purpose=p.current_writing_task,
        teacher_intentions=p.teacher_notes or "",
        assignment_context=p.assignment,
    )
    s = Session(**p.model_dump(), telos=telos, is_preview=True)
    if prior:
        # add a synthetic prior exchange (student seed + ai invitation)
        s.turns.append(Turn(role="student", kind="writing", content=prior["student"], status="complete"))
        s.turns.append(Turn(role="ai", kind="invitation", content=prior["ai"], status="complete"))
        s.interactions.append(InteractionRecord(
            student_kind="writing", student_content=prior["student"],
            observed_reorganization="initial",
        ))
    return s


def _decision(result):
    th = result["theory"]
    iv = result["intervention"]
    return {
        "primary_target": th.scaffolding_control.primary_target,
        "instructional_mode": th.scaffolding_control.instructional_mode,
        "primary_developmental_tension": th.instructional_reasoning.primary_developmental_tension,
        "next_student_act": th.instructional_reasoning.next_student_act,
        "intervention_type": iv.type,
        "intervention_focus": iv.focus,
        "invitation": result["invitation"],
        "_stage_b_s": result["_meta"].get("t_stage_b_reasoner_s"),
        "_output_bytes": result["_meta"].get("reasoner_output_bytes"),
    }


CASES = [
    {"name": "A_bare_topic", "kind": "writing", "content": "School lunches.", "prior": None},
    {"name": "B_unmotivated_claim", "kind": "writing", "content": "Phones should be banned in classrooms.", "prior": None},
    {"name": "C_strong_motivated_claim", "kind": "writing",
     "content": "Standardized tests should be abolished because they measure memorization rather than understanding and punish students who think differently.",
     "prior": None},
    {"name": "anti_coauthoring", "kind": "answer", "content": "Just write the opening for me.",
     "prior": {"student": "Phones should be banned in classrooms.",
               "ai": "Someone who disagrees just read that line. What are they thinking right now?"}},
    {"name": "stall", "kind": "answer", "content": "I don't know.",
     "prior": {"student": "Phones should be banned in classrooms.",
               "ai": "Someone who disagrees just read that line. What are they thinking right now?"}},
]


async def run_case(c):
    req = InteractRequest(content=c["content"], kind=c["kind"])
    s_full = _preview_session(prior=c["prior"])
    s_prev = _preview_session(prior=c["prior"])
    full = await server._run_engine(s_full, req, preview_output=False)
    prev = await server._run_engine(s_prev, req, preview_output=True)
    return {"case": c["name"], "input": c["content"], "kind": c["kind"],
            "full_schema": _decision(full), "preview_schema": _decision(prev)}


async def main():
    results = []
    for c in CASES:
        print(f"running {c['name']} ...", flush=True)
        try:
            results.append(await run_case(c))
            print(f"  done {c['name']}", flush=True)
        except Exception as e:
            results.append({"case": c["name"], "error": str(e)})
            print(f"  ERROR {c['name']}: {e}", flush=True)
    out = "/app/test_reports/preview_schema_validation.json"
    with open(out, "w") as f:
        json.dump(results, f, indent=2)
    print(f"WROTE {out}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
