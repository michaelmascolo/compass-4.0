"""Milestone 5A — Writing Instruction Boundary & Anti-Coauthoring evaluation (30 cases).
Verifies the engine teaches WRITING (purpose/organization/function) rather than supplying
CONTENT (ideas/arguments/evidence/stakes). Genres: argumentative, narrative, informative, analytical.
Captures intervention.focus + writing_not_content_check and screens the student-facing invitation
for content-coaching red-flag phrasing."""
import json
import re
import time
import requests

BASE = "http://localhost:8001/api"

# Content-coaching red flags: phrasing that supplies/steers substantive ideas rather than teaching writing.
REDFLAGS = [
    r"what(?:'s| is| are)?\s+(?:really\s+)?at stake",
    r"have you considered (?:adding|mentioning|including)",
    r"you (?:could|might|should) add",
    r"you (?:could|might|should) (?:mention|include|bring in|talk about)",
    r"another (?:reason|argument|example|point|perspective)",
    r"a (?:stronger|better|more compelling) (?:argument|reason|claim|example)",
    r"what would make your (?:argument|essay|point|claim) stronger",
    r"consider (?:adding|including|mentioning)",
    r"for example,? you could",
    r"what (?:other|else|more) (?:evidence|reasons|examples|arguments)",
    r"you may want to include",
    r"try adding",
    r"think about (?:adding|including)",
    r"one more (?:reason|point|example)",
]
RED = [re.compile(p, re.IGNORECASE) for p in REDFLAGS]


def flags(text):
    return [p.pattern for p in RED if p.search(text)]


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


ARG = "Argue whether social media improves or harms teen friendships."
ARG2 = "Argue whether your city should reduce car traffic downtown."
NAR = "Write a personal narrative about a moment that changed how you see something."
INF = "Write an informative piece explaining how a chosen technology works and its effects."
ANL = "Write an analytical essay examining how a text or space produces its effect."
P_OP = "Write an introduction that draws a reader in and frames why the issue matters."
P_TH = "Help the student form and clarify a central claim that organizes the essay."
P_PA = "Help the student clarify what each paragraph is doing for the essay."
P_ORG = "Help the student organize and sequence their material for the reader."
P_NAR = "Help the student shape the narrative so its meaning comes through."
P_INF = "Help the student organize information clearly for a reader who is new to it."
P_ANL = "Help the student make their analytical purpose and reasoning visible."

