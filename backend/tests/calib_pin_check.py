"""Focused check: ai_education 2-turn episode. Confirms (1) no DCO truncation on the
continuation turn, (2) learner_accessible_target is PINNED identical across turns,
(3) accessible_target_achieved flips to yes when the learner performs the operation,
(4) richer organization appears under next_developmental_opportunity, (5) transition holds."""
import sys, json, time, requests
with open("/app/frontend/.env") as f:
    for line in f:
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE = line.strip().split("=", 1)[1]
API = f"{BASE}/api"

T1 = ("The real problem with AI in education is not that it exists but that students can use it to "
      "complete their work without doing the thinking, and thinking is how people actually learn. Schools "
      "have mostly responded by either banning AI or pretending it is not there, yet banning is nearly "
      "impossible to enforce and ignoring it simply lets students hand their thinking over to a machine. "
      "What we should do instead is distinguish AI that completes a task from AI that guides learning, and "
      "build tools of the second kind. A tool like Compass does not write the paragraph for the student; it "
      "asks the student questions that lead them to construct the answer themselves. Because the student "
      "still performs the effortful intellectual work, they still learn, and because the tool removes some "
      "of the overwhelm, they stay motivated to keep going. That creates a virtuous loop: guided effort "
      "produces a small success, the success builds motivation, and the motivation fuels more learning.")
T2 = ("The real problem with AI in education is not that it exists but that students can use it to "
      "complete their work without doing the thinking, and thinking is how people actually learn. Schools "
      "have mostly responded by either banning AI or pretending it is not there, yet banning is nearly "
      "impossible to enforce and ignoring it simply lets students hand their thinking over to a machine. "
      "What we should do instead is distinguish AI that completes a task from AI that guides learning, and "
      "build tools of the second kind. A tool like Compass does not write the paragraph for the student; it "
      "asks the student questions that lead them to construct the answer themselves. Because the student "
      "still performs the effortful intellectual work, they still learn. This is what creates a virtuous "
      "loop: because the tool breaks an overwhelming task into one guided question at a time, the student "
      "actually finishes a piece of real thinking; finishing it feels like a success, and that success "
      "makes them willing to attempt the next question instead of giving up; each attempt is more genuine "
      "thinking, so the learning and the motivation keep feeding each other, which is exactly what banning "
      "or ignoring AI destroys.")

s = requests.post(f"{API}/sessions", json={
    "assignment": "What should we do about AI in education?",
    "pedagogical_purpose": "Develop the learner's ability to state and support a position for a reader.",
    "current_writing_task": "One paragraph.", "assignment_prompt": "What should we do about AI in education?",
    "reasoning_mode": "canonical_v2"}, timeout=30)
s.raise_for_status(); sid = s.json()["id"]; print("SESSION", sid)


def wait(n):
    for _ in range(180):
        time.sleep(4)
        tr = requests.get(f"{API}/dev/functional-v3-trace/{sid}", timeout=30)
        if tr.status_code == 200:
            t = tr.json().get("trace", [])
            if len(t) >= n and (t[n-1].get("developmental_cognition") or {}).get("learner_relative_sufficiency"):
                return t
    return None


results = []
for i, draft in enumerate((T1, T2), start=1):
    print(f"\n--- turn {i} ---")
    requests.post(f"{API}/sessions/{sid}/interact", json={"content": draft, "kind": "writing"}, timeout=30)
    tr = wait(i)
    if not tr:
        # inspect whether the DCO truncated
        raw = requests.get(f"{API}/dev/functional-v3-trace/{sid}", timeout=30).json().get("trace", [])
        dco = (raw[i-1].get("developmental_cognition") if len(raw) >= i else {}) or {}
        print(f"FAIL turn {i}: lrs missing. dco keys={len(dco)} last={list(dco.keys())[-5:]}")
        sys.exit(1)
    dco = tr[i-1]["developmental_cognition"]; lrs = dco["learner_relative_sufficiency"]
    print("  dco_keys:", len(dco), "| lrs_present: True")
    print("  value:", lrs.get("value"), "| achieved:", lrs.get("accessible_target_achieved"),
          "| ep_status:", lrs.get("episode_target_status"), "| transition:", lrs.get("transition_recommendation"))
    print("  TARGET:", lrs.get("learner_accessible_target"))
    if lrs.get("_target_before_pin_enforcement"):
        print("  [PIN ENFORCED] model wanted:", lrs.get("_target_before_pin_enforcement"))
    print("  NEXT_OPP:", lrs.get("next_developmental_opportunity"))
    print("  ADEQUACY:", dco.get("task_relative_adequacy", {}).get("value"),
          "| timely:", dco.get("timely_success_status", {}).get("value"))
    results.append(lrs)

t1, t2 = results
print("\n=== PIN VERDICT ===")
print("targets identical:", t1.get("learner_accessible_target") == t2.get("learner_accessible_target"))
print("t1 target:", repr(t1.get("learner_accessible_target")))
print("t2 target:", repr(t2.get("learner_accessible_target")))
print("t2 ep_status:", t2.get("episode_target_status"), "| t2 achieved:", t2.get("accessible_target_achieved"))
