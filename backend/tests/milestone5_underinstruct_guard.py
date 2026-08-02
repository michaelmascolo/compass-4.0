"""Guard: ensure restraint change did NOT suppress instruction where it's needed.
Expect instruct_then_invite for genuine needs_instruction / misuses / rigid_formula cases."""
import json
import time
import requests

BASE = "http://localhost:8001/api"
TH = "Help the student form and clarify a central claim that organizes the essay."
PA = "Help the student clarify what each paragraph is doing for the essay."
A_ARG = "Argue whether social media improves or harms teen friendships."

CASES = [
 (2, "needs_instruction", TH, "Draft your thesis.", "My essay is about social media and friendship."),
 (12, "misuses", TH, "Draft your thesis.", "Social media is very popular and important and everyone uses it a lot these days."),
 (22, "rigid_formula", TH, "Draft your thesis.", "Social media harms teen friendships because it is distracting, because it is fake, and because it is addictive."),
 (23, "rigid_formula", PA, "Draft a body paragraph.", "Topic sentence: Social media is distracting. Evidence: Teens check phones 100 times a day. Analysis: This shows it is distracting. Concluding sentence: Therefore social media is distracting."),
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
    out = []
    for (n, profile, purpose, task, text) in CASES:
        t0 = time.time()
        try:
            sid = create_session(A_ARG, purpose, task)
            s = interact(sid, "writing", text)
            iv = s["interactions"][-1]["intervention"]
            ok = iv["type"] in {"instruct_then_invite", "interpretation_only"}
            rec = {"n": n, "profile": profile, "type": iv["type"], "ok": ok, "elapsed_s": round(time.time() - t0, 1)}
            print(f"case {n} [{profile}] type={rec['type']} ok={ok} {rec['elapsed_s']}s", flush=True)
            out.append(rec)
        except Exception as e:  # noqa: BLE001
            print(f"case {n} FAILED: {e}", flush=True)
            out.append({"n": n, "error": str(e)})
        json.dump(out, open("/app/backend/tests/milestone5_guard_results.json", "w"), indent=2)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
