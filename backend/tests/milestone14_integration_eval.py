"""Milestone 14 — Developmental Integration & Calibration evaluation (30 cases).
Verifies the meta-check: (a) integration_calibration applies every turn with a primary_framework
that ALIGNS with the M11 primary_target, (b) supporting_frameworks reinforce (not compete), (c)
calibration is proportional (strong drafts -> light/stop; weak -> single high-leverage target;
no over/under-teaching), (d) ONE coherent invitation (no duplicate/conflicting asks), (e) similar
samples get consistent priorities, (f) M5A focus='writing'. Categories: multi-framework, conflicting-
priority, similar-pair (consistency), repeated-revision, strong, weak."""
import json
import re
import time
import requests

BASE = "http://localhost:8001/api"

# multiple-target / conflicting-invitation heuristic on the student-facing text (should be ONE ask).
MULTI_ASK = [r"\balso,\s", r"\banother thing\b", r"\bin addition,\s", r"\bsecondly\b",
             r"\btwo things\b", r"\bfirst[,.].*\bsecond[,.]", r"\bat the same time,? (?:try|consider|work)"]
MFLAG = [re.compile(p, re.IGNORECASE) for p in MULTI_ASK]


def mflags(t):
    return [p.pattern for p in MFLAG if p.search(t)]


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


def ic(s):
    th = s["theory"]
    c = th.get("integration_calibration", {}) or {}
    sc = th.get("scaffolding_control", {}) or {}
    iv = s["interactions"][-1]["intervention"]
    return {
        "applies": bool(c.get("applies")),
        "primary_framework": (c.get("primary_framework") or "").strip(),
        "supporting_frameworks": c.get("supporting_frameworks") or [],
        "calibration_check": (c.get("calibration_check") or "").strip(),
        "consistency_check": (c.get("consistency_check") or "").strip(),
        "integration_notes": (c.get("integration_notes") or "").strip(),
        "primary_target": (sc.get("primary_target") or "").strip(),
        "iv_type": iv["type"],
        "focus": iv.get("focus", ""),
        "student_facing": s["turns"][-1]["content"],
    }


ARG = "Argue whether social media improves or harms teen friendships."
ARG2 = "Argue whether your city should reduce car traffic downtown."
EXPL = "Explain how a chosen process or phenomenon works."
ANL = "Analyze how a text or space produces its effect."
REF = "Reflect on what an experience taught you."
PA = "Help the student develop as a writer with one coherent, calibrated focus."
TASK = "Work on your draft."

# (n, category, assignment, drafts(tuple), pair_key or None)
CASES = [
 # multiple applicable frameworks at once (must unify into one focus)
 (1, "multi_framework", ARG, ("social media bad. teens phones. no clear point. sentences dont connect and no evidence and it just stops at the end.",), None),
 (2, "multi_framework", EXPL, ("photosynthesis happens. sun. water. steps unclear. sentences jump around. and the ending trails off with no completion.",), None),
 (3, "multi_framework", ANL, ("the poem has imagery and short lines and a mood and no interpretation and paragraphs that dont connect and a weak ending.",), None),
 (4, "multi_framework", ARG2, ("cars bad. traffic. eiffel tower tall. reduce cars. no thesis, messy order, irrelevant evidence, abrupt conclusion.",), None),
 (5, "multi_framework", REF, ("the trip. it happened. stuff. no meaning drawn out, events out of order, and it ends mid-thought.",), None),
 # conflicting potential priorities (frameworks could pull different ways -> must cooperate, pick one)
 (6, "conflicting_priority", ARG, ("Social media, which was invented after the smartphone in 2007 by companies, harms friendships because it is distracting and also here is a statistic I heard once.",), None),
 (7, "conflicting_priority", ANL, ("The imagery is sad, and the author's biography is interesting, and the poem has good structure, so overall it is a sad and well-made poem about the author's life.",), None),
 (8, "conflicting_priority", EXPL, ("The immune system is complex and vaccines are important and there are many types and it all connects to how the body works in general somehow.",), None),
 (9, "conflicting_priority", ARG2, ("Downtown cars cause pollution, and parking is expensive, and cities are old, and bikes are fun, so traffic should be reduced for these reasons.",), None),
 # similar sample PAIRS (consistency) — equivalent problems should get equivalent priorities
 (10, "similar_pair", ARG, ("My essay is about social media and friendship.",), "topic_announce"),
 (11, "similar_pair", ARG2, ("My essay is about cars and the city downtown.",), "topic_announce"),
 (12, "similar_pair", EXPL, ("This essay is about how the internet works.",), "topic_announce2"),
 (13, "similar_pair", ANL, ("This essay is about the poem and what it means.",), "topic_announce2"),
 (14, "similar_pair", ARG, ("Social media harms friendships because it is distracting, because it is fake, and because it is addictive.",), "three_reason"),
 (15, "similar_pair", ARG2, ("The city should reduce traffic because it is polluting, because it is loud, and because it is crowded.",), "three_reason"),
 (16, "similar_pair", ANL, ("The imagery is significant. It matters. The significance is important.",), "empty_restate"),
 (17, "similar_pair", REF, ("The trip was meaningful. It meant a lot. The meaning stayed.",), "empty_restate"),
 # strong writing (calibration: should NOT over-teach)
 (18, "strong", ARG, ("When a friend likes your post but never texts back, the gesture says everything: presence without contact — the gap that makes online closeness feel thinner than it looks.",), None),
 (19, "strong", ANL, ("The room forces intimacy: chairs bolted in a tight ring, no corner to retreat to, so the design itself decides no one can be a bystander.",), None),
 (20, "strong", EXPL, ("A vaccine works by rehearsal: it shows the immune system a harmless piece of a threat so the real thing meets a body that already knows the face.",), None),
 (21, "strong", REF, ("I trained to avoid mistakes instead of to recover from them, and a game punishes that quietly.",), None),
 # weak writing (calibration: pick ONE high-leverage target, not everything)
 (22, "weak", ARG, ("social media. friends. bad. idk. phones.",), None),
 (23, "weak", EXPL, ("it works. parts. does thing. idk how.",), None),
 (24, "weak", ANL, ("poem. words. mood. deep i guess.",), None),
 (25, "weak", REF, ("trip. happened. felt stuff. the end.",), None),
 # repeated revisions (integration stays coherent across turns; transfer noted, one target)
 (26, "repeated_revision", ARG, ("Social media bad.",
                                 "Social media harms friendship.",
                                 "Social media harms close friendships because it rewards shallow contact over focused attention."), None),
 (27, "repeated_revision", REF, ("The trip changed me.",
                                "The trip changed how I saw home.",
                                "Leaving taught me home was the people who expected me back, not the place."), None),
 (28, "repeated_revision", EXPL, ("Compounding is a money thing.",
                                 "Compounding grows money over time.",
                                 "Compounding grows money because each period's gains earn their own gains."), None),
 # cross-framework transfer (growth in one supports another) at whole-paper scale
 (29, "cross_transfer", ARG, ("Intro sets up that social media harms closeness. Body develops attention vs contact. But the conclusion just restates the three reasons and stops.",), None),
 (30, "cross_transfer", EXPL, ("The intro asks how vaccines work. The body explains rehearsal clearly. The conclusion introduces a brand-new topic about vaccine history and ends abruptly.",), None),
]