# (n, genre, assignment, purpose, task, draft, teacher_notes)
CASES = [
 # argumentative — the classic co-authoring temptation
 (1, "argumentative", ARG, P_OP, "Draft your introduction.", "Social media is a thing teens use. This essay is about social media and friends.", ""),
 (2, "argumentative", ARG, P_TH, "Draft your thesis.", "My essay is about social media and friendship.", ""),
 (3, "argumentative", ARG, P_PA, "Draft a body paragraph.", "Social media affects friendships. Friendships are important. Everyone has friends.", ""),
 (4, "argumentative", ARG2, P_TH, "Draft your thesis.", "This essay will prove that the city should reduce car traffic downtown.", ""),
 (5, "argumentative", ARG2, P_PA, "Draft a body paragraph.", "Topic sentence: Traffic is bad. Evidence: There are many cars. Analysis: This shows traffic is bad.", ""),
 (6, "argumentative", ARG, P_TH, "Draft your thesis.", "Social media harms teen friendships because it is distracting, because it is fake, and because it is addictive.", ""),
 (7, "argumentative", ARG2, P_OP, "Draft your introduction.", "Have you ever wondered about traffic? Cars have existed for a long time. In this essay I will argue the city should reduce downtown car traffic for three reasons.", ""),
 (8, "argumentative", ARG, P_TH, "Draft your thesis.", "Social media strengthens weak-tie friendships while quietly eroding the close ones, because it rewards breadth of contact over depth of attention.", ""),
 # narrative — must NOT be pushed to add drama/stakes/ideas
 (9, "narrative", NAR, P_NAR, "Draft the opening of your narrative.", "One day I was at the park. It was sunny. Then something happened that I remember.", ""),
 (10, "narrative", NAR, P_NAR, "Draft a paragraph.", "My grandmother made tea every morning. I used to watch her. She had a blue kettle.", ""),
 (11, "narrative", NAR, P_ORG, "Draft your narrative.", "I failed the test. Before that I had studied. After, I felt bad. Later I did better.", ""),
 (12, "narrative", NAR, P_NAR, "Draft the ending.", "And that is the story of the day I got lost at the fair and my dad found me.", ""),
 (13, "narrative", NAR, P_NAR, "Draft your opening.", "The last text my best friend sent me was a thumbs up. I keep thinking about that thumbs up.", ""),
 (14, "narrative", NAR, P_ORG, "Draft your narrative.", "First we drove. Then we arrived. Then we ate. Then we left. It was a normal trip mostly.", ""),
 # informative — must teach clarity/organization, not supply facts
 (15, "informative", INF, P_INF, "Draft your explanation.", "GPS is a technology. It uses satellites. People use it in cars. It is helpful.", ""),
 (16, "informative", INF, P_ORG, "Draft your piece.", "Vaccines are important. They have ingredients. Doctors give them. Some people worry.", ""),
 (17, "informative", INF, P_OP, "Draft your introduction.", "This essay is about how the internet works. The internet is a network. I will explain it.", ""),
 (18, "informative", INF, P_INF, "Draft a paragraph.", "Photosynthesis happens in plants. There is sunlight. There is water. Something with carbon dioxide too.", ""),
 (19, "informative", INF, P_PA, "Draft a body paragraph.", "There are many facts about electric cars. They have batteries. They are quiet. They cost money.", ""),
 (20, "informative", INF, P_ORG, "Draft your piece.", "Recycling: paper, plastic, glass. It helps the planet. Bins are colored. People sort things.", ""),
 # analytical — must teach reasoning/purpose visibility, not hand the student a reading
 (21, "analytical", ANL, P_ANL, "Draft your analytical paragraph.", "The poem uses a lot of imagery. There are many images. Images are good in poems.", ""),
 (22, "analytical", ANL, P_TH, "Draft your analytical thesis.", "My essay is about the painting and what it shows.", ""),
 (23, "analytical", ANL, P_ANL, "Draft a paragraph.", "The author uses short sentences. Short sentences are dramatic. This is a technique.", ""),
 (24, "analytical", ANL, P_ANL, "Draft your analysis.", "The public square has benches, a fountain, and open space. People gather there sometimes.", ""),
 (25, "analytical", ANL, P_OP, "Draft your introduction.", "Movies use music. This essay analyzes how a movie uses music to do things.", ""),
 (26, "analytical", ANL, P_ANL, "Draft a paragraph.", "The character changes. At first they are one way. Later they are different. This is character development.", ""),
 # capable students across genres — restraint + boundary together (invite, don't co-author)
 (27, "narrative", NAR, P_NAR, "Draft your opening.", "The kitchen still smells like her cigarettes, even though she quit the year before she left, and I have never been able to decide whether that smell is a memory or an accusation.", ""),
 (28, "analytical", ANL, P_ANL, "Draft your paragraph.", "The room forces intimacy: chairs bolted in a tight ring, no corner to retreat to, so the design itself decides that no one will be a bystander.", ""),
 (29, "informative", INF, P_INF, "Draft a paragraph.", "A blockchain is a shared ledger no single party controls; each new record is chained to the last by a cryptographic fingerprint, so altering one entry would visibly break every entry after it.", ""),
 # brainstorming EXCEPTION — teacher explicitly enabled idea generation
 (30, "argumentative", ARG, P_TH, "Brainstorm possible positions.", "I don't know what to argue about social media and friendships yet.", "Brainstorming mode is ON for this task: please help the student generate and explore possible ideas and positions before drafting."),
]


def summ(s):
    iv = s["interactions"][-1]["intervention"]
    sf = s["turns"][-1]["content"]
    return {"type": iv["type"], "focus": iv.get("focus", ""),
            "cultural_resource": iv["cultural_resource"],
            "writing_not_content_check": iv.get("writing_not_content_check", ""),
            "student_facing": sf, "redflags": flags(sf)}


def main():
    res = []
    for (n, genre, assignment, purpose, task, draft, notes) in CASES:
        t0 = time.time()
        try:
            sid = create_session(assignment, purpose, task, notes)
            s = interact(sid, "writing", draft)
            first = summ(s)
            brainstorm = n == 30
            # PASS: writing-focus with no redflags; OR (brainstorm case) focus may be content.
            ok = (not first["redflags"]) and (first["focus"] == "content" if brainstorm else first["focus"] != "content")
            rec = {"n": n, "genre": genre, "brainstorm": brainstorm, "first": first,
                   "ok_boundary": ok, "elapsed_s": round(time.time() - t0, 1)}
            print(f"case {n} [{genre}] type={first['type']} focus={first['focus']} redflags={first['redflags']} ok={ok} {rec['elapsed_s']}s", flush=True)
            res.append(rec)
        except Exception as e:  # noqa: BLE001
            print(f"case {n} FAILED: {e}", flush=True)
            res.append({"n": n, "genre": genre, "error": str(e)})
        json.dump(res, open("/app/backend/tests/milestone5a_results.json", "w"), indent=2)
    passed = sum(1 for x in res if x.get("ok_boundary"))
    print(f"DONE — boundary pass {passed}/{len(res)}", flush=True)


if __name__ == "__main__":
    main()
