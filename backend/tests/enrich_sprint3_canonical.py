"""
Sprint 3 canonical enrichment — 18 instructional objects.

Source of truth: Writing Elements Chart (uploaded, canonical).
- The 5 canonical fields (definition, performance_structure, recognition_diagnostics,
  next_developmental_moves, indicators_of_control) are set VERBATIM from the chart.
- Deeper Compass fields follow the established pilot pattern (Thesis/Evidence/
  Explanation/Introduction) and are derived CONSERVATIVELY from the chart. Nothing
  is added that cannot reasonably be inferred from the chart + existing enriched objects.
- The 4 pilot objects are NOT touched. related_elements (network) is NOT changed.
- provenance[] records, per field, whether content is 'canonical_verbatim',
  'canonical_derived' (low interpretation, restatement of chart), or
  'pattern_interpreted' (conservative inference from chart + pilot pattern) so the
  validation report can flag interpretation.
"""
import json, os, copy

HERE = os.path.dirname(__file__)
KB_PATH = os.path.join(HERE, "..", "instructional_objects.json")

PILOTS = {"Thesis", "Evidence", "Explanation / Analysis", "Introduction"}
ENRICH_VERSION = "sprint3-canonical-v1"

# Shared engine_usage mapping (field -> engine stage). Object-independent boilerplate,
# identical in meaning across pilots; reused verbatim (pattern, not new content).
ENGINE_USAGE = {
    "reader_function/writer_function": "target selection + interpretation (why this element matters now)",
    "performance_structure": "interpretation (gap between the attempt and the canonical function)",
    "functional_relationships": "target selection (is this the bottleneck vs a neighbor) + sequencing",
    "common_difficulties/recognition_diagnostics_detailed": "diagnostics (name what the learner is attempting + the likely misconception)",
    "productive_misconceptions": "instructional invitation (turn an error into a stepping stone, not a correction)",
    "indicators_of_development": "interpretation (degree_of_student_control) + stopping",
    "developmental_invitations": "instructional invitation (choose the invitation type; honor use_when/avoid_when; still ONE per turn)",
    "followup_decisions": "instructional decision (continue / redirect / increase or decrease support / change target / conclude)",
    "revision_strategies": "instructional invitation for revision (functional, not editing)",
    "stopping_conditions": "stopping / session closure",
    "transfer": "session closure (consolidation + a transfer note)",
}

# Shared followup-decision spine (pattern-interpreted; specialized first line per object below).
def followups(component, neighbor):
    return [
        {"after": f"Learner improves the {component} in the targeted way.",
         "consider": "continue — consolidate the gain, then check the next-most-limiting aspect."},
        {"after": "Learner repeats the same difficulty after one invitation.",
         "consider": "increase_support — vary the scaffold (change the lens); do NOT supply the content."},
        {"after": f"The {component} now works but a neighbor is the real obstacle.",
         "consider": f"change_target to {neighbor} — this element is no longer the bottleneck."},
        {"after": "Learner independently performs and can explain the change.",
         "consider": "conclude this target — consolidate and release."},
        {"after": "Learner asks to proceed on their own.",
         "consider": "stop — hand back control (independence request)."},
    ]

def stopping(component):
    return [
        f"Learner independently produces a {component} that performs its canonical function for this reader and purpose.",
        "Diminishing returns — the element substantially works and further tuning yields little developmental gain.",
        "Another component has become the primary obstacle to communicating the meaning.",
        "Learner requests independence.",
        "Teacher override designates a different focus.",
    ]

# ---------------------------------------------------------------------------
# CANONICAL (verbatim from the Writing Elements Chart) for the 18 target objects.
# key order: definition, performance_structure, recognition_diagnostics,
#            next_developmental_moves, indicators_of_control
# ---------------------------------------------------------------------------
CANON = {
 "Topic Sentence": [
  "A sentence that identifies the central contribution a paragraph makes to the surrounding discussion.",
  "Establish the paragraph\u2019s focus; state or imply its principal claim or function; connect it to the thesis or preceding discussion; prepare the reader for the paragraph\u2019s development.",
  "Does the sentence merely announce a topic? Does it accurately represent the paragraph? Is the paragraph\u2019s contribution clear without it?",
  "Ask, \u201cWhat single idea does this paragraph help the reader understand?\u201d Help the student state that idea in relation to the larger argument.",
  "Topic sentences increasingly express meaningful claims, orient the reader, and accurately govern paragraph development.",
 ],
 "Supporting Detail": [
  "Specific information that develops, clarifies, illustrates, or supports a paragraph\u2019s central idea.",
  "Determine what the paragraph\u2019s claim requires; add relevant facts, examples, descriptions, quotations, or reasoning; explain their relationship to the central idea.",
  "Is the paragraph underdeveloped? Are details relevant, sufficient, and ordered? Do they support the main idea or merely concern the same topic?",
  "Ask what the reader still needs to know or understand to accept the paragraph\u2019s main point.",
  "The student selects and organizes details according to their function rather than accumulating loosely related information.",
 ],
 "Concluding Sentence": [
  "A sentence that completes a paragraph\u2019s work and helps the reader understand its significance or connection to what follows.",
  "Synthesize the paragraph\u2019s contribution; state its implication; connect it to the larger claim or next idea; avoid merely repeating the topic sentence.",
  "Does the paragraph end abruptly? Does the final sentence add significance or simply restate earlier wording? Is closure actually needed?",
  "Ask, \u201cWhat should the reader now understand because of this paragraph?\u201d Invite the student to express that implication.",
  "The student closes paragraphs selectively and purposefully, emphasizing implications or movement in the argument.",
 ],
 "Paragraph": [
  "A group of related sentences that develops one coherent contribution to a larger piece of writing.",
  "Establish a central purpose or claim; orient the reader; develop the idea through explanation, evidence, and examples; organize sentences logically; connect the paragraph to the larger text.",
  "Does the paragraph have one governing purpose? Are sentences relevant and coherently ordered? Is it adequately developed? Should it be divided or combined?",
  "Ask the student to state the paragraph\u2019s job in the essay and examine how each sentence contributes to that job.",
  "The student constructs unified, developed paragraphs of flexible length and organizes them according to meaning rather than formula.",
 ],
 "Hook / Opening Move": [
  "An opening that gives the reader a meaningful reason to attend to the subject.",
  "Identify what is interesting, puzzling, consequential, vivid, or contested about the subject; present it accurately; connect it directly to the essay\u2019s purpose.",
  "Does the opening create relevant interest or merely use a decorative question, quotation, or dramatic statement? Is its connection to the essay clear?",
  "Ask what is genuinely surprising, important, or unresolved about the topic and help the student begin there.",
  "The student creates varied, relevant openings and abandons formulaic hooks that do not serve the essay.",
 ],
 "Background / Context": [
  "Information readers need in order to understand the subject, problem, concepts, or argument that follows.",
  "Identify what the intended reader likely knows; supply necessary history, circumstances, definitions, or debate; select only information that prepares the reader for the central discussion.",
  "What knowledge is being assumed? Is essential information missing? Is the writer providing an unfocused history or facts that do not support understanding?",
  "Ask what the reader must understand before the main claim will make sense, then identify the minimum sufficient context.",
  "The student anticipates audience knowledge and provides focused context without overwhelming or distracting the reader.",
 ],
 "Conclusion": [
  "The closing section that completes the essay\u2019s work by clarifying what has been established and why it matters.",
  "Return to the central problem or claim; synthesize rather than merely repeat; draw implications; acknowledge remaining questions or limits when appropriate; provide meaningful closure.",
  "Does the conclusion merely restate the thesis and main points? Does it introduce unsupported new claims? Does it explain the significance of the essay\u2019s reasoning?",
  "Ask, \u201cWhat can the reader now understand that was not clear at the beginning, and why does that matter?\u201d",
  "The student produces conclusions that synthesize reasoning, articulate implications, and provide closure suited to the essay\u2019s purpose.",
 ],
 "Title": [
  "A brief name for a piece of writing that identifies or frames its subject and invites appropriate expectations.",
  "Identify the central subject and angle; select precise and engaging language; signal genre, argument, or focus when useful; avoid titles that are vague or misleading.",
  "Does the title reflect the actual essay? Is it overly general, decorative, or simply the assignment label?",
  "Ask the student to name both the subject and what the essay says or reveals about it.",
  "Titles become more precise, purposeful, original, and aligned with the completed writing.",
 ],
 "Sentence": [
  "A linguistically complete thought; a linguistically complete unit that expresses a thought, action, relationship, question, or command.",
  "Establish a subject or focus; express an action, state, or relationship; organize clauses and modifiers so their relationships are clear; punctuate the resulting structure appropriately.",
  "Can the reader identify who or what the sentence concerns and what is being said? Is it fragmented, fused, overloaded, ambiguous, or syntactically confusing?",
  "Ask the student to identify the central actor or topic and the main action or assertion, then rebuild the sentence around that relationship.",
  "The student creates increasingly varied, controlled sentences and revises syntax according to meaning, emphasis, and reader comprehension.",
 ],
 "Word Choice": [
  "The selection of words that express the writer\u2019s intended meaning with appropriate precision, force, and tone.",
  "Determine the exact meaning; choose words suited to audience and context; prefer concrete and specific language where useful; test connotations; remove unnecessary or misleading wording.",
  "Is the wording vague, inaccurate, repetitive, inflated, informal, or inconsistent with the intended meaning? Would a different word materially improve understanding?",
  "Ask what the student means in ordinary language, then compare the current word with the intended meaning.",
  "The student chooses increasingly precise language, notices connotation, and revises wording based on meaning rather than superficial variety.",
 ],
 "Tone": [
  "The stance or attitude toward the subject and reader conveyed through language and presentation.",
  "Identify the relationship the writer wants with the reader; choose vocabulary, syntax, level of certainty, detail, and formality consistent with that relationship; maintain or deliberately vary the stance.",
  "Does the tone suit the audience, purpose, and subject? Does it shift unintentionally? Is it dismissive, exaggerated, detached, or falsely authoritative?",
  "Ask how the writer wants the reader to experience the voice and identify one wording choice that supports or undermines that relationship.",
  "The student deliberately adjusts tone across contexts and explains how particular language choices create that tone.",
 ],
 "Audience Awareness": [
  "Attention to what intended readers know, need, value, expect, or may misunderstand.",
  "Identify likely readers; estimate their knowledge and perspectives; anticipate questions and points of confusion; select explanations, evidence, organization, and tone accordingly.",
  "Is the student writing only from personal understanding? What knowledge, assumptions, or responses are attributed to the reader without justification?",
  "Ask the student to imagine a particular reader and identify the first question or confusion that reader might have.",
  "The student anticipates reader needs throughout composing and adapts writing flexibly for different audiences.",
 ],
 "Purpose": [
  "The communicative work the writer is trying to accomplish with the reader.",
  "Identify the desired change in the reader\u2019s understanding, judgment, feeling, or action; coordinate content, form, tone, and evidence toward that end; revise when the actual writing serves a different purpose.",
  "Can the student explain what the writing is intended to accomplish? Do the essay\u2019s choices serve that purpose? Has the purpose become confused with merely completing the assignment?",
  "Ask, \u201cWhat should become different for the reader after reading this?\u201d Use the answer to evaluate the current passage.",
  "The student formulates meaningful purposes, maintains them during writing, and deliberately coordinates choices around them.",
 ],
 "Organization": [
  "The purposeful arrangement of ideas and sections so that the reader can follow the development of the writing.",
  "Identify the overall task; determine the major ideas or stages required; group related material; order groups according to logic and reader need; establish relationships among sections.",
  "Is there a discernible progression? Are ideas grouped and sequenced purposefully? Does the organization reflect the argument or merely the order in which ideas occurred?",
  "Ask the student to name the major jobs the essay must perform and arrange them in the order the reader needs.",
  "The student creates and revises organizational plans based on conceptual relationships, purpose, and reader understanding.",
 ],
 "Coherence": [
  "The quality by which ideas fit together into an understandable and continuous line of thought.",
  "Maintain a clear focus; establish logical and semantic relationships; order information purposefully; use transitions, repeated concepts, and consistent terminology; resolve unexplained shifts.",
  "Can the reader explain how each idea follows from the previous one? Are relationships missing, contradictory, or dependent on unstated assumptions?",
  "Select one confusing shift and ask the student to state the relationship between the ideas explicitly.",
  "The student anticipates where readers may lose the line of thought and creates coherence through reasoning and structure, not transition words alone.",
 ],
 "Unity": [
  "The condition in which all parts of a passage contribute to a shared central purpose or idea.",
  "Establish the governing purpose; include material that develops it; remove, relocate, or reframe material that does not; ensure each part has a discernible function.",
  "Do all sentences or sections contribute to the same central work? Is material merely related to the topic rather than relevant to the purpose?",
  "Ask the student to identify the passage\u2019s job and explain how each sentence helps perform it. Examine the first sentence that does not.",
  "The student independently detects digressions, maintains focus, and reorganizes useful material rather than retaining it merely because it is interesting.",
 ],
 "Voice": [
  "The recognizable presence or perspective of the writer expressed through choices of language, emphasis, reasoning, and stance.",
  "Develop ideas the writer genuinely understands and can stand behind; make deliberate language and tone choices; express judgments with appropriate confidence; integrate sources without surrendering authorship.",
  "Does the writing sound generic, borrowed, mechanical, or unlike the student\u2019s demonstrated understanding? Is personal voice replacing disciplined reasoning, or has formal language erased the writer\u2019s agency?",
  "Ask the student to explain the idea aloud in their own words, then revise the passage while preserving that meaning and meeting the demands of the context.",
  "The student maintains an identifiable perspective while adapting appropriately to genre, evidence, audience, and academic conventions.",
 ],
 "Revision": [
  "The purposeful reworking of writing to improve what it communicates and how effectively it does so.",
  "Reconsider purpose and task; evaluate reader understanding; examine global organization and central claims; revise paragraphs and reasoning; refine sentences and words; proofread after substantive changes.",
  "Is revision limited to correction and word substitution? Does the student recognize mismatches among purpose, meaning, structure, and reader response?",
  "Choose one high-leverage issue connected to the essay\u2019s purpose. Ask the student to make a meaningful change and compare the effect of the two versions.",
  "The student rereads from a reader\u2019s perspective, identifies consequential problems, makes substantive changes, and explains why revisions improve the writing.",
 ],
}

