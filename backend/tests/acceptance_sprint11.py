"""Sprint 1.1 acceptance test: task-requirement scaffolding without answer content."""
import os, requests, json, re

BASE = os.environ.get("BASE", "http://localhost:8001") + "/api/assignment"
ASSIGNMENT = "How do fixed and growth mindsets differ? How do they affect learning?"

# Substantive-answer leak detectors: phrases where the AI ITSELF asserts a definition.
LEAK_PATTERNS = [
    r"is the belief that", r"means that abilities",
    r"is defined as", r"is the assumption that",
    r"refers to the (?:belief|idea|view)",
    r"is the (?:idea|view|theory) that (?:ability|abilities|intelligence|talent)",
]

def leaks(text):
    t = (text or "").lower()
    return [p for p in LEAK_PATTERNS if re.search(p, t)]

def show_scaffold(sess, label):
    sc = sess.get("current_scaffold") or {}
    task = sc.get("studentTask", "")
    print(f"\n--- {label} [L{sc.get('level')} {sc.get('instructionType')}] target={sess.get('active_target_id','')[:14]}")
    print("studentTask:", task)
    lk = leaks(task)
    if lk:
        print("!!! ANSWER-CONTENT LEAK:", lk)
    return sc, lk

all_leaks = []

# 1. Create
r = requests.post(f"{BASE}/sessions", json={"assignment_text": ASSIGNMENT}, timeout=120)
r.raise_for_status()
sess = r.json()
sid = sess["id"]
print("SESSION:", sid, "| level:", sess.get("educational_level"), "| stage:", sess.get("stage"))
print("\nDEMANDS:")
for d in sess["demands"]:
    print(f"  [{d['source']}/{d['priority']}/{d['category']}] {d['label']} ({d['operation']}) — {d['description']}")
    all_leaks += leaks(d["description"])
print("distinctions:", sess.get("important_distinctions"))

# 2. Weak interpretation: learner has NOT yet realized definitions are needed first.
weak = "I think it's asking me to talk about mindsets and learning."
r = requests.post(f"{BASE}/sessions/{sid}/interpret", json={"text": weak}, timeout=120)
r.raise_for_status()
sess = r.json()
sc, lk = show_scaffold(sess, "after interpret")
all_leaks += lk

# 3. Learner infers the task requirement (definitions before comparison)
resp1 = "Oh, I need to explain what each mindset actually is before I can compare them."
r = requests.post(f"{BASE}/sessions/{sid}/operation", json={"text": resp1}, timeout=120)
r.raise_for_status()
sess = r.json()
sc, lk = show_scaffold(sess, "after inferring task requirement")
all_leaks += lk

# 4. If asked to actually define, learner performs the work; AI must NOT have supplied it,
#    and evaluation must not generate a definition.
resp2 = "A fixed mindset is believing your abilities are set and can't really improve, while a growth mindset is believing you can develop your abilities through effort."
r = requests.post(f"{BASE}/sessions/{sid}/operation", json={"text": resp2}, timeout=120)
r.raise_for_status()
sess = r.json()
sc, lk = show_scaffold(sess, "after learner-provided definition")
all_leaks += lk
last_op = [i for i in sess["interactions"] if i["kind"] == "operation"][-1]
print("evaluation.reason:", last_op["evaluation"].get("reason"),
      "| operation_performed:", last_op["evaluation"].get("operation_performed"))
all_leaks += leaks(last_op["evaluation"].get("learner_evidence", ""))

print("\n================ RESULT ================")
if all_leaks:
    print("FAIL — answer-content leaks detected:", set(all_leaks))
else:
    print("PASS — no answer-content leaks. AI scaffolded task requirements only.")
