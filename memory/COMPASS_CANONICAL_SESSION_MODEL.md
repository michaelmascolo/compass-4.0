# Compass — Canonical Instructional Session Model (operational spec)

Status: CANONICAL. Every current and future capability MUST fit this lifecycle. This is an operational
contract, not theory. It does not redesign the engine, the interface, or the loops — it names the single
instructional rhythm they all already share, and the exact artifacts that perform each stage.

Definitions used throughout:
- **Representation** = an assignment/task understanding (collection `assignment_sessions`, model `AssignmentSession`).
- **Writing session** = a Milestone-engine instructional session (collection `sessions`, model `Session`).
- **Cycle** = one Invitation → Performance → Interpretation → Decision loop inside a writing session (one `Turn` pair).
- **Engine** = the FROZEN Milestone M1–M14 reasoning in `server.py` (`_run_reasoning`, SYSTEM_MESSAGE). Never modified here.

---

## 1. CANONICAL SESSION LIFECYCLE DIAGRAM

```
                         (any entry: assignment · draft · teacher feedback ·
                          selected component · prior session · learner goal)
                                          │
                                   ┌──────▼───────┐
                                   │ 1 ORIENTATION │  → shared representation sufficient to begin
                                   └──────┬───────┘
                                          │  (handoff: readiness gate)
                                   ┌──────▼───────────────┐
                                   │ 2 TARGET SELECTION     │ → ONE developmental focus
                                   └──────┬───────────────┘
                                          │
          ┌───────────────────────────────▼───────────────────────────────┐
          │                        INSTRUCTIONAL CYCLE                       │
          │   ┌────────────────┐   ┌────────────────┐   ┌────────────────┐  │
          │   │ 3 INVITATION    │──▶│ 4 PERFORMANCE   │──▶│ 5 INTERPRETATION│  │
          │   │ (one move)      │   │ (learner works) │   │ (dev. state)    │  │
          │   └────────────────┘   └────────────────┘   └───────┬────────┘  │
          │                                                       │           │
          │                                             ┌─────────▼────────┐  │
          │                                             │ 6 DECISION        │  │
          │                                             │ continue/±support/ │  │
          │                                             │ redirect/retarget/ │  │
          │                                             │ conclude/pause     │  │
          │                                             └─────────┬────────┘  │
          └───────────────────────────────┬───────────────────────┘           
              continue → back to Stage 3   │  conclude/pause
                                    ┌───────▼────────┐
                                    │ 7 CLOSURE       │ → resumable developmental state
                                    └────────────────┘
                                 (resume re-enters at Stage 1/2 with prior state)
```

**Success (Stage 8, applies to the whole loop):** a session succeeds when the learner demonstrates **increased
control over ONE meaningful aspect of writing** — observable as `instructional_reasoning.degree_of_student_control`
moving up (scaffolded → emerging → increasing → largely_independent) and/or a non-empty
`evidence_of_developmental_movement`. NOT a finished essay, assignment, or perfect draft.

---

## 2. STAGE-BY-STAGE SPECIFICATION

### Stage 1 — Orientation
- **Purpose:** establish enough shared understanding of the learner's task to begin productive work.
- **Inputs (any):** assignment prompt, existing draft, teacher feedback, prior session, learner goal, selected component.
- **Output:** a shared **representation** sufficient to begin (adequate — not exhaustive).
- **Learner:** states the task / pastes draft / picks a goal; edits Compass's summary if wrong.
- **Compass:** extracts task demands; assesses adequacy-for-handoff; surfaces open questions without interrogating.
- **Teacher (when applicable):** supplies the assignment, purpose, and any required component via configuration.
- **Implements:** `AssignmentSession` + Question Loop (`/api/assignment/*`); `assess_handoff_readiness`; `build_handoff`;
  `GET /assignment/sessions/{id}/handoff`; `BeginWorkingModal` (editable summary). Draft/teacher-feedback entries seed the
  representation directly. Output is carried in `Session.origin_representation`.

### Stage 2 — Instructional Target Selection
- **Purpose:** identify exactly ONE productive instructional focus for this cycle.
- **Output:** `scaffolding_control.primary_target` (+ `prioritization_rationale`) for the current cycle.
- **Selection order (authoritative):** teacher-selected component > learner-selected component > engine's highest-leverage
  target. The bridge produces a *soft suggestion* (`_select_initial_component`, priority teacher>learner>highest-leverage);
  the **engine makes the binding per-cycle choice** from the learner's actual performance.
