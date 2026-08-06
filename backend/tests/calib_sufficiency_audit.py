"""Compass 4.5 calibration audit — multi-turn, target-stability focused.

For each calibration case we run a real multi-turn session against the live engine and
capture the FULL DCO per turn. The point is not "do fields populate" but whether the
Learner-Relative Developmental Sufficiency architecture produces the right STOPPING
decisions and whether the learner-accessible target stays FIXED once the learner reaches it.

Writes /app/backend/tests/calib_sufficiency_report.json (full per-turn DCO) and prints a
readable per-turn summary to stdout (captured to a log).
"""
import sys, json, time, requests

with open("/app/frontend/.env") as f:
    for line in f:
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE = line.strip().split("=", 1)[1]
API = f"{BASE}/api"

CASES = [
    {
        "id": "ai_education",
        "assignment": "What should we do about AI in education?",
        "purpose": "Develop the learner's ability to state and support a position for a reader.",
        "task": "One paragraph.",
        "turns": [
            # Turn 1 — the advanced calibration paragraph (virtuous loop asserted, not unfolded)
            ("The real problem with AI in education is not that it exists but that students can use it to "
             "complete their work without doing the thinking, and thinking is how people actually learn. Schools "
             "have mostly responded by either banning AI or pretending it is not there, yet banning is nearly "
             "impossible to enforce and ignoring it simply lets students hand their thinking over to a machine. "
             "What we should do instead is distinguish AI that completes a task from AI that guides learning, and "
             "build tools of the second kind. A tool like Compass does not write the paragraph for the student; it "
             "asks the student questions that lead them to construct the answer themselves. Because the student "
             "still performs the effortful intellectual work, they still learn, and because the tool removes some "
             "of the overwhelm, they stay motivated to keep going. That creates a virtuous loop: guided effort "
             "produces a small success, the success builds motivation, and the motivation fuels more learning."),
            # Turn 2 — learner UNFOLDS the one previously-flagged material gap (the virtuous loop mechanism).
            # Supplies exactly that relation; introduces NO structurally new requirement.
            ("The real problem with AI in education is not that it exists but that students can use it to "
             "complete their work without doing the thinking, and thinking is how people actually learn. Schools "
             "have mostly responded by either banning AI or pretending it is not there, yet banning is nearly "
             "impossible to enforce and ignoring it simply lets students hand their thinking over to a machine. "
             "What we should do instead is distinguish AI that completes a task from AI that guides learning, and "
             "build tools of the second kind. A tool like Compass does not write the paragraph for the student; it "
             "asks the student questions that lead them to construct the answer themselves. Because the student "
             "still performs the effortful intellectual work, they still learn. This is what creates a virtuous "
             "loop: because the tool breaks an overwhelming task into one guided question at a time, the student "
             "actually finishes a piece of real thinking; finishing it feels like a success, and that success "
             "makes them willing to attempt the next question instead of giving up; each attempt is more genuine "
             "thinking, so the learning and the motivation keep feeding each other."),
        ],
    },
    {
        "id": "homework_developing",
        "assignment": "Should schools reduce the amount of homework they assign?",
        "purpose": "Develop the learner's ability to state a position and connect one reason to it for a reader.",
        "task": "One paragraph.",
        "turns": [
            # Turn 1 — position stated, reasons ASSERTED but not connected (list-like).
            ("Schools should give less homework. Too much homework is bad for students. It makes them stressed "
             "and tired. Homework does not always help students learn. Kids also need time for other things."),
            # Turn 2 — learner constructs the ONE central because-relation (the accessible target):
            # connects "less homework" to "homework's own purpose (learning)" via the stress mechanism.
            ("Schools should give less homework because the whole point of homework is to help students learn, "
             "but when there is too much of it students get so stressed and exhausted that they stop absorbing "
             "anything they do. So piling on more homework actually stops it from doing the one thing it is "
             "supposed to do, which is help them learn."),
            # Turn 3 — learner adds a concrete example (surface richness) but NO new relation/organization.
            # CRITICAL target-stability probe: does Compass keep the fixed target / transition, or invent a
            # higher target (e.g. now demand a counterargument) simply because more is possible?
            ("Schools should give less homework because the whole point of homework is to help students learn, "
             "but when there is too much of it students get so stressed and exhausted that they stop absorbing "
             "anything they do. For example, a student with five hours of homework often rushes through it at "
             "midnight just to finish, learning nothing. So piling on more homework actually stops it from doing "
             "the one thing it is supposed to do, which is help them learn."),
        ],
    },
    {
        "id": "phones_short",
        "assignment": "Should phones be allowed in class?",
        "purpose": "Develop the learner's ability to state a position and give a clear supporting reason for a reader.",
        "task": "One short paragraph.",
        "turns": [
            # Turn 1 — short, self-contained, coherent, task-adequate for a less advanced learner.
            ("Phones should not be allowed in class because students look at them instead of listening, and when "
             "you are not listening you cannot learn what the teacher is explaining. If phones stayed in lockers, "
             "students would pay attention and understand the lesson better."),
            # Turn 2 — a tiny tightening revision (no new organization). Probe: does Compass recognize
            # good_enough coherence / sufficiency, or reach for expert differentiation beyond the horizon?
            ("Phones should not be allowed in class because students end up looking at them instead of listening, "
             "and when you are not paying attention you cannot learn what the teacher is explaining. If phones "
             "were kept in lockers during lessons, students would focus and understand the material much better."),
        ],
    },
]

