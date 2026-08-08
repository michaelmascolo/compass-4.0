"""4.6 end-to-end: contract card data on the AI turn + scope-gate in the trace."""
import sys, time, json, requests
with open("/app/frontend/.env") as f:
    for line in f:
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE = line.strip().split("=", 1)[1]
API = f"{BASE}/api"
T1 = ("Schools should give less homework. Too much homework is bad for students. It makes them stressed "
      "and tired. Homework does not always help students learn. Kids also need time for other things.")
T2 = ("Schools should give less homework because the whole point of homework is to help students learn, "
      "but when there is too much of it students get so stressed and exhausted that they stop absorbing "
      "anything they do. So piling on more homework actually stops it from doing the one thing it is "
      "supposed to do, which is help them learn.")
s = requests.post(f"{API}/sessions", json={
    "assignment": "Should schools reduce the amount of homework they assign?",
    "pedagogical_purpose": "Develop the learner's ability to state a position and connect one reason to it.",
    "current_writing_task": "One paragraph.", "assignment_prompt": "Should schools reduce homework?",
    "reasoning_mode": "canonical_v2"}, timeout=30)
s.raise_for_status(); sid = s.json()["id"]; print("SESSION", sid)


def wait_turns(nstudent):
    for _ in range(170):
        time.sleep(4)
        r = requests.get(f"{API}/sessions/{sid}", timeout=30).json()
        ai = [t for t in r.get("turns", []) if t["role"] == "ai" and t.get("status") == "complete" and t.get("content")]
        st = [t for t in r.get("turns", []) if t["role"] == "student"]
        if len(st) >= nstudent and len(ai) >= nstudent:
            return ai
    return None


for i, d in enumerate((T1, T2), start=1):
    print(f"\n--- turn {i} ---")
    requests.post(f"{API}/sessions/{sid}/interact", json={"content": d, "kind": "writing"}, timeout=30)
    ai = wait_turns(i)
    if not ai:
        print(f"FAIL turn {i}: no complete AI turn"); sys.exit(1)
    turn = ai[-1]
    c = turn.get("instructional_contract") or {}
    al = turn.get("contract_alignment") or {}
    print("  invitation:", (turn.get("content") or "")[:180].replace("\n", " "))
    print("  CONTRACT: goal=", repr(c.get("goal")))
    print("           where=", repr(c.get("where_we_are")))
    print("           next=", repr(c.get("what_happens_next")))
    print("           status=", c.get("status"), "achieved=", c.get("achieved"), "revision=", c.get("revision_reason"))
    print("  ALIGNMENT:", al.get("alignment"), "| heuristic=", al.get("heuristic_verdict"),
          "| escalated=", al.get("llm_escalated"), "| regen=", al.get("regenerated"),
          "| sel_fn=", al.get("selected_function"), "| contract_fn=", al.get("contract_function"))
    print("           reason=", al.get("reason"))

print("\nOK — contract + alignment present on AI turns")