- **Why-this / why-not:** the engine records the chosen `primary_target` with `prioritization_rationale`
  (developmental readiness / importance for communication / leverage / dependency) and lists rejected options in
  `scaffolding_control.postponed` and `future_opportunity`.
- **Learner:** may choose a starting component (honored if workable).
- **Compass/Engine:** diagnoses all opportunities, prioritizes exactly one, defers the rest.
- **Teacher:** a teacher-selected component is honored when appropriate.
- **Implements:** Milestone engine M11 `scaffolding_control` + M-frameworks; KB retrieval
  (`canonical_writing_model.json` → broad domain; `instructional_objects.json` → precise `active_instructional_element`).

### Stage 3 — Developmental Invitation
- **Purpose:** produce ONE invitation that lets the learner perform the intellectual work of the current target.
- **Output:** a single learner-facing coach message ending in one doable act; expects a learner action.
- **Requirements:** connects to purpose, reader, and the current writing component; matches `instructional_mode`
  (developmental_question | explicit_instruction | brief_demonstration | guided_revision | reflection | consolidation);
  never asks random questions; never supplies the answer (M5A anti-coauthoring).
- **Learner:** none yet (receives the invitation).
- **Compass/Engine:** generates one invitation via `Intervention` + M11 mode; obeys "one target, one invitation."
- **Implements:** `_run_reasoning` output (`Intervention`); rendered as the coach `Turn` in `StudentWorkspace`
  (first invitation auto-opens after handoff).

### Stage 4 — Learner Performance
- **Purpose:** the learner performs the substantive work; Compass waits.
- **Output:** new learner performance (a `Turn` with `kind` ∈ writing | revise | answer | explain | continue).
- **Learner:** writes / revises / reflects / reorganizes / evaluates / explains — in the draft canvas or reply.
- **Compass:** does nothing except wait (no auto-writing, no auto-revision).
- **Implements:** `POST /sessions/{id}/interact`; draft persisted per session; `DRAFT_KINDS` = {writing, revise}.

### Stage 5 — Instructional Interpretation
- **Purpose:** interpret what the learner actually did (diagnosis, NOT grading, NO scores).
- **Output:** current developmental state.
- **Determines:** what improved / what did not; whether control increased (`degree_of_student_control`); whether
  misconceptions remain (`primary_developmental_tension`); movement since last turn (`evidence_of_developmental_movement`).
- **Compass/Engine:** produces `DevelopmentalTheory.instructional_reasoning`; on a `revise`, appends a `RevisionRecord`.
- **Implements:** `_run_reasoning` (`InstructionalReasoning`); `_record_revision` → `Session.revision_history`.

### Stage 6 — Instructional Decision
- **Purpose:** decide the next move for the cycle.
- **Output:** ONE decision → `scaffolding_control.cycle_status` ∈ {continue | consolidate_and_return | stop}
  (+ `stopping_reason`), and `instructional_reasoning.continue_consolidate_release_or_shift`.
- **Decision criteria (authoritative, from the engine):** end the cycle when the objective is achieved, sufficient
  developmental movement has occurred, another domain has become primary, continued interaction yields diminishing
  returns, or the learner asks for independence. **Two MANDATORY stops:** (a) *independence request* → stop/consolidate,
  `stopping_reason="student requests independence"`; (b) *diminishing returns on a target* → consolidate_and_return, never
  re-teach an absorbed target. Calibration guard: intervention must be proportional (no over/under-teaching, no unmotivated
  target-shifting).
- **Implements:** Milestone engine M11 stopping/consolidation rules (SYSTEM_MESSAGE "STOPPING RULES").
- **Branch:** `continue` → Stage 3 (new cycle, re-selects target at Stage 2 as needed); `stop`/pause → Stage 7.

### Stage 7 — Session Closure
- **Purpose:** consolidate and leave a resumable state.
- **Summarize:** progress made, remaining work, next recommendation.
- **Persist:** the writing (draft), instructional history (turns), current target, unresolved issues, recommended next step.
- **Output:** a resumable developmental state.
- **Learner:** may pause/leave at any time.
- **Compass:** consolidates the gain; does not force completion.
- **Teacher:** (future dashboard) can read the persisted state.
- **Implements:** durable `Session` in `db.sessions` (turns/telos/theory/revision_history/origin_representation);
  `assignment_sessions.writing_session_id` links back for resume; `GET /sessions/{id}` and
  `GET /sessions/{id}/revision-history`. NOTE: an explicit end-of-session **recap object** is not yet emitted (see Gaps).

