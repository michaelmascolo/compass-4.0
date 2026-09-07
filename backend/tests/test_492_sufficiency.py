"""Compass 4.9.2 acceptance (1 case, per cost rule): the exact multi-trajectory sprawling AI paragraph.
Expected: adequate + conceptual sufficiency recognized; paragraph OVERLOAD recognized; NO new elaboration;
NO counterargument suggestion; instructional_operation = structural_selection; coaching explicitly says the
paragraph is carrying too much structural work; scaffolds keep/combine/condense/move/remove; Sentence Craft
identified as what follows structural reduction."""
import time, json, requests

API = "http://localhost:8001/api"

# Matches the user's enumerated structural work: survey of teacher responses, critique, central solution,
# Compass example, ChatGPT affordance contrast, learning loop, ZPD-like calibrated challenge, effectance.
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


def create():
    return requests.post(f"{API}/sessions/preview", json={"assignment": "What should we do about AI in education?", "canonical": True}, timeout=30).json()["id"]

sid = create(); print("SESSION", sid)
requests.post(f"{API}/sessions/{sid}/interact", json={"content": SPRAWL, "kind": "writing"}, timeout=30)

turn = None
deadline = time.time() + 700
while time.time() < deadline:
    time.sleep(5)
    r = requests.get(f"{API}/sessions/{sid}", timeout=30).json()
    ai = [t for t in r.get("turns", []) if t["role"] == "ai" and t.get("status") == "complete" and t.get("content")]
    if any(t["role"] == "ai" and t.get("status") == "failed" for t in r.get("turns", [])):
        print("FAILED"); break
    if ai:
        turn = ai[-1]; break

tr = requests.get(f"{API}/dev/functional-v3-trace/{sid}", timeout=30).json().get("trace", [])
dco = (tr[-1].get("developmental_cognition") or {}) if tr else {}
s = dco.get("structural_load_analysis") or {}
ec = dco.get("episode_closure") or {}
tra = dco.get("task_relative_adequacy") or {}
lrs = dco.get("learner_relative_sufficiency") or {}
coach = (turn or {}).get("content") or ""
op = (turn or {}).get("instructional_operation")

print("\n=== DCO ===")
print("task adequacy:", tra.get("value"), "| sufficiency:", lrs.get("value"), "| achieved:", lrs.get("accessible_target_achieved"))
print("structural_load_status:", s.get("structural_load_status"), "| pruning:", s.get("structural_pruning_needed"))
print("secondary_trajectories:", json.dumps(s.get("secondary_trajectories"))[:200])
print("competing_structural_work:", json.dumps(s.get("competing_structural_work"))[:160])
print(">> instructional_operation:", op, "| closure:", ec.get("episode_closure_decision"))
print("\n=== COACHING ===\n", coach)

low = coach.lower()
overload_lang = any(w in low for w in ["carrying more", "more work than", "too much", "more than it can",
                                       "carry more", "carrying the same", "same job", "organize clearly",
                                       "than it can organize", "crowded", "carrying too much"])
scaffold = any(w in low for w in ["combine", "condense", "move", "remove", "belongs in another", "stay",
                                  "keep", "which version", "shorten"])
no_counter = not any(w in low for w in ["counterargument", "counter-argument", "objection", "opposing view",
                                        "other side", "rebuttal"])
sentence_next = any(w in low for w in ["sentence by sentence", "sentence-by-sentence", "work on it sentence",
                                       "strengthening it sentence", "word by word"])

print("\n=== ACCEPTANCE ===")
print("adequate:", (tra.get("value") or "").lower() == "adequate")
print("conceptual sufficiency recognized:", (lrs.get("value") or "").lower() in ("sufficient", "approaching_sufficiency"))
print("overload recognized (status):", (s.get("structural_load_status") or "").lower() in ("crowded", "overloaded"))
print("instructional_operation == structural_selection:", op == "structural_selection")
print("coaching says paragraph carries too much:", overload_lang)
print("coaching scaffolds keep/combine/condense/move/remove:", scaffold)
print("NO counterargument suggestion:", no_counter)
print("Sentence Craft identified as next:", sentence_next)
print("\nPASS:", op == "structural_selection" and overload_lang and scaffold and no_counter and sentence_next)
print("DONE")
