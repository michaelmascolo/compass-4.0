"""Compass 4.9.5 check (Phase 1 only): the sprawling AI paragraph should now externalize the arguments
as GROUPED conceptual chunks (headings with indented lettered items), ask the learner to choose
(preferably at the group level), in learner-centered language (no internal terms), and NOT ask to rewrite."""
import time, re, requests
API = "http://localhost:8001/api"
SPRAWL = ("AI is poised to reshape education, and schools need a real answer. Some teachers have banned it "
          "outright, others quietly ignore it, and a few try to police every assignment for signs of it. "
          "None of these responses works: bans are unenforceable, ignoring it lets students hand their "
          "thinking to a machine, and policing turns teachers into detectives. The answer is to distinguish "
          "AI that completes a task from AI that guides learning, and to build only the second kind. A tool "
          "like Compass, for instance, never writes the paragraph for the student; it asks questions that "
          "lead the student to construct the answer. This is the opposite of ChatGPT, whose affordances "
          "invite the student to request a finished product, because the design of a tool shapes the "
          "actions it invites. When a student does the effortful thinking with support, a learning loop "
          "forms: effort produces success, success builds motivation, and motivation fuels more effort. "
          "This is essentially the zone of proximal development, where a learner can do with support what "
          "they cannot yet do alone, and it also draws on the idea of effectance, the intrinsic satisfaction "
          "of producing an effect through one's own competence, which is a further reason guided tools keep "
          "students engaged.")
sid = requests.post(f"{API}/sessions/preview", json={"assignment": "What should we do about AI in education?", "canonical": True}, timeout=30).json()["id"]
print("SESSION", sid)
requests.post(f"{API}/sessions/{sid}/interact", json={"content": SPRAWL, "kind": "writing"}, timeout=30)
turn=None; deadline=time.time()+700
while time.time()<deadline:
    time.sleep(5)
    r=requests.get(f"{API}/sessions/{sid}", timeout=30).json()
    ai=[t for t in r.get("turns",[]) if t["role"]=="ai" and t.get("status")=="complete" and t.get("content")]
    if ai: turn=ai[-1]; break
c=turn.get("content") or ""; op=turn.get("instructional_operation")
print(">> op:", op)
print("\n=== COACHING ===\n", c)
low=c.lower()
cats=["problem","cause","solution","example","mechanism","loop","principle","evidence","conclusion","background","contrast","theory"]
cat_hits=[w for w in cats if w in low]
has_letters = len(re.findall(r"(?m)[A-I][\.\)]\s+\S", c))>=3
group_level_ask = any(w in low for w in ["group","groups","from the","one from","two from","which of these areas","category"])
no_internal = not any(w in low for w in ["structural selection","structural decomposition","reduction operation","instructional operation"])
no_rewrite = not any(w in low for w in ["rewrite","submit it again","resubmit","rebuild the paragraph"])
print("\n=== CHECKS ===")
print("op=structural_selection:", op=="structural_selection")
print("conceptual group headings present (>=2):", len(cat_hits)>=2, cat_hits)
print("items still lettered (>=3):", has_letters)
print("asks at group level:", group_level_ask)
print("no internal terminology spoken:", no_internal)
print("does NOT ask to rewrite (phase 1):", no_rewrite)
print("\nRESULT:", "PASS" if (op=="structural_selection" and len(cat_hits)>=2 and has_letters and no_internal and no_rewrite) else "REVIEW")
print("DONE")
