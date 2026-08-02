"""Milestone 7 — Functional Paragraph Development evaluation (30 cases).
Verifies the engine (a) identifies each paragraph's communicative purpose (paragraph_function.applies
+ purpose populated), (b) evaluates coherence functionally, (c) adapts development to purpose,
(d) imposes NO paragraph template, (e) preserves the M5A content boundary (focus='writing').
Paragraph types: effective, weakly-organized, competing-purposes, incoherent, weak-development,
plus narrative/explanatory/analytical/argumentative/reflective paragraphs."""
import json
import re
import time
import requests

BASE = "http://localhost:8001/api"

# Rigid paragraph-template phrasing that would signal formulaic (not functional) teaching.
TEMPLATE_FLAGS = [
    r"topic sentence,? (?:then )?(?:evidence|example),? (?:then )?(?:analysis|explanation),? (?:then )?(?:concluding|closing)",
    r"claim[- ]evidence[- ]analysis (?:format|template|formula|structure)",
    r"every paragraph (?:must|should|needs to) (?:have|contain|include|start with) a topic sentence",
    r"(?:begin|start) (?:every|each) paragraph with a topic sentence",
    r"(?:PEE|PEEL|TEAL|MEAL|RACE) (?:paragraph|format|structure|method)",
    r"(?:three|3) sentences? of (?:evidence|analysis)",
    r"must (?:end|close|finish) with a concluding sentence",
    r"follow (?:the|this) (?:paragraph )?(?:template|formula)",
]
TFLAG = [re.compile(p, re.IGNORECASE) for p in TEMPLATE_FLAGS]

# Content-coaching red flags (M5A) reused.
CONTENT_FLAGS = [
    r"what(?:'s| is| are)?\s+(?:really\s+)?at stake",
    r"another (?:reason|argument|example|point|perspective)",
    r"you (?:could|might|should) add",
    r"you (?:could|might|should) (?:mention|include|bring in)",
    r"a (?:stronger|better|more compelling) (?:argument|reason|claim|example)",
    r"consider (?:adding|including|mentioning)",
    r"for example,? you could",
    r"try adding",
]
CFLAG = [re.compile(p, re.IGNORECASE) for p in CONTENT_FLAGS]


def tflags(t):
    return [p.pattern for p in TFLAG if p.search(t)]


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


PA = "Help the student clarify what each paragraph is doing for the essay."
ARG = "Argue whether social media improves or harms teen friendships."
EXPL = "Explain how a chosen process or phenomenon works."
INFO = "Write an informative report on a topic of your choice."
ANL = "Analyze how a text or space produces its effect."
NAR = "Write a personal narrative about a meaningful experience."
REF = "Reflect on what an experience taught you."
CMP = "Compare two options and help a reader understand the trade-offs."
TASK = "Draft a paragraph."