# ---------------------------------------------------------------------------
# Deeper enrichment (conservative; derived from chart + pilot pattern).
# For each object: reader_function, writer_function, functional_relationships,
# common_difficulties, productive_misconceptions, indicators_of_development,
# recognition_diagnostics_detailed, developmental_invitations, revision_strategies,
# transfer. followup_decisions/stopping_conditions/engine_usage are generated.
# ---------------------------------------------------------------------------
DEEP = {}

def add(el, reader, writer, fr, cd, pm, iod, rdd, di, rs, tr, neighbor):
    DEEP[el] = dict(
        reader_function=reader, writer_function=writer, functional_relationships=fr,
        common_difficulties=cd, productive_misconceptions=pm, indicators_of_development=iod,
        recognition_diagnostics_detailed=rdd, developmental_invitations=di,
        revision_strategies=rs, transfer=tr, _neighbor=neighbor,
    )

def iod(early, partial):
    # independent/flexible are taken from the chart's Indicators of Increasing Control at apply time.
    return {"early": early, "partial": partial}

# ---- Topic Sentence ----
add("Topic Sentence",
 "Tells the reader the one contribution this paragraph makes, so they know how to read what follows and how it advances the whole.",
 "Commits the writer to a single paragraph job and gives a test for what belongs in the paragraph.",
 {"purpose":"Names the paragraph's share of the whole purpose; if the paragraph's job is unclear, the topic sentence is where it must be decided.",
  "reader":"Orients the reader to the paragraph's point before its development; without it the reader must guess.",
  "neighboring_components":"Advances one part of the Thesis; governs the Supporting Detail and Concluding Sentence beneath it.",
  "overall_organization":"Each topic sentence should trace to some part of the controlling idea; sequence of topic sentences reveals the essay's organization."},
 [{"type":"topic_not_claim","description":"Announces a subject ('This paragraph is about X') without stating the paragraph's contribution."},
  {"type":"inaccurate","description":"Promises something the paragraph does not actually develop."},
  {"type":"redundant","description":"The paragraph's point is already clear, so a stated topic sentence adds nothing."},
  {"type":"disconnected","description":"States a point unrelated to the thesis or the preceding discussion."}],
 [{"misconception":"Every paragraph must start with a topic sentence.","why_productive":"Shows awareness that paragraphs need a governing point.","leverage":"Move from placement to function: the point may be stated or implied, as long as one contribution governs the paragraph."},
  {"misconception":"A topic sentence just names the paragraph's topic.","why_productive":"The learner can locate the subject.","leverage":"Push from topic to contribution: what does this paragraph help the reader understand about the thesis?"}],
 iod("Announces a topic or restates the thesis; cannot say what the paragraph contributes.",
     "States a real contribution but it drifts from the paragraph's actual development or from the thesis; revises when shown the mismatch."),
 {"attempting":"Is the learner naming a topic, restating the thesis, or asserting the paragraph's contribution? Quote the candidate sentence.",
  "control_level":"Does it express a meaningful claim/function, orient the reader, and match what the paragraph develops? Map to early/partial/independent/flexible.",
  "likely_misconception":"Only names a subject -> topic_not_claim; promises more than the paragraph delivers -> inaccurate.",
  "next_move":"Ask what single idea the paragraph helps the reader understand, then align the sentence to the paragraph's real work."},
 [{"type":"clarify","purpose":"Surface the single idea the paragraph contributes.","use_when":"The sentence only names a topic.","avoid_when":"The contribution is already clear."},
  {"type":"connect","purpose":"Tie the paragraph's point to the thesis.","use_when":"The paragraph feels unrelated to the argument.","avoid_when":"It is already well anchored."},
  {"type":"reorganize","purpose":"Align the sentence to what the paragraph actually develops.","use_when":"Sentence and body diverge.","avoid_when":"They already match."},
  {"type":"reflect","purpose":"Have the learner state the paragraph's job in their own words.","use_when":"Consolidating a gain.","avoid_when":"The learner is still unclear on the concept."}],
 ["Rewrite the topic announcement as the paragraph's contribution to the thesis.",
  "Re-derive the sentence from what the paragraph actually proves, then align the two.",
  "Cut a topic sentence that only labels the subject if the paragraph's point is already clear."],
 {"other_genres":"The 'governing point of a unit' function persists (a section's lead in a report, a stanza's turn), though form varies.",
  "other_assignments":"Asking 'what does this chunk contribute to the whole?' applies to any multi-part writing.",
  "other_disciplines":"Lab and history writing still need each section's contribution made visible.",
  "future_writing":"Foundational for structuring reports, memos, and proposals a reader can skim by leads."},
 "Thesis")

