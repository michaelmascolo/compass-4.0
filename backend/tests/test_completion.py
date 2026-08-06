import sys, json, time, requests
with open("/app/frontend/.env") as f:
    for line in f:
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE = line.strip().split("=", 1)[1]
API = f"{BASE}/api"
s = requests.post(f"{API}/sessions", json={
    "assignment": "Explain what a growth mindset is and how it shapes how students respond to failure.",
    "pedagogical_purpose": "Define and explain a concept for a reader.",
    "current_writing_task": "One paragraph.",
    "assignment_prompt": "What is a growth mindset and how does it shape how students respond to failure?",
    "reasoning_mode": "canonical_v2",
}, timeout=30)
s.raise_for_status(); sid = s.json()["id"]; print("SESSION", sid)
# A fairly complete, coherent paragraph (to push completion toward ready/nearly_ready)
draft = ("A growth mindset is the belief that a person's abilities can develop through effort, practice, and learning, "
         "rather than being fixed traits. This belief changes how students interpret failure: instead of seeing a poor "
         "result as proof that they lack ability, a student with a growth mindset reads it as information about what they "
         "have not yet learned. Because the failure signals a gap rather than a limit, the student responds by trying "
         "again and adjusting their approach. In this way, a growth mindset turns setbacks into opportunities for "
         "learning, which is exactly why it strengthens how students respond to failure.")
requests.post(f"{API}/sessions/{sid}/interact", json={"content": draft, "kind": "writing"}, timeout=30).raise_for_status()
cr = None
for i in range(70):
    time.sleep(4)
    tr = requests.get(f"{API}/dev/functional-v3-trace/{sid}", timeout=30)
    if tr.status_code == 200:
        t = tr.json().get("trace", [])
        if t and t[-1].get("developmental_cognition", {}).get("completion_readiness"):
            dco = t[-1]["developmental_cognition"]; cr = dco["completion_readiness"]; break
if not cr:
    print("FAIL: no completion_readiness"); sys.exit(1)
print("\n=== completion_readiness ==="); print(json.dumps(cr, indent=2, ensure_ascii=False))
print("\n=== completion_message ==="); print(json.dumps(dco.get("completion_message"), indent=2, ensure_ascii=False))
ok = isinstance(cr, dict) and cr.get("value") in {"not_ready","nearly_ready","ready","uncertain"} and cr.get("reason")
print("\nRESULT:", "PASS" if ok else "FAIL"); sys.exit(0 if ok else 1)
