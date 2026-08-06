import sys, json, time, requests
with open("/app/frontend/.env") as f:
    for line in f:
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE = line.strip().split("=", 1)[1]
API = f"{BASE}/api"
s = requests.post(f"{API}/sessions", json={
    "assignment": "What should we do about AI in education?",
    "pedagogical_purpose": "Develop the learner's ability to state and support a position for a reader.",
    "current_writing_task": "One paragraph.",
    "assignment_prompt": "What should we do about AI in education?",
    "reasoning_mode": "canonical_v2",
}, timeout=30)
s.raise_for_status(); sid = s.json()["id"]; print("SESSION", sid)
# §12 calibration: a substantial, coherent AI-in-education paragraph (developmentally advanced, needs only org/sentence work)
draft = ("The real problem with AI in education is not that it exists but that students can use it to complete "
         "their work without doing the thinking, and thinking is how people actually learn. Schools have mostly "
         "responded by either banning AI or pretending it is not there, yet banning is nearly impossible to "
         "enforce and ignoring it simply lets students hand their thinking over to a machine. What we should do "
         "instead is distinguish AI that completes a task from AI that guides learning, and build tools of the "
         "second kind. A tool like Compass does not write the paragraph for the student; it asks the student "
         "questions that lead them to construct the answer themselves. Because the student still performs the "
         "effortful intellectual work, they still learn, and because the tool removes some of the overwhelm, "
         "they stay motivated to keep going. That creates a virtuous loop: guided effort produces a small "
         "success, the success builds motivation, and the motivation fuels more learning.")
requests.post(f"{API}/sessions/{sid}/interact", json={"content": draft, "kind": "writing"}, timeout=30).raise_for_status()
dco = None
for i in range(70):
    time.sleep(4)
    tr = requests.get(f"{API}/dev/functional-v3-trace/{sid}", timeout=30)
    if tr.status_code == 200:
        t = tr.json().get("trace", [])
        if t and t[-1].get("developmental_cognition", {}).get("learner_relative_sufficiency"):
            dco = t[-1]["developmental_cognition"]; break
if not dco:
    print("FAIL: no learner_relative_sufficiency"); sys.exit(1)
lrs = dco["learner_relative_sufficiency"]
print("\n=== learner_relative_sufficiency ==="); print(json.dumps(lrs, indent=2, ensure_ascii=False))
print("\nvalue:", lrs.get("value"), "| dev_advance:", lrs.get("developmental_advance"),
      "| org_stability:", lrs.get("organization_stability"), "| coherence:", lrs.get("self_contained_coherence"),
      "| value_further:", lrs.get("likely_value_of_further_instruction"),
      "| cost_further:", lrs.get("likely_cost_of_further_instruction"),
      "| effectance_risk:", lrs.get("effectance_risk"), "| transition:", lrs.get("transition_recommendation"))
print("\nregression -> map:", "constructible_whole_map" in dco, "orientation:", "learner_orientation" in dco,
      "completion:", "completion_readiness" in dco, "adequacy:", "task_relative_adequacy" in dco)
valid = {"not_yet_sufficient","approaching_sufficiency","sufficient","uncertain"}
ok = (isinstance(lrs, dict) and lrs.get("value") in valid and lrs.get("learner_accessible_target")
      and lrs.get("developmental_advance") and lrs.get("transition_recommendation") and lrs.get("reason"))
print("\nRESULT:", "PASS" if ok else "FAIL"); sys.exit(0 if ok else 1)
