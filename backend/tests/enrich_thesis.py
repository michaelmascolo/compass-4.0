"""Sprint 3 — enrich the Thesis / Controlling Idea instructional object IN PLACE.
Preserves all existing fields; adds the required enrichment sections. Reuses the
existing instructional_objects.json (no new KB, no duplication)."""
import json, copy, pathlib

PATH = pathlib.Path("/app/backend/instructional_objects.json")
kb = json.load(open(PATH))
objs = kb["instructional_objects"]

before_count = len(objs)
before_elements = [o["element"] for o in objs]

thesis = next(o for o in objs if o["element"] == "Thesis")
snapshot = copy.deepcopy(thesis)

ENRICH = {
    # IDENTITY (element/communicative_purpose/related_elements already present)
    "reader_function": "Tells the reader the single idea the whole text will establish, so they know what to expect, why it matters, and how to weigh everything that follows.",
    "writer_function": "Gives the writer a decision rule for what belongs and what does not, and commits the writer to one arguable position the rest of the draft must earn.",

    # FUNCTIONAL RELATIONSHIPS
    "functional_relationships": {
        "purpose": "Operationalizes the communicative purpose as one arguable idea; if the purpose shifts, the thesis must be re-examined.",
        "reader": "Sets the reader's expectations and the standard of proof; a vague thesis leaves the reader unable to judge what is relevant.",
        "neighboring_components": "The introduction frames and lands it; supporting claims and topic sentences each advance one part of it; evidence and explanation earn it; the conclusion returns to it changed.",
        "overall_organization": "Acts as the organizing spine: every section should trace to some part of the thesis; parts that cannot trace to it signal either drift or a thesis that must widen or narrow."
    },

    # COMMON DIFFICULTIES (richer than common_obstacles; kept alongside it)
    "common_difficulties": [
        {"type": "missing", "description": "A topic or title stands in for a claim; the reader cannot tell what is being argued."},
        {"type": "topic_not_claim", "description": "Names a subject without asserting anything contestable about it."},
        {"type": "too_broad", "description": "Claims more than the draft can support; scope is unbounded."},
        {"type": "too_narrow", "description": "States a fact or a single step so small the essay has nothing to develop."},
        {"type": "unsupportable", "description": "Asserts a matter of pure taste or an untestable feeling rather than a supportable position."},
        {"type": "obvious", "description": "States something no reasonable reader would dispute, so there is nothing to earn."},
        {"type": "announcement", "description": "'In this essay I will...' describes the plan instead of asserting the idea."},
        {"type": "disconnected", "description": "Does not answer the assignment, or the body never develops it."},
        {"type": "buried_or_multiple", "description": "Several competing ideas, or the real claim hidden late, so no single controlling idea governs."}
    ],

    # PRODUCTIVE MISCONCEPTIONS (stepping stones, not just errors)
    "productive_misconceptions": [
        {"misconception": "A thesis is just the last sentence of the intro.", "why_productive": "The learner knows a thesis has a prominent, fixed home.", "leverage": "Move from 'where it lives' to 'what work it does' — ask what the reader should now expect."},
        {"misconception": "A strong thesis states an obvious truth clearly.", "why_productive": "The learner values clarity and confidence.", "leverage": "Redirect that energy toward contestability: 'what could a thoughtful person argue instead?'"},
        {"misconception": "A thesis must be one sentence, stated first.", "why_productive": "Shows awareness of focus and placement conventions.", "leverage": "Loosen to function: it may be built or refined, as long as one controlling idea governs the draft."},
        {"misconception": "More claims make a stronger thesis.", "why_productive": "The learner is trying to be substantive.", "leverage": "Channel toward one governing idea with parts, rather than several competing ideas."}
    ],

    # INDICATORS OF DEVELOPMENT (early/partial/independent/flexible)
    "indicators_of_development": {
        "early": "Produces a topic or an obvious statement; treats the thesis as a label; needs prompting to see it is not yet contestable.",
        "partial": "States a contestable position but scope is off (too broad/narrow) or it drifts from the body; revises when the mismatch is pointed out.",
        "independent": "Independently writes a focused, contestable, supportable controlling idea that answers the task and governs the draft.",
        "flexible": "Adjusts the thesis as the draft's reasoning develops, tunes scope to available support, and adapts its form across genres and purposes."
    },

    # RECOGNITION DIAGNOSTICS (detailed; kept alongside recognition_diagnostics)
    "recognition_diagnostics_detailed": {
        "attempting": "Is the learner naming a subject, describing a plan, or asserting a position? Quote the candidate thesis.",
        "control_level": "Contestable? Appropriately scoped for this draft? Answers the task? Governs the body? Map to early/partial/independent/flexible.",
        "likely_misconception": "Only a topic -> topic_not_claim; undisputable -> obvious; 'I will...' -> announcement; body ignores it -> disconnected.",
        "next_move": "Choose the single move that closes the most important gap now (usually: make it contestable, OR right-size scope, OR reconnect it to the body)."
    },

    # DEVELOPMENTAL INVITATIONS (types, not fixed prompts)
    "developmental_invitations": [
        {"type": "clarify", "purpose": "Surface the one idea the learner most wants the reader to accept.", "use_when": "The thesis is a topic or is vague.", "avoid_when": "The claim is already sharp — would stall momentum."},
        {"type": "compare", "purpose": "Hold two candidate claims side by side to reveal which is contestable and supportable.", "use_when": "The learner is stuck between ideas or keeps stating the obvious.", "avoid_when": "There is no draft claim yet to compare."},
        {"type": "predict_reader_understanding", "purpose": "Test what a reader would expect the essay to prove.", "use_when": "Scope or relevance is unclear.", "avoid_when": "The thesis is not yet an assertion."},
        {"type": "reorganize", "purpose": "Align the body to the thesis, or the thesis to what the body actually argues.", "use_when": "Thesis and body diverge.", "avoid_when": "There is no body yet."},
        {"type": "justify", "purpose": "Ask why the claim is worth asserting and who might disagree.", "use_when": "The claim is obvious or unsupportable.", "avoid_when": "The learner already anticipates opposition."},
        {"type": "evaluate", "purpose": "Judge whether the current thesis is the best available given the evidence.", "use_when": "Later in development, comparing revisions.", "avoid_when": "At first formulation."},
        {"type": "connect", "purpose": "Tie the thesis to purpose, assignment, and reader.", "use_when": "The thesis is disconnected from the task.", "avoid_when": "It is already well anchored."},
        {"type": "simplify", "purpose": "Reduce several competing ideas to one governing idea.", "use_when": "There are too many claims.", "avoid_when": "It is already single-focused."},
        {"type": "expand", "purpose": "Widen a too-narrow or factual thesis into a developable position.", "use_when": "The thesis is a fact or a single step.", "avoid_when": "It is already appropriately scoped."},
        {"type": "test", "purpose": "Check supportability against the evidence the learner can actually marshal.", "use_when": "The thesis may overreach.", "avoid_when": "Support is already mapped."},
        {"type": "reflect", "purpose": "Have the learner say in their own words what the thesis commits them to prove.", "use_when": "Consolidating a gain.", "avoid_when": "The learner is still confused about the concept."}
    ],

    # FOLLOW-UP DECISIONS (after learner performance)
    "followup_decisions": [
        {"after": "Learner turns a topic into a contestable claim.", "consider": "continue — now right-size scope or reconnect it to the body."},
        {"after": "Claim is contestable but too broad or too narrow.", "consider": "change_invitation to expand/simplify; keep the same target."},
        {"after": "Learner restates the obvious again.", "consider": "increase_support — offer a compare invitation with two candidate claims."},
        {"after": "Thesis is sound but the body ignores it.", "consider": "change_target to Organization/Topic Sentence — the thesis is no longer the bottleneck."},
        {"after": "Learner independently produces and defends a focused claim.", "consider": "conclude this target — consolidate and release."},
        {"after": "Learner asks to proceed on their own.", "consider": "stop — hand back control (independence request)."}
    ],

    # REVISION STRATEGIES (functional improvement, not editing)
    "revision_strategies": [
        "Rewrite the topic as an assertion a thoughtful reader could dispute.",
        "Right-size scope to what the draft can actually support — narrow an unbounded claim, widen a bare fact.",
        "Make the governing idea one, folding competing claims into parts of it or cutting them.",
        "Re-derive the thesis from what the body actually proves, then realign the body to it.",
        "Add the 'so what' — why the claim matters to the reader — without turning it into an announcement.",
        "Qualify an over-absolute claim so it becomes supportable."
    ],

    # STOPPING CONDITIONS
    "stopping_conditions": [
        "Learner independently produces a focused, contestable, supportable thesis that answers the task and governs the draft.",
        "Diminishing returns — the thesis substantially works and further tuning yields little developmental gain.",
        "Another component (evidence, organization) has become the primary obstacle to communicating the idea.",
        "Learner requests independence.",
        "Teacher override designates a different focus."
    ],

    # TRANSFER
    "transfer": {
        "other_genres": "The controlling-idea function persists across genres though its form varies (argumentative claim, explanatory main idea, analytical interpretation, narrative dominant impression).",
        "other_assignments": "The habit of asking 'what one idea must the reader accept, and is it contestable and supportable?' applies to any prompt.",
        "other_disciplines": "Lab reports, historical arguments, and literary analyses each need a governing claim tuned to their standards of evidence.",
        "future_writing": "Foundational for reports, proposals, and professional writing where a reader must grasp the central point quickly."
    },

    # ENGINE USAGE — which Milestone-engine decision consumes each section (mapping only; engine unchanged)
    "engine_usage": {
        "reader_function/writer_function": "target selection + interpretation (why the thesis matters now)",
        "performance_structure": "interpretation (gap between the attempt and the canonical function)",
        "functional_relationships": "target selection (is the thesis the bottleneck vs a neighbor) + sequencing",
        "common_difficulties/recognition_diagnostics_detailed": "diagnostics (name what the learner is attempting + the likely misconception)",
        "productive_misconceptions": "instructional invitation (turn an error into a stepping stone, not a correction)",
        "indicators_of_development": "interpretation (degree_of_student_control) + stopping",
        "developmental_invitations": "instructional invitation (choose the invitation type; honor use_when/avoid_when; still ONE per turn)",
        "followup_decisions": "instructional decision (continue / redirect / increase or decrease support / change target / conclude)",
        "revision_strategies": "instructional invitation for revision (functional, not editing)",
        "stopping_conditions": "stopping / session closure",
        "transfer": "session closure (consolidation + a transfer note)"
    },
    "enrichment_version": "sprint3-v1"
}

# Improve existing fields ONLY where clearly incomplete: broaden next_developmental_moves to reference
# the invitation library rather than a single fixed prompt (kept backward-compatible in spirit).
thesis.update(ENRICH)

json.dump(kb, open(PATH, "w"), indent=1, ensure_ascii=False)

after = json.load(open(PATH))
after_objs = after["instructional_objects"]
th2 = next(o for o in after_objs if o["element"] == "Thesis")
print("object count:", before_count, "->", len(after_objs), "(unchanged)" if before_count == len(after_objs) else "CHANGED!")
print("elements identical:", before_elements == [o["element"] for o in after_objs])
print("original fields preserved:", all(k in th2 for k in snapshot))
print("new fields added:", [k for k in ENRICH if k not in snapshot])
