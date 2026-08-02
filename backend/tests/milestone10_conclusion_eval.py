"""Milestone 10 — Functional Conclusions evaluation (30 cases).
Verifies the engine (a) identifies the conclusion's communicative function (applies + functions),
(b) evaluates communicative COMPLETION relative to purpose, (c) adapts to purpose, (d) imposes NO
formulaic conclusion rules ('In conclusion', restate thesis, summary), (e) preserves M5A (never
invents ideas/content; focus='writing'). Categories: effective, merely-stops, only-summarizes,
persuasive, explanatory, analytical, narrative, reflective, introduces-new-idea, mixed, brainstorm."""
import json
import re
import time
import requests

BASE = "http://localhost:8001/api"

# formulaic conclusion-rule phrasing the engine must AVOID prescribing.
RULE_FLAGS = [
    r"start (?:it |the conclusion )?with ['\"]?in conclusion",
    r"use ['\"]?in conclusion['\"]?",
    r"begin with ['\"]?(?:in conclusion|to conclude|in summary|in closing)",
    r"restate (?:your |the )?thesis",
    r"repeat (?:your |the )?thesis",
    r"summarize (?:all |each of )?your (?:points|reasons|paragraphs)",
    r"restate (?:all |each of )?your (?:points|main points|reasons)",
    r"you (?:need|should|must) (?:to )?summarize",
    r"remind the reader of (?:all )?your (?:points|reasons)",
]
RFLAG = [re.compile(p, re.IGNORECASE) for p in RULE_FLAGS]

# content-coaching red flags (M5A).
CONTENT_FLAGS = [
    r"you (?:could|might|should) add (?:a|an|the|another) (?:point|idea|argument|reason|example|claim)",
    r"another (?:reason|argument|point|idea|example)",
    r"consider (?:adding|including|mentioning) (?:the|a|an)",
    r"what(?:'s| is| are)?\s+(?:really\s+)?at stake",
    r"a (?:stronger|better) (?:claim|argument|point)",
]
CFLAG = [re.compile(p, re.IGNORECASE) for p in CONTENT_FLAGS]


def rflags(t):
    return [p.pattern for p in RFLAG if p.search(t)]


def cflags(t):
    return [p.pattern for p in CFLAG if p.search(t)]


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
EXPL = "Explain how a chosen process or phenomenon works."
ANL = "Analyze how a text or space produces its effect."
NAR = "Write a personal narrative about a meaningful experience."
REF = "Reflect on what an experience taught you."
PA = "Help the student write a conclusion that completes the essay's communicative purpose."
TASK = "Draft your conclusion."

