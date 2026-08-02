"""Milestone 5 — Developmental Instruction Layer evaluation (30 scenarios).
Tests whether the engine chooses an appropriate intervention type
(interpret-only / instruct-then-invite / invite-only / consolidate / postpone)
for six student profiles across Opening, Thesis, and Paragraph Purpose."""
import json
import time
import requests

BASE = "http://localhost:8001/api"
ALLOWED = {"interpretation_only", "instruct_then_invite", "invite_only", "consolidate", "postpone_instruction"}


def create_session(a, p, t):
    r = requests.post(f"{BASE}/sessions", json={"assignment": a, "pedagogical_purpose": p, "current_writing_task": t, "teacher_notes": ""}, timeout=30)
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


OP = "Write an introduction that draws a reader in and frames why the issue matters."
TH = "Help the student form and clarify a central claim that organizes the essay."
PA = "Help the student clarify what each paragraph is doing for the essay."
A_ARG = "Argue whether social media improves or harms teen friendships."

# profile: acceptable intervention types
ACCEPT = {
 "already_understands": {"invite_only", "interpretation_only"},
 "misuses": {"instruct_then_invite", "interpretation_only", "invite_only"},
 "discovered_without_name": {"consolidate", "invite_only", "interpretation_only", "instruct_then_invite"},
 "rigid_formula": {"instruct_then_invite", "interpretation_only", "invite_only"},
 "needs_instruction": {"instruct_then_invite"},
 "needs_less": {"interpretation_only", "invite_only", "postpone_instruction"},
}

CASES = [
 # --- needs explicit instruction (P5) ---
 (1,"needs_instruction","Opening",OP,"Draft your introduction.","Social media is a thing teens use. This essay is about social media and friends.",None),
 (2,"needs_instruction","Thesis",TH,"Draft your thesis.","My essay is about social media and friendship.",None),
 (3,"needs_instruction","Paragraph",PA,"Draft a body paragraph.","There are many things about social media. It is used a lot. People post things.",None),
 (4,"needs_instruction","Opening",OP,"Draft your introduction.","Phones exist. Teens have phones. The end of the intro.",None),
 (5,"needs_instruction","Thesis",TH,"Draft your thesis.","Social media."),
 # --- already understands (P1) ---
 (6,"already_understands","Opening",OP,"Draft your introduction.","Picture a sixteen-year-old with 800 online 'friends' who eats lunch alone every day. That contradiction is where this essay begins, because it exposes what we really mean when we call an app 'social.'",None),
 (7,"already_understands","Thesis",TH,"Draft your thesis.","Social media strengthens weak-tie friendships while quietly eroding the close ones, because it rewards breadth of contact over depth of attention.",None),
 (8,"already_understands","Paragraph",PA,"Draft a body paragraph.","Consider how a group chat behaves at midnight. Messages pile up, in-jokes form, and no one wants to be the first to log off — the paragraph's point being that constant availability manufactures a closeness that daylight rarely tests.",None),
 (9,"already_understands","Opening",OP,"Draft your introduction.","We assume 'more connection' is always better. This essay questions that assumption, starting from a simple observation: the teens who post most often are often the ones who feel most alone.",None),
 (10,"already_understands","Thesis",TH,"Draft your thesis.","The problem is not screen time but attention: social media harms teen friendship precisely when it replaces undivided attention with performed presence.",None),
 # --- misuses the concept (P2) ---
 (11,"misuses","Opening",OP,"Draft your introduction.","Did you know the average person blinks 20,000 times a day? Anyway, this essay is about whether social media helps teen friendships.",None),
 (12,"misuses","Thesis",TH,"Draft your thesis.","Social media is very popular and important and everyone uses it a lot these days.",None),
 (13,"misuses","Paragraph",PA,"Draft a body paragraph.","Social media affects friendships. Friendships are important. Everyone has friends. This paragraph is about friendships and social media and how they are connected in many ways.",None),
 (14,"misuses","Opening",OP,"Draft your introduction.","Webster's dictionary defines friendship as 'the state of being friends.' Social media is websites. This essay combines them.",None),
 (15,"misuses","Thesis",TH,"Draft your thesis.","In this essay I will discuss and talk about social media and its effects on teenagers today.",None),
 # --- discovered strategy without knowing its name (P3) ---
 (16,"discovered_without_name","Opening",OP,"Draft your introduction.","I want to open by describing my own group chat blowing up during a fight between two friends, because I think a reader will get pulled into the tension right away and see why this matters.",None),
 (17,"discovered_without_name","Thesis",TH,"Draft your thesis.","I keep coming back to one idea in my notes: it's not that social media is good or bad, it's that it changes what counts as paying attention to a friend. I think that's the real thing my essay is about.",None),
 (18,"discovered_without_name","Paragraph",PA,"Draft a body paragraph.","I put the surprising statistic first and then explained what I think it means for real friendships, so the reader sees the fact and then sees why it matters before I move on.",None),
 (19,"discovered_without_name","Opening",OP,"Draft your introduction.","I started with a question I actually can't answer yet — 'can you really know someone you've never been bored with?' — because I want the reader wondering along with me.",None),
 (20,"discovered_without_name","Paragraph",PA,"Draft a body paragraph.","This paragraph is really just setting up the next one — I admit the good side of social media here so that when I push back in the following paragraph it lands harder.",None),
 # --- rigid formula reliance (P4) ---
 (21,"rigid_formula","Opening",OP,"Draft your introduction.","Have you ever wondered about social media? Social media has been around since the early 2000s. In this essay I will argue that social media harms teen friendships because of three reasons.",None),
 (22,"rigid_formula","Thesis",TH,"Draft your thesis.","Social media harms teen friendships because it is distracting, because it is fake, and because it is addictive.",None),
 (23,"rigid_formula","Paragraph",PA,"Draft a body paragraph.","Topic sentence: Social media is distracting. Evidence: Teens check phones 100 times a day. Analysis: This shows it is distracting. Concluding sentence: Therefore social media is distracting.",None),
 (24,"rigid_formula","Opening",OP,"Draft your introduction.","Hook. Background about social media history. Thesis: social media is bad for friendships for three reasons that I will list now.",None),
 (25,"rigid_formula","Thesis",TH,"Draft your thesis.","This essay will prove that social media is harmful using reason one, reason two, and reason three.",None),
 # --- needs less instruction, not more (P6) ---
 (26,"needs_less","Opening",OP,"Draft your introduction.","A year ago my best friend and I stopped talking, and it happened entirely in the spaces between text messages — the read receipts, the slow replies, the story she posted but didn't send to me.",None),
 (27,"needs_less","Thesis",TH,"Draft your thesis.","Social media doesn't destroy friendship; it exposes how fragile some friendships were to begin with.",None),
 (28,"needs_less","Paragraph",PA,"Draft a body paragraph.","When a friend 'likes' your post but never texts back, the gesture says everything: presence without contact, acknowledgment without care. That gap is the whole problem this paragraph names.",None),
 (29,"needs_less","Opening",OP,"Draft your introduction.","There is a specific loneliness that only arrives after you close a very active group chat. This essay is about that feeling, and what it reveals about online friendship.",None),
 (30,"needs_less","Thesis",TH,"Draft your thesis.","The closer a friendship is, the less social media seems to help it — and that inverse relationship is what this essay sets out to explain.",None),
]

