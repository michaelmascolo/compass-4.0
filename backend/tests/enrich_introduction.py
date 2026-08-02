"""Sprint 3 — enrich the Introduction instructional object IN PLACE (additive).
Adds instructional_leverage (expert prioritization) + cross_object_dependencies."""
import json, copy, pathlib

PATH = pathlib.Path("/app/backend/instructional_objects.json")
kb = json.load(open(PATH))
objs = kb["instructional_objects"]
before_count = len(objs)
before_elements = [o["element"] for o in objs]

intro = next(o for o in objs if o["element"] == "Introduction")
snapshot = copy.deepcopy(intro)

ENRICH = {
    "reader_function": "Orients the reader to the subject, the stakes, and — above all — the DIRECTION of the essay, so they know what to expect and why it is worth reading.",
    "writer_function": "Commits the writer to a destination and a reader; an introduction cannot be built well until the writer knows what the essay will establish and for whom.",

    "functional_relationships": {
        "purpose": "The introduction exists to deliver the reader to the thesis with the context and motivation needed to accept it; with no thesis/purpose, there is no destination to introduce.",
        "reader": "Calibrated to what THIS reader needs before the claim — too little context loses them, too much buries the point.",
        "neighboring_components": "Depends on Thesis/Purpose (the destination), Audience Awareness (how much context), and draws on Hook/Opening Move and Background/Context; it is frequently a symptom whose cause lives in those objects.",
        "overall_organization": "Sets the trajectory the body will follow; a reader who finishes the intro unsure of the path signals a direction problem, not a wording problem."
    },

    "common_difficulties": [
        {"type": "hook_no_direction", "description": "An engaging opening that never tells the reader where the essay is going."},
        {"type": "hook_disconnected", "description": "A hook unrelated to the thesis — attention captured, then wasted."},
        {"type": "background_no_direction", "description": "Accurate context with no motivation or destination — an info-dump."},
        {"type": "purpose_no_orientation", "description": "States the claim but gives the reader no context or stakes to receive it."},
        {"type": "announcement", "description": "'In this essay I will...' describes the plan instead of introducing the idea."},
        {"type": "late_introduction", "description": "The real opening/claim arrives only after paragraphs of warm-up."},
        {"type": "overbroad_opening", "description": "'Since the dawn of time...' generic universals that orient no one."}
    ],

    # Expert diagnostic discrimination (standard section).
    "instructionally_significant_discriminations": [
        {
            "observable_performance": "A vivid opening that doesn't connect to the argument.",
            "possible_interpretations": ["No thesis/destination yet to connect to", "Has a thesis but doesn't see the hook must serve it", "Thinks a hook's job is only to be interesting"],
            "evidence_to_distinguish": "Check whether a clear thesis exists elsewhere in the draft, then ask what job the opening should do for THIS argument.",
            "response_per_interpretation": {"no_thesis": "Retarget upstream — establish the claim/purpose first.", "has_thesis": "Connect the hook to the thesis (the opening should earn the claim).", "hook_as_decoration": "Reframe the hook's purpose: orient the reader to this argument, not merely entertain."},
            "common_incorrect_response": "Coaching hook craft when there is no thesis for the hook to serve.",
            "why_it_matters": "Teaching a better opening is wasted if the essay has no destination; the leverage is the destination."
        },
        {
            "observable_performance": "Background information with no direction.",
            "possible_interpretations": ["Missing thesis/purpose (no direction to give)", "Weak audience awareness (dumping all known context)", "Organizational problem (direction exists but is misplaced)"],
            "evidence_to_distinguish": "Ask what the reader most needs to know to reach the claim, and whether a claim exists yet.",
            "response_per_interpretation": {"missing_thesis": "Retarget to Thesis/Purpose.", "audience": "Select only reader-necessary context; cut the rest.", "organization": "Move the existing direction forward so background becomes purposeful."},
            "common_incorrect_response": "Telling the learner to 'trim the background' without first establishing the direction that makes trimming meaningful.",
            "why_it_matters": "Background is aimless until there is a destination; sequencing the fix matters."
        },
        {
            "observable_performance": "'In this essay I will...' announcement.",
            "possible_interpretations": ["No claim yet (announces because nothing to assert)", "Has a claim but front-loads a roadmap out of habit", "Genre confusion (thinks intros state plans)"],
            "evidence_to_distinguish": "Ask the learner to state the IDEA (not the plan) in one sentence; a ready idea means it's habit/genre, a blank means the claim is missing.",
            "response_per_interpretation": {"no_claim": "Retarget to Thesis/Purpose.", "roadmap_habit": "Convert the plan-statement into an idea plus orientation.", "genre_confusion": "Distinguish introducing an idea from announcing a plan."},
            "common_incorrect_response": "Rewriting the announcement into a polished plan-statement, cementing the habit.",
            "why_it_matters": "Announcements usually signal a missing claim; fixing surface wording hides the real gap."
        }
    ],

    # NEW CANONICAL SECTION — expert prioritization: which move has the greatest developmental leverage.
    "instructional_leverage": [
        {
            "observable_learner_state": "Engaging or disconnected hook, but the reader cannot tell where the essay is going.",
            "possible_responses": ["Polish the hook", "Connect the hook to the thesis/purpose", "Establish the thesis first", "Add reader orientation/stakes"],
            "recommended_first_response": "Secure the destination: make sure a clear purpose/thesis exists, then make the opening serve it.",
            "why_highest_leverage": "The introduction's core job is to orient the reader toward a destination; a clever opening that leads nowhere cannot be improved by more polish. Direction unlocks every other opening decision.",
            "when_another_takes_priority": "If NO thesis exists yet -> fix the thesis first (dependency). If a strong thesis already exists and only the hook is off -> connecting/replacing the hook is the move."
        },
        {
            "observable_learner_state": "Accurate background with no motivation or direction (info-dump).",
            "possible_responses": ["Trim the background", "Add a motivating problem/stakes", "Surface the direction early", "Add the thesis"],
            "recommended_first_response": "Surface the direction and the stakes (why it matters), so the background becomes selectable against a destination.",
            "why_highest_leverage": "Background gains meaning only from direction; establishing 'where and why' lets the learner see which context is relevant and cut the rest — a durable, transferable move.",
            "when_another_takes_priority": "If the claim/purpose is missing -> thesis first. If the context is simply irrelevant -> cut before reorganizing."
        },
        {
            "observable_learner_state": "Reader is confused about the paper's trajectory even though content is present.",
            "possible_responses": ["Add a forecasting sentence", "Reorder the opening", "Sharpen the thesis", "Polish wording"],
            "recommended_first_response": "Make the destination visible early — ensure the thesis's direction is clear, then order the opening to lead there.",
            "why_highest_leverage": "Reader orientation IS the introduction's function; clarity of trajectory matters more than elegance and is what a reader actually needs.",
            "when_another_takes_priority": "If the confusion stems from an unfocused thesis -> thesis precision first (a forecasting sentence cannot forecast an unclear claim)."
        },
        {
            "observable_learner_state": "Opening is competent but flat; the learner wants it to be 'better'.",
            "possible_responses": ["Teach a fancier hook", "Deepen the stakes/relevance", "Leave it and move to the body"],
            "recommended_first_response": "Check leverage before investing: if the opening already orients the reader and leads to the thesis, move to higher-leverage work (evidence, reasoning, organization).",
            "why_highest_leverage": "Polishing an already-functional introduction is low developmental return; the learner grows more by working where the reader is actually being lost.",
            "when_another_takes_priority": "If the assignment/genre foregrounds engagement (e.g., a personal or persuasive piece) and the flat opening genuinely disengages the reader -> then invest in stakes/hook."
        }
    ],

    # Leverage != correctness: sometimes clarity/reader-awareness/purpose/confidence must come first.
    "leverage_over_correctness_note": "A technically better introduction is not always the best next move. If the learner lacks a clear purpose, a sense of the reader, organization, or confidence, address that first — a polished opening built on an unclear destination does not help the writer develop.",

    # CROSS-OBJECT DEPENDENCIES — most introduction problems are symptoms; check the cause before teaching intro craft.
    "cross_object_dependencies": [
        {"intro_symptom": "hook_disconnected / hook_no_direction", "likely_cause": "Thesis / Purpose", "action": "If no clear destination exists, retarget to Thesis/Purpose before shaping the opening."},
        {"intro_symptom": "background_no_direction", "likely_cause": "Purpose/Thesis or Organization", "action": "Establish direction (or reorder) before trimming context."},
        {"intro_symptom": "announcement", "likely_cause": "Thesis / Purpose", "action": "Elicit the idea; if none, retarget to Thesis."},
        {"intro_symptom": "reader_confusion_about_trajectory", "likely_cause": "Thesis precision or Organization", "action": "Sharpen the claim's direction first."},
        {"intro_symptom": "cannot judge which context is relevant", "likely_cause": "Audience Awareness or Missing Knowledge", "action": "Address audience awareness; if the learner lacks the content itself, the Knowledge Loop (Orientation) precedes intro work."}
    ],

    "productive_misconceptions": [
        {"misconception": "An introduction's job is to grab attention.", "why_productive": "The learner cares about the reader's engagement.", "leverage": "Extend 'grab attention' to 'orient the reader toward the point' — attention in service of direction."},
        {"misconception": "Start broad ('Since the beginning of time') then narrow.", "why_productive": "The learner senses an intro should set a stage.", "leverage": "Replace the empty universal with the specific problem THIS reader needs to care about."},
        {"misconception": "Tell the reader your plan so they know what's coming.", "why_productive": "The learner values orientation.", "leverage": "Convert the plan-statement into the idea itself plus a real sense of direction."}
    ],

    "indicators_of_development": {
        "early": "Opens with a generic or disconnected move; states a plan rather than an idea; gives the reader no clear direction.",
        "partial": "Provides some orientation but misjudges context (too much/little) or lets the hook drift from the thesis; fixes it when pointed out.",
        "independent": "Independently orients the reader, selects relevant context, and leads coherently to the thesis.",
        "flexible": "Adapts the opening to genre, audience, and purpose; calibrates engagement and context to what the specific reader needs."
    },

    "recognition_diagnostics_detailed": {
        "attempting": "Identify what the opening is doing — hooking, giving background, announcing, or orienting — and whether a destination (thesis) is visible.",
        "control_level": "Does the reader end the intro knowing the subject, the stakes, and the direction? Is context reader-necessary? Map to early/partial/independent/flexible.",
        "likely_misconception": "See instructionally_significant_discriminations; then check cross_object_dependencies before teaching intro craft.",
        "next_move": "Run the destination check first; if the destination is missing/unclear, retarget upstream; otherwise choose the leverage-ranked intro move."
    },

    "developmental_invitations": [
        {"type": "orient_the_reader", "purpose": "Make the essay's direction clear early.", "use_when": "The reader can't tell where the paper is going.", "avoid_when": "Direction is already clear."},
        {"type": "name_the_stakes", "purpose": "Establish why the subject matters to this reader.", "use_when": "Background is aimless or the opening is flat.", "avoid_when": "Stakes are already established."},
        {"type": "connect_hook_to_purpose", "purpose": "Tie an engaging opening to the thesis.", "use_when": "A hook exists but is disconnected.", "avoid_when": "There is no thesis to connect to yet (retarget)."},
        {"type": "select_relevant_context", "purpose": "Keep only the context the reader needs to reach the claim.", "use_when": "Background is excessive or generic.", "avoid_when": "Context is already lean and relevant."},
        {"type": "forecast_direction", "purpose": "Signal the trajectory without listing a plan.", "use_when": "Reader is unsure of the path but the thesis is clear.", "avoid_when": "The thesis itself is unclear (sharpen it first)."},
        {"type": "convert_announcement_to_idea", "purpose": "Turn 'I will discuss...' into the idea itself.", "use_when": "The opening announces a plan.", "avoid_when": "No claim exists yet (retarget to Thesis)."},
        {"type": "test_reader_trajectory", "purpose": "Have the learner predict what a reader expects after the intro.", "use_when": "Trajectory is in doubt.", "avoid_when": "Trajectory is already clear."},
        {"type": "reflect", "purpose": "Have the learner state what their introduction promises the reader.", "use_when": "Consolidating a gain.", "avoid_when": "The intro is not yet oriented."}
    ],

    "followup_decisions": [
        {"after": "Destination check shows NO clear thesis.", "consider": "change_target to Thesis/Purpose before any intro work."},
        {"after": "Thesis is clear; hook is disconnected.", "consider": "continue — connect_hook_to_purpose."},
        {"after": "Learner adds direction and stakes to background.", "consider": "continue — select_relevant_context, then move on."},
        {"after": "Intro now orients the reader and leads to the thesis.", "consider": "conclude this target; move to higher-leverage body work."},
        {"after": "Confusion traces to an unfocused thesis.", "consider": "change_target to Thesis precision."},
        {"after": "Learner cannot supply needed context (lacks the knowledge).", "consider": "route to the Knowledge Loop (Orientation) before continuing."}
    ],

    "revision_strategies": [
        "Add or surface the direction early so the reader knows the destination.",
        "Replace a generic/universal opening with the specific problem the reader should care about.",
        "Connect or replace a disconnected hook so it earns the thesis.",
        "Cut context the reader does not need to reach the claim; keep what they do.",
        "Convert an 'I will discuss...' announcement into the idea itself plus orientation.",
        "Move a buried opening/claim to the front so the essay's path is visible."
    ],

    "stopping_conditions": [
        "Learner independently orients the reader, selects relevant context, and leads to the thesis.",
        "Diminishing returns — the introduction does its job for the intended reader.",
        "The real bottleneck is upstream (thesis/purpose) or content (knowledge) -> retarget.",
        "Learner requests independence; or teacher override designates another focus."
    ],

    "genre_variation": {
        "argument_persuasive": "Foreground the stakes and the contested question; a motivating problem earns the claim.",
        "explanatory": "Foreground the subject and why it is worth understanding; orient before explaining.",
        "literary_analysis": "Foreground the interpretive question about the text; minimal plot summary, quick move to the claim.",
        "historical": "Foreground the situation and its significance; supply only orienting context, not a full chronicle.",
        "scientific": "Foreground the question/problem and its relevance; context is background to the investigation.",
        "personal_reflective": "Engagement and voice carry more weight; a scene or tension may legitimately open the piece."
    },

    "transfer": {
        "other_genres": "The orient-the-reader-toward-a-destination function is constant; the balance of hook, context, and stakes varies by genre.",
        "other_assignments": "The habit of asking 'what does my reader need before my main point, and do they know where I'm going?' applies to any piece.",
        "other_disciplines": "Orienting context differs by field, but every discipline expects a reader to know the question and its significance up front.",
        "future_writing": "Foundational for reports, proposals, emails, and any communication where a reader decides quickly whether to keep reading."
    },

    "engine_usage": {
        "reader_function/writer_function": "target selection + interpretation (the intro's job = orientation toward a destination)",
        "functional_relationships/cross_object_dependencies": "target selection — decide whether Introduction is the real target or a symptom of Thesis/Purpose/Audience/Organization/Knowledge; retarget if so",
        "common_difficulties": "diagnostics — name the surface fault",
        "instructionally_significant_discriminations": "diagnostics + decision — resolve which underlying case; avoid the common_incorrect_response",
        "instructional_leverage": "instructional decision — when several moves are possible, pick the highest-leverage FIRST response (and know when another takes priority)",
        "leverage_over_correctness_note": "instructional decision — prefer clarity/purpose/reader-awareness/confidence over a technically better opening when needed",
        "productive_misconceptions": "instructional invitation — turn an intro misconception into a stepping stone",
        "indicators_of_development": "interpretation (degree_of_student_control) + stopping",
        "developmental_invitations": "instructional invitation — ONE type, leverage-ranked (honor use_when/avoid_when)",
        "followup_decisions": "instructional decision — continue / retarget / conclude / route to Knowledge Loop",
        "revision_strategies": "instructional invitation for functional revision",
        "genre_variation": "diagnostics + interpretation — calibrate hook/context/stakes to genre",
        "stopping_conditions": "stopping / session closure",
        "transfer": "session closure — consolidation + transfer note"
    },
    "enrichment_version": "sprint3-v1"
}

intro.update(ENRICH)
json.dump(kb, open(PATH, "w"), indent=1, ensure_ascii=False)

after = json.load(open(PATH))["instructional_objects"]
i2 = next(o for o in after if o["element"] == "Introduction")
print("object count:", before_count, "->", len(after), "(unchanged)" if before_count == len(after) else "CHANGED!")
print("elements identical:", before_elements == [o["element"] for o in after])
print("original fields preserved:", all(k in i2 for k in snapshot))
print("new fields added:", [k for k in ENRICH if k not in snapshot])
print("leverage situations:", len(i2["instructional_leverage"]), "| dependencies:", len(i2["cross_object_dependencies"]))
