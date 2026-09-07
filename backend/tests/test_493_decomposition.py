"""Compass 4.9.3 acceptance (1 case, per cost rule): the sprawling AI paragraph.
Expected student experience: (1) plainly says paragraph does too much; (2) restates central thesis;
(3) lists major local arguments already present; (4) explains there are too many for one paragraph;
(5) asks learner to choose a small subset; (6) gives ONE concrete rewrite operation; (7) stop + resubmit;
(8) no new conceptual elaboration; (9) no sentence-level work begins yet."""
import time, json, re, requests
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
coach=(turn or {}).get("content") or ""
op=(turn or {}).get("instructional_operation")
print(">> instructional_operation:", op)
print("\n=== COACHING ===\n", coach)

low=coach.lower()
diagnose = any(w in low for w in ["too much", "more than", "carrying more", "trying to do", "more work than", "can't do all", "can hold"])
thesis = any(w in low for w in ["central idea", "main idea", "your thesis", "central argument", "central movement", "i think your"])
# lettered/bulleted list of >=3 items
letters = len(re.findall(r"(?m)^\s*[A-F][\.\)]\s+", coach)) >= 3
bullets = len(re.findall(r"(?m)^\s*[-•\*]\s+\S", coach)) >= 3
listed = letters or bullets
too_many = any(w in low for w in ["separate paragraph", "another paragraph", "own paragraph", "belong", "related but", "not all doing", "each of those"])
choose_subset = any(w in low for w in ["two or three", "two of", "three of", "which of these", "choose", "select", "pick", "which two"])
rewrite_op = any(w in low for w in ["rewrite", "using only", "write a new version", "redraft", "revise the paragraph using"])
stop_resubmit = any(w in low for w in ["submit", "resubmit", "send it back", "share it again", "post it again"])
no_counter = not any(w in low for w in ["counterargument", "counter-argument", "objection", "rebuttal", "opposing view"])

print("\n=== ACCEPTANCE ===")
for name,val in [("op==structural_selection", op=="structural_selection"),
                 ("1 diagnoses too much", diagnose),
                 ("2 restates thesis", thesis),
                 ("3 lists local arguments (>=3)", listed),
                 ("4 explains too many for one paragraph", too_many),
                 ("5 asks to choose subset", choose_subset),
                 ("6 one concrete rewrite operation", rewrite_op),
                 ("7 stop + resubmit", stop_resubmit),
                 ("8 no counterargument", no_counter)]:
    print(f"  {'PASS' if val else 'FAIL'}  {name}")
allpass = op=="structural_selection" and diagnose and thesis and listed and too_many and choose_subset and rewrite_op and stop_resubmit and no_counter
print("\nRESULT:", "PASS" if allpass else "REVIEW")
print("DONE")
