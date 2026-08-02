# Compass Governance Implementation v1 — Stage-2 Decomposition (Implemented + Validated, 2026-06)

> Executable form of the canonical `COMPASS_GOVERNANCE_ARCHITECTURE.md`. Implemented entirely in `backend/triage_experiment.py`; the frozen `SYSTEM_MESSAGE` is byte-for-byte unchanged (verified). SYSTEM_MESSAGE remains the authoritative source of Layers 1–2; the focused directive only FOREGROUNDS those invariants and makes Layer 3 conditional.

## What was built (all in `triage_experiment.py`)
- **Explicit L1–L5 governance tagging** in comments + generated prompt-section headers, traceable to the canonical architecture.
- **L1 Constitutional + L2 Policy = always-govern core.** The focused directive opens with the mandated non-supersession disclaimer ("This directive narrows the diagnostic work required for the current route. It does not replace, revise, weaken, or supersede any constitutional commitment or developmental policy in the governing SYSTEM_MESSAGE.") and foregrounds the invariants (anti-coauthoring, learner ownership, answer-the-assignment, honor teacher purpose, one target, one invitation, restraint, no scores, stopping rules, function-before-convention, timely inside→outside). Kept short so the always-on core GOVERNS the decision without recreating latency (`MIN_SAFETY_SET`).
- **L3 Diagnostic Reasoning = conditional per route**, driven by `ROUTE_LENS_MAP` — the single implementation source of truth (pure + unit-testable). `resolve_route_activation()` derives active/dormant lenses, permitted moves, new-target permission, consolidation/fading permission; `select_content_lens()` picks one content lens (M7/M8/M9/M10) by triaged dimension for reader/task routes; M13 auto-activates on a prior draft; `prev_target_status` overrides (`unchanged`→no new target, `resolved`→consolidation).
- **Anti-suppression fallback.** The focused pass may set `route_fallback_required` + `route_fallback_reason` when the route cannot contain the actual (foundational) problem; the pipeline then escalates to the full frozen engine (`path="route_fallback_full"`). Route may NOT hide a foundational problem.
- **Candidate deliberation.** Directive requires EXACTLY TWO internal candidates (down from 2–3), one selected; candidates stay internal.
- **L4/L5** behavior unchanged; tagged only.
- **Unit tests:** `backend/tests/test_governance_decomposition.py` — 12/12 pass (route coverage, lens partition, prev-target overrides, no-competing-constitution).

## Validation — full 66-case Compare-Two-Runs vs frozen baseline `fd0dec0c`
Governance v1 run: `fab70c01-1cdb-4bc5-b604-4a3f7849c633` (label "Governance v1 (Stage-2 decomposition)"). Judged on governing behavior, not textual similarity. Report: `test_reports/governance_v1_deliverable.json`; subset gate: `test_reports/governance_v1_subset.json`.

| Metric | Exhaustive `fd0dec0c` | Triage v4 `532b8231` | **Governance v1** |
|---|---|---|---|
| Verdicts (pass/partial/fail) | 58 / 8 / 0 (87.9%) | 57 / 9 / 0 (86.4%) | **55 / 11 / 0 (83.3%)** |
| Anti-coauthoring (focus=writing) | 74/74 | — | **74/74 (100%)** |
| Constitutional-unsafe cases | — | — | **0** |
| Over-narrowed cases | — | — | **0** |
| Latency median /turn | 64.7s | 36.0s | **40.4s** |

- **Decision equivalence:** 52/66 same target (78.8%). 14 divergences: **3 triage_BETTER** (TC15, TC35, TC65 — improved routing / inside-outside correction), **11 equivalent_but_different** (evaluator ambiguity, not defects), **0 exhaustive_better, 0 triage_unsafe**.
- **Fallback:** foundational fallback fired 1× (reliable, rare = 1.4%); route-fallback mechanism present (0 fires — no severe mismatch in the suite).
- **Routing spread:** all 6 routes exercised (inside_out 47, outside_in 10, convention 9, stall 6, support_fading 1, transfer 1).
- **TC15/TC30/TC50/TC61 (watch cases):** TC15 = triage_better; TC30/TC50/TC61 = same-target, verdict `partial` — identical to the frozen exhaustive baseline (pre-existing frozen-engine weaknesses, NOT introduced by the decomposition; confirmed identical Stage-1 routing to triage v4).

## Success-criteria status (9 of 10 met)
✓ zero constitutional regressions · ✓ zero anti-coauthoring regressions · ✓ zero unsafe cases · ✓ no systematic over-narrowing · ✓ reliable foundational fallback · ✓ defensible L3 routing (3 better, 0 worse) · ✓ teacher purpose/assignment preserved (TC35 improved) · ✓ judged on governing behavior · ✓ streaming path preserved (focused invitation is what is parsed/finalized; rare route-fallback documented as superseding the stream).
✗ **"latency meaningfully below triage v4"** — Governance v1 is **37.5% below the exhaustive baseline (64.7s→40.4s)** but **~4.4s ABOVE triage v4 (36.0s)**. Cause: the richer governed directive (explicit L1–L5 foregrounding + route→lens block + anti-suppression clause, ~1050 added input tokens). This is the deliberate cost of auditable governance; per the architecture doc this is "an enduring architecture, not a latency fix." OPEN: if pure speed is prioritized over explicit foregrounding, the directive can be trimmed to recover the ~4s.

## Files
- `backend/triage_experiment.py` — LENS, MIN_SAFETY_SET, ROUTE_LENS_MAP, DIMENSION_LENS_KEYWORDS, select_content_lens, resolve_route_activation, build_focused_override, route-fallback escalation in run_triage_pipeline(+streaming).
- `backend/tests/test_governance_decomposition.py` — pure unit tests.
- `backend/validate_governance_subset.py` — 12-case regression gate; `backend/analyze_governance_v1.py` — full Compare-Two-Runs analyzer (reads GOV_RUN env).
