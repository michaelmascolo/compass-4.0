"""Milestone 13 — Revision as Development evaluation (30 cases, mostly multi-turn).
Verifies the engine (a) evaluates a revision as DEVELOPMENTAL change (applies + development_detected)
when a prior draft exists, (b) names ONE primary_growth qualitatively (no edit-counting), (c) generates
a transfer_message on real growth, (d) names a single remaining_opportunity on limited/regressed progress,
(e) does NOT set applies on the FIRST submission, (f) reads trajectory across 3+ drafts, (g) keeps ONE
M11 target, (h) preserves M5A (no rewriting/inventing; focus='writing'). Categories: substantial-growth,
superficial-edit, multi-draft-trajectory, regression, reader-understanding, coherence, conclusion, purpose,
first-submission (control)."""
import json
import re
import time
import requests

BASE = "http://localhost:8001/api"

CONTENT_FLAGS = [
    r"you (?:could|might|should) add (?:a|an|the|another) (?:point|idea|argument|reason|example)",
    r"another (?:reason|argument|point|idea|example)", r"here'?s a (?:better|stronger) version",
    r"for example,? you could", r"try writing it (?:as|like)", r"rewrite (?:it|this) (?:as|to)",
]
CFLAG = [re.compile(p, re.IGNORECASE) for p in CONTENT_FLAGS]
# edit-counting / scorekeeping phrasing M13 must avoid.
SCORE_FLAGS = [
    r"you made \d+ (?:changes|edits|revisions)", r"\d+ edits", r"count(?:ed|ing)? (?:your )?(?:edits|changes)",
    r"great, you revised a lot", r"lots of changes", r"so many (?:edits|changes)",
]
SFLAG = [re.compile(p, re.IGNORECASE) for p in SCORE_FLAGS]


def cflags(t):
    return [p.pattern for p in CFLAG if p.search(t)]


def sflags(t):
    return [p.pattern for p in SFLAG if p.search(t)]


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


def rd(s):
    th = s["theory"]
    d = th.get("revision_development", {}) or {}
    sc = th.get("scaffolding_control", {}) or {}
    iv = s["interactions"][-1]["intervention"]
    return {
        "applies": bool(d.get("applies")),
        "development_detected": (d.get("development_detected") or "").strip(),
        "primary_growth": (d.get("primary_growth") or "").strip(),
        "communication_change": (d.get("communication_change") or "").strip(),
        "reader_change": (d.get("reader_change") or "").strip(),
        "remaining_opportunity": (d.get("remaining_opportunity") or "").strip(),
        "transfer_message": (d.get("transfer_message") or "").strip(),
        "primary_target": (sc.get("primary_target") or "").strip(),
        "focus": iv.get("focus", ""),
        "student_facing": s["turns"][-1]["content"],
    }


ARG = "Argue whether social media improves or harms teen friendships."
EXPL = "Explain how a chosen process or phenomenon works."
ANL = "Analyze how a text or space produces its effect."
REF = "Reflect on what an experience taught you."
PA = "Help the student grow as a writer across drafts, focusing on developmental change."
TASK = "Work on your draft."

