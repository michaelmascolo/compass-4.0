"""Verify the whole-paragraph completion guard: a revision that satisfies the requested
operation (develop) but leaves the paragraph still needing organization/support must NOT be
marked 'complete'. The engine should advance/recurse to the remaining limiting function."""
import asyncio
import os
import uuid

import functional_v3 as fv3
import compass_foundation as F

ASSIGNMENT = "What is the fixed mindset?"

T1 = (
    "The fixed mindset is the belief that one's abilities are fixed and cannot change. People with "
    "this mindset see qualities like math, sports, and art as permanent traits. They think "
    "intelligence is something you are born with."
)

# Revision: adds development ("why it matters") but keeps everything as a loose, unsequenced pile
# and offers no grounding — organization should read partial/weak, support missing/partial.
T2_partial = (
    "The fixed mindset is the belief that one's abilities are fixed and cannot change. It matters "
    "because it affects effort. Also people think intelligence is inborn. And it matters because they "
    "give up. Math and sports are seen as permanent. It matters for motivation too. IQ is seen as "
    "fixed. People with this mindset avoid challenges. Talent is seen as something you either have or "
    "don't. It also matters because they fear failure. Effort seems pointless to them."
)


async def main():
    assert os.environ.get("EMERGENT_LLM_KEY")
    session = {"id": f"fv3-guard-{uuid.uuid4().hex[:8]}", "assignment": ASSIGNMENT,
               "assignment_prompt": ASSIGNMENT, "current_writing_task": "one paragraph",
               "reasoning_mode": "canonical_v2", "turns": [], "telos": {}}
    await fv3.run(session, T1, "writing")
    session["turns"] = [{"id": "t1", "role": "student", "content": T1}]
    r2 = await fv3.run(session, T2_partial, "revise")
    fd = (r2.get("decision") or {}).get("functional_decision") or {}
    cont = (fd.get("continuity_decision") or "").lower()
    org = ((fd.get("functional_organization") or {}).get("status") or "").lower()
    guard = fd.get("_completion_guard")
    print("continuity_decision:", cont)
    print("functional_organization.status:", org)
    print("selected_function:", fd.get("selected_function"))
    print("completion_guard:", guard)
    print("invitation:\n", (r2.get("invitation") or "")[:600])
    ok = cont != "complete"  # must not prematurely complete a still-disorganized paragraph
    print(f"\n[{'PASS' if ok else 'FAIL'}] disorganized revision NOT marked complete")
    try:
        await F.STATES.delete_many({"session_id": session["id"]})
    except Exception:
        pass
    return ok


if __name__ == "__main__":
    raise SystemExit(0 if asyncio.run(main()) else 1)
