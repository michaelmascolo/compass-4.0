# Compass — Latency Audit & Conditional Triage Architecture

> Deliverable for the latency workstream. The frozen `SYSTEM_MESSAGE` and all constitutional commitments are UNCHANGED. The triage path is additive and experimental (`backend/triage_experiment.py`), runs alongside the production engine, and was benchmarked against it (`backend/triage_benchmark.py`).

---

## 1. Map of the current reasoning sequence (per coaching turn)

```
POST /api/sessions/{id}/interact
  ├─ append student turn (complete) + AI placeholder (status=processing)   ~<0.2s, 1 DB write
  ├─ return Session immediately (durable — client may disconnect)
  └─ asyncio.create_task(_run_reasoning)                                   ← background

_run_reasoning  (server.py)
  ├─ DB read session
  ├─ _run_engine(session, req):
  │    ├─ STAGE A  _select_relevant_domains → 1 LLM call  (~3–5s)
  │    │     small compact-index prompt → picks 1–3 domains + sections + 1–3 instructional objects
  │    ├─ _build_prompt → assembles LARGE prompt (~20–25 KB):
  │    │     telos + compact theory + interaction summary + FULL domain data
  │    │     + instructional objects + instructional network + developmental profile
  │    │     + shared resource menu + latest draft block
  │    └─ STAGE B  reasoner → 1 LLM call  (~40–80s, ~90–93% of turn time)
  │          system = frozen SYSTEM_MESSAGE
  │          OUTPUT = one very large structured JSON: the ENTIRE DevelopmentalTheory
  │          (M6 communicative_purpose, M7 paragraph_function, M8 evidence_function,
  │           M9 coherence_function, M10 conclusion_function, M11 scaffolding_control,
  │           M12 reader_construction, M13 revision_development, M14 integration_calibration,
  │           instructional_reasoning[12 fields]) + candidate_invitations + selected_invitation
  │           + intervention + developmental_profile_update + observed_reorganization
  ├─ _finalize_turn → fill placeholder, snapshot theory_history, merge profile,
  │     append interaction, (NEW) record revision_history for substantive revises
  └─ DB write (turns, telos, theory, theory_history, interactions, profile, revision_history)

Frontend polls GET /sessions/{id} every 1.5–2.5s until the AI turn is complete.
```

**Two model calls per turn.** STAGE A is cheap; **STAGE B dominates** (measured 54s of a 58s turn in the earlier audit; benchmark below shows ~55–70s).

---

## 2. Evidence of redundant work (why STAGE B is slow)

The bottleneck is **output generation**, not input. STAGE B is instructed (by the frozen prompt + JSON schema) to **reconstruct and serialize the entire developmental model every turn**, even when the immediate task is a single narrow coaching decision:

- **Full-model reassessment every turn.** All 10 framework lenses (M6–M14) + the 12-field `instructional_reasoning` + `integration_calibration` are emitted on every turn, regardless of what actually changed. The M11 controller already selects **exactly ONE** target — so 9 of the 10 lenses' detailed output is diagnostic scaffolding the turn does not act on.
- **Repeated analysis of unchanged text.** On a `revise` turn that touches one paragraph, the engine still re-derives purpose, paragraph function, evidence, coherence, conclusion, reader model, etc. for the whole piece.
- **Generation of unused structured output.** The R3 preview experiment already proved this: trimming ONLY the serialized fields (reasoning unchanged) cut reasoner latency **25–35%** with no change to the decision. That is direct evidence that a large fraction of STAGE B time is spent *writing JSON the turn never consumes*.
- **No early exit.** There is no mechanism to stop once a decisive route is known (e.g., a stalled learner, an unresolved prior target, a clearly-local sentence problem). The single exhaustive pass always runs to completion.
- **Inside-out vs outside-in is implicit.** The choice is embedded in the big reasoning pass rather than decided cheaply up front, so both branches are effectively "considered" inside one long generation.

STAGE A is not redundant, but it can be **folded into triage** (triage already names the relevant instructional objects), removing one call from the fast path.

