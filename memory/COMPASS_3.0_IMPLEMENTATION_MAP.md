# Compass 3.0 — Implementation Map (Existing Engine)

**Status:** Documentation only. No code was modified to produce this map.
**Purpose:** Give Compass 3.0 a precise picture of the CURRENT execution path so that future
changes MODIFY existing components rather than accidentally recreating them.
**Scope of the traced path:** Prompt → OT → CM → Teacher Review → Selector → Coaching Prompt → Student Response.

> Terminology note (as used in this repo):
> - **Prompt** = Assignment Representation / "Question Loop" (`assignment_representation.py`) + the per-session `assignment` / `assignment_prompt` / `Telos`.
> - **OT** = Organizing Thought (`organizing_thought.py`) — the five pre-writing objects + the "My Ideas" workflow.
> - **CM** = Canonical Model — the authoritative knowledge layer (`compass_curriculum.py`, `canonical_models/*.json`, `canonical_writing_model.json`, `instructional_objects.json`, `developmental_exit_criteria.json`).
> - **Teacher Review** = the `teacher_review` ENTRY POINT into the one structural reasoner, plus the review-surface endpoints (`/api/teacher-review/cases`, `/api/sessions/{id}/teacher-reflection`) and `TeacherReview.jsx`.
> - **Selector** = the Decision Engine (`compass_structure_engine.select_structure` → `_select_structure_canonical`).
> - **Coaching Prompt** = the Dialogue Engine (`generate_dialogue` / `generate_closure`).
> - **Student Response** = the `/api/sessions/{id}/interact` turn cycle orchestrated by `_run_reasoning` → `_finalize_structure_v5`.

---

## High-level runtime flow

```
[Prompt / Question Loop]            assignment_representation.py  (/api/assignment/*)
        │  build_handoff() -> handoff object (provenance-tagged)
        ▼
[Bridge]                            server.py  POST /api/sessions/from-representation
        │  _map_component_to_kb(), _compile_representation_notes() -> Session(+telos, teacher_notes)
        ▼
[OT — Organizing Thought]           organizing_thought.py  (/api/ot/*)   (OPTIONAL pre-writing)
        │  ot state on Session.ot; /handoff sets handoff_ready
        ▼
[Student Response cycle]            server.py  POST /api/sessions/{id}/interact
        │  creates placeholder AI Turn (status=processing); background task:
        │  _run_reasoning() -> (RP5 path) _finalize_structure_v5()
        ▼
[Selector — Decision Engine]        compass_structure_engine.select_structure()
        │  -> _select_structure_canonical()  [reads CM: curriculum + decision model]
        │  picks ONE structure (target) + provisional judgment; writes InstructionalState (compass_foundation)
        ▼
[Coaching Prompt — Dialogue Engine] compass_structure_engine.generate_dialogue() / generate_closure()
        │  builds the FIXED target into ONE learner-facing invitation (cannot re-decide)
        ▼
[Persisted Turn]                    AI Turn.content = invitation; focus_of_work etc. persisted
        ▼
[Teacher Review surface]            server.py /api/sessions/{id}/teacher-reflection, /teacher-review/cases
                                    _curate_case() reads the same live state -> TeacherReview.jsx
```

Engine selector flag (added earlier): `COMPASS_ENGINE` (`canonical_v2` default | `functional_v3`) chooses
WHICH engine module `_finalize_structure_v5` imports (`compass_structure_engine` vs `functional_v3`, currently identical).

---

## Stage-by-stage documentation

### STAGE 1 — PROMPT (Assignment Representation / Question Loop)

1. **Files / functions:** `assignment_representation.py` — `analyze_assignment()`, `compare_interpretation()`,
   `generate_scaffold()`, `evaluate_operation()`, `evaluate_restatement()`, control logic (`_pick_target`,
   `_open_target_or_restatement`), `build_handoff()`, `assess_handoff_readiness()`. Router prefix `/api/assignment`.
   Knowledge-Loop extension (`assess_knowledge_need`, `evaluate_knowledge_turn`) lives here too.
2. **Inputs:** Raw `assignment_text` (student/teacher); student interpretation, operation attempts, restatement text.
3. **Outputs:** `AssignmentSession` (Mongo `assignment_sessions`) with `demands[]`, `important_distinctions`,
   `ambiguities`, per-demand `status`; and a transient **handoff** dict (provenance-tagged:
   `explicit_teacher | explicit_student | inferred_by_compass | unresolved`).
