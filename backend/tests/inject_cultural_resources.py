import json

PATH = "/app/backend/canonical_writing_model.json"
m = json.load(open(PATH))
by = {d["domain_name"]: d for d in m["domains"]}


def cr(name, purpose, fdef, mis, approp, inapprop, conn, friendly):
    return {
        "name": name,
        "purpose": purpose,
        "functional_definition": fdef,
        "typical_misunderstandings": mis,
        "appropriate_uses": approp,
        "inappropriate_uses": inapprop,
        "developmental_connections": conn,
        "student_friendly_explanation": friendly,
        "explanation_note": "This is a seed. Adapt the wording to the student's current organization, the assignment, the genre, and what the student has already shown they understand. Do not simply recite it.",
    }


by["Opening / Introduction"]["cultural_resources"] = [
    cr("Hook",
       "Solves the problem of a reader who has no reason yet to care or keep reading.",
       "A hook is not just a dramatic or surprising sentence. It is an opening move that engages the reader while preparing them for the essay's real concern.",
       ["Every introduction must begin with a hook.", "Any shocking or clever sentence is a good hook.", "A hook can be unrelated to the essay as long as it grabs attention."],
       ["When the reader needs a reason to enter the topic.", "When engagement and orientation can be combined.", "When the genre rewards drawing the reader in (argument, feature, personal)."],
       ["When a knowledgeable audience needs orientation more than enticement.", "When a dramatic opener would distort or misrepresent the essay.", "When the genre expects a direct, sober opening (some research/technical writing)."],
       {"purpose": "engages the reader in service of the essay's purpose", "audience": "shaped by what will actually interest this reader", "organization": "leads into context and the eventual claim", "neighboring_concepts": "Context, Significance, Thesis"},
       "A hook is a way of opening so your reader leans in — not a trick, but a door into what your essay is really about."),
    cr("Significance",
       "Solves the problem of a reader who understands the topic but not why it matters.",
       "Significance is the move that shows what is at stake — why this topic deserves the reader's attention now.",
       ["Saying a topic is 'important' establishes significance.", "Significance is the same as background."],
       ["When the reader may see the topic as obvious or trivial.", "When stakes motivate the argument to come."],
       ["When stakes are already obvious to this audience.", "When asserting importance would substitute for grounding it."],
       {"purpose": "connects the topic to why it matters", "audience": "what this reader would find at stake", "neighboring_concepts": "Problem framing, Thesis"},
       "Significance is where you show your reader why this is worth their time — not by saying 'this is important' but by making the stakes visible."),
]

by["Central Claim / Thesis"]["cultural_resources"] = [
    cr("Thesis",
       "Solves the problem of an essay whose parts do not add up to one governing idea.",
       "A thesis is not merely an opinion. It is the controlling idea that gives an essay direction and holds its parts accountable to one purpose.",
       ["A thesis must be one sentence at the end of the first paragraph.", "A thesis must follow 'X because A, B, and C.'", "A fact can be a thesis.", "Every genre needs an explicit thesis."],
       ["When the essay needs a controlling idea to organize its parts.", "When the reader must know what the essay will establish."],
       ["When the genre organizes by question, narrative, or reflection instead.", "When forcing an early explicit claim would flatten purposeful inquiry."],
       {"purpose": "the idea through which the whole purpose is realized", "organization": "sets expectations for the essay's movement", "evidence": "defines what counts as support", "neighboring_concepts": "Claim, Opening, Paragraph Purpose"},
       "A thesis is the one idea your whole essay is trying to get a reader to accept, understand, or see differently — the spine everything else hangs on."),
    cr("Claim",
       "Solves the problem of writing that reports or opines without asserting anything a reader could reasonably dispute.",
       "A claim is a statement you take a position on and could defend — not a fact and not a bare preference.",
       ["An opinion is automatically a claim.", "A true statement is a strong claim."],
       ["When the assignment asks you to argue or interpret.", "When you want the reader to accept something contestable."],
       ["When the task is purely to explain or narrate.", "When the 'claim' is really just a topic."],
       {"purpose": "makes the essay's position arguable", "evidence": "a claim tells you what to support", "neighboring_concepts": "Thesis, Evidence, Interpretation"},
       "A claim is something a thoughtful person could disagree with — that's what makes it worth arguing and gives your evidence a job."),
]

by["Paragraph Purpose"]["cultural_resources"] = [
    cr("Topic Sentence",
       "Solves the problem of a paragraph whose sentences do not obviously belong together or serve the essay.",
       "A topic sentence names the job a paragraph is doing so the reader can follow one local movement. It need not be the first sentence, and some paragraphs (inductive, narrative) govern themselves differently.",
       ["Every paragraph must open with a topic sentence.", "The topic sentence must be the first sentence.", "A topic sentence is the paragraph's topic."],
       ["When a paragraph's job would otherwise be unclear.", "When the reader needs a signpost for the local movement."],
       ["When the paragraph is deliberately inductive or narrative.", "When a stated sentence would spoil a built effect.", "When it merely names a topic instead of a purpose."],
       {"purpose": "makes the paragraph's job explicit", "organization": "helps the reader track progression", "neighboring_concepts": "Paragraph Purpose, Transition, Thesis"},
       "A topic sentence is a quick signpost telling your reader what this paragraph is doing — it can go anywhere, and some paragraphs earn their point instead of announcing it."),
    cr("Transition",
       "Solves the problem of paragraphs that sit next to each other without a visible relationship.",
       "A transition makes the relationship between ideas explicit — it signals a conceptual move (contrast, cause, extension), not just a verbal connector.",
       ["A transition is just a word like 'however' or 'furthermore.'", "Transitions only go at the start of paragraphs."],
       ["When the logical relationship between parts is not obvious.", "When a section shifts and the reader needs to know why."],
       ["When the connection is already clear.", "When a connective word is used to fake a link that isn't there."],
       {"purpose": "keeps the essay's movement coherent", "organization": "expresses how parts relate", "neighboring_concepts": "Paragraph Purpose, Organization"},
       "A transition is where you tell your reader how one idea relates to the next — a real bridge in meaning, not just a word like 'however.'"),
]

json.dump(m, open(PATH, "w"), indent=2)
for n in ("Opening / Introduction", "Central Claim / Thesis", "Paragraph Purpose"):
    print(n, "-> cultural_resources:", [c["name"] for c in by[n]["cultural_resources"]])
