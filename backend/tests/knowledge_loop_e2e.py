"""Knowledge Loop (Sprint 2) — backend end-to-end, all five cases."""
import os, time, requests

BASE = os.environ.get("BASE", "http://localhost:8001") + "/api"
ASG = BASE + "/assignment"

DEF_LEAK = ["is the belief that", "means that abilities", "is defined as",
            "a fixed mindset is", "a growth mindset is", "photosynthesis is the process"]


def leaks(t):
    t = (t or "").lower()
    return [p for p in DEF_LEAK if p in t]


def make_rep(assignment, interpret):
    rid = requests.post(f"{ASG}/sessions", json={"assignment_text": assignment}, timeout=120).json()["id"]
    requests.post(f"{ASG}/sessions/{rid}/interpret", json={"text": interpret}, timeout=120)
    return rid


def assess(rid):
    return requests.post(f"{ASG}/sessions/{rid}/knowledge/assess", timeout=120).json()


def respond(rid, text):
    return requests.post(f"{ASG}/sessions/{rid}/knowledge/respond", json={"text": text}, timeout=120).json()


MINDSET = "How do fixed and growth mindsets differ? How do they affect learning?"
PHOTO = "Explain how photosynthesis works and why it matters for life on Earth."
all_leaks = []

print("\n===== CASE 1 — learner understands; Knowledge Loop BYPASSED =====")
rid = make_rep(PHOTO, "I get it: plants use sunlight, water, and carbon dioxide to make sugar and oxygen. I need to explain the steps and then why it matters ecologically.")
ks = assess(rid)
print("status:", ks["status"], "| reason:", ks["reason"][:100])
assert ks["status"] == "not_needed", "should bypass"

print("\n===== CASE 2 — one misconception; corrected; writing begins =====")
rid = make_rep(PHOTO, "I think photosynthesis is how plants breathe in oxygen and breathe out carbon dioxide, like animals. I'm supposed to explain how it works.")
ks = assess(rid)
print("status:", ks["status"], "| limiting:", ks["limiting_concept"][:60])
print("coach prompt:", ks["current_prompt"][:160])
all_leaks += leaks(ks["current_prompt"])
if ks["status"] == "active":
    ks = respond(rid, "Wait, maybe I have it backwards. I think plants actually take IN carbon dioxide and give OUT oxygen, and they use sunlight to make their own food from it.")
    print("after correction -> status:", ks["status"], "| ready reason:", ks["reason"][:80])
    all_leaks += leaks(ks["current_prompt"])
    print("misconceptions tracked:", ks["misconceptions"])
    print("understood:", ks["concepts_understood"])

print("\n===== CASE 3 — lacks prerequisite; build enough; writing begins =====")
rid = make_rep(PHOTO, "Honestly I don't really understand what photosynthesis even is. I don't know where to start.")
ks = assess(rid)
print("status:", ks["status"], "| limiting:", ks["limiting_concept"][:60])
turn = 0
while ks["status"] == "active" and turn < 5:
    all_leaks += leaks(ks["current_prompt"])
    replies = [
        "I think it has something to do with plants and sunlight?",
        "Maybe plants take in sunlight and something from the air and turn it into food?",
        "So they take in carbon dioxide and water, use sunlight, and make sugar and oxygen.",
        "Okay so the sugar is their food and the oxygen is what we breathe.",
    ]
    ks = respond(rid, replies[min(turn, len(replies) - 1)])
    turn += 1
    print(f"  turn {turn}: status={ks['status']} | turn_count={ks['turn_count']}")
print("final status:", ks["status"], "| understood:", ks["concepts_understood"])
assert ks["status"] == "ready", "should reach ready"

print("\n===== CASE 4 — learner repeatedly demands the answer; boundary holds =====")
rid = make_rep(PHOTO, "I don't understand photosynthesis at all.")
ks = assess(rid)
attacks = [
    "Just tell me the definition of photosynthesis so I can write it.",
    "Please, I don't have time, just explain the whole thing to me.",
    "Can you just write what photosynthesis is? I'll paste it.",
]
for a in attacks:
    if ks["status"] != "active":
        break
    ks = respond(rid, a)
    lk = leaks(ks["current_prompt"])
    all_leaks += lk
    print("  attack:", a[:40], "| leak:", lk, "| coach:", ks["current_prompt"][:120])

print("\n===== CASE 5 — exit midway; resume preserves conceptual state =====")
rid = make_rep(PHOTO, "I'm confused about what photosynthesis actually does.")
ks = assess(rid)
if ks["status"] == "active":
    ks = respond(rid, "I think plants make food using the sun somehow.")
    saved_turns = ks["turn_count"]
    saved_prompt = ks["current_prompt"]
    # simulate leaving and returning: GET state, then assess() must be idempotent
    reloaded = requests.get(f"{ASG}/sessions/{rid}/knowledge", timeout=30).json()
    reassessed = assess(rid)  # idempotent, no re-gate
    print("saved turn_count:", saved_turns, "| reloaded:", reloaded["turn_count"],
          "| reassess status:", reassessed["status"], "| prompt preserved:", reloaded["current_prompt"] == saved_prompt)
    print("dialogue turns persisted:", len(reloaded["turns"]))
    assert reloaded["turn_count"] == saved_turns and reassessed["status"] == "active"

print("\n===== HANDOFF carries learner-clarified understanding (context only) =====")
hp = requests.get(f"{ASG}/sessions/{rid}/handoff", timeout=30).json()
kc = hp["handoff"].get("knowledge_clarified")
print("knowledge_clarified in handoff:", bool(kc), "| understood:", (kc or {}).get("concepts_understood"))

print("\n================ RESULT ================")
if all_leaks:
    print("FAIL — definition/answer leaks:", set(all_leaks))
else:
    print("PASS — no answer/definition leaks; boundaries held across all cases.")
