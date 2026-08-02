"""Capture a thesis-focused instructional interaction (before/after enrichment)."""
import os, sys, time, json, requests

BASE = os.environ.get("BASE", "http://localhost:8001") + "/api"
ASG = BASE + "/assignment"
MODE = sys.argv[1] if len(sys.argv) > 1 else "before"
OUT = "/app/test_reports/thesis_enrichment_validation.json"

PROMPT = "Write an essay explaining the most important cause of the fall of the Roman Empire."
DRAFT = ("The fall of the Roman Empire. There were many reasons the Roman Empire fell. "
         "It was a very big empire and it lasted a long time and then it fell. This essay is about that.")


def poll(sid, timeout=200):
    t0 = time.time()
    while time.time() - t0 < timeout:
        s = requests.get(f"{BASE}/sessions/{sid}", timeout=30).json()
        ai = [t for t in s.get("turns", []) if t["role"] == "ai"]
        if ai and ai[-1]["status"] in ("complete", "failed"):
            return s, ai[-1]
        time.sleep(4)
    return requests.get(f"{BASE}/sessions/{sid}", timeout=30).json(), None


rid = requests.post(f"{ASG}/sessions", json={"assignment_text": PROMPT}, timeout=120).json()["id"]
res = requests.post(f"{BASE}/sessions/from-representation",
                    json={"assignment_session_id": rid, "existing_draft": DRAFT}, timeout=200).json()
sid = res["session_id"]
s, ai = poll(sid)
# one revision to see a second cycle
requests.post(f"{BASE}/sessions/{sid}/interact",
              json={"content": "The most important cause was that Rome got too big to manage.", "kind": "revise"}, timeout=30)
s, ai2 = poll(sid)

sc = (s.get("theory") or {}).get("scaffolding_control", {})
ir = (s.get("theory") or {}).get("instructional_reasoning", {})
record = {
    "mode": MODE,
    "assignment": PROMPT,
    "first_invitation": (ai.get("content") if ai else ""),
    "second_invitation": (ai2.get("content") if ai2 else ""),
    "primary_target": sc.get("primary_target"),
    "prioritization_rationale": sc.get("prioritization_rationale"),
    "instructional_mode": sc.get("instructional_mode"),
    "active_instructional_element": ir.get("active_instructional_element"),
    "primary_developmental_tension": ir.get("primary_developmental_tension"),
    "next_student_act": ir.get("next_student_act"),
    "degree_of_student_control": ir.get("degree_of_student_control"),
}
try:
    data = json.load(open(OUT))
except Exception:
    data = {}
data[MODE] = record
json.dump(data, open(OUT, "w"), indent=2)
print(json.dumps(record, indent=2)[:2000])
print("\nsaved ->", OUT)
