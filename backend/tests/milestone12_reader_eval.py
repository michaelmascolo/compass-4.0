"""Milestone 12 — Reader Construction Framework evaluation (30 cases).
Verifies the engine (a) builds a reader model (applies + reader_understanding) whenever text exists,
(b) identifies likely misunderstandings (assumed_knowledge / precision_risk / elaboration_needed
populated in the relevant cases), (c) treats elaboration/precision as reader-understanding (not
word-count/grammar), (d) still selects ONE target via M11 (scaffolding_control.primary_target),
(e) preserves M5A (never invents content; focus='writing'), (f) reader model EVOLVES across turns.
Categories: clear, hidden-assumption, missing-background, inferential-gap, abrupt-shift,
excessive-elaboration, insufficient-elaboration, ambiguous, precise, strong-guidance, evolving(multi-turn)."""
import json
import re
import time
import requests

BASE = "http://localhost:8001/api"

# content-coaching red flags (M5A) — the AI must not invent content/evidence/examples.
CONTENT_FLAGS = [
    r"you (?:could|might|should) add (?:a|an|the|another) (?:point|idea|argument|reason|example|fact)",
    r"another (?:reason|argument|point|idea|example|fact)",
    r"consider (?:adding|including|mentioning) (?:the|a|an)",
    r"for example,? you could",
    r"what(?:'s| is| are)?\s+(?:really\s+)?at stake",
    r"try adding (?:a|an|the)",
]
CFLAG = [re.compile(p, re.IGNORECASE) for p in CONTENT_FLAGS]
# grammar-correctness phrasing precision should NOT reduce to.
GRAMMAR_FLAGS = [
    r"grammatically (?:correct|incorrect)", r"fix the grammar", r"comma splice", r"subject[- ]verb agreement",
    r"punctuation error", r"spelling", r"correct the tense",
]
GFLAG = [re.compile(p, re.IGNORECASE) for p in GRAMMAR_FLAGS]


def cflags(t):
    return [p.pattern for p in CFLAG if p.search(t)]


def gflags(t):
    return [p.pattern for p in GFLAG if p.search(t)]


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


def rc(s):
    th = s["theory"]
    r = th.get("reader_construction", {}) or {}
    sc = th.get("scaffolding_control", {}) or {}
    iv = s["interactions"][-1]["intervention"]
    return {
        "applies": bool(r.get("applies")),
        "reader_understanding": (r.get("reader_understanding") or "").strip(),
        "likely_questions": r.get("likely_reader_questions") or [],
        "assumed_knowledge": (r.get("assumed_knowledge") or "").strip(),
        "clarification_needed": (r.get("clarification_needed") or "").strip(),
        "elaboration_needed": (r.get("elaboration_needed") or "").strip(),
        "precision_risk": (r.get("precision_risk") or "").strip(),
        "next_reader_need": (r.get("next_reader_need") or "").strip(),
        "primary_target": (sc.get("primary_target") or "").strip(),
        "focus": iv.get("focus", ""),
        "student_facing": s["turns"][-1]["content"],
    }


ARG = "Argue whether social media improves or harms teen friendships."
EXPL = "Explain how a chosen process or phenomenon works."
ANL = "Analyze how a text or space produces its effect."
NAR = "Write a personal narrative about a meaningful experience."
REF = "Reflect on what an experience taught you."
PA = "Help the student communicate clearly to a reader who knows only what the text has said."
TASK = "Work on your draft."