# revision follow-ups to test consolidation (append 3 two-turn cases reusing needs_instruction openers)
REVISIONS = {
 1: "Picture scrolling through 300 friends' posts and realizing you haven't actually spoken to any of them in weeks. That quiet gap between 'connected' and 'close' is what this essay is really about.",
 3: "This paragraph does one job: it shows that constant posting can crowd out real conversation. A teen who documents every moment, I'll argue, often has less to say when a friend actually needs them.",
}


def summ(s):
    ir = s["interactions"][-1]
    iv = ir["intervention"]
    ai = [x for x in s["turns"] if x["role"] == "ai"]
    inv = ir["selected_invitation"]["invitation"]
    return {"type": iv["type"], "cultural_resource": iv["cultural_resource"],
            "interpretation": iv["interpretation"], "instruction": iv["instruction"],
            "consolidation": iv["consolidation"], "timing": iv["timing_rationale"],
            "student_facing": s["turns"][-1]["content"], "invitation": inv,
            "domains": s["theory"]["currently_relevant_domains"],
            "one_invitation": len(ai) == len(s["interactions"]),
            "instr_has_content": bool(iv["instruction"].strip()) if iv["type"] in ("instruct_then_invite",) else True,
            "consol_has_content": bool(iv["consolidation"].strip()) if iv["type"] == "consolidate" else True}


def main():
    res = []
    for (n, profile, domain, purpose, task, text, _extra) in [(c[0], c[1], c[2], c[3], c[4], c[5], None) for c in CASES]:
        t0 = time.time()
        try:
            sid = create_session(A_ARG, purpose, task)
            s = interact(sid, "writing", text)
            r = {"n": n, "profile": profile, "domain": domain, "text": text, "first": summ(s)}
            if n in REVISIONS:
                s2 = interact(sid, "revise", REVISIONS[n])
                r["second"] = summ(s2)
                r["theory_versions"] = len(s2["theory_history"])
            r["ok_type"] = r["first"]["type"] in ACCEPT[profile]
            r["elapsed_s"] = round(time.time() - t0, 1)
            print(f"case {n} [{profile}/{domain}] type={r['first']['type']} ok={r['ok_type']} {r['elapsed_s']}s", flush=True)
            res.append(r)
        except Exception as e:  # noqa: BLE001
            print(f"case {n} FAILED: {e}", flush=True)
            res.append({"n": n, "profile": profile, "error": str(e)})
        json.dump(res, open("/app/backend/tests/milestone5_results.json", "w"), indent=2)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
