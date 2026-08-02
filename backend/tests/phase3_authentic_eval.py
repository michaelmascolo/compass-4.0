"""Phase III — Authentic Instructional Testing & Calibration.

Runs multi-turn instructional sessions with AUTHENTIC student writing (varied
levels, ages, genres, purposes) through real revision cycles against the LIVE
engine, and records the full transcript + the engine's internal reasoning for
qualitative evaluation. NO architecture changes — observation only.

Uses the durable-processing API: POST /interact returns immediately with a
'processing' placeholder; we poll GET /sessions/{id} until the AI turn resolves.
"""
import json
import time
import requests

BASE = "http://localhost:8001/api"
PA = "Develop this student as a writer with one coherent, calibrated focus per turn."
OUT = "/app/test_reports/phase3_transcripts.json"


def create_session(assignment, task, notes=""):
    r = requests.post(f"{BASE}/sessions", json={
        "assignment": assignment, "pedagogical_purpose": PA,
        "current_writing_task": task, "teacher_notes": notes}, timeout=30)
    r.raise_for_status()
    return r.json()["id"]


def interact(sid, kind, content, max_wait=260):
    r = requests.post(f"{BASE}/sessions/{sid}/interact",
                      json={"kind": kind, "content": content}, timeout=30)
    r.raise_for_status()
    t0 = time.time()
    while time.time() - t0 < max_wait:
        time.sleep(5)
        s = requests.get(f"{BASE}/sessions/{sid}", timeout=30).json()
        ai = [t for t in s["turns"] if t["role"] == "ai"]
        if ai and ai[-1]["status"] == "complete":
            return s, round(time.time() - t0, 0)
        if ai and ai[-1]["status"] == "failed":
            raise RuntimeError(f"turn failed after {round(time.time()-t0)}s")
    raise TimeoutError(f"turn did not complete in {max_wait}s")


def extract(s):
    th = s["theory"]
    sc = th.get("scaffolding_control", {}) or {}
    ic = th.get("integration_calibration", {}) or {}
    rc = th.get("reader_construction", {}) or {}
    rd = th.get("revision_development", {}) or {}
    cp = th.get("communicative_purpose", {}) or {}
    iv = s["interactions"][-1]["intervention"]
    ai_turn = [t for t in s["turns"] if t["role"] == "ai"][-1]
    return {
        "ai_invitation": ai_turn["content"],
        "purpose_primary": cp.get("primary", ""),
        "purpose_secondary": cp.get("secondary", []),
        "primary_target": sc.get("primary_target", ""),
        "instructional_mode": sc.get("instructional_mode", ""),
        "postponed": sc.get("postponed", []),
        "cycle_status": sc.get("cycle_status", ""),
        "stopping_reason": sc.get("stopping_reason", ""),
        "ic_primary_framework": ic.get("primary_framework", ""),
        "ic_supporting": ic.get("supporting_frameworks", []),
        "ic_calibration_check": ic.get("calibration_check", ""),
        "ic_consistency_check": ic.get("consistency_check", ""),
        "iv_type": iv.get("type", ""),
        "iv_focus": iv.get("focus", ""),
        "iv_cultural_resource": iv.get("cultural_resource", ""),
        "iv_writing_not_content_check": iv.get("writing_not_content_check", ""),
        "reader_applies": rc.get("applies", False),
        "reader_next_need": rc.get("next_reader_need", ""),
        "revision_applies": rd.get("applies", False),
        "revision_growth": rd.get("primary_growth", ""),
        "revision_remaining": rd.get("remaining_opportunity", ""),
        "revision_transfer": rd.get("transfer_message", ""),
    }