# ---- Supporting Detail ----
add("Supporting Detail",
 "Gives the reader concrete grounds to understand or accept the paragraph's point, not just more words on the topic.",
 "Forces the writer to decide what the claim actually requires and to make each detail earn its place.",
 {"purpose":"Serves the paragraph's contribution; details that do not develop the point do not serve the purpose.",
  "reader":"Supplies what the reader still needs to understand or believe the point.",
  "neighboring_components":"Develops the Topic Sentence; overlaps Evidence and Example as the material a paragraph uses.",
  "overall_organization":"Ordered by function within the paragraph, not by the order details came to mind."},
 [{"type":"underdeveloped","description":"The point is asserted with too little concrete material for the reader to accept it."},
  {"type":"irrelevant","description":"Details concern the same topic but do not develop the paragraph's actual point."},
  {"type":"unordered","description":"Relevant details appear in no functional order, so their cumulative effect is lost."},
  {"type":"unexplained","description":"Details are listed without showing their relationship to the central idea."}],
 [{"misconception":"More detail always makes a paragraph stronger.","why_productive":"The learner values development.","leverage":"Shift from quantity to function: which details does the claim actually require?"},
  {"misconception":"Anything true about the topic belongs in the paragraph.","why_productive":"The learner is gathering material.","leverage":"Introduce relevance-to-the-point as the test for inclusion."}],
 iod("Adds little, or piles on topic-related facts with no clear relationship to the point.",
     "Adds relevant details but leaves their connection implicit or orders them loosely; adjusts when the point's requirements are named."),
 {"attempting":"Is the learner developing the point or accumulating topic-related information? Quote the details.",
  "control_level":"Are details relevant, sufficient, ordered, and tied to the central idea? Map to early/partial/independent/flexible.",
  "likely_misconception":"Same-topic facts with no link -> irrelevant/unexplained; too little -> underdeveloped.",
  "next_move":"Ask what the reader still needs to accept the point, then select and connect the details that supply it."},
 [{"type":"clarify","purpose":"Name what the paragraph's point requires the reader to know.","use_when":"The paragraph is thin.","avoid_when":"Development is already sufficient."},
  {"type":"evaluate","purpose":"Judge which existing details actually develop the point.","use_when":"Details are topic-related but loose.","avoid_when":"Relevance is already tight."},
  {"type":"reorganize","purpose":"Order details by their function in the paragraph.","use_when":"Order is arbitrary.","avoid_when":"Order already builds the point."},
  {"type":"connect","purpose":"Make each detail's relationship to the central idea explicit.","use_when":"Details sit unexplained.","avoid_when":"Connections are already clear."}],
 ["List what the point requires the reader to know, then keep only details that supply it.",
  "Reorder details so they build toward the paragraph's contribution.",
  "Add one sentence connecting each detail to the central idea."],
 {"other_genres":"Selecting material by what the point requires transfers to narrative detail, technical spec, and description.",
  "other_assignments":"'What does this claim require?' governs support in any developed paragraph.",
  "other_disciplines":"Discipline sets what counts as sufficient detail; the selection habit is constant.",
  "future_writing":"Foundational for developed, non-padded professional and academic paragraphs."},
 "Evidence")

# ---- Concluding Sentence ----
add("Concluding Sentence",
 "Leaves the reader with the paragraph's significance or its link to what follows, rather than a flat stop.",
 "Makes the writer state what the paragraph established and why it matters, testing whether the paragraph did its job.",
 {"purpose":"Completes the paragraph's share of the purpose; names the 'so what' of the paragraph.",
  "reader":"Tells the reader what to carry forward from the paragraph.",
  "neighboring_components":"Answers the Topic Sentence; bridges to the next Paragraph; contributes to overall Coherence.",
  "overall_organization":"Optional by design — used where a paragraph needs closure or a hinge, not mechanically."},
 [{"type":"restates","description":"Merely repeats the topic sentence wording without adding significance."},
  {"type":"abrupt","description":"The paragraph stops without completing its point, leaving the reader unsure what it established."},
  {"type":"unnecessary","description":"Closure is forced where the paragraph's point is already complete."},
  {"type":"new_tangent","description":"Introduces a new idea instead of completing the current one."}],
 [{"misconception":"Every paragraph needs a concluding sentence.","why_productive":"Shows attention to closure.","leverage":"Move to selectivity: closure is used where it adds significance or movement, not by rule."},
  {"misconception":"A conclusion restates what was said.","why_productive":"The learner values reinforcement.","leverage":"Redirect from restatement to implication: what should the reader now understand?"}],
 iod("Ends abruptly or repeats the opening sentence; cannot say what the paragraph established.",
     "States an implication but it echoes earlier wording or adds a tangent; refines when asked for the 'so what'."),
 {"attempting":"Is the ending restating, completing, or wandering? Quote the final sentence.",
  "control_level":"Does it synthesize the contribution, state an implication, or connect forward — without mere repetition? Map to levels.",
  "likely_misconception":"Echoes the topic sentence -> restates; adds a new idea -> new_tangent.",
  "next_move":"Ask what the reader should now understand because of the paragraph, and whether closure is even needed here."},
 [{"type":"reflect","purpose":"Have the learner name what the paragraph established.","use_when":"The ending only repeats.","avoid_when":"Significance is already stated."},
  {"type":"predict_reader_understanding","purpose":"Test what the reader should carry forward.","use_when":"The paragraph stops abruptly.","avoid_when":"The forward link is clear."},
  {"type":"evaluate","purpose":"Decide whether this paragraph needs closure at all.","use_when":"Closure feels forced.","avoid_when":"A hinge is clearly needed."},
  {"type":"connect","purpose":"Bridge the paragraph's point to the next idea.","use_when":"Paragraphs feel disjointed.","avoid_when":"The transition already works."}],
 ["Replace a restatement with the paragraph's implication ('what this means for the argument').",
  "Add a one-clause bridge to the next paragraph where the argument needs a hinge.",
  "Delete a forced closing sentence when the paragraph is already complete."],
 {"other_genres":"Completion-vs-stop transfers to scene endings, section wrap-ups, and stanza turns.",
  "other_assignments":"'What should the reader carry forward?' applies to any paragraph that needs a hinge.",
  "other_disciplines":"Where each section's takeaway must be explicit (reports), the function is heightened.",
  "future_writing":"Foundational for signposted professional writing readers can follow by takeaways."},
 "Coherence")

# ---- Paragraph ----
add("Paragraph",
 "Delivers one coherent chunk of meaning the reader can take in as a unit and connect to the whole.",
 "Requires the writer to commit a group of sentences to a single job and to build that job out.",
 {"purpose":"A paragraph performs one share of the whole purpose; multiple jobs signal it should be split.",
  "reader":"Lets the reader absorb the argument in digestible, ordered units.",
  "neighboring_components":"Built from Topic Sentence + Supporting Detail (+ Concluding Sentence); a unit of Organization.",
  "overall_organization":"Paragraph breaks and order should reflect the movement of meaning, not a fixed count."},
 [{"type":"no_governing_purpose","description":"Sentences concern a topic but no single contribution governs them."},
  {"type":"underdeveloped","description":"The point is asserted without enough explanation, evidence, or example."},
  {"type":"incoherent_order","description":"Relevant sentences are ordered so the reader cannot follow the development."},
  {"type":"overloaded","description":"Two or more distinct jobs are crammed into one paragraph that should be divided."}],
 [{"misconception":"A paragraph must be a set number of sentences.","why_productive":"Shows awareness that paragraphs have shape.","leverage":"Replace length rules with function: length follows the job the paragraph must do."},
  {"misconception":"A new idea means a new paragraph, always.","why_productive":"The learner senses paragraphs track ideas.","leverage":"Refine to one governing contribution: related sentences that serve one job stay together."}],
 iod("Writes topic-related sentences with no single governing purpose or clear order.",
     "Holds one purpose but under-develops or mis-orders it, or should split; reorganizes when the paragraph's job is named."),
 {"attempting":"Can the learner state this paragraph's single job? Quote the paragraph.",
  "control_level":"One governing purpose? Relevant, ordered sentences? Adequately developed? Right size (split/combine)? Map to levels.",
  "likely_misconception":"Two jobs in one -> overloaded; loose order -> incoherent_order.",
  "next_move":"Have the learner name the paragraph's job, then test each sentence against it."},
 [{"type":"clarify","purpose":"Name the paragraph's single job.","use_when":"No governing purpose is visible.","avoid_when":"The job is already clear."},
  {"type":"reorganize","purpose":"Order sentences to build the point; split overloaded paragraphs.","use_when":"Order or scope is off.","avoid_when":"The paragraph already moves cleanly."},
  {"type":"expand","purpose":"Develop an under-supported point.","use_when":"The paragraph is thin.","avoid_when":"Development is sufficient."},
  {"type":"reflect","purpose":"Have the learner justify what each sentence contributes.","use_when":"Consolidating.","avoid_when":"The learner is still unclear on the job."}],
 ["State the paragraph's job in one phrase, then cut or move sentences that do not serve it.",
  "Split a paragraph that carries two jobs into two paragraphs, each with its own point.",
  "Develop a thin paragraph with the explanation/evidence the point requires."],
 {"other_genres":"The 'one coherent chunk' unit transfers to scenes, sections, and slides.",
  "other_assignments":"'What is this paragraph's job?' governs paragraphing in any prose.",
  "other_disciplines":"Conventions on length differ; the one-contribution principle is constant.",
  "future_writing":"Foundational for readable reports, articles, and documentation."},
 "Organization")

