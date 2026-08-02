"""Post-fix probe: run case C (strong motivated claim) N times under the PREVIEW
output schema to confirm the RESTRAINT INVARIANT restores invite_only."""
import asyncio, json
import server
from server import Session, InteractRequest, PREVIEW_BOOTSTRAP, Telos

CONTENT = "Standardized tests should be abolished because they measure memorization rather than understanding and punish students who think differently."
N = 8


def sess():
    p = PREVIEW_BOOTSTRAP
    t = Telos(governing_pedagogical_purpose=p.pedagogical_purpose, immediate_task_purpose=p.current_writing_task,
              teacher_intentions=p.teacher_notes or "", assignment_context=p.assignment)
    return Session(**p.model_dump(), telos=t, is_preview=True)


async def one():
    r = await server._run_engine(sess(), InteractRequest(content=CONTENT, kind="writing"), preview_output=True)
    return {"intervention_type": r["intervention"].type,
            "mode": r["theory"].scaffolding_control.instructional_mode,
            "target": r["theory"].scaffolding_control.primary_target}


async def main():
    out = []
    for i in range(N):
        res = await one()
        print(f"preview {i}:", res["intervention_type"], flush=True)
        out.append(res)
    json.dump(out, open("/app/test_reports/preview_C_fix.json", "w"), indent=2)
    types = [x["intervention_type"] for x in out]
    invite = sum(1 for t in types if t in ("invite_only", "interpretation_only"))
    print(f"WROTE. invite_only/interpretation_only = {invite}/{N}", flush=True)
    print("types:", types, flush=True)


if __name__ == "__main__":
    asyncio.run(main())
