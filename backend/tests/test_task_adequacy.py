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
# §9 calibration: a coherent, adequate AI-in-education response
draft = ("The problem with AI in education is that students can use tools like chatbots to do their work "
         "for them, which means they stop learning. Many schools have responded either by banning these "
         "tools or by ignoring the issue, but banning them is hard to enforce and ignoring the problem "
         "lets students avoid thinking. A better approach is to design AI tools that support learning "
         "instead of replacing it: rather than writing the essay for a student, the tool asks the student "
         "questions that guide them to construct the answer themselves. This keeps the student doing the "
         "actual thinking, so they still learn, while the tool makes the work less overwhelming. In this "
         "way AI creates a virtuous loop where students get help and still build their own understanding.")
requests.post(f"{API}/sessions/{sid}/interact", json={"content": draft, "kind": "writing"}, timeout=30).raise_for_status()
dco = None
for i in range(70):
    time.sleep(4)
    tr = requests.get(f"{API}/dev/functional-v3-trace/{sid}", timeout=30)
    if tr.status_code == 200:
        t = tr.json().get("trace", [])
        if t and t[-1].get("developmental_cognition", {}).get("task_relative_adequacy"):
            dco = t[-1]["developmental_cognition"]; break
if not dco:
    print("FAIL: no task_relative_adequacy"); sys.exit(1)
tra = dco["task_relative_adequacy"]
print("\n=== task_relative_adequacy ==="); print(json.dumps(tra, indent=2, ensure_ascii=False))
print("\n=== timely_success_status ==="); print(json.dumps(dco.get("timely_success_status"), indent=2, ensure_ascii=False))
# ensure map + orientation still emit (tail-drop regression check)
print("\nmap present:", "constructible_whole_map" in dco, "| orientation present:", "learner_orientation" in dco,
      "| completion present:", "completion_readiness" in dco)
valid = {"inadequate","approaching_adequacy","adequate","uncertain"}
ok = (isinstance(tra, dict) and tra.get("value") in valid and isinstance(tra.get("task_expectations"), list)
      and tra.get("reason") and "transition_recommendation" in tra
      and isinstance(dco.get("timely_success_status"), dict))
# §9: expect adequate/approaching with transition presumption; if inadequate, must name a material gap
if tra.get("value") == "inadequate" and not (tra.get("material_gap") or "").strip():
    print("WARN: inadequate WITHOUT a specific material gap (violates presumption rule)")
print("\nRESULT:", "PASS" if ok else "FAIL"); sys.exit(0 if ok else 1)
