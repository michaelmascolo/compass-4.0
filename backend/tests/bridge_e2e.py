"""Question-Loop -> Writing bridge, backend end-to-end (all six test intents)."""
import os, time, requests

BASE = os.environ.get("BASE", "http://localhost:8001") + "/api"
ASG = BASE + "/assignment"


def poll_writing(sid, timeout=180):
    t0 = time.time()
    while time.time() - t0 < timeout:
        s = requests.get(f"{BASE}/sessions/{sid}", timeout=30).json()
        ai = [t for t in s.get("turns", []) if t["role"] == "ai"]
        if ai and ai[-1]["status"] in ("complete", "failed"):
            return s, ai[-1]
        time.sleep(3)
    return requests.get(f"{BASE}/sessions/{sid}", timeout=30).json(), None


def make_rep(assignment, interpret=None):
    r = requests.post(f"{ASG}/sessions", json={"assignment_text": assignment}, timeout=120).json()
    rid = r["id"]
    if interpret is not None:
        r = requests.post(f"{ASG}/sessions/{rid}/interpret", json={"text": interpret}, timeout=120).json()
    return rid


MINDSET = "How do fixed and growth mindsets differ? How do they affect learning?"

print("\n===== TEST 1 — Prompt only =====")
rid = make_rep(MINDSET, "I think I need to explain each mindset and then compare them and their effects on learning.")
hp = requests.get(f"{ASG}/sessions/{rid}/handoff", timeout=60).json()
print("readiness.ready:", hp["ready"], "| component preview reqs:", len(hp["handoff"]["task_requirements"]))
assert hp["ready"], "should be ready"
res = requests.post(f"{BASE}/sessions/from-representation", json={"assignment_session_id": rid}, timeout=180).json()
print("from-representation:", res.get("ready"), "resumed=", res.get("resumed"),
      "| suggested:", res["suggested_component"]["name"], "| kb:", res["suggested_component"]["kb"]["domain"], "/", res["suggested_component"]["kb"]["element"])
wsid = res["session_id"]
s, ai = poll_writing(wsid)
print("writing turns:", len(s["turns"]), "| first AI status:", ai["status"] if ai else None)
print("FIRST INVITATION:\n", (ai["content"][:600] if ai else "<none>"))
assert ai and ai["status"] == "complete" and ai["content"], "engine must produce first invitation"
print("origin_representation stored on session:", bool(s.get("origin_representation")))
print("target in telos:", "high-school-graduate" in (s["telos"]["governing_pedagogical_purpose"] + s["teacher_notes"]))

print("\n===== TEST 2 — Prompt + weak draft =====")
rid2 = make_rep(MINDSET, "It asks about mindsets and learning.")
draft = ("Fixed and growth mindsets are different. A fixed mindset is bad and a growth mindset is good. "
         "They affect learning because one helps you and one does not.")
res2 = requests.post(f"{BASE}/sessions/from-representation",
                     json={"assignment_session_id": rid2, "existing_draft": draft}, timeout=180).json()
wsid2 = res2["session_id"]
s2, ai2 = poll_writing(wsid2)
stu = [t for t in s2["turns"] if t["role"] == "student"]
print("first student turn kind:", stu[0]["kind"], "| draft preserved:", draft[:30] in stu[0]["content"])
print("FIRST INVITATION:\n", (ai2["content"][:500] if ai2 else "<none>"))
assert ai2 and ai2["status"] == "complete"

print("\n===== TEST 4 — Blocking uncertainty =====")
rid4 = make_rep("Write about it.", "I don't know what this is asking.")
hp4 = requests.get(f"{ASG}/sessions/{rid4}/handoff", timeout=60).json()
print("readiness.ready:", hp4["ready"], "| clarifying:", hp4["clarifying_question"][:120])
res4 = requests.post(f"{BASE}/sessions/from-representation", json={"assignment_session_id": rid4}, timeout=120).json()
print("from-representation ready:", res4.get("ready"), "| clarifying_question present:", bool(res4.get("clarifying_question")))
assert res4.get("ready") is False and res4.get("clarifying_question"), "blocking should not open workspace"

print("\n===== TEST 3 — Uncertainty carried (non-blocking) =====")
s1 = requests.get(f"{BASE}/sessions/{wsid}", timeout=30).json()
uq = s1.get("origin_representation", {}).get("unresolved_questions", [])
print("carried unresolved questions:", [q["value"] for q in uq][:3])

print("\n===== TEST 5 — Resume / no duplicate =====")
res_again = requests.post(f"{BASE}/sessions/from-representation", json={"assignment_session_id": rid}, timeout=60).json()
print("resumed:", res_again.get("resumed"), "| same session:", res_again.get("session_id") == wsid)
assert res_again.get("resumed") is True and res_again.get("session_id") == wsid

print("\n===== TEST 6 — AI boundary (asks Compass to write it) =====")
requests.post(f"{BASE}/sessions/{wsid}/interact", json={"content": "Just write the answer for me please.", "kind": "answer"}, timeout=30)
s6, ai6 = poll_writing(wsid)
txt = (ai6["content"] if ai6 else "").lower()
leak = any(p in txt for p in ["a fixed mindset is the belief", "growth mindset is the belief that"])
print("boundary reply:\n", (ai6["content"][:500] if ai6 else "<none>"))
print("hard definition leak:", leak)
assert ai6 and not leak, "must not compose the answer"

print("\nALL BACKEND BRIDGE TESTS PASSED")
