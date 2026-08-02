"""Milestone 2 — Opening/Introduction exemplar evaluation harness.
Internal script (no public interface). Hits the running backend on localhost:8001,
streams the SSE /interact response, and records the engine's reasoning for 24
introductions plus one revision case. Writes JSON + a markdown review table."""
import json
import time
import re
import requests

BASE = "http://localhost:8001/api"

STAGE_WORDS = re.compile(r"\b(level|stage|score|grade\b|rubric|proficien|novice|advanced writer|beginner|competen)\b", re.I)
FORMULA_WORDS = re.compile(r"\b(must (start|begin|have|include) a hook|need a hook|add a hook|broad to narrow|thesis must|always (start|begin|end))\b", re.I)


def create_session(assignment, purpose, task, notes=""):
    r = requests.post(f"{BASE}/sessions", json={
        "assignment": assignment, "pedagogical_purpose": purpose,
        "current_writing_task": task, "teacher_notes": notes,
    }, timeout=30)
    r.raise_for_status()
    return r.json()["id"]


def interact(sid, kind, content):
    r = requests.post(f"{BASE}/sessions/{sid}/interact", json={"kind": kind, "content": content},
                      stream=True, timeout=180)
    r.raise_for_status()
    session = None
    err = None
    buf = ""
    for chunk in r.iter_content(chunk_size=None, decode_unicode=True):
        if not chunk:
            continue
        buf += chunk
        while "\n\n" in buf:
            raw, buf = buf.split("\n\n", 1)
            event, data = "message", ""
            for line in raw.split("\n"):
                if line.startswith(":"):
                    continue
                if line.startswith("event:"):
                    event = line[6:].strip()
                elif line.startswith("data:"):
                    data += line[5:].strip()
            if event == "done" and data:
                session = json.loads(data)
            elif event == "error" and data:
                err = json.loads(data).get("detail")
    if err:
        raise RuntimeError(err)
    return session