---

## 3. Proposed conditional triage architecture

Two stages around the **unchanged** frozen engine. New tiny `TRIAGE_SYSTEM_MESSAGE`; STAGE 2 keeps the frozen `SYSTEM_MESSAGE` verbatim (all constitutional/anti-coauthoring rules intact) and only **narrows scope + trims output**.

**STAGE 1 — Rapid Instructional Triage** (new, ~3s, ~130 output tokens)
Input = a compact, *incrementally-maintained* learner state (NOT the transcript): assignment purpose, active target + prior mode, known strengths, unresolved needs, and the current draft + previous draft (the revision delta). Output = the 6 triage decisions: what changed, prior-target status (resolved/partial/unchanged/worse), learner state (engaged/stalled/confused/finished), instructional route (stall / inside-out / outside-in / convention / transfer / fade), inside-vs-outside, `foundational_problem?`, the single highest-leverage dimension, the relevant instructional objects, and a confidence. Probabilistic: a plausible focused hypothesis is preferred over exhaustive certainty.

**Early-exit routing (code, between stages)**
- `foundational_problem = true` → fall back to the **full exhaustive engine** (broad reassessment is genuinely warranted).
- `learner stalled` → stall support on the current target; do not open a new one.
- prior target `unchanged` → keep the same target; do not search for a new one.
- prior target `resolved` → assess fade / advance.
- intention already clear → do not linger inside-out; test reader/task/convention (routing invariant).

**STAGE 2 — Focused Analysis** (frozen SYSTEM_MESSAGE, ~30s, small output)
Loads only the triaged dimension's canonical data + the relevant span + prior target/response, and emits a **trimmed** payload (invitation + scaffolding_control[one target] + intervention + instructional_reasoning + revision_development when applicable). Same governed reasoning, one target, anti-coauthoring — just scoped.

**Incremental student model.** Reuses the now-persisted `developmental_profile` + `revision_history` + compact `theory` so subsequent turns narrow reasoning instead of rebuilding from the transcript.

Net: fast path = **triage (replaces STAGE A) + focused STAGE B with small output**. Foundational path = triage + full engine (a small triage tax for a guaranteed-correct broad pass).

---

## 4. Benchmark results

EXHAUSTIVE frozen engine vs TRIAGE experimental, same starting session per case; representative set TC01/TC03/TC07/TC08/TC25/TC30; decision equivalence LLM-judged. Raw: `test_reports/triage_benchmark.json`.

| Metric | Exhaustive | Triage | Δ |
|---|---|---|---|
| Avg latency / turn | **64.7 s** | **36.5 s** | **−43.6%** |
| Avg output tokens | 2,990 | 1,743 | −41.7% |
| Model calls / turn | 2 (A+B) | 2 (triage+focused) | same count, far smaller STAGE-2 output |
| Same target | — | **4 / 6** | |
| Materially different decision | — | 2 / 6 | both judged **triage-better** |
| Anti-coauthoring (`focus=writing`) | 6/6 | **6/6** | preserved |

Per-case latency: TC01 61→43s · TC03 67→35s · TC07 70→35s · TC08 67→37s · TC25 59→32s · TC30 65→38s.

## 5. Latency reduction achieved

**−43.6% wall-clock per turn** (64.7 s → 36.5 s), from **−41.7%** fewer generated output tokens. The reduction comes entirely from STAGE 2 serializing only the triaged dimension instead of the full 10-lens model — the exact lever R3 validated on the preview, now generalized. STAGE 1 triage costs ~3 s (≈130 tokens) and replaces the STAGE-A selector, so the fast path adds no net call. Further headroom (not yet taken): a faster/cheaper model for STAGE 1; streaming the STAGE-2 invitation token-stream to the client for a lower *time-to-first-word*; caching unchanged-context between revise turns.

## 6. Cases where triage produced a materially different instructional decision

Only 2 of 6, and the independent LLM judge rated **triage better in both** (equivalent in the other 4). Neither is a regression:

