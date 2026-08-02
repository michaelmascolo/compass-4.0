# Compass Governance v2 — Architecture Specification (DRAFT FOR REVIEW)

> Status: **DRAFT — refinements incorporated (round 2), awaiting your confirmation to lock as the authoritative contract.** Architectural level only (behavior + interfaces, no code).
> Change log: round-2 refinements applied — three-pass call granularity (§1), Assignment vs. Student purpose (S1), functional-representation output (S4), prewriting triggers only on insufficient conceptual organization not weak prose (S4/B2), target = leverage + forward progress (S5), reader-perspective explicit teaching (S7), `why_this_now` transparency field (§5), Cognitive-Substitution gating evaluator dimension (§7/§8), and the "Interpret Before Instruct" architectural principle (§0).
> Relationship to v1: Governance v2 is a **candidate successor** to Governance v1. It is implemented behind the existing `reasoning_mode` feature flag (`reasoning_mode: "governance_v2"`). The default **`exhaustive` (frozen v1) engine remains unchanged and is the safety net + baseline.** v2 is promoted to default only after it passes the 66-case Compare-Two-Runs constitutional review AND demonstrates improvement in clarity, transparency, instructional quality, and latency — not merely output matching.

---

## 0. Core thesis — what v2 changes (and what it does NOT)

**v2 changes the CONTROL ARCHITECTURE, not the instructional knowledge.**

- The frozen `SYSTEM_MESSAGE` is treated as a **reusable Instructional Knowledge Base (KB)**: developmental principles, canonical functional models (M6–M13), the IO 12-step element library, scaffolding strategies, ZPD/learner-model concepts, dialogue guidance, and constitutional rules. **It is not rewritten in this round.**
- A new **Governance v2 Orchestrator** owns the *sequence* of reasoning and *when* each governance layer is invoked. It queries the KB as needed at each stage.
- If, after validation, we find the KB *itself* needs changes, that becomes a future "true SYSTEM_MESSAGE v2." Not a goal now.

The 5-Layer Governance Architecture (L1 Constitutional, L2 Developmental Policy, L3 Diagnosis, L4 Learner Model, L5 Presentation) is preserved. v2 changes **the order in which the layers are engaged** and adds an explicit, inspectable orchestration spine.

### Central architectural principle — INTERPRET BEFORE INSTRUCT
Governance v2 intentionally **separates interpretation from instruction**. Compass must first *understand what communicative work the student's writing is currently performing* (S1–S4) before deciding *how to teach* (S5–S7). Interpretation stages never teach, model the learner, or select a target; instruction stages never re-open interpretation. This separation is the central architectural improvement over Governance v1, and it is what makes each downstream decision cheap, scoped, and inspectable.

---

## 1. Overall processing pipeline

```
                         ┌──────────────────────────────────────────────┐
   student turn ───────▶ │  GOVERNANCE V2 ORCHESTRATOR                    │
   (text + session)      │                                                │
                         │  S1 PURPOSE ───────────────┐                   │
                         │      │  (purpose unclear?) ─┴──▶ [B1 CLARIFY]   │
                         │      ▼                                          │
                         │  S2 WRITING UNIT                                │
                         │      ▼                                          │
                         │  S3 CANONICAL FUNCTIONAL MODEL  (KB lookup)     │
                         │      ▼                                          │
                         │  S4 FUNCTIONAL INTERPRETATION ─┐                │
                         │      │ (conceptual org missing?)┴─▶ [B2 PREWRITE]│
                         │      │ (off-task/incoherent?) ──────▶ [B3 FALLBACK]
                         │      ▼                                          │
                         │  S5 INSTRUCTIONAL TARGET  (exactly ONE)         │
                         │      ▼    ◀───── learner modeling BEGINS here ──│
                         │  S6 DEVELOPMENTAL STRATEGY (L4 + scaffolding)   │
                         │      ▼                                          │
                         │  S7 DIALOGUE / EXPLICIT TEACHING (L5)           │
                         │      │  Orient→Teach→Locate→Invite→Reflect      │
                         └──────┼─────────────────────────────────────────┘
                                ▼
                    one learner-facing invitation + transparency_state
```

**Ordering principles enforced by the spine:** interpret before instruct (S1–S4 before S5–S7); purpose before development (S1); writing unit before learner model (S2 before S6); interpret before teach (S4 before S7); exactly one target (S5); developmental reasoning deferred until after the target is chosen (S6); explicit, reader-centered teaching (S7); function over form (S3/S4); prewriting as a decision point (B2); transparency emitted every turn (S7).