4. **Internal purpose:** Help the student build an ADEQUATE REPRESENTATION of what the task requires — at the
   level of TASK REQUIREMENTS, never answer content. Upstream service, NOT an instructional writing engine.
5. **Decision rules:** Deterministic control (`_pick_target`: essential > important; `needs_attention` > `unconfirmed`;
   original order). Scaffold ladder L0–L3; anti-fixation (`escalations_this_visit`); "credit everything" across demands;
   reconstruction gating; adequacy-for-now = every essential demand ≥ `developing`.
6. **Data structures produced:** `AssignmentDemand`, `Scaffold`, `InteractionRecord`, `KnowledgeState`, handoff dict.
7. **Dependencies on earlier stages:** None (entry point). Shares LLM key + `now_iso` injected by `server.py` `init()`.

### STAGE 1b — BRIDGE (Representation → Writing Session)

1. **Files / functions:** `server.py` — `POST /api/sessions/from-representation` (`create_session_from_representation`),
   `_map_component_to_kb()`, `_select_initial_component()`, `_compile_representation_notes()`.
2. **Inputs:** `assignment_session_id`, optional `learner_goal`/`teacher_goal`/`existing_draft`/`task_representation`.
3. **Outputs:** A live `Session` (Mongo `sessions`) seeded with `assignment`, `telos`, engine-facing `teacher_notes`
   (with provenance), `origin_representation` = handoff, and a suggested initial component (soft hint only).
4. **Internal purpose:** Convert an adequate representation into a Milestone-engine writing session WITHOUT teaching.
5. **Decision rules:** Initial-component priority = teacher goal > learner goal > highest-leverage demand.
   `_OP_TO_ELEMENT` / `_ELEMENT_TO_DOMAIN` map a demand to a precise element + broad domain (fallback = Purpose).
6. **Data structures produced:** `Session`, `Telos`, `origin_representation` dict.
7. **Dependencies:** Consumes Stage 1's `AssignmentSession` + handoff. The suggested component is a HINT; the
   Selector (Stage 5) still chooses the authoritative target from live participation.

### STAGE 2 — OT (Organizing Thought)

1. **Files / functions:** `organizing_thought.py` (router `/api/ot`). Core: `_ot_reason()` + `_OT_SYSTEM`
   (PROCEED/TEACH/ASK/PAUSE); five-object endpoints (`/start`, `/object`, `/interact`, `/advance`, `/handoff`);
   "My Ideas" two-pass workflow (`_ideas_reason`, `_ideas_map`, `_ideas_challenge`, `_ideas_inquiry`,
   `_ideas_construct`, `_leakage_sanitize`). Curriculum data: `ot_curriculum.json`.
2. **Inputs:** `session_id`, current stage, student's per-stage text, "My Ideas" answers.
3. **Outputs:** `ot` object stored ON the Session (`Session.ot`): `objects{}` (five objects), `status{}`,
   `needs_review[]`, `ideas{}` (questions, per-question responses, `inquiry_plan`, `my_ideas_construct`), `handoff_ready`.
4. **Internal purpose:** Help the student ORGANIZE THINKING before writing (Assignment, Questions, My Ideas,
   Current Answer, Plan). Extension of the student experience; does NOT touch the M1–M14 writing engine.
5. **Decision rules:** One move per turn; instructional SUFFICIENCY not perfection; `_flag_dependents` marks later
   objects for review on material change; strong anti-leakage (teach STRUCTURE, never assignment-specific content);
   "My Ideas" phases pass1 → knowledge_map → inquiry_plan → inquiry_paused → pass2 → construct → done.
6. **Data structures produced:** `ot` dict + `ideas` sub-dict (all on `Session.ot`). No new collection.
7. **Dependencies:** Reuses the `sessions` collection; seeded from `Session.assignment`. OPTIONAL — a session may skip
   OT and go straight to the writing/interact cycle.

### STAGE 3 — CM (Canonical Model / knowledge layer)

1. **Files / functions:** `compass_curriculum.py` (five PRIMARY structures + cross-structure
   `instructional_decision_making` model; `is_structure_ready`, `get_structure`, `get_decision_section`,
   `canonical_decision_questions`, …); data in `canonical_models/*.json`. Complementary KBs loaded in `server.py`:
   `canonical_writing_model.json` (13 domains), `instructional_objects.json` (elements), `developmental_exit_criteria.json`.
   Consumed inside the engine via `_canonical_primary_digest()` + `_decision_model_digest()`.
