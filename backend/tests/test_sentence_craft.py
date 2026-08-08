import sys, json, time, requests

with open("/app/frontend/.env") as f:
    for line in f:
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE = line.strip().split("=", 1)[1]
API = f"{BASE}/api"

s = requests.post(f"{API}/sessions", json={
    "assignment": "Explain what a growth mindset is and how it shapes the way students respond to failure.",
    "pedagogical_purpose": "Develop the learner's ability to define and explain a concept for a reader.",
    "current_writing_task": "One paragraph.",
    "assignment_prompt": "What is a growth mindset and how does it shape how students respond to failure?",
    "reasoning_mode": "canonical_v2",
}, timeout=30)
s.raise_for_status()
sid = s.json()["id"]
print("SESSION", sid)
draft = ("The growth mindset is the most beneficial and positive way of thinking. "
         "Having a growth mindset means believing your abilities are able to be changed and made better. "
         "When students fail, they don't give up. They keep trying because they think they can get better. "
         "This is why a growth mindset is so important for learning.")
requests.post(f"{API}/sessions/{sid}/interact", json={"content": draft, "kind": "writing"}, timeout=30).raise_for_status()

# wait for the DCO turn to complete (sentence_craft_readiness present)
readiness = None
for i in range(70):
    time.sleep(4)
    tr = requests.get(f"{API}/dev/functional-v3-trace/{sid}", timeout=30)
    if tr.status_code == 200:
        t = tr.json().get("trace", [])
        if t and t[-1].get("developmental_cognition", {}).get("sentence_craft_readiness"):
            readiness = t[-1]["developmental_cognition"]["sentence_craft_readiness"]
            break
print("\n=== sentence_craft_readiness (from DCO) ===")
print(json.dumps(readiness, indent=2, ensure_ascii=False))

# now hit the dedicated sentence-craft endpoint
r = requests.get(f"{API}/dev/sentence-craft/{sid}", timeout=120)
print("\nendpoint status:", r.status_code)
if r.status_code != 200:
    print("BODY:", r.text[:500]); sys.exit(1)
data = r.json()
cog = data.get("sentence_craft_cognition") or {}
sents = cog.get("sentences") or []
print("\nsentence count:", len(sents))
for s in sents:
    print(f"  #{s['sentence_index']} [{s['beginning_character_offset']}-{s['ending_character_offset']}] "
          f"imp={s.get('importance_to_whole')} prio={s.get('teaching_priority')} purpose={s.get('communicative_purpose','')[:60]}")
    if s.get("observed_sentence_patterns"):
        print("      patterns:", "; ".join(s["observed_sentence_patterns"]))
# verify offsets map back to the exact draft substring
offsets_ok = all(draft[s["beginning_character_offset"]:s["ending_character_offset"]] == s["exact_sentence_text"] for s in sents)
print("\noffsets map exactly to draft:", offsets_ok)
st = cog.get("selected_teaching")
print("\n=== selected_teaching ===")
print(json.dumps(st, indent=2, ensure_ascii=False))
print("\npost_revision schema present:", bool(cog.get("post_revision_evaluation_schema")))
ok = (len(sents) >= 3 and offsets_ok and isinstance(st, dict) and st.get("pattern_noticed")
      and st.get("instructional_principle") and st.get("learner_invitation"))
print("\nRESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
