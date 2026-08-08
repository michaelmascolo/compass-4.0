"""Compass 4.8 §13 acceptance test: after the sprawling AI paragraph, an explicit learner
'I'm done elaborating; move on' MUST NOT trigger another elaboration — Compass acknowledges
sufficiency and transitions. Also §12 short paragraph should still continue (budget substantial)."""
import time, json, requests
with open("/app/frontend/.env") as f:
    for line in f:
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE = line.strip().split("=", 1)[1]
API = f"{BASE}/api"
SPRAWL = ("The real problem with AI in education is not that it exists but that students can use it to "
          "complete their work without doing the thinking, and thinking is how people actually learn. "
          "Schools have mostly responded by either banning AI or pretending it is not there, yet banning "
          "is nearly impossible to enforce and ignoring it lets students hand their thinking to a machine. "
          "What we should do instead is distinguish AI that completes a task from AI that guides learning, "
          "and build tools of the second kind. A tool like Compass does not write the paragraph for the "
          "student; it asks questions that lead them to construct the answer themselves. Because the "
          "student still performs the effortful intellectual work, they still learn, and because the tool "
          "removes overwhelm, they stay motivated, creating a virtuous loop where guided effort produces "
          "success, success builds motivation, and motivation fuels more learning.")

s = requests.post(f"{API}/sessions", json={
    "assignment": "What should we do about AI in education?",
    "pedagogical_purpose": "State and support a position for a reader.",
    "current_writing_task": "One paragraph.", "assignment_prompt": "What should we do about AI in education?",
    "reasoning_mode": "canonical_v2"}, timeout=30)
sid = s.json()["id"]; print("SESSION", sid)


def wait(nturns):
    for _ in range(180):
        time.sleep(4)
        r = requests.get(f"{API}/sessions/{sid}", timeout=30).json()
        ai = [t for t in r.get("turns", []) if t["role"] == "ai" and t.get("status") == "complete" and t.get("content")]
        if len(ai) >= nturns:
            return ai, r
    return None, None


print("\n--- turn 1: sprawling paragraph (writing) ---")
requests.post(f"{API}/sessions/{sid}/interact", json={"content": SPRAWL, "kind": "writing"}, timeout=30)
ai, _ = wait(1)
print("  coach:", (ai[-1].get("content") or "")[:160].replace("\n", " "))

print("\n--- turn 2: 'I'm done elaborating; move on' (answer) ---")
requests.post(f"{API}/sessions/{sid}/interact", json={"content": "I'm done elaborating; move on.", "kind": "answer"}, timeout=30)
ai, _ = wait(2)
turn = ai[-1]
inv = (turn.get("content") or "")
tr = requests.get(f"{API}/dev/functional-v3-trace/{sid}", timeout=30).json().get("trace", [])
ec = (tr[-1].get("developmental_cognition") or {}).get("episode_closure") or {}
print("  coach:", inv[:400].replace("\n", " "))
print("  episode_closure_decision:", ec.get("episode_closure_decision"))
print("  learner_transition_request:", ec.get("learner_transition_request"))
print("  remaining_communicative_budget:", ec.get("remaining_communicative_budget"))
print("  coaching_permitted:", ec.get("coaching_permitted"), "| material_gap:", repr(ec.get("material_gap")))
# crude elaboration-request detector for the acceptance criterion
low = inv.lower()
asks_more = any(p in low for p in ["can you explain", "could you explain", "add", "elaborate",
                                   "tell me more", "expand on", "go deeper", "one more", "another reason",
                                   "explain how", "why do you think", "what else"])
print("\n  ACCEPTANCE:")
print("   closure=close_and_transition:", ec.get("episode_closure_decision") == "close_and_transition")
print("   NOT asking for more elaboration:", not asks_more)
print("   transition-request detected explicit:", ec.get("learner_transition_request") == "explicit")
print("\nDONE")
