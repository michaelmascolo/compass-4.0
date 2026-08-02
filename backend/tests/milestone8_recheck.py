"""Re-verify M8 applies-recognition fix on embedded process/experiential support (cases 11, 22).
Expect applies=True; also re-check case 30 brainstorm stays boundary-safe (no rigid rules)."""
import json
import re
import time
import requests

BASE = "http://localhost:8001/api"
EXPL = "Explain how a chosen process or phenomenon works."
REF = "Reflect on what an experience taught you."
ARG = "Argue whether social media improves or harms teen friendships."
PA = "Help the student use evidence and support to serve the essay's purpose."
TASK = "Draft a body paragraph."

RULE = [re.compile(p, re.IGNORECASE) for p in [r"add more evidence", r"need (?:more|another|additional) (?:evidence|examples?|sources?)", r"(?:at least|use|include) (?:two|three|3|2|several|multiple) (?:sources?|examples?|quotes?)"]]

CASES = [
 (11, EXPL, "When you flip the switch, current flows through the filament, which heats until it glows. The glowing filament is what produces the light you see.", ""),
 (22, REF, "The scar on my thumb reminds me of the summer I learned that fixing things and breaking them use the same tools.", ""),
 (30, ARG, "I want to support my claim that social media weakens close friendships but I don't know what kind of evidence would work.", "Brainstorming mode is ON: help the student generate possible kinds of evidence and support before drafting."),
]


def create_session(a, p, t, notes=""):
    r = requests.post(f"{BASE}/sessions", json={"assignment": a, "pedagogical_purpose": p, "current_writing_task": t, "teacher_notes": notes}, timeout=30)
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
    for (n, assignment, draft, notes) in CASES:
        t0 = time.time()
        sid = create_session(assignment, PA, TASK, notes)
        s = interact(sid, "writing", draft)
        ef = s["theory"].get("evidence_function", {}) or {}
        sf = s["turns"][-1]["content"]
        rf = [p.pattern for p in RULE if p.search(sf)]
        print(f"case {n} applies={bool(ef.get('applies'))} fn='{(ef.get('function') or '')[:45]}' rule_flags={rf} {round(time.time()-t0,1)}s", flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