### Call granularity (DECIDED) — three logical passes, seven conceptual stages
The seven stages are conceptual and always distinct in the reasoning ledger, but they are executed in **three batched model passes** (not one call per stage, not one monolithic call):
- **Pass 1 — Orientation & functional frame:** S1 Purpose · S2 Writing Unit · S3 Canonical Functional Model.
- **Pass 2 — Interpretation & target:** S4 Functional Interpretation · S5 Single Instructional Target.
- **Pass 3 — Strategy & teaching:** S6 Developmental Strategy · S7 Dialogue / Explicit Teaching.

Rationale: preserves the conceptual seven-stage separation (and full inspectability via the ledger) while keeping latency low. Branch checks (B1 after S1, B2/B3 after S4) are evaluated at the end of the pass that produces their trigger, and may short-circuit the remaining passes. Implementation retains flexibility *within* this batching (e.g., how much KB each pass loads), but the pass boundaries above are part of the contract.

---

## 2. The reasoning ledger (data passed between stages)

A single accumulating structure flows through the stages and is persisted per turn for inspectability and for the transparency UI. Conceptually:

```
GovernanceV2Trace {
  purpose:                { assignment_purpose, student_purpose, purpose_alignment, confidence, source, assignment_alignment }
  writing_unit:           { unit, scope, confidence, prior_unit_continuity }
  functional_model:       { functions[], reader_needs[] }
  functional_interpretation: { functional_representation, function_status[ {function, functional_reading, evidence} ], reader_gap_summary }
  target:                 { primary_target, leverage_rationale, forward_progress_rationale, target_continuity }
  developmental_strategy: { learner_state, zpd_position, scaffolding_level, support_move, consolidation/fading }
  dialogue:               { student_facing_invitation, candidate_invitations[2], teaching_content, reflection_prompt }
  transparency_state:     { where_you_are, current_unit, why_it_matters, why_this_now, todays_goal, whats_next }
  branch:                 none | purpose_unclear | prewriting | foundational_fallback
  layers_invoked:         { per-stage list of L1..L5 }
  pass_latencies_s:       { pass1, pass2, pass3 }
}
```

