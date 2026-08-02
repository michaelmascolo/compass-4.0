"""Variance probe: run case C (strong motivated claim) N times under FULL and
PREVIEW output schemas to see whether the intervention_type difference is
schema-caused or ordinary run-to-run stochastic variance."""
import asyncio, json
import server
from server import Session, InteractRequest, PREVIEW_BOOTSTRAP, Telos

CONTENT = "Standardized tests should be abolished because they measure memorization rather than understanding and punish students who think differently."
N = 3


def sess():
    p = PREVIEW_BOOTSTRAP
    t = Telos(governing_pedagogical_purpose=p.pedagogical_purpose, immediate_task_purpose=p.current_writing_task,
              teacher_intentions=p.teacher_notes or "", assignment_context=p.assignment)
    return Session(**p.model_dump(), telos=t, is_preview=True)


async def one(po):
    r = await server._run_engine(sess(), InteractRequest(content=CONTENT, kind="writing"), preview_output=po)
    return {"intervention_type": r["intervention"].type,
            "mode": r["theory"].scaffolding_control.instructional_mode,
            "target": r["theory"].scaffolding_control.primary_target,
            "stage_b": r["_meta"].get("t_stage_b_reasoner_s")}


async def main():
    out = {"full": [], "preview": []}
    for i in range(N):
        print(f"full {i}", flush=True); out["full"].append(await one(False))
        print(f"preview {i}", flush=True); out["preview"].append(await one(True))
    json.dump(out, open("/app/test_reports/preview_variance_C.json", "w"), indent=2)
    print("WROTE", flush=True)
    for k in out:
        print(k, "intervention_types:", [x["intervention_type"] for x in out[k]])


if __name__ == "__main__":
    asyncio.run(main())
