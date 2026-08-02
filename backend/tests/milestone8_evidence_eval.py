"""Milestone 8 — Functional Evidence and Support evaluation (30 cases).
Verifies the engine (a) treats evidence as a communicative resource read relative to purpose,
(b) distinguishes evidence FROM interpretation, (c) teaches WHY evidence matters rather than
'add more evidence', (d) imposes no rigid evidence rules / no counting, (e) preserves the M5A
content boundary (never invents evidence/examples/stats/quotations; focus='writing').
Categories: strong-evidence/weak-interpretation, weak-evidence/strong-interpretation, persuasive,
explanatory, analytical, narrative, reflective, missing-evidence, irrelevant-evidence, unsupported-claim."""
import json
import re
import time
import requests

BASE = "http://localhost:8001/api"

# "just add more evidence" / counting / rigid-rule phrasing that M8 must AVOID.
RULE_FLAGS = [
    r"add more evidence", r"more evidence", r"need(?:s)? (?:more|another|additional) (?:evidence|examples?|sources?|quotes?|statistics?|data)",
    r"(?:at least|need|use|include|cite) (?:two|three|3|2|several|multiple) (?:sources?|examples?|quotes?|pieces of evidence|statistics?)",
    r"you (?:need|should) (?:cite|include|add) (?:a )?(?:source|statistic|quote|study)",
    r"back (?:it|this|that) up with (?:more )?(?:facts|data|statistics|sources)",
    r"one (?:more|additional) (?:example|source|quote|statistic)",
]
RFLAG = [re.compile(p, re.IGNORECASE) for p in RULE_FLAGS]

