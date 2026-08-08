"""4.6 calibration A (AI-in-education) + C (phones): contract stays on the pinned relation,
no expert-level demands, goal FIXED across turns."""
import time, json, requests
with open("/app/frontend/.env") as f:
    for line in f:
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE = line.strip().split("=", 1)[1]
API = f"{BASE}/api"
CASES = [
    {"id": "A_ai_education", "assignment": "What should we do about AI in education?",
     "purpose": "Develop the learner's ability to state and support a position for a reader.",
     "turns": [
        ("AI in education is a problem because students use it to avoid thinking, and thinking is how "
         "people learn. We should build AI that guides learning instead of doing the work, so students "
         "still do the thinking and stay motivated in a virtuous loop."),
        ("AI in education is a problem because students use it to avoid thinking, and thinking is how "
         "people learn. We should build AI that guides learning instead of doing the work. When a tool "
         "asks questions instead of giving answers, the student still does the effortful thinking, so "
         "they still learn; and because each guided step ends in a small success, they stay motivated "
         "to take the next step — the effort and the motivation keep feeding each other."),
     ]},
    {"id": "C_phones", "assignment": "Should phones be allowed in class?",
     "purpose": "Develop the learner's ability to state a position and give a clear supporting reason.",
     "turns": [
        ("Phones should not be allowed in class because students look at them instead of listening, and "
         "when you are not listening you cannot learn what the teacher is explaining."),
        ("Phones should not be allowed in class because students end up looking at them instead of "
         "listening, and when you are not paying attention you cannot learn what the teacher is "
         "explaining. If phones were kept away during lessons, students would focus and understand more."),
     ]},
]


def wait(sid, n):
    for _ in range(170):
        time.sleep(4)
        r = requests.get(f"{API}/sessions/{sid}", timeout=30).json()
        ai = [t for t in r.get("turns", []) if t["role"] == "ai" and t.get("status") == "complete" and t.get("content")]
        st = [t for t in r.get("turns", []) if t["role"] == "student"]
        if len(st) >= n and len(ai) >= n:
            return ai
    return None


for case in CASES:
    print("\n" + "=" * 70); print("CASE", case["id"]); print("=" * 70)
    s = requests.post(f"{API}/sessions", json={
        "assignment": case["assignment"], "pedagogical_purpose": case["purpose"],
        "current_writing_task": "One paragraph.", "assignment_prompt": case["assignment"],
        "reasoning_mode": "canonical_v2"}, timeout=30)
    sid = s.json()["id"]; print("SESSION", sid)
    goals = []
    for i, d in enumerate(case["turns"], start=1):
        requests.post(f"{API}/sessions/{sid}/interact", json={"content": d, "kind": "writing"}, timeout=30)
        ai = wait(sid, i)
        if not ai:
            print(f"  FAIL turn {i}"); break
        t = ai[-1]; c = t.get("instructional_contract") or {}; al = t.get("contract_alignment") or {}
        goals.append(c.get("goal"))
        print(f"  T{i}: alignment={al.get('alignment')} heuristic={al.get('heuristic_verdict')} "
              f"escalated={al.get('llm_escalated')} regen={al.get('regenerated')} achieved={c.get('achieved')}")
        print(f"      goal={c.get('goal')!r}")
        print(f"      invitation={ (t.get('content') or '')[:150].replace(chr(10),' ') }")
    print(f"  >>> GOAL FIXED across turns: {len(set(g for g in goals if g)) <= 1}")
print("\nDONE")