# expects: 'assumed' -> assumed_knowledge should be non-empty; 'precision' -> precision_risk;
# 'elaboration' -> elaboration_needed; 'clean' -> reader_understanding positive (no fabricated confusion required)
# (n, category, assignment, draft, expects)
CASES = [
 # clear writing
 (1, "clear", ARG, "Social media harms close friendships because it rewards constant, shallow contact over the rare, focused attention that deep friendship needs.", "clean"),
 (2, "clear", EXPL, "A vaccine works by rehearsal: it shows the immune system a harmless piece of a threat so the body can recognize the real thing quickly.", "clean"),
 (3, "clear", NAR, "The bus pulled away as I reached the corner, and I stood in the rain realizing no one was expecting me anywhere.", "clean"),
 # hidden assumptions (writer assumes knowledge not communicated)
 (4, "hidden_assumption", ANL, "As everyone knows, the green light obviously symbolizes what Gatsby was reaching for, which proves the novel's whole point about America.", "assumed"),
 (5, "hidden_assumption", ARG, "Because of the well-known network effect, it's clear that quitting social media is basically impossible for teens today.", "assumed"),
 (6, "hidden_assumption", EXPL, "Since compounding works the way it does, obviously starting to invest early is the only rational choice.", "assumed"),
 # missing background (reader lacks needed context)
 (7, "missing_background", EXPL, "The Krebs cycle then feeds the electron transport chain, which is where most of the ATP finally gets produced in the mitochondria.", "assumed"),
 (8, "missing_background", ANL, "The volta shifts everything, and after it the sonnet's argument turns against itself in the final couplet.", "assumed"),
 (9, "missing_background", ARG, "Given Dunbar's number, teens simply cannot maintain the hundreds of connections that these platforms encourage.", "assumed"),
 # inferential gaps (jumps a step the reader can't fill)
 (10, "inferential_gap", ARG, "Teens check their phones constantly. Therefore, they no longer value their close friends.", "elaboration"),
 (11, "inferential_gap", EXPL, "The water heats up. So the town's whole ecosystem changes within a season.", "elaboration"),
 (12, "inferential_gap", ANL, "The author uses short sentences. This means the story is fundamentally about grief.", "elaboration"),
 # abrupt topic shifts (reader loses the thread)
 (13, "abrupt_shift", ARG, "Social media reduces face-to-face time. The printing press was invented in the 1400s. Anyway, friendships suffer.", "elaboration"),
 (14, "abrupt_shift", EXPL, "First the yeast ferments the dough. Mount Everest is very tall. Then the bread bakes.", "elaboration"),
 (15, "abrupt_shift", REF, "I was nervous before the recital. Tigers are endangered. After it, I felt different about failure.", "elaboration"),
 # excessive elaboration (over-explains what the reader already gets)
 (16, "excessive_elaboration", ARG, "Social media is used on phones. Phones are devices. Devices are things you hold. You hold them in your hands. Your hands have fingers. Anyway, social media affects friendship.", "clean"),
 (17, "excessive_elaboration", NAR, "I walked to the door. The door was a door. Doors open and close. This door could open. I opened the door that opens. Then I went through the open door.", "clean"),
 # insufficient elaboration (states meaning without helping reader understand)
 (18, "insufficient_elaboration", ANL, "The imagery is significant. It matters a lot. The significance is important to the poem.", "elaboration"),
 (19, "insufficient_elaboration", REF, "The trip was meaningful. It really meant something. The meaning stayed with me.", "elaboration"),
 (20, "insufficient_elaboration", EXPL, "The process is complex. There are many parts. It all works together somehow.", "elaboration"),
 # ambiguous wording (reader could read it two ways)
 (21, "ambiguous", ARG, "Social media makes people feel connected, which is the problem.", "precision"),
 (22, "ambiguous", ANL, "The narrator's cold description of the funeral shows how he really felt.", "precision"),
 (23, "ambiguous", NAR, "After I told my brother the truth about the money, he never spoke to her again.", "precision"),
 (24, "ambiguous", EXPL, "When the cell divides, it copies it, and then it sends it to the other one.", "precision"),
 # precise writing (should be honored, not 'corrected')
 (25, "precise", ARG, "Social media strengthens acquaintanceships while weakening intimate friendships, because it optimizes for the breadth of contact rather than its depth.", "clean"),
 (26, "precise", ANL, "By withholding the narrator's name until the final line, the story keeps the reader uncertain whether to trust him — and that uncertainty is the point.", "clean"),
 # strong reader guidance (writer anticipates reader needs well)
 (27, "strong_guidance", EXPL, "Before explaining how routers work, it helps to picture the internet as a postal system: every message is broken into labeled envelopes. With that image in mind, a router is simply the sorting office.", "clean"),
 (28, "strong_guidance", ARG, "You might expect that more contact means closer friends. This essay argues the opposite — and to see why, we first need to separate 'contact' from 'attention'.", "clean"),
 # evolving reader model across turns (multi-turn)
 (29, "evolving", EXPL, ("Photosynthesis is how plants make food.",
                          "Photosynthesis is how plants make food. Inside the leaf, chloroplasts capture sunlight and use it to combine water and carbon dioxide into sugar, releasing oxygen as a byproduct."), "clean"),
 (30, "evolving", ARG, ("Social media harms friendship.",
                         "Social media harms friendship. Specifically, by rewarding quick reactions over sustained attention, it trains teens to maintain many shallow ties instead of a few deep ones."), "clean"),
]