2. **Inputs:** None at runtime beyond a structure/section name (pure lookups). Populated verbatim from JSON on import.
3. **Outputs:** Structured records: nine-field primary models (definition, function, dependencies, requirements,
   developmental_variations, developmental_sufficiency, discovery/rescue instruction, observable_decision_questions);
   decision model sections (foundational_principles, order_of_decision, when_not_to_teach, when_to_recurse, questions).
4. **Internal purpose:** The authoritative, non-invented knowledge Compass reasons FROM. "Structured internal
   knowledge, not prompt fragments." Governs WHAT the five canonical primaries are and HOW selection is decided.
5. **Decision rules:** No content judgment — only schema validation (`validate_model`, `validate_decision_model`);
   fields stay `PENDING_CANONICAL_INPUT` until an authority-supplied model is inserted verbatim.
6. **Data structures produced:** `CURRICULUM{}`, `DECISION_MODEL{}` (module-level registries); the engine also keeps a
   parallel `MINIMAL_OBJECTS` (5-component legacy objects) + `PRIORITY_ORDER` list.
7. **Dependencies:** Read-only; consumed by the Selector (Stage 5) and, via `retrieve_object()`, by the Dialogue
   Engine (Stage 6). Not wired to OT/Prompt at runtime today.

### STAGE 4 — TEACHER REVIEW (entry point + review surface)

1. **Files / functions:** `server.py` — `GET /api/teacher-review/cases` (`teacher_review_cases`),
   `GET /api/sessions/{id}/teacher-reflection` (`teacher_reflection`), `_curate_case()`. Engine-side: the
   `entry_point = teacher_review` branch of the UNIFIED STRUCTURAL REASONING described in `SYSTEM_MESSAGE`
   (`StructuralReasoning` model). Frontend: `TeacherReview.jsx`, `TeacherReflection.jsx`.
2. **Inputs:** A `session_id` (live) or curated fixtures (`teacher_review_fixtures.json`); the session's `turns` +
   persisted theory/state.
3. **Outputs:** A curated "case" object (assignment, response, the single instructional focus chosen, why that focus,
   what was set aside, broader developmental goal) rendered as the teacher's professional mirror.
4. **Internal purpose:** Let a teacher SEE what Compass understood and why it chose one instructional focus — the same
   reasoning that drives student coaching, presented for review. It is an ENTRY POINT / VIEW, not a second engine.
5. **Decision rules:** "First locate where the writing sits in the canonical hierarchy, then activate that structure's
   canonical representation; the remaining reasoning is IDENTICAL to the Composition Process" (per `SYSTEM_MESSAGE`).
   `entry_point` is inferred: first submission of an existing passage = `teacher_review`; progressive construction =
   `composition_process`.
6. **Data structures produced:** Curated case dict (view model); no separate persistence — reads live session state.
7. **Dependencies:** Consumes the Selector + Dialogue outputs already persisted on the session/`InstructionalState`.

### STAGE 5 — SELECTOR (Decision Engine — WHAT is taught)

1. **Files / functions:** `compass_structure_engine.py` — `select_structure()` (dispatcher) →
   `_select_structure_canonical()` (canonical path; `_CANON_SEL_SYS`, `_canonical_primary_digest`,
   `_decision_model_digest`) OR legacy `select_structure` body + `_SEL_SYS`/`PRIORITY_ORDER`. Orchestrated by
   `run()` STEP 1–3. Model: `SEL_MODEL` = `claude-haiku-4-5`.
2. **Inputs:** `session_id`, `assignment`, `unit` (`_unit_hint`), `student_text`, `canonical` flag,
   `prior_target`/`prior_variation`/`prior_student_text` (Instructional Continuity), teacher overrides from state.
3. **Outputs:** dict `{selected, status, developmental_variation, established[], not_applicable[], justification,
   candidate_objects[], next_objective, current_thesis, confidence, _provisional{...}, _meta bytes}`.
4. **Internal purpose:** Identify the SINGLE highest-leverage structure to teach this turn (One Thing Rule). It is the
   ONLY component that determines WHAT is taught; nothing downstream may override it.
5. **Decision rules:** Canonical path = five primaries (Opening, Thesis, Elaboration, Evidence / Example, Conclusion)
   governed by the CM decision model + **generative (developmental) sufficiency** ("can this structure now support work
   on its dependents?"). Deterministic guards: developmental-sufficiency guard (auto-advance a `present`+`integrated`
   Thesis), continuity label, teacher-override honoring (`CASE_4`), null → closure (`CASE_2`). Legacy path walks a fixed
   `PRIORITY_ORDER`.
