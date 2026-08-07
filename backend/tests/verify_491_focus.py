"""4.9.1 focus-label fix verification (1 case, per cost rule): preview session, sprawling paragraph.
Confirm: turn.instructional_operation == structural_selection, coaching remains a structural-selection
move, focus_of_work still 'Elaboration' (unchanged), and the new field is populated for the UI."""
import time, json, requests

API = "http://localhost:8001/api"
SPRAWL = ("The real problem with AI in education is that students use it to avoid thinking, and thinking "
          "is how people learn. Let me say that again: the danger is that students stop doing their own "
          "thinking, and since thinking is how learning happens, avoiding it means they do not learn. In "
          "other words, if a student lets AI think for them, no real learning takes place, because "
          "learning only happens when the student does the thinking themselves. Schools have responded by "
          "banning AI or ignoring it, but banning does not work and ignoring it is worse, and neither "
          "response helps students learn to think. What we should do instead is build AI that guides "
          "thinking rather than replacing it, so the student still does the effortful work and therefore "
          "still learns, and because the tool removes overwhelm they stay motivated, which creates a loop "
          "where effort produces success, success builds motivation, and motivation produces more effort "
          "and more learning. This also relates to the zone of proximal development, where a learner can "
          "do with support what they cannot yet do alone, and to affordance theory in design, where the "
          "features of a tool shape the actions people take with it, and also to research on intrinsic "
          "motivation, which shows that autonomy and competence drive engagement, all of which are "
          "separate frameworks that each deserve their own full treatment elsewhere.")

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
ic = (turn or {}).get("instructional_contract") or {}
print("\n=== INSTRUCTIONAL CONTRACT (learner-facing card) ===")
print("where_we_are:", ic.get("where_we_are"))
print("goal:", ic.get("goal"))
print("what_happens_next:", ic.get("what_happens_next"))
print("operation:", ic.get("operation"), "| pinned_episode_target (preserved):", (ic.get("pinned_episode_target") or "")[:80])
print("\n=== COACHING ===")
print(turn.get("content") if turn else "(none)")
