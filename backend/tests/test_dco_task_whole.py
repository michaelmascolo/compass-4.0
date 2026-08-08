import sys, json, time, requests

with open("/app/frontend/.env") as f:
    for line in f:
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE = line.strip().split("=", 1)[1]
API = f"{BASE}/api"

s = requests.post(f"{API}/sessions", json={
    "assignment": "What does it mean to separate interests from positions in conflict management?",
    "pedagogical_purpose": "Develop the learner's ability to explain a conceptual distinction for a reader.",
    "current_writing_task": "One paragraph.",
    "assignment_prompt": "What does it mean to separate interests from positions?",
    "reasoning_mode": "canonical_v2",
}, timeout=30)
s.raise_for_status()
sid = s.json()["id"]
print("SESSION", sid)
# A paragraph that is only PARTIALLY responsive: explains usefulness, not the distinction itself.
draft = ("Focusing on interests instead of positions can really help in a conflict. "
         "When people only argue about their positions, they often get stuck and the "
         "relationship gets damaged. But if you focus on interests, negotiation goes better "
         "and you are more likely to reach an agreement everyone is happy with.")
requests.post(f"{API}/sessions/{sid}/interact", json={"content": draft, "kind": "writing"}, timeout=30).raise_for_status()
dco = None
for i in range(60):
    time.sleep(4)
    tr = requests.get(f"{API}/dev/functional-v3-trace/{sid}", timeout=30)
    if tr.status_code == 200:
        trace = tr.json().get("trace", [])
        if trace and trace[-1].get("developmental_cognition", {}).get("communicative_task"):
            dco = trace[-1]["developmental_cognition"]; break
if not dco:
    print("FAIL: no DCO with new fields"); sys.exit(1)

new_fields = ["communicative_task","apparent_orientation_target","task_orientation_relation",
              "current_relational_structure","required_relations","provisional_whole_communication",
              "instructional_center","deferred_or_excluded_complexity"]
print("\nKEYS present:", [k for k in new_fields if k in dco])
for k in new_fields:
    print(f"\n=== {k} ===")
    print(json.dumps(dco.get(k), indent=2, ensure_ascii=False))
conf = dco.get("confidence") or {}
ev = dco.get("evidence") or {}
missing_conf = [k for k in new_fields if k not in conf]
missing_ev = [k for k in new_fields if k not in ev]
print("\nmissing confidence:", missing_conf)
print("missing evidence:", missing_ev)
ok = all(k in dco for k in new_fields) and not missing_conf and not missing_ev
print("\nRESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