CASES = [
  {"n":1,"desc":"Broad topic, no specific purpose","genre":"expository","grade":"9","audience":"general classmates",
   "assign":"Write an essay about technology.","purpose":"Help the student narrow a broad topic into a specific focus with a purpose.","task":"Draft your introduction.",
   "intro":"Technology is a big part of our lives. It is everywhere and it keeps changing. Many people use it every day."},
  {"n":2,"desc":"Topic + useful context but no significance","genre":"expository","grade":"10","audience":"general reader",
   "assign":"Explain a current issue in your community.","purpose":"Help the student move from context to significance.","task":"Draft your introduction.",
   "intro":"Our town built a new recycling center last year. It processes about ten tons of waste each week and employs twelve people. It replaced the old landfill program."},
  {"n":3,"desc":"Clear problem, weak reader orientation","genre":"argumentative","grade":"11","audience":"school board (naive to specifics)",
   "assign":"Argue for a change to school policy.","purpose":"Help the student orient a reader who does not share the writer's context.","task":"Draft your introduction.",
   "intro":"The block schedule is destroying everything. Nobody can focus for that long and the whole thing needs to be scrapped immediately before it gets worse."},
  {"n":4,"desc":"Clear claim introduced too abruptly for the reader","genre":"argumentative","grade":"11","audience":"general public",
   "assign":"Argue a position on urban planning.","purpose":"Help the student prepare a reader to understand a claim.","task":"Draft your introduction.",
   "intro":"Cities must ban all private cars from downtown immediately. This is the only reasonable position and anyone who disagrees has not thought about it."},
  {"n":5,"desc":"Anecdote with no visible connection to purpose","genre":"argumentative","grade":"10","audience":"peers",
   "assign":"Argue about the value of part-time jobs for teenagers.","purpose":"Help the student connect an anecdote to the essay's purpose.","task":"Draft your introduction.",
   "intro":"Last summer I dropped my ice cream cone at the beach and a seagull swooped down and grabbed it. It was hilarious. Anyway, teenagers should have jobs."},
  {"n":6,"desc":"Anecdote whose connection becomes clear later","genre":"reflective","grade":"12","audience":"general reader",
   "assign":"Write a reflective essay about learning.","purpose":"Let purposeful indirect openings stand; interpret function.","task":"Draft your introduction.",
   "intro":"The first time I tried to bake bread, it came out flat and dense as a brick. I did not understand that yeast is alive and needs time. That failure taught me something about patience that changed how I approach every hard thing I now attempt."},
  {"n":7,"desc":"Formulaic hook-background-thesis introduction","genre":"argumentative","grade":"9","audience":"teacher",
   "assign":"Argue whether homework should be reduced.","purpose":"Help resources function together rather than fill a template.","task":"Draft your introduction.",
   "intro":"Have you ever felt stressed? Homework has existed for a long time in schools around the world. In this essay I will argue that homework should be reduced because it causes stress, wastes time, and hurts families."},
  {"n":8,"desc":"Strong conventional argumentative introduction","genre":"argumentative","grade":"12","audience":"informed public",
   "assign":"Argue a position on social media age limits.","purpose":"Extend an already strong opening.","task":"Draft your introduction.",
   "intro":"Every day, millions of children under thirteen log into platforms designed to hold adult attention for as long as possible. Regulators have largely looked away. Yet the evidence of harm is mounting, and it raises an urgent question about who is responsible when a product built for engagement meets a developing mind. This essay argues that platforms, not parents alone, must bear that responsibility."},
  {"n":9,"desc":"Strong unconventional argumentative introduction","genre":"argumentative","grade":"12","audience":"literary/engaged reader",
   "assign":"Argue a position on how cities treat public space.","purpose":"Honor a purposeful unconventional opening.","task":"Draft your introduction.",
   "intro":"There is a bench near my apartment with three metal armrests bolted across it. It is not designed for resting; it is designed so that no one can lie down. Once you notice one, you see them everywhere, and the city starts to look like an argument about who is allowed to exist in it."},
  {"n":10,"desc":"Research introduction with necessary background","genre":"research","grade":"college","audience":"academic reader new to topic",
   "assign":"Write a research essay on antibiotic resistance.","purpose":"Coordinate background, problem, and significance.","task":"Draft your introduction.",
   "intro":"Antibiotics transformed medicine in the twentieth century, turning once-fatal infections into treatable conditions. But bacteria evolve, and decades of heavy use have accelerated the spread of resistant strains. Understanding how resistance emerges is now central to protecting the gains modern medicine has made."},
  {"n":11,"desc":"Research introduction overloaded with background","genre":"research","grade":"college","audience":"academic reader",
   "assign":"Write a research essay on the printing press.","purpose":"Help select relevant context over exhaustive background.","task":"Draft your introduction.",
   "intro":"Writing began with cuneiform in Mesopotamia around 3200 BCE, followed by Egyptian hieroglyphs, the Phoenician alphabet, Greek and Roman scripts, medieval manuscripts copied by monks, the development of paper in China, its spread along the Silk Road, and eventually block printing, before Gutenberg, who was born around 1400 in Mainz, developed movable type in Europe."},
  {"n":12,"desc":"Personal essay opening without explicit thesis","genre":"personal","grade":"11","audience":"general reader",
   "assign":"Write a personal essay about a place that shaped you.","purpose":"Allow voice/situation without forcing a thesis.","task":"Draft your introduction.",
   "intro":"My grandmother's kitchen always smelled of cardamom and burnt sugar. The linoleum was cracked in the corner where the table leg had worn it, and that was exactly where I sat every afternoon after school."},
  {"n":13,"desc":"Narrative opening (should not be forced into argument)","genre":"narrative","grade":"10","audience":"general reader",
   "assign":"Write a narrative about a turning point.","purpose":"Interpret narrative openings on their own terms.","task":"Draft your introduction.",
   "intro":"The bus pulled away before I reached the corner, and I stood there in the rain watching its taillights blur. I had exactly four dollars and no way to get across the city by six."},
  {"n":14,"desc":"Reflective opening organized around uncertainty","genre":"reflective","grade":"12","audience":"general reader",
   "assign":"Write a reflective essay about a belief you questioned.","purpose":"Value uncertainty as an organizing move.","task":"Draft your introduction.",
   "intro":"I used to think honesty was simple: you either told the truth or you lied. I am no longer sure. Somewhere between a comforting silence and a cruel fact, I lost my confidence about what honesty even requires of me."},
  {"n":15,"desc":"Rhetorical question that genuinely organizes the essay","genre":"argumentative","grade":"11","audience":"general reader",
   "assign":"Argue about the ethics of zoos.","purpose":"Interpret whether a question organizes the essay.","task":"Draft your introduction.",
   "intro":"What do we owe an animal that cannot consent to being watched? Zoos claim to protect species while displaying them for profit, and that contradiction is exactly what this essay tries to work through."},
  {"n":16,"desc":"Rhetorical question used only decoratively","genre":"argumentative","grade":"9","audience":"peers",
   "assign":"Argue about the importance of exercise.","purpose":"Distinguish a functional question from decoration.","task":"Draft your introduction.",
   "intro":"Do you like being healthy? Everybody knows exercise is good for you. In this essay I will talk about why exercise is important for people of all ages."},
  {"n":17,"desc":"Dictionary definition that does not serve purpose","genre":"expository","grade":"9","audience":"general reader",
   "assign":"Explain the value of friendship.","purpose":"Distinguish orienting definitions from filler.","task":"Draft your introduction.",
   "intro":"Merriam-Webster defines friendship as 'the state of being friends.' Friendship is something that has existed for as long as people have. It is a very important thing to have."},
  {"n":18,"desc":"Definition necessary for reader understanding","genre":"analytical","grade":"college","audience":"reader new to the term",
   "assign":"Analyze the role of 'moral luck' in judging actions.","purpose":"Recognize a genuinely orienting definition.","task":"Draft your introduction.",
   "intro":"Philosophers use the term 'moral luck' to describe cases where we praise or blame people for outcomes that were partly beyond their control. A driver who looks away for a second is called reckless only if a child happens to step into the road. That dependence on chance is the puzzle this essay examines."},
  {"n":19,"desc":"Opening with several uncoordinated ideas","genre":"argumentative","grade":"10","audience":"general reader",
   "assign":"Argue about the effects of remote work.","purpose":"Help coordinate ideas under a governing purpose.","task":"Draft your introduction.",
   "intro":"Remote work saves commuting time. Also cities are changing. Some people feel lonely working from home. Office real estate is expensive. Technology makes it possible. There are many things to consider about this topic."},
  {"n":20,"desc":"Opening that clearly establishes stakes","genre":"argumentative","grade":"12","audience":"policy-aware reader",
   "assign":"Argue about groundwater use in agriculture.","purpose":"Extend an opening that already establishes stakes.","task":"Draft your introduction.",
   "intro":"The aquifer beneath the valley took twelve thousand years to fill and, at current rates, will be effectively empty within thirty. Every choice the region's farmers make now is a choice about whether the next generation inherits farmland or dust."},
  {"n":21,"desc":"Opening that merely declares the topic 'important'","genre":"expository","grade":"9","audience":"general reader",
   "assign":"Explain why voting matters.","purpose":"Move from asserted importance to grounded significance.","task":"Draft your introduction.",
   "intro":"Voting is a very important part of a democracy. It is important for everyone to vote. This essay will explain why voting is so important for our country."},
  {"n":22,"desc":"Opening for an audience that already knows the context","genre":"analytical","grade":"college","audience":"specialists who share context",
   "assign":"Write for a seminar of peers who have read the same novel: analyze its ending.","purpose":"Judge orientation relative to a knowledgeable audience.","task":"Draft your introduction.",
   "intro":"The novel's final chapter refuses the reconciliation the earlier chapters seem to promise. Reading the closing scene against the garden imagery of chapter three, this essay argues that the ambiguity is deliberate rather than a failure of resolution."},
  {"n":23,"desc":"Opening for a naive audience lacking necessary context","genre":"expository","grade":"11","audience":"readers unfamiliar with the topic",
   "assign":"Explain a specialized hobby to newcomers.","purpose":"Orient a reader who lacks the writer's context.","task":"Draft your introduction.",
   "intro":"After you catch the flash you set the hook and palm the reel, but only if the tippet is light enough or you will snap off on the take. Most people ruin the drift by mending too late."},
  {"n":24,"desc":"Revision that meaningfully reorganizes after an invitation","genre":"argumentative","grade":"11","audience":"naive general reader","revision":True,
   "assign":"Argue about phones in schools.","purpose":"Help the student prepare a naive reader to understand the problem and why it matters.","task":"Draft your introduction.",
   "intro":"Phones are everywhere today. Almost every teenager has one. Schools have different rules about them.",
   "revised":"Every morning students walk into class with a device more powerful than the computers that sent people to the moon, and no two schools agree on what to do about it. Some ban phones outright; others let students use them freely. That inconsistency is not just confusing — it hides a real question that affects how well students learn: when does a phone help and when does it quietly harm?"},
]


