"""Compass 3.0 Sprint 1 — function-centered engine acceptance harness.

Runs the Fixed-Mindset case directly through functional_v3.run() (bypasses the API,
hits the same reasoning path). Checks:
  T1  topic recognized; focus recognized as sufficient; NOT held on Thesis for polish;
      selected function is develop OR functional_organization (student term Elaboration/Organization);
      full internal schema emitted; invitation does not rewrite the paragraph.
  T2  a revision that improves organization is acknowledged (progress named) and the
      engine advances/holds/completes coherently (does not repeat a fulfilled request).
"""
import asyncio
import json
import os
import uuid

import functional_v3 as fv3
import compass_foundation as F

ASSIGNMENT = "What is the fixed mindset?"

PARA_T1 = (
    "What is the fixed mindset? The fixed mindset consists of the belief that one's abilities are "
    "fixed and cannot change. \"Fixed\" and \"unchanging\" abilities are those that can be said to be "
    "\"carved in stone\" (Dweck, 2006, p.x). Qualities that are seen as \"carved in stone\" also tend "
    "to be seen as deep-seated traits. For example, people with the fixed mindset see qualities such "
    "as math, sports, and artistic ability as fixed traits that are permanent and unchanging. They "
    "think they are born with a certain level of intelligence; they believe that IQ test asses a "
    "person's unchanging intelligence. People with fixed mindsets believe that a persons fixed "
    "abilities have physical cause. People with fixed mindsets believe that there physical traits and "
    "qualities are inborn. They believe that there are fixed physical differences that comes with a "
    "persons brain and genes. They believe if there good at something they don't have to be good at "
    "everything else. Fixed minded people don't believe they can change how they work or improve "
    "there failures."
)

# A revision that organizes the ideas so each unfolds the thesis (models learner progress on Develop/Org).
PARA_T2 = (
    "The fixed mindset is the belief that one's abilities are fixed and cannot change. This belief "
    "shapes how people explain their own qualities. First, because they see ability as \"carved in "
    "stone\" (Dweck, 2006), they treat skills like math, sports, and art as permanent traits rather "
    "than things that can grow. Second, this leads them to trust measures like IQ tests as fixed "
    "verdicts about intelligence, since if ability cannot change, a single score can define it. "
    "Finally, and most importantly, this belief discourages effort: if failure simply reveals a limit "
    "that cannot move, there is little reason to try to improve. In this way each idea unfolds why the "
    "belief that ability is fixed matters for how a person learns."
)


def _make_session():
    return {
        "id": f"fv3-test-{uuid.uuid4().hex[:8]}",
        "assignment": ASSIGNMENT,
        "assignment_prompt": ASSIGNMENT,
        "current_writing_task": "one paragraph",
        "reasoning_mode": "canonical_v2",
        "turns": [],
        "telos": {},
    }


def _check(label, cond, detail=""):
    print(f"  [{'PASS' if cond else 'FAIL'}] {label}" + (f" — {detail}" if detail else ""))
    return cond


async def main():
    assert os.environ.get("EMERGENT_LLM_KEY"), "EMERGENT_LLM_KEY missing"
    session = _make_session()
    results = []

    print("\n=== TURN 1: Fixed Mindset (first submission) ===")
    r1 = await fv3.run(session, PARA_T1, "writing")
    fd1 = (r1.get("decision") or {}).get("functional_decision") or {}
    target1 = (r1.get("decision") or {}).get("selected_instructional_object")
    inv1 = r1.get("invitation") or ""
    print("  full internal decision schema:")
    print(json.dumps(fd1, indent=2)[:2600])
    print(f"\n  selected_instructional_object (student term): {target1}")
    print(f"  invitation:\n{inv1}\n")

    schema_keys = {"communicative_task", "topic", "current_focus", "focus_status", "functions",
                   "functional_organization", "naive_reader_need", "selected_function",
                   "student_facing_term", "selected_operation", "local_target",
                   "developmental_sufficiency", "continuity_decision", "confidence"}
    results.append(_check("T1 full schema emitted", schema_keys.issubset(set(fd1.keys())),
                          f"missing={schema_keys - set(fd1.keys())}"))
    results.append(_check("T1 topic ~ fixed mindset", "fixed mindset" in (fd1.get("topic") or "").lower(),
                          fd1.get("topic")))
    results.append(_check("T1 focus recognized as sufficient (not held for polish)",
                          (fd1.get("focus_status") or "").lower() == "sufficient",
                          f"focus_status={fd1.get('focus_status')}"))
    results.append(_check("T1 selected function is develop OR functional_organization",
                          (fd1.get("selected_function") or "").lower() in ("develop", "functional_organization"),
                          f"selected_function={fd1.get('selected_function')}"))
    results.append(_check("T1 student term is Elaboration OR Organization",
                          target1 in ("Elaboration", "Organization"), f"target={target1}"))
    results.append(_check("T1 naive_reader_need populated", bool((fd1.get("naive_reader_need") or "").strip())))
    # ownership: invitation must not rewrite the paragraph for the learner
    lowered = inv1.lower()
    rewrote = any(p in lowered for p in ("here's your", "here is your", "rewritten version",
                                         "i'll rewrite", "i will rewrite", "use this sentence"))
    results.append(_check("T1 invitation does not rewrite the paragraph", not rewrote))
    results.append(_check("T1 invitation is non-empty", len(inv1.strip()) > 40))

    print("=== TURN 2: revision that organizes ideas (compare + advance/complete) ===")
    session["turns"] = [{"id": "t1", "role": "student", "content": PARA_T1},
                        {"id": "a1", "role": "assistant", "content": inv1}]
    r2 = await fv3.run(session, PARA_T2, "revise")
    fd2 = (r2.get("decision") or {}).get("functional_decision") or {}
    target2 = (r2.get("decision") or {}).get("selected_instructional_object")
    inv2 = r2.get("invitation") or ""
    print(f"  continuity_decision: {fd2.get('continuity_decision')}")
    print(f"  progress_since_last_turn: {fd2.get('progress_since_last_turn')}")
    print(f"  selected_function: {fd2.get('selected_function')} -> term {target2}")
    print(f"  invitation:\n{inv2}\n")
    results.append(_check("T2 continuity_decision is a revision verdict",
                          (fd2.get("continuity_decision") or "").lower() in ("hold", "advance", "recurse", "complete"),
                          fd2.get("continuity_decision")))
    results.append(_check("T2 progress named (not empty)", bool((fd2.get("progress_since_last_turn") or "").strip())))
    results.append(_check("T2 invitation non-empty + no rewrite",
                          len(inv2.strip()) > 40 and "here's your" not in inv2.lower()))

    # cleanup test state/audit
    try:
        await F.STATES.delete_many({"session_id": session["id"]})
    except Exception:
        pass

    passed = sum(1 for x in results if x)
    print(f"\n==== RESULT: {passed}/{len(results)} checks passed ====")
    return passed == len(results)


if __name__ == "__main__":
    ok = asyncio.run(main())
    raise SystemExit(0 if ok else 1)