6. **Data structures produced:** Writes authoritative decision to persistent `InstructionalState` (compass_foundation):
   `selected_instructional_object`, `developmental_variation`, `instructional_analysis`, strengths, sufficiency, plus an
   `AuditEvent` (`instructional_decision`).
7. **Dependencies:** Reads CM (Stage 3) + prior `InstructionalState`; consumed by the Dialogue Engine (Stage 6). Runs
   only on the RP5 path (`reasoning_mode ∈ {consolidated_v2, structure_v5, canonical_v2}`).

### STAGE 6 — COACHING PROMPT (Dialogue Engine — HOW it is taught)

1. **Files / functions:** `compass_structure_engine.py` — `generate_dialogue()` (+ `_resolve_teaching_source`,
   action hints, `developmental_operations.py` operation menu) and `generate_closure()` (CASE_2). Model:
   `DLG_MODEL` = `claude-sonnet-4-6`. Global constitution/coaching contract lives in `server.py` `SYSTEM_MESSAGE`.
2. **Inputs:** The FIXED target + its retrieved 5-component object (`retrieve_object()`), `status`, `kind`,
   `action`, `mode` (first_turn|continuation), `sufficiency`, `rescue`, `prior_student_text`, `assignment`, `unit`.
3. **Outputs:** ONE learner-facing `invitation` string (+ prompt byte count for telemetry).
4. **Internal purpose:** Build the chosen structure into a warm, single-focus coaching invitation. It may explain /
   scaffold / question / encourage / pace — but MUST NOT choose, replace, strengthen, or substitute the target.
5. **Decision rules:** Coaching execution contract (name the lesson first → locate it in the student's own words →
   purpose → missing dependency → one scaffolded act); one target, one invitation; scaffold-not-supply; anti-coauthoring
   / writing-over-content priority; developmental sufficiency → release. `first_turn` vs `continuation`; `rescue` after
   ≥2 stuck attempts or a help request.
6. **Data structures produced:** `invitation` text persisted to the AI `Turn.content`; `focus_of_work`,
   `focus_description`, `current_thesis`, `established_structures` set on the Turn; `AuditEvent` (`coaching_dialogue`).
7. **Dependencies:** Strictly downstream of the Selector — receives the already-decided target; cannot re-decide.

### STAGE 7 — STUDENT RESPONSE (turn cycle / orchestration)

1. **Files / functions:** `server.py` — `POST /api/sessions/{id}/interact`, background `_run_reasoning()` →
   `_finalize_structure_v5()` (RP5) [or legacy `_run_engine` / `triage_experiment` / `governance_v2` for other modes];
   `compass_foundation.begin_instructional_turn()` (bridge read). Frontend: `StudentWorkspace.jsx` (durable polling).
2. **Inputs:** `InteractRequest {content, kind ∈ writing|revise|continue|answer|explain}`; the persisted `Session`.
3. **Outputs:** Updated `Session` with a new student `Turn` + a completed AI `Turn` (invitation); updated
   `InstructionalState`, `revision_history`, audit events; efficiency `_meta`.
4. **Internal purpose:** Run reasoning independently of the client connection (client disconnects never interrupt),
   persist the completed coaching turn, and keep the developmental record.
5. **Decision rules:** Placeholder AI turn created immediately (`status=processing`); background task computes the
   invitation, then writes it only if the turn is still active; RP5 routing via
   `reasoning_mode ∈ RP5_MODES`; engine module chosen by `COMPASS_ENGINE` (canonical_v2 | functional_v3).
6. **Data structures produced:** `Turn` (student + ai), persisted `Session`, `RevisionRecord` (on revise),
   `functional_v3_trace.log` records (only when `COMPASS_ENGINE=functional_v3`).
7. **Dependencies:** Wraps Stages 5–6; feeds Stage 4 (Teacher Review reads the resulting state). Preview sessions add
   the `ExperienceControl` cap (one objective → reflection).

---

## KEEP / MODIFY / REPLACE table (Compass 3.0 expectation)

> Guidance for Compass 3.0: implement new reasoning INSIDE the components marked **MODIFY** (primarily inside
> `functional_v3.py` — the experimental duplicate of `compass_structure_engine.py`). Do NOT create parallel copies of
> KEEP components; extend them in place behind the `COMPASS_ENGINE=functional_v3` flag.

