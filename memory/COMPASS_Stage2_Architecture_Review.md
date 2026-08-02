# Compass — Stage-2 Focused Reasoner: Architectural Review

> Analysis only. No simplifications implemented. Produced after the revise-and-retest cycle, per directive. The question: **is the focused Stage-2 reasoner still solving a broader problem than the immediate instructional decision requires?** Short answer: **yes** — because the broad, multi-framework reasoning is mandated *inside the frozen SYSTEM_MESSAGE*, which Stage 2 uses verbatim. Our triage override trims Stage-2 **output** and scopes the prompt, but it cannot switch off the SYSTEM_MESSAGE's own "diagnose across ALL frameworks / integrate across ALL frameworks every turn" instructions.

## 1. What reasoning tasks is Stage 2 still performing?
Stage 2 calls the model with the **frozen SYSTEM_MESSAGE**, which instructs — *every turn* — the full governed pipeline:
- **M11 Master Developmental Loop:** identify unit → (re)confirm communicative purpose → **DIAGNOSE across ALL frameworks** (list every opportunity) → prioritize exactly one → choose instructional mode → evaluate the latest response → consolidate → return control → stopping rules → name a future opportunity.
- **M6 Communicative Purpose** (re)inference.
- **M12 Reader Construction** (every turn with text): dynamic reader model, likely reader questions, assumed knowledge, elaboration, precision, next reader need.
- **M13 Revision-as-Development** (conditional: when a prior draft exists).
- **M14 Integration & Calibration** (every turn): integrated reasoning across frameworks, calibration (proportionality/restraint), consistency, cross-framework transfer, pre-finalize self-check.
- **Governed Canonical Instruction (IO layer):** a 12-step internal sequence recorded in `instructional_reasoning`.
- **Output production:** 2–3 `candidate_invitations` → `selected_invitation` → `intervention` (focus/type) → the single `student_facing_invitation`.

Our FOCUSED_OUTPUT_OVERRIDE narrows *scope framing* and *serialized fields* (invitation + scaffolding_control[one target] + instructional_reasoning + revision_development + candidates + intervention), but the SYSTEM_MESSAGE's mandated **internal** reasoning is unchanged.

## 2. Which of those tasks are ESSENTIAL to select the next coaching move?
- Interpret the **triaged unit/span** of the draft.
- Run the **ONE relevant framework lens** for the triaged dimension.
- Apply the **constitutional invariants**: M5A writing-instruction boundary (never write/rewrite/supply content), the one-invitation rule, restraint/calibration **for that single target**.
- Produce the **one invitation + intervention** (focus=writing, support level).
These are the irreducible core. Triage has *already* supplied unit, purpose read, route, inside/outside, and the target.

## 3. Which tasks are INHERITED from the exhaustive architecture (now redundant given triage)?
- **M11-step-3 "diagnose across ALL frameworks"** — triage already diagnosed and prioritized; Stage 2 re-does it.
- **M6 full purpose re-inference every turn** — triage already assessed whether intention is sufficiently clear.
- **M14 cross-framework integration/consistency scan** — requires holding all frameworks; largely moot once a single target is fixed (its useful residue is a single restraint/calibration self-check).
- **M12 full reader model** — only pertinent when the triaged dimension is reader-facing (clarity/elaboration/coherence/precision).
- **The 12-field `instructional_reasoning` block** — mostly teacher-facing rationale; not required to produce the invitation.
- **Enumerating 2–3 candidate invitations then selecting** — internal deliberation that improves restraint but is a real generation cost.

## 4. Which tasks can become CONDITIONAL rather than mandatory?
| Task | Proposed condition |
|---|---|
| M11 broad multi-framework diagnosis | Skip — consume triage's diagnosis/priority |
| M6 purpose re-inference | Only when triage flags intention unclear / foundational |
| M12 reader construction | Only when the triaged dimension is reader-facing |
| M13 revision analysis | Already conditional (revise turns only) |
| M14 cross-framework integration | Collapse to a single restraint/calibration self-check on the one target |
| candidate_invitations (2–3) | 1–2, or skip enumeration when triage confidence is high |
| instructional_reasoning (12 fields) | Terse, or teacher-panel-only |

## 5. Can Stage 2 be decomposed into smaller conditional paths WITHOUT violating the frozen constitutional commitments?
**In principle, yes — but not purely via prompt scoping.** The distinction that matters:
- **Constitutional invariants (must run every turn):** M5A anti-coauthoring boundary, the one-invitation rule, restraint/calibration, never-rewrite. These are non-negotiable and cheap.
- **Diagnostic breadth (not constitutional):** M11-step-3 broad diagnosis and M14 cross-framework integration are *quality* scaffolding, not constitutional guarantees.

The obstacle: **the broad-diagnosis and cross-framework mandates live literally inside the frozen SYSTEM_MESSAGE** ("DIAGNOSE across ALL frameworks", "confirm they point to compatible recommendations … every turn"). Our override *asks* the model to focus, but it is arguing against its own system prompt — which is why Stage 2 still spends ~34s (≈89% of the triage turn) and why residual over-reasoning persists. Genuinely shrinking Stage-2 **reasoning** (not just output) requires one of:
1. **A dedicated focused system message** that carries the constitutional invariants verbatim but replaces "diagnose across ALL frameworks" with "reason from the triaged dimension" — i.e., a *constitutional-core + conditional-diagnostic* split of the frozen prompt. **This edits the frozen SYSTEM_MESSAGE and needs explicit approval.**
2. **A two-tier Stage 2:** a light path (interpret span → single lens → constitutional self-check → invitation) for high-confidence single-target turns, and the full frozen engine for reader-facing / low-confidence / foundational turns (already the fallback). The light path still needs option 1's focused system message to actually reduce reasoning.
3. **Streaming** the Stage-2 invitation (orthogonal): does not reduce total reasoning but cuts *time-to-first-word* dramatically; a transport change.

**Recommendation for the design decision (not implemented):** the highest-leverage, lowest-risk next step is **option 1** — factor the frozen prompt into (a) an immutable *constitutional core* (M5A, one-invitation, restraint, never-rewrite) and (b) a *conditional diagnostic layer* invoked only when triage signals it's needed. This preserves every constitutional commitment while letting Stage 2 stop re-solving the whole developmental model on turns where triage has already made the call. Because it touches the frozen prompt, it should be gated behind your approval and validated with the same 66-case Compare-Two-Runs methodology before any production use.

<!-- RETEST NUMBERS appended below after the revised 66-case run completes -->

## Retest confirmation (v4, run `532b8231`)
The revise-and-retest cycle confirms this review's premise empirically. After recalibration, Stage 1 triage runs in **~3.8s** and is functioning well (correct routing, 0 unsafe divergences, fallback a healthy 1.4%). The **entire residual latency lives in Stage 2**: focused call avg **32.9s = ~88%** of the 37.2s triage turn; DB/serialization ≈ 0ms. This is direct evidence that the focused reasoner is still solving a broader problem than the immediate decision requires — it executes the frozen SYSTEM_MESSAGE's "diagnose across ALL frameworks" (M11-3), M12 reader construction, M14 cross-framework integration, and the 12-step IO reasoning on every turn, even when triage has already selected the single target. The next architectural decision (Section 5, option 1) — factoring the frozen prompt into an immutable constitutional core + a conditional diagnostic layer — is where the remaining ~33s can be attacked without weakening any constitutional commitment. Not implemented; awaiting your decision.