SUFFIELDS = ["value", "task_answered", "learner_accessible_target", "accessible_target_achieved",
             "developmental_advance", "organization_stability", "self_contained_coherence",
             "further_growth_potential", "likely_value_of_further_instruction",
             "likely_cost_of_further_instruction", "effectance_risk", "transition_recommendation",
             "reason", "confidence"]


def wait_for_turn(sid, expected_count, timeout_polls=170):
    for _ in range(timeout_polls):
        time.sleep(4)
        tr = requests.get(f"{API}/dev/functional-v3-trace/{sid}", timeout=30)
        if tr.status_code == 200:
            t = tr.json().get("trace", [])
            if len(t) >= expected_count and t[expected_count - 1].get(
                    "developmental_cognition", {}).get("learner_relative_sufficiency"):
                return t
    return None


report = {"cases": []}
for case in CASES:
    print("\n" + "=" * 70)
    print(f"CASE: {case['id']}")
    print("=" * 70)
    s = requests.post(f"{API}/sessions", json={
        "assignment": case["assignment"],
        "pedagogical_purpose": case["purpose"],
        "current_writing_task": case["task"],
        "assignment_prompt": case["assignment"],
        "reasoning_mode": "canonical_v2",
    }, timeout=30)
    s.raise_for_status()
    sid = s.json()["id"]
    print("SESSION", sid)
    case_rec = {"id": case["id"], "session_id": sid, "turns": []}
    trace = None
    for i, draft in enumerate(case["turns"], start=1):
        print(f"\n--- submitting turn {i} ---")
        r = requests.post(f"{API}/sessions/{sid}/interact",
                          json={"content": draft, "kind": "writing"}, timeout=30)
        if r.status_code not in (200, 201):
            print("interact status", r.status_code, r.text[:200])
        trace = wait_for_turn(sid, i)
        if not trace:
            print(f"FAIL: turn {i} DCO never appeared")
            break
        dco = trace[i - 1]["developmental_cognition"]
        lrs = dco.get("learner_relative_sufficiency", {})
        tra = dco.get("task_relative_adequacy", {})
        tss = dco.get("timely_success_status", {})
        turn_rec = {
            "turn": i,
            "learner_relative_sufficiency": lrs,
            "task_relative_adequacy": tra,
            "timely_success_status": tss,
            "sentence_craft_readiness": dco.get("sentence_craft_readiness", {}),
            "completion_readiness": dco.get("completion_readiness", {}),
        }
        case_rec["turns"].append(turn_rec)
        print(f"\n[TURN {i}] learner_relative_sufficiency:")
        for k in SUFFIELDS:
            v = lrs.get(k)
            if v not in (None, "", []):
                print(f"    {k}: {v}")
        print(f"[TURN {i}] task_relative_adequacy: value={tra.get('value')} | "
              f"transition={tra.get('transition_recommendation')} | material_gap={tra.get('material_gap')!r}")
        print(f"[TURN {i}] timely_success_status: value={tss.get('value')} | "
              f"now_meets_task={tss.get('now_meets_task')} | what_changed={tss.get('what_changed')!r}")
    # target-stability cross-turn comparison
    targets = [t["learner_relative_sufficiency"].get("learner_accessible_target") for t in case_rec["turns"]]
    achieved = [t["learner_relative_sufficiency"].get("accessible_target_achieved") for t in case_rec["turns"]]
    transitions = [t["learner_relative_sufficiency"].get("transition_recommendation") for t in case_rec["turns"]]
    print(f"\n>>> TARGET ACROSS TURNS ({case['id']}):")
    for j, (tg, ac, tn) in enumerate(zip(targets, achieved, transitions), start=1):
        print(f"    turn {j}: target={tg!r} | achieved={ac} | transition={tn}")
    case_rec["target_trajectory"] = {"targets": targets, "achieved": achieved, "transitions": transitions}
    report["cases"].append(case_rec)

with open("/app/backend/tests/calib_sufficiency_report.json", "w") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)
print("\n\nDONE — wrote /app/backend/tests/calib_sufficiency_report.json")
