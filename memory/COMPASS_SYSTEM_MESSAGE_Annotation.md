# COMPASS — Frozen SYSTEM_MESSAGE Governance Annotation

> **Architectural annotation only. The SYSTEM_MESSAGE text is NOT modified.** This document tags every section of the current frozen prompt (`server.py`, SYSTEM_MESSAGE ≈ lines 655–866) with exactly one **primary** governance layer from the canonical `COMPASS_GOVERNANCE_ARCHITECTURE.md`, plus any cross-layer dependencies. Purpose: make every future modification traceable to a governance layer, and make the Stage-2 decomposition mechanical and auditable.
>
> Tags: **[L1]** Constitutional Commitments · **[L2]** Developmental Policy · **[L3]** Diagnostic Reasoning (3A interpretation / 3B instructional decision) · **[L4]** Learner Model · **[L5]** Presentation Contract.
>
> Rule applied: where a section spans layers, the **primary** tag is the layer whose *authority* the section carries (what governs it), and dependencies note the layers it reads or writes.

| Lines | Section | Primary | Dependencies | Note |
|---|---|---|---|---|
| 655, 659 | Interpret participation vs telos; provisional, revisable theory | **[L1]** | L3 | Identity-level interpretive contract framing every turn. |
| 657 | No hidden traits / no fixed stages / no scores | **[L1]** | L4 | Constitutional safeguard against deficit labeling; constrains what L4 may store. |
| 661 | Functional asymmetry; author ownership; never write/rewrite/give answer | **[L1]** | L3, L5 | Core anti-coauthoring / learner-ownership invariant. |
| 663 | Domain-independent reasoner; keep developmental reasoning distinct from canonical knowledge | **[L1]** | L2, L3 | Architectural identity invariant governing how knowledge may be used. |
| 665 | Canonical model = resources, not stages/sequence/templates | **[L2]** | L3 | Developmental-policy governance over the *use* of diagnostic knowledge. |
| 667 | Inside–Outside coordination (the 5 questions) | **[L2]** | L3 | Developmental policy: inside-out before outside-in routing. Now also encoded in rapid triage. |
| 669–674 | M6 Communicative Purpose (infer purpose before evaluating) | **[L3]** (3A) | L2 | Interpretation of intended meaning; the "know purpose first" commitment is L2. |
| 676–682 | M7 Functional Paragraph | **[L3]** (3A/3B) | L2 | Conditional lens; runs when route = paragraph focus/coherence. |
| 684–689 | M8 Functional Evidence | **[L3]** (3A/3B) | L2 | Conditional lens; route = evidence/interpretation. |
| 691–696 | M9 Transitions & Coherence | **[L3]** (3A/3B) | L2 | Conditional lens; route = coherence/organization. |
| 698–704 | M10 Conclusion | **[L3]** (3A/3B) | L2 | Conditional lens; route = conclusion completion. |
| 706–710 | M11 Master Loop steps 1–4 (diagnose across ALL frameworks → prioritize one) | **[L3]** (3A) | L2 | The broad diagnosis is the main inherited cost; "exactly ONE target" is the L2 discipline. |
| 711 | M11 step 5 choose instructional mode | **[L2]** | L3 | Support-calibration / mode = developmental policy. |
| 712–714 | M11 steps 6–8 evaluate response / consolidate / return control | **[L2]** | L3 (3B) | Developmental sequencing + return-of-control policy. |
| 715 | M11 stopping rules (independence request; diminishing returns) | **[L1]** | — | Hard constitutional safeguards ("not optional"). |
| 716 | M11 future_opportunity | **[L5]** | L4 | Reported field (reporting/output). |
| 718–725 | M12 Reader Construction | **[L3]** (3A) | L2 | Conditional; runs when the dimension is reader-facing. |
| 727–733 | M13 Revision-as-Development | **[L3]** (3A) | L4 | Conditional on a prior draft; reads/writes learner model. |
| 735–739, 741 | M14 Integration & Calibration (integrated reasoning / consistency) | **[L3]** | L2 | Cross-framework integration; largely moot once one target is fixed. |
| 737 | M14 calibration_check (proportionality / restraint / no over-teaching) | **[L1]** | L2 | Restraint is constitutional; retained as an always-on self-check. |
| 743–754 | Governed Canonical Instruction — IO 12-step sequence | **[L3]** (3B) | L1, L2 | Per-element instructional decision from instructional objects; run for the triaged element only. |
| 757 | Canonical-Knowledge Governance (student thinking leads; culture leads instruction) | **[L1]** | L2 | Constitutional stance. |
| 758 | ANSWER-THE-ASSIGNMENT check | **[L1]** | L2 | Off-task safeguard + a foundational trigger; always runs. |
| 759–761 | Teach-don't-only-ask; supported performance; never perform for them | **[L2]** | L1 | Developmental policy ("teach, don't only ask"); the "never perform" clause is L1. |
| 763 | Student-facing response shape A–E | **[L5]** | L1 | Presentation shape; the one-invitation/no-content guarantees are L1. |
| 767 | W-A Consolidation by principle | **[L2]** | L4 | Developmental policy: consolidate/transfer on success. |
| 768 | W-B Restraint on competent performance | **[L1]** | L2 | Constitutional anti-over-teaching. |
| 769 | W-C No copyable content | **[L1]** | L5 | Hard anti-coauthoring boundary, enforced at the surface. |
| 770 | W-D Honor teacher purpose & developmental priority | **[L2]** | L3 | Developmental policy; now mechanized in triage dimension selection. |
| 781 | DRAFT RULE (a differing draft = a revision) | **[L1]** | L3 | Interpretive safeguard. |
| 783–789 | Recursive Loop steps 1–6 (rebuild telos/organization/differentiation/evidence/change) | **[L3]** (3A) | L4 | Broad theory rebuild; the enduring architecture makes it consume the persistent learner model instead. |
| 790–791 | Recursive Loop steps 7–8 (generate 2–3 candidates; select by coherence) | **[L3]** (3B) | L2 | Instructional decision; "pick by coherence not optimality" is an L2 quality rule; candidate count is L5. |
| 792 | Recursive Loop step 9 (one concise invitation) | **[L1]** | L5 | One-invitation rule (constitutional), expressed at presentation. |
| 793 | Recursive Loop step 10 (revise full theory) | **[L4]** | L3 | Learner-model update. |
| 795 | Student-facing invitation rules (voice / length / no grading) | **[L5]** | L1 | Presentation contract; no-grading is an L1 guarantee. |
| 797–802 | M5A Writing Instruction Boundary (writing vs content targets; anti-coauthoring; self-check; content mode) | **[L1]** | L3, L5 | THE central constitutional layer. Never conditional. |
| 804–812 | Developmental Instruction Layer (intervention types + timing + RESTRAINT) | **[L2]** | L1 | Intervention selection/timing = developmental policy; restraint clause is L1. |
| 814–862 | OUTPUT FORMAT JSON schema | **[L5]** | L3, L4 | Serialization; per-framework blocks emit only when their L3 lens ran. |
| 863 | Provide 2–3 candidates; no scores | **[L5]** | L1 | Output guidance; count is reducible, no-scores is L1. |
| 859–864 | developmental_profile_update | **[L4]** | L3 | Learner-model update. |
| 866 | BREVITY | **[L5]** | — | Output guidance. |

