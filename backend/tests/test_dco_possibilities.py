import os, sys, json, time, requests

BASE = os.environ.get("REACT_APP_BACKEND_URL")
if not BASE:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE = line.strip().split("=", 1)[1]
API = f"{BASE}/api"

def main():
    s = requests.post(f"{API}/sessions", json={
        "assignment": "Write a paragraph arguing whether schools should assign less homework.",
        "pedagogical_purpose": "Develop the learner's ability to organize an argument for a reader.",
        "current_writing_task": "One paragraph.",
        "assignment_prompt": "Should schools assign less homework?",
    }, timeout=30)
    s.raise_for_status()
    sid = s.json()["id"]
    print("session", sid)

    draft = ("Schools should give less homework. Homework takes up too much time. "
             "Students get stressed and tired. They cannot do other things they enjoy. "
             "So homework is bad and schools should reduce it.")
    r = requests.post(f"{API}/sessions/{sid}/interact",
                      json={"content": draft, "kind": "writing"}, timeout=30)
    r.raise_for_status()
    print("interact returned, polling for completion...")

    dco = None
    for i in range(60):
        time.sleep(4)
        tr = requests.get(f"{API}/dev/functional-v3-trace/{sid}", timeout=30)
        if tr.status_code != 200:
            continue
        trace = tr.json().get("trace", [])
        if trace and trace[-1].get("developmental_cognition"):
            dco = trace[-1]["developmental_cognition"]
            break
    if not dco:
        print("FAIL: no DCO recorded after polling")
        sys.exit(1)

    print("\n=== DCO KEYS ===")
    print(list(dco.keys()))
    dp = dco.get("developmental_possibilities")
    print("\n=== developmental_possibilities ===")
    print(json.dumps(dp, indent=2))
    print("\n=== instructional_horizon ===")
    print(dco.get("instructional_horizon"))
    print("\n=== confidence[developmental_possibilities] ===", (dco.get("confidence") or {}).get("developmental_possibilities"))
    print("=== evidence[developmental_possibilities] ===")
    print(json.dumps((dco.get("evidence") or {}).get("developmental_possibilities"), indent=2))

    ok = True
    if "developmental_possibilities" not in dco:
        print("FAIL: field missing"); ok = False
    if not isinstance(dp, list) or len(dp) < 2:
        print("FAIL: developmental_possibilities is not a plural list"); ok = False
    if not (dco.get("confidence") or {}).get("developmental_possibilities"):
        print("WARN: no confidence for developmental_possibilities")
    keys = list(dco.keys())
    if "developmental_constraint" in keys and "instructional_horizon" in keys and "developmental_possibilities" in keys:
        ci, di, hi = keys.index("developmental_constraint"), keys.index("developmental_possibilities"), keys.index("instructional_horizon")
        print(f"\norder: constraint={ci} possibilities={di} horizon={hi}")
        if not (ci < di < hi):
            print("WARN: field order not constraint<possibilities<horizon (JSON key order is not guaranteed)")
    print("\nRESULT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
