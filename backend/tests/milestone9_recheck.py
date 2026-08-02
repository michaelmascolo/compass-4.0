"""Re-verify M9 applies-recognition fix on strong-flow paragraphs (cases 1, 21)."""
import json
import time
import requests

BASE = "http://localhost:8001/api"
ARG = "Argue whether social media improves or harms teen friendships."
ANL = "Analyze how a text or space produces its effect."
PA = "Help the student create coherence and communicate relationships among ideas clearly."
TASK = "Draft this section of your writing."

CASES = [
 (1, ARG, "Constant availability removes the small absences that used to make return meaningful. When no one is ever gone, no one is ever quite missed. The friendship stays lit but stops being felt."),
 (21, ANL, "The film cuts faster as the argument escalates. The quickening rhythm makes the audience feel the loss of control the characters describe."),
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
    for (n, assignment, draft) in CASES:
        t0 = time.time()
        sid = create_session(assignment, PA, TASK)
        s = interact(sid, "writing", draft)
        cf = s["theory"].get("coherence_function", {}) or {}
        print(f"case {n} applies={bool(cf.get('applies'))} rel='{(cf.get('intended_relationship') or '')[:45]}' focus={s['interactions'][-1]['intervention'].get('focus')} {round(time.time()-t0,1)}s", flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
