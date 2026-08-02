"""Phase IIIA — Targeted verification of Finding F1.

Does the engine wrongly assume an essay / body-paragraph context when a strong,
COMPLETE, self-contained paragraph is submitted (esp. when the assignment signals
single-paragraph scope)? OBSERVATION ONLY — no architecture/prompt changes.

Runs 10 authentic sessions (strong writers, self-contained paragraphs, all genres;
several explicitly NOT part of a larger essay). Uses the durable-processing API.
"""
import json
import re
import time
import requests

BASE = "http://localhost:8001/api"
PA = "Develop this student as a writer with one coherent, calibrated focus per turn."
OUT = "/app/test_reports/phase3a_scope_transcripts.json"

# phrases that reveal the engine ASSUMED a larger essay / more paragraphs to come
ESSAY_ASSUME = [
    "body paragraph", "first body", "next paragraph", "next section", "the essay",
    "into the body", "each paragraph", "following paragraph", "rest of the essay",
    "develop the essay", "your essay", "subsequent paragraph", "additional paragraph",
    "more paragraphs", "the introduction", "your intro", "as an intro",
]
# phrases showing it recognized completeness / clarified scope / offered a stop
SCOPE_OR_STOP = [
    "self-contained", "standalone", "as a complete", "already complete", "complete as",
    "what scope", "intend this", "intended length", "is this the whole", "the whole piece",
    "on its own", "as a single paragraph", "if this is meant to stand alone",
    "nothing more is needed", "you may be done", "hand it back", "your call",
    "do you intend", "is this finished", "consider it complete",
]
ESSAY_RE = [re.compile(re.escape(p), re.IGNORECASE) for p in ESSAY_ASSUME]
STOP_RE = [re.compile(re.escape(p), re.IGNORECASE) for p in SCOPE_OR_STOP]


def flags(text):
    ea = sorted({p.pattern for p in ESSAY_RE if p.search(text)})
    ss = sorted({p.pattern for p in STOP_RE if p.search(text)})
    return ea, ss


def create_session(a, t):
    r = requests.post(f"{BASE}/sessions", json={"assignment": a, "pedagogical_purpose": PA, "current_writing_task": t}, timeout=30)
    r.raise_for_status()
    return r.json()["id"]


def interact(sid, kind, content, max_wait=260):
    requests.post(f"{BASE}/sessions/{sid}/interact", json={"kind": kind, "content": content}, timeout=30).raise_for_status()
    t0 = time.time()
    while time.time() - t0 < max_wait:
        time.sleep(5)
        s = requests.get(f"{BASE}/sessions/{sid}", timeout=30).json()
        ai = [x for x in s["turns"] if x["role"] == "ai"]
        if ai and ai[-1]["status"] == "complete":
            return s, round(time.time() - t0)
        if ai and ai[-1]["status"] == "failed":
            raise RuntimeError("turn failed")
    raise TimeoutError("no completion")


def extract(s):
    th = s["theory"]
    sc = th.get("scaffolding_control", {}) or {}
    iv = s["interactions"][-1]["intervention"]
    ai = [t for t in s["turns"] if t["role"] == "ai"][-1]["content"]
    target = sc.get("primary_target", "")
    ea_t, ss_t = flags(target + " || " + ai)
    return {
        "ai_invitation": ai,
        "primary_target": target,
        "instructional_mode": sc.get("instructional_mode", ""),
        "cycle_status": sc.get("cycle_status", ""),
        "stopping_reason": sc.get("stopping_reason", ""),
        "iv_type": iv.get("type", ""),
        "iv_focus": iv.get("focus", ""),
        "ic_primary_framework": (th.get("integration_calibration", {}) or {}).get("primary_framework", ""),
        "essay_assume_flags": ea_t,
        "scope_or_stop_flags": ss_t,
        "F1_recurs": bool(ea_t) and not ss_t,  # assumed essay scope AND no scope/stop move
    }


