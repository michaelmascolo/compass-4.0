"""Compass 4.9 refinement acceptance (2 cases only, per cost rule).
A. Sprawling AI paragraph -> communicative load (current draft) is overloaded/crowded ->
   instructional_operation = structural_selection, episode does NOT close, coach teaches REDUCTION
   (select/condense/combine/move) rather than conceptual elaboration or transition.
B. Genuinely underdeveloped on-topic paragraph -> still DEVELOPS (instructional_operation = develop),
   NOT prematurely condensed/pruned.
Runs against localhost:8001 (pure backend DCO verification)."""
import time, json, requests

API = "http://localhost:8001/api"

SPRAWL = ("The real problem with AI in education is not that it exists but that students can use it to "
          "complete their work without doing the thinking, and thinking is how people actually learn. "
          "Schools have mostly responded by either banning AI or pretending it is not there, yet banning "
          "is nearly impossible to enforce and ignoring it lets students hand their thinking to a machine. "
          "What we should do instead is distinguish AI that completes a task from AI that guides learning, "
          "and build tools of the second kind. A tool like Compass does not write the paragraph for the "
          "student; it asks questions that lead them to construct the answer themselves. Because the "
          "student still performs the effortful intellectual work, they still learn, and because the tool "
          "removes overwhelm, they stay motivated, creating a virtuous loop where guided effort produces "
          "success, success builds motivation, and motivation fuels more learning. This also connects to "
          "the idea of the zone of proximal development, where a learner can do with support what they "
          "cannot yet do alone, and to theories of affordances in tool design, where the design of a tool "
          "shapes the actions it invites, which is why the interface and prompts of an educational AI "
          "matter so much for whether it helps or harms.")

# On-topic but thin: states a position, almost no development. Should DEVELOP, not prune.
THIN = ("I think schools should teach students how to use AI responsibly instead of banning it. "
        "Banning does not really work anyway.")


def create_session():
    s = requests.post(f"{API}/sessions", json={
        "assignment": "What should we do about AI in education?",
        "pedagogical_purpose": "State and support a position for a reader.",
        "current_writing_task": "One paragraph.",
        "assignment_prompt": "What should we do about AI in education?",
        "reasoning_mode": "canonical_v2"}, timeout=30)
    return s.json()["id"]


def wait(sid, nturns, budget_s=700):
    deadline = time.time() + budget_s
    while time.time() < deadline:
        time.sleep(5)
        r = requests.get(f"{API}/sessions/{sid}", timeout=30).json()
        ai = [t for t in r.get("turns", []) if t["role"] == "ai"
              and t.get("status") == "complete" and t.get("content")]
        failed = [t for t in r.get("turns", []) if t["role"] == "ai" and t.get("status") == "failed"]
        if failed:
            return "FAILED"
        if len(ai) >= nturns:
            return ai
    return None


def latest_dco(sid):
    tr = requests.get(f"{API}/dev/functional-v3-trace/{sid}", timeout=30).json().get("trace", [])
    return (tr[-1].get("developmental_cognition") or {}) if tr else {}


def report(label, sid, coach):
    dco = latest_dco(sid)
    s = dco.get("structural_load_analysis") or {}
    ec = dco.get("episode_closure") or {}
    cap = dco.get("communicative_capacity") or {}
    print(f"\n===== {label} =====")
    print("  coach:", (coach or "")[:500].replace("\n", " "))
    print("  current_communicative_load:", cap.get("current_communicative_load"),
          "| overload_risk:", cap.get("overload_risk"))
    print("  structural_load_status:", s.get("structural_load_status"),
          "| pruning_needed:", s.get("structural_pruning_needed"))
    print("  redundant:", json.dumps(s.get("redundant_structural_work"))[:140])
    print("  competing:", json.dumps(s.get("competing_structural_work"))[:140])
    print("  recommended_structural_operation:", (s.get("recommended_structural_operation") or "")[:140])
    print("  >> instructional_operation:", ec.get("instructional_operation"))
    print("  >> episode_closure_decision:", ec.get("episode_closure_decision"))
    return s, ec, coach


print("SESSION A (sprawling / overloaded)")
sidA = create_session(); print(" ", sidA)
requests.post(f"{API}/sessions/{sidA}/interact", json={"content": SPRAWL, "kind": "writing"}, timeout=30)
aiA = wait(sidA, 1)
sA, ecA, coachA = report("A: SPRAWLING PARAGRAPH", sidA, (aiA[-1].get("content") if isinstance(aiA, list) else str(aiA)))

print("\nSESSION B (thin / underdeveloped, on-topic)")
sidB = create_session(); print(" ", sidB)
requests.post(f"{API}/sessions/{sidB}/interact", json={"content": THIN, "kind": "writing"}, timeout=30)
aiB = wait(sidB, 1)
sB, ecB, coachB = report("B: THIN PARAGRAPH", sidB, (aiB[-1].get("content") if isinstance(aiB, list) else str(aiB)))

# --- acceptance ---
opA = ecA.get("instructional_operation"); clA = ecA.get("episode_closure_decision")
opB = ecB.get("instructional_operation")
lowA = (coachA or "").lower()
reduction_words = any(w in lowA for w in ["combine", "condense", "same", "overlap", "which version",
                                          "belongs in another", "move", "remove", "tighten", "select",
                                          "one strong version", "central"])
A_op_ok = opA in ("structural_selection", "condense_and_integrate")
A_not_closed = clA not in ("close_and_transition", "close_and_complete")
# B: genuinely underdeveloped -> must DEVELOP (develop or address a real gap), never prune/condense.
B_status = (sB.get("structural_load_status") or "").lower()
B_dev_ok = opB in ("develop", "address_material_gap", "consolidate")
B_not_pruned = opB not in ("structural_selection", "condense_and_integrate")
lowB = (coachB or "").lower()
B_develops = any(w in lowB for w in ["develop", "elaborat", "unfold", "explain", "reader", "next task"])

print("\n\n========== ACCEPTANCE ==========")
print("A instructional_operation = structural_selection/condense:", A_op_ok, "(op=%s)" % opA)
print("A episode did NOT close:", A_not_closed, "(closure=%s)" % clA)
print("A coach guides reduction (combine/condense/move/select):", reduction_words)
print("B structural_load_status underloaded/proportionate:", B_status in ("underloaded", "proportionate"))
print("B instructional_operation develops (not pruned):", B_dev_ok, "| not-pruned:", B_not_pruned, "(op=%s)" % opB)
print("B coach guides development:", B_develops)
print("\nA PASS:", A_op_ok and A_not_closed and reduction_words)
print("B PASS:", B_not_pruned and B_develops)
print("DONE")