# ---------------------------------------------------------------------------
# Authentic test set — realistic student voices across levels/ages/genres,
# each a multi-turn revision cycle. `special` documents the scenario probed.
# Each turn: (kind, content). First turn kind='writing'; later 'revise'/'answer'.
# ---------------------------------------------------------------------------
SESSIONS = [
    {
        "id": "P1_ms_weak_argument",
        "profile": "Middle school (grade 7), weak writer, argument",
        "assignment": "Should phones be allowed in school? Write to convince your principal.",
        "task": "Write your argument.",
        "special": "very weak fragmented draft; turn2 = compliance-style minimal revision; turn3 = unexpected/off-target revision",
        "turns": [
            ("writing", "Phones should be aloud in school. Because there fun and you can text your mom. Also games. My teacher takes them and its not fair. Phones are good."),
            ("revise", "Phones should be allowed in school because there fun and you can text your mom if there is a emergency. Also you can play games at lunch. My teacher takes them and its not fair. Phones are good and helpful."),
            ("revise", "I think phones should be allowed. Here is a story. One time my friend got hurt and I called my mom on my phone. So phones help in emergencies. Thats my reason."),
        ],
    },
    {
        "id": "P2_ms_avg_narrative",
        "profile": "Middle school (grade 8), average writer, personal narrative",
        "assignment": "Write a personal narrative about a time something didn't go as planned.",
        "task": "Draft your narrative.",
        "special": "narrative purpose must NOT be forced into claim-evidence; meaning-making focus",
        "turns": [
            ("writing", "The day of the science fair everything went wrong. I woke up late. Then my volcano broke in the car. When I got there my poster fell off the board. The judges came and I was so nervous. I dont really remember what I said. Then it was over and I went home."),
            ("revise", "The day of the science fair everything went wrong. I woke up late because my alarm didnt go off. In the car my volcano cracked and blue goo leaked on the seat. My mom was mad. When I got to school my poster fell off the board twice. The judges came over and I froze. I mumbled something about baking soda. Then it was over. On the way home I felt like a failure but my mom said at least I showed up."),
            ("revise", "The day of the science fair everything went wrong. My alarm never went off, so I woke up late with my heart already pounding. In the car my volcano cracked and blue goo leaked across the seat while my mom sighed. At school my poster kept falling off the board like it didnt want to be seen either. When the judges came I froze and mumbled about baking soda and vinegar. It was over in two minutes. On the way home I felt like a failure, but my mom said showing up scared is braver than staying home. I think she was right, even though I still didnt want to talk about it."),
        ],
    },
    {
        "id": "P3_hs_avg_explanatory",
        "profile": "High school (grade 10), average writer, explanatory",
        "assignment": "Explain how vaccines work to a reader who knows nothing about biology.",
        "task": "Write your explanation.",
        "special": "reader construction is central (naive reader); no invented facts",
        "turns": [
            ("writing", "Vaccines work by using your immune system. They put a weak version of a germ in your body. Then your body makes antibodies. So next time you dont get sick. Thats basically how vaccines work."),
            ("revise", "Vaccines work with your immune system, which is the part of your body that fights germs. A vaccine puts a weak or dead version of a germ into your body. Your body sees it and makes antibodies, which are like tiny soldiers. The antibodies remember the germ. So if the real germ comes later, your body already knows how to fight it and you dont get sick."),
            ("answer", "I wasnt sure if a reader would know what an antibody actually is or how the body remembers. I was trying to make it simple with the soldier idea."),
        ],
    },
    {
        "id": "P4_hs_strong_analytical",
        "profile": "High school (grade 12), strong writer, literary analysis",
        "assignment": "Analyze how a poem creates its emotional effect.",
        "task": "Write your analysis.",
        "special": "strong draft; interpretation gap vs. more evidence; should not over-teach",
        "turns": [
            ("writing", "In 'Those Winter Sundays,' Hayden builds guilt through cold. The father wakes 'in the blueblack cold' and 'with cracked hands that ached.' The speaker 'spoke indifferently to him.' The repeated cold imagery makes the fathers love feel invisible, like the boy only understands it now, looking back. The last lines, 'What did I know of loves austere and lonely offices,' turn the poem into a confession."),
            ("revise", "In 'Those Winter Sundays,' Hayden builds a quiet guilt through images of cold and labor. The father wakes 'in the blueblack cold' and works 'with cracked hands that ached from labor.' No one thanks him. The speaker admits he 'spoke indifferently to him,' and the flat word 'indifferently' shows how ordinary the neglect was. By ending with the question 'What did I know, what did I know / of loves austere and lonely offices,' Hayden makes the poem a confession spoken across time — the adult finally naming a love the child could not see."),
        ],
    },
    {
        "id": "P5_college_strong_argument_nearperfect",
        "profile": "College freshman, strong writer, argument (near-perfect)",
        "assignment": "Argue a position on whether universities should require standardized tests.",
        "task": "Draft your argument.",
        "special": "almost-perfect writing; repeated revisions; system should stop/consolidate not invent problems",
        "turns": [
            ("writing", "Universities should stop requiring standardized tests, not because the tests measure nothing, but because they measure the wrong thing at the wrong moment. A single Saturday morning cannot capture four years of intellectual growth, yet it disproportionately shapes admissions. Worse, the scores track family income more faithfully than they track future performance, quietly converting a supposed meritocracy into an inherited one. Test-optional policies do not lower standards; they relocate them to the fuller record of a student's actual work."),
            ("revise", "Universities should stop requiring standardized tests, not because the tests measure nothing, but because they measure the wrong thing at the wrong moment. A single Saturday morning cannot capture four years of intellectual growth, yet it disproportionately shapes who gets in. Worse, scores track family income more faithfully than future performance, quietly converting a supposed meritocracy into an inherited one. Critics warn that dropping tests lowers standards, but this confuses a standard with a proxy for it: test-optional policies do not abandon rigor, they relocate it to the fuller record of a student's actual work — transcripts, projects, and sustained effort over time."),
            ("revise", "Universities should stop requiring standardized tests, not because the tests measure nothing, but because they measure the wrong thing at the wrong moment. One Saturday morning cannot capture four years of growth, yet it disproportionately decides who gets in. Worse, scores track family income more faithfully than future performance, converting a supposed meritocracy into an inherited one. Critics warn that dropping tests lowers standards, but this confuses a standard with a proxy for it. Test-optional policies do not abandon rigor; they relocate it to the fuller record of a student's actual work. That record is harder to read than a number — and that difficulty is the point, because students are harder to read than numbers too."),
        ],
    },
    {
        "id": "P6_college_avg_compare_purposeshift",
        "profile": "College sophomore, average writer, compare/contrast shifting to argument",
        "assignment": "Compare two approaches to reducing city traffic; you may argue for one.",
        "task": "Write your draft.",
        "special": "communicative purpose CHANGES across turns (compare -> argue); engine must track the shift",
        "turns": [
            ("writing", "There are two main ways cities reduce traffic: building more roads and improving public transit. More roads gives cars more space. Public transit gives people another option. Both cost a lot of money. More roads is faster to build but fills up again. Transit takes longer to build but moves more people. They are different approaches with different results."),
            ("revise", "There are two main ways cities reduce traffic: building more roads and improving public transit. Building roads adds space for cars but tends to fill up again as more people choose to drive, a pattern called induced demand. Public transit is slower and more expensive to build, but once it exists it moves far more people per dollar and does not induce the same driving. Comparing the two on cost, speed, and long-term effect, they are clearly different."),
            ("revise", "Cities have two main options for reducing traffic, but they are not equally good. Building more roads feels intuitive, yet it triggers induced demand: new lanes fill with new drivers within a few years, so the relief is temporary. Public transit costs more up front and takes longer to build, but it moves far more people per dollar and does not generate the same rebound. Once you weigh the long-term effect rather than the short-term convenience, the stronger choice is clear — cities should invest in transit, even though roads promise faster results."),
        ],
    },
    {
        "id": "P7_adult_avg_reflective",
        "profile": "Adult learner, average writer, reflective",
        "assignment": "Reflect on something a job or experience taught you.",
        "task": "Write your reflection.",
        "special": "reflection honors uncertainty; meaning over structure; not forced into thesis",
        "turns": [
            ("writing", "Working night shifts at the hospital taught me a lot. It was hard being awake when everyone slept. I saw people at their worst and their best. I learned to stay calm. It changed how I see nurses now. I have a lot of respect for them."),
            ("revise", "Working the night shift at the hospital taught me things I did not expect. At 3 a.m. the building feels different, quieter but heavier. I saw families get the worst news and I saw a nurse hold a strangers hand until morning. I learned to stay calm not by not feeling anything, but by feeling it and still doing the next thing. I am not sure I fully understand what those nights did to me, but I know I look at nurses differently now — not as helpers but as people who carry a lot quietly."),
        ],
    },
    {
        "id": "P8_hs_weak_informative_ignores",
        "profile": "High school (grade 9), weak writer, informative; student ignores advice",
        "assignment": "Write an informative paragraph about a topic you know well.",
        "task": "Write your paragraph.",
        "special": "STUDENT IGNORES the invitation on turn2 (revises something else); turn3 = abandons and starts a new topic",
        "turns": [
            ("writing", "Basketball is a sport. You dribble and shoot. There are 5 players. My favorite team is the Lakers. LeBron is good. You can dunk if your tall. Basketball is fun to play and watch."),
            ("revise", "Basketball is a fun sport. You dribble and shoot the ball. There are 5 players on the court. My favorite team is the Lakers and my favorite player is LeBron James who is really good. You can dunk if you are tall enough. I like basketball a lot. It is fun."),
            ("revise", "Actually I want to write about my dog instead. My dog is a husky named Kaia. She is very energetic and runs a lot. Huskies have thick fur for cold weather. She likes the snow. Dogs are loyal animals."),
        ],
    },
    {
        "id": "P9_hs_avg_argument_multiframework",
        "profile": "High school (grade 11), average writer, argument (many issues at once)",
        "assignment": "Argue whether homework should be limited in high school.",
        "task": "Write your argument.",
        "special": "MULTIPLE frameworks applicable at once (thesis, paragraph, evidence, coherence, conclusion) — must unify to ONE target",
        "turns": [
            ("writing", "Homework is bad for students. Studies show homework causes stress. Also students have sports and jobs. Teachers give too much. In addition sleep is important for teens. Homework should be limited. Because students need free time. Also it doesnt even help that much some people say. So limit it."),
            ("revise", "Homework should be limited in high school because too much of it does more harm than good. Studies have found that heavy homework loads raise stress and cut into sleep, and teenagers need sleep to learn. Many students also work jobs or play sports after school, so there is little time left. Some people argue homework builds discipline, and a reasonable amount can. But past a certain point it stops helping and just wears students down. Schools should cap homework so it supports learning instead of replacing rest."),
            ("revise", "Homework should be limited in high school because past a certain point it does more harm than good. Moderate practice helps students remember what they learned. But heavy loads raise stress and steal the sleep teenagers need to actually learn, and many students also juggle jobs or sports. So the problem is not homework itself — it is the amount. A fair cap, like a set number of minutes per class, would keep the benefit of practice while protecting the rest and time that make learning possible in the first place."),
        ],
    },
]


