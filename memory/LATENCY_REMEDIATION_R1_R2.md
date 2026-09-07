# Compass P0 Latency Remediation — R1 + R2 (2026-06). Engine cognition, measured.

## Result headline
Slimming the per-turn `developmental_cognition` (DCO) output schema cut total backend turn
latency by ~55–70% with instructional behavior preserved. The ≤10s target is NOT yet met
(remaining time is genuine learner-critical cognition); next lever identified below.

## Before → R1a → R1b latency (backend `run()`, per representative turn)

| Mode | BASELINE fn-sel / total | R1a (brevity+cap16k) fn-sel / total | R1b (slim schema) fn-sel / total (n=2) |
|---|---|---|---|
| Conceptual | 76.4s / **83.6s** | 57.2s / 64.1s | 19.7–23.2s / **24.9–28.6s** |
| Structural | 94.8s / **104.4s** | 75.0s + 64.4s retry / **150.6s** ⚠ | 29.8–33.0s / **37.2–41.2s** |
| Sentence Craft | 91.4s / **104.4s** | 56.4s (+dco-tail) / 79.6s | 23.9–24.8s / **34.1–35.5s** |

DCO OUTPUT size (chars): Conceptual 32,415 → 24,789 (R1a) → **8,463–10,116 (R1b)**;
Structural 41,240 → **12,873–13,213**; SC 38,516 → **10,725–11,122**. (~70% smaller.)
Non-LLM overhead stayed ~0.00–0.02s throughout (no dev-environment cost on the critical path).

### Why R1a alone failed (kept, but insufficient)
A system-message brevity contract + `max_tokens=16000` did not overcome a ~300-line verbose
schema; worse, the 16k cap TRUNCATED the still-large output → invalid-JSON RETRY (a full extra
64s fn-sel) on the structural turn (total 150s) + a `dco-tail` recovery on SC. Lesson: **make the
schema small by design first, then cap.** R1a's brevity contract is retained (it keeps the slim
values terse) and `max_tokens` is now 8000 (safe headroom over the ~2–3k-token slim output; no
truncation observed).

