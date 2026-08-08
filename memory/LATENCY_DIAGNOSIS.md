# Compass P0 Latency Diagnosis (2026-06) — MEASURED, read-only. STOP before rewrite.

## Central question, answered
**Do we have a slow Compass, or a fast Compass inside a slow development environment?**
→ **We have a genuinely slow Compass RUNTIME.** Development-environment overhead on the
backend critical path is **0.01s** — effectively zero. The latency is real production cognition.

## Method
Read-only instrumentation (`backend/tests/latency_profile.py`): monkeypatched
`LlmChat.send_message` to time every LLM call, then drove ONE representative learner turn
through the REAL engine `functional_v3.run()` for each mode. No production code changed.
Non-LLM time = `total run() − Σ(LLM calls)` = state load + audit writes + DB persistence +
all deterministic Python.

## Measured per-turn breakdown (backend `run()` only)

| Mode | Call 1 `fn-sel` (DCO) | Call 2 | Call 3 `contract-judge` | non-LLM | **TOTAL** |
|---|---|---|---|---|---|
| Conceptual (thin→develop) | **76.39s** · out 32,415 ch | rp5-dlg 6.22s · out 892 ch | 0.97s | 0.01s | **83.59s** |
| Structural (sprawl→selection) | **94.78s** · out 41,240 ch | rp5-dlg 8.18s · out 1,222 ch | 1.45s | 0.01s | **104.42s** |
| Sentence Craft (complete→SC) | **91.35s** · out 38,516 ch | sentence-craft 11.94s · out 4,946 ch | 1.07s | 0.01s | **104.37s** |

Models: `fn-sel` = DCO = **claude-haiku-4-5** (`SEL_MODEL`, `max_tokens=64000`);
`rp5-dlg` / `rp5-close` = coaching = **claude-sonnet-4-6** (`DLG_MODEL`);
`contract-judge`, `sentence-craft`, `dco-tail` = haiku.

## A vs B — the required separation
- **B. Development-environment latency = ~0.00s.** state load, `_write_audit` DB writes,
  deterministic controllers, persistence/finalize together = **0.01s** per turn. The Developmental
  Cognition Object (DCO) is NOT a dev-only process — it runs on every production learner turn.
  So the "dev mode adds ~48s" hypothesis is **FALSE for the backend engine**.
- **A. Production Compass runtime = essentially the whole number (83–104s).** Of that, the single
  DCO call (`fn-sel`) is **91–95% of every turn**.

Against product thresholds (≤10s desired / >15s degraded / >20s unacceptable): **every mode is
4–10× over the unacceptable line, and the DCO call alone blows past it.**

## Root cause (specific)
The DCO call is slow because it **GENERATES an enormous structured JSON output**
(**32,000–41,000 characters ≈ 8,000–10,000 output tokens**) every turn. Output-token generation is
the dominant LLM latency factor; input (~34k char prompt ≈ 8.5k tokens) is cheap by comparison.
The coaching call (small output, 892–1,222 ch) is only 6–8s; contract-judge ~1s; SC cognition ~12s.

### Why the DCO output is so large — and why most of it is wasted on the learner path
- The DCO OUTPUT schema requests **~68 fields** (top-level + nested): e.g. `constructible_whole_map`,
  `nodes`, `integrated_instructional_problem_space`, `developmental_possibilities`,
  `coordinative_capacity`, `effectance_risk`, `local_instruction_constraints`,
  `likely_cost/value_of_further_instruction`, `learner_orientation`, `instructional_horizon`, …
- The engine's **deterministic controllers consume only ~16 fields**: `structural_load_analysis`
  (+ `central_communicative_movement`, `current_structural_work`, `secondary_trajectories`,
  `competing_structural_work`, `redundant_structural_work`, `structural_load_status`,
  `structural_pruning_needed`, `confidence`), `learner_relative_sufficiency`,
  `task_relative_adequacy`, `timely_success_status`, `communicative_capacity`, `completion`,
  `learner_orientation`, `evidence`.