# (id, paragraph_type, scope_signal, assignment, task, turns[(kind,content)])
SESSIONS = [
    ("S1_arg_explicit", "argument", "explicit single-paragraph",
     "Write ONE self-contained paragraph (not an essay) arguing a single idea. This paragraph is the whole assignment.",
     "Write your paragraph.",
     [("writing", "A library fine is a strange kind of punishment: it charges the people who returned the book late but still returned it, while doing nothing about the ones who never bring books back at all. If the goal is to get books circulating, fines aim at the wrong target — they nudge the already-conscientious and shrug at the truly careless. Dropping them, as many libraries now have, doesn't reward irresponsibility; it just stops pretending that a few cents a day was ever the thing holding the collection together.")]),
    ("S2_reflective_explicit", "reflective", "explicit single-paragraph",
     "In a single, complete paragraph, reflect on something small that changed how you think. One paragraph only.",
     "Write your reflection.",
     [("writing", "I used to think patience was a kind of waiting, until I spent a summer teaching my grandmother to text. She'd hunt for each letter, apologize, start over. What I felt wasn't waiting; it was the slow embarrassment of realizing how fast I expected the world to move, and how rarely I'd extended to anyone the room she was asking for. Patience, it turned out, wasn't doing nothing. It was staying present while someone else caught up, without making them feel the cost of it.")]),
    ("S3_analytical_explicit", "analytical", "explicit single-paragraph",
     "Write one self-contained analytical paragraph. It is not part of a larger essay.",
     "Write your analysis.",
     [("writing", "The diner's fluorescent light in Hopper's 'Nighthawks' does the opposite of what light usually does in a painting: instead of warming the scene, it exposes it. The glass wraps the four figures in a bright box with no visible door, so the very thing that lets us see them is what seals them off from the dark street. Hopper makes brightness feel like isolation — the couple sit inches apart and look nowhere, lit up and unreachable, as if being seen and being alone had become the same condition.")]),
    ("S4_explanatory_explicit", "explanatory", "explicit single-paragraph",
     "Explain one idea clearly in a single paragraph for a general reader. One paragraph is the complete task.",
     "Write your explanation.",
     [("writing", "Noise-cancelling headphones don't block sound so much as answer it. A tiny microphone listens to the low hum around you — an engine, a fan — and the headphones instantly generate a matching wave that is its exact opposite: where the incoming wave pushes, the new one pulls. The two collide and flatten each other before they reach your ear, which is why the effect works best on steady drones and barely touches sudden, irregular sounds like a voice. You aren't hearing silence; you're hearing two noises cancel to almost nothing.")]),
    ("S5_narrative_explicit", "narrative", "explicit single-paragraph (flash)",
     "Write a single complete paragraph of flash narrative. It stands on its own.",
     "Write your narrative.",
     [("writing", "The last day of the pool's season, the lifeguard let us stay past closing while she coiled the ropes. We floated on our backs in water going gray with dusk, not talking, listening to the filter tick down. Someone's radio played a song none of us would remember by name but all of us would recognize for years, the way you recognize a smell from a house you no longer live in. Then the underwater lights clicked off, and we climbed out into a summer that was, though we didn't say it, already over.")]),
    ("S6_arg_noscope", "argument", "no scope hint",
     "Argue a single idea.",
     "Write your paragraph.",
     [("writing", "Ranking hospitals by patient-satisfaction scores sounds fair until you notice what it actually rewards: the hospitals that make sick people comfortable, not the ones that make them well. A patient who leaves annoyed but alive rates their care lower than one who was pampered through a minor stay. Tie funding to those scores and you quietly pressure doctors to prescribe the pleasant thing over the necessary one — to treat the survey instead of the illness.")]),
    ("S7_analytical_noscope", "analytical", "no scope hint",
     "Analyze how something creates its effect.",
     "Write your analysis.",
     [("writing", "A grocery store hides its staples — milk, eggs, bread — along the very back wall, and this is not laziness but design. To reach the things you actually came for, you must walk past everything you didn't, and the store bets, correctly, that proximity will do the persuading. The layout turns a short errand into a long corridor of small temptations, so the map of the store is really a map of how attention decays over distance.")]),
    ("S8_explanatory_mild", "explanatory", "mild ('a paragraph')",
     "Write a paragraph explaining a concept to a curious reader.",
     "Write your paragraph.",
     [("writing", "Compound interest feels like magic mostly because our intuition is built for addition, not multiplication. If you add the same amount every year, growth is a straight line; but interest pays you on your interest, so each year's gain is slightly larger than the last, and the line quietly bends upward. Over a few years the difference is boring. Over forty, it's the difference between a modest sum and a life-changing one — which is why the most valuable ingredient isn't the rate, it's the time.")]),
    ("S9_reflective_revise", "reflective", "explicit single-paragraph + revision (stopping check)",
     "Write a single self-contained reflective paragraph. Not an essay.",
     "Write your reflection.",
     [("writing", "Learning to sail taught me that control and steering are not the same thing. You cannot make the wind do anything; you can only decide how to meet it. For a while that felt like a loss. Later it felt like the only honest way anything works."),
      ("writing", "Learning to sail taught me that control and steering are not the same thing. You can't command the wind, only choose the angle at which you meet it — and the boat moves not despite the resistance but because of it. For a while that felt like defeat, like admitting I was at the mercy of something bigger. Now it feels less like surrender than like literacy: the wind was always going to have its say, and the skill was never silencing it, only learning to read it well enough to go somewhere anyway.")]),
    ("S10_arg_revise", "argument", "explicit single-paragraph + revision (stopping check)",
     "Write ONE complete paragraph arguing a position. This paragraph is the entire piece.",
     "Write your paragraph.",
     [("writing", "Autocorrect makes us worse spellers by making spelling feel unnecessary. When every mistake is fixed before we notice it, we stop building the memory that catches the next one. The convenience is real, but so is the quiet erosion underneath it."),
      ("writing", "Autocorrect makes us worse spellers precisely because it works so well. Every error it silently repairs is an error we never have to notice, and noticing is how the memory that prevents the next mistake gets built. The tool doesn't just fix the word in front of us; it removes the small, useful friction that used to teach us. The convenience is genuine — but it's the kind that quietly bills us later, in a skill we stopped practicing without ever deciding to.")]),
]