# ---- Hook / Opening Move ----
add("Hook / Opening Move",
 "Gives the reader a genuine reason to care about the subject from the first lines.",
 "Makes the writer locate what is actually compelling about the subject rather than decorate the opening.",
 {"purpose":"The opening must serve the essay's purpose, not merely attract attention.",
  "reader":"Creates relevant interest tied to what the essay will do.",
  "neighboring_components":"Part of the Introduction; leads toward Background/Context and the Thesis.",
  "overall_organization":"Sets the entry point; its promise must be paid off by the essay."},
 [{"type":"decorative","description":"A generic question, quotation, or dramatic line that does not connect to the essay's purpose."},
  {"type":"disconnected","description":"Interest is created but its link to the essay is unclear."},
  {"type":"overbroad","description":"Opens with sweeping generality ('Since the dawn of time') rather than the real subject."},
  {"type":"misleading","description":"Promises a subject or tone the essay does not deliver."}],
 [{"misconception":"An essay must start with a hook.","why_productive":"Shows awareness that openings should engage.","leverage":"Move from a required device to a relevant reason: what is genuinely worth attending to here?"},
  {"misconception":"A surprising fact or quote is automatically a good hook.","why_productive":"The learner is reaching for interest.","leverage":"Test the device against purpose: does it lead into what the essay argues?"}],
 iod("Opens with a formula (broad statement, generic question) unrelated to the essay's real point.",
     "Creates interest but its connection to the essay's purpose is loose; sharpens when asked what is truly at stake."),
 {"attempting":"Is the opening decorative or purpose-connected? Quote it.",
  "control_level":"Does it create RELEVANT interest and connect clearly to the essay's purpose? Map to levels.",
  "likely_misconception":"Generic device -> decorative; sweeping start -> overbroad.",
  "next_move":"Ask what is genuinely surprising, important, or unresolved about the topic and start there."},
 [{"type":"clarify","purpose":"Find what is actually compelling about the subject.","use_when":"The opening is decorative.","avoid_when":"The opening already earns attention."},
  {"type":"connect","purpose":"Tie the opening to the essay's purpose.","use_when":"Interest is disconnected.","avoid_when":"The link is clear."},
  {"type":"compare","purpose":"Weigh two possible openings for relevance.","use_when":"The learner is unsure how to begin.","avoid_when":"A strong opening exists."},
  {"type":"reflect","purpose":"Have the learner say why a reader should care.","use_when":"Consolidating.","avoid_when":"Purpose is still unclear."}],
 ["Replace a generic device with the genuinely surprising or consequential aspect of the topic.",
  "Add one clause linking the opening to what the essay will establish.",
  "Cut a sweeping 'since the beginning of time' opener and begin at the real subject."],
 {"other_genres":"Purpose-connected openings transfer to talks, applications, and articles.",
  "other_assignments":"'Why should the reader care, and how does that lead in?' applies to any opening.",
  "other_disciplines":"Registers differ; the relevance-over-decoration principle holds.",
  "future_writing":"Foundational for openings in professional and public writing."},
 "Introduction")

# ---- Background / Context ----
add("Background / Context",
 "Gives the reader exactly the prior knowledge needed to follow what comes next — no more, no less.",
 "Forces the writer to model the reader's knowledge and select only preparatory information.",
 {"purpose":"Context exists to make the central discussion understandable; it is not an end in itself.",
  "reader":"Supplies the minimum the reader needs before the main claim will make sense.",
  "neighboring_components":"Part of the Introduction; depends on Audience Awareness; clears the way for the Thesis.",
  "overall_organization":"Sequenced so each piece prepares the next; front-loaded only as far as needed."},
 [{"type":"missing","description":"Essential information the reader needs is assumed rather than provided."},
  {"type":"excessive","description":"Unfocused history or facts that do not prepare the reader overwhelm the opening."},
  {"type":"mis-scoped","description":"Context is provided but not the context this reader actually needs."},
  {"type":"front_loaded","description":"All background is dumped before the reader has a reason to want it."}],
 [{"misconception":"More background shows thoroughness.","why_productive":"The learner is trying to be responsible to the reader.","leverage":"Introduce sufficiency: only what prepares the central discussion belongs."},
  {"misconception":"Everyone needs the same background.","why_productive":"The learner recognizes readers need setup.","leverage":"Attach context to a specific reader's knowledge."}],
 iod("Assumes the reader knows what the writer knows, or dumps unfocused history.",
     "Provides relevant context but too much or mis-scoped; trims when the reader's actual need is named."),
 {"attempting":"Is background missing, excessive, or mis-scoped for this reader? Quote it.",
  "control_level":"Does it supply the minimum sufficient context THIS reader needs before the claim? Map to levels.",
  "likely_misconception":"Unfocused history -> excessive; assumed knowledge -> missing.",
  "next_move":"Ask what the reader must understand before the main claim makes sense, then keep only that."},
 [{"type":"predict_reader_understanding","purpose":"Model what the reader already knows.","use_when":"Background is assumed or excessive.","avoid_when":"The reader model is already clear."},
  {"type":"evaluate","purpose":"Judge which context pieces actually prepare the claim.","use_when":"Context is unfocused.","avoid_when":"It is already minimal and sufficient."},
  {"type":"simplify","purpose":"Cut background that does not serve understanding.","use_when":"The opening is overloaded.","avoid_when":"Every piece is needed."},
  {"type":"connect","purpose":"Tie each context piece to what it prepares.","use_when":"Relevance is unclear.","avoid_when":"Links are explicit."}],
 ["List what the reader must know before the claim, then cut everything else.",
  "Move background to the point of need rather than front-loading it all.",
  "Add the one missing fact the reader needs to follow the argument."],
 {"other_genres":"Reader-calibrated setup transfers to instructions, briefings, and reports.",
  "other_assignments":"'What must the reader know first?' governs context in any writing.",
  "other_disciplines":"What counts as needed context varies; the sufficiency test is constant.",
  "future_writing":"Foundational for onboarding docs, proposals, and explanatory writing."},
 "Audience Awareness")

# ---- Conclusion ----
add("Conclusion",
 "Leaves the reader understanding what was established and why it matters, not just that the essay stopped.",
 "Requires the writer to synthesize the essay's reasoning and state its significance.",
 {"purpose":"Completes the communicative purpose; the conclusion is where 'so what' is delivered.",
  "reader":"Consolidates the reader's new understanding and its implications.",
  "neighboring_components":"Answers the Introduction and Thesis; draws on the whole body's reasoning.",
  "overall_organization":"Returns to the central problem changed by the argument; provides closure suited to purpose."},
 [{"type":"summary_only","description":"Merely restates the thesis and main points without synthesizing or drawing implications."},
  {"type":"new_unsupported","description":"Introduces new claims the essay never supported."},
  {"type":"abrupt","description":"Stops without completing the essay's work for the reader."},
  {"type":"formulaic","description":"Relies on 'In conclusion' restatement rather than significance."}],
 [{"misconception":"A conclusion restates the introduction.","why_productive":"The learner values return and closure.","leverage":"Move from repetition to synthesis: what can the reader now understand that they could not at the start?"},
  {"misconception":"A conclusion should summarize every point.","why_productive":"The learner wants completeness.","leverage":"Redirect to implication and significance over inventory."}],
 iod("Restates the thesis and points, or stops abruptly; cannot say what changed for the reader.",
     "Synthesizes partially but leans on restatement or adds an unsupported flourish; refines when asked for significance."),
 {"attempting":"Is the ending summarizing, synthesizing, or adding new claims? Quote it.",
  "control_level":"Does it return to the claim, synthesize, and draw implications suited to purpose — without new unsupported claims? Map to levels.",
  "likely_misconception":"Repeats the intro -> summary_only; new claim -> new_unsupported.",
  "next_move":"Ask what the reader can now understand that was unclear at the start, and why it matters."},
 [{"type":"reflect","purpose":"Have the learner name what the essay established.","use_when":"The ending only restates.","avoid_when":"Significance is already articulated."},
  {"type":"predict_reader_understanding","purpose":"Test the reader's new understanding.","use_when":"The essay stops abruptly.","avoid_when":"Closure already lands."},
  {"type":"justify","purpose":"Ask why the argument matters.","use_when":"Significance is missing.","avoid_when":"The 'so what' is clear."},
  {"type":"evaluate","purpose":"Check the conclusion against the essay's purpose.","use_when":"Closure feels generic.","avoid_when":"It already fits the purpose."}],
 ["Replace restatement with a synthesis of what the reasoning together established.",
  "State the implication or significance the argument earns, without adding new evidence.",
  "Cut a new unsupported claim from the ending and fold significance in instead."],
 {"other_genres":"Completion-over-summary transfers to reflective, narrative, and evaluative endings.",
  "other_assignments":"'What does the reader now understand, and why does it matter?' applies to any close.",
  "other_disciplines":"Report recommendations vs literary insight differ in form; synthesis is constant.",
  "future_writing":"Foundational for executive summaries and recommendation sections."},
 "Thesis")

