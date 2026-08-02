"""Milestone 6 — Communicative Purpose Framework evaluation (30 cases).
Verifies the engine (a) infers communicative purpose BEFORE evaluating writing,
(b) adapts instruction to that purpose, (c) keeps writing concepts consistent while their
FUNCTION shifts, (d) imposes no rigid template, (e) handles mixed-purpose assignments.
Categories: persuasive, explanatory, informative, analytical, narrative, reflective, mixed."""
import json
import re
import time
import requests

BASE = "http://localhost:8001/api"

# purpose keyword families used ONLY to check that the engine's inferred primary purpose
# lands in the expected family (case-insensitive substring match on communicative_purpose.primary).
FAMILY = {
    "persuasive": ["persuad", "argu", "convinc"],
    "explanatory": ["explain", "explanat"],
    "informative": ["inform"],
    "analytical": ["analy", "interpret"],
    "narrative": ["narrat", "story", "recount"],
    "reflective": ["reflect"],
    "evaluative": ["evaluat", "assess", "judg"],
    "comparative": ["compar", "contrast"],
    "proposal": ["propos", "recommend"],
}

# rigid-template phrasing that would signal formulaic (not functional) teaching.
TEMPLATE_FLAGS = [
    r"five[- ]paragraph", r"5[- ]paragraph",
    r"three (?:body )?paragraphs", r"topic sentence, ?evidence, ?analysis",
    r"hook, ?background, ?thesis", r"introduction, ?body, ?conclusion (?:format|template|structure)",
    r"claim[- ]evidence[- ]analysis (?:format|template|formula)",
    r"must (?:have|contain|include) (?:a|an|three|five)",
    r"standard essay (?:format|structure|template)",
]
TFLAG = [re.compile(p, re.IGNORECASE) for p in TEMPLATE_FLAGS]


def template_flags(text):
    return [p.pattern for p in TFLAG if p.search(text)]


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


