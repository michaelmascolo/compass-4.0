"""Live 2-turn revise test for the 'Development Through Emerging Communicative Constraints'
constitutional rule (functional_v3 only). Validates:
  - selector emits emerging_constraints on the revision turn (turn 2)
  - continuation dialogue narrates the transition (why the next task emerged from the revision)
Runs against localhost:8001 to avoid the ingress SSE ceiling.
"""
import json
import time
import requests

BASE = "http://localhost:8001/api"

DRAFT_1 = (
    "Being on time matters. When you are late you make other people wait for you."
)
DRAFT_2 = (
    "Being on time is a way of showing people respect. When you are late you make other "
    "people wait for you, and that tells them their time is worth less than yours. Showing up "
    "on time quietly says the opposite: that you value the other person."
)


TRACE = "/app/backend/functional_v3_trace.log"


def _poll(session_id, want_ai=1, timeout=220):
    t0 = time.time()
    while time.time() - t0 < timeout:
        r = requests.get(f"{BASE}/sessions/{session_id}")
        r.raise_for_status()
        s = r.json()
        ai = [t for t in s.get("turns", []) if t.get("role") == "ai"]
        if len(ai) >= want_ai:
            last = ai[-1]
            if last.get("status") in ("complete", None) and last.get("content"):
                return s
            if last.get("status") == "failed":
                raise RuntimeError(f"AI turn failed: {last}")
        time.sleep(2.5)
    raise TimeoutError("polling timed out")


def _last_trace(session_id):
    recs = []
    with open(TRACE) as f:
        for line in f:
            i = line.find("{")
            if i < 0:
                continue
            try:
                r = json.loads(line[i:])
            except Exception:
                continue
            if r.get("session_id") == session_id:
                recs.append(r)
    return recs


def main():
    create = requests.post(f"{BASE}/sessions", json={
        "assignment": "Write one paragraph explaining an idea you believe about everyday life.",
        "pedagogical_purpose": "Develop the writer's ability to unfold a thesis for a reader.",
        "current_writing_task": "one paragraph",
    })
    create.raise_for_status()
    sid = create.json()["id"]
    print("session:", sid)

    # Turn 1 — first draft
    requests.post(f"{BASE}/sessions/{sid}/interact", json={"content": DRAFT_1, "kind": "writing"}).raise_for_status()
    s = _poll(sid, want_ai=1)
    ai1 = [t for t in s["turns"] if t.get("role") == "ai"][-1]
    print("\n=== TURN 1 (first) invitation ===\n", ai1["content"][:900])

    # Turn 2 — revise (compare against draft 1)
    requests.post(f"{BASE}/sessions/{sid}/interact", json={"content": DRAFT_2, "kind": "revise"}).raise_for_status()
    s = _poll(sid, want_ai=2)
    ai2 = [t for t in s["turns"] if t.get("role") == "ai"][-1]
    print("\n=== TURN 2 (revise) invitation ===\n", ai2["content"])

    recs = _last_trace(sid)
    fd2 = (recs[-1].get("functional_decision") or {}) if recs else {}
    ec = fd2.get("emerging_constraints") or {}
    print("\nturn2 continuity_decision:", fd2.get("continuity_decision"))
    print("turn2 emerging_constraints:\n", json.dumps(ec, indent=2, ensure_ascii=False))

    # assertions
    assert fd2.get("continuity_decision") in ("hold", "advance", "recurse", "complete"), "no continuity decision"
    has_ec = any((ec.get(k) or "").strip() for k in ("relations_strengthened", "new_constraint", "why_focus_shifted"))
    print("\nRESULT: emerging_constraints populated on revision turn:", has_ec)
    assert has_ec, "emerging_constraints not populated on revision turn"
    print("PASS")


if __name__ == "__main__":
    main()
