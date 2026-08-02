import json

PATH = "/app/backend/canonical_writing_model.json"
m = json.load(open(PATH))

record = {
  "domain_name": "Paragraph Purpose",
  "domain_status": {
    "description": "Culturally available functions and resources for the work a paragraph does within a whole essay.",
    "is_not": ["a rigid one-structure template", "a rule that every paragraph opens with a topic sentence", "a rule that every paragraph must be claim-evidence-analysis", "a rule that a paragraph performs only one function", "a developmental stage", "a grading checklist", "the same thing as the paragraph's topic"],
    "must_be_interpreted_relative_to": ["the assignment", "the writer's operative purpose", "the teacher's pedagogical purpose", "the intended audience", "the genre", "the central claim or controlling idea", "the neighboring paragraphs", "the organization of the developing whole essay"]
  },
  "governing_communicative_function": "A paragraph is a locally organized movement of meaning that performs one or more coordinated functions in relation to the developing whole text. Its purpose is the work it does for the reader and the essay, not merely the topic it names.",
  "communicative_functions": ["do a definable job for the essay", "advance the controlling idea", "organize sentences under one local movement", "connect to neighboring paragraphs", "serve the reader's next need"],
  "possible_communicative_functions": ["introduce a point", "develop a claim", "supply context", "present evidence", "interpret evidence", "explain a process", "define a concept", "distinguish ideas", "compare or contrast", "complicate a prior claim", "acknowledge another perspective", "respond to an objection", "develop an example", "narrate an event", "reflect on an experience", "establish consequences", "connect sections", "synthesize prior material", "prepare the next movement"],
  "engine_note_on_functions": "This is not a checklist or fixed taxonomy. A paragraph may perform one function or several coordinated functions. Do not require any particular function.",
  "reader_needs": ["knowing what this paragraph is doing for the argument or essay", "seeing how the paragraph connects to the one before it", "understanding why this paragraph appears here", "being able to follow one local movement without confusion", "knowing which idea governs the sentences", "seeing the paragraph's contribution to the whole"],
  "reader_needs_note": "Interpretive possibilities, not mandatory requirements.",
  "canonical_writing_resources": ["topic sentence", "governing idea", "transition or bridge", "point-development", "example", "evidence", "interpretation or warrant", "definition", "distinction", "comparison", "concession", "rebuttal", "consequence", "synthesis", "forecasting sentence", "inductive build to a point", "narrative sequence", "descriptive detail in service of a point"],
  "resources_note": "Introduce a resource only when it serves the paragraph's function, the genre, and the reader. No single paragraph structure is required.",
  "observable_organizations": [
    {"code": "A", "name": "Topic without purpose", "description": "Names a subject for the paragraph but does no definable work for the essay.", "example": "There are many things about pollution."},
    {"code": "B", "name": "Clear purpose, disconnected from whole", "description": "The paragraph does a clear local job but its relation to the thesis/essay is not visible."},
    {"code": "C", "name": "Competing purposes", "description": "Several distinct jobs coexist in one paragraph without a governing movement."},
    {"code": "D", "name": "Purpose shift midway", "description": "The paragraph begins doing one job and silently switches to another."},
    {"code": "E", "name": "Clear function, no explicit topic sentence", "description": "The paragraph clearly does a job though no single sentence announces it (may be inductive/narrative)."},
    {"code": "F", "name": "Topic sentence that does not govern", "description": "A formulaic opening sentence is present but the rest of the paragraph does not follow from it."},
    {"code": "G", "name": "Evidence without interpretation", "description": "Facts/quotations are supplied but their meaning for the claim is not made."},
    {"code": "H", "name": "Interpretation without sufficient evidence", "description": "Claims about meaning are asserted without grounding."},
    {"code": "I", "name": "Necessary context", "description": "The paragraph orients the reader with background the essay genuinely needs."},
    {"code": "J", "name": "Overloaded with unnecessary background", "description": "Background exceeds what the reader needs and delays the essay's movement."},
    {"code": "K", "name": "Develops the central claim", "description": "The paragraph advances or extends the thesis with new work."},
    {"code": "L", "name": "Repeats the thesis without developing", "description": "Restates the controlling idea but adds no development."},
    {"code": "M", "name": "Complicates or qualifies the thesis", "description": "Introduces tension, limitation, or nuance to the claim."},
    {"code": "N", "name": "Acknowledges another perspective", "description": "Represents a view other than the writer's."},
    {"code": "O", "name": "Responds to an objection", "description": "Answers a counter-position or anticipated challenge."},
    {"code": "P", "name": "Transitional / bridge", "description": "Chiefly connects sections or movements rather than developing content."},
    {"code": "Q", "name": "Narrative paragraph", "description": "Organized as an event sequence; should not be forced into claim-evidence-analysis."},
    {"code": "R", "name": "Reflective paragraph around uncertainty", "description": "Organized by a question or unresolved thinking rather than a settled point."},
    {"code": "S", "name": "Descriptive serving analysis", "description": "Description whose purpose is to enable a larger analytical point."},
    {"code": "T", "name": "Dependent on neighbor", "description": "Only coheres when read with the preceding or following paragraph (part of a multi-paragraph movement)."},
    {"code": "U", "name": "Integrated multi-function movement", "description": "Coordinates several functions (e.g., concede -> rebut -> extend) into one coherent movement."},
    {"code": "V", "name": "Mismatch with assignment", "description": "A competent paragraph whose apparent weakness is that it does not serve what was assigned."}
  ],
  "observable_organizations_note": "Descriptive organizations, not stages and not exhaustive. Multiple readings may fit; look for evidence before deciding.",
  "possible_differentiations": ["paragraph topic from paragraph purpose", "paragraph purpose from paragraph function", "paragraph content from paragraph structure", "the paragraph's local job from its relation to the whole", "evidence from interpretation of evidence", "necessary context from delaying background", "development of a claim from repetition of a claim", "a governing idea from a decorative opening sentence", "one integrated movement from several competing jobs", "a deliberately inductive build from an ungoverned paragraph"],
  "possible_integrations": ["paragraph purpose with the central claim", "evidence with its interpretation", "concession with rebuttal", "context with the point it enables", "description with the analysis it serves", "the paragraph with the preceding paragraph's movement", "the paragraph with the following paragraph it sets up", "several sentences under one governing idea", "several functions into one coherent movement"],
  "possible_coordinations": ["the assignment and what the paragraph is doing", "the thesis and each paragraph's job", "the paragraph and its neighbors", "evidence and reasoning within the paragraph", "audience needs and the paragraph's orientation", "the paragraph's function and the essay's overall organization", "local movement and global progression", "genre expectations and paragraph form"],
  "common_productive_tensions": ["A topic is named but the paragraph does no definable work.", "The paragraph does a clear job but its link to the thesis is invisible.", "Several purposes compete and none governs the paragraph.", "The paragraph shifts purpose midway without signaling it.", "A function is clearly performed but no sentence states it, and it is unclear whether that is purposeful.", "A topic sentence is present but does not govern the paragraph.", "Evidence is present but its meaning for the claim is not made.", "Interpretation is asserted without enough evidence.", "Context is useful but exceeds what the reader needs.", "The paragraph restates the thesis without developing it.", "The paragraph complicates the claim, but the relation to the main argument is unclear.", "A counter-perspective is raised but not yet answered or positioned.", "A transitional paragraph connects but its own contribution is thin.", "A narrative paragraph is being pushed toward argument it need not make.", "The paragraph only coheres with a neighbor, and that dependence is not yet coordinated.", "The paragraph is competent but does not serve the assignment.", "Multiple functions are present and it is unclear whether they are integrated or overloaded."],
  "tensions_note": "Identify only ONE primary tension at a time.",
  "alternative_interpretations": [
    {"observation": "no explicit topic sentence", "possible_meanings": ["the paragraph is poorly governed", "it is deliberately inductive", "it is narratively organized", "it depends on the preceding paragraph", "it is part of a larger multi-paragraph movement", "it is incomplete", "it is appropriate for the genre"]},
    {"observation": "multiple functions in one paragraph", "possible_meanings": ["meaningfully integrated", "overloaded", "transitional", "performing a complex argumentative movement", "insufficiently differentiated"]},
    {"observation": "a paragraph disconnected from the thesis", "possible_meanings": ["it sets up a later paragraph", "it supplies needed context", "it has drifted from the argument", "the essay's thesis has shifted", "only part of the draft was submitted"]},
    {"observation": "evidence with little interpretation", "possible_meanings": ["interpretation is coming in the next paragraph", "the writer assumes the meaning is obvious", "the writer has not yet interpreted", "the genre foregrounds evidence first"]}
  ],
  "alternative_interpretations_note": "Do not assume one interpretation without evidence; preserve plausible alternatives.",
  "common_misunderstandings": ["Every paragraph must begin with a topic sentence.", "The topic sentence must always be the first sentence.", "Every paragraph must follow claim-evidence-analysis.", "A paragraph can perform only one function.", "Paragraph purpose is the same as paragraph topic.", "A paragraph can be evaluated in isolation from its neighbors.", "Longer paragraphs are automatically more developed.", "A narrative or reflective paragraph is deficient if it lacks a claim.", "Restating the thesis counts as developing it.", "A transition sentence at the end is enough to connect paragraphs.", "More background is always more helpful to the reader."],
  "misunderstandings_note": "Be alert to these but do not automatically assume them.",
  "possible_developmental_movements": ["from naming a topic to performing a definable function", "from an isolated paragraph to one coordinated with the whole essay", "from competing purposes to one governing movement", "from a purpose shift to a deliberate, signaled progression", "from evidence alone to evidence plus interpretation", "from asserted interpretation to grounded interpretation", "from repeating the thesis to developing it", "from an ungoverned paragraph to a clearly governed one (topic sentence OR coherent inductive build)", "from raising a counter-view to positioning or answering it", "from a paragraph read in isolation to one coordinated with its neighbors", "from content-focus to function-awareness (what the paragraph is doing)", "from a genre-mismatched form to a form that fits the paragraph's job"],
  "movements_note": "Possible reorganizations, not a required progression.",
  "candidate_developmental_invitations": ["state, in a few words, the one job this paragraph is doing for the essay", "distinguish what this paragraph is about (topic) from what it is trying to do (purpose)", "explain how this paragraph connects to the paragraph before it", "identify which sentence, if any, governs the paragraph", "decide which of the competing jobs should govern the paragraph", "point to where the paragraph shifts purpose and decide whether to split it", "explain what a specific piece of evidence shows about your claim", "identify what evidence would ground the interpretation you are making", "decide how much of this background the reader actually needs", "explain how this paragraph develops the thesis rather than repeating it", "position the perspective you raised: do you concede, answer, or extend it?", "explain what this paragraph sets up in the paragraph that follows", "test whether this paragraph still makes sense if the neighboring paragraph were removed", "explain what changed about the paragraph's job after your revision"],
  "invitations_note": "Invitations should require the student to think, explain, choose, or revise. Present only one at a time.",
  "invitation_construction_rules": {
    "three_parts": ["Brief recognition of an observable feature in the student's paragraph", "Connection to the current communicative purpose or the whole essay", "One intellectual or writing action for the student to perform"],
    "example_form": "This paragraph gives the reader several facts about the recycling center. To help the reader see why they are here, try saying in a phrase what job this paragraph is doing for your argument.",
    "cautions": ["Do not use the example as a fixed verbal template.", "Do not rewrite the paragraph for the student."]
  },
  "relationships_to_other_domains": ["Whole Essay Purpose", "Central Claim / Thesis", "Organization", "Evidence", "Interpretation / Reasoning", "Transitions", "Opening / Introduction", "Revision and Reflective Control"],
  "relationship_notes": {
    "Whole Essay Purpose": "A paragraph's job is defined by what the whole essay is trying to do.",
    "Central Claim / Thesis": "Most body paragraphs should be answerable to the controlling idea.",
    "Organization": "Paragraph purpose is realized through where the paragraph sits in the essay's movement.",
    "Evidence": "A paragraph that presents evidence coordinates with how that evidence supports the claim.",
    "Interpretation / Reasoning": "Interpreting evidence is often the work a paragraph must do.",
    "Transitions": "Connections between paragraphs make a paragraph's relation to its neighbors explicit.",
    "Opening / Introduction": "An introductory paragraph may perform one or several coordinated opening functions.",
    "Revision and Reflective Control": "Explaining why a paragraph's job changed is evidence of intentional control."
  },
  "genre_sensitivity": {
    "note": "Do not apply one paragraph model to all genres. Reason from the actual assignment and teacher purpose rather than infer genre solely from surface form.",
    "argumentative": "Body paragraphs typically develop, support, complicate, or defend the claim; forms vary.",
    "expository": "Paragraphs may define, explain, exemplify, or sequence information toward the organizing idea.",
    "analytical": "Paragraphs often move between evidence and interpretation to build an analysis.",
    "research": "Paragraphs may report, synthesize sources, or situate findings; some are chiefly contextual.",
    "personal": "Paragraphs may narrate, reflect, or dwell; a stated point is not required.",
    "narrative": "Paragraphs advance scene, action, or meaning; do not force claim-evidence-analysis.",
    "reflective": "Paragraphs may be organized around questions or evolving understanding.",
    "literary_analysis": "Paragraphs typically coordinate textual evidence with interpretive claims."
  },
  "inside_outside_coordination": "Begin by interpreting what the paragraph is already doing and how it sits among its neighbors. Distinguish the student's operative purpose, the assigned purpose, the teacher's pedagogical purpose, the reader's needs, the genre, and the paragraph's relation to the whole. A missing topic sentence, multiple functions, or a loose connection is not automatically a deficit — it may be inductive, narrative, transitional, part of a multi-paragraph movement, or an unfinished draft. The next invitation should help the student clarify, differentiate, or coordinate the paragraph's job — never supply the paragraph.",
  "prohibitions": ["require a topic sentence in every paragraph", "require the topic sentence to be the first sentence", "require claim-evidence-analysis in every genre or every paragraph", "assume a paragraph can perform only one function", "treat paragraph purpose as identical to paragraph topic", "evaluate a paragraph in isolation from its neighbors and the whole", "force a narrative or reflective paragraph into an argumentative structure", "write or rewrite the student's paragraph", "provide a polished model paragraph for the student to copy", "list every weakness of the paragraph", "classify the student into a stage, level, or ability", "infer a stable writing ability from one paragraph", "treat the domain as a grading rubric or checklist"]
}

for i, d in enumerate(m["domains"]):
    if d["domain_name"] == "Paragraph Purpose":
        m["domains"][i] = record
        break

json.dump(m, open(PATH, "w"), indent=2)
print("replaced Paragraph Purpose; domains:", len(m["domains"]), "record keys:", len(record))