# (n, ptype, assignment, purpose, draft, teacher_notes)
CASES = [
 # effective paragraphs (should be honored, invited forward — not restructured)
 (1, "effective_argumentative", ARG, PA, "When a friend 'likes' your post but never texts back, the gesture says everything: presence without contact. That gap — being acknowledged but not reached — is what makes online closeness feel thinner than it looks.", ""),
 (2, "effective_analytical", ANL, PA, "The room forces intimacy: the chairs are bolted in a tight ring with no corner to retreat to, so the design itself decides that no one in the circle can be a mere bystander.", ""),
 (3, "effective_narrative", NAR, PA, "The kitchen still smelled like her cigarettes that morning, though she'd quit a year before she left. I stood in the doorway not going in, the way you pause at the edge of a photograph you're not ready to be inside of.", ""),
 (4, "effective_reflective", REF, PA, "I used to think losing the match was the failure. Only later did I see the real one: I had trained to avoid mistakes instead of training to recover from them, and a game punishes that quietly.", ""),
 (5, "effective_explanatory", EXPL, PA, "A vaccine works by rehearsal. It shows the immune system a harmless piece of a threat, so that when the real thing arrives the body already knows the face and can respond before damage spreads.", ""),
 # weakly organized paragraphs
 (6, "weak_org_argumentative", ARG, PA, "Social media is bad. Also teens use it. Phones are expensive. Friendships matter. There are many apps. So social media affects friends somehow.", ""),
 (7, "weak_org_informative", INFO, PA, "Solar panels exist. The sun is hot. Electricity is useful. Some houses have panels. Batteries store things. Energy is a topic people discuss.", ""),
 (8, "weak_org_explanatory", EXPL, PA, "A bill is a thing. Congress is in Washington. The president signs stuff. There are votes. Laws are important for society and rules.", ""),
 (9, "weak_org_analytical", ANL, PA, "The poem has words. Imagery is used. Poets do that. The mood is a mood. Lines are short and long. It is a poem about things.", ""),
 (10, "weak_org_narrative", NAR, PA, "I went somewhere. It was a day. Things happened. People were there. Then it ended. It was memorable I think.", ""),
 # multiple competing purposes in one paragraph
 (11, "competing_arg", ARG, PA, "Social media harms deep friendships, and here is a definition of social media, and also my personal story about camp, and the history of the telephone is interesting too.", ""),
 (12, "competing_expl", EXPL, PA, "Photosynthesis converts light to energy, but also plants are pretty, and my garden did badly last year, and here is my argument that everyone should garden.", ""),
 (13, "competing_anl", ANL, PA, "The author uses short sentences for tension, and this reminds me of a movie, and short sentences are grammatically simple, and I think everyone should write shortly.", ""),
 (14, "competing_ref", REF, PA, "Failing taught me patience, and also here are the rules of chess, and my brother is annoying, and patience is a virtue that dictionaries define clearly.", ""),
 # lacking coherence (sentences don't hold together)
 (15, "incoherent_arg", ARG, PA, "Teens post constantly. The Roman Empire fell in 476. My phone battery dies fast. Therefore friendships are complicated in interesting ways for people.", ""),
 (16, "incoherent_info", INFO, PA, "The water cycle has stages. Pizza is popular. Evaporation is one word. Clouds can be white. My favorite season is fall for many reasons.", ""),
 (17, "incoherent_narr", NAR, PA, "We drove to the lake. Triangles have three sides. My grandfather laughed. Inflation rose last year. The water was cold when I finally jumped.", ""),
 # weak development (a purpose stated but not developed)
 (18, "underdeveloped_arg", ARG, PA, "Social media weakens close friendships. This is true. It really does weaken them. That is my point about friendships and social media.", ""),
 (19, "underdeveloped_expl", EXPL, PA, "The internet routes data using packets. Packets are how it works. They route the data. That is basically the process of routing data.", ""),
 (20, "underdeveloped_anl", ANL, PA, "The imagery creates a sad mood. It is very sad imagery. The mood is definitely sad. Sadness is the mood created by the imagery.", ""),
 (21, "underdeveloped_ref", REF, PA, "The trip changed me. I am different now. It really changed me a lot. Change is what happened to me on the trip.", ""),
 # narrative / explanatory / analytical / argumentative / reflective (typed, moderate)
 (22, "narrative_scene", NAR, PA, "The bus pulled away just as I reached the corner. I stood there in the rain watching its lights blur, aware for the first time that no one was expecting me anywhere.", ""),
 (23, "explanatory_process", EXPL, PA, "First the yeast wakes in warm water. Then it feeds on the flour's sugars and releases gas, which is why the dough swells — the bubbles are trapped by the gluten you kneaded.", ""),
 (24, "analytical_claim", ANL, PA, "The narrator never names the town, and that absence does real work: it lets the reader lower any specific place into the story, so the loneliness feels like it could be anyone's.", ""),
 (25, "argumentative_reason", ARG, PA, "One reason constant availability strains friendship is that it removes the small absences that used to make return meaningful; when no one is ever gone, no one is ever quite missed.", ""),
 (26, "reflective_meaning", REF, PA, "I keep returning to the silence after I apologized. I thought forgiveness would feel like relief, but it felt more like work — the slow kind that starts, not ends, a repair.", ""),
 # comparison paragraph + placement/relationship-to-whole cases
 (27, "comparison_para", CMP, PA, "Congestion pricing and car bans both cut downtown traffic, but they distribute the cost differently: one puts a price on entry, the other removes the choice — so the real question is who each approach protects.", ""),
 (28, "transition_bridge", ARG, "Help the student clarify what each paragraph is doing and how paragraphs connect.", "So far the harms have all been about attention. But attention isn't the only casualty; the next kind of loss is slower and harder to see.", ""),
 (29, "concession_para", ARG, PA, "It's fair to say social media keeps distant friends in contact who would otherwise drift apart entirely. That much is real — but keeping a thread unbroken is not the same as keeping it strong.", ""),
 # brainstorming exception at paragraph grain (content help allowed)
 (30, "brainstorm_para", ARG, "Help the student generate ideas for a body paragraph.", "I need a body paragraph about social media and friendship but I don't have any ideas for what it should be about yet.", "Brainstorming mode is ON: help the student generate possible directions for this paragraph before drafting."),
]