# content-coaching red flags (M5A) — the AI must not invent evidence/examples/content.
CONTENT_FLAGS = [
    r"you (?:could|might|should) (?:cite|mention|use the fact|add the example|include the statistic)",
    r"for (?:example|instance),? (?:you could|consider|try)",
    r"consider (?:citing|adding|including|mentioning) (?:the|a|an)",
    r"what if you (?:cited|added|mentioned|used)",
    r"a (?:study|statistic|fact) (?:that|showing|about)",
    r"try (?:citing|adding|using) (?:a|an|the)",
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
PA = "Help the student use evidence and support to serve the essay's purpose."
TASK = "Draft a body paragraph."

# has_evidence: True if the draft contains support that should trigger evidence_function.applies
# (n, category, assignment, draft, has_evidence, teacher_notes)
CASES = [
 # strong evidence, weak interpretation (the classic M8 target)
 (1, "strong_ev_weak_interp", ARG, "Teens check their phones an average of 100 times a day, according to a 2023 study. This proves social media is a problem for friendships.", True, ""),
 (2, "strong_ev_weak_interp", ARG2, "Downtown car trips fell 22% after congestion pricing began, city data shows. So congestion pricing works.", True, ""),
 (3, "strong_ev_weak_interp", ANL, "The narrator repeats the word 'gray' six times in the first page. This shows the mood is gray.", True, ""),
 (4, "strong_ev_weak_interp", EXPL, "Yeast releases carbon dioxide when it feeds on sugar. That is why bread rises. This explains bread.", True, ""),
 # weak evidence, strong interpretation
 (5, "weak_ev_strong_interp", ARG, "I think social media quietly rewires how we value friends — it teaches us to measure closeness in likes rather than time. My cousin once said she felt lonelier the more she posted.", True, ""),
 (6, "weak_ev_strong_interp", ANL, "The empty chair in the corner does enormous work: it makes absence into a presence the reader can't ignore. I noticed it while reading.", True, ""),
 (7, "weak_ev_strong_interp", REF, "Failing taught me that recovery, not perfection, is the real skill. I remember feeling this once after a bad game.", True, ""),
 # persuasive with evidence
 (8, "persuasive", ARG2, "Studies from three cities show reduced downtown driving improves air quality. Air quality matters for public health. Therefore we should reduce car traffic.", True, ""),
 (9, "persuasive", ARG, "A survey found 60% of teens feel pressure to respond instantly to messages. This pressure changes how friendships feel.", True, ""),
 (10, "persuasive", ARG2, "Bike lanes in our neighbor city increased cycling by 40%. That number is impressive. Cities should build more.", True, ""),
 # explanatory with support
 (11, "explanatory", EXPL, "When you flip the switch, current flows through the filament, which heats until it glows. The glowing filament is what produces the light you see.", True, ""),
 (12, "explanatory", EXPL, "A vaccine introduces a harmless fragment of a pathogen. The immune system builds antibodies in response. Later, real exposure meets a prepared defense.", True, ""),
 (13, "explanatory", EXPL, "Interest compounds because each period's interest is added to the principal. The next period then earns interest on a larger base.", True, ""),
 # analytical with textual evidence
 (14, "analytical", ANL, "The poem ends mid-sentence, with a dash instead of a period. The unfinished line leaves the reader suspended in the same uncertainty the speaker feels.", True, ""),
 (15, "analytical", ANL, "In the passage, every sentence about the father is short and clipped, while sentences about the mother run long and looping. The rhythm itself sorts the two parents.", True, ""),
 (16, "analytical", ANL, "The camera lingers on the empty doorway for a full ten seconds. That held shot asks the audience to feel the waiting the character cannot voice.", True, ""),
 # narrative with descriptive evidence
 (17, "narrative", NAR, "She set the tea down without a word. The cup rattled against the saucer, and I understood, before she said anything, that the news was bad.", True, ""),
 (18, "narrative", NAR, "The gym smelled like floor wax and nerves. My sneakers squeaked once, too loud, and the whole row of parents looked up.", True, ""),
 (19, "narrative", NAR, "He kept tying and retying his shoelace at the starting line. When the gun finally went off, he was still kneeling.", True, ""),
 # reflective with experiential evidence
 (20, "reflective", REF, "I keep coming back to the moment I didn't call. The phone was right there. What that silence taught me is still unfolding.", True, ""),
 (21, "reflective", REF, "Volunteering at the shelter, I expected to feel useful. Instead I felt small — and that smallness turned out to be the point.", True, ""),
 (22, "reflective", REF, "The scar on my thumb reminds me of the summer I learned that fixing things and breaking them use the same tools.", True, ""),
 # missing evidence (claim/interpretation but no support yet)
 (23, "missing_evidence", ARG, "Social media is destroying real friendship among teenagers. It is one of the biggest problems of our generation.", False, ""),
 (24, "missing_evidence", ANL, "This poem is clearly about grief and the impossibility of moving on. That is the whole meaning of it.", False, ""),
 (25, "missing_evidence", EXPL, "Photosynthesis is how plants make food. It is a very important process for life on Earth.", False, ""),
 # irrelevant evidence (support present but not connected to purpose)
 (26, "irrelevant_evidence", ARG, "Social media harms teen friendships. The first smartphone was released in 2007. Steve Jobs was a famous CEO. So friendships suffer today.", True, ""),
 (27, "irrelevant_evidence", ARG2, "Cities should reduce car traffic. The Eiffel Tower is 330 meters tall and attracts millions of tourists. Therefore traffic should be reduced.", True, ""),
 # unsupported claims (assertions stacked without grounding)
 (28, "unsupported_claim", ARG, "Everyone knows social media ruins friendships. It obviously makes people fake. It is clearly the worst thing for teens.", False, ""),
 (29, "unsupported_claim", ARG2, "Reducing car traffic is simply the right thing to do. Anyone can see cars are bad. It's just common sense.", False, ""),
 # brainstorming exception (content help enabled — may discuss possible evidence)
 (30, "brainstorm_evidence", ARG, "I want to support my claim that social media weakens close friendships but I don't know what kind of evidence would work.", True, "Brainstorming mode is ON: help the student generate possible kinds of evidence and support before drafting."),
]


def summ(s):
    th = s["theory"]
    ef = th.get("evidence_function", {}) or {}
    iv = s["interactions"][-1]["intervention"]
    return {
        "applies": bool(ef.get("applies")),
        "function": (ef.get("function") or "").strip(),
        "interpretation_gap": (ef.get("interpretation_gap") or "").strip(),
        "forms": ef.get("forms") or [],
        "focus": iv.get("focus", ""),
        "type": iv["type"],
        "student_facing": s["turns"][-1]["content"],
        "cp": (th.get("communicative_purpose", {}) or {}).get("primary", ""),
    }


def main():
    res = []
    for (n, cat, assignment, draft, has_ev, notes) in CASES:
        t0 = time.time()
        try:
            sid = create_session(assignment, PA, TASK, notes)
            s = interact(sid, "writing", draft)
            f = summ(s)
            brainstorm = n == 30
            rf = rflags(f["student_facing"])
            cf = [] if brainstorm else cflags(f["student_facing"])
            focus_ok = (f["focus"] == "content") if brainstorm else (f["focus"] == "writing")
            # when the draft has evidence, evidence_function should apply; missing/unsupported may legitimately not.
            applies_ok = f["applies"] if has_ev else True
            ok = applies_ok and (not rf) and (not cf) and focus_ok
            rec = {"n": n, "category": cat, "has_evidence": has_ev, "brainstorm": brainstorm,
                   "applies": f["applies"], "function": f["function"],
                   "interpretation_gap": f["interpretation_gap"], "forms": f["forms"],
                   "focus": f["focus"], "type": f["type"], "cp": f["cp"],
                   "rule_flags": rf, "content_flags": cf, "ok": ok,
                   "student_facing": f["student_facing"], "elapsed_s": round(time.time() - t0, 1)}
            print(f"case {n} [{cat}] applies={f['applies']} fn='{f['function'][:34]}' focus={f['focus']} rf={rf} cf={cf} ok={ok} {rec['elapsed_s']}s", flush=True)
            res.append(rec)
        except Exception as e:  # noqa: BLE001
            print(f"case {n} FAILED: {e}", flush=True)
            res.append({"n": n, "category": cat, "error": str(e)})
        json.dump(res, open("/app/backend/tests/milestone8_results.json", "w"), indent=2)
    passed = sum(1 for x in res if x.get("ok"))
    print(f"DONE — functional evidence pass {passed}/{len(res)}", flush=True)


if __name__ == "__main__":
    main()