## Layer coverage summary
- **[L1] Constitutional Commitments:** 655, 657, 661, 663, 715, 737, 757, 758, 768, 769, 781, 792, 797–802 (+ guarantees embedded in 763, 793, 795, 863).
- **[L2] Developmental Policy:** 665, 667, 711, 712–714, 759–761, 767, 770, 804–812.
- **[L3] Diagnostic Reasoning:** 669–674, 676–704, 706–710, 718–733, 735–741, 743–754, 783–791.
- **[L4] Learner Model:** 793, 859–864 (+ read across 727–733, 783–789).
- **[L5] Presentation Contract:** 716, 763, 795, 814–862, 863, 866.

## How this guides the Stage-2 decomposition (no text changed yet)
- **Always-run core** = all **[L1]** rows + the **[L2]** rows that govern acceptable moves (665, 667, 711–714, 759–761, 767, 770, 804–812). These execute every turn on every path.
- **Conditional modules** = the **[L3]** rows, activated by the triage route/dimension (foundational → all run; focused → the relevant subset).
- **Learner-model I/O** = **[L4]** rows, applied incrementally.
- **Emission** = **[L5]** rows, produced for whatever ran.

Any future prompt edit MUST cite the layer(s) of the row(s) it touches, and MUST NOT reduce an [L1] or governing-[L2] guarantee to gain speed. Validation of any resulting refactor remains the full 66-case Compare-Two-Runs vs `fd0dec0c`, judged on constitutional behavior (did [L1]/[L2] hold), not textual similarity.
