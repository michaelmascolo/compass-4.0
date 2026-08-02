import json

PATH = "/app/backend/canonical_writing_model.json"
m = json.load(open(PATH))

record = {
  "domain_name": "Central Claim / Thesis",
  "domain_status": {
    "description": "Culturally available functions and resources for giving an essay a controlling idea.",
    "is_not": ["a rigid one-sentence template", "a developmental stage", "a required sequence", "a rule that a thesis must appear in the final sentence of the introduction", "a rule that every genre needs an explicit thesis", "a grading checklist"],
    "must_be_interpreted_relative_to": ["the assignment", "the writer's operative purpose", "the teacher's pedagogical purpose", "the intended audience", "the genre", "the evidence available", "the argument the body actually makes", "the organization of the developing whole essay"]
  },
  "governing_communicative_function": "Give the essay a controlling idea that organizes its parts and communicates to the reader what the whole essay is trying to establish, interpret, or explore. What counts as a claim, how explicit it must be, and where it appears depend on the essay's purpose and genre.",
  "communicative_functions": ["organize the essay", "communicate the controlling idea", "establish direction", "make a position or interpretation arguable", "coordinate parts toward one end"],
  "possible_communicative_functions": ["state a position", "offer an interpretation", "answer a question the essay poses", "frame an inquiry or line of exploration", "make a claim arguable rather than merely factual", "establish the scope of what is claimed", "signal the essay's direction and structure", "distinguish the writer's claim from common opinion", "commit to something a reader could dispute", "hold body paragraphs accountable to one idea", "qualify or bound a claim", "synthesize several observations into one governing idea"],
  "engine_note_on_functions": "Not every genre requires an explicit, early, single-sentence thesis. A claim may be stated, implied, distributed, delayed, or exploratory.",
  "reader_needs": ["knowing what the essay is trying to establish", "being able to tell the claim apart from the topic", "understanding what is being asserted, interpreted, or asked", "knowing what would count as support", "being able to predict the essay's direction", "understanding the scope and limits of the claim", "seeing why the claim is worth making (arguable, not obvious)"],
  "reader_needs_note": "Interpretive possibilities, not mandatory requirements.",
  "canonical_writing_resources": ["claim", "position", "interpretation", "organizing statement", "thesis statement", "controlling idea", "governing question", "hypothesis", "qualification or scope", "claim plus reasoning (because-structure)", "enumerated preview", "counter-claim or concession"],
  "resources_note": "Introduce a resource only when it serves the writer's operative purpose and the essay's genre. No single thesis form is required.",
  "observable_organizations": [
    {"code": "A", "name": "Topic without claim", "description": "Names a subject but asserts nothing arguable.", "example": "This essay is about social media."},
    {"code": "B", "name": "Opinion without reasoning", "description": "States a like/dislike or 'should' with no grounds.", "example": "Homework is bad."},
    {"code": "C", "name": "Factual statement as thesis", "description": "An accurate but non-arguable fact stands in for a claim.", "example": "The Amazon is the largest rainforest."},
    {"code": "D", "name": "Overly broad claim", "description": "A claim so large the essay cannot support it.", "example": "Technology has changed everything about society."},
    {"code": "E", "name": "Vague claim", "description": "A claim whose key terms are undefined or fuzzy.", "example": "Social media has a big impact on people."},
    {"code": "F", "name": "Multiple competing claims", "description": "Several candidate claims coexist without one governing them."},
    {"code": "G", "name": "Clear but unsupported claim", "description": "A sharp, arguable claim with no visible support yet."},
    {"code": "H", "name": "Implicit claim", "description": "The claim is inferable from the writing but never stated."},
    {"code": "I", "name": "Delayed claim", "description": "The claim is purposefully withheld until later."},
    {"code": "J", "name": "Distributed claim", "description": "The claim is spread across several sentences or parts rather than one statement."},
    {"code": "K", "name": "Exploratory thesis", "description": "The essay frames an inquiry or question it will investigate rather than assert."},
    {"code": "L", "name": "Interpretive thesis", "description": "Asserts a reading or meaning of an object (text, event, data)."},
    {"code": "M", "name": "Argumentative thesis", "description": "Takes a disputable position and commits to defending it."},
    {"code": "N", "name": "Analytical thesis", "description": "Claims how or why something works, or what it reveals."},
    {"code": "O", "name": "Research question in place of a thesis", "description": "Organized by a question the essay answers."},
    {"code": "P", "name": "Formulaic three-part thesis", "description": "'X because A, B, and C' template; the parts may not cohere."},
    {"code": "Q", "name": "Integrated / coordinated claim", "description": "A claim that governs the body and is answerable to it."},
    {"code": "R", "name": "Claim mismatched to assignment", "description": "A real claim that does not address what was assigned."},
    {"code": "S", "name": "Claim mismatched to body", "description": "The stated claim and what the essay actually argues diverge."}
  ],
  "observable_organizations_note": "Descriptive organizations, not stages and not exhaustive. Personal, narrative, and reflective essays may legitimately have no explicit thesis.",
  "possible_differentiations": ["topic from claim", "fact from arguable claim", "opinion from reasoned position", "claim from evidence", "claim from the reasons it matters", "broad claim from a claim scoped to what the essay can support", "vague terms from precise terms", "the writer's claim from common opinion", "a question from a claim", "the assigned purpose from the writer's operative claim", "the stated claim from the claim the body actually supports", "a claim from a mere announcement of intent ('I will discuss...')"],
  "possible_integrations": ["claim with the essay's purpose", "claim with the body paragraphs that support it", "claim with evidence and reasoning", "claim with a counter-claim or concession", "several observations into one governing claim", "claim with the opening that prepares it", "claim scope with what the essay can actually deliver", "question with the eventual answer or claim"],
  "possible_coordinations": ["the assignment and the writer's operative claim", "the claim and its location/explicitness for the genre", "the claim and each paragraph's purpose", "the claim and the evidence available", "the stated claim and the argument the body makes", "claim and counterargument", "breadth of claim and length/scope of essay", "claim and the opening's framing"],
  "common_productive_tensions": ["A topic is present but no arguable claim organizes it.", "An opinion is stated but the reasoning that makes it a claim is missing.", "A true statement stands in for a claim, so nothing is at stake.", "The claim is arguable but too broad for the essay to support.", "The claim's key terms are vague, so the reader cannot tell what is asserted.", "Several candidate claims compete and none yet governs.", "A sharp claim is stated but not yet supported.", "A claim is implied throughout but never made explicit where the genre expects it.", "The claim is delayed, and it is unclear whether the delay is purposeful.", "The claim is distributed across sentences and has not been consolidated.", "The essay poses a question but does not yet commit to an answer.", "A three-part thesis lists reasons that do not actually cohere.", "The stated claim does not match what the body argues.", "The claim does not address the assignment.", "The claim is strong but the essay's scope cannot deliver it.", "The writer's operative claim differs from the assigned purpose."],
  "tensions_note": "Identify only ONE primary tension at a time.",
  "alternative_interpretations": [
    {"observation": "no explicit thesis", "possible_meanings": ["the claim is implicit and clear", "the claim is purposefully delayed", "the genre (personal/narrative/reflective) does not require one", "the writer has not yet formed a claim", "the passage is an unfinished draft", "the essay is exploratory and organized by a question"]},
    {"observation": "a broad claim", "possible_meanings": ["the writer has not scoped the claim", "the breadth is a deliberate framing to be narrowed", "the essay will progressively focus", "the writer misread the assignment's scope", "only part of the essay was submitted"]},
    {"observation": "a question instead of a statement", "possible_meanings": ["an exploratory, inquiry-driven thesis", "the writer is still discovering the claim", "the genre invites a guiding question", "the writer is avoiding commitment", "a rhetorical question not meant to organize"]},
    {"observation": "claim differs from the body", "possible_meanings": ["the thesis was written first and the thinking moved on", "the body drifted", "the writer holds two claims", "the claim needs revision to match the discovered argument"]}
  ],
  "alternative_interpretations_note": "Do not collapse uncertainty into a single confident diagnosis.",
  "common_misunderstandings": ["Every essay must have one explicit thesis sentence.", "The thesis must be the last sentence of the introduction.", "A thesis must always be a single sentence.", "A thesis must always take the form 'X because A, B, and C.'", "A statement of fact can serve as a thesis.", "Announcing the topic ('This essay will discuss...') is a thesis.", "A strong thesis must be broad enough to cover everything.", "A question can never function as a thesis.", "The thesis is decided once and cannot change during drafting.", "A thesis is judged by its shape rather than by how it organizes the essay.", "Personal and narrative essays must state an explicit thesis."],
  "misunderstandings_note": "Be alert to these but do not automatically assume them.",
  "possible_developmental_movements": ["from naming a topic to asserting an arguable claim", "from an opinion to a reasoned position", "from a factual statement to a claim with something at stake", "from a broad claim to one scoped to the essay", "from vague terms to precise terms", "from several competing claims to one governing claim", "from an implicit claim to an explicit one where the genre calls for it", "from a distributed claim to a consolidated one", "from a question to a committed answer, or to a purposefully sustained inquiry", "from a template thesis to a claim whose parts cohere", "from a claim mismatched to the body to alignment between claim and argument", "from a claim decided in advance to a claim revised in light of the writing"],
  "movements_note": "Possible reorganizations, not a required progression.",
  "candidate_developmental_invitations": ["state, in one sentence, the single idea the whole essay is trying to establish", "identify what in the current sentence a reader could actually disagree with", "distinguish the topic from the claim about the topic", "name what would count as evidence for the claim", "scope the claim to what this essay can actually support", "define the key term so the reader knows what is being asserted", "decide which of the competing claims should govern the others", "explain the reasoning that turns this opinion into a defensible position", "test whether each body paragraph advances the stated claim", "decide whether the essay answers its question or sustains it as inquiry", "check whether the stated claim matches what the body actually argues", "explain what changed about the claim after revision and why", "identify whether the claim addresses the assignment", "consider whether an implicit claim should be made explicit for this reader and genre"],
  "invitations_note": "Invitations should require the student to think, explain, choose, or revise. Present only one at a time.",
  "invitation_construction_rules": {
    "three_parts": ["Brief recognition of an observable feature in the student's participation", "Connection to the current communicative purpose", "One intellectual or writing action for the student to perform"],
    "example_form": "You've told the reader what your essay is about, but not yet what you claim about it. To give the essay something to defend, try stating in one sentence what you want the reader to accept by the end.",
    "cautions": ["Do not use the example as a fixed verbal template.", "Do not write or rewrite the student's thesis for them."]
  },
  "relationships_to_other_domains": ["Whole Essay Purpose", "Opening / Introduction", "Paragraph Purpose", "Evidence", "Interpretation / Reasoning", "Organization", "Conclusion", "Revision and Reflective Control"],
  "relationship_notes": {
    "Whole Essay Purpose": "The claim is the controlling idea through which the whole purpose is realized.",
    "Opening / Introduction": "The opening may state, prepare, complicate, or deliberately delay the claim.",
    "Paragraph Purpose": "Each paragraph should be answerable to the claim.",
    "Evidence": "A claim defines what would count as support.",
    "Interpretation / Reasoning": "Reasoning connects evidence to the claim and makes it defensible.",
    "Organization": "The claim sets expectations for how the essay proceeds.",
    "Conclusion": "The conclusion may return to, extend, or qualify the claim.",
    "Revision and Reflective Control": "Explaining why a claim changed is evidence of intentional control."
  },
  "genre_sensitivity": {
    "note": "Do not apply one thesis model to all genres. Reason from the actual assignment and teacher purpose rather than infer genre solely from surface form.",
    "argumentative": "Usually commits to a disputable position the essay defends; may state it early or build to it.",
    "expository": "May use an organizing or controlling idea, or a thesis of scope, rather than a contested claim.",
    "analytical": "Asserts how or why something works, or what an object means; interpretive rather than merely factual.",
    "research": "May be a guiding claim OR a research question/hypothesis the study investigates.",
    "personal": "May have no explicit thesis; a controlling insight or tension may organize instead.",
    "narrative": "Typically organized by event and meaning, not an explicit thesis; do not force one.",
    "reflective": "May be organized by a question, uncertainty, or evolving understanding rather than a fixed claim.",
    "literary_analysis": "Advances an interpretive claim about the text, supported by textual evidence."
  },
  "inside_outside_coordination": "Begin by interpreting the claim organization already present. Distinguish the student's operative claim, the assigned purpose, the teacher's pedagogical purpose, the reader's needs, and the genre's conventions for claims. A missing or unconventional thesis is not automatically a deficit — it may reflect a genre that does not require one, a purposeful delay, an exploratory design, an unfinished draft, or a mismatch between the assignment and the writer's intention. The next invitation should help the student differentiate, scope, consolidate, make explicit, or align the claim — never supply the claim itself.",
  "prohibitions": ["require an explicit one-sentence thesis in every genre", "require the thesis in the final sentence of the introduction", "require the 'X because A, B, and C' form", "treat a factual statement as automatically acceptable or unacceptable without reference to purpose", "reject a question-driven or exploratory thesis merely because it is not a statement", "force a personal or narrative essay to state an argumentative thesis", "evaluate the claim in isolation from purpose, audience, genre, evidence, and the body", "write or rewrite the student's thesis", "provide a polished model thesis for the student to copy", "list every weakness of the claim", "classify the student into a stage, level, or ability", "infer a stable writing ability from one thesis", "treat the domain as a grading rubric or checklist"]
}

for i, d in enumerate(m["domains"]):
    if d["domain_name"] == "Central Claim / Thesis":
        m["domains"][i] = record
        break

json.dump(m, open(PATH, "w"), indent=2)
print("replaced Central Claim / Thesis; total domains:", len(m["domains"]))
print("record keys:", len(record))