- **TC07 (strong thesis — must not be over-taught).** Exhaustive redirected to body-paragraph drafting (`consolidate`); triage kept the writer stress-testing the claim's arguability against a skeptic (`invite_only`, outside-in). The expected behavior is "light / consolidate or move forward" — triage's restrained `invite_only` is the more conservative, on-spec move.
- **TC30 (returning student with independent control; expected target = evidence/explanation, NOT thesis).** Exhaustive pulled to "generate a body-paragraph claim" (structural); triage targeted **grounding the argument in evidence and explanation** — matching the expected target and the developmental-profile growth edge. This is precisely the known residual weakness **W-D / TC30** (engine defaults to thesis/structure over the profile's evidence edge) — **triage corrected it**, because the incremental student-state summary surfaced the profile's growth edge to the triage decision directly.

**Conclusion.** Equivalent-or-better instructional judgment at **~44% lower latency** on a representative set, with anti-coauthoring and one-target discipline intact and one known weakness improved. Recommended next step (pending approval): wire the triage path into production behind a per-session flag, keep `foundational_problem → full-engine` fallback, and run the full 66-case suite through the frozen evaluator (Compare-Two-Runs vs `fd0dec0c`) before making it the default.

---

### Files
- `backend/triage_experiment.py` — experimental triage engine (additive; frozen SYSTEM_MESSAGE untouched).
- `backend/triage_benchmark.py` — exhaustive-vs-triage benchmark harness.
- `test_reports/triage_benchmark.json` — full per-case results + aggregate.

---

# PART II — Production integration + full 66-case validation (deliverable)

## Production integration behind a per-session flag (DONE)
- `Session.reasoning_mode` ∈ {`exhaustive` (default, unchanged frozen path), `triage_experimental`}. `Turn.reasoning_path` records which path produced each AI turn (`exhaustive_full` | `triage_focused` | `foundational_fallback_full`) — never a silent switch. Set at create (`SessionCreate.reasoning_mode`) or flipped via `PATCH /api/sessions/{id}/reasoning-mode`. Dispatch in `_run_reasoning`; triage path = rapid Stage 1 + early-exit rules + inside/outside classification + focused Stage 2 + `foundational_problem → full frozen engine` fallback. Verified live (session → interact → poll → `reasoning_path=triage_focused`).
- **Shadow comparison**: the test harness (`_harness_run_turn`) honors `reasoning_mode` and captures, per turn, the full comparison payload (route, target, span, support level via intervention.type, inside/outside, invitation, next act, anti-coauthoring focus, fallback flag, stage latencies, token counts). `TestRunRequest.reasoning_mode` runs the whole suite in either mode and stores a normal `test_run` → **Compare-Two-Runs** compatible with the exhaustive baseline `fd0dec0c`.

## Full 66-case results (triage run `f9d4e3a7` vs exhaustive `fd0dec0c`, frozen evaluator)
- **Verdicts** — exhaustive 58 pass / 8 partial / 0 fail (87.9%); triage **49 pass / 16 partial / 0 FAIL / 1 error** (74.2%). **Zero fails in both.** The extra partials are almost entirely "equivalent-but-different" targets the frozen evaluator scored down (see divergence table), not constitutional failures.
- **Latency (per turn)** — exhaustive avg 64.9s / median 64.7 / p90 73.6 / max 80.6; triage avg **38.5s** / median **37.8** / p90 **42.4** / max 57.0 → **−40.7% avg, −42% p90**, tight distribution (stable across case types).
- **Latency by stage (triage)** — Stage 1 triage avg **3.9s**; Stage 2 focused avg **34.3s** (= **89%** of the triage turn). DB read/write ≈ 0.001s each (negligible). Remaining delay is dominated by the focused frozen-engine **output generation**, even trimmed.
- **Tokens** — triage output ~1.4–1.7k vs exhaustive ~3k (≈ −42%); triage prompt comparable.
- **Anti-coauthoring / constitutional** — triage **73/73** `focus=writing` (exhaustive 74/74). **Zero regressions.**
- **Fallback** — `foundational_fallback_full` fired **1/73 (1.4%)**; `triage_focused` 72. Confidence is saturated high (0.8–0.9, avg 0.9) → confidence-based fallback alone is ineffective; explicit structural triggers are needed.
- **Routing** — routes: inside_out_clarification 49, outside_in_reader_task 12, convention_instruction 6, stall_support 6. inside/outside: 56 inside / 17 outside (76% inside — a mild inside-out lean; the routing invariant helps but does not fully counter it).

## Divergence classification (22 of 65 differ; LLM-judged)
- **triage_better 9** (improved_routing 3, over_narrowing-toward-foundation 3, early_exit 1, inside/outside correction 1, missed_foundational-but-better 1) — incl. TC63 (POV correction) and TC42/TC27 (retreat to the real foundational purpose).
- **equivalent_but_different 10** (all evaluator_ambiguity) — triage chose a defensible different target (often "central claim") that the frozen evaluator scored partial; not degradations.
- **exhaustive_better 2** — TC30 & TC61 (`over_narrowing`: triage retreated to claim/generic where the live edge was evidence-interpretation).
- **triage_unsafe 1** — **TC15** (`missed_foundational`): the assignment purpose explicitly targeted transitions/relationships; triage retreated to "central claim", inventing a deficiency outside the stated purpose (a W-D teacher-purpose miss).
- Disagreement is NOT failure: 9 better + 10 equivalent + 2 worse + 1 unsafe.

## Inside-out / outside-in analysis
Classification present on every turn; 1 explicit correction (TC63) rated better; overall a mild inside-out lean (76%). No case showed inside-out persisting after intention was clearly established in a harmful way, but the "central claim" default (below) is the same root tendency.

## Root causes of the residual gap (all addressable)
1. **"Central claim / purpose-alignment" narrowing bias** — Stage 1 over-selects thesis/purpose as highest-leverage even when a downstream target (evidence-interpretation, transitions, POV) is the live edge (TC30, TC61) or the teacher purpose names another skill (TC15). This drives most extra partials + the 2 exhaustive-better + the 1 unsafe.
2. **Foundational detector under-fires** (1.4%) and can't lean on the model's saturated confidence.
3. **No Stage-2 retry** — the 1 error (TC17) was an unreadable focused-output; the exhaustive path retries once, the focused path does not.

## Recommended confidence & fallback thresholds
- Fall back to the full frozen engine when ANY: `foundational_problem=true`; the draft does not address the assignment / whole purpose unclear (explicit structural trigger, not self-confidence); triage selects claim/purpose **while a prior downstream target was unresolved**; OR the teacher purpose names a specific element that triage did not select. Confidence `<0.75` as a secondary trigger (rare given current calibration).
- Add **one Stage-2 retry** on unreadable output (parity with the exhaustive path) before failing.

## Safety-gate verdict
- ✅ zero constitutional/anti-coauthoring regressions; ✅ zero fails; ✅ stable latency win across case types.
- ⚠️ NOT met: no systematic premature narrowing (5 over-narrowings, 2 worse); no systematic foundational miss (TC15 + 1.4% fallback); teacher-purpose adherence (TC15).

## 10. RECOMMENDATION — **REVISE AND RETEST** (then enable for limited sessions)
Triage delivers a **~41% latency reduction with zero constitutional/anti-coauthoring regressions and zero fails**, and improves several known weaknesses — but it is **not yet safe as the default** because of the central-claim narrowing bias (1 unsafe + 2 worse) and an under-firing foundational fallback. Recommended path: (1) apply the 3 fixes above (curb central-claim retreat / honor explicit teacher purpose; strengthen structural foundational triggers; add Stage-2 retry); (2) re-run the 66-case suite and Compare-Two-Runs vs `fd0dec0c`; (3) if the unsafe/worse divergences clear and fallback fires appropriately, **enable triage for limited opt-in sessions** behind the existing per-session flag (already shipped, default exhaustive) before considering it the default. Next latency lever after that: **stream the Stage-2 invitation** (bookkeeping is ~0ms, so partial-result delivery alone is negligible; streaming is the real time-to-first-word win) — requires approval as a transport change.

### Files (Part II)
- `backend/server.py` — reasoning_mode flag, reasoning_path, dispatch, PATCH endpoint, harness threading.
- `/tmp/analyze_triage.py` — deliverable analyzer (kept outside the reload-watched dir).
- `test_reports/triage_66_deliverable.json` — full metrics + divergence classification.
- Runs: triage `f9d4e3a7` ("Triage 66 v2"), exhaustive baseline `fd0dec0c`.

---

# PART III — Revise-and-retest cycle (3 fixes; final result)

Three approved fixes, no other architectural change: (1) reduce central-claim narrowing bias + honor the assignment's named element at the **dimension-selection** step; (2) strengthen foundational triggering; (3) add a single Stage-2 retry for recoverable (unreadable) failures.

## Iteration log (why two retest runs)
- **v3 (`115b7491`)** — first pass of the 3 fixes. Quality up (78.8%, 0 fail, TC15 unsafe fixed, TC30 flipped to better) BUT the strengthened foundational trigger **over-fired to 68.9%** — 69% of turns fell back to the full frozen engine, erasing the latency win (avg 59.1s, only −9%). Root cause: a foundational trigger keyed on "assignment names an element and the draft is failing at it" matched nearly every case.
- **Recalibration** — moved teacher-purpose adherence entirely into **dimension selection** (fix #1) and narrowed `foundational_problem` to genuinely broad cases only (off-task / undeterminable purpose / incoherent-across-ideas; "rare").
- **v4 (`532b8231`)** — deployable result below.

## Final results — v4 (recalibrated) vs exhaustive baseline `fd0dec0c`
| Metric | Exhaustive | Triage v4 | Δ |
|---|---|---|---|
| Verdicts | 58 pass / 8 partial / 0 fail | **57 pass / 9 partial / 0 fail / 0 error** | −1 pass (statistically equivalent) |
| Pass rate | 87.9% | **86.4%** | −1.5 pts |
| Latency avg | 64.9s | **37.2s** | **−42.7%** |
| Latency median / p90 | 64.7 / 73.6 | **36.0 / 40.9** | −44% / −44% |
| Stage split | — | triage 3.8s + focused 32.9s | — |
| Anti-coauthoring | 74/74 | **74/74** | zero regressions |
| Fallback rate | — | **1.4%** (1 case) | appropriately rare |
| Errors | 0 | **0** | retry fix works (v2/v3 had 1) |

## Divergences (25 of 66; LLM-judged) — **0 unsafe**
- **triage_better 9** (TC02, TC06, TC25, TC29, TC32, TC35, TC42, TC59, TC60) — improved routing, inside/outside corrections, and catching foundational edges the exhaustive path missed.
- **equivalent_but_different 13** (evaluator ambiguity — defensible different target).
- **exhaustive_better 3** (TC07, TC17, TC22 — minor residual over-narrowing / one inside-outside call). Not systematic, not unsafe.
- **triage_unsafe 0.** The previous unsafe case (TC15) is resolved via correct dimension selection (targets idea-relationships, not thesis), not fallback.

## Safety-gate assessment (v4)
- ✅ zero constitutional / anti-coauthoring regressions; ✅ zero fails; ✅ zero errors.
- ✅ no systematic foundational miss (0 unsafe; the "missed_foundational"-tagged divergences were judged triage-*better*).
- ✅ latency win restored and stable (median 36.0, p90 40.9, tight); ✅ fallback fires rarely and appropriately (1.4%).
- ⚠️ minor residual premature-narrowing on 3 cases (TC07/TC17/TC22) — small, not systematic.

## Recommended thresholds (calibrated from v4)
- **Fallback to full engine when** `foundational_problem=true` (now narrow: off-task / purpose undeterminable / incoherent-across-ideas). Confidence is saturated high (0.8–0.9) so a confidence threshold is a weak secondary signal; the structural triggers carry it. Current fallback 1.4% is healthy — do not re-broaden it; teacher-purpose adherence is handled at dimension selection, not fallback.
- **Retry:** one Stage-2 retry on unreadable output (shipped) — eliminated all errors.

## Recommendation (per directive: do NOT auto-enable default)
Triage v4 delivers **~43% latency reduction at baseline-equivalent instructional quality** (86.4% vs 87.9%, 0 fails, 0 errors, 0 unsafe, anti-coauthoring intact). It is **safe enough to enable for limited opt-in sessions** behind the shipped per-session flag. Per your instruction, it is **not** being made the default. Before that decision, see the **Stage-2 Architecture Review** (`COMPASS_Stage2_Architecture_Review.md`): Stage 1 is functioning well (~3.8s); the residual ~33s lives in the focused Stage-2 call, which still runs the frozen SYSTEM_MESSAGE's broad multi-framework mandates internally — the next design decision is whether to factor the frozen prompt into a constitutional core + conditional diagnostic layer.

### Files (Part III)
- `backend/triage_experiment.py` — recalibrated TRIAGE_SYSTEM_MESSAGE (fixes 1–2) + Stage-2 retry (fix 3).
- `test_reports/triage_66_deliverable_v4.json` (+ `_v3`) — full metrics + divergence classification.
- Runs: v3 `115b7491`, **v4 `532b8231`** (final), exhaustive baseline `fd0dec0c`.

---

# PART IV — Streaming + limited opt-in (implemented, verified)

## Triage v4 — limited opt-in (WS1, DONE)
Per-session flag ships as the opt-in surface: `PATCH /api/sessions/{id}/reasoning-mode` or `SessionCreate.reasoning_mode`. Frontend opt-in via `?triage` (or `localStorage dws_reasoning_mode`) — sessions created in triage mode; everyone else stays on the exhaustive default. `reasoning_path` recorded per turn keeps comparison data flowing.

## Streaming the coaching invitation (WS2, DONE — perceived-latency only)
Implemented over the existing durable-polling transport (no SSE → sidesteps the 60s ingress cap). The focused Stage-2 call now uses `LlmChat.stream_message`; because `student_facing_invitation` is the first serialized field, its tokens are extracted and written to the placeholder turn (`status="streaming"`) as they generate. The frontend polls at 1.2s, auto-opens the coaching card, and renders the invitation live with a caret; background bookkeeping (full theory, analytics, revision-history, persistence) finalizes afterward (`status="complete"`) with the **identical** invitation text.
- Guard fix: `_run_reasoning` finalize + interact concurrency now treat `streaming` as in-flight (previously the streaming status tripped the "no longer processing → discard" guard).
- **Measured (live triage session):** invitation fully visible at **~8s** vs the full turn completing at **~36s** — a **~4–5× reduction in time-to-first-coaching**, with byte-identical invitation between the streamed and finalized states (decision NOT altered). Verified in-browser (`?dev&triage`): card auto-opens and renders live.
- Scope: streaming is wired for the triage focused path (invitation-first). The default exhaustive path is unchanged (its schema is not invitation-first); enabling streaming there would require reordering the frozen schema (a prompt change) — deferred to the Stage-2 refactor.

## Stage-2 decomposition design (WS3/4, DELIVERED for review — NO prompt edits)
`COMPASS_Stage2_Decomposition_Design.md` classifies every SYSTEM_MESSAGE section as **[A] invariant constitutional rule**, **[B] conditional diagnostic process**, **[C] learner-model update**, or **[D] reporting/output**, with rationale, plus the proposed constitutional-core + conditional-diagnostic architecture and open design questions. **No prompt will be modified until this is reviewed and approved**; any refactor must then clear the full 66-case Compare-Two-Runs (WS5), judged on constitutional behavior, not textual similarity.

