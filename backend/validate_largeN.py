"""Larger-n confirmation (quiet, non-blocking). Runs representative seeds N times
under FULL vs PREVIEW output schema and reports the distribution of the categorical
decision fields, to confirm the preview-only output schema hasn't shifted decisions.
Identical inputs; R1 fixed retrieval held constant on both sides."""
import asyncio, json
from collections import Counter
import server
from server import Session, InteractRequest, PREVIEW_BOOTSTRAP, Telos

SEEDS = {
    "A_bare_topic": "School lunches.",
    "B_unmotivated_claim": "Phones should be banned in classrooms.",
    "C_strong_motivated_claim": "Standardized tests should be abolished because they measure memorization rather than understanding and punish students who think differently.",
}
N = {"A_bare_topic": 6, "B_unmotivated_claim": 6, "C_strong_motivated_claim": 10}


def sess():
    p = PREVIEW_BOOTSTRAP
    t = Telos(governing_pedagogical_purpose=p.pedagogical_purpose, immediate_task_purpose=p.current_writing_task,
              teacher_intentions=p.teacher_notes or "", assignment_context=p.assignment)
    return Session(**p.model_dump(), telos=t, is_preview=True)


async def one(content, po):
    r = await server._run_engine(sess(), InteractRequest(content=content, kind="writing"), preview_output=po)
    return {"intervention_type": r["intervention"].type,
            "mode": r["theory"].scaffolding_control.instructional_mode,
            "focus": r["intervention"].focus,
            "stage_b": r["_meta"].get("t_stage_b_reasoner_s")}


async def main():
    out = {}
    for name, content in SEEDS.items():
        n = N[name]
        rec = {"full": [], "preview": []}
        for i in range(n):
            print(f"{name} full {i+1}/{n}", flush=True); rec["full"].append(await one(content, False))
            print(f"{name} preview {i+1}/{n}", flush=True); rec["preview"].append(await one(content, True))
        out[name] = rec
        json.dump(out, open("/app/test_reports/preview_largeN_validation.json", "w"), indent=2)
        print(f"=== {name} SUMMARY ===", flush=True)
        for sch in ("full", "preview"):
            it = Counter(x["intervention_type"] for x in rec[sch])
            md = Counter(x["mode"] for x in rec[sch])
            avg = sum(x["stage_b"] for x in rec[sch]) / len(rec[sch])
            print(f"  {sch}: intervention_type={dict(it)} mode={dict(md)} avg_stage_b={avg:.1f}s", flush=True)
    print("WROTE_ALL", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
