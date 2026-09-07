"""4.7 calibration: communicative_capacity populates, is placed early (survives truncation),
and constrains transition. Case §11 (sprawling AI-education) + §12A (short underdeveloped)."""
import time, json, requests
with open("/app/frontend/.env") as f:
    for line in f:
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE = line.strip().split("=", 1)[1]
API = f"{BASE}/api"

SPRAWL = ("The real problem with AI in education is not that it exists but that students can use it to "
          "complete their work without doing the thinking, and thinking is how people actually learn. "
          "Schools have mostly responded by either banning AI or pretending it is not there, yet banning "
          "is nearly impossible to enforce and ignoring it simply lets students hand their thinking over "
          "to a machine. What we should do instead is distinguish AI that completes a task from AI that "
          "guides learning, and build tools of the second kind. A tool like Compass does not write the "
          "paragraph for the student; it uses a hidden developmental cognition object, a structure "
          "engine, and a sentence-craft module to ask questions that lead them to construct the answer "
          "themselves. Because the student still performs the effortful intellectual work, they still "
          "learn, and because the tool removes overwhelm, they stay motivated, creating a virtuous loop "
          "where guided effort produces success, success builds motivation, and motivation fuels more "
          "learning, which over time could reshape testing, grading, teacher training, and policy.")
SHORT = ("Homework should be reduced. It is bad for students.")

CASES = [("11_sprawl_ai", "What should we do about AI in education?", SPRAWL),
         ("12A_short", "Should schools reduce homework?", SHORT)]

for cid, assign, draft in CASES:
    print("\n" + "=" * 70); print("CASE", cid); print("=" * 70)
    s = requests.post(f"{API}/sessions", json={
        "assignment": assign, "pedagogical_purpose": "State and support a position for a reader.",
        "current_writing_task": "One paragraph.", "assignment_prompt": assign,
        "reasoning_mode": "canonical_v2"}, timeout=30)
    sid = s.json()["id"]; print("SESSION", sid)
    requests.post(f"{API}/sessions/{sid}/interact", json={"content": draft, "kind": "writing"}, timeout=30)
    tr = None
    for _ in range(170):
        time.sleep(4)
        d = requests.get(f"{API}/dev/functional-v3-trace/{sid}", timeout=30).json()
        t = d.get("trace", [])
        if t and (t[-1].get("developmental_cognition") or {}).get("communicative_capacity"):
            tr = t[-1]; break
    if not tr:
        print("  FAIL: no communicative_capacity in trace"); continue
    dco = tr["developmental_cognition"]; cc = dco.get("communicative_capacity") or {}
    lrs = dco.get("learner_relative_sufficiency") or {}; tra = dco.get("task_relative_adequacy") or {}
    print("  writing_unit:", cc.get("writing_unit"))
    print("  central_movement:", cc.get("central_communicative_movement"))
    print("  load:", cc.get("current_communicative_load"), "| remaining:", cc.get("remaining_capacity"),
          "| overload:", cc.get("overload_risk"), "| scope_status:", cc.get("scope_status"))
    print("  defer/exclude:", cc.get("material_to_defer_or_exclude"))
    print("  lrs_present:", bool(lrs), "| transition(sufficiency):", lrs.get("transition_recommendation"),
          "| adequacy:", tra.get("value"), "| adequacy_transition:", tra.get("transition_recommendation"))
    print("  tail_recovered:", bool(lrs.get("_tail_recovered")))
print("\nDONE")
