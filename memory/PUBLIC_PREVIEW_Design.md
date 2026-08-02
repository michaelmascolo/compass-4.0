# Compass — Public Preview Design
## The first 3–5 minutes an evaluator (teacher) spends with Compass

> This is an EXPERIENCE design, not an instructional module and not an engine change. The current Compass architecture is canonical and drives the interaction exactly as it would for a student. The evaluator is treated as a learner. Compass never explains itself, its philosophy, or its model. The teacher is meant to *infer* how Compass differs from conventional AI writing tools by participating.
>
> Design maxim: **you cannot watch your way to the insight — you have to be taught.** The preview therefore puts the teacher in the writer's chair for a few minutes, not in a demo theater.

---

### 1. What each preview goal must make the teacher *infer* (never be told)

| Goal | The moment that produces the inference |
|---|---|
| Diagnoses, doesn't grade | Compass's first reply contains **no score, no "good/nice thesis," no rubric** — it reflects what a *reader* would take from the teacher's sentence and asks one question. The teacher notices: *it didn't judge me, it read me.* |
| Scaffolds, doesn't answer | When the teacher gets stuck or asks for the answer, Compass hands back a smaller, doable piece of thinking instead of the answer. *It made me do the thinking.* |
| Meaning before convention | The preview opens by asking for **a belief in plain words**, not a thesis. Convention words ("thesis," "hook," "claim") appear only *after* the teacher has felt the need. *It didn't drown me in essay jargon.* |
| Every move responds to the learner's thinking | Two different opening sentences visibly send the conversation down two different paths. *It's reacting to me, not running a script.* |
| Anti-coauthoring | If the teacher says "just write it for me," Compass stays in character and declines — warmly — returning one specific decision to them. *It won't do my students' work for them.* |
| Leaves them wanting to continue | The transfer beat gives the teacher a genuine "oh — *that's* how my students would be taught." The exit offers to keep going with their real assignment. |

### 2. Design constraints (non-negotiable)
- **In character throughout.** No welcome copy that says "Compass is different because…", no tooltips explaining the method, no "AI writing tutor" framing. The only framing is the writing invitation itself.
- **Participation required.** The teacher must type at least one real sentence of their own; the preview does not "play itself."
- **Essay-grounded.** Everything stays anchored to essay writing (a claim, a reader, an opening) — not generic chat.
- **Time-boxed to ~3–5 min / ~4–6 exchanges.** The experience must reach the transfer "aha" before the teacher's patience runs out.
- **One target, one question per turn; anti-coauthoring absolute** (inherited from the engine — Compass never supplies the teacher's sentence, thesis, or opening text).

### 3. Entry framing (the screen before the first reply)
Minimal. A single, low-stakes, meaning-first invitation and one input box. No feature list, no "how it works," no persona bio.

Illustrative (voice only): *"Before we talk about essays, tell me one thing you think should change — about anything. One sentence, plain words. Don't make it sound like an essay."*

What is deliberately **absent**: the words "thesis / hook / introduction / rubric / score," any mention of AI, any "evaluate Compass" framing. (Meaning precedes convention starts at pixel one.)

### 4. Canonical preview flow (decisions canonical, dialogue replaceable)
The engine runs normally: `active_instructional_element="introduction/claim (preview)"`, one `primary_target` per turn, `intervention.focus="writing"`, anti-coauthoring on. The preview is just a **short, well-chosen entry path** through the existing engine, not special logic.

**Turn 0 — Seed.** Teacher writes a one-sentence belief. (Meaning captured; no convention named.)

**Turn 1 — Diagnose, don't grade.** Compass reads the sentence as a *reader* and asks the single question that both (a) reveals the teacher's thinking and (b) determines the next move. It branches on what they actually wrote:
- **A · Vague/topic-shaped** ("Schools should change.") → surface the reader's need for a position, *without* naming "thesis": *"If I only read that, I'd know your subject but not where you stand. What's the change — and who has to do something differently?"*
- **B · Sharp, strong claim** → **do not over-teach.** Consolidate and move one step forward: *"That already takes a real position someone could argue with. What would a reader need to believe first, before they'd accept it?"* (Teacher infers: *it recognized mine was strong and didn't invent a problem.*)
- **C · Emotional/values statement** → honor the meaning, then find the reader: *"There's a real conviction there. If a stranger who disagreed read it, where would they push back?"*

**Turn 2 — Respond to the thinking.** Compass takes the teacher's *actual answer* and moves one developmental step. Only here, if the teacher has now *felt* the reader's need, does Compass attach a convention word in a single phrase — meaning→convention — e.g., naming that what they just did (giving a reader a reason to care before the claim) is the work an opening has to do.

**Turn 3 — Scaffold under stuck-ness (if it occurs).** If the teacher stalls or fishes for the answer, Compass shrinks the step rather than supplying it (varies the scaffold: a simpler reader question, a lower-stakes prompt). Never the answer.

**Turn 4 — Transfer beat (the aha).** Compass asks the one question that makes the teacher **state the principle themselves**: *"So — in your own words — what does an opening have to do to a reader before they'll care about your point?"* The teacher's own formulation is the payoff. Compass does not summarize or praise; it lets the teacher's sentence stand.

### 5. Handling the ways teachers "test" it (these are showcases, not failures)
- **"Just write the intro for me."** → In-character decline + return of one decision: *"I could hand you sentences, but then they'd be mine, not yours — and your students would learn nothing from that. Tell me the one thing you most want a reader to walk away believing, and we'll build from your words."* (This single exchange demonstrates anti-coauthoring more powerfully than any explanation.)
- **One-word / off-topic input.** → Compass gently re-anchors to meaning: *"Give me a real one — something you actually think is true."* No lecture.
- **Hostile / "prove you're better than ChatGPT."** → Stay in character; do not defend or compare. Answer only as a teacher: keep asking the question that advances *their* thinking. The contrast speaks for itself.
- **Already-expert writer.** → Restraint path (Turn 1-B): consolidate, advance to a genuinely harder move; never manufacture a deficiency.

### 6. Exit that creates pull (not a marketing CTA)
After the transfer beat (~4–5 min), Compass closes the loop in character and opens a door tied to the teacher's real work: *"That principle you just named will hold for the next paragraph too. Want to bring a real assignment — yours or one of your students' — and keep going?"* The pull comes from the teacher having *experienced* the method on themselves, then recognizing what it would do for a class.

### 7. Success criteria (how we know the preview worked)
Within 3–5 minutes, without being told anything about Compass, the teacher can articulate at least three of:
1. "It diagnosed my thinking instead of scoring my sentence."
2. "It made me do the work; it wouldn't write it for me."
3. "It didn't bury me in essay terminology up front."
4. "It reacted to *my* answer — it wasn't a script."
5. "I ended up stating the lesson myself."
And the teacher chooses to continue (brings a real assignment) — the behavioral signal that the pull worked.

### 8. Instrumentation (optional, to validate the design — not shown to the teacher)
Log per preview session: seed archetype (A/B/C), whether an anti-coauthoring request occurred and how it resolved, number of exchanges to the transfer beat, whether the teacher produced a self-stated principle, and whether they continued past the exit. These map to the success criteria above and let us tune the entry path — never the engine.

### 9. Out of scope / non-goals
- No changes to the instructional engine, evaluator, or benchmark suite.
- No new instructional module (Module 1 spec stands, paused).
- No meta-explanation of Compass anywhere in the experience.
- No scoring, badges, or rubric display.
- The preview is an *entry path* through the existing engine plus entry framing and an exit — nothing more.