Each stage appends only its own outputs; downstream stages read only what they need. This ledger directly powers (a) the Compare-Two-Runs governance panel (one panel per stage + branch) and (b) the transparency UI (point #10).

---

## 3. Stage-by-stage contract

For each stage: **Responsibility · Inputs · Outputs · Does NOT do · Governance layer(s) · KB referenced.**

### S1 — PURPOSE
- **Responsibility:** Determine the communicative purpose of the writing task, distinguishing two purposes that may differ and must be detected **separately**:
  - **Assignment Purpose** — what the *teacher* is asking students to accomplish (from telos / teacher_notes / assignment).
  - **Student Purpose** — what the *student's writing suggests they believe* they are trying to accomplish (inferred from the text itself).
- **Inputs:** session telos (teacher purpose, assignment, teacher_notes), current student text, prior conversation.
- **Outputs:** `assignment_purpose`, `student_purpose`, `purpose_alignment` (aligned | partial | divergent), `confidence`, `source` (teacher | student-stated | inferred), `assignment_alignment` (on-task | drift | off-task).
- **Does NOT:** diagnose weaknesses, model the learner, select a target, or teach. (Note: a divergence between assignment and student purpose is *observed* here, not yet acted on — it becomes evidence for later stages.)
- **Layers:** L2 (purpose-first, honor teacher purpose), L1 (answer-the-assignment gate).
- **KB:** M6 communicative purpose; telos/teacher_notes.
- **Branch:** if the **student purpose** cannot be determined at all (intended meaning indeterminate) or overall `confidence` is below threshold → **B1 Purpose-Unclear**.

### S2 — WRITING UNIT
- **Responsibility:** Identify the current instructional object (prewriting, thesis, introduction, body paragraph, evidence, transition, conclusion, whole-draft, …).
- **Inputs:** purpose, student text, turn kind, prior target/unit.
- **Outputs:** `writing_unit`, `unit_scope` (local span | whole draft), `unit_confidence`, `prior_unit_continuity` (same | advanced | regressed).
- **Does NOT:** judge quality, teach, or model the learner.
- **Layers:** L2; L3 (light — object identification only).
- **KB:** IO 12-step canonical element library.

### S3 — CANONICAL FUNCTIONAL MODEL
- **Responsibility:** Load, from the KB, the canonical functional model for the identified unit — the communicative functions that unit performs for a reader, and what the reader needs from it. Function over form: multiple valid realizations.
- **Inputs:** `writing_unit`, `communicative_purpose`.
- **Outputs:** `functions[]` (ordered communicative functions of the unit), `reader_needs[]`.
- **Does NOT:** evaluate the student's text (this is a KB lookup, not a judgment).
- **Layers:** L2 (function-over-form), reader-centered framing (M12).
- **KB:** the unit's functional frameworks (M6–M13) + IO element definitions.

### S4 — FUNCTIONAL INTERPRETATION
- **Responsibility:** Produce a **functional representation** of the student's current writing — a description of *what communicative work each part is currently performing (or attempting) for a reader* — interpreted against the functional model. **Understand, not evaluate.** The emphasis is understanding communicative function, **not** assigning quality labels.
  - *Not:* "Thesis weak."
  - *Instead:* "The writer appears to be attempting to state a position, but the statement does not yet organize the essay for the reader."
- **Inputs:** `functions[]`, `reader_needs[]`, student text, purpose (assignment + student).
- **Outputs:** `functional_representation` (prose account of the writing's current communicative work), `function_status[]` (each: function, `functional_reading` = what this part is doing / attempting for the reader, evidence = span/quote), `reader_gap_summary` (what the reader still needs).
- **Does NOT:** select a target, teach, model the learner, invent deficiencies (restraint), or assign quality scores/labels.
- **Layers:** L3 (diagnosis — interpretation only), reader-centered, L1 (restraint: no invented deficiencies).
- **KB:** the unit's functional frameworks.
- **Branches:** enter **B2 Prewriting Mode** ONLY when the functional representation shows **insufficient conceptual organization** — i.e., there is not yet a developed idea/claim for the unit's functions to organize, so the functions cannot even be meaningfully attempted. **Weak prose alone does NOT trigger prewriting.** If the text is **off-task or incoherent across ideas** (inconsistent with the established purpose/unit) → **B3 Foundational Fallback**.

### S5 — INSTRUCTIONAL TARGET
- **Responsibility:** Select **exactly ONE** instructional target. Selection criterion is twofold: the issue with the **greatest developmental leverage**, *while also preserving forward progress toward completion of the assignment*. The chosen target should both matter most developmentally and keep the student moving toward finishing the task (not send them into an unbounded detour).
- **Inputs:** `functional_representation`, `function_status[]`, `reader_gap_summary`, purpose (assignment + student), prior target/continuity.
- **Outputs:** `primary_target` (single function/aspect of the unit), `leverage_rationale`, `forward_progress_rationale` (how addressing this keeps the student advancing toward completing the assignment), `target_continuity` (new | continued | resolved→advance).
- **Does NOT:** model the learner (next stage), teach, or address multiple issues.
- **Layers:** L2 (one-target policy), L3.
- **Constitutional:** exactly one target.

### S6 — DEVELOPMENTAL STRATEGY  ◀ learner modeling & developmental reasoning BEGIN here
- **Responsibility:** Now invoke the learner model + ZPD + scaffolding decision for the selected target only. Decide amount of support, question/explanation balance, and whether to teach-heavy, guide, or fade — given the learner's history.
- **Inputs:** `primary_target`, learner `developmental_profile`/history, `revision_history`, teacher scaffolding config.
- **Outputs:** `learner_state` (for this target), `zpd_position`, `scaffolding_level`, `support_move` (teach-heavy | guided | fade), `consolidation`/`fading` flags.
- **Does NOT:** generate the student-facing text yet; address other targets.
- **Layers:** L4 (learner model), L2 (scaffolding/fading policy).
- **KB:** scaffolding strategies, ZPD, learner-model concepts.

### S7 — DIALOGUE / EXPLICIT TEACHING
- **Responsibility:** Generate ONE learner-facing coaching turn following the **explicit-teaching pattern**:
  1. **Orient** — where we are (unit) and why it matters (reader-centered).
  2. **Teach** — explicitly explain the concept **from the reader's perspective**: what the concept does for the reader, not merely a formal definition. E.g., *"A thesis helps readers understand the central idea that will organize the essay,"* rather than *"a thesis expresses an opinion."*
  3. **Locate** — identify the student's closest current attempt; explain why it's working or where its function is incomplete.
  4. **Invite** — invite the student to apply/revise **their own writing** (one invitation).
  5. **Reflect** — set up reflection on how the revision improved communication.
- **Inputs:** `primary_target`, developmental strategy, functional interpretation (to locate the attempt), purpose, unit, KB dialogue guidance.
- **Outputs:** `student_facing_invitation` (single), `candidate_invitations` (exactly 2, internal), `teaching_content`, `reflection_prompt`, `transparency_state` (see §5).
- **Does NOT:** write, rewrite, or supply the student's content; introduce a second target; score.
- **Layers:** L5 (presentation), L1 (anti-coauthoring), L2.
- **Constitutional:** one invitation; explicit teaching of the concept is permitted, but the student generates the ideas, makes the decisions, and produces the revised text.

---

## 4. Branches / decision points

### B1 — Purpose-Unclear (after S1)
- **Trigger:** low `purpose_confidence` / intended meaning indeterminate.
- **Behavior:** skip heavy diagnosis (S3–S6); run a clarification turn (inside-out) whose single target is *surface the student's intended meaning/purpose*. Still explicit + reader-centered ("to help a reader, we first need to know what you're trying to say"). One invitation.
- **Exit:** once purpose is sufficiently clear (this or a later turn), resume the normal pipeline at S2.

### B2 — Prewriting Mode (after S4)
- **Trigger:** the S4 functional representation shows **insufficient conceptual organization** — not merely weak prose. Prewriting is invoked only when there is not yet a developed idea/claim for the unit's functions to organize. **Weak or clumsy prose that nonetheless carries an organizable idea does NOT trigger prewriting** (it is handled as a normal target).
- **Behavior:** temporarily set `writing_unit = prewriting`; the target becomes organizing thinking (idea generation, claim formation, structure-of-thought) before returning to drafting/revision. Explicit teaching of the prewriting move; the student does the thinking.
- **Exit:** when sufficient conceptual organization exists, return to the drafting unit.
- **Design intent:** detection uses only S4 signals (cheap), so we do NOT reintroduce the global analysis v2 is trying to avoid.

### B3 — Foundational Fallback (anti-suppression; inherited from v1)
- **Trigger:** any stage finds evidence inconsistent with the established purpose/unit (off-task, incoherent across ideas) that the current lens cannot contain.
- **Behavior:** raise a fallback flag → escalate to the full frozen `exhaustive` engine. Never force material into the wrong lens. Preserves constitutional safety.

---

## 5. Transparency contract (point #10)

Every v2 turn MUST emit `transparency_state` (the engine produces it even before any UI consumes it):
- `where_you_are` — position in the assignment arc.
- `current_unit` — the writing unit being worked.
- `why_it_matters` — reader-centered rationale.
- `why_this_now` — **why we are working on this before something else** (makes instructional prioritization transparent to the learner; derived from S5's leverage + forward-progress rationale).
- `todays_goal` — the single instructional target as a student-facing goal.
- `whats_next` — the anticipated next unit/step.

Layer: L5 + a later `StudentWorkspace` UI sub-phase. The evaluator scores its completeness/accuracy.

---

## 6. Where key things happen (explicit answers)
- **Purpose determination (assignment + student, separately):** S1 (Pass 1).
- **Writing unit / instructional context:** S2 (Pass 1, before learner modeling).
- **Functional interpretation (functional representation; understand, not evaluate):** S4 (Pass 2).
- **Single instructional target selected (leverage + forward progress):** S5 (Pass 2).
- **Learner modeling BEGINS:** S6 (Pass 3).
- **Developmental reasoning BEGINS:** S6 (Pass 3).
- **Explicit teaching occurs (reader-perspective):** S7 (Pass 3, steps 2–3).
- **Dialogue generation occurs:** S7 (Pass 3).

---

## 7. Updated evaluator dimensions for Compare-Two-Runs

Keep all existing v1 dimensions (constitutional preservation, anti-coauthoring, target defensibility, restraint, etc.) and ADD:
- **Cognitive Substitution (CONSTITUTIONAL, gating).** Question: *"Could the learner submit the assignment after reading Compass's response without performing the intended cognitive work?"* If **yes**, the response **fails constitutional review** (hard fail, same severity as an anti-coauthoring violation). This guards the boundary between explicit *teaching* and doing the student's *thinking/writing*.
- **Interpret-before-instruct ordering** — interpretation (S1–S4) precedes and is distinct from instruction (S5–S7); no teaching leaks into interpretation stages.
- **Purpose-first ordering** — purpose established before diagnosis; assignment vs. student purpose distinguished.
- **Single-target discipline** — exactly one target addressed; target preserves forward progress toward assignment completion.
- **Explicit teaching present** — concept taught from the reader's perspective before the invitation; the 5-step pattern followed.
- **Reader-centered framing** — instruction framed by what the reader needs.
- **Function over form** — no rigid template imposed; alternative valid realizations respected.
- **Transparency completeness** — all six transparency fields present + accurate (including `why_this_now`).
- **Prewriting-mode appropriateness** — entered only for insufficient conceptual organization; never for weak prose alone; not over-triggered.
- **Latency** — total + per-pass timings.

**Promotion criteria:** constitutional preservation maintained (0 regressions, 0 anti-coauthoring violations) AND measurable improvement on clarity / explicit-teaching / transparency / latency vs. v1. NOT mere output matching (per the v1 precedent: judge governing behavior, not textual similarity).

---

## 8. Constitutional invariants every stage must preserve (L1 — non-negotiable)
- Student authorship / anti-coauthoring: never write, rewrite, or supply copyable content.
- Exactly one instructional target; exactly one learner-facing invitation.
- Restraint: no invented deficiencies; intervention proportional to genuine need.
- No scores.
- Honor stopping rules (independence requests / diminishing returns).
- Answer-the-assignment / honor the teacher's stated purpose.
- The student performs all revision and all cognitive work. **Explicit teaching is permitted but must not cross into doing the student's thinking or writing.**
- **No cognitive substitution:** a learner must not be able to submit the assignment after reading Compass's response without performing the intended cognitive work. (Evaluated as a gating dimension — see §7.)

---

## 9. Reuse & integration map (least disruption)
- `reasoning_mode` gains a third value: `governance_v2` (alongside `exhaustive`, `triage_experimental`). Default stays `exhaustive`.
- Reuse the existing triage Stage-1 signals for S1/S2 where suitable (or a v2-specific purpose/unit pass — see open choices).
- Reuse the `ROUTE_LENS_MAP` concept as the basis for the S3 functional-model lookup.
- Reuse durable polling + streaming (stream the S7 invitation).
- Reuse the Compare-Two-Runs harness + governance inspectability UI (extend to 7 stage-panels + branch + transparency).
- Frozen `SYSTEM_MESSAGE` untouched — referenced as the KB.

---

## 10. Open implementation choices — RESOLVED
1. ~~Call granularity~~ — **DECIDED (§1):** three batched passes (P1: S1–S3, P2: S4–S5, P3: S6–S7), seven conceptual stages preserved.
2. **P1 prompt — DECIDED:** create a **dedicated Governance v2 P1 prompt**, designed around the new architecture (purpose/unit/functional-model as the foundation of v2 reasoning), NOT a reuse of the v1 triage pass. It may borrow ideas/components but must not be constrained by v1 triage assumptions.
9. **Assignment vs. Student purpose divergence — DECIDED:** divergence is **observed, not an automatic branch**. Flow: determine Assignment Purpose → infer Student Purpose → compute `purpose_alignment` → record in the ledger. If alignment is good → continue normally. If partial/divergent → decide whether the divergence *prevents meaningful work on the current writing unit*: if the student has misunderstood the assignment so substantially that productive instruction cannot proceed, **briefly repair the student's understanding of the assignment first** (a bounded assignment-understanding repair, then continue); otherwise **retain the original instructional target while acknowledging the divergence**. Principle: preserve instructional momentum; intervene on assignment understanding only when it genuinely blocks progress. (This repair is a bounded action within S1/S5, NOT a new top-level branch, so not every misunderstanding derails the trajectory.)
- Remaining genuinely-open (safe to settle in code): §10.3 prewriting signal operationalization, §10.4 purpose-confidence threshold, §10.5 candidate count (default keep 2), §10.6 `why_this_now` phrasing, §10.7 per-pass KB budget, §10.8 abbreviated vs full turn for B1/B2.

---

## 11. Non-goals for this round
- No rewrite of the instructional knowledge (frozen `SYSTEM_MESSAGE` stays; a "true SM v2" is a possible future).
- No teacher-product changes (**Phase III Teacher Dashboard is PAUSED** until v2 is specced, implemented, validated, and promoted).
- No constitutional changes.

---

## 12. Proposed workstream sequence (after this spec is approved)
1. Approve this spec (authoritative contract).
2. Implement Governance v2 behind `reasoning_mode="governance_v2"`.
3. Extend the evaluator with the §7 dimensions.
4. Validate via the full 66-case Compare-Two-Runs vs the frozen v1 baseline (+ vs Governance v1).
5. Promote v2 to default only on passing constitutional review + comparative improvement.
6. Transparency UI sub-phase (#10).
7. Prewriting-mode refinement sub-phase (#9).
8. Resume Phase III Teacher Dashboard, designed around v2's actual outputs.