---

## 3. TRANSITION TABLE

| Transition | Entry criteria | Exit criteria | Required info | Optional info | Failure / missing-info handling |
|---|---|---|---|---|---|
| **→ 1 Orientation** | any entry event | a representation exists | assignment OR draft OR feedback OR prior session | learner goal, teacher component | if nothing usable: stay in Question Loop and elicit |
| **1 → 2** (handoff readiness gate) | representation built | `assess_handoff_readiness.ready == true` | ≥1 essential/important scaffoldable demand + assignment ≥4 words | edited summary, chosen goal, draft | **not ready → do NOT open workspace**; return ONE `clarifying_question`; remain in Stage 1 |
| **2 → 3** | a representation is ready | `primary_target` set | current representation / draft; retrieved KB element | teacher/learner selected component | if no clear target: engine defaults meaning-first (Purpose/understanding-the-task) |
| **3 → 4** | one invitation issued | learner submits a turn | the invitation | — | if learner is silent: session pauses (Stage 7); no auto-progress |
| **4 → 5** | learner turn received (non-empty) | `DevelopmentalTheory` produced | learner performance; prior theory | prior invitation, draft_before | empty content → rejected (400); if reasoning fails, turn `status=failed`, learner re-submits |
| **5 → 6** | interpretation produced | `cycle_status` set | `instructional_reasoning`; movement evidence | revision record | none (decision always computed) |
| **6 → 3** (continue) | `cycle_status == continue` | new invitation | current developmental state | postponed opportunities | avoid loops: MANDATORY diminishing-returns stop overrides continue |
| **6 → 7** (stop/pause) | `cycle_status ∈ {consolidate_and_return, stop}` OR learner leaves | state persisted | full session state | recommended next step | independence request forces this transition |
| **7 → 1/2** (resume) | learner returns / re-enters | prior session loaded (no duplicate) | `writing_session_id` (or localStorage `dws_session_id`) | new goal/draft | if link/session missing: start a new session from the representation |

---

## 4. RESPONSIBILITY MATRIX