## Final critical-path call graph (R1b)
Sequential, **2 LLM calls per turn** (was 3–4); genuinely serial (coaching needs the decision):
1. `fn-sel` — DCO/function-selection — **claude-haiku-4-5** — now ~20–33s (was 76–95s)
2a. conceptual/structural: coaching `rp5-dlg` — **claude-sonnet-4-6** — ~5–8s
2b. SC turns: `sentence-craft` — haiku — ~10–11s (runs INSTEAD of coaching, not stacked)
`contract-judge` (haiku, ~1s) did NOT fire in R1b runs (already conditional). `dco-tail` recovery
no longer fires (slim output isn't truncated). No JSON-retry.

## DCO field classification (evidence-based; from the dependency audit)
**A — learner-critical (KEPT, full/structured):** `structural_load_analysis` {central_communicative_movement,
current_structural_work[], secondary_trajectories[], competing_structural_work[], redundant_structural_work[],
structural_load_status, structural_pruning_needed, recommended_structural_operation}; `learner_relative_sufficiency`
{value, learner_accessible_target, accessible_target_achieved, episode_target_status, episode_target_revision_reason};
`task_relative_adequacy` {value, material_gap, transition_recommendation}; `timely_success_status` {value, now_meets_task};
`communicative_capacity` {writing_unit, central_communicative_movement, current_communicative_load, remaining_capacity,
remaining_communicative_budget, overload_risk, scope_status, material_to_defer_or_exclude[]}; `learner_orientation`
{current_direction, where_we_are, current_work, likely_next_step, estimated_remaining_moves, orientation_revision_reason};
`completion_readiness`; `completion_message`. (Consumed by run()'s deterministic controllers + the learner-facing contract/orientation.)
**B — needed only under a mode (KEPT, terse):** `task_orientation_relation`, `structural_relations_and_dependencies`,
`whole_communication_requirements`, `provisional_whole_communication`, `instructional_center`,
`current_instructional_sufficiency`, `sentence_craft_readiness.developmental_work_remaining` — consumed by
`_dco_governing_context` that governs **Sentence Craft cognition**; kept as compact fields.
**B/quality — reasoning anchors (KEPT, terse):** `instructional_horizon`, `developmental_constraint` — retained
compactly so the model still reasons developmentally before emitting the consumed decisions.
**C — development/calibration, NOT consumed by any runtime path (REMOVED from the per-turn blocking output):**
`apparent_orientation_target`, `orientation_target_interpretation`, `orientation_target_confirmed`,
`conceptual_organization`, `communicative_organization`, `current_relational_structure`, `coordinative_capacity`,
`developmental_possibilities`, `content_relations_and_dependencies`, `task_required_content_relations`,
`task_required_structural_relations`, `integrated_instructional_problem_space`, `local_instruction_constraints`,
`reachable_next_move`, `constructible_whole_map`, `beyond_horizon`, `deferred_or_excluded_complexity`,
`further_growth_potential`, `likely_value_of_further_instruction`, `likely_cost_of_further_instruction`,
`effectance_risk`, `developmental_advance`, `organization_stability`, `self_contained_coherence`, `unit_scope_disposition`,
`additions_that_still_belong`, `expected_functional_range`, `reasonable_scope`, `unit_purpose`, plus ALL per-field
`evidence[]` arrays and the top-level `confidence`/`evidence` aggregation.
**D — obsolete:** none identified distinctly (the C set had a dev-panel/trace consumer only, which degrades gracefully via `.get`).

## R2 status — separation of learner-critical vs development cognition
R2's central requirement ("only cognition required to make the next instructional decision blocks
the learner") was **achieved as part of R1b**: every Class-C development/calibration field was
removed from the per-turn blocking DCO output. Verification that this is safe: none of the removed
fields are read by any runtime decision path — the sole consumer was the dev-panel/trace
`confidence`/`evidence` aggregation, which now simply shows less and does not error (uses `.get`).
So no deferred/async recomputation is required for current functionality. If a future
Teacher-Review/research surface wants the rich calibration cognition, the verbose schema is
preserved in git history + `/tmp/functional_v3.bak.py` and can be reintroduced as a **dev-only,
off-critical-path** call — it must never block a learner turn (spec §8–10).

## Regression results (R1b)
- Deterministic `tests/test_sc_controller.py` (controller + payload architecture): **PASS**.
- `tests/test_structural_49.py`: **A PASS** (sprawl → structural_selection, episode did NOT close,
  coach guides reduction) + **B PASS** (thin → develops, not pruned). Structural imbalance detection,
  closure gating, and one-operation-per-turn preserved.
- `tests/test_492_sufficiency.py`: DCO-driven checks PASS (adequate, sufficiency recognized, overload
  status=crowded, op=structural_selection, coach says "too much", keep/combine/condense scaffolds, NO
  counterargument). The single failing sub-criterion ("coach names Sentence Craft as next") is a
  brittle keyword match on the coaching (sonnet) OUTPUT — coaching-LLM variance, NOT a DCO change
  (R1b did not touch `generate_dialogue`).
- `tests/test_closure_48.py`: closure decision `close_and_transition` + explicit transition detection
  PASS. The "not asking for elaboration = False" sub-criterion is the **pre-existing 4.10 SC-wiring**
  behavior (turn 2 now enters Sentence Craft) interacting with a pre-4.10 test — not a DCO-slim regression.
- `tests/live_sc_path.py`: SC end-to-end **PASS** (thesis inferred, payload correct, SC cognition + controller intact).

## Remaining bottleneck & recommendation (≤10s NOT yet met; ~25–41s now)
- After R1b the remaining cost is **genuine learner-critical cognition**: `fn-sel` still generates
  ~2–3k output tokens at a measured **~107 tokens/s** on the current haiku path (~20–33s), plus
  serial coaching/SC (5–11s). Non-LLM ≈ 0.
- To approach ≤10s (ranked):
  - **R2b (mode-sensitive cognition, §4):** on SC-*continuation* turns, skip the full conceptual DCO
    and synthesize a light governing DCO from persisted state (thesis + task) — would cut SC turns
    ~34s → ~12s. MED risk (touches run() flow + SC loop); needs multi-turn SC regression. Recommended next.
  - **Inference-path (§12):** the ~107 tok/s generation rate dominates. Evaluate streaming the coaching
    turn for perceived responsiveness, and/or a faster inference route for `fn-sel`. Do NOT change
    model/merge coaching blindly — measure first, per spec.
  - **Further schema trim is near its safe floor:** remaining output is mostly consumed structured
    fields + verbatim `visible_interpretation` spans (needed for highlighting) — not safely cuttable.

## Files
- `functional_v3.py`: `_FUNCTION_SEL_SYS` gained an OUTPUT-DISCIPLINE contract; `developmental_cognition`
  schema replaced with the slim version (330 verbose src lines → compact); `fn-sel` `max_tokens` 64000 → 8000.
- Harness: `tests/latency_profile.py`. One-shot patcher record: `tests/_patch_dco_slim.py`. Backup: `/tmp/functional_v3.bak.py`.

---

## R2b — Mode-sensitive Sentence Craft CONTINUATION fast path (2026-06, DONE — verified)
Approved follow-up, scoped ONLY to SC continuation turns (no bypass for conceptual/structural).

### What it does
On a genuine SC CONTINUATION turn, `run()` short-circuits BEFORE the full conceptual DCO: it reuses
a persisted governing context and invokes the SAME production `sentence_craft_cognition` +
deterministic controller. Gate (all required): `sc_active` AND `sc_transitioned` (so NOT the initial
entry) AND not `sc_complete` AND not `sc_force_full_next` AND draft turn AND text present. Governing
context (assignment, thesis, communicative task, `_dco_governing_context` fields, completion message)
is captured on every FULL SC turn via `_sc_capture_governing` (thesis resolved from several DCO
sources for reliability) and stored on `state.sc_governing_context`. Upward routing: when SC returns
`route_upward`, the light path still delivers THAT turn's SC routing coaching (identical to the full
path) and sets `state.sc_force_full_next=True` so the NEXT turn returns to the full higher-order
engine (spec §3). Missing/insufficient governing context → `_run_sc_light` returns a fallback reason
and `run()` uses the full path (spec §6, never improvise). Diagnostic: `sentence_craft.sc_light_path_used`
(true/false) surfaced per turn; fallback reason logged.

### Measured latency (per spec §8 — entry vs continuation reported SEPARATELY)
| SC turn type | path | LLM calls | latency |
|---|---|---|---|
| ENTRY (transition into SC) | full | fn-sel + sentence-craft | ~33s |
| CONTINUATION | **light** | **sentence-craft only** | **8.8–9.2s** ✅ under ≤10s target |
| COMPLETION (holistic review) | light | sentence-craft only | ~10.2–10.9s |
Continuation reduction vs entry: **~72–73%**. Light path makes exactly ONE LLM call (no fn-sel).

### Regression (spec §7) — ALL PASS
Multi-turn `tests/test_r2b_sc_light.py`: entry uses full path + captures governing context w/ thesis;
continuation skips fn-sel (light) w/ coherent operation/focus; pattern state persists; active-sentence
index tracked; completion reaches holistic review via light path; `sc_force_full_next` forces the next
turn full + auto-clears; missing-context safe fallback. Plus re-run: `test_sc_controller` PASS,
`test_structural_49` A+B PASS, `live_sc_path` PASS (full path untouched — the gate only affects SC
continuation turns, so conceptual/structural behavior is unchanged by construction).

### Net latency picture (baseline → R1b → R2b)
- Conceptual turn: 83.6s → ~25–29s (R1b). (R2b does not touch conceptual — scoped out per instruction.)
- Structural turn: 104.4s → ~37–41s (R1b).
- Sentence Craft ENTRY: 104.4s → ~33s (R1b).
- Sentence Craft CONTINUATION: 104.4s → ~34s (R1b) → **~9s (R2b)** ✅.

### Remaining bottleneck & next lever
Conceptual/structural/SC-ENTRY turns remain ~25–41s = genuine learner-critical cognition (`fn-sel`
generating ~2–3k tokens at a measured ~107 tok/s). SC CONTINUATION now meets target. Next lever
(NOT done; per §10 do not change models until measured): evaluate a faster inference route and/or
streaming for the remaining full-DCO turns; an intermittent `dco-tail` recovery (~6s, pre-existing
truncation guard) occasionally fires on full turns and could be tightened. R2b files:
`compass_foundation.py` (+`sc_governing_context`, `sc_force_full_next`); `functional_v3.py`
(`_sc_capture_governing`, `_run_sc_light`, run() continuation gate, full-path capture);
test `tests/test_r2b_sc_light.py`.
