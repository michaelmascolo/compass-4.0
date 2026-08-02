"""Milestone 3 — Central Claim / Thesis exemplar evaluation harness.
Internal script (no public interface). Streams SSE /interact on localhost:8001,
records the engine's reasoning for 24 thesis cases (incl. revision cases), and
writes JSON + a markdown review table."""
import json
import time
import re
import requests

BASE = "http://localhost:8001/api"
STAGE_WORDS = re.compile(r"\b(level|stage|score|grade\b|rubric|proficien|novice|competen)\b", re.I)
FORMULA_WORDS = re.compile(r"\b(must (be|have|include|state) a thesis|need a thesis sentence|thesis must (be|go|come)|x because a[, ]|last sentence of (your |the )?intro)\b", re.I)


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
 {"n":1,"desc":"Topic without claim","genre":"argumentative","aud":"peers","assign":"Argue a position on year-round school.","purpose":"Help the student form a central claim from a topic.","task":"Draft your thesis.",
  "text":"This essay is about year-round school. Year-round school is a topic people discuss a lot these days."},
 {"n":2,"desc":"Opinion without reasoning","genre":"argumentative","aud":"peers","assign":"Argue about school uniforms.","purpose":"Help move from opinion to reasoned position.","task":"Draft your thesis.",
  "text":"School uniforms are bad and I don't like them."},
 {"n":3,"desc":"Factual statement mistaken for thesis","genre":"expository","aud":"general","assign":"Write about the water cycle's role in climate.","purpose":"Distinguish fact from arguable/organizing claim.","task":"Draft your thesis.",
  "text":"Water evaporates from oceans, forms clouds, and falls as rain."},
 {"n":4,"desc":"Overly broad claim","genre":"argumentative","aud":"general","assign":"Argue about the effects of the internet.","purpose":"Scope the claim to what the essay can support.","task":"Draft your thesis.",
  "text":"The internet has completely changed everything about human life and society forever."},
 {"n":5,"desc":"Vague claim","genre":"argumentative","aud":"general","assign":"Argue about social media and teens.","purpose":"Make key terms precise.","task":"Draft your thesis.",
  "text":"Social media has a really big impact on young people in a lot of different ways."},
 {"n":6,"desc":"Multiple competing claims","genre":"argumentative","aud":"general","assign":"Argue about remote work.","purpose":"Help one claim govern the others.","task":"Draft your thesis.",
  "text":"Remote work saves money. Also it makes people lonely. And it will reshape cities. Companies should probably let people choose."},
 {"n":7,"desc":"Clear but unsupported claim","genre":"argumentative","aud":"school board","assign":"Argue for a policy change.","purpose":"Connect claim to support/reasoning.","task":"Draft your thesis.",
  "text":"Standardized testing should be abolished because it fails to measure real learning."},
 {"n":8,"desc":"Implicit claim","genre":"argumentative","aud":"general","assign":"Argue about fast fashion.","purpose":"Consider making an implicit claim explicit.","task":"Draft your thesis.",
  "text":"Fast fashion brands release dozens of collections a year. Landfills are filling with barely-worn clothes. Workers are paid pennies. Something about this cannot continue."},
 {"n":9,"desc":"Delayed claim (purposeful)","genre":"argumentative","aud":"engaged reader","assign":"Argue about surveillance in public spaces.","purpose":"Interpret a purposeful delay, not force early thesis.","task":"Draft your opening; thesis may come later.","note":"delay",
  "text":"The camera on the corner has been there so long that no one looks at it anymore. That is exactly the problem I want to build toward before I say what I think we should do."},
 {"n":10,"desc":"Distributed claim","genre":"analytical","aud":"class","assign":"Analyze a poem's treatment of time.","purpose":"Consolidate a distributed claim.","task":"Draft your thesis.",
  "text":"The poem keeps returning to clocks. It also mentions seasons more than once. The speaker seems afraid of aging. Time is clearly important throughout."},
 {"n":11,"desc":"Exploratory thesis","genre":"reflective","aud":"general","assign":"Write a reflective essay exploring a question about honesty.","purpose":"Value inquiry-driven organization.","task":"Draft your guiding thesis or question.",
  "text":"I want to understand whether honesty is always kind, or whether kindness sometimes requires a gentle untruth. I am not sure yet, and this essay is my attempt to find out."},
 {"n":12,"desc":"Interpretive thesis","genre":"literary_analysis","aud":"seminar","assign":"Interpret the ending of a novel.","purpose":"Sharpen an interpretive claim.","task":"Draft your thesis.",
  "text":"The novel's final silence is not emptiness but the character's first honest choice, and the book has been teaching us to read silence this way all along."},
 {"n":13,"desc":"Argumentative thesis","genre":"argumentative","aud":"public","assign":"Argue about single-use plastics.","purpose":"Extend a committed argumentative claim.","task":"Draft your thesis.",
  "text":"Cities should ban single-use plastics because the environmental cost far outweighs the minor convenience they provide."},
 {"n":14,"desc":"Analytical thesis","genre":"analytical","aud":"class","assign":"Analyze why a marketing campaign succeeded.","purpose":"Deepen a how/why analytical claim.","task":"Draft your thesis.",
  "text":"The campaign succeeded because it reframed a boring product as a marker of identity, turning buyers into advocates."},
 {"n":15,"desc":"Research question instead of thesis","genre":"research","aud":"academic","assign":"Write a research essay on urban heat islands.","purpose":"Coordinate a guiding question with an eventual claim.","task":"Draft your guiding question or thesis.",
  "text":"How does tree canopy coverage affect summer temperatures in low-income neighborhoods compared to wealthier ones?"},
 {"n":16,"desc":"Personal essay without explicit thesis","genre":"personal","aud":"general","assign":"Write a personal essay about a mentor.","purpose":"Allow a controlling insight without forcing a thesis.","task":"Draft your opening.",
  "text":"Mr. Alvarez never once told me I was talented. He just kept handing me harder problems, as if my confusion were a door rather than a wall."},
 {"n":17,"desc":"Narrative that should not be forced into a thesis","genre":"narrative","aud":"general","assign":"Write a narrative about a decision under pressure.","purpose":"Interpret narrative on its own terms.","task":"Draft your opening.",
  "text":"I had thirty seconds to decide, the whistle in my mouth and both teams staring, and the ball still rolling toward the line."},
 {"n":18,"desc":"Claim that does not match the assignment","genre":"argumentative","aud":"teacher","assign":"Argue whether homework improves learning.","purpose":"Check the claim addresses the assignment.","task":"Draft your thesis.",
  "text":"Teachers are underpaid and deserve a raise, which is the most important issue in education today."},
 {"n":19,"desc":"Claim that does not match the body","genre":"argumentative","aud":"general","assign":"Argue about zoos.","purpose":"Align claim with the argument the body makes.","task":"Draft your thesis and first point.",
  "text":"Zoos should be abolished. In fact, modern zoos fund conservation, protect endangered species, and educate millions of children every year, which is why they are so valuable."},
 {"n":20,"desc":"Claim that changes during revision","genre":"argumentative","aud":"general","assign":"Argue about electric cars.","purpose":"Notice and support a shifting claim.","task":"Draft your thesis.","revision":True,
  "text":"Electric cars are good for the environment.",
  "revised":"Electric cars reduce tailpipe emissions, but unless the electricity that charges them comes from clean sources, their climate benefit is smaller than most buyers assume."},
 {"n":21,"desc":"Formulaic three-part thesis","genre":"argumentative","aud":"teacher","assign":"Argue about junk food in schools.","purpose":"Help the parts cohere, not fill a template.","task":"Draft your thesis.",
  "text":"Junk food should be banned in schools because it is unhealthy, it is distracting, and it is expensive."},
 {"n":22,"desc":"Strong conventional thesis","genre":"argumentative","aud":"informed public","assign":"Argue about voting age.","purpose":"Extend an already strong claim.","task":"Draft your thesis.",
  "text":"Lowering the voting age to sixteen would strengthen democracy, because sixteen-year-olds already bear adult responsibilities the state expects them to take seriously, and early voting builds lifelong civic habits."},
 {"n":23,"desc":"Strong unconventional thesis","genre":"argumentative","aud":"literary reader","assign":"Argue about how we measure success.","purpose":"Honor a purposeful unconventional claim.","task":"Draft your thesis.",
  "text":"Ask most people to define success and they will describe a finish line; this essay argues that the metaphor itself is the problem, and that a life organized around finish lines is designed to feel like failure."},
 {"n":24,"desc":"Revision after a developmental invitation","genre":"argumentative","aud":"naive reader","assign":"Argue about phones in schools.","purpose":"Help form and support a central claim.","task":"Draft your thesis.","revision":True,
  "text":"Phones in schools are a problem.",
  "revised":"Because phones are engineered to capture attention, schools that allow unrestricted use during class are effectively competing with billion-dollar companies for their students' focus — and losing."},
]


