"""
Testing-phase driver: runs real Assignment Representation sessions with scripted,
deliberately imperfect learner personas across the level/discipline/type matrix.
It does NOT write developer notes (the human/agent reviews transcripts and writes
Developer Notes / Summary / Sprint Recommendation afterwards).

Run in background:  python run_dev_sessions.py  (writes /tmp/dev_sessions/*.json + index)
"""
import json
import os
import time
import requests

BASE = "http://localhost:8001/api/assignment"
OUT = "/tmp/dev_sessions"
os.makedirs(OUT, exist_ok=True)

# Each scenario: assignment + a learner "persona" = interpretation followed by a
# queue of operation responses (deliberately flawed / escalating), then a restatement.
SCENARIOS = [
    {
        "key": "g4_animal",
        "meta": "Grade 4 · Reflective · short",
        "assignment": "Draw a picture of your favorite animal and write two sentences about why you like it.",
        "interpretation": "I have to draw an animal and write about it.",
        "ops": ["Because it is cute.", "I don't know.", "I like dolphins because they are smart and they can do tricks and they are friendly."],
        "restatement": "I draw my favorite animal and write two sentences saying why I like it.",
    },
    {
        "key": "g8_civilwar",
        "meta": "Grade 8 · History · explanation",
        "assignment": "Explain the main causes of the American Civil War.",
        "interpretation": "I need to say what started the Civil War, like the battles and Abraham Lincoln.",
        "ops": ["It was because the North and South did not get along.", "I think slavery and states rights but I'm not sure how they connect.", "I don't know.", "Slavery was the main cause, and states' rights and the economy were tied to it."],
        "restatement": "I have to explain the causes of the Civil War, mainly slavery, plus states' rights and economic differences, and how they led to war.",
    },
    {
        "key": "g12_enzyme_lab",
        "meta": "Grade 12 · Biology · lab report",
        "assignment": "Design an experiment to test how temperature affects enzyme activity. State your hypothesis, identify your variables, and predict the results.",
        "interpretation": "I need to do an experiment about enzymes and write down what happens.",
        "ops": ["My hypothesis is that enzymes work.", "The variable is temperature.", "I don't know the difference between the variables.", "Independent variable is temperature, dependent is reaction rate, and I keep pH and enzyme amount the same."],
        "restatement": "I design an enzyme-temperature experiment: state a hypothesis, name independent/dependent/controlled variables, and predict how rate changes with temperature.",
    },
    {
        "key": "col_mindset",
        "meta": "College · Psychology · compare/contrast",
        "assignment": "Compare fixed and growth mindsets. Explain how each mindset affects both the process and outcomes of learning. Use relevant examples to support your explanation.",
        "interpretation": "I need to talk about growth mindset and how believing you can improve helps you learn better and try harder.",
        "ops": ["Growth mindset makes you get better grades.", "Fixed mindset is when you give up. I'm not sure what process vs outcome means.", "I don't know.", "Process is how you learn (effort, strategies) and outcome is the result like grades; the mindsets change both."],
        "restatement": "I compare fixed and growth mindsets and explain how each shapes the learning process and the outcomes, with examples.",
    },
    {
        "key": "col_remotework",
        "meta": "College · Business · argument",
        "assignment": "Critically evaluate whether remote work improves employee productivity, drawing on at least three peer-reviewed sources.",
        "interpretation": "I need to say whether remote work is good and give my opinion.",
        "ops": ["Remote work is good because people like it.", "I guess I need evidence but any article is fine.", "I don't know what counts as peer-reviewed.", "I take a position, support it with three peer-reviewed studies, and weigh counter-evidence."],
        "restatement": "I argue a position on whether remote work improves productivity, support it with at least three peer-reviewed sources, and address counterarguments.",
    },
    {
        "key": "grad_attachment",
        "meta": "Graduate · Psychology · synthesis/argument",
        "assignment": "For your graduate seminar, synthesize competing theoretical frameworks of attachment and argue for the most explanatorily powerful account.",
        "interpretation": "I should summarize attachment theories like Bowlby and Ainsworth.",
        "ops": ["I'll describe each theory one by one.", "Synthesize just means summarize, right?", "I don't know how to argue which is most powerful.", "Synthesis means integrating them into a comparative account, then arguing which best explains the evidence and why."],
        "restatement": "I synthesize competing attachment frameworks into an integrated comparison and argue, with criteria, which account is most explanatorily powerful.",
    },
]


def post(path, payload):
    r = requests.post(f"{BASE}{path}", json=payload, timeout=120)
    r.raise_for_status()
    return r.json()


def patch(path, payload):
    r = requests.patch(f"{BASE}{path}", json=payload, timeout=120)
    r.raise_for_status()
    return r.json()


def get_record(sid):
    r = requests.get(f"{BASE}/sessions/{sid}/record", timeout=120)
    r.raise_for_status()
    return r.json()


def run(scn):
    t0 = time.time()
    sess = post("/sessions", {"assignment_text": scn["assignment"]})
    sid = sess["id"]
    sess = post(f"/sessions/{sid}/interpret", {"text": scn["interpretation"]})
    turns = 0
    for resp in scn["ops"]:
        if sess["stage"] != "mapping":
            break
        sess = post(f"/sessions/{sid}/operation", {"text": resp})
        turns += 1
        if turns >= 8:
            break
    if sess["stage"] == "restatement":
        sess = post(f"/sessions/{sid}/restatement", {"text": scn["restatement"]})
    rec = get_record(sid)
    rec["_scenario_meta"] = scn["meta"]
    with open(f"{OUT}/{scn['key']}.json", "w") as f:
        json.dump(rec, f, indent=2, default=str)
    m = rec["metadata"]
    return {
        "key": scn["key"], "meta": scn["meta"], "id": sid,
        "final_stage": sess["stage"], "adequate": sess["representation_adequate"],
        "op_turns": turns, "level3": m["num_level3_interventions"],
        "idk": m["i_dont_know_occurred"], "seconds": round(time.time() - t0),
        "subject": sess.get("subject"), "level": sess.get("educational_level"),
    }


def main():
    results = []
    for scn in SCENARIOS:
        try:
            res = run(scn)
        except Exception as e:
            res = {"key": scn["key"], "error": str(e)}
        results.append(res)
        with open(f"{OUT}/_index.json", "w") as f:
            json.dump(results, f, indent=2)
        print(json.dumps(res), flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