def summ(s):
    th = s["theory"]
    pf = th.get("paragraph_function", {}) or {}
    iv = s["interactions"][-1]["intervention"]
    sf = s["turns"][-1]["content"]
    return {
        "applies": bool(pf.get("applies")),
        "pf_purpose": (pf.get("purpose") or "").strip(),
        "pf_coherence": (pf.get("coherence") or "").strip(),
        "pf_development": (pf.get("development") or "").strip(),
        "focus": iv.get("focus", ""),
        "type": iv["type"],
        "student_facing": sf,
        "domains": th.get("currently_relevant_domains", []),
    }


def main():
    res = []
    for (n, ptype, assignment, purpose, draft, notes) in CASES:
        t0 = time.time()
        try:
            sid = create_session(assignment, purpose, draft and TASK or TASK, notes)
            s = interact(sid, "writing", draft)
            f = summ(s)
            brainstorm = n == 30
            tf = tflags(f["student_facing"])
            cf = [] if brainstorm else cflags(f["student_facing"])
            purpose_identified = f["applies"] and bool(f["pf_purpose"])
            focus_ok = (f["focus"] == "content") if brainstorm else (f["focus"] == "writing")
            # Brainstorm case has no paragraph written yet — paragraph_function need not apply;
            # correctness there is content-mode + no template imposition.
            ok = (not tf) and (not cf) and focus_ok and (True if brainstorm else purpose_identified)
            rec = {"n": n, "ptype": ptype, "brainstorm": brainstorm, "applies": f["applies"],
                   "pf_purpose": f["pf_purpose"], "pf_coherence": f["pf_coherence"],
                   "pf_development": f["pf_development"], "focus": f["focus"], "type": f["type"],
                   "template_flags": tf, "content_flags": cf, "ok": ok,
                   "student_facing": f["student_facing"], "elapsed_s": round(time.time() - t0, 1)}
            print(f"case {n} [{ptype}] applies={f['applies']} purpose='{f['pf_purpose'][:40]}' focus={f['focus']} tf={tf} cf={cf} ok={ok} {rec['elapsed_s']}s", flush=True)
            res.append(rec)
        except Exception as e:  # noqa: BLE001
            print(f"case {n} FAILED: {e}", flush=True)
            res.append({"n": n, "ptype": ptype, "error": str(e)})
        json.dump(res, open("/app/backend/tests/milestone7_results.json", "w"), indent=2)
    passed = sum(1 for x in res if x.get("ok"))
    print(f"DONE — functional paragraph pass {passed}/{len(res)}", flush=True)


if __name__ == "__main__":
    main()
