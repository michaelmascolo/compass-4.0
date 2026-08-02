"""Sprint 3 — enrich the Evidence instructional object IN PLACE (additive)."""
import json, copy, pathlib

PATH = pathlib.Path("/app/backend/instructional_objects.json")
kb = json.load(open(PATH))
objs = kb["instructional_objects"]
before_count = len(objs)
before_elements = [o["element"] for o in objs]

ev = next(o for o in objs if o["element"] == "Evidence")
snapshot = copy.deepcopy(ev)

ENRICH = {
    "reader_function": "Gives a skeptical reader concrete grounds to accept the claim; the test of evidence is not whether it is true but whether it gives THIS reader a reason to believe THIS claim.",
    "writer_function": "Forces the writer to choose what actually earns the claim and to represent it honestly; disciplines the writer against asserting more than the grounds allow.",

    "functional_relationships": {
        "purpose": "Evidence exists to serve a claim; with no claim yet worth supporting, evidence work is premature — repair the claim first.",
        "reader": "Calibrated to what a doubting reader would require and trust; irrelevant, thin, or untrusted grounds invite dismissal of the whole argument.",
        "neighboring_components": "Depends on a contestable Central Claim/Thesis; is completed by Explanation/Analysis (which states HOW it bears on the claim); an Example is one kind of evidence; Counterargument tests it.",
        "overall_organization": "Each body paragraph should marshal evidence for the one part of the thesis its topic sentence advances; evidence that fits no part signals drift."
    },

    # EXPERT ADDITION 1 — the four INDEPENDENT quality dimensions; each fails differently and is TAUGHT differently.
    "evidence_quality_dimensions": [
        {"dimension": "relevance", "test": "Does it bear on THIS claim (not a neighboring or background point)?",
         "failure_signal": "Real, credible information that actually supports a different proposition (e.g., 'there was a crisis' offered for 'the program fixed it').",
         "remedy": "Have the learner state exactly which proposition the evidence establishes, then compare it to the claim."},
        {"dimension": "sufficiency", "test": "Is there enough, and of the right kind, to carry the claim's SCOPE?",
         "failure_signal": "A single instance/anecdote offered as 'proof' for a general or strong claim.",
         "remedy": "Make scope and grounds meet: either narrow the claim to what the evidence can carry, or add representative evidence."},
        {"dimension": "credibility", "test": "Would the intended reader trust the source/kind of grounds?",
         "failure_signal": "Popularity, hearsay, an unvetted source, or personal feeling presented as authoritative grounds.",
         "remedy": "Ask what would make a skeptical reader trust this; move from 'people say' to grounds the reader accepts for this genre."},
        {"dimension": "accuracy", "test": "Is the evidence represented faithfully — not distorted, cherry-picked, or overstated?",
         "failure_signal": "The source says less (or other) than the learner claims it says; quotation wrenched from context.",
         "remedy": "Return to the source; state what it actually establishes and qualify the claim to match."}
    ],

    "common_difficulties": [
        {"type": "dropped_no_interpretation", "description": "Quote/fact inserted with no statement of how it bears on the claim (hand to Explanation)."},
        {"type": "irrelevant_or_background", "description": "Information that describes context or a neighboring point rather than grounds for THIS claim."},
        {"type": "insufficient", "description": "Too little, or a single anecdote, for the scope/strength of the claim."},
        {"type": "not_credible", "description": "Weak/unvetted source, popularity, or feeling treated as authoritative grounds."},
        {"type": "misrepresented", "description": "Evidence distorted, overstated, or cherry-picked; says less than claimed."},
        {"type": "circular", "description": "'Evidence' merely restates the claim in other words."},
        {"type": "over_citation", "description": "Piling many sources with no selection, so nothing is actually developed."}
    ],

    # EXPERT ADDITION 2 — same-looking situations that require DIFFERENT teaching (false pos/neg, same text/different understanding).
    "look_alike_distinctions": [
        {"surface": "A relevant-sounding fact that doesn't actually support the claim.",
         "could_be": "Background/context vs. outcome evidence (relevance failure) — LOOKS like support (false positive).",
         "distinguish_by": "Ask what proposition the fact establishes and hold it against the claim.",
         "teach_differently": "Do NOT ask for 'more explanation'; teach relevance — find evidence about the claim's actual point."},
        {"surface": "A single vivid personal story used as support.",
         "could_be": "Legitimate ILLUSTRATION of an already-supported point, OR an anecdote mistaken for PROOF (sufficiency).",
         "distinguish_by": "Ask whether the learner intends it to prove the claim or to illustrate it.",
         "teach_differently": "If proof-intent: teach representativeness/sufficiency. If illustration-intent: keep it, but ensure real grounds exist elsewhere."},
        {"surface": "A quotation/fact sitting after the claim with no comment.",
         "could_be": "Learner doesn't see interpretation is needed, OR assumes the connection is obvious to the reader.",
         "distinguish_by": "Ask the learner to say in their own words why it supports the claim.",
         "teach_differently": "If they can't: this is an Explanation gap. If they can but didn't write it: teach reader-awareness (the reader can't read your mind)."},
        {"surface": "A well-cited, fluent evidence paragraph.",
         "could_be": "Genuinely strong, OR fluent-but-off-claim evidence (false positive) the reader would still reject.",
         "distinguish_by": "Test each piece against the specific claim, not against the topic.",
         "teach_differently": "Praise fluency but redirect to relevance/selection rather than accepting polish as support."}
    ],

    "productive_misconceptions": [
        {"misconception": "More evidence makes a stronger argument.", "why_productive": "The learner wants to be convincing.", "leverage": "Redirect from quantity to relevance and selection: which ONE piece most earns the claim?"},
        {"misconception": "A quotation or statistic speaks for itself.", "why_productive": "The learner trusts sources and facts.", "leverage": "Show the reader still needs the writer to state what it proves — hand toward interpretation."},
        {"misconception": "My own experience proves the point.", "why_productive": "The learner draws on real, felt knowledge.", "leverage": "Move from 'my case' to representativeness — for whom, and how widely, does this hold?"},
        {"misconception": "If a fact is true, it supports my point.", "why_productive": "The learner values accuracy.", "leverage": "Separate 'true' from 'relevant to THIS claim' — truth is necessary, not sufficient."}
    ],

    "indicators_of_development": {
        "early": "Inserts facts/quotes because 'evidence is required'; cannot say what any piece proves; treats truth as sufficient.",
        "partial": "Selects on-topic evidence and can explain some connections when prompted, but misjudges relevance, sufficiency, or credibility and over/under-supports.",
        "independent": "Selects relevant, sufficient, credible evidence, represents it accurately, and explains its bearing without prompting.",
        "flexible": "Calibrates the kind and amount of evidence to genre, reader skepticism, and claim strength; anticipates and answers the doubting reader."
    },

    "recognition_diagnostics_detailed": {
        "attempting": "Quote the evidence and the claim it is meant to serve. Is the learner supporting, illustrating, or merely restating?",
        "control_level": "Score each dimension separately — relevance, sufficiency, credibility, accuracy — and map to early/partial/independent/flexible.",
        "likely_misconception": "Off-claim fact -> relevance; single anecdote as proof -> sufficiency; source/popularity -> credibility; overstates the source -> accuracy; restates claim -> circular.",
        "next_move": "Teach the ONE failing dimension that most blocks the reader now; do not pile multiple critiques."
    },

    # EXPERT ADDITION 3 — what counts as evidence, and the credibility/sufficiency bar, varies by genre/discipline.
    "genre_variation": {
        "literary_analysis": "Evidence = specific textual detail and accurate quotation; sufficiency = enough of the text to show a pattern, not one line.",
        "historical": "Evidence = primary/secondary sources, dates, documented outcomes; credibility = provenance; beware context offered as outcome.",
        "scientific": "Evidence = data, studies, mechanisms; anecdote is not proof; sufficiency = representative/replicable, not a single case.",
        "argument_persuasive": "Evidence = statistics, expert testimony, documented examples; calibrate to a skeptical general reader.",
        "personal_reflective": "Lived experience is legitimate evidence for claims about the writer's own experience, but not proof of general claims."
    },

    "developmental_invitations": [
        {"type": "clarify_what_it_proves", "purpose": "Have the learner state the exact proposition a piece of evidence establishes.", "use_when": "Relevance is in doubt or evidence is dropped.", "avoid_when": "The connection is already stated well."},
        {"type": "test_relevance", "purpose": "Hold the evidence against the specific claim (not the topic).", "use_when": "Background/off-claim information is offered as support.", "avoid_when": "Evidence is clearly on-claim."},
        {"type": "test_sufficiency", "purpose": "Ask whether the amount/kind can carry the claim's scope.", "use_when": "A single instance supports a broad/strong claim.", "avoid_when": "Support is already proportionate."},
        {"type": "test_credibility", "purpose": "Ask what would make a skeptical reader trust these grounds.", "use_when": "Source is weak/popular/hearsay for the genre.", "avoid_when": "Grounds are already trusted for the genre."},
        {"type": "check_accuracy", "purpose": "Return to the source and check it says what is claimed.", "use_when": "Possible overstatement or out-of-context quotation.", "avoid_when": "Representation is faithful."},
        {"type": "compare_candidates", "purpose": "Weigh two possible pieces of evidence to select the stronger.", "use_when": "The learner has several options or is over-citing.", "avoid_when": "There is no evidence yet to weigh."},
        {"type": "predict_reader_skepticism", "purpose": "Voice the doubting reader's objection to the evidence.", "use_when": "The learner assumes the evidence is self-evidently convincing.", "avoid_when": "The learner already anticipates objections."},
        {"type": "connect_to_claim", "purpose": "Ask the learner to explain HOW the evidence bears on the claim (hand toward Explanation).", "use_when": "Relevant evidence sits unconnected.", "avoid_when": "Relevance itself is the problem — fix that first."},
        {"type": "reflect", "purpose": "Have the learner state, in their own words, what makes evidence strong here.", "use_when": "Consolidating a gain.", "avoid_when": "The learner is still misjudging a dimension."}
    ],

    "followup_decisions": [
        {"after": "Learner shows the evidence is off-claim and finds a relevant piece.", "consider": "continue — now check sufficiency, then hand to Explanation for the connection."},
        {"after": "Learner narrows the claim to match a single case.", "consider": "continue — verify the narrowed claim still answers the task."},
        {"after": "Evidence is relevant/sufficient/credible but unconnected.", "consider": "change_target to Explanation/Analysis — evidence is no longer the bottleneck."},
        {"after": "Learner keeps treating an anecdote as proof.", "consider": "increase_support — offer compare_candidates or make the illustration-vs-proof distinction explicit."},
        {"after": "Learner independently selects and represents evidence well.", "consider": "conclude this target — consolidate and release."},
        {"after": "The underlying claim turns out to be the real weakness.", "consider": "change_target to Central Claim/Thesis — do not teach evidence for an unworthy claim."}
    ],

    "revision_strategies": [
        "Replace off-claim/background information with evidence about the claim's actual point.",
        "Right-size the fit: narrow the claim to what the evidence carries, or add representative evidence.",
        "Upgrade the grounds a skeptical reader would trust for this genre; drop popularity/hearsay.",
        "Return to the source and correct any overstatement or out-of-context use.",
        "Select the single strongest piece and cut redundant citations, then develop it.",
        "Follow each retained piece with one sentence stating what it proves (bridge to Explanation)."
    ],

    "stopping_conditions": [
        "Learner independently selects relevant, sufficient, credible, accurately-represented evidence and can say what it proves.",
        "Diminishing returns — the evidence substantially earns the claim for the intended reader.",
        "The connection (not the evidence) is now the bottleneck -> move to Explanation.",
        "The claim itself is the bottleneck -> move to Central Claim/Thesis.",
        "Learner requests independence; or teacher override designates another focus."
    ],

    "transfer": {
        "other_genres": "The relevance/sufficiency/credibility/accuracy test persists; only the KIND of admissible evidence changes by genre.",
        "other_assignments": "The habit of asking 'what would give a doubting reader grounds to believe THIS claim?' applies to any argument.",
        "other_disciplines": "Standards of evidence differ (textual, documentary, empirical); the learner learns to ask what each field will accept.",
        "future_writing": "Foundational for research, professional reports, and any writing where conclusions must be earned, not asserted."
    },

    "engine_usage": {
        "reader_function/writer_function": "target selection + interpretation (why evidence matters now, from the reader's grounds)",
        "functional_relationships": "target selection — is EVIDENCE the bottleneck vs. the claim (upstream) or the explanation (downstream)",
        "evidence_quality_dimensions": "diagnostics — score relevance/sufficiency/credibility/accuracy SEPARATELY and pick the one failing dimension",
        "common_difficulties/recognition_diagnostics_detailed": "diagnostics — name what the learner is attempting + the specific fault",
        "look_alike_distinctions": "diagnostics + invitation — resolve same-looking cases that need different teaching (false positives/negatives)",
        "productive_misconceptions": "instructional invitation — turn an evidence error into a stepping stone",
        "genre_variation": "diagnostics + interpretation — calibrate the credibility/sufficiency bar to the genre",
        "indicators_of_development": "interpretation (degree_of_student_control) + stopping",
        "developmental_invitations": "instructional invitation — choose ONE type matched to the failing dimension (honor use_when/avoid_when)",
        "followup_decisions": "instructional decision — continue / retarget (claim or explanation) / +support / conclude",
        "revision_strategies": "instructional invitation for functional revision",
        "stopping_conditions": "stopping / session closure",
        "transfer": "session closure — consolidation + transfer note"
    },
    "enrichment_version": "sprint3-v1"
}

ev.update(ENRICH)
json.dump(kb, open(PATH, "w"), indent=1, ensure_ascii=False)

after = json.load(open(PATH))["instructional_objects"]
ev2 = next(o for o in after if o["element"] == "Evidence")
print("object count:", before_count, "->", len(after), "(unchanged)" if before_count == len(after) else "CHANGED!")
print("elements identical:", before_elements == [o["element"] for o in after])
print("original fields preserved:", all(k in ev2 for k in snapshot))
print("new fields added:", [k for k in ENRICH if k not in snapshot])
