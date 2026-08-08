"""Sentence Craft reflexive-framework CALIBRATION (spec §14). Drives the REAL production SC turn
(sentence_craft_cognition + coordinated controller + coaching) on a phenomenon-rich fixed-mindset
paragraph and dumps the developer diagnostics: concrete candidate phenomena across the paragraph,
recurring patterns, the selected phenomenon + why, its reflexive category, scaffold, and the actual
learner-facing coaching. Expectations are NOT hard-coded — we report what the framework detects.

Run: cd /app/backend && set -a && source .env && set +a && python tests/calib_sc_fixedmindset.py
"""
import asyncio, sys, json
sys.path.insert(0, "/app/backend")
import functional_v3 as fv3
from compass_foundation import InstructionalState

ASSIGNMENT = "Explain how a fixed mindset can hold a student back and what they can do about it."

# Fixed-mindset paragraph deliberately rich in DIFFERENT concrete phenomena so we can see the
# framework DISCRIMINATE (contractions, 2nd-person 'you', colloquial, weak 'to be' verbs, a run-on,
# a weak/missing transition, vague reference). Not hard-coded as expectations.
PARAGRAPH = (
    "A fixed mindset is when you think you're just born smart or not. "
    "It is a really big problem and it is something that holds a lot of kids back. "
    "You give up because you think you can't get better so why even try, that is the trap. "
    "This shows that effort matters more than talent."
)


async def main():
    state = InstructionalState(session_id="calib-sc")
    state.sc_active = True
    state.sc_transitioned = True   # skip the transition preamble for a clean diagnostic read
    state.sc_index = 0
    dco = {"structural_load_analysis": {"central_communicative_movement":
           "A fixed mindset holds students back, but they can change it through effort."},
           "communicative_task": ASSIGNMENT, "completion": {}}

    res = await fv3._sentence_craft_turn(state, ASSIGNMENT, PARAGRAPH, dco, "", "revise")
    d = res["diagnostics"]

    print("\n================ SENTENCE CRAFT DIAGNOSTIC READOUT ================\n")
    print("PER-SENTENCE concrete phenomena detected (reflexive framework):")
    # re-run cognition read from diagnostics isn't per-sentence; show the paragraph-wide set + recurrence
    print("  candidate phenomena across paragraph:")
    for x in d.get("paragraph_candidate_phenomena", []):
        print(f"    - {x}  -> domain={fv3.sc_domain_for_pattern(x) or '(none)'}")
    print("\n  RECURRING patterns across the paragraph (domain -> #sentences):")
    for dom, cnt in sorted((d.get("paragraph_recurrence") or {}).items(), key=lambda kv: -kv[1]):
        print(f"    - {dom}: {cnt}")

    sel = d.get("selection", {})
    print("\nSELECTED for instruction this turn:")
    print(f"  active sentence:      \"{d.get('active_sentence_text','')}\"")
    print(f"  concrete phenomenon:  {d.get('selected_phenomenon','')}")
    print(f"  reflexive category:   {d.get('reflexive_category','')}")
    print(f"  operation (internal): {sel.get('operation')}")
    print(f"  scaffold level:       {sel.get('scaffold_level')}")
    print(f"  recurring pattern?    {sel.get('pattern_recurrent')} (count={sel.get('recurrence_count')})")
    print(f"  why selected:         {sel.get('reason')}")
    print(f"  candidate domains (active sentence): {d.get('candidate_domains')}")

    print("\nLEARNER-FACING COACHING:\n")
    print(res["invitation"])
    print("\n================ END ================\n")

    # basic non-hardcoded sanity: coaching must NOT be the old generic effect line
    generic = "communicate this more directly" in res["invitation"].lower() and not d.get("selected_phenomenon")
    print("generic-fallback avoided:", not generic)

asyncio.run(main())
