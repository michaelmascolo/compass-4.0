"""Capture evidence-focused interactions across 3 scenarios (before/after enrichment)."""
import os, sys, time, json, requests

BASE = os.environ.get("BASE", "http://localhost:8001") + "/api"
ASG = BASE + "/assignment"
MODE = sys.argv[1] if len(sys.argv) > 1 else "before"
OUT = "/app/test_reports/evidence_enrichment_validation.json"

SCENARIOS = {
    "S1_weak_credibility": {
        "assignment": "Argue whether homework should be assigned in elementary schools.",
        "draft": ("Homework should not be assigned in elementary schools because it causes stress without improving "
                  "learning. As evidence, a random blog post I found online says homework is bad, and lots of kids "
                  "I know don't like doing it."),
    },
    "S2_relevance_mismatch": {
        "assignment": "Argue that the New Deal significantly reduced unemployment in the 1930s.",
        "draft": ("The New Deal significantly reduced unemployment in the 1930s, primarily through direct federal "
                  "job-creation programs like the WPA and CCC. As evidence, the stock market crashed in 1929 and "
                  "thousands of banks failed, which shows the country was in a severe economic depression."),
    },
    "S3_insufficient_anecdote": {
        "assignment": "Argue whether heavy social media use is associated with anxiety in teenagers.",
        "draft": ("Heavy daily social media use is associated with increased anxiety among many teenagers, largely "
                  "because it fuels constant social comparison. As proof, my friend felt anxious after scrolling "
                  "Instagram one night."),
    },
}


def poll(sid, timeout=200):
    t0 = time.time()
    while time.time() - t0 < timeout:
        s = requests.get(f"{BASE}/sessions/{sid}", timeout=30).json()
        ai = [t for t in s.get("turns", []) if t["role"] == "ai"]
        if ai and ai[-1]["status"] in ("complete", "failed"):
            return s, ai[-1]
        time.sleep(4)
    return requests.get(f"{BASE}/sessions/{sid}", timeout=30).json(), None


try:
    data = json.load(open(OUT))
except Exception:
    data = {}
data.setdefault(MODE, {})

for name, sc in SCENARIOS.items():
    rid = requests.post(f"{ASG}/sessions", json={"assignment_text": sc["assignment"]}, timeout=120).json()["id"]
    res = requests.post(f"{BASE}/sessions/from-representation",
                        json={"assignment_session_id": rid, "existing_draft": sc["draft"]}, timeout=200).json()
    sid = res["session_id"]
    s, ai = poll(sid)
    th = (s.get("theory") or {})
    scf = th.get("scaffolding_control", {})
    ir = th.get("instructional_reasoning", {})
    rec = {
        "first_invitation": (ai.get("content") if ai else ""),
        "primary_target": scf.get("primary_target"),
        "instructional_mode": scf.get("instructional_mode"),
        "active_instructional_element": ir.get("active_instructional_element"),
        "primary_developmental_tension": ir.get("primary_developmental_tension"),
        "next_student_act": ir.get("next_student_act"),
        "selected_io": res.get("suggested_component", {}).get("kb", {}).get("element"),
    }
    data[MODE][name] = rec
    json.dump(data, open(OUT, "w"), indent=2)
    print(f"\n### [{MODE}] {name} | element={rec['active_instructional_element']} | target={rec['primary_target']}")
    print("tension:", rec["primary_developmental_tension"])
    print("invitation:", (rec["first_invitation"] or "")[:520])

print("\nsaved ->", OUT)