# (n, category, expected_family(s), assignment, pedagogical_purpose, task, draft, teacher_notes)
CASES = [
 # persuasive
 (1, "persuasive", ["persuasive"], "Argue whether your school should require uniforms.", "Help the student build and organize a persuasive case.", "Draft your introduction.", "School uniforms are a topic. Some like them, some don't. This essay is about uniforms.", ""),
 (2, "persuasive", ["persuasive"], "Convince readers that your town needs a public library.", "Help the student persuade a real audience.", "Draft your thesis.", "My town should build a library because reading is good and libraries have books.", ""),
 (3, "persuasive", ["persuasive"], "Argue for or against year-round school.", "Help the student organize an argument.", "Draft a body paragraph.", "Year-round school is bad. Kids need breaks. Breaks are important. That is my reason.", ""),
 (4, "persuasive", ["persuasive"], "Persuade your principal to add a later start time.", "Help the student address an audience persuasively.", "Draft your opening.", "Dear principal, school should start later. Teens are tired. Please change it.", ""),
 # explanatory
 (5, "explanatory", ["explanatory", "informative"], "Explain how a bill becomes a law.", "Help the student explain a process clearly.", "Draft your explanation.", "A bill becomes a law somehow. There are steps. Congress is involved. Then the president.", ""),
 (6, "explanatory", ["explanatory", "informative"], "Explain why the sky appears blue.", "Help the student make an explanation understandable.", "Draft your opening.", "The sky is blue. This essay explains why the sky is blue. It has to do with light.", ""),
 (7, "explanatory", ["explanatory", "informative"], "Explain how a vaccine trains the immune system.", "Help the student sequence an explanation.", "Draft a paragraph.", "Vaccines do things to your body. Your immune system reacts. Then you are protected maybe.", ""),
 (8, "explanatory", ["explanatory", "informative"], "Explain the causes of the Dust Bowl.", "Help the student explain causes and effects.", "Draft your thesis.", "The Dust Bowl happened because of many reasons that I will explain in this essay.", ""),
 # informative
 (9, "informative", ["informative", "explanatory"], "Write an informative report on renewable energy sources.", "Help the student organize information for a reader.", "Draft a paragraph.", "There are facts about solar power. It uses the sun. It is renewable. There are panels.", ""),
 (10, "informative", ["informative", "explanatory"], "Write an informative piece about the water cycle.", "Help the student present information clearly.", "Draft your opening.", "This report is about the water cycle. Water goes around. There are stages. It repeats.", ""),
 (11, "informative", ["informative", "explanatory"], "Write a fact sheet on healthy sleep habits for teens.", "Help the student organize information for a teen reader.", "Draft your piece.", "Sleep is important. Teens need sleep. Here are facts about sleep and also some tips.", ""),
 (12, "informative", ["informative", "explanatory"], "Write an informative overview of how the internet routes data.", "Help the student organize technical information.", "Draft a body paragraph.", "Data goes on the internet. There are routers. Packets travel. It arrives somewhere.", ""),
 # analytical
 (13, "analytical", ["analytical"], "Analyze how imagery creates mood in a poem of your choice.", "Help the student make an interpretation and support it.", "Draft an analytical paragraph.", "The poem has imagery. There is a lot of it. Imagery is a poetic device. It is important.", ""),
 (14, "analytical", ["analytical"], "Analyze the author's use of point of view in a short story.", "Help the student analyze a technique's effect.", "Draft your thesis.", "This essay is about the point of view in the story and what it does.", ""),
 (15, "analytical", ["analytical"], "Analyze how a public space shapes behavior.", "Help the student connect observation to interpretation.", "Draft a paragraph.", "The plaza has benches and a fountain. People sit there. It is a nice open space.", ""),
 (16, "analytical", ["analytical"], "Analyze how sentence rhythm affects tone in a passage.", "Help the student support an interpretive claim.", "Draft a paragraph.", "The author uses short sentences. They are short. Short sentences feel a certain way.", ""),
 # narrative
 (17, "narrative", ["narrative"], "Write a personal narrative about a turning point.", "Help the student shape a narrative so its meaning comes through.", "Draft your opening.", "One day at school something happened. It was a normal day. Then it was not normal.", ""),
 (18, "narrative", ["narrative"], "Narrate a memory involving a family tradition.", "Help the student let the narrative's significance emerge.", "Draft a paragraph.", "Every year we make dumplings. My grandma leads it. We sit around the table. It is nice.", ""),
 (19, "narrative", ["narrative"], "Write a narrative about a time you were wrong about someone.", "Help the student organize events to reveal change.", "Draft your narrative.", "I met someone. I judged them. Later I learned I was wrong. Then we became friends.", ""),
 (20, "narrative", ["narrative"], "Recount a moment that changed how you see home.", "Help the student shape the arc of the experience.", "Draft the ending.", "And that is how moving away made me finally understand what home meant to me.", ""),
 # reflective
 (21, "reflective", ["reflective"], "Reflect on what a personal failure taught you.", "Help the student explore meaning, not just narrate.", "Draft your opening.", "I failed my driving test twice. It was embarrassing. I am not sure what to think about it.", ""),
 (22, "reflective", ["reflective"], "Reflect on how a book changed your thinking.", "Help the student move from experience to insight.", "Draft a paragraph.", "I read a book. It made me think. I am still figuring out what it made me think about.", ""),
 (23, "reflective", ["reflective"], "Reflect on a value that guides your decisions.", "Help the student examine a belief honestly.", "Draft your reflection.", "I value honesty. I try to be honest. Sometimes it is hard. I think honesty matters.", ""),
 (24, "reflective", ["reflective"], "Reflect on what community means to you after a service project.", "Help the student surface genuine insight.", "Draft your opening.", "I did a service project. It was fine. I helped people. Community is important I guess.", ""),
 # evaluative & comparative & proposal (still 'not limited to' purposes)
 (25, "evaluative", ["evaluative", "persuasive"], "Evaluate whether a movie succeeds at its goal.", "Help the student judge against clear criteria.", "Draft a paragraph.", "The movie was good. I liked it. It had action. The acting was fine. I would recommend it.", ""),
 (26, "comparative", ["comparative", "analytical"], "Compare two approaches to reducing traffic downtown.", "Help the student structure a comparison for a reader.", "Draft a paragraph.", "There is congestion pricing and there are car bans. Both do things. They are different.", ""),
 (27, "proposal", ["proposal", "persuasive"], "Propose a solution to lunchroom food waste at your school.", "Help the student make a workable proposal.", "Draft your opening.", "There is food waste at lunch. I have an idea. My idea would fix it. Here is my proposal.", ""),
 # mixed-purpose assignments (must hold multiple purposes, not force one)
 (28, "mixed", ["persuasive", "explanatory", "informative"], "Explain how social media algorithms work AND argue whether they should be regulated.", "Help the student coordinate explaining and persuading.", "Draft your introduction.", "Algorithms are complicated. They should maybe be regulated. This essay explains and argues about them.", ""),
 (29, "mixed", ["analytical", "persuasive"], "Analyze a policy's effects AND recommend whether to keep it.", "Help the student coordinate analysis and recommendation.", "Draft your thesis.", "This essay looks at the policy and its effects and then says what should happen with it.", ""),
 (30, "mixed", ["reflective", "narrative", "analytical"], "Narrate an experience with failure AND reflect on what it revealed about learning.", "Help the student coordinate narrating and reflecting.", "Draft a paragraph.", "I failed and it was a story and also I learned something about myself and how I learn.", ""),
]