def run_case(n, cat, assignment, draft, expects):
    sid = create_session(assignment, PA, TASK)
    turns = draft if isinstance(draft, tuple) else (draft,)
    snaps = []
    last = None
    for i, content in enumerate(turns):
        s = interact(sid, "writing" if i == 0 else "revise", content)
        last = rc(s)
        snaps.append({"reader_understanding": last["reader_understanding"], "next_reader_need": last["next_reader_need"]})
    applies_ok = last["applies"] and bool(last["reader_understanding"])
    one_target = bool(last["primary_target"])
    cf = cflags(last["student_facing"])
    gf = gflags(last["student_facing"])
    focus_ok = last["focus"] == "writing"
    expect_ok = True
    if expects == "assumed":
        expect_ok = bool(last["assumed_knowledge"])
    elif expects == "precision":
        expect_ok = bool(last["precision_risk"])
    elif expects == "elaboration":
        expect_ok = bool(last["elaboration_needed"]) or bool(last["clarification_needed"])
    # evolving: reader model should change between turns
    evolve_ok = True
    if cat == "evolving":
        evolve_ok = snaps[0]["reader_understanding"] != snaps[-1]["reader_understanding"]
    ok = applies_ok and one_target and (not cf) and (not gf) and focus_ok and expect_ok and evolve_ok
    return {"n": n, "category": cat, "turns": len(turns), "applies": last["applies"],
            "reader_understanding": last["reader_understanding"][:80], "assumed_knowledge": last["assumed_knowledge"][:60],
            "precision_risk": last["precision_risk"][:60], "elaboration_needed": last["elaboration_needed"][:60],
            "next_reader_need": last["next_reader_need"][:60], "primary_target": last["primary_target"][:50],
            "focus": last["focus"], "content_flags": cf, "grammar_flags": gf,
            "checks": {"applies_ok": applies_ok, "one_target": one_target, "focus_ok": focus_ok,
                       "expect_ok": expect_ok, "evolve_ok": evolve_ok},
            "ok": ok, "snaps": snaps, "student_facing": last["student_facing"]}


def main():
    res = []
    for c in CASES:
        t0 = time.time()
        try:
            rec = run_case(*c)
            rec["elapsed_s"] = round(time.time() - t0, 1)
            print(f"case {rec['n']} [{rec['category']}] applies={rec['applies']} target='{rec['primary_target'][:26]}' expect_ok={rec['checks']['expect_ok']} focus={rec['focus']} cf={rec['content_flags']} gf={rec['grammar_flags']} ok={rec['ok']} {rec['elapsed_s']}s", flush=True)
            res.append(rec)
        except Exception as e:  # noqa: BLE001
            print(f"case {c[0]} FAILED: {e}", flush=True)
            res.append({"n": c[0], "category": c[1], "error": str(e)})
        json.dump(res, open("/app/backend/tests/milestone12_results.json", "w"), indent=2)
    passed = sum(1 for x in res if x.get("ok"))
    print(f"DONE — reader construction pass {passed}/{len(res)}", flush=True)


if __name__ == "__main__":
    main()
