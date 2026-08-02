import json, requests
BASE = "http://localhost:8001/api/assignment"
idx = {r["key"]: r for r in json.load(open("/tmp/dev_sessions/_index.json"))}

OBS = {
    "g4_animal": {
        "developer_summary": "A trivial Grade-4 task was over-analyzed into 5 demands and the engine FIXATED on 'Write two sentences' — a length constraint mislabeled as a Define operation — escalating to Level 3 three times. The learner's genuinely adequate answer ('I like dolphins because they are smart, do tricks, and are friendly') was FAILED as 'no_reconstruction'. Severe over-scaffolding; the child never reached the real task.",
        "developer_notes": "1) 'Write two sentences' is a format/length CONSTRAINT, not a developmental operation, yet it was scaffolded as one (op=Define). 2) L3 mandatory 'reconstruction' misfires on non-conceptual doing-tasks — a correct answer was marked no_reconstruction. 3) Escalation far too fast for a derivable Grade-4 demand (one weak answer + one 'I don't know' -> L3 direct teaching). 4) Scaffold register too abstract for Grade 4. 5) Inferred demand 'Connect drawing to writing (Relate)' is marginal padding.",
        "sprint_recommendation": "Developmental Control Engine revision",
    },
    "g8_civilwar": {
        "developer_summary": "Engine fixated on 'Identify Main Causes' for 3 turns while the OPERATION LABEL mutated every turn into long invented phrases (Distinguish causes from events -> 'Identify causation - selecting specific historical conditions...' -> 'Explain how a factor functions as a cause...'). Never advanced to explaining or prioritizing causes. Operation not anchored to the demand.",
        "developer_notes": "Operation field is unstable and verbose across turns for the SAME demand; it should be fixed (e.g. Analyze/Identify). Target fixation prevents coverage of the other four demands. The cause-vs-event distinction is a good target though.",
        "sprint_recommendation": "Developmental Control Engine revision",
    },
    "g12_enzyme_lab": {
        "developer_summary": "Reasonable demands (hypothesis, variables, prediction). Learner conflated hypothesis with prediction and IV/DV; the engine picked the right target (variable differentiation) but escalated to Level 3 twice after a single 'I don't know', before the learner had a fair chance at L1/L2.",
        "developer_notes": "Variable-differentiation is the correct high-leverage target. Escalation to L3 felt premature. A stronger L2 guided-construction contrast (IV vs DV vs controlled) would likely have worked without direct teaching.",
        "sprint_recommendation": "New scaffold",
    },
    "col_mindset": {
        "developer_summary": "Canonical case. Engine correctly prioritized Define -> Compare, but FIXATED on 'Define Both Mindsets' for 3 turns (L2->L3->L3). When the learner finally articulated the process-vs-outcome distinction (turn 4), the active target had switched to Compare and the response was scored 'misconception' — credit was NOT applied to the Differentiate demand it actually satisfied. Never reached the substantive compare/explain work.",
        "developer_notes": "1) Target fixation delays the real conceptual work. 2) DIAGNOSTIC MIS-ATTRIBUTION: a response demonstrating demand X is judged only against the active target Y. Diagnosis should re-scan all demands after every response. 3) 6 essential demands -> long loop / fatigue risk.",
        "sprint_recommendation": "Developmental Control Engine revision",
    },
    "col_remotework": {
        "developer_summary": "Best-paced session of the batch. Demands (position, >=3 peer-reviewed sources, counter-evidence) identified well; only one Level-3. The learner's 'any article is fine' misconception about peer-review was an excellent, well-chosen target. Argument-vs-opinion distinction captured.",
        "developer_notes": "Worked largely as intended. 'What counts as peer-reviewed' is a strong high-leverage target. Note the '>=3 sources' quota is a constraint, not an operation — same constraint-vs-operation issue to watch, but here it did not derail the session.",
        "sprint_recommendation": "No change needed",
    },
    "grad_attachment": {
        "developer_summary": "Graduate synthesis task. The 'synthesis means summarize' misconception was correctly identified as the target, but the engine drilled it (2x Level-3) rather than moving toward the argument/criteria demand. For graduate level the Level-3 teaching read as too elementary.",
        "developer_notes": "Synthesis-vs-summary is a strong distinction and correct target. Target fixation again. Level-3 direct teaching not calibrated to graduate register. Argument/criteria demand never reached.",
        "sprint_recommendation": "Developmental Control Engine revision",
    },
}

for key, obs in OBS.items():
    sid = idx[key]["id"]
    r = requests.patch(f"{BASE}/sessions/{sid}/developer-notes", json=obs, timeout=60)
    print(key, r.status_code)
print("done")
