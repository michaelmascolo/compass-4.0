"""Sprint 3 — enrich the Explanation / Analysis instructional object IN PLACE (additive).
Introduces the standard 'instructionally_significant_discriminations' section."""
import json, copy, pathlib

PATH = pathlib.Path("/app/backend/instructional_objects.json")
kb = json.load(open(PATH))
objs = kb["instructional_objects"]
before_count = len(objs)
before_elements = [o["element"] for o in objs]

ex = next(o for o in objs if o["element"] == "Explanation / Analysis")
snapshot = copy.deepcopy(ex)

ENRICH = {
    "reader_function": "Supplies the reasoning a reader needs to see WHY the evidence means what the writer says it means; makes the hidden 'because' (the warrant) visible so the reader can follow, not just be told.",
    "writer_function": "Forces the writer to make their own thinking explicit and inspectable, exposing leaps, missing warrants, and unsupported causal claims the writer had only assumed.",

    "functional_relationships": {
        "purpose": "Explanation turns evidence into support FOR the claim; without it, evidence and claim sit adjacent but unconnected.",
        "reader": "Written for a reader who does NOT already share the writer's reasoning; the test is whether such a reader could follow each step.",
        "neighboring_components": "Follows Evidence (which supplies the grounds) and serves the Central Claim (which it earns); a missing warrant is often mistaken for an Evidence problem but is an Explanation problem.",
        "overall_organization": "Each piece of evidence should be followed by the reasoning that ties it to the paragraph's point; unexplained evidence signals a reasoning gap, not necessarily a content gap."
    },

    "common_difficulties": [
        {"type": "no_reasoning", "description": "Evidence and claim sit adjacent with no interpretive step ('this shows X') — the 'because' is missing."},
        {"type": "restatement", "description": "The 'explanation' repeats or summarizes the evidence in other words instead of reasoning about it."},
        {"type": "description_not_reasoning", "description": "States WHAT happens/appears rather than WHY it matters or HOW it supports the claim."},
        {"type": "example_for_explanation", "description": "Adds another example instead of the reasoning that connects examples to the claim."},
        {"type": "missing_warrant", "description": "A causal or inferential leap is asserted; the principle linking evidence to conclusion is unstated."},
        {"type": "unsupported_causation", "description": "Correlation or sequence is presented as cause without ruling out other explanations."},
        {"type": "overgeneralization", "description": "Leaps from a specific instance to a broad conclusion the reasoning does not license."}
    ],

    # NEW STANDARD SECTION — expert diagnostic discrimination (A–F per case).
    "instructionally_significant_discriminations": [
        {
            "observable_performance": "The learner gives NO explanation — evidence is dropped next to the claim.",
            "possible_interpretations": [
                "Does not yet understand how the evidence connects (cannot reason it).",
                "Understands the connection but assumes the reader already sees it.",
                "Can reason but cannot organize/sequence the explanation.",
                "Believes evidence 'speaks for itself' and no explanation is owed."
            ],
            "evidence_to_distinguish": "Ask the learner to say ALOUD, in their own words, what the evidence shows and why it supports the claim. Fluent answer -> reader-awareness or belief issue; halting/incorrect -> understanding issue; scattered -> organization issue.",
            "response_per_interpretation": {
                "cannot_reason": "Build the reasoning one step at a time ('what does this word/fact tell you? and what would that mean for your claim?').",
                "assumes_reader_knows": "Teach reader-awareness — the reader can't read your mind; write the step you just said aloud.",
                "cannot_organize": "Give a minimal ordering frame (observation -> meaning -> link to claim) and let the learner fill it.",
                "evidence_speaks_for_itself": "Make the norm explicit: in this genre the writer owes the reader the reasoning; then ask for it."
            },
            "common_incorrect_response": "Blanket 'explain more' or handing over a model explanation — which teaches nothing when the learner already understood but assumed the reader knew, and overwhelms the learner who cannot yet reason.",
            "why_it_matters": "The four cases need opposite moves (build understanding vs. surface known reasoning vs. structure vs. reset the norm); a single generic prompt helps at most one."
        },
        {
            "observable_performance": "The 'explanation' RESTATES or summarizes the evidence.",
            "possible_interpretations": [
                "Summary is mistaken for interpretation.",
                "Causal/inferential reasoning is genuinely missing.",
                "Reader-awareness is weak (thinks restating = explaining).",
                "Assignment misunderstood as a task to report rather than analyze."
            ],
            "evidence_to_distinguish": "Ask 'what does that MEAN for your claim?' If the learner adds a genuine 'because', reasoning exists but wasn't offered; if they restate again, the reasoning is absent or the task is misread.",
            "response_per_interpretation": {
                "summary_as_interpretation": "Name the difference: summary says WHAT the source says; interpretation says what it MEANS for your point.",
                "reasoning_missing": "Elicit the warrant step by step; do not accept another restatement.",
                "reader_awareness": "Ask what a reader still doesn't know after the restatement.",
                "assignment_misread": "Reconnect to the task's verb (analyze/explain) and what it asks the reader to receive."
            },
            "common_incorrect_response": "Praising the restatement as 'good detail' and moving on, cementing summary-as-analysis.",
            "why_it_matters": "Restatement is the most common false positive for explanation; treating it as adequate blocks the move from reporting to reasoning."
        },
        {
            "observable_performance": "An unsupported CAUSAL claim ('X higher scores, therefore X causes learning').",
            "possible_interpretations": [
                "Missing warrant — the learner has a reason but left the linking principle unstated.",
                "Genuine misconception — the learner believes correlation/sequence IS causation.",
                "Evidence problem masquerading as reasoning — the data can't establish cause at all."
            ],
            "evidence_to_distinguish": "Voice a plausible alternative explanation ('could higher scores just mean better test-taking?'). If the learner can rule it out, the warrant was merely unstated; if they cannot see the issue, it's a misconception; if no evidence could decide it, it's an evidence problem.",
            "response_per_interpretation": {
                "missing_warrant": "Ask them to state the principle that links the two and why it holds here.",
                "misconception": "Make the correlation-vs-causation distinction explicit via the alternative explanation, then have them address it.",
                "evidence_problem": "Redirect to Evidence — seek information that could actually establish causation."
            },
            "common_incorrect_response": "Asking for 'more explanation' when the real issue is a conceptual misconception or an evidence limitation.",
            "why_it_matters": "The same sentence needs teaching about reasoning, about a concept, or about evidence — three different targets."
        },
        {
            "observable_performance": "The learner DESCRIBES (says what happens) instead of reasoning about significance.",
            "possible_interpretations": [
                "Genre confusion — believes analysis means detailed description.",
                "Has not yet inferred implications (stops at the surface).",
                "Warrant is present in the learner's head but treated as self-evident."
            ],
            "evidence_to_distinguish": "Ask 'so what — why does that matter for your claim/reader?' A ready 'so what' means the implication exists but was omitted; a blank means it hasn't been inferred.",
            "response_per_interpretation": {
                "genre_confusion": "Distinguish description (what) from analysis (why it matters), tied to the task.",
                "not_yet_inferred": "Scaffold the inference from the specific detail to its meaning.",
                "self_evident_warrant": "Ask them to write the 'so what' they assume the reader shares."
            },
            "common_incorrect_response": "Accepting vivid description as analysis because it is well written.",
            "why_it_matters": "Fluent description is a frequent false positive for analysis; the remedy differs by cause."
        }
    ],

    "productive_misconceptions": [
        {"misconception": "Explaining means saying the evidence again more clearly.", "why_productive": "The learner values clarity and the reader.", "leverage": "Redirect clarity toward MEANING: what does it show, beyond what it says?"},
        {"misconception": "Good evidence speaks for itself.", "why_productive": "The learner trusts strong evidence.", "leverage": "Show the reader still needs the writer's reasoning to accept the link."},
        {"misconception": "If two things happen together, one causes the other.", "why_productive": "The learner is reaching for causal explanation.", "leverage": "Introduce the alternative-explanation test to build genuine causal reasoning."},
        {"misconception": "More examples make a stronger explanation.", "why_productive": "The learner wants to be convincing.", "leverage": "Move from adding instances to stating the principle that ties them to the claim."}
    ],

    "indicators_of_development": {
        "early": "Reports or restates evidence; omits the interpretive step; treats connections as self-evident.",
        "partial": "Adds reasoning when prompted but leaves warrants implicit, over-claims causation, or explains some links and not others.",
        "independent": "Independently makes reasoning explicit, states warrants, and develops implications rather than asserting.",
        "flexible": "Anticipates a skeptical reader's alternative explanations and addresses them; calibrates depth of reasoning to genre and claim."
    },

    "recognition_diagnostics_detailed": {
        "attempting": "Quote the evidence, the claim, and whatever sits between them. Is there an interpretive step, a restatement, a description, or nothing?",
        "control_level": "Is the warrant stated? Could a non-sharing reader follow it? Are causal claims defended against alternatives? Map to early/partial/independent/flexible.",
        "likely_misconception": "See instructionally_significant_discriminations — resolve WHICH underlying case before choosing a move.",
        "next_move": "Run the distinguishing probe first when the surface performance is ambiguous; then teach the specific underlying case."
    },

    "developmental_invitations": [
        {"type": "say_it_aloud", "purpose": "Have the learner state in their own words what the evidence shows and why it supports the claim (the key distinguishing probe).", "use_when": "Explanation is missing or ambiguous.", "avoid_when": "Reasoning is already explicit and sound."},
        {"type": "make_the_because_explicit", "purpose": "Elicit the reasoning step that links evidence to claim.", "use_when": "No reasoning is offered and the learner can reason.", "avoid_when": "The learner cannot yet reason it (build understanding first)."},
        {"type": "name_the_warrant", "purpose": "Ask for the general principle that makes the evidence count.", "use_when": "An inferential/causal leap is unstated.", "avoid_when": "The warrant is already stated."},
        {"type": "so_what", "purpose": "Push from description to significance.", "use_when": "The learner reports what happens without why it matters.", "avoid_when": "Significance is already drawn."},
        {"type": "distinguish_summary_from_interpretation", "purpose": "Name the difference between restating and reasoning.", "use_when": "The explanation restates the evidence.", "avoid_when": "Genuine interpretation is present."},
        {"type": "consider_alternative_explanation", "purpose": "Voice a rival explanation to test a causal claim.", "use_when": "Correlation/sequence is asserted as cause.", "avoid_when": "Alternatives are already addressed."},
        {"type": "test_reader_can_follow", "purpose": "Check whether a reader who doesn't share the reasoning could follow it.", "use_when": "The learner assumes the connection is obvious.", "avoid_when": "The step is already spelled out."},
        {"type": "reflect", "purpose": "Have the learner state what makes an explanation (vs a summary) here.", "use_when": "Consolidating a gain.", "avoid_when": "The learner is still restating."}
    ],

    "followup_decisions": [
        {"after": "Distinguishing probe shows the learner CAN reason but omitted it.", "consider": "continue — teach reader-awareness (write the step you just said)."},
        {"after": "Probe shows the learner CANNOT yet reason the link.", "consider": "increase_support — build the reasoning one step at a time."},
        {"after": "Learner keeps restating after a 'what does it mean?' prompt.", "consider": "increase_support — make the summary-vs-interpretation distinction explicit."},
        {"after": "Learner rules out the alternative explanation.", "consider": "continue — the warrant just needed stating; consolidate."},
        {"after": "Learner cannot see the alternative — a real misconception.", "consider": "stay on target — teach correlation vs causation before proceeding."},
        {"after": "The data genuinely cannot establish the point.", "consider": "change_target to Evidence."},
        {"after": "Learner independently states warrants and implications.", "consider": "conclude this target — consolidate and release."}
    ],

    "revision_strategies": [
        "After each piece of evidence, add one sentence stating what it MEANS for the claim (not what it says).",
        "Make the hidden warrant explicit: state the principle that makes the evidence count.",
        "Convert description into analysis by answering 'so what for my claim?'",
        "Address the strongest alternative explanation before asserting a cause.",
        "Cut a redundant example and replace it with the reasoning that ties examples to the point.",
        "Rewrite any restatement as an interpretation a non-sharing reader could follow."
    ],

    "stopping_conditions": [
        "Learner independently supplies explicit reasoning and warrants and can distinguish it from summary.",
        "Diminishing returns — the reasoning is followable by a skeptical reader.",
        "The link is sound but the grounds are weak -> move to Evidence.",
        "The claim itself is the bottleneck -> move to Central Claim/Thesis.",
        "Learner requests independence; or teacher override designates another focus."
    ],

    "transfer": {
        "other_genres": "The 'make the reasoning explicit for a non-sharing reader' function is constant; the KIND of reasoning varies (textual inference, historical causation, empirical mechanism).",
        "other_assignments": "The habit of asking 'what does this mean and why should the reader accept the link?' applies to any analysis.",
        "other_disciplines": "Warrants differ by field (literary inference, historical causation, scientific mechanism); the learner learns to state the field-appropriate reasoning.",
        "future_writing": "Foundational for analysis, argument, research, and any writing that must persuade rather than merely inform."
    },

    "engine_usage": {
        "reader_function/writer_function": "target selection + interpretation (why reasoning matters now, from a non-sharing reader's view)",
        "functional_relationships": "target selection — is EXPLANATION the bottleneck vs Evidence (upstream grounds) or Claim",
        "common_difficulties": "diagnostics — name the surface fault",
        "instructionally_significant_discriminations": "diagnostics + decision — run the distinguishing probe, resolve the underlying case, choose the matching move; AVOID the common_incorrect_response",
        "productive_misconceptions": "instructional invitation — turn a reasoning error into a stepping stone",
        "indicators_of_development": "interpretation (degree_of_student_control) + stopping",
        "recognition_diagnostics_detailed": "diagnostics — attempting / control_level / next_move",
        "developmental_invitations": "instructional invitation — ONE type matched to the resolved case (honor use_when/avoid_when)",
        "followup_decisions": "instructional decision — branch on what the probe revealed; continue / +support / retarget / conclude",
        "revision_strategies": "instructional invitation for functional revision",
        "stopping_conditions": "stopping / session closure",
        "transfer": "session closure — consolidation + transfer note"
    },
    "enrichment_version": "sprint3-v1"
}

ex.update(ENRICH)
json.dump(kb, open(PATH, "w"), indent=1, ensure_ascii=False)

after = json.load(open(PATH))["instructional_objects"]
ex2 = next(o for o in after if o["element"] == "Explanation / Analysis")
print("object count:", before_count, "->", len(after), "(unchanged)" if before_count == len(after) else "CHANGED!")
print("elements identical:", before_elements == [o["element"] for o in after])
print("original fields preserved:", all(k in ex2 for k in snapshot))
print("new fields added:", [k for k in ENRICH if k not in snapshot])
print("discriminations count:", len(ex2["instructionally_significant_discriminations"]))