def run():
    results = []
    for sess in SESSIONS:
        sid = create_session(sess["assignment"], sess["task"])
        cycles = []
        print(f"\n=== {sess['id']} — {sess['profile']} ===", flush=True)
        try:
            for i, (kind, content) in enumerate(sess["turns"]):
                s, secs = interact(sid, kind, content)
                ex = extract(s)
                cycles.append({"turn": i + 1, "kind": kind, "student": content, "elapsed_s": secs, **ex})
                print(f"  turn {i+1} [{kind}] {secs}s | target='{ex['primary_target'][:55]}' | mode={ex['instructional_mode']} | iv={ex['iv_type']} focus={ex['iv_focus']} | cycle={ex['cycle_status']} | rev_applies={ex['revision_applies']}", flush=True)
                print(f"       INVITE: {ex['ai_invitation'][:160]}", flush=True)
        except Exception as e:  # noqa: BLE001
            print(f"  ERROR: {e}", flush=True)
            cycles.append({"error": str(e)})
        results.append({"id": sess["id"], "profile": sess["profile"], "special": sess["special"],
                        "assignment": sess["assignment"], "session_id": sid, "cycles": cycles})
        json.dump(results, open(OUT, "w"), indent=2)
    print(f"\nDONE — wrote {OUT}", flush=True)


if __name__ == "__main__":
    run()