def run():
    results = []
    for sid_name, ptype, scope, assignment, task, turns in SESSIONS:
        sid = create_session(assignment, task)
        cycles = []
        print(f"\n=== {sid_name} [{ptype}] scope={scope} ===", flush=True)
        try:
            for i, (kind, content) in enumerate(turns):
                s, secs = interact(sid, kind, content)
                ex = extract(s)
                cycles.append({"turn": i + 1, "kind": kind, "student": content, "elapsed_s": secs, **ex})
                print(f"  t{i+1} {secs}s | target='{ex['primary_target'][:60]}'", flush=True)
                print(f"     iv={ex['iv_type']} cycle={ex['cycle_status']} stop='{ex['stopping_reason'][:30]}' | essay_flags={ex['essay_assume_flags']} scope/stop={ex['scope_or_stop_flags']} | F1_recurs={ex['F1_recurs']}", flush=True)
                print(f"     INVITE: {ex['ai_invitation'][:200]}", flush=True)
        except Exception as e:  # noqa: BLE001
            print(f"  ERROR: {e}", flush=True)
            cycles.append({"error": str(e)})
        results.append({"id": sid_name, "paragraph_type": ptype, "scope_signal": scope,
                        "assignment": assignment, "session_id": sid, "cycles": cycles})
        json.dump(results, open(OUT, "w"), indent=2)

    # recurrence stats (turn 1 of each session = the fresh complete-paragraph judgment)
    t1 = [r["cycles"][0] for r in results if r["cycles"] and "error" not in r["cycles"][0]]
    recur = [r for r in t1 if r.get("F1_recurs")]
    print(f"\n=== F1 RECURRENCE (turn 1, complete paragraph): {len(recur)}/{len(t1)} sessions assumed essay scope with no scope/stop move ===", flush=True)
    for r in recur:
        print(f"  RECUR: target='{r['primary_target'][:70]}' flags={r['essay_assume_flags']}", flush=True)
    print(f"DONE — wrote {OUT}", flush=True)


if __name__ == "__main__":
    run()