# expects_growth: 'yes' (real growth -> transfer_message expected), 'no' (superficial/regression -> remaining_opportunity), 'first' (first submission -> applies False)
# drafts is a tuple of turns.
CASES = [
 # substantial developmental improvement
 (1, "substantial_growth", ARG, ("Social media is bad for friends.",
   "Social media harms close friendships because constant, shallow contact crowds out the focused attention deep friendship needs."), "yes"),
 (2, "substantial_growth", ANL, ("The poem is about grief.",
   "By refusing to name the town, the poet makes the grief portable, so any reader lowers their own street into it."), "yes"),
 (3, "substantial_growth", EXPL, ("Photosynthesis is important.",
   "Photosynthesis is how a leaf turns sunlight, water, and CO2 into the sugar the plant lives on, releasing oxygen as a byproduct."), "yes"),
 (4, "substantial_growth", REF, ("The loss taught me something.",
   "Losing the match taught me that I'd trained to avoid mistakes rather than to recover from them — and recovery is the real skill."), "yes"),
 (5, "substantial_growth", ARG, ("Cars downtown are bad and should be reduced for reasons.",
   "Reducing downtown cars isn't only about cleaner air; it changes who the center of a city is for — reclaiming the street reclaims the reason people gathered there."), "yes"),
 # superficial editing only (word swaps, no developmental change)
 (6, "superficial_edit", ARG, ("Social media is bad for teen friendships.",
   "Social media is really bad for teenage friendships."), "no"),
 (7, "superficial_edit", EXPL, ("The water cycle has stages that repeat over time.",
   "The water cycle has various stages which repeat again over time."), "no"),
 (8, "superficial_edit", ANL, ("The author uses imagery to create a mood in the poem.",
   "The author utilizes imagery in order to create a certain mood within the poem."), "no"),
 (9, "superficial_edit", REF, ("The trip was meaningful to me in many ways.",
   "The trip was very meaningful to me in a lot of different ways."), "no"),
 # regression (revision makes communication worse)
 (10, "regression", ARG, ("Social media weakens close friendships by trading depth of attention for breadth of contact.",
   "Social media is a thing. Friends too. It does stuff to them maybe."), "no"),
 (11, "regression", ANL, ("By withholding the narrator's name, the story keeps the reader unsure whether to trust him.",
   "The story has a narrator. He does things. There is trust or something in it."), "no"),
 (12, "regression", EXPL, ("A vaccine trains the immune system by showing it a harmless piece of a threat.",
   "Vaccines and immune systems. They interact. Then protection happens somehow."), "no"),
 # multi-draft trajectory (3 turns; growing capacity)
 (13, "multi_draft", ARG, ("Social media bad.",
   "Social media harms friendship.",
   "Social media harms close friendships because it rewards constant shallow contact over focused attention."), "yes"),
 (14, "multi_draft", REF, ("The trip changed me.",
   "The trip changed how I saw home.",
   "Leaving finally taught me what home meant — not a place, but the people who expected me back."), "yes"),
 (15, "multi_draft", ANL, ("The poem has imagery.",
   "The poem's winter imagery feels cold.",
   "The poem's relentless winter imagery makes the speaker's grief feel like a season that refuses to end."), "yes"),
 (16, "multi_draft", EXPL, ("Compounding is a money thing.",
   "Compounding grows money over time.",
   "Compounding grows money because each period's gains earn their own gains, so time does the work effort can't."), "yes"),
 # stronger reader understanding (revision closes an inferential gap)
 (17, "reader_understanding", ARG, ("Teens check phones constantly. Therefore they don't value close friends.",
   "Teens check phones constantly, and that habit of split attention means close friends rarely get the undivided presence that signals they matter."), "yes"),
 (18, "reader_understanding", EXPL, ("The water heats. So the ecosystem changes.",
   "As the lake water heats, oxygen levels drop, and because many fish can't survive the thinner oxygen, the whole food chain shifts within a season."), "yes"),
 (19, "reader_understanding", ANL, ("Short sentences mean the story is about grief.",
   "The clipped, short sentences withhold emotion the way the grieving narrator does, so their flatness becomes the grief the story won't state outright."), "yes"),
 # stronger coherence (revision connects previously disconnected ideas)
 (20, "coherence", ARG, ("Social media reduces face time. The printing press was invented in the 1400s. Friendships suffer.",
   "Social media reduces face-to-face time, and because friendship is built in shared presence, less of it quietly weakens the bond."), "yes"),
 (21, "coherence", EXPL, ("First the yeast ferments. Mount Everest is tall. Then the bread bakes.",
   "First the yeast ferments, filling the dough with gas; then the heat sets that risen structure, which is why the loaf holds its airy shape."), "yes"),
 # improved conclusion (ending now completes rather than stops)
 (22, "conclusion", ARG, ("And that is my third reason. The end.",
   "So the real danger isn't losing touch — it's mistaking constant contact for closeness, and forgetting to protect the few friendships that ask for our full attention."), "yes"),
 (23, "conclusion", REF, ("Anyway that's what happened on the trip.",
   "I went looking for adventure and came back with something quieter: the sense that the people waiting for me were the trip's real destination."), "yes"),
 # improved communicative purpose (from topic to arguable claim)
 (24, "purpose", ARG, ("My essay is about social media and friendship.",
   "My essay argues that social media strengthens loose acquaintances while quietly eroding our closest friendships."), "yes"),
 (25, "purpose", ANL, ("This essay is about the painting.",
   "This essay argues that the painting's empty center forces the viewer to supply the missing figure, making absence its true subject."), "yes"),
 (26, "purpose", EXPL, ("I will talk about how the internet works.",
   "This piece explains how the internet delivers a message by breaking it into labeled packets that travel separate routes and reassemble on arrival."), "yes"),
 # limited progress on the right idea but still incomplete
 (27, "limited_progress", ARG, ("Social media is bad for friends.",
   "Social media is bad for close friends because of attention."), "no"),
 (28, "limited_progress", ANL, ("The imagery matters.",
   "The imagery matters because it is significant to the poem's mood."), "no"),
 # first submission control (NO prior draft -> applies must be False)
 (29, "first_submission", ARG, ("Social media harms teen friendships by trading attention for contact.",), "first"),
 (30, "first_submission", EXPL, ("A vaccine rehearses the immune system on a harmless fragment of a threat.",), "first"),
]


