"""Milestone 11 — Recursive Developmental Scaffolding Controller evaluation (30 cases).
Verifies the meta-layer: (a) exactly ONE primary_target selected per turn, (b) other opportunities
postponed (never teaches multiple major concepts at once), (c) an appropriate instructional_mode
chosen, (d) stopping rules honored (cycle_status + stopping_reason), (e) consolidation on real
revisions, (f) no endless recursion across repeated revisions, (g) M5A boundary preserved (focus).
Categories: multiple-weaknesses, needs-explanation, needs-questioning, needs-consolidation (revision),
strong-draft, weak-draft, repeated-revision (multi-turn)."""
import json
import re
import time
import requests

BASE = "http://localhost:8001/api"

MODES = {"developmental_question", "explicit_instruction", "brief_demonstration",
         "guided_revision", "reflection", "consolidation"}
STATUSES = {"continue", "consolidate_and_return", "stop"}

# more-than-one-target heuristic on the student-facing text (should teach ONE thing).
MULTI_ASK = [
    r"\balso,\s", r"\banother thing\b", r"\bin addition,\s", r"\bsecondly\b",
    r"\bas well as\b.*\b(and|also)\b", r"\btwo things\b", r"\bfirst[,.].*\bsecond[,.]",
]
MFLAG = [re.compile(p, re.IGNORECASE) for p in MULTI_ASK]


def multi_flags(t):
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


def sc(s):
    th = s["theory"]
    c = th.get("scaffolding_control", {}) or {}
    iv = s["interactions"][-1]["intervention"]
    return {
        "unit": (c.get("current_unit") or "").strip(),
        "diagnosed": c.get("diagnosed_opportunities") or [],
        "primary": (c.get("primary_target") or "").strip(),
        "rationale": (c.get("prioritization_rationale") or "").strip(),
        "mode": (c.get("instructional_mode") or "").strip(),
        "postponed": c.get("postponed") or [],
        "status": (c.get("cycle_status") or "").strip(),
        "stopping_reason": (c.get("stopping_reason") or "").strip(),
        "future": (c.get("future_opportunity") or "").strip(),
        "iv_type": iv["type"],
        "focus": iv.get("focus", ""),
        "student_facing": s["turns"][-1]["content"],
    }


ARG = "Argue whether social media improves or harms teen friendships."
ARG2 = "Argue whether your city should reduce car traffic downtown."
EXPL = "Explain how a chosen process or phenomenon works."
ANL = "Analyze how a text or space produces its effect."
NAR = "Write a personal narrative about a meaningful experience."
REF = "Reflect on what an experience taught you."
PA = "Help the student develop as a writer, one focused step at a time."
TASK = "Work on your draft."