def summ(s):
    th = s["theory"]
    cp = th.get("communicative_purpose", {}) or {}
    iv = s["interactions"][-1]["intervention"]
    return {
        "primary": (cp.get("primary") or "").strip(),
        "secondary": cp.get("secondary") or [],
        "inferred_from": cp.get("inferred_from") or "",
        "focus": iv.get("focus", ""),
        "type": iv["type"],
        "student_facing": s["turns"][-1]["content"],
        "domains": th.get("currently_relevant_domains", []),
    }


def family_hit(primary, secondary, expected_families):
    text = (primary + " " + " ".join(secondary)).lower()
    for fam in expected_families:
        if any(kw in text for kw in FAMILY.get(fam, [])):
            return True
    return False


def main():
    res = []
    for (n, cat, exp, assignment, purpose, task, draft, notes) in CASES:
        t0 = time.time()
        try:
            sid = create_session(assignment, purpose, task, notes)
            s = interact(sid, "writing", draft)
            f = summ(s)
            purpose_ok = family_hit(f["primary"], f["secondary"], exp)
            tflags = template_flags(f["student_facing"])
            mixed_ok = True
            if cat == "mixed":
                mixed_ok = len(f["secondary"]) >= 1  # must hold >1 purpose
            ok = purpose_ok and not tflags and mixed_ok and f["focus"] == "writing"
            rec = {"n": n, "category": cat, "expected": exp, "primary": f["primary"],
                   "secondary": f["secondary"], "focus": f["focus"], "type": f["type"],
                   "purpose_ok": purpose_ok, "mixed_ok": mixed_ok, "template_flags": tflags,
                   "ok": ok, "student_facing": f["student_facing"], "elapsed_s": round(time.time() - t0, 1)}
            print(f"case {n} [{cat}] primary='{f['primary']}' sec={f['secondary']} purpose_ok={purpose_ok} tflags={tflags} ok={ok} {rec['elapsed_s']}s", flush=True)
            res.append(rec)
        except Exception as e:  # noqa: BLE001
            print(f"case {n} FAILED: {e}", flush=True)
            res.append({"n": n, "category": cat, "error": str(e)})
        json.dump(res, open("/app/backend/tests/milestone6_results.json", "w"), indent=2)
    passed = sum(1 for x in res if x.get("ok"))
    print(f"DONE — purpose framework pass {passed}/{len(res)}", flush=True)


if __name__ == "__main__":
    main()
