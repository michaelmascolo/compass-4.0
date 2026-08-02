"""Capture introduction-focused interactions across 3 scenarios (before/after enrichment)."""
import os, sys, time, json, requests

BASE = os.environ.get("BASE", "http://localhost:8001") + "/api"
ASG = BASE + "/assignment"
MODE = sys.argv[1] if len(sys.argv) > 1 else "before"
OUT = "/app/test_reports/introduction_enrichment_validation.json"

SCENARIOS = {
    # Solid contestable thesis, but the HOOK is disconnected/decorative.
    "S1_hook_disconnected": {
        "assignment": "Write an essay arguing whether cities should invest in public transit.",
        "draft": ("Dinosaurs once ruled the Earth for millions of years before suddenly going extinct. Cities should "
                  "invest heavily in public transit, because it reduces congestion, cuts carbon emissions, and expands "
                  "economic access for low-income residents who cannot afford cars."),
    },
    # Specific causal thesis present, but NO reader orientation — plunges in with no context/stakes.
    "S2_no_reader_orientation": {
        "assignment": "Write an essay explaining the causes of the French Revolution.",
        "draft": ("The French Revolution happened mainly because of a fiscal crisis, Enlightenment ideas, and a rigid "
                  "social hierarchy. The fiscal crisis was the deepest cause because it forced the king to call the "
                  "Estates-General, which set everything else in motion."),
    },
    # Controlling idea IS present but BURIED after undirected background with no motivation.
    "S3_background_buried_thesis": {
        "assignment": "Write an essay analyzing how setting shapes mood in a novel of your choice.",
        "draft": ("The Great Gatsby is set on Long Island in the 1920s. There is a place called West Egg and a place "
                  "called East Egg. There is also the Valley of Ashes. Fitzgerald describes these places in a lot of "
                  "detail throughout the book. Setting is important. Fitzgerald uses the decaying Valley of Ashes and "
                  "the glittering mansion parties to build a mood of hollow excess beneath the surface glamour."),
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