| Stage | Learner | Compass (engine/UI) | Teacher (when applicable) |
|---|---|---|---|
| 1 Orientation | state task / paste draft / pick goal / correct summary | extract demands, assess adequacy, surface open questions (don't interrogate) | supply assignment, purpose, required component |
| 2 Target Selection | may choose a start point | diagnose all, pick ONE, defer rest, record rationale | selected component honored first |
| 3 Invitation | — | one purpose/reader-connected invitation; no answers | — |
| 4 Performance | do the substantive work | wait | — |
| 5 Interpretation | — | diagnose movement/control/misconception (no scores) | — |
| 6 Decision | may request independence | continue/±support/redirect/retarget/conclude; honor mandatory stops | — |
| 7 Closure | may pause/leave anytime | consolidate + persist resumable state | (future) read persisted state |

Roles never blur: **the learner performs the intellectual work; Compass scaffolds and never composes; the teacher frames
purpose and constraints.**

---

## 5. DEVELOPMENTAL RHYTHM (invariant)

```
Orientation → Shared understanding → One instructional focus → Developmental invitation →
Learner work → Interpretation → Instructional decision → (repeat cycle | conclude) → Resumable state
```

Every future feature MUST express itself as some subset/instance of this rhythm — never as a parallel instructional
process. If a feature needs "teach," it enters at Stage 2–6 of a writing session; if it needs "understand the task," it
enters at Stage 1; it never invents its own invitation/interpretation/decision logic.

---

## 6. MAPPING TO CURRENT IMPLEMENTATION

| Stage | Performed by |
|---|---|
| 1 Orientation | Question Loop (`assignment_representation.py`, `/api/assignment/*`), `AssignmentSession`, `assess_handoff_readiness`, `build_handoff`, `GET /assignment/sessions/{id}/handoff`, `BeginWorkingModal` |
| Bridge (1→2) | `POST /sessions/from-representation`, `_select_initial_component`, `_map_component_to_kb`, `_compile_representation_notes`, `Session.origin_representation` |
| 2 Target Selection | Milestone engine M11 `scaffolding_control`; KB: `canonical_writing_model.json` (domain) + `instructional_objects.json` (element) via `get_relevant_instructional_objects` |
| 3 Invitation | `_run_reasoning` → `Intervention`; rendered as coach `Turn` in `StudentWorkspace.jsx` |
| 4 Performance | `POST /sessions/{id}/interact` (`DRAFT_KINDS`), draft canvas + autosave |
| 5 Interpretation | `_run_reasoning` → `DevelopmentalTheory.instructional_reasoning`; `_record_revision` → `Session.revision_history` |
| 6 Decision | Milestone engine M11 stopping/consolidation rules (`cycle_status`, `stopping_reason`) |
| 7 Closure / Resume | `db.sessions` persistence, `GET /sessions/{id}`, `GET /sessions/{id}/revision-history`, `writing_session_id` link, localStorage `dws_session_id` |
| Developmental target vs support | `DEVELOPMENTAL_TARGET_ID="high-school-graduate"` (engine-level) + grade support profiles (`grade-9`, seeded) |
| Teacher framing | `TeacherConfiguration`, `create_session_from_config`, grade profiles |

---

## 7. GAP ANALYSIS (no redesign — status only)

| Stage | Implemented | Partial | Missing | Redundant |
|---|---|---|---|---|
| 1 Orientation | ✔ assignment & draft entry, readiness gate, editable summary | teacher-feedback & selected-component entries (adapter architected, not wired) | dedicated "prior-session/goal-only" entry UI | Question Loop's own "Continue to Knowledge" stub (Sprint-2 placeholder) |
| 2 Target Selection | ✔ engine chooses one target with rationale | KB hint tags loosely mapped (cosmetic); teacher-facing rationale is boilerplate | per-case, draft-specific "why this target" for teachers | soft bridge suggestion overlaps engine choice (harmless — engine is authoritative) |
| 3 Invitation | ✔ single, purpose/reader-connected invitation | — | explicit UI cue to "make the change in the draft" (describe-vs-do risk) | — |
| 4 Performance | ✔ interact + draft persistence | describe-in-chat vs edit-in-draft can diverge | detection of "described but not performed" | — |
| 5 Interpretation | ✔ full reasoning + revision_history | — | surfacing movement/control to learner/teacher in plain language | — |
| 6 Decision | ✔ cycle_status + mandatory stops | stuck-learner concreteness escalation (repeat "I don't know") | benchmarked escalation cases (engine frozen — needs 66-case additions first) | — |
| 7 Closure | ✔ durable, resumable state | resume UX proven but no explicit closure/recap object | end-of-session **recap** (progress / remaining / next step) as a stored artifact | — |

---

## 8. FUTURE INTEGRATION POINTS (reuse this lifecycle — no parallel processes)

Each future capability plugs into named stages; none creates its own invitation/interpretation/decision logic.

- **Knowledge Loop** — a Stage-1 Orientation variant that enriches the representation with *content the learner needs*
  (source material, prior knowledge). It hands off through the SAME bridge (`from-representation`-style) into a writing
  session; the engine (Stages 2–6) does all teaching. It must NOT contain its own coaching engine.
- **Reading Loop** — Stage 1 + a reading-specific writing session: same Invitation→Performance→Interpretation→Decision
  cycle with reading elements from `instructional_objects.json`. Reuses Stages 2–7 unchanged.
- **Teacher Dashboard** — a *read* surface over Stage 7 persisted state (`db.sessions`, `revision_history`,
  `origin_representation`, `primary_target`, `cycle_status`). Adds no instructional logic. Write path = existing
  `TeacherConfiguration` (Stage 1 framing).
- **Revision Analytics** — aggregates `Session.revision_history` (`GET /sessions/{id}/revision-history`); a Stage-5/7
  reporting view, not a new interpretation engine.
- **Resume Session** — the 7→1/2 transition: load by `writing_session_id`/`dws_session_id`, re-enter at Stage 2 with prior
  developmental state; no duplicate session.
- **Component-specific entry** — Stage 1 with `learner_selected_goal`/`teacher_selected_goal` pre-set; Stage 2 honors it
  (teacher>learner>engine). Already supported by `from-representation`.
- **Teacher-feedback entry** — Stage 1 seeds the representation/telos from feedback text (provenance `explicit_teacher`);
  Stage 2 selects the target implied by the feedback. Adapter shape already accepts it; UI wiring is the only gap.

---

## Non-negotiables
1. There is ONE instructional engine (Milestone M1–M14) and ONE session rhythm. Future loops are Orientation/entry
   variants that hand into it — never parallel engines.
2. The engine, its system prompt, and the 66-case evaluator are FROZEN. Any change to Stage 2/3/5/6 behavior requires a
   separate, benchmarked engine task (add cases first).
3. Success = increased learner control over one meaningful aspect of writing — measured, not assumed; a finished artifact
   is neither required nor sufficient.
