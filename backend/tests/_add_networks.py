"""One-off: add `related_elements` (instructional network edges) to each object."""
import json, pathlib

P = pathlib.Path("/app/backend/instructional_objects.json")
kb = json.load(open(P))

REL = {
    "Purpose": ["Thesis", "Audience Awareness", "Organization", "Tone"],
    "Thesis": ["Purpose", "Central Claim", "Introduction", "Audience Awareness", "Organization", "Supporting Claim"],
    "Central Claim": ["Thesis", "Supporting Claim", "Evidence", "Qualification", "Counterargument"],
    "Supporting Claim": ["Central Claim", "Thesis", "Evidence", "Explanation / Analysis", "Paragraph", "Topic Sentence"],
    "Evidence": ["Central Claim", "Supporting Claim", "Explanation / Analysis", "Example", "Paragraph", "Audience Awareness"],
    "Explanation / Analysis": ["Evidence", "Central Claim", "Supporting Claim", "Reasoning", "Cause-and-Effect Explanation"],
    "Example": ["Evidence", "Explanation / Analysis", "Concept", "Supporting Detail"],
    "Counterargument": ["Central Claim", "Rebuttal / Response", "Qualification", "Audience Awareness"],
    "Rebuttal / Response": ["Counterargument", "Central Claim", "Qualification", "Evidence"],
    "Qualification": ["Central Claim", "Thesis", "Evidence", "Counterargument"],
    "Comparison": ["Contrast", "Organization", "Explanation / Analysis"],
    "Contrast": ["Comparison", "Organization", "Explanation / Analysis"],
    "Cause-and-Effect Explanation": ["Explanation / Analysis", "Evidence", "Reasoning"],
    "Classification": ["Organization", "Concept", "Definition"],
    "Transition": ["Coherence", "Organization", "Paragraph", "Topic Sentence"],
    "Topic Sentence": ["Paragraph", "Thesis", "Organization", "Coherence", "Supporting Claim"],
    "Supporting Detail": ["Paragraph", "Evidence", "Example", "Explanation / Analysis", "Unity"],
    "Concluding Sentence": ["Paragraph", "Topic Sentence", "Coherence", "Conclusion"],
    "Paragraph": ["Topic Sentence", "Supporting Detail", "Coherence", "Unity", "Organization", "Transition"],
    "Introduction": ["Thesis", "Hook / Opening Move", "Background / Context", "Purpose", "Audience Awareness"],
    "Hook / Opening Move": ["Introduction", "Purpose", "Audience Awareness"],
    "Background / Context": ["Introduction", "Audience Awareness", "Definition", "Thesis"],
    "Conclusion": ["Thesis", "Central Claim", "Purpose", "Concluding Sentence", "Organization"],
    "Title": ["Thesis", "Purpose"],
    "Sentence": ["Word Choice", "Coherence", "Tone", "Revision"],
    "Word Choice": ["Sentence", "Tone", "Voice", "Audience Awareness"],
    "Tone": ["Voice", "Word Choice", "Audience Awareness", "Purpose"],
    "Audience Awareness": ["Purpose", "Tone", "Background / Context", "Evidence", "Coherence"],
    "Organization": ["Thesis", "Paragraph", "Coherence", "Transition", "Purpose"],
    "Coherence": ["Transition", "Organization", "Unity", "Paragraph", "Sentence"],
    "Unity": ["Coherence", "Paragraph", "Thesis", "Purpose"],
    "Voice": ["Tone", "Word Choice", "Audience Awareness", "Revision"],
    "Revision": ["Purpose", "Coherence", "Organization", "Audience Awareness", "Sentence"],
    "Definition": ["Concept", "Background / Context", "Audience Awareness"],
    "Concept": ["Definition", "Example", "Classification"],
}

names = {o["element"] for o in kb["instructional_objects"]}
for o in kb["instructional_objects"]:
    rel = [r for r in REL.get(o["element"], []) if r in names]
    o["related_elements"] = rel

kb["note"] = kb.get("note", "") + " Each object now carries `related_elements` (instructional-network edges) so the engine can reason over a network, not an isolated object."
json.dump(kb, open(P, "w"), indent=2, ensure_ascii=False)
print("updated", len(kb["instructional_objects"]), "objects with related_elements")
for o in kb["instructional_objects"]:
    print(f"  {o['element']:<30} -> {o['related_elements']}")
