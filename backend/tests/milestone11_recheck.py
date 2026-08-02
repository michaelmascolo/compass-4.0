"""Re-verify M11 stopping-rule fix: independence request (22) + repeated-revision diminishing returns (28, 29)."""
import json
import time
import requests

BASE = "http://localhost:8001/api"
ARG = "Argue whether social media improves or harms teen friendships."
REF = "Reflect on what an experience taught you."
PA = "Help the student develop as a writer, one focused step at a time."
TASK = "Work on your draft."

CASES = [
 (22, "requests_independence", REF, ("Got it, that makes sense. Let me take it from here and keep writing myself.",)),
 (28, "repeated_revision", ARG, ("Social media is bad for friends.",
                                "Social media harms close friendships because constant contact removes the absences that made return meaningful.",
                                "Social media harms close friendships because constant contact removes the absences that made return meaningful — when no one is ever gone, no one is quite missed.")),
 (29, "repeated_revision", REF, ("The trip changed me.",
                                "The trip changed how I saw home.",
                                "Leaving finally taught me what home had meant — not a place I lived, but the people who expected me back.")),
]


def create_session(a, p, t):
    r = requests.post(f"{BASE}/sessions", json={"assignment": a, "pedagogical_purpose": p, "current_writing_task": t, "teacher_notes": ""}, timeout=30)
    r.raise_for_status()
    return r.json()["id"]


def interact(sid, kind, content):
    r = requests.post(f"{BASE}/sessions/{sid}/interact", json={"kind": kind, "content": content}, stream=True, timeout=180)
    r.raise_for_status()
    session, err, buf = None, None, ""
    for chunk in r.iter_content(chunk_size=None, decode_unicode=True):
        if not chunk:
            continue
        buf += chunk
        while "\n\n" in buf:
            raw, buf = buf.split("\n\n", 1)
            ev, data = "message", ""
            for line in raw.split("\n"):
                if line.startswith(":"):
                    continue
                if line.startswith("event:"):
                    ev = line[6:].strip()
                elif line.startswith("data:"):
                    data += line[5:].strip()
            if ev == "done" and data:
                session = json.loads(data)
            elif ev == "error" and data:
                err = json.loads(data).get("detail")
    if err:
        raise RuntimeError(err)
    return session


def main():
    for (n, cat, assignment, turns) in CASES:
        sid = create_session(assignment, PA, TASK)
        last = None
        for i, c in enumerate(turns):
            last = interact(sid, "writing" if i == 0 else "revise", c)
        sc = last["theory"].get("scaffolding_control", {}) or {}
        ok = sc.get("cycle_status") in {"stop", "consolidate_and_return"} or last["interactions"][-1]["intervention"]["type"] == "consolidate"
        print(f"case {n} [{cat}] status={sc.get('cycle_status')} reason='{(sc.get('stopping_reason') or '')[:40]}' iv={last['interactions'][-1]['intervention']['type']} ok={ok}", flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
