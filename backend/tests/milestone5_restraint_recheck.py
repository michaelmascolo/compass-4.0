"""Re-check restraint fix on advanced students (cases 10, 27) + capable controls (6,7,30).
Expect NO over-instruction: invite_only / interpretation_only preferred over instruct_then_invite."""
import json
import time
import requests

BASE = "http://localhost:8001/api"
TH = "Help the student form and clarify a central claim that organizes the essay."
OP = "Write an introduction that draws a reader in and frames why the issue matters."
A_ARG = "Argue whether social media improves or harms teen friendships."

CASES = [
 (10, "already_understands", TH, "Draft your thesis.",
  "The problem is not screen time but attention: social media harms teen friendship precisely when it replaces undivided attention with performed presence."),
 (27, "needs_less", TH, "Draft your thesis.",
  "Social media doesn't destroy friendship; it exposes how fragile some friendships were to begin with."),
 (6, "already_understands", OP, "Draft your introduction.",
  "Picture a sixteen-year-old with 800 online 'friends' who eats lunch alone every day. That contradiction is where this essay begins, because it exposes what we really mean when we call an app 'social.'"),
 (7, "already_understands", TH, "Draft your thesis.",
  "Social media strengthens weak-tie friendships while quietly eroding the close ones, because it rewards breadth of contact over depth of attention."),
 (30, "needs_less", TH, "Draft your thesis.",
  "The closer a friendship is, the less social media seems to help it — and that inverse relationship is what this essay sets out to explain."),
]
OK = {"invite_only", "interpretation_only", "postpone_instruction"}


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
    out = []
    for (n, profile, purpose, task, text) in CASES:
        t0 = time.time()
        try:
            sid = create_session(A_ARG, purpose, task)
            s = interact(sid, "writing", text)
            iv = s["interactions"][-1]["intervention"]
            rec = {"n": n, "profile": profile, "type": iv["type"],
                   "instruction_len": len(iv["instruction"].strip()),
                   "student_facing": s["turns"][-1]["content"],
                   "ok_restraint": iv["type"] in OK, "elapsed_s": round(time.time() - t0, 1)}
            print(f"case {n} [{profile}] type={rec['type']} ok={rec['ok_restraint']} instr={rec['instruction_len']} {rec['elapsed_s']}s", flush=True)
            out.append(rec)
        except Exception as e:  # noqa: BLE001
            print(f"case {n} FAILED: {e}", flush=True)
            out.append({"n": n, "error": str(e)})
        json.dump(out, open("/app/backend/tests/milestone5_restraint_results.json", "w"), indent=2)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
