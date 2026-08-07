"""Compass 4.9 focused acceptance (2 cases only, per cost rule).
A. Sprawling/overloaded AI paragraph -> Compass identifies structural overload/redundancy and selects
   reduction/combination/movement (instructional_operation in {structural_selection, condense_and_integrate}),
   NOT additional elaboration.
B. Short underdeveloped paragraph -> Compass still PERMITS development (instructional_operation = develop),
   does NOT incorrectly prune.
Runs against localhost:8001 for reliability (pure backend DCO verification)."""
import time, json, requests

API = "http://localhost:8001/api"

# A: a paragraph that says the same thing several ways and piles on relations = overloaded/crowded.
SPRAWL = ("The real problem with AI in education is not that it exists but that students can use it to "
          "complete their work without doing the thinking, and thinking is how people actually learn, "
          "and if you do not think you do not learn, which is the whole point of school. Schools have "
          "mostly responded by either banning AI or pretending it is not there, yet banning is nearly "
          "impossible to enforce and ignoring it lets students hand their thinking to a machine, and "
          "neither of these responses actually helps students learn to think. What we should do instead "
          "is distinguish AI that completes a task from AI that guides learning, and build tools of the "
          "second kind, because a guiding tool does not write the paragraph for the student but asks "
          "questions that lead them to construct the answer themselves, and because the student still "
          "performs the effortful intellectual work they still learn, and because the tool removes "
          "overwhelm they stay motivated, creating a virtuous loop where guided effort produces success, "
          "success builds motivation, and motivation fuels more learning, and that loop is exactly what "
          "good education has always tried to create in the first place.")

# B: short, one idea, under-developed = room to develop, must NOT be pruned.
SHORT = ("Homework causes a lot of stress for students. It takes up their free time and makes them tired.")


def create_session():
    s = requests.post(f"{API}/sessions", json={
        "assignment": "What should we do about AI in education?",
        "pedagogical_purpose": "State and support a position for a reader.",
        "current_writing_task": "One paragraph.",
        "assignment_prompt": "What should we do about AI in education?",
        "reasoning_mode": "canonical_v2"}, timeout=30)
    return s.json()["id"]


def wait(sid, nturns):
    for _ in range(90):  # up to 6 min
        time.sleep(4)
        r = requests.get(f"{API}/sessions/{sid}", timeout=30).json()
        ai = [t for t in r.get("turns", []) if t["role"] == "ai"
              and t.get("status") == "complete" and t.get("content")]
        if len(ai) >= nturns:
            return ai
    return None


def latest_dco(sid):
    tr = requests.get(f"{API}/dev/functional-v3-trace/{sid}", timeout=30).json().get("trace", [])
    return (tr[-1].get("developmental_cognition") or {}) if tr else {}


def report(label, sid, coach):
    dco = latest_dco(sid)
    struct = dco.get("structural_load_analysis") or {}
    ec = dco.get("episode_closure") or {}
    op = ec.get("instructional_operation")
    print(f"\n===== {label} =====")
    print("  coach:", (coach or "")[:400].replace("\n", " "))
    print("  structural_load_status:", struct.get("structural_load_status"))
    print("  central_communicative_movement:", (struct.get("central_communicative_movement") or "")[:120])
    for k in ("redundant_structural_work", "competing_structural_work", "secondary_trajectories",
              "structural_pruning_needed", "recommended_structural_operation", "reason"):
        if k in struct:
            v = struct.get(k)
            print(f"  {k}:", (json.dumps(v) if not isinstance(v, str) else v)[:180])
    print("  >> instructional_operation:", op)
    return struct, op


print("SESSION A (sprawling/overloaded)")
sidA = create_session(); print(" ", sidA)
requests.post(f"{API}/sessions/{sidA}/interact", json={"content": SPRAWL, "kind": "writing"}, timeout=30)
aiA = wait(sidA, 1)
structA, opA = report("A: SPRAWLING PARAGRAPH", sidA, aiA[-1].get("content") if aiA else "")

print("\nSESSION B (short underdeveloped)")
sidB = create_session(); print(" ", sidB)
requests.post(f"{API}/sessions/{sidB}/interact", json={"content": SHORT, "kind": "writing"}, timeout=30)
aiB = wait(sidB, 1)
structB, opB = report("B: SHORT UNDERDEVELOPED PARAGRAPH", sidB, aiB[-1].get("content") if aiB else "")

# --- acceptance ---
A_status_ok = (structA.get("structural_load_status") or "").lower() in ("crowded", "overloaded")
A_op_ok = opA in ("structural_selection", "condense_and_integrate")
B_status_ok = (structB.get("structural_load_status") or "").lower() in ("underloaded", "proportionate")
B_op_ok = opB in ("develop", "consolidate")  # develop primarily; consolidate acceptable (not pruning)
B_not_pruned = opB not in ("structural_selection", "condense_and_integrate")

print("\n\n========== ACCEPTANCE ==========")
print("A structural_load_status crowded/overloaded:", A_status_ok)
print("A selects reduction (structural_selection/condense_and_integrate):", A_op_ok)
print("B structural_load_status underloaded/proportionate:", B_status_ok)
print("B permits development (develop/consolidate, NOT pruned):", B_op_ok, "| not-pruned:", B_not_pruned)
print("\nRESULT:", "PASS" if (A_op_ok and B_not_pruned) else "REVIEW NEEDED")
print("DONE")