# ---- Title ----
add("Title",
 "Tells the reader what the piece is about and what to expect, setting accurate expectations.",
 "Makes the writer name both the subject and the angle, testing whether they know their own point.",
 {"purpose":"Frames the subject and signals the essay's angle or genre.",
  "reader":"Invites appropriate expectations and orients before the first line.",
  "neighboring_components":"Reflects the Thesis and overall Purpose; pairs with the Introduction.",
  "overall_organization":"A frame for the whole; finalized once the essay's point is settled."},
 [{"type":"generic","description":"Overly general or vague ('Essay 1', 'My Paper') and tells the reader nothing."},
  {"type":"assignment_label","description":"Simply repeats the assignment prompt rather than the essay's point."},
  {"type":"decorative","description":"Clever but does not reflect the actual subject or angle."},
  {"type":"misleading","description":"Sets expectations the essay does not meet."}],
 [{"misconception":"The title is decoration added at the end.","why_productive":"The learner knows titles come last.","leverage":"Reframe as a framing tool: it should name the subject AND the angle."},
  {"misconception":"A title should be catchy above all.","why_productive":"The learner wants to engage.","leverage":"Balance interest with accuracy to the completed essay."}],
 iod("Uses the assignment label or a vague/decorative phrase; cannot name the essay's angle.",
     "Names the subject but not what the essay says about it, or over-reaches for cleverness; refines when asked for the angle."),
 {"attempting":"Does the title name the subject, the angle, both, or neither? Quote it.",
  "control_level":"Precise, purposeful, aligned with the finished essay, appropriately engaging? Map to levels.",
  "likely_misconception":"Repeats the prompt -> assignment_label; vague -> generic.",
  "next_move":"Ask the learner to name both the subject and what the essay reveals about it."},
 [{"type":"clarify","purpose":"Name the subject and the angle together.","use_when":"The title is vague or a label.","avoid_when":"Both are already present."},
  {"type":"compare","purpose":"Weigh two candidate titles for accuracy and interest.","use_when":"The learner is unsure.","avoid_when":"A strong title exists."},
  {"type":"evaluate","purpose":"Check the title against the finished essay.","use_when":"Alignment is uncertain.","avoid_when":"It already fits."},
  {"type":"reflect","purpose":"Have the learner justify what the title promises.","use_when":"Consolidating.","avoid_when":"Purpose is unclear."}],
 ["Rewrite a label as subject + angle ('what this essay says about X').",
  "Test the title against the finished essay and adjust for accuracy.",
  "Trade a purely clever title for one that also signals the real point."],
 {"other_genres":"Subject+angle framing transfers to headlines, report titles, and subject lines.",
  "other_assignments":"'Name the subject and the point' governs any title.",
  "other_disciplines":"Descriptive vs argumentative title conventions differ; the framing habit is constant.",
  "future_writing":"Foundational for email subjects, report titles, and document naming."},
 "Purpose")

# ---- Sentence ----
add("Sentence",
 "Delivers one complete thought the reader can parse — who/what and what is said about it.",
 "Requires the writer to control subject, action, and structure so the meaning is unambiguous.",
 {"purpose":"Carries a unit of meaning toward the passage's point; structure should serve emphasis and clarity.",
  "reader":"Lets the reader identify the actor/topic and the assertion without re-reading.",
  "neighboring_components":"The building block of the Paragraph; realizes Word Choice, Tone, and Voice.",
  "overall_organization":"Sentence variety and structure track emphasis and the flow of ideas."},
 [{"type":"fragment","description":"An incomplete unit missing a subject or predicate the reader needs."},
  {"type":"fused_or_comma_splice","description":"Two complete thoughts run together without proper joining."},
  {"type":"overloaded","description":"Too many clauses/modifiers so the main relationship is lost."},
  {"type":"ambiguous","description":"Word order or reference makes who-does-what unclear."}],
 [{"misconception":"Longer, more complex sentences are more sophisticated.","why_productive":"The learner is reaching for maturity.","leverage":"Shift to control: structure should clarify the main relationship, not bury it."},
  {"misconception":"Grammar rules are separate from meaning.","why_productive":"The learner attends to correctness.","leverage":"Tie structure to comprehension: punctuation and order encode relationships the reader must see."}],
 iod("Produces fragments, fused sentences, or tangled structures the reader cannot parse.",
     "Writes clear simple sentences but loses control when combining clauses; rebuilds when the core relationship is named."),
 {"attempting":"Can the reader identify the actor/topic and the assertion? Quote the sentence.",
  "control_level":"Complete, unambiguous, appropriately varied, punctuated to show relationships? Map to levels.",
  "likely_misconception":"Runs thoughts together -> fused_or_comma_splice; clause pile-up -> overloaded.",
  "next_move":"Have the learner name the central actor/topic and main action, then rebuild around that relationship."},
 [{"type":"clarify","purpose":"Identify the sentence's core actor and action.","use_when":"The sentence is tangled.","avoid_when":"It is already clear."},
  {"type":"reorganize","purpose":"Restructure clauses so the main relationship leads.","use_when":"Emphasis is buried.","avoid_when":"Structure already serves meaning."},
  {"type":"simplify","purpose":"Break an overloaded sentence into controlled units.","use_when":"Too many clauses obscure the point.","avoid_when":"Complexity is controlled."},
  {"type":"reflect","purpose":"Have the learner read the sentence as a stranger would.","use_when":"Ambiguity is suspected.","avoid_when":"Clarity is confirmed."}],
 ["Identify the main actor and action, then rebuild the sentence around that core.",
  "Split a fused/overloaded sentence into units that show one relationship each.",
  "Reorder clauses so the emphasis falls where the meaning needs it."],
 {"other_genres":"Sentence control transfers to every kind of writing and speech.",
  "other_assignments":"'Who does what, made clear' applies universally.",
  "other_disciplines":"Register varies; parseability is constant.",
  "future_writing":"Foundational for clear professional correspondence and documentation."},
 "Word Choice")

# ---- Word Choice ----
add("Word Choice",
 "Gives the reader the writer's exact meaning with the right precision, force, and connotation.",
 "Makes the writer match language to intended meaning, audience, and context rather than settle for the first word.",
 {"purpose":"Words are chosen to serve the intended meaning and effect, not variety for its own sake.",
  "reader":"Precise wording prevents misunderstanding and sets connotation.",
  "neighboring_components":"Realized within the Sentence; shapes Tone and Voice; serves Audience Awareness.",
  "overall_organization":"Consistent terminology supports Coherence across the piece."},
 [{"type":"vague","description":"Wording is too general to convey the intended meaning."},
  {"type":"inaccurate","description":"The chosen word does not mean what the writer intends."},
  {"type":"inflated","description":"Unnecessarily elevated wording obscures rather than clarifies."},
  {"type":"connotation_mismatch","description":"The word's associations conflict with the intended effect or audience."}],
 [{"misconception":"Bigger or more varied vocabulary is better writing.","why_productive":"The learner values range.","leverage":"Shift to fit: the best word is the one that carries the exact meaning for this reader."},
  {"misconception":"Synonyms are interchangeable.","why_productive":"The learner is avoiding repetition.","leverage":"Introduce connotation: near-synonyms differ in association and force."}],
 iod("Reaches for impressive or generic words without checking them against intended meaning.",
     "Chooses accurate words in familiar contexts but misses connotation or precision under pressure; revises when meaning is compared."),
 {"attempting":"Is the wording precise, inflated, or off in connotation? Quote the word/phrase.",
  "control_level":"Does the word carry the exact intended meaning for this audience/context? Map to levels.",
  "likely_misconception":"Synonym swapped in -> connotation_mismatch; grand word -> inflated.",
  "next_move":"Ask the learner what they mean in ordinary language, then compare that with the current word."},
 [{"type":"clarify","purpose":"State the intended meaning in plain language.","use_when":"Wording is vague or inflated.","avoid_when":"Meaning is already precise."},
  {"type":"compare","purpose":"Weigh the current word against a plainer alternative.","use_when":"Connotation may be off.","avoid_when":"The word already fits."},
  {"type":"evaluate","purpose":"Judge whether a different word improves understanding.","use_when":"Precision is uncertain.","avoid_when":"The word is exact."},
  {"type":"reflect","purpose":"Have the learner justify a deliberate word choice.","use_when":"Consolidating.","avoid_when":"The choice is not yet deliberate."}],
 ["Say the meaning in ordinary words, then choose the word that carries it exactly.",
  "Replace an inflated or vague term with the precise one the meaning needs.",
  "Check a near-synonym's connotation against the intended effect and adjust."],
 {"other_genres":"Precision and connotation transfer to all writing and speaking.",
  "other_assignments":"'Does this word carry my exact meaning?' applies everywhere.",
  "other_disciplines":"Technical vocabulary differs; the meaning-fit test is constant.",
  "future_writing":"Foundational for precise professional and technical communication."},
 "Tone")