- The **coaching call does NOT receive the raw DCO** — `generate_dialogue(structure, obj, status,
  structural_scaffold, selection_phase)` gets only a small *extracted* scaffold (built in `run()`
  from the consumed fields). So ~48 of the 68 DCO fields are **pure developer-facing calibration
  output that no learner-facing consumer reads** — yet they cost the majority of the 76–95s.

This is the true bridge to the "Developer" hypothesis: the DCO **call** is production, but a large
fraction of its **output (and therefore its latency)** is developer-facing calibration the learner
turn never uses. `functional_v3.py:2143` even labels this object "DEVELOPER-FACING".

## Critical-path shape (per mode)
Sequential, 3 LLM calls each; genuinely serial (each waits on the prior):
1. `fn-sel` (DCO, haiku, ~8–10k out tokens) — **the bottleneck**
2. coaching (`rp5-dlg` sonnet) OR, on SC turns, `sentence-craft` (haiku); depends on DCO output
3. `contract-judge` (haiku) — depends on the coaching invitation
No accidental fan-out beyond this; SC does NOT stack an extra cognition — `sentence_craft_cognition`
runs INSTEAD of coaching on the SC branch (verified: SC turn had fn-sel + sentence-craft + judge, not
fn-sel + dco-tail + coaching + SC). `dco-tail` (recovery) did not fire in these runs.

## Pre-"Developer" comparison — limitation
Git history is 69 auto-generated squash commits with no semantic messages, so a precise
commit-level diff to "the last fast pre-DCO version" is not recoverable from history. But the
architectural evidence is conclusive on its own: a 68-field, ~8–10k-output-token cognition JSON on
the critical path is what a fast pre-DCO Compass did not have. Recovering speed = shrinking that
output, not removing developmental function.

## Recommendations (ranked; NOT yet implemented — awaiting review)
- **R1 — Slim the DCO OUTPUT schema to consumed fields only.** [HIGHEST leverage · LOW–MED risk]
  Emit only the ~16–20 fields the deterministic controllers + extracted coaching scaffold read; drop
  the ~48 developer-only calibration fields from the per-turn output. Est. output 8–10k → ~1.5–2.5k
  tokens → **DCO ~80s → ~15–25s; total turn → ~25–35s**. Risk is LOW-MED because downstream consumers
  already read only a defined subset (coaching never sees the raw DCO). Must re-run deterministic
  regression + a few live turns to confirm controller decisions + coaching quality unchanged.
- **R2 — Split cognition: fast learner-critical DCO (every turn) + deferred developer-calibration
  cognition (dev/inspection only, off the learner critical path).** [HIGH leverage · MED risk]
  Directly realizes the requested production-vs-development separation and preserves full
  developer-facing calibration for when it's actually needed (dev panel / test harness), not per
  learner turn. Larger change than R1; do after R1 if further headroom is needed.
- **R3 — Cap/target DCO output length.** [LOW risk] `max_tokens=64000` doesn't cause latency (it's a
  ceiling, not a target) but permits unbounded generation; a slimmer schema (R1) is the real cap.
- **R4 — Parallelism: little available.** The 3 calls are genuinely serial (coaching depends on DCO;
  judge depends on coaching). Not a meaningful lever.
- **R5 — Faster model isn't the lever.** `fn-sel` is already haiku (a fast model); OUTPUT SIZE, not
  model choice, is the cost. Streaming coaching would help perceived latency later but coaching is
  only 6–8s. Deprioritize.

## What this does NOT recommend
Do NOT weaken the Constitution, Episode Target, sufficiency/load/structural-selection logic, one-
operation-per-turn, scaffolding, or Sentence Craft. The fix is to stop GENERATING developer-only
cognition detail on the learner critical path — not to reduce developmental judgment.

## Definition of done for THIS task: MET
Measured evidence answers "why slow now": a per-turn ~8–10k-token developer-facing DCO JSON on the
serial critical path (91–95% of every turn); dev-environment overhead ≈ 0. Ranked, behavior-aware
recommendations provided. **STOPPING here for review before any major architectural change.**
