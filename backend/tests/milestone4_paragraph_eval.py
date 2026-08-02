"""Milestone 4 — Paragraph Purpose exemplar evaluation harness.
Streams SSE /interact on localhost:8001; records the engine's reasoning for 24
paragraph cases (incl. revision case); writes JSON + a markdown review table."""
import json
import time
import re
import requests

BASE = "http://localhost:8001/api"
STAGE = re.compile(r"\b(level|score|grade\b|rubric|proficien|novice|competen)\b", re.I)
FORMULA = re.compile(r"\b(must (start|begin|have|include) a topic sentence|need a topic sentence|every paragraph must|claim[- ]evidence[- ]analysis is required|topic sentence must be (the )?first)\b", re.I)


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


A_ARG = "Write an argumentative essay about whether cities should reduce car traffic downtown."
P_PARA = "Help the student clarify what each paragraph is doing for the essay and coordinate it with the whole."
CASES = [
 {"n":1,"desc":"Topic but no clear purpose","genre":"argumentative","assign":A_ARG,"purpose":P_PARA,"task":"Draft a body paragraph.",
  "text":"There are many things about traffic downtown. Traffic is a big topic. Downtown areas have a lot of cars and people and stores and buses."},
 {"n":2,"desc":"Clear purpose, disconnected from whole","genre":"argumentative","assign":A_ARG,"purpose":P_PARA,"task":"Draft a body paragraph.",
  "text":"Bicycles are an efficient form of transport. A cyclist can travel four times faster than a walker using the same energy, and bikes take up little space. Cycling is also good exercise."},
 {"n":3,"desc":"Several competing purposes","genre":"argumentative","assign":A_ARG,"purpose":P_PARA,"task":"Draft a body paragraph.",
  "text":"Downtown congestion wastes hours. Also, my uncle drives a delivery truck and says parking is impossible. Meanwhile, air quality studies show particulates rise near intersections, and some cities have beautiful pedestrian squares."},
 {"n":4,"desc":"Changes purpose midway","genre":"argumentative","assign":A_ARG,"purpose":P_PARA,"task":"Draft a body paragraph.",
  "text":"Reducing car traffic would cut emissions significantly, since transport is a leading source of urban CO2. Speaking of downtown, the new food hall on Main Street has fifteen vendors and is always crowded on weekends."},
 {"n":5,"desc":"Clear function, no explicit topic sentence","genre":"argumentative","assign":A_ARG,"purpose":P_PARA,"task":"Draft a body paragraph.",
  "text":"First the buses slowed. Then delivery vans double-parked. By eight-thirty the intersection was gridlocked and an ambulance sat trapped for four minutes. Scenes like this repeat across the city every morning, which is exactly why the current system cannot continue."},
 {"n":6,"desc":"Formulaic topic sentence that does not govern","genre":"argumentative","assign":A_ARG,"purpose":P_PARA,"task":"Draft a body paragraph.",
  "text":"Cars cause pollution. My favorite car is a red convertible. Convertibles look cool in movies. Some actors drive them in famous scenes."},
 {"n":7,"desc":"Evidence without interpretation","genre":"argumentative","assign":A_ARG,"purpose":P_PARA,"task":"Draft a body paragraph.",
  "text":"A 2019 study found downtown traffic dropped 22% after congestion pricing in one city. Retail revenue changed by 4%. Bus ridership rose 11%. Average commute times fell by nine minutes."},
 {"n":8,"desc":"Interpretation without sufficient evidence","genre":"argumentative","assign":A_ARG,"purpose":P_PARA,"task":"Draft a body paragraph.",
  "text":"Clearly, reducing cars would transform downtown into a thriving, healthier, more human place where everyone would be happier and businesses would boom like never before."},
 {"n":9,"desc":"Supplies necessary context","genre":"research","assign":"Write a research essay on congestion pricing.","purpose":P_PARA,"task":"Draft a context paragraph.",
  "text":"Congestion pricing charges drivers a fee to enter a defined zone during peak hours. London introduced it in 2003 and Stockholm in 2007. Understanding how these systems are designed is necessary before evaluating their effects."},
 {"n":10,"desc":"Overloaded with unnecessary background","genre":"research","assign":"Write a research essay on congestion pricing.","purpose":P_PARA,"task":"Draft a paragraph.",
  "text":"The wheel was invented around 3500 BCE. Roman roads spanned 80,000 km. The Model T appeared in 1908. Highways expanded after 1956. Traffic lights were patented in 1923. Eventually cities became congested and someone proposed charging drivers."},
 {"n":11,"desc":"Develops the central claim","genre":"argumentative","assign":A_ARG,"purpose":P_PARA,"task":"Draft a body paragraph.",
  "text":"If cities reduce car traffic, the freed street space becomes the argument's strongest asset. A single traffic lane converted to a bus-and-bike corridor moves several times more people per hour, which means the same street serves more residents without expanding at all."},
 {"n":12,"desc":"Repeats the thesis without developing","genre":"argumentative","assign":A_ARG,"purpose":P_PARA,"task":"Draft a body paragraph.",
  "text":"Cities should reduce car traffic downtown. It is important for cities to reduce the amount of car traffic. Reducing downtown car traffic is something cities should do because it would reduce car traffic downtown."},
 {"n":13,"desc":"Complicates or qualifies the thesis","genre":"argumentative","assign":A_ARG,"purpose":P_PARA,"task":"Draft a body paragraph.",
  "text":"Reducing car traffic helps most residents, but not all equally. Shift workers who finish after transit stops and people with mobility impairments may lose access unless the plan funds alternatives, which complicates the simple case for a ban."},
 {"n":14,"desc":"Acknowledges another perspective","genre":"argumentative","assign":A_ARG,"purpose":P_PARA,"task":"Draft a body paragraph.",
  "text":"Small-business owners often oppose car restrictions. They argue that customers who cannot drive and park will simply shop elsewhere, and that deliveries become harder and more expensive."},
 {"n":15,"desc":"Responds to an objection","genre":"argumentative","assign":A_ARG,"purpose":P_PARA,"task":"Draft a body paragraph.",
  "text":"Business owners fear losing driving customers. But data from pedestrianized districts shows foot traffic and spending often rise, because people on foot linger and return more often than drivers who park briefly, so the feared losses rarely materialize."},
 {"n":16,"desc":"Transitional / bridge paragraph","genre":"argumentative","assign":A_ARG,"purpose":P_PARA,"task":"Draft a bridge paragraph.",
  "text":"So far the case has rested on efficiency and emissions. But numbers alone do not decide how a city should feel to the people who live in it. The next question is therefore not what works, but what kind of downtown we actually want."},
 {"n":17,"desc":"Narrative paragraph (not forced into argument)","genre":"narrative","assign":"Write a narrative about a morning commute.","purpose":P_PARA,"task":"Draft a paragraph.",
  "text":"The 7:14 was already packed when I squeezed on. A man's umbrella dripped onto my shoe. Somewhere near the bridge the train stopped, the lights flickered, and for a moment the whole car went silent and still."},
 {"n":18,"desc":"Reflective paragraph around uncertainty","genre":"reflective","assign":"Write a reflective essay about how you move through your city.","purpose":P_PARA,"task":"Draft a paragraph.",
  "text":"I am not sure whether I hate the traffic or depend on it. The jams are maddening, yet the car is the only place all day where no one asks anything of me. Maybe what I resent is not the congestion but the fact that I need it."},
 {"n":19,"desc":"Descriptive serving a larger analytical purpose","genre":"analytical","assign":"Analyze how a public plaza shapes behavior.","purpose":P_PARA,"task":"Draft a paragraph.",
  "text":"The plaza slopes gently toward a shallow fountain ringed by wide, backless stone ledges. There are no signs, no gates, and no single entrance. People drift in from four directions and settle facing one another rather than the street."},
 {"n":20,"desc":"Weakness caused by mismatch with assignment","genre":"argumentative","assign":"Argue specifically about congestion pricing (not car bans).","purpose":P_PARA,"task":"Draft a body paragraph.",
  "text":"Electric cars are the real solution. As batteries improve and charging spreads, downtown emissions will fall without restricting anyone's driving at all, so the city should focus on incentivizing EV adoption."},
 {"n":21,"desc":"Works only with the preceding paragraph","genre":"argumentative","assign":A_ARG,"purpose":P_PARA,"task":"Draft the paragraph that follows your evidence paragraph.",
  "text":"This is why the objection collapses. If even the merchants' own sales data point the other way, then the strongest practical argument against the plan is really an argument for it."},
 {"n":22,"desc":"Function clear only via the following paragraph","genre":"argumentative","assign":A_ARG,"purpose":P_PARA,"task":"Draft a paragraph that sets up your next point.",
  "text":"Consider what a street is actually for. Not, at first, for any particular mode of travel, but for the movement and gathering of people. Hold that question for a moment."},
 {"n":23,"desc":"Strong unconventional paragraph organization","genre":"argumentative","assign":A_ARG,"purpose":P_PARA,"task":"Draft a body paragraph.",
  "text":"Ten thousand cars. Forty parked delivery vans. One ambulance, motionless. Now subtract the private cars and run the morning again: the vans still deliver, the buses flow, the ambulance arrives in ninety seconds. The difference is not magic; it is arithmetic about space."},
 {"n":24,"desc":"Revision that reorganizes paragraph purpose after an invitation","genre":"argumentative","assign":A_ARG,"purpose":P_PARA,"task":"Draft a body paragraph.","revision":True,
  "text":"Downtown has a lot of traffic. There are cars and buses and trucks. Parking is hard. Pollution is bad. It is a problem.",
  "revised":"The clearest cost of downtown car traffic is space. Private cars occupy the majority of road area while carrying a minority of travelers, which means that every lane devoted to them is a lane not serving the buses, deliveries, and emergency vehicles the city actually depends on."},
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
            "paragraph_selected": "Paragraph Purpose" in t.get("currently_relevant_domains", []),
            "no_stage_language": not STAGE.search(inv) and not STAGE.search(json.dumps(t)),
            "no_formula_imposition": not FORMULA.search(inv),
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
            rec = {"n": c["n"], "desc": c["desc"], "genre": c["genre"], "text": c["text"], "first": summarize(s)}
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
        json.dump(results, open("/app/backend/tests/milestone4_results.json", "w"), indent=2)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