# ---- Tone ----
add("Tone",
 "Shapes how the reader experiences the writer's stance toward the subject and toward them.",
 "Makes the writer decide the relationship they want with the reader and hold it deliberately.",
 {"purpose":"Tone is chosen to fit the purpose and the desired relationship with the reader.",
  "reader":"Signals how to take the writer — as authority, peer, advocate — and whether to trust the stance.",
  "neighboring_components":"Produced through Word Choice and Sentence structure; a facet of Voice; calibrated by Audience Awareness.",
  "overall_organization":"Held consistently, or varied deliberately, across the whole piece."},
 [{"type":"mismatch","description":"Tone does not suit the audience, purpose, or subject."},
  {"type":"unintended_shift","description":"The stance shifts without intention, confusing the reader."},
  {"type":"overreach","description":"Dismissive, exaggerated, or falsely authoritative stance undermines trust."},
  {"type":"flat","description":"Detached or generic tone conveys no stance where one is needed."}],
 [{"misconception":"Academic writing must be toneless.","why_productive":"The learner is avoiding inappropriate informality.","leverage":"Reframe: even formal writing has a deliberate stance toward reader and subject."},
  {"misconception":"Tone is just word choice.","why_productive":"The learner links tone to language.","leverage":"Broaden to certainty, detail, and syntax as tone-carrying choices."}],
 iod("Writes with an unexamined or mismatched stance; cannot name the relationship the tone creates.",
     "Sets an appropriate tone but shifts unintentionally or overreaches; adjusts when the intended relationship is named."),
 {"attempting":"What stance does the tone create, and does it suit purpose/audience? Quote a telling phrase.",
  "control_level":"Consistent, appropriate, trust-building, deliberately varied where useful? Map to levels.",
  "likely_misconception":"Sudden informality -> unintended_shift; grand claims -> overreach.",
  "next_move":"Ask how the writer wants the reader to experience the voice, then find one choice that supports or undermines it."},
 [{"type":"clarify","purpose":"Name the relationship the writer wants with the reader.","use_when":"Tone is unexamined.","avoid_when":"The stance is deliberate."},
  {"type":"evaluate","purpose":"Judge whether the tone fits purpose and audience.","use_when":"Tone may be mismatched.","avoid_when":"It clearly fits."},
  {"type":"reorganize","purpose":"Locate and resolve an unintended shift.","use_when":"The stance wavers.","avoid_when":"Tone is consistent."},
  {"type":"reflect","purpose":"Have the learner explain how a choice creates the tone.","use_when":"Consolidating.","avoid_when":"Control is not yet present."}],
 ["Name the intended relationship with the reader, then adjust wording that fights it.",
  "Locate the sentence where the tone shifts and bring it back to the intended stance.",
  "Temper an overreaching or dismissive phrase to rebuild the reader's trust."],
 {"other_genres":"Deliberate stance transfers to persuasive, reflective, and professional registers.",
  "other_assignments":"'How should the reader experience me?' applies to any writing.",
  "other_disciplines":"Expected registers differ; deliberate control is constant.",
  "future_writing":"Foundational for emails, advocacy, and public-facing writing."},
 "Voice")

# ---- Audience Awareness ----
add("Audience Awareness",
 "Ensures the writing meets the reader where they are — what they know, need, and might misread.",
 "Makes the writer model a real reader and choose content, evidence, and tone for them.",
 {"purpose":"The purpose is defined relative to a reader; audience shapes every other choice.",
  "reader":"Directly anticipates the reader's knowledge, questions, and points of confusion.",
  "neighboring_components":"Governs Background/Context, Word Choice, Tone, Evidence selection, and Organization.",
  "overall_organization":"Reader needs drive what to explain first and how much to include."},
 [{"type":"writer_only","description":"Writes from personal understanding without modeling the reader."},
  {"type":"unjustified_assumption","description":"Attributes knowledge or reactions to the reader without warrant."},
  {"type":"one_size","description":"Ignores differences among possible readers."},
  {"type":"mis-estimated","description":"Over- or under-estimates what the reader knows."}],
 [{"misconception":"Good writing is clear to everyone equally.","why_productive":"The learner values clarity.","leverage":"Introduce specificity: clarity is relative to a particular reader's knowledge."},
  {"misconception":"The teacher is the only audience.","why_productive":"The learner has a concrete reader in mind.","leverage":"Widen to the intended reader the writing is really for."}],
 iod("Writes only from personal understanding; does not consider what a reader needs or might misread.",
     "Considers a reader in places but assumes knowledge or reactions without warrant; adapts when a specific reader is imagined."),
 {"attempting":"Is the learner modeling a reader or writing from self? Quote where a reader assumption appears.",
  "control_level":"Are reader knowledge, questions, and confusions anticipated and served? Map to levels.",
  "likely_misconception":"No reader modeled -> writer_only; assumed reactions -> unjustified_assumption.",
  "next_move":"Ask the learner to imagine a particular reader and name that reader's first question or confusion."},
 [{"type":"predict_reader_understanding","purpose":"Model a specific reader's knowledge and questions.","use_when":"Writing is self-referential.","avoid_when":"A reader model is already active."},
  {"type":"evaluate","purpose":"Test choices against that reader's needs.","use_when":"Assumptions are unwarranted.","avoid_when":"Choices already fit the reader."},
  {"type":"clarify","purpose":"Name who the writing is actually for.","use_when":"Audience is unspecified.","avoid_when":"It is defined."},
  {"type":"reflect","purpose":"Have the learner justify an audience-driven choice.","use_when":"Consolidating.","avoid_when":"Reader-awareness is not yet present."}],
 ["Name a specific reader, then list their first two likely questions and answer them.",
  "Check each assumption attributed to the reader and adjust unwarranted ones.",
  "Revise an explanation to fit what this reader actually knows."],
 {"other_genres":"Reader modeling transfers to every communicative act.",
  "other_assignments":"'Who is this for and what do they need?' governs all writing.",
  "other_disciplines":"Expert vs lay audiences differ; the modeling habit is constant.",
  "future_writing":"Foundational for client, user, and stakeholder communication."},
 "Purpose")

# ---- Purpose ----
add("Purpose",
 "Determines what should be different for the reader after reading — the change the writing seeks.",
 "Gives the writer the standard against which every choice is judged and coordinated.",
 {"purpose":"Purpose is the top-level intention all other elements serve.",
  "reader":"Names the intended change in the reader's understanding, judgment, feeling, or action.",
  "neighboring_components":"Directs Thesis, Organization, Evidence, Tone, and Audience choices.",
  "overall_organization":"Every section should be traceable to the purpose; drift signals a purpose problem."},
 [{"type":"unclear","description":"The writer cannot say what the writing is meant to accomplish."},
  {"type":"assignment_completion","description":"Purpose has collapsed into 'finish the task' rather than affect a reader."},
  {"type":"mismatch","description":"The essay's choices serve a different purpose than the stated one."},
  {"type":"drift","description":"The purpose shifts mid-draft without the writer noticing."}],
 [{"misconception":"The purpose is to answer the prompt.","why_productive":"The learner is task-oriented.","leverage":"Lift from task to reader effect: what should change for the reader?"},
  {"misconception":"Purpose and topic are the same.","why_productive":"The learner has a subject in mind.","leverage":"Separate subject (about what) from purpose (to do what to the reader)."}],
 iod("Equates purpose with completing the assignment; cannot state the intended effect on a reader.",
     "Names a purpose but the draft's choices only partly serve it, or it drifts; re-coordinates when the effect is restated."),
 {"attempting":"Can the learner state the intended reader-effect, or only the task? Quote their statement.",
  "control_level":"Is the purpose meaningful, maintained, and served by the essay's choices? Map to levels.",
  "likely_misconception":"'Answer the prompt' -> assignment_completion; choices serve something else -> mismatch.",
  "next_move":"Ask what should become different for the reader after reading, then judge the passage by it."},
 [{"type":"clarify","purpose":"State the intended change in the reader.","use_when":"Purpose is unclear or task-bound.","avoid_when":"It is already articulated."},
  {"type":"evaluate","purpose":"Test whether choices serve the stated purpose.","use_when":"There is a suspected mismatch.","avoid_when":"Alignment is evident."},
  {"type":"connect","purpose":"Trace sections back to the purpose.","use_when":"Drift is suspected.","avoid_when":"Everything traces cleanly."},
  {"type":"reflect","purpose":"Have the learner restate purpose in their own words.","use_when":"Consolidating.","avoid_when":"Purpose is still confused."}],
 ["State the intended reader-effect in one sentence, then test each section against it.",
  "Realign choices that serve a different purpose than the one intended.",
  "Name where the purpose drifted and decide which purpose to keep."],
 {"other_genres":"Purpose-first reasoning transfers to every genre (genres are means to purposes).",
  "other_assignments":"'What should change for the reader?' governs all writing.",
  "other_disciplines":"Disciplinary aims differ; the reader-effect question is constant.",
  "future_writing":"Foundational for goal-directed professional writing."},
 "Thesis")