def summarize(session):
    t = session["theory"]
    ir = session["interactions"][-1]
    ai_turns = [x for x in session["turns"] if x["role"] == "ai"]
    inv = ir["selected_invitation"]["invitation"]
    return {
        "operative_purpose": session["telos"].get("immediate_task_purpose", ""),
        "current_organization": t.get("current_organization", ""),
        "observed_functions": (t.get("observed_differentiations", []) + t.get("observed_integrations", []))[:4],
        "supporting_evidence": t.get("supporting_evidence", []),
        "complicating_evidence": t.get("complicating_evidence", []),
        "alternative_interpretations": t.get("alternative_interpretations", []),
        "primary_tension": (t.get("unresolved_tensions") or [""])[0],
        "relevant_resources": (t.get("cultural_resources_in_use", []) + t.get("potential_cultural_resources", []))[:6],
        "relevant_domains": t.get("currently_relevant_domains", []),
        "candidate_invitations": [c["invitation"] for c in ir["candidate_invitations"]],
        "selected_invitation": inv,
        "changes_since_previous": t.get("changes_since_previous", ""),
        "checks": {
            "one_invitation_this_turn": len(ai_turns) == len(session["interactions"]),
            "opening_selected": "Opening / Introduction" in t.get("currently_relevant_domains", []),
            "requires_action": bool(re.search(r"\?|identify|explain|revise|decide|compare|imagine|name|state|choose|check|consider|test", inv, re.I)),
            "no_stage_language": not bool(STAGE_WORDS.search(inv)) and not bool(STAGE_WORDS.search(json.dumps(t))),
            "no_formula_imposition": not bool(FORMULA_WORDS.search(inv)),
            "invitation_len_chars": len(inv),
            "preserved_alternatives": len(t.get("alternative_interpretations", [])) > 0,
        },
    }


def main():
    results = []
    for c in CASES:
        t0 = time.time()
        try:
            sid = create_session(c["assign"], c["purpose"], c["task"])
            s = interact(sid, "writing", c["intro"])
            rec = {"n": c["n"], "desc": c["desc"], "genre": c["genre"], "grade": c["grade"],
                   "audience": c["audience"], "intro": c["intro"], "first": summarize(s)}
            if c.get("revision"):
                s2 = interact(sid, "revise", c["revised"])
                rec["revised_text"] = c["revised"]
                rec["second"] = summarize(s2)
                rec["theory_versions"] = len(s2["theory_history"])
            rec["elapsed_s"] = round(time.time() - t0, 1)
            print(f"case {c['n']} OK in {rec['elapsed_s']}s  tension={rec['first']['primary_tension'][:60]!r}", flush=True)
            results.append(rec)
        except Exception as e:  # noqa: BLE001
            print(f"case {c['n']} FAILED: {e}", flush=True)
            results.append({"n": c["n"], "desc": c["desc"], "error": str(e)})
        with open("/app/backend/tests/milestone2_results.json", "w") as f:
            json.dump(results, f, indent=2)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
