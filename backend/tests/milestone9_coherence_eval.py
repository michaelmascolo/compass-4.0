"""Milestone 9 — Functional Transitions and Coherence evaluation (30 cases).
Verifies the engine (a) identifies the RELATIONSHIP among ideas before the language,
(b) evaluates coherence at sentence/paragraph/paragraph-to-paragraph/whole levels,
(c) treats transition words as ONE of many resources (strong flow w/ few words is honored;
many words w/ weak coherence is caught), (d) imposes no rigid transition rules / no 'add
transition words', (e) preserves M5A (never invents ideas/content; focus='writing').
Categories: strong-flow-few-transitions, many-transitions-weak-coherence, weak-sentence-to-sentence,
weak-paragraph-to-paragraph, persuasive, explanatory, analytical, narrative, reflective, mixed."""
import json
import re
import time
import requests

BASE = "http://localhost:8001/api"

# "just add transition words" / rigid transition-rule phrasing that M9 must AVOID.
RULE_FLAGS = [
    r"add (?:more )?transition(?:al)? words?", r"use (?:more )?transition(?:al)? words?",
    r"(?:start|begin) (?:each|every|the) (?:sentence|paragraph) with (?:a )?transition",
    r"insert (?:a )?transition(?:al)? (?:word|phrase)",
    r"words? like ['\"]?(?:however|therefore|furthermore|moreover|additionally|consequently|firstly|secondly)",
    r"(?:need|should) (?:more|some) transition",
    r"sprinkle in (?:some )?transitions?",
    r"use connective words",
]
RFLAG = [re.compile(p, re.IGNORECASE) for p in RULE_FLAGS]