# (n, category, assignment, draft, teacher_notes, expect_postponed, expect_stop)
CASES = [
 # multiple simultaneous weaknesses -> must pick ONE, postpone others
 (1, "multiple_weaknesses", ARG, "social media bad for friends. teens use phones alot. also my friend sarah she posts alot. in conclusion social media harmful and thats my three reasons distraction and fake and addiction which i will discuss.", "", True, False),
 (2, "multiple_weaknesses", ARG2, "cars are a topic. traffic bad. the eiffel tower is tall. reduce cars. no thesis really and paragraphs are messy and no evidence and the ending just stops.", "", True, False),
 (3, "multiple_weaknesses", EXPL, "photosynthesis. plants green. sun. water somewhere. i think plants are pretty. the steps are unclear and sentences dont connect and theres no real explanation.", "", True, False),
 (4, "multiple_weaknesses", ANL, "the poem has words and imagery and short lines and a mood and the author lived somewhere and its about grief maybe and none of it is organized or interpreted.", "", True, False),
 (5, "multiple_weaknesses", NAR, "one day stuff happened. it was a day. my shoes red. then the end. no scene no significance no order to the events at all really.", "", True, False),
 # students needing EXPLANATION (missing a concept)
 (6, "needs_explanation", ARG, "My essay is about social media and friendship.", "", False, False),
 (7, "needs_explanation", ARG2, "This essay will discuss traffic in the city and cars and stuff about downtown.", "", False, False),
 (8, "needs_explanation", ANL, "This essay is about the poem and what it is about basically.", "", False, False),
 (9, "needs_explanation", EXPL, "I am going to talk about how the internet works in this essay here.", "", False, False),
 # students needing QUESTIONING (capable, close to insight)
 (10, "needs_questioning", ARG, "Social media strengthens weak-tie friendships while quietly eroding the close ones, because it rewards breadth of contact over depth of attention.", "", False, False),
 (11, "needs_questioning", ANL, "The narrator never names the town, and that absence lets any reader lower their own street into the story.", "", False, False),
 (12, "needs_questioning", REF, "I thought forgiveness would feel like relief; it felt more like work — the kind that starts a repair instead of ending one.", "", False, False),
 (13, "needs_questioning", NAR, "The kitchen still smelled like her cigarettes, though she'd quit a year before she left.", "", False, False),
 # strong drafts (little to teach -> honor, consider stop/diminishing returns)
 (14, "strong_draft", ARG, "When a friend likes your post but never texts back, the gesture says everything: presence without contact. That gap is what makes online closeness feel thinner than it looks.", "", False, True),
 (15, "strong_draft", ANL, "The room forces intimacy: the chairs bolted in a tight ring, no corner to retreat to, so the design itself decides no one can be a bystander.", "", False, True),
 (16, "strong_draft", EXPL, "A vaccine works by rehearsal: it shows the immune system a harmless piece of a threat, so the real thing meets a body that already knows the face.", "", False, True),
 (17, "strong_draft", REF, "I trained to avoid mistakes instead of training to recover from them, and a game punishes that quietly.", "", False, True),
 # weak drafts (much to do, still pick one)
 (18, "weak_draft", ARG, "Social media. Friends. Bad. Good. I dont know. Phones.", "", False, False),
 (19, "weak_draft", EXPL, "It works somehow. There are parts. It does the thing. Idk how.", "", False, False),
 (20, "weak_draft", NAR, "we went. it happened. the end. it was a memory i guess.", "", False, False),
 # student requests to continue independently (stopping rule)
 (21, "requests_independence", ARG, "I think I see what to do now — I want to try revising this on my own for a while.", "", False, True),
 (22, "requests_independence", REF, "Got it, that makes sense. Let me take it from here and keep writing myself.", "", False, True),
 # mixed unit sizes (sentence vs whole paper)
 (23, "unit_sentence", ARG, "Social media, which is used by teens who have phones that are expensive and made by companies, harms friendships.", "", False, False),
 (24, "unit_whole_paper", ARG2, "Intro about cars. Body one about pollution. Body two about the printing press. Conclusion restates cars are bad. The whole thing does not hold together.", "", True, False),
 # needs consolidation via REVISION (multi-turn: draft then improved revision)
 (25, "revision_consolidation", ARG, ("My essay is about social media and friendship.",
                                     "Social media weakens close friendships because it trades depth of attention for breadth of contact."), "", False, False),
 (26, "revision_consolidation", ANL, ("This essay is about the poem and grief.",
                                     "By refusing to name the town, the poet makes the grief portable, so the reader carries it as their own."), "", False, False),
 (27, "revision_consolidation", EXPL, ("Photosynthesis is important for plants.",
                                      "Photosynthesis is how a plant turns sunlight, water, and carbon dioxide into the sugar it lives on."), "", False, False),
 # repeated revision (multi-turn x2) -> must NOT keep re-teaching the same target; consolidate/hand back
 (28, "repeated_revision", ARG, ("Social media is bad for friends.",
                                 "Social media harms close friendships because constant contact removes the absences that made return meaningful.",
                                 "Social media harms close friendships because constant contact removes the absences that made return meaningful — when no one is ever gone, no one is quite missed."), "", False, True),
 (29, "repeated_revision", REF, ("The trip changed me.",
                                "The trip changed how I saw home.",
                                "Leaving finally taught me what home had meant — not a place I lived, but the people who expected me back."), "", False, True),
 # brainstorming enabled (controller still picks one focus; mode may differ)
 (30, "brainstorm", ARG, "I have no idea where to start with this essay on social media and friendship.", "Brainstorming mode is ON: help the student explore possible directions before drafting.", False, False),
]


