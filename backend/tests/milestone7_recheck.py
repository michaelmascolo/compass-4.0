"""Re-verify M7 applies-reliability fix: strong/effective paragraphs must set applies=True."""
import json
import time
import requests

BASE = "http://localhost:8001/api"
PA = "Help the student clarify what each paragraph is doing for the essay."
CMP = "Compare two options and help a reader understand the trade-offs."
ARG = "Argue whether social media improves or harms teen friendships."
ANL = "Analyze how a text or space produces its effect."
TASK = "Draft a paragraph."

CASES = [
 (27, CMP, "Congestion pricing and car bans both cut downtown traffic, but they distribute the cost differently: one puts a price on entry, the other removes the choice — so the real question is who each approach protects."),
 (1, ARG, "When a friend 'likes' your post but never texts back, the gesture says everything: presence without contact. That gap — being acknowledged but not reached — is what makes online closeness feel thinner than it looks."),
 (2, ANL, "The room forces intimacy: the chairs are bolted in a tight ring with no corner to retreat to, so the design itself decides that no one in the circle can be a mere bystander."),
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
    for (n, assignment, draft) in CASES:
        t0 = time.time()
        sid = create_session(assignment, PA, TASK)
        s = interact(sid, "writing", draft)
        pf = s["theory"].get("paragraph_function", {}) or {}
        rec = {"n": n, "applies": bool(pf.get("applies")), "purpose": (pf.get("purpose") or "")[:60],
               "focus": s["interactions"][-1]["intervention"].get("focus"), "elapsed_s": round(time.time() - t0, 1)}
        print(f"case {n} applies={rec['applies']} purpose='{rec['purpose']}' focus={rec['focus']} {rec['elapsed_s']}s", flush=True)
        out.append(rec)
    ok = all(x["applies"] for x in out)
    print(f"DONE — all applies True: {ok}", flush=True)


if __name__ == "__main__":
    main()
