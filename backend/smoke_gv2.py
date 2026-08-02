import asyncio, json
import server, governance_v2
from server import Session, Telos, DevelopmentalObservation, InteractRequest

CASES = json.load(open("test_cases/instructional_test_cases.json")).get("cases", [])
BY = {c["id"]: c for c in CASES}
PICK = ["TC08", "TC01", "TC03"]  # normal / misunderstanding-assignment / possibly-prewriting


def build(case):
    s = Session(
        assignment=case.get("assignment", ""), pedagogical_purpose=case.get("pedagogical_purpose", ""),
        current_writing_task=case.get("current_writing_task", ""), assignment_prompt=case.get("assignment", ""),
        telos=Telos(governing_pedagogical_purpose=case.get("pedagogical_purpose", ""),
                    immediate_task_purpose=case.get("current_writing_task", ""),
                    assignment_context=case.get("assignment", "")),
    )
    for p in case.get("initial_profile", []) or []:
        s.developmental_profile.append(DevelopmentalObservation(
            element=p.get("element", ""), control_statement=p.get("control_statement", ""),
            trend=p.get("trend", ""), evidence=p.get("evidence", ""), episodes=p.get("episodes", 1)))
    return s


async def main():
    for cid in PICK:
        case = BY.get(cid)
        if not case:
            print(cid, "missing"); continue
        try:
            s = build(case)
            req = InteractRequest(content=case.get("initial_draft", ""), kind="writing")
            r = await governance_v2.run_governance_v2(s, req)
            gv = r.get("_governance_v2", {})
            tm = r.get("_triage_meta", {})
            sc = r["theory"].scaffolding_control
            interv = r["intervention"]
            print("=" * 70)
            print(cid, case["name"])
            print(" path:", tm.get("path"), "| branch:", gv.get("branch"), "| mode:", gv.get("mode"))
            print(" purpose_alignment:", gv.get("purpose", {}).get("purpose_alignment"),
                  "| unit:", gv.get("writing_unit", {}).get("unit"))
            print(" functional_rep:", (gv.get("functional_interpretation", {}).get("functional_representation") or "")[:160])
            print(" primary_target:", sc.primary_target)
            print(" focus:", interv.focus, "| one_target_ok:", bool(sc.primary_target and r["invitation"]))
            t = gv.get("transparency_state", {})
            print(" transparency keys:", sorted(t.keys()), "| why_this_now:", (t.get("why_this_now") or "")[:90])
            print(" latency:", tm.get("total_latency_s"), "s  (p1/p2/p3:", tm.get("t_pass1_s"), tm.get("t_pass2_s"), tm.get("t_pass3_s"), ")")
            print(" invitation:", (r["invitation"] or "")[:240])
        except Exception as e:
            import traceback; traceback.print_exc()
            print(cid, "ERROR", repr(e))
    print("DONE")


if __name__ == "__main__":
    asyncio.run(main())