def run_case(n, cat, assignment, draft, notes, expect_postponed, expect_stop):
    sid = create_session(assignment, PA, TASK, notes)
    turns = draft if isinstance(draft, tuple) else (draft,)
    last = None
    primaries = []
    for i, content in enumerate(turns):
        kind = "writing" if i == 0 else "revise"
        s = interact(sid, kind, content)
        last = sc(s)
        primaries.append(last["primary"])
    brainstorm = n == 30
    one_target = bool(last["primary"])
    mode_ok = last["mode"] in MODES
    status_ok = last["status"] in STATUSES
    mf = multi_flags(last["student_facing"])
    postponed_ok = (len(last["postponed"]) >= 1) if expect_postponed else True
    stop_ok = True
    if expect_stop:
        stop_ok = last["status"] in {"stop", "consolidate_and_return"} and (bool(last["stopping_reason"]) or last["status"] == "consolidate_and_return")
    # repeated revision: the final turn should not still be 'continue'-ing the same first target endlessly
    no_recursion_ok = True
    if cat == "repeated_revision":
        no_recursion_ok = last["status"] in {"stop", "consolidate_and_return"} or last["iv_type"] == "consolidate"
    consolidation_ok = True
    if cat in ("revision_consolidation",):
        consolidation_ok = (last["iv_type"] == "consolidate") or ("consolid" in last["mode"]) or (last["status"] in {"consolidate_and_return", "stop"})
    focus_ok = (last["focus"] in {"writing", "content"}) if brainstorm else (last["focus"] == "writing")
    ok = one_target and mode_ok and status_ok and (not mf) and postponed_ok and stop_ok and no_recursion_ok and consolidation_ok and focus_ok
    return {"n": n, "category": cat, "turns": len(turns), "primary": last["primary"],
            "primaries_across_turns": primaries, "mode": last["mode"], "status": last["status"],
            "postponed_count": len(last["postponed"]), "stopping_reason": last["stopping_reason"],
            "iv_type": last["iv_type"], "focus": last["focus"], "multi_flags": mf,
            "checks": {"one_target": one_target, "mode_ok": mode_ok, "status_ok": status_ok,
                       "postponed_ok": postponed_ok, "stop_ok": stop_ok, "no_recursion_ok": no_recursion_ok,
                       "consolidation_ok": consolidation_ok, "focus_ok": focus_ok},
            "ok": ok, "student_facing": last["student_facing"]}


def main():
    res = []
    for c in CASES:
        t0 = time.time()
        try:
            rec = run_case(*c)
            rec["elapsed_s"] = round(time.time() - t0, 1)
            print(f"case {rec['n']} [{rec['category']}] target='{rec['primary'][:30]}' mode={rec['mode']} status={rec['status']} postp={rec['postponed_count']} ok={rec['ok']} {rec['elapsed_s']}s", flush=True)
            res.append(rec)
        except Exception as e:  # noqa: BLE001
            print(f"case {c[0]} FAILED: {e}", flush=True)
            res.append({"n": c[0], "category": c[1], "error": str(e)})
        json.dump(res, open("/app/backend/tests/milestone11_results.json", "w"), indent=2)
    passed = sum(1 for x in res if x.get("ok"))
    print(f"DONE — scaffolding controller pass {passed}/{len(res)}", flush=True)


if __name__ == "__main__":
    main()