# (n, category, assignment, draft, teacher_notes)
CASES = [
 # effective conclusions (honored, not restructured)
 (1, "effective", ARG, "So the danger was never that teens would stop talking — it's that constant contact can feel like closeness while quietly replacing it. What's worth protecting isn't the number of friends onscreen, but the few we still make time to be fully present with.", ""),
 (2, "effective", ANL, "The unnamed town, then, is not a gap in the story but its engine: by refusing a specific place, the writer makes the loneliness portable, and the reader carries it home.", ""),
 (3, "effective", NAR, "I never did catch that bus. But standing in the rain, unexpected by anyone, I understood for the first time that being unaccounted for could feel less like freedom than like disappearing.", ""),
 (4, "effective", REF, "I still don't forgive easily. What the silence taught me is smaller and harder: that repair is not a feeling that arrives but a practice you choose, again, on the days you least want to.", ""),
 (5, "effective", EXPL, "Seen whole, the cycle is less a list of steps than a single motion: water rising, cooling, falling, and rising again — the same water, endlessly reused, which is why not a drop is ever truly lost.", ""),
 # conclusions that merely STOP (no completion)
 (6, "merely_stops", ARG, "And that is my third reason why social media harms friendships. The end.", ""),
 (7, "merely_stops", EXPL, "So that is the last step of how a bill becomes a law. That's it.", ""),
 (8, "merely_stops", NAR, "Then we got in the car and drove home. And then the day was over.", ""),
 (9, "merely_stops", ANL, "So the poem uses imagery. That's the last thing I noticed about it.", ""),
 (10, "merely_stops", REF, "Anyway, that's what happened on the trip. So yeah. The end of my reflection.", ""),
 # conclusions that only SUMMARIZE
 (11, "only_summarizes", ARG, "In conclusion, social media is distracting, it is fake, and it is addictive. As I said, these are my three reasons that social media harms friendships.", ""),
 (12, "only_summarizes", ARG2, "To sum up, cars cause pollution, cars cause congestion, and cars are noisy. Therefore, as stated, the city should reduce downtown traffic.", ""),
 (13, "only_summarizes", EXPL, "In summary, first the water evaporates, then it condenses, then it precipitates. Those are the three stages I explained above.", ""),
 (14, "only_summarizes", ANL, "In conclusion, the author used short sentences, imagery, and repetition. Those are the three techniques I discussed in this essay.", ""),
 # persuasive
 (15, "persuasive", ARG2, "Fewer cars downtown is not just cleaner air; it is a different idea of who the center of a city is for. Reclaim the street, and you reclaim the reason people came together there in the first place.", ""),
 (16, "persuasive", ARG, "If closeness is measured in presence rather than pixels, then the strongest thing a teenager can do for a friendship is the least shareable: show up, put the phone down, and stay.", ""),
 # explanatory
 (17, "explanatory", EXPL, "Once you see the immune system as a memory rather than a wall, the whole logic of vaccines falls into place: we are not blocking the threat, we are teaching the body to recognize it early.", ""),
 (18, "explanatory", EXPL, "Compounding, then, is simply patience made mathematical: because each gain earns its own gains, time does the heavy lifting that effort alone never could.", ""),
 # analytical
 (19, "analytical", ANL, "The clipped father-sentences and the looping mother-sentences never argue with each other; they simply let the reader feel a verdict the narrator is too loyal to speak aloud.", ""),
 (20, "analytical", ANL, "By holding the empty doorway for ten full seconds, the film hands its silence to us — and in that borrowed waiting, the character's grief finally becomes ours to carry.", ""),
 # narrative
 (21, "narrative", NAR, "She never did drink the tea. But the rattle of that cup is the sound I reach for whenever I need to remember that bad news, too, can be delivered gently.", ""),
 (22, "narrative", NAR, "He crossed the line last, still fumbling with the lace. No one clapped. But he looked up grinning, as if finishing had never been the point.", ""),
 # reflective
 (23, "reflective", REF, "The scar is faint now. What stayed is the lesson under it: that the same hands can break and mend, and that growing up is mostly learning which one a moment asks of you.", ""),
 (24, "reflective", REF, "I keep the unmade call like a small stone in my pocket. It reminds me that silence is also a choice — and that the next time, I would rather regret the words I said than the ones I saved.", ""),
 # conclusions that INTRODUCE ENTIRELY NEW IDEAS (fractures completion)
 (25, "introduces_new_idea", ARG, "In the end, social media harms friendships. Also, we should talk about how it affects sleep, and the economy, and whether phones cause bad eyesight, which are big topics too.", ""),
 (26, "introduces_new_idea", ARG2, "So the city should reduce car traffic. On another note, the city should also build a new stadium, fix the schools, and consider a citywide art program.", ""),
 (27, "introduces_new_idea", ANL, "Thus the imagery creates a mournful mood. By the way, the poet's biography is fascinating and the historical period had many other famous writers worth studying.", ""),
 # mixed-purpose
 (28, "mixed", "Explain how social media algorithms work AND argue whether they should be regulated.", "Understanding that algorithms optimize for engagement is exactly what makes the case for oversight: a system built to hold attention will keep amplifying whatever holds it, unless we decide it shouldn't.", ""),
 (29, "mixed", "Narrate an experience with failure AND reflect on what it revealed about learning.", "I still hear the wrong note. But I've stopped hearing it as the end of the recital and started hearing it as the beginning of how I actually learned to play — by recovering, not by never slipping.", ""),
 # brainstorming exception (content help enabled)
 (30, "brainstorm_conclusion", ARG, "I've written my whole argument but I have no idea what my conclusion should do or leave the reader with.", "Brainstorming mode is ON: help the student explore what their conclusion could accomplish before drafting it."),
]


def summ(s):
    th = s["theory"]
    cf = th.get("conclusion_function", {}) or {}
    iv = s["interactions"][-1]["intervention"]
    return {
        "applies": bool(cf.get("applies")),
        "functions": cf.get("functions_in_play") or [],
        "completes_purpose": (cf.get("completes_purpose") or "").strip(),
        "relationship_to_opening": (cf.get("relationship_to_opening") or "").strip(),
        "final_understanding": (cf.get("final_understanding") or "").strip(),
        "focus": iv.get("focus", ""),
        "type": iv["type"],
        "student_facing": s["turns"][-1]["content"],
    }


def main():
    res = []
    for (n, cat, assignment, draft, notes) in CASES:
        t0 = time.time()
        try:
            sid = create_session(assignment, PA, TASK, notes)
            s = interact(sid, "writing", draft)
            f = summ(s)
            brainstorm = n == 30
            rf = rflags(f["student_facing"])
            cf = [] if brainstorm else cflags(f["student_facing"])
            focus_ok = True if brainstorm else (f["focus"] == "writing")
            applies_ok = True if brainstorm else f["applies"]
            ok = applies_ok and (not rf) and (not cf) and focus_ok
            rec = {"n": n, "category": cat, "brainstorm": brainstorm, "applies": f["applies"],
                   "functions": f["functions"], "completes_purpose": f["completes_purpose"],
                   "relationship_to_opening": f["relationship_to_opening"],
                   "final_understanding": f["final_understanding"], "focus": f["focus"], "type": f["type"],
                   "rule_flags": rf, "content_flags": cf, "ok": ok,
                   "student_facing": f["student_facing"], "elapsed_s": round(time.time() - t0, 1)}
            print(f"case {n} [{cat}] applies={f['applies']} completes='{f['completes_purpose'][:30]}' focus={f['focus']} rf={rf} cf={cf} ok={ok} {rec['elapsed_s']}s", flush=True)
            res.append(rec)
        except Exception as e:  # noqa: BLE001
            print(f"case {n} FAILED: {e}", flush=True)
            res.append({"n": n, "category": cat, "error": str(e)})
        json.dump(res, open("/app/backend/tests/milestone10_results.json", "w"), indent=2)
    passed = sum(1 for x in res if x.get("ok"))
    print(f"DONE — functional conclusion pass {passed}/{len(res)}", flush=True)


if __name__ == "__main__":
    main()