def run_case(n, cat, assignment, drafts, pair_key):
    sid = create_session(assignment, PA, TASK)
    last = None
    for i, content in enumerate(drafts):
        s = interact(sid, "writing" if i == 0 else "revise", content)
        last = ic(s)
    applies_ok = last["applies"] and bool(last["primary_framework"]) and bool(last["calibration_check"])
    one_target = bool(last["primary_target"])
    # alignment: primary_framework should not conflict with there being a single primary_target
    mf = mflags(last["student_facing"])
    focus_ok = last["focus"] == "writing"
    ok = applies_ok and one_target and (not mf) and focus_ok
    return {"n": n, "category": cat, "pair_key": pair_key, "turns": len(drafts),
            "applies": last["applies"], "primary_framework": last["primary_framework"][:40],
            "supporting": last["supporting_frameworks"], "calibration_check": last["calibration_check"][:70],
            "consistency_check": last["consistency_check"][:60], "primary_target": last["primary_target"][:44],
            "iv_type": last["iv_type"], "focus": last["focus"], "multi_flags": mf,
            "checks": {"applies_ok": applies_ok, "one_target": one_target, "one_ask": not mf, "focus_ok": focus_ok},
            "ok": ok, "student_facing": last["student_facing"]}


def main():
    res = []
    for c in CASES:
        t0 = time.time()
        try:
            rec = run_case(*c)
            rec["elapsed_s"] = round(time.time() - t0, 1)
            print(f"case {rec['n']} [{rec['category']}] applies={rec['applies']} primary_fw='{rec['primary_framework'][:24]}' sup={len(rec['supporting'])} one_ask={rec['checks']['one_ask']} iv={rec['iv_type']} focus={rec['focus']} ok={rec['ok']} {rec['elapsed_s']}s", flush=True)
            res.append(rec)
        except Exception as e:  # noqa: BLE001
            print(f"case {c[0]} FAILED: {e}", flush=True)
            res.append({"n": c[0], "category": c[1], "error": str(e)})
        json.dump(res, open("/app/backend/tests/milestone14_results.json", "w"), indent=2)
    # consistency: group similar_pair by pair_key and check primary_framework agreement
    pairs = {}
    for x in res:
        if x.get("category") == "similar_pair" and "error" not in x:
            pairs.setdefault(x["pair_key"], []).append(x["primary_framework"].lower())
    consistency = {k: v for k, v in pairs.items()}
    json.dump(consistency, open("/app/backend/tests/milestone14_consistency.json", "w"), indent=2)
    passed = sum(1 for x in res if x.get("ok"))
    print(f"DONE — integration/calibration pass {passed}/{len(res)}", flush=True)
    print(f"CONSISTENCY PAIRS: {json.dumps(consistency)}", flush=True)


if __name__ == "__main__":
    main()