def run_case(n, cat, assignment, drafts, expects):
    sid = create_session(assignment, PA, TASK)
    last = None
    for i, content in enumerate(drafts):
        s = interact(sid, "writing" if i == 0 else "revise", content)
        last = rd(s)
    one_target = bool(last["primary_target"])
    cf = cflags(last["student_facing"])
    sf = sflags(last["student_facing"])
    focus_ok = last["focus"] == "writing"
    if expects == "first":
        # first submission: no prior draft -> revision_development should NOT apply
        applies_ok = not last["applies"]
        expect_ok = applies_ok
    else:
        applies_ok = last["applies"] and bool(last["development_detected"])
        if expects == "yes":
            # real growth -> primary_growth + transfer_message present
            expect_ok = bool(last["primary_growth"]) and bool(last["transfer_message"])
        else:  # 'no' -> limited/regression -> remaining_opportunity named
            expect_ok = bool(last["remaining_opportunity"])
    ok = applies_ok and one_target and (not cf) and (not sf) and focus_ok and expect_ok
    return {"n": n, "category": cat, "turns": len(drafts), "applies": last["applies"],
            "development_detected": last["development_detected"][:50], "primary_growth": last["primary_growth"][:50],
            "transfer_message": last["transfer_message"][:70], "remaining_opportunity": last["remaining_opportunity"][:60],
            "primary_target": last["primary_target"][:44], "focus": last["focus"],
            "content_flags": cf, "score_flags": sf,
            "checks": {"applies_ok": applies_ok, "one_target": one_target, "focus_ok": focus_ok, "expect_ok": expect_ok},
            "ok": ok, "student_facing": last["student_facing"]}


def main():
    res = []
    for c in CASES:
        t0 = time.time()
        try:
            rec = run_case(*c)
            rec["elapsed_s"] = round(time.time() - t0, 1)
            print(f"case {rec['n']} [{rec['category']}] turns={rec['turns']} applies={rec['applies']} dev='{rec['development_detected'][:20]}' growth='{rec['primary_growth'][:22]}' expect_ok={rec['checks']['expect_ok']} focus={rec['focus']} cf={rec['content_flags']} sf={rec['score_flags']} ok={rec['ok']} {rec['elapsed_s']}s", flush=True)
            res.append(rec)
        except Exception as e:  # noqa: BLE001
            print(f"case {c[0]} FAILED: {e}", flush=True)
            res.append({"n": c[0], "category": c[1], "error": str(e)})
        json.dump(res, open("/app/backend/tests/milestone13_results.json", "w"), indent=2)
    passed = sum(1 for x in res if x.get("ok"))
    print(f"DONE — revision development pass {passed}/{len(res)}", flush=True)


if __name__ == "__main__":
    main()
