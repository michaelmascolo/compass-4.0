"""Capture explanation-focused interactions across 3 scenarios (before/after enrichment)."""
import os, sys, time, json, requests

BASE = os.environ.get("BASE", "http://localhost:8001") + "/api"
ASG = BASE + "/assignment"
MODE = sys.argv[1] if len(sys.argv) > 1 else "before"
OUT = "/app/test_reports/explanation_enrichment_validation.json"

SCENARIOS = {
    # Evidence is relevant+present; the gap is INTERPRETATION. Looks like "no explanation".
    "S1_no_explanation": {
        "assignment": "Analyze how Lady Macbeth's language reveals her ambition in Act 1.",
        "draft": ("Lady Macbeth is deeply ambitious. In Act 1 she says, \"unsex me here, / And fill me from the crown "
                  "to the toe top-full / Of direst cruelty.\" This shows she is very ambitious."),
    },
    # Explanation RESTATES the evidence rather than reasoning about it.
    "S2_restatement_not_reasoning": {
        "assignment": "Explain why the invention of the printing press accelerated the spread of new ideas in Europe.",
        "draft": ("The printing press accelerated the spread of new ideas. Before the press, books were copied by hand, "
                  "which was slow. The printing press could produce many books quickly. So the printing press meant "
                  "books could be produced quickly and in large numbers."),
    },
    # Unsupported CAUSAL claim / missing warrant: asserts a cause-effect link without the reasoning connecting them.
    "S3_missing_warrant_causal": {
        "assignment": "Argue whether standardized testing improves student learning.",
        "draft": ("Standardized testing improves student learning. Schools that use frequent standardized tests report "
                  "higher average test scores. Therefore standardized testing makes students learn more."),
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
    }
    data[MODE][name] = rec
    json.dump(data, open(OUT, "w"), indent=2)
    print(f"\n### [{MODE}] {name} | element={rec['active_instructional_element']} | target={rec['primary_target']}")
    print("tension:", rec["primary_developmental_tension"])
    print("invitation:", (rec["first_invitation"] or "")[:520])

print("\nsaved ->", OUT)
