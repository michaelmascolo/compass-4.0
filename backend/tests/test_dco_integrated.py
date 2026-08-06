import sys, json, time, requests

with open("/app/frontend/.env") as f:
    for line in f:
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE = line.strip().split("=", 1)[1]
API = f"{BASE}/api"

s = requests.post(f"{API}/sessions", json={
    "assignment": "What does it mean to separate interests from positions in conflict resolution?",
    "pedagogical_purpose": "Develop the learner's ability to explain a conceptual distinction for a reader.",
    "current_writing_task": "One paragraph.",
    "assignment_prompt": "What does it mean to separate interests from positions in conflict resolution?",
    "reasoning_mode": "canonical_v2",
}, timeout=30)
s.raise_for_status()
sid = s.json()["id"]
print("SESSION", sid)
draft = ("Focusing on interests instead of positions can really help in a conflict. "
         "When people only argue about their positions, they often get stuck and the "
         "relationship gets damaged. But if you focus on interests, negotiation goes better "
         "and you are more likely to reach an agreement everyone is happy with.")
requests.post(f"{API}/sessions/{sid}/interact", json={"content": draft, "kind": "writing"}, timeout=30).raise_for_status()
dco = None
for i in range(70):
    time.sleep(4)
    tr = requests.get(f"{API}/dev/functional-v3-trace/{sid}", timeout=30)
    if tr.status_code == 200:
        trace = tr.json().get("trace", [])
        if trace and trace[-1].get("developmental_cognition", {}).get("integrated_instructional_problem_space"):
            dco = trace[-1]["developmental_cognition"]; break
if not dco:
    print("FAIL: no DCO with integrated fields"); sys.exit(1)

new_fields = ["content_relations_and_dependencies","structural_relations_and_dependencies",
              "task_required_content_relations","task_required_structural_relations",
              "whole_communication_requirements","provisional_whole_communication",
              "integrated_instructional_problem_space","instructional_center",
              "local_instruction_constraints","current_instructional_sufficiency"]
for k in new_fields:
    print(f"\n=== {k} ===")
    print(json.dumps(dco.get(k), indent=2, ensure_ascii=False))
conf = dco.get("confidence") or {}
ev = dco.get("evidence") or {}
# confidence/evidence scoped to the calibration-critical set (reliable LLM compliance)
meta_set = ["content_relations_and_dependencies","structural_relations_and_dependencies",
            "whole_communication_requirements","provisional_whole_communication",
            "integrated_instructional_problem_space","instructional_center",
            "current_instructional_sufficiency","coordinative_capacity","developmental_constraint"]
mc = [k for k in meta_set if k not in conf]
me = [k for k in meta_set if k not in ev]
present = [k for k in new_fields if k in dco]
print("\npresent:", present)
print("confidence keys count:", len(conf), "evidence keys count:", len(ev))
print("missing confidence (meta set):", mc)
print("missing evidence (meta set):", me)
# required_relations should be gone
print("old required_relations still present:", "required_relations" in dco)
lo = dco.get("learner_orientation")
print("\n=== learner_orientation ===")
print(json.dumps(lo, indent=2, ensure_ascii=False))
lo_ok = isinstance(lo, dict) and all(k in lo for k in
    ["current_direction","where_we_are","current_work","likely_next_step","estimated_remaining_moves"])
valid_est = {"probably one more step","probably one or two more steps","several steps remain","not yet estimable"}
est_ok = isinstance(lo, dict) and lo.get("estimated_remaining_moves") in valid_est
print("learner_orientation complete:", lo_ok, "| estimated_remaining_moves valid:", est_ok)
ok = all(k in dco for k in new_fields) and not mc and not me and lo_ok and est_ok
print("\nRESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