# ---- Organization ----
add("Organization",
 "Lets the reader follow the development of the writing through purposeful arrangement.",
 "Makes the writer decide the major jobs and order them by logic and reader need.",
 {"purpose":"Arrangement should reflect the argument and the reader's path, not the order ideas occurred.",
  "reader":"Provides a followable progression from one idea to the next.",
  "neighboring_components":"Sequences Paragraphs; realizes the Thesis's parts; supported by Transitions and Coherence.",
  "overall_organization":"Is the whole-level plan the other elements populate."},
 [{"type":"no_progression","description":"No discernible development; sections appear in the order they were thought of."},
  {"type":"ungrouped","description":"Related material is scattered rather than grouped."},
  {"type":"mis-sequenced","description":"Order does not follow the logic the reader needs."},
  {"type":"unmarked_relationships","description":"Sections are present but their relationships to each other are unclear."}],
 [{"misconception":"Organization means the five-paragraph format.","why_productive":"The learner has a structural schema.","leverage":"Replace the template with function: structure follows the jobs the argument requires."},
  {"misconception":"Write ideas in the order they come.","why_productive":"The learner is generating material.","leverage":"Separate drafting order from the reader's needed order."}],
 iod("Presents ideas in the order they occurred, with no grouping or reader-driven sequence.",
     "Groups some material but sequence or relationships are off; replans when the essay's jobs are named."),
 {"attempting":"Is there a reader-driven progression, or just occurrence order? Outline the sections.",
  "control_level":"Are ideas grouped and sequenced by logic and reader need, with clear relationships? Map to levels.",
  "likely_misconception":"Thought-order draft -> no_progression; scattered material -> ungrouped.",
  "next_move":"Have the learner name the major jobs the essay must do and order them the way the reader needs."},
 [{"type":"clarify","purpose":"Name the major jobs the essay must perform.","use_when":"No plan is visible.","avoid_when":"The jobs are already named."},
  {"type":"reorganize","purpose":"Group and re-sequence sections by reader need.","use_when":"Order is off.","avoid_when":"The sequence already works."},
  {"type":"connect","purpose":"Make relationships among sections explicit.","use_when":"Sections feel disconnected.","avoid_when":"Relationships are clear."},
  {"type":"evaluate","purpose":"Test whether the order reflects the argument.","use_when":"Structure may mirror drafting order.","avoid_when":"It reflects the logic."}],
 ["List the major jobs the essay must do, then order them the way the reader needs.",
  "Group scattered material that serves the same job into one place.",
  "Re-sequence sections so each prepares the next."],
 {"other_genres":"Reader-driven arrangement transfers to reports, talks, and narratives.",
  "other_assignments":"'What jobs, in what order for the reader?' governs any structure.",
  "other_disciplines":"Conventional structures differ; the function-over-template principle holds.",
  "future_writing":"Foundational for structuring documents, proposals, and presentations."},
 "Coherence")

# ---- Coherence ----
add("Coherence",
 "Lets the reader see how each idea follows from the last as one continuous line of thought.",
 "Makes the writer establish and signal the real relationships among ideas.",
 {"purpose":"Coherence serves understanding: the reader must be able to trace the reasoning.",
  "reader":"Ensures each move connects to the previous one without unstated leaps.",
  "neighboring_components":"Achieved through Transitions, repeated concepts, and consistent terminology across Sentences and Paragraphs.",
  "overall_organization":"Local coherence realizes the whole-level Organization for the reader."},
 [{"type":"unexplained_shift","description":"The line of thought jumps without showing how ideas relate."},
  {"type":"missing_relationship","description":"Ideas sit adjacent with no stated logical/semantic link."},
  {"type":"contradiction","description":"Adjacent claims conflict without acknowledgement."},
  {"type":"assumed_link","description":"The connection depends on unstated assumptions only the writer holds."}],
 [{"misconception":"Coherence means adding transition words.","why_productive":"The learner knows connectives help.","leverage":"Move from labels to relationships: name the actual link, then express it."},
  {"misconception":"If I understand it, it flows.","why_productive":"The learner has an internal line of thought.","leverage":"Externalize: the reader can only follow what the text makes explicit."}],
 iod("Places ideas side by side with unexplained shifts; assumes the reader shares the writer's links.",
     "Connects ideas in places but leaves some relationships implicit; makes them explicit when a specific shift is examined."),
 {"attempting":"Can the reader explain how each idea follows from the previous? Quote a shift.",
  "control_level":"Are relationships explicit, consistent, and free of unstated leaps? Map to levels.",
  "likely_misconception":"Adds 'however/therefore' without a real link -> unexplained_shift; writer-only logic -> assumed_link.",
  "next_move":"Select one confusing shift and ask the learner to state the relationship between the ideas explicitly."},
 [{"type":"clarify","purpose":"State the relationship between two adjacent ideas.","use_when":"A shift is unexplained.","avoid_when":"The link is clear."},
  {"type":"connect","purpose":"Make an implicit relationship explicit in the text.","use_when":"The reader must infer the link.","avoid_when":"It is already stated."},
  {"type":"reorganize","purpose":"Reorder ideas so each follows from the last.","use_when":"Sequence breaks the line of thought.","avoid_when":"The progression holds."},
  {"type":"reflect","purpose":"Have the learner trace the line of thought as a reader.","use_when":"Consolidating.","avoid_when":"Coherence is not yet achieved."}],
 ["Name the relationship between two ideas in plain words, then express it in the text.",
  "Make an assumed link explicit so the reader need not infer it.",
  "Reorder or bridge ideas at the point the reader would lose the thread."],
 {"other_genres":"Traceable reasoning transfers to argument, explanation, and narrative.",
  "other_assignments":"'Can the reader follow each step?' applies to all connected prose.",
  "other_disciplines":"What counts as a warranted link varies; explicit connection is constant.",
  "future_writing":"Foundational for logical reports, analyses, and instructions."},
 "Transition")

# ---- Unity ----
add("Unity",
 "Assures the reader that everything in the passage serves one central purpose, with no distractions.",
 "Makes the writer test every part against the passage's governing purpose and cut or refit the rest.",
 {"purpose":"Unity is fidelity to the governing purpose: parts that do not serve it do not belong.",
  "reader":"Keeps the reader focused on one line of work without digression.",
  "neighboring_components":"Applies within the Paragraph and across the whole; complements Coherence (relatedness) with relevance-to-purpose.",
  "overall_organization":"Each part must have a discernible function relative to the purpose."},
 [{"type":"digression","description":"Interesting but off-purpose material distracts from the central work."},
  {"type":"topic_not_purpose","description":"Material relates to the topic but not to the passage's actual purpose."},
  {"type":"functionless_part","description":"A sentence or section has no discernible job."},
  {"type":"competing_purpose","description":"Two purposes contend within one passage that should serve one."}],
 [{"misconception":"If it's about the topic, it belongs.","why_productive":"The learner is gathering relevant-seeming material.","leverage":"Shift the test from topic to purpose: does this part perform the passage's job?"},
  {"misconception":"Good material should never be cut.","why_productive":"The learner values their content.","leverage":"Reframe cutting as relocating: keep good material where it serves a purpose."}],
 iod("Keeps material because it is interesting or on-topic, without testing it against the purpose.",
     "Detects some digressions but hesitates to cut or refit; reorganizes when each part is tested against the passage's job."),
 {"attempting":"Can the learner state the passage's job and defend each part by it? Quote the first off-purpose part.",
  "control_level":"Does every part serve one governing purpose, with digressions removed or refit? Map to levels.",
  "likely_misconception":"On-topic tangent -> topic_not_purpose; kept-because-interesting -> digression.",
  "next_move":"Ask the learner to name the passage's job, then examine the first sentence that does not perform it."},
 [{"type":"clarify","purpose":"Name the passage's single governing purpose.","use_when":"Focus is diffuse.","avoid_when":"The purpose is clear."},
  {"type":"evaluate","purpose":"Test each part against that purpose.","use_when":"Digressions are suspected.","avoid_when":"Every part clearly serves it."},
  {"type":"reorganize","purpose":"Cut, relocate, or refit off-purpose material.","use_when":"Useful material sits in the wrong place.","avoid_when":"Everything is in place."},
  {"type":"reflect","purpose":"Have the learner justify why each part belongs.","use_when":"Consolidating.","avoid_when":"Focus is not yet controlled."}],
 ["Name the passage's job, then test each sentence: does it perform that job?",
  "Relocate good but off-purpose material to where it serves a purpose.",
  "Cut a digression the passage does not need."],
 {"other_genres":"Relevance-to-purpose transfers to reports, talks, and narratives.",
  "other_assignments":"'Does each part serve the job?' governs focus in any passage.",
  "other_disciplines":"What serves the purpose varies; the discipline of focus is constant.",
  "future_writing":"Foundational for concise, on-point professional writing."},
 "Coherence")

