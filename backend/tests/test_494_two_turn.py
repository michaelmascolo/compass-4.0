"""Compass 4.9.4 acceptance (1 case, two turns): sprawling AI paragraph.
Turn 1: diagnose + thesis + visible list of arguments + ask ONLY to choose a subset (no rewrite).
Turn 2 (after learner selects): re-show the selected subset + ONE rewrite operation + stop/resubmit.
Learner must never have to remember what the letters meant between turns."""
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


def wait_ai(sid, n):
    deadline=time.time()+700
    while time.time()<deadline:
        time.sleep(5)
        r=requests.get(f"{API}/sessions/{sid}", timeout=30).json()
        ai=[t for t in r.get("turns",[]) if t["role"]=="ai" and t.get("status")=="complete" and t.get("content")]
        if len(ai)>=n: return ai
    return None

sid = requests.post(f"{API}/sessions/preview", json={"assignment": "What should we do about AI in education?", "canonical": True}, timeout=30).json()["id"]
print("SESSION", sid)

# TURN 1
requests.post(f"{API}/sessions/{sid}/interact", json={"content": SPRAWL, "kind": "writing"}, timeout=30)
ai=wait_ai(sid,1)
t1=ai[-1]; op1=t1.get("instructional_operation"); c1=t1.get("content") or ""
print("\n===== TURN 1 (op=%s) =====\n" % op1, c1)

# TURN 2 — learner selects a subset (message, not a new paragraph)
requests.post(f"{API}/sessions/{sid}/interact", json={"content": "I'll keep B, C, and E.", "kind": "answer"}, timeout=30)
ai=wait_ai(sid,2)
t2=ai[-1]; op2=t2.get("instructional_operation"); c2=t2.get("content") or ""
print("\n===== TURN 2 (op=%s) =====\n" % op2, c2)

l1=c1.lower(); l2=c2.lower()
# Turn 1 checks
t1_diag = any(w in l1 for w in ["too much","more than","carrying more","trying to do","more work than","can hold"])
t1_thesis = any(w in l1 for w in ["central idea","main idea","your thesis","central argument","i think your"])
t1_list = len(re.findall(r"(?m)^\s*[A-G][\.\)]\s+", c1))>=3 or len(re.findall(r"(?m)^\s*[-•\*]\s+\S", c1))>=3
t1_choose = any(w in l1 for w in ["two or three","which of these","which two","choose","select","most necessary","most belong"])
t1_no_rewrite = not any(w in l1 for w in ["rewrite","submit it again","submit again","resubmit","rebuild the paragraph"])
# Turn 2 checks
t2_reshow = any(w in l2 for w in ["you chose","you selected","you picked","you kept","b,","b."]) or (("b" in l2 and "c" in l2 and "e" in l2))
t2_rewrite = any(w in l2 for w in ["rewrite","using only","rebuild","write a new version","use only these"])
t2_nonew = any(w in l2 for w in ["nothing new","without adding","don't add","do not add","add anything new"])
t2_stop = any(w in l2 for w in ["submit","resubmit","send it back","share it again"])

print("\n=== ACCEPTANCE ===")
for n,v in [("T1 op=structural_selection", op1=="structural_selection"),
            ("T1 diagnoses overload", t1_diag),
            ("T1 shows thesis", t1_thesis),
            ("T1 visibly lists arguments (>=3)", t1_list),
            ("T1 asks to choose subset", t1_choose),
            ("T1 does NOT ask to rewrite", t1_no_rewrite),
            ("T2 op=structural_selection", op2=="structural_selection"),
            ("T2 re-shows selected subset", t2_reshow),
            ("T2 gives ONE rewrite operation", t2_rewrite),
            ("T2 tells not to add new", t2_nonew),
            ("T2 stop + resubmit", t2_stop)]:
    print(f"  {'PASS' if v else 'FAIL'}  {n}")
allpass = all([op1=="structural_selection",t1_diag,t1_thesis,t1_list,t1_choose,t1_no_rewrite,
               op2=="structural_selection",t2_reshow,t2_rewrite,t2_nonew,t2_stop])
print("\nRESULT:", "PASS" if allpass else "REVIEW")
print("DONE")