def summarize(session):
    t = session["theory"]
    ir = session["interactions"][-1]
    ai = [x for x in session["turns"] if x["role"] == "ai"]
    inv = ir["selected_invitation"]["invitation"]
    return {
        "operative_purpose": session["telos"].get("immediate_task_purpose", ""),
        "current_organization": t.get("current_organization", ""),
        "supporting_evidence": t.get("supporting_evidence", []),
        "complicating_evidence": t.get("complicating_evidence", []),
        "alternative_interpretations": t.get("alternative_interpretations", []),
        "primary_tension": (t.get("unresolved_tensions") or [""])[0],
        "relevant_domains": t.get("currently_relevant_domains", []),
        "candidate_invitations": [c["invitation"] for c in ir["candidate_invitations"]],
        "selected_invitation": inv,
        "changes_since_previous": t.get("changes_since_previous", ""),
        "checks": {
            "one_invitation_this_turn": len(ai) == len(session["interactions"]),
            "thesis_selected": "Central Claim / Thesis" in t.get("currently_relevant_domains", []),
            "requires_action": bool(re.search(r"\?|identify|explain|revise|decide|compare|state|choose|check|consider|test|name|scope|define|finish", inv, re.I)),
            "no_stage_language": not STAGE_WORDS.search(inv) and not STAGE_WORDS.search(json.dumps(t)),
            "no_formula_imposition": not FORMULA_WORDS.search(inv),
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
            s = interact(sid, "writing", c["text"])
            rec = {"n": c["n"], "desc": c["desc"], "genre": c["genre"], "aud": c["aud"], "text": c["text"], "first": summarize(s)}
            if c.get("revision"):
                s2 = interact(sid, "revise", c["revised"])
                rec["revised_text"] = c["revised"]
                rec["second"] = summarize(s2)
                rec["theory_versions"] = len(s2["theory_history"])
            rec["elapsed_s"] = round(time.time() - t0, 1)
            print(f"case {c['n']} OK {rec['elapsed_s']}s domains={rec['first']['relevant_domains']} tension={rec['first']['primary_tension'][:55]!r}", flush=True)
            results.append(rec)
        except Exception as e:  # noqa: BLE001
            print(f"case {c['n']} FAILED: {e}", flush=True)
            results.append({"n": c["n"], "desc": c["desc"], "error": str(e)})
        json.dump(results, open("/app/backend/tests/milestone3_results.json", "w"), indent=2)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