# ---- Voice ----
add("Voice",
 "Lets the reader sense a real writer thinking — a genuine perspective behind the words.",
 "Requires the writer to own ideas they understand and make deliberate, confident choices.",
 {"purpose":"Voice carries the writer's authorship of ideas while meeting the demands of the context.",
  "reader":"Signals that a person with understanding stands behind the reasoning.",
  "neighboring_components":"Emerges through Word Choice, Tone, and Sentence choices; disciplined by Evidence and reasoning.",
  "overall_organization":"A consistent perspective across the piece; adapts to genre and audience."},
 [{"type":"generic","description":"Sounds borrowed, mechanical, or like anyone; no perspective present."},
  {"type":"erased_by_formality","description":"Formal language removes the writer's agency and understanding."},
  {"type":"undisciplined","description":"Personal voice replaces reasoning or evidence."},
  {"type":"borrowed","description":"Sources are echoed without the writer's own understanding or authorship."}],
 [{"misconception":"Academic writing should sound impersonal, so voice is inappropriate.","why_productive":"The learner is meeting formality norms.","leverage":"Reframe: voice is disciplined perspective, compatible with academic register."},
  {"misconception":"Voice means writing casually or about myself.","why_productive":"The learner senses authorship matters.","leverage":"Redirect to owned reasoning expressed with appropriate confidence."}],
 iod("Produces generic or borrowed prose, or lets formal language erase their understanding.",
     "Shows perspective in places but loses it under formality or leans on personality over reasoning; steadies when asked to explain the idea in their own words."),
 {"attempting":"Does a perspective come through, or is it generic/borrowed? Quote a telling passage.",
  "control_level":"Is there an identifiable, disciplined perspective adapted to the context? Map to levels.",
  "likely_misconception":"Formal-but-empty -> erased_by_formality; source-echo -> borrowed.",
  "next_move":"Ask the learner to explain the idea aloud in their own words, then revise preserving that meaning within the context's demands."},
 [{"type":"reflect","purpose":"Have the learner explain the idea in their own words.","use_when":"The prose sounds borrowed.","avoid_when":"Understanding is clearly the learner's own."},
  {"type":"clarify","purpose":"Surface what the learner actually thinks about the idea.","use_when":"Voice is generic.","avoid_when":"A perspective is present."},
  {"type":"revise","purpose":"Rework a passage to preserve owned meaning within the register.","use_when":"Formality has erased agency.","avoid_when":"Voice and register already coexist."},
  {"type":"evaluate","purpose":"Check whether confidence matches understanding.","use_when":"Stance seems over/understated.","avoid_when":"Confidence is calibrated."}],
 ["Explain the idea aloud in your own words, then rewrite the passage to keep that understanding.",
  "Replace echoed source language with your own reasoning about the point.",
  "Adjust confidence so it matches what you actually understand and can defend."],
 {"other_genres":"Owned, adaptable perspective transfers to reflective, analytical, and professional writing.",
  "other_assignments":"'Do I understand and stand behind this?' applies to any authored text.",
  "other_disciplines":"Conventions on visible authorship differ; owned reasoning is constant.",
  "future_writing":"Foundational for authoritative professional and public writing."},
 "Tone")

# ---- Revision ----
add("Revision",
 "Improves what the writing communicates and how well, judged by a reader's actual understanding.",
 "Makes the writer re-see the draft against purpose, meaning, and reader response — not just fix errors.",
 {"purpose":"Revision realigns the draft with its purpose and the reader's understanding.",
  "reader":"Re-reads from the reader's perspective to find where meaning breaks down.",
  "neighboring_components":"Operates across all elements — from Purpose and Organization down to Sentence and Word Choice.",
  "overall_organization":"Substantive changes precede proofreading; global before local."},
 [{"type":"editing_only","description":"Revision is limited to correction and word substitution."},
  {"type":"no_mismatch_detection","description":"The writer does not notice gaps among purpose, meaning, structure, and reader response."},
  {"type":"local_before_global","description":"Sentences are polished while larger problems remain."},
  {"type":"changes_unjustified","description":"Changes are made without a reason connected to communication."}],
 [{"misconception":"Revision means fixing grammar and spelling.","why_productive":"The learner attends to correctness.","leverage":"Expand to substance: revision reworks meaning and structure, then proofreads."},
  {"misconception":"A draft that reads fine to me needs no revision.","why_productive":"The learner trusts their reading.","leverage":"Introduce the reader's perspective as the test."}],
 iod("Treats revision as correction and word swaps; does not detect mismatches among purpose, meaning, and structure.",
     "Makes some substantive changes but stays local or cannot say why a change helps; deepens when one high-leverage, purpose-connected issue is chosen."),
 {"attempting":"Is the learner correcting or re-seeing? Quote the change made.",
  "control_level":"Does the learner reread as a reader, find consequential problems, change substantively, and explain the gain? Map to levels.",
  "likely_misconception":"Grammar-only pass -> editing_only; polish-first -> local_before_global.",
  "next_move":"Choose one high-leverage, purpose-connected issue; ask for a meaningful change and compare the two versions' effect."},
 [{"type":"evaluate","purpose":"Judge the draft against purpose and reader understanding.","use_when":"Revision is stuck at editing.","avoid_when":"Substantive re-seeing is underway."},
  {"type":"compare","purpose":"Weigh the effect of two versions of a passage.","use_when":"The value of a change is unclear.","avoid_when":"The improvement is evident and explained."},
  {"type":"clarify","purpose":"Name the single highest-leverage problem now.","use_when":"Many small edits obscure the real issue.","avoid_when":"The priority is clear."},
  {"type":"reflect","purpose":"Have the learner explain why a revision improves communication.","use_when":"Consolidating.","avoid_when":"The rationale is still missing."}],
 ["Reread as the intended reader and mark the first place meaning breaks down.",
  "Choose one high-leverage, purpose-connected change and make it before polishing.",
  "Compare the two versions and state what the change does for the reader."],
 {"other_genres":"Re-seeing against purpose transfers to every kind of writing.",
  "other_assignments":"'What is the one change that most helps the reader?' applies to any draft.",
  "other_disciplines":"Standards differ; the reader-perspective reread is constant.",
  "future_writing":"Foundational for iterative professional writing and editing."},
 "Purpose")

# ---------------------------------------------------------------------------
# APPLY
# ---------------------------------------------------------------------------
def main():
    kb = json.load(open(KB_PATH, encoding="utf-8"))
    objs = kb["instructional_objects"]
    by_el = {o["element"]: o for o in objs}
    report = []

    targets = list(CANON.keys())
    for el in targets:
        assert el not in PILOTS, f"{el} is a pilot; must not be touched"
        o = by_el[el]
        d = DEEP[el]
        canon = CANON[el]
        prov = {}

        # 1) canonical 5 fields — VERBATIM
        o["definition"] = canon[0]
        o["performance_structure"] = canon[1]
        o["recognition_diagnostics"] = canon[2]
        o["next_developmental_moves"] = canon[3]
        o["indicators_of_control"] = canon[4]
        for k in ["definition","performance_structure","recognition_diagnostics","next_developmental_moves","indicators_of_control"]:
            prov[k] = "canonical_verbatim"

        # 2) deeper fields — conservative
        o["reader_function"] = d["reader_function"]; prov["reader_function"] = "pattern_interpreted"
        o["writer_function"] = d["writer_function"]; prov["writer_function"] = "pattern_interpreted"
        o["functional_relationships"] = d["functional_relationships"]; prov["functional_relationships"] = "pattern_interpreted"
        o["common_difficulties"] = d["common_difficulties"]; prov["common_difficulties"] = "canonical_derived"  # from Recognition & Diagnosis
        o["productive_misconceptions"] = d["productive_misconceptions"]; prov["productive_misconceptions"] = "pattern_interpreted"
        iodict = dict(d["indicators_of_development"])
        iodict["independent"] = canon[4]  # canonical Indicators of Increasing Control
        iodict["flexible"] = canon[4]
        o["indicators_of_development"] = iodict
        prov["indicators_of_development"] = "mixed (independent/flexible=canonical_verbatim; early/partial=pattern_interpreted)"
        o["recognition_diagnostics_detailed"] = d["recognition_diagnostics_detailed"]; prov["recognition_diagnostics_detailed"] = "canonical_derived"
        o["developmental_invitations"] = d["developmental_invitations"]; prov["developmental_invitations"] = "pattern_interpreted"
        o["followup_decisions"] = followups(el.split(" / ")[0].lower(), d["_neighbor"]); prov["followup_decisions"] = "pattern_interpreted"
        o["revision_strategies"] = d["revision_strategies"]; prov["revision_strategies"] = "canonical_derived"
        o["stopping_conditions"] = stopping(el.split(" / ")[0].lower()); prov["stopping_conditions"] = "pattern_interpreted"
        o["transfer"] = d["transfer"]; prov["transfer"] = "pattern_interpreted"
        o["engine_usage"] = copy.deepcopy(ENGINE_USAGE); prov["engine_usage"] = "pattern_boilerplate"

        o["canonical_source"] = "Writing Elements Chart"
        o["enrichment_version"] = ENRICH_VERSION
        o["field_provenance"] = prov

        report.append((el, prov))

    kb["instructional_objects"] = objs
    with open(KB_PATH, "w", encoding="utf-8") as f:
        json.dump(kb, f, ensure_ascii=False, indent=2)

    print(f"Enriched {len(targets)} objects with {ENRICH_VERSION}.")
    return report

if __name__ == "__main__":
    main()
