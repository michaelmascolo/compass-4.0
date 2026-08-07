"""4.9.1 focus-label fix verification (1 case, per cost rule): preview session, sprawling paragraph.
Confirm: turn.instructional_operation == structural_selection, coaching remains a structural-selection
move, focus_of_work still 'Elaboration' (unchanged), and the new field is populated for the UI."""
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
          "the zone of proximal development, where a learner can do with support what they cannot yet do "
          "alone, and to theories of affordances in tool design, where the design of a tool shapes the "
          "actions it invites, which is why the interface and prompts of an educational AI matter so much.")

s = requests.post(f"{API}/sessions/preview", json={"assignment": "What should we do about AI in education?", "canonical": True}, timeout=30).json()
sid = s["id"]; print("PREVIEW SESSION", sid)
requests.post(f"{API}/sessions/{sid}/interact", json={"content": SPRAWL, "kind": "writing"}, timeout=30)

deadline = time.time() + 700
turn = None
while time.time() < deadline:
    time.sleep(5)
    r = requests.get(f"{API}/sessions/{sid}", timeout=30).json()
    ai = [t for t in r.get("turns", []) if t["role"] == "ai" and t.get("status") == "complete" and t.get("content")]
    if any(t["role"] == "ai" and t.get("status") == "failed" for t in r.get("turns", [])):
        print("TURN FAILED"); break
    if ai:
        turn = ai[-1]; break

print("\n=== TURN FIELDS ===")
print("SESSION_ID_FOR_SCREENSHOT:", sid)
print("focus_of_work:", turn.get("focus_of_work") if turn else None)
print(">> instructional_operation:", turn.get("instructional_operation") if turn else None)
print("\n=== COACHING ===")
print(turn.get("content") if turn else "(none)")