| # | Component | File(s) / entry | Disposition | Rationale |
|---|-----------|-----------------|-------------|-----------|
| 1 | Prompt / Question Loop | `assignment_representation.py` | **KEEP** | Upstream representation service; not the reasoning engine. Stable contract via handoff. |
| 2 | Representation→Session bridge | `server.py` `from-representation`, `_map_component_to_kb`, `_compile_representation_notes` | **KEEP** | Pure mapping/seed; provenance handling is sound. Touch only if handoff schema changes. |
| 3 | OT (Organizing Thought) | `organizing_thought.py`, `ot_curriculum.json` | **KEEP** | Pre-writing organizer; independent of the writing engine. Out of scope for reasoning changes. |
| 4 | CM — canonical curriculum data | `compass_curriculum.py`, `canonical_models/*.json` | **KEEP (extend data only)** | Authoritative, verbatim-supplied knowledge. Compass 3.0 supplies/refines MODELS, not code. |
| 4b | CM — legacy `MINIMAL_OBJECTS` + `PRIORITY_ORDER` | `compass_structure_engine.py` | **MODIFY** | The 5-component objects + fixed priority list are the concrete decision knowledge Compass 3.0 will most likely revise/replace decision-by-decision. |
| 5 | Complementary KBs | `canonical_writing_model.json`, `instructional_objects.json`, `developmental_exit_criteria.json` | **KEEP (extend data only)** | Data layer consulted by selector/dialogue; grow via data, not new loaders. |
| 6 | Teacher Review surface | `server.py` `teacher-review/cases`, `teacher-reflection`, `_curate_case`; `TeacherReview.jsx` | **KEEP** | Explicitly protected. It is a VIEW over engine state; must keep showing whichever engine ran. |
| 7 | Turn orchestration | `server.py` `interact`, `_run_reasoning`, `_finalize_structure_v5` | **KEEP (thin extend)** | Stable transport + persistence + engine routing. Only the engine-selection branch is a seam. |
| 8 | Engine selector flag | `server.py` `COMPASS_ENGINE` | **KEEP** | The single switch that routes to `functional_v3`. This is the intended seam for 3.0. |
| 9 | **Selector / Decision Engine** | `compass_structure_engine.select_structure` / `_select_structure_canonical` (→ duplicated in `functional_v3.py`) | **MODIFY → eventually REPLACE (in functional_v3 only)** | The core of "WHAT is taught." Compass 3.0 reasoning changes land here, one decision at a time, in the `functional_v3` copy. `canonical_v2` original stays frozen. |
| 10 | **Coaching Prompt / Dialogue Engine** | `compass_structure_engine.generate_dialogue` / `generate_closure` (→ `functional_v3.py`) | **MODIFY (in functional_v3 only)** | "HOW it is taught." Wording/scaffolding evolves with the new reasoning, still one-target/one-invitation. |
| 11 | Selector/Dialogue system prompts | `_CANON_SEL_SYS`, `_SEL_SYS`, coaching contract in `SYSTEM_MESSAGE` | **MODIFY (in functional_v3 only; per spec)** | Prompts encode current reasoning; 3.0 rewrites them deliberately, only after the conceptual spec. NOT now. |
| 12 | Persistent InstructionalState + audit | `compass_foundation.py` | **KEEP** | Storage/audit contract reused unchanged (Sprint 1–4). Add fields only if a decision truly requires it. |
| 13 | Developmental operations menu | `developmental_operations.py` | **MODIFY (optional)** | A transformation catalogue the dialogue draws on; may grow as 3.0 reasoning matures. |
| 14 | Legacy alternate engines | `triage_experiment.py`, `governance_v2.py`, `_run_engine` (exhaustive) | **KEEP (dormant)** | Retained for rollback/comparison; not on the live RP5 path. Do not extend for 3.0. |

---

## Guardrails for Compass 3.0 changes (derived from this map)

- The live learner path is **only** `interact → _run_reasoning → _finalize_structure_v5 → compass_structure_engine`
  (or `functional_v3` when the flag is set). New reasoning belongs in **`functional_v3.py`** behind
  `COMPASS_ENGINE=functional_v3`; `compass_structure_engine.py` (`canonical_v2`) stays byte-frozen.
- The **Selector is the single authority** on WHAT is taught (one target/turn); the **Dialogue Engine may never
  re-decide**. Preserve this contract in any 3.0 change.
- **CM is data, not code.** Prefer supplying/adjusting canonical JSON models over adding new lookup paths.
- **Teacher Review, OT, Prompt, API contracts, DB schema, and UI are protected.** They consume engine state; changing
  the engine must not change their shapes (`Session`, `Turn`, `InstructionalState`, handoff, `ot`).
- Persist through the existing `InstructionalState` + `AuditEvent` writers; do not introduce a parallel store.