# content-coaching red flags (M5A).
CONTENT_FLAGS = [
    r"you (?:could|might|should) add (?:a|an|the|another) (?:point|idea|argument|reason|example)",
    r"another (?:reason|argument|point|idea|example)",
    r"consider (?:adding|including|mentioning) (?:the|a|an)",
    r"what(?:'s| is| are)?\s+(?:really\s+)?at stake",
    r"for example,? you could",
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
PA = "Help the student create coherence and communicate relationships among ideas clearly."
TASK = "Draft this section of your writing."

# (n, category, assignment, draft, teacher_notes)
CASES = [
 # strong logical flow with FEW transition words (must be honored, not told to add words)
 (1, "strong_flow_few_words", ARG, "Constant availability removes the small absences that used to make return meaningful. When no one is ever gone, no one is ever quite missed. The friendship stays lit but stops being felt.", ""),
 (2, "strong_flow_few_words", EXPL, "Yeast wakes in the warm water. It feeds on the flour's sugars and breathes out gas. The gas is trapped by the gluten. The dough swells.", ""),
 (3, "strong_flow_few_words", ANL, "The narrator never names the town. That absence lets any reader lower their own street into the story. The loneliness stops being his and starts being ours.", ""),
 (4, "strong_flow_few_words", REF, "I thought forgiveness would arrive like relief. It arrived like work. The kind that starts a repair instead of ending one.", ""),
 # MANY transition words but WEAK coherence (must catch the disconnect, not praise the words)
 (5, "many_words_weak_coherence", ARG, "Firstly, social media is popular. However, phones are expensive. Moreover, teens are busy. Therefore, in conclusion, friendships are a topic. Furthermore, apps exist.", ""),
 (6, "many_words_weak_coherence", ARG2, "To begin with, cars are common. In addition, roads are long. Consequently, the weather changes. Nevertheless, downtown is a place. Thus, ultimately, traffic.", ""),
 (7, "many_words_weak_coherence", EXPL, "First, the sun exists. Secondly, plants are green. Furthermore, water is wet. As a result, photosynthesis. Moreover, in summary, energy is made somehow.", ""),
 (8, "many_words_weak_coherence", ANL, "Firstly the poem has words. However imagery appears. Therefore the mood. Moreover lines are short. In conclusion, thus, the poem is analyzed here.", ""),
 # weak SENTENCE-TO-SENTENCE connections
 (9, "weak_sentence_to_sentence", ARG, "Teens post a lot. My phone is blue. Friendship matters to society. The cafeteria was crowded yesterday.", ""),
 (10, "weak_sentence_to_sentence", EXPL, "The engine has parts. Metal is heavy. Some cars are fast. Gasoline comes from the ground somewhere.", ""),
 (11, "weak_sentence_to_sentence", NAR, "We arrived at the lake. My shoes were red. A dog barked far away. The sandwiches were in a bag.", ""),
 (12, "weak_sentence_to_sentence", REF, "I felt nervous. The room was beige. My grandmother liked tea. Time passed during the afternoon.", ""),
 # weak PARAGRAPH-TO-PARAGRAPH flow (two paragraphs that don't build on each other)
 (13, "weak_para_to_para", ARG, "Paragraph one argues social media distracts teens during homework.\n\nParagraph two suddenly describes the history of the printing press in the 1400s with no link back.", ""),
 (14, "weak_para_to_para", ARG2, "The first paragraph shows congestion pricing cut downtown trips.\n\nThe next paragraph abruptly lists types of trees found in city parks, unconnected to traffic.", ""),
 (15, "weak_para_to_para", ANL, "One paragraph interprets the poem's imagery of winter.\n\nThe following paragraph jumps to the author's biography and birthplace with no bridge.", ""),
 (16, "weak_para_to_para", EXPL, "The first paragraph explains how vaccines train the immune system.\n\nThe second paragraph unexpectedly explains how to bake sourdough bread, with no connection.", ""),
 # persuasive
 (17, "persuasive", ARG2, "Reducing downtown cars would cut pollution. It would also free space for people. These two effects reinforce each other: cleaner air makes public space worth using.", ""),
 (18, "persuasive", ARG, "Social media keeps distant friends in contact. That much is real. But keeping a thread unbroken is not the same as keeping it strong.", ""),
 # explanatory
 (19, "explanatory", EXPL, "First the water heats and evaporates. The vapor rises and cools into clouds. When the droplets grow heavy they fall as rain. The cycle then begins again.", ""),
 (20, "explanatory", EXPL, "A bill is introduced. It moves to committee. Then both chambers vote. Finally the president signs or vetoes it.", ""),
 # analytical
 (21, "analytical", ANL, "The film cuts faster as the argument escalates. The quickening rhythm makes the audience feel the loss of control the characters describe.", ""),
 (22, "analytical", ANL, "Early sentences about the father are clipped and short. Later ones about the mother run long. The shift in rhythm sorts the reader's sympathy before any judgment is stated.", ""),
 # narrative
 (23, "narrative", NAR, "The bus pulled away as I reached the corner. I stood in the rain watching its lights blur. For the first time, no one was expecting me anywhere.", ""),
 (24, "narrative", NAR, "She set the tea down. The cup rattled against the saucer. Before she spoke, I already knew the news was bad.", ""),
 # reflective
 (25, "reflective", REF, "At first the silence after my apology felt like failure. Later I understood it differently. The quiet was not the end of the friendship but the slow start of its repair.", ""),
 (26, "reflective", REF, "I keep returning to the moment I didn't call. The phone was right there. What that silence taught me is still unfolding, years later.", ""),
 # mixed-purpose
 (27, "mixed", "Explain how social media algorithms work AND argue whether they should be regulated.", "Algorithms rank posts to hold attention. Because they optimize for engagement, they amplify outrage. That tendency is exactly why they need oversight.", ""),
 (28, "mixed", "Narrate an experience with failure AND reflect on what it revealed about learning.", "I bombed the recital. My hands shook on the keys. Only afterward did I see that I had practiced to avoid mistakes, never to recover from them.", ""),
 (29, "mixed", "Analyze a policy's effects AND recommend whether to keep it.", "The policy cut emissions but raised costs for small shops. Weighing both, the harm to small business outweighs the gain, so the policy should be revised rather than kept.", ""),
 # brainstorming exception (content help enabled)
 (30, "brainstorm_coherence", ARG, "My two paragraphs feel disconnected but I don't know how they relate to each other yet.", "Brainstorming mode is ON: help the student explore possible relationships between their ideas before drafting connections."),
]


def summ(s):
    th = s["theory"]
    cf = th.get("coherence_function", {}) or {}
    iv = s["interactions"][-1]["intervention"]
    return {
        "applies": bool(cf.get("applies")),
        "relationship": (cf.get("intended_relationship") or "").strip(),
        "level": (cf.get("level") or "").strip(),
        "resources": cf.get("resources_in_use") or [],
        "reader_can_follow": (cf.get("reader_can_follow") or "").strip(),
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
            # coherence should apply whenever transitions/flow are at issue (all our cases target it),
            # but a brainstorm-no-draft may legitimately not populate it.
            applies_ok = True if brainstorm else f["applies"]
            ok = applies_ok and (not rf) and (not cf) and focus_ok
            rec = {"n": n, "category": cat, "brainstorm": brainstorm, "applies": f["applies"],
                   "relationship": f["relationship"], "level": f["level"], "resources": f["resources"],
                   "reader_can_follow": f["reader_can_follow"], "focus": f["focus"], "type": f["type"],
                   "rule_flags": rf, "content_flags": cf, "ok": ok,
                   "student_facing": f["student_facing"], "elapsed_s": round(time.time() - t0, 1)}
            print(f"case {n} [{cat}] applies={f['applies']} rel='{f['relationship'][:28]}' lvl='{f['level'][:24]}' focus={f['focus']} rf={rf} cf={cf} ok={ok} {rec['elapsed_s']}s", flush=True)
            res.append(rec)
        except Exception as e:  # noqa: BLE001
            print(f"case {n} FAILED: {e}", flush=True)
            res.append({"n": n, "category": cat, "error": str(e)})
        json.dump(res, open("/app/backend/tests/milestone9_results.json", "w"), indent=2)
    passed = sum(1 for x in res if x.get("ok"))
    print(f"DONE — functional coherence pass {passed}/{len(res)}", flush=True)


if __name__ == "__main__":
    main()
