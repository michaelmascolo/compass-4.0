# Compass — Stage-2 Constitutional / Diagnostic Decomposition (design; NOT implemented)

> Proposed **architectural decomposition** of the frozen `SYSTEM_MESSAGE` prior to any edit. This is NOT a simplification or weakening. Every current commitment is preserved; the goal is to separate **A. Constitutional reasoning (always active)** from **B. Conditional instructional diagnosis (activated only when the triage route requires it)**, plus two support categories: **C. Learner-model update** and **D. Reporting/output requirement**. No prompt is modified until this decomposition is reviewed and approved. Any refactor must then pass the full 66-case comparison (constitutional behavior, not textual similarity, is the acceptance criterion).

## Category legend
- **[A] Invariant constitutional rule** — must execute on EVERY coaching turn regardless of route.
- **[B] Conditional diagnostic process** — executes only when the triage route/dimension calls for it.
- **[C] Learner-model update** — maintains the incremental student model across turns.
- **[D] Reporting / output requirement** — serialization/format; not reasoning.

## Section-by-section classification (line refs into current server.py SYSTEM_MESSAGE)

| Prompt section | Category | Why |
|---|---|---|
| Opening stance: interpret participation vs telos; provisional theory (655, 659) | **A** | The interpretive contract; frames every turn. |
| No hidden traits / no stages / no scores (657) | **A** | Constitutional safeguard against deficit labeling; always on. |
| Functional asymmetry + author-ownership; never write/rewrite/give the answer (661) | **A** | Core anti-coauthoring / learner-ownership invariant. |
| Domain-independent reasoner; keep developmental reasoning distinct from canonical knowledge (663) | **A** | Architectural invariant governing how any diagnosis is used. |
| Canonical model = resources, not stages/sequence/templates (665) | **A** | Governs the *use* of all diagnostic knowledge; always on. |
| Inside-Outside coordination rule — the 5 questions (667) | **A** (routing) | Constitutional sequencing rule; triage now answers Q1–Q4, but the *commitment* stays invariant. |
| **M6 Communicative Purpose** — infer purpose before evaluating (669–674) | **A (thin) + B (deep)** | The *commitment* "know the purpose before instructing" is [A]; the full re-inference + purpose-sensitivity walkthrough is [B], run when triage flags purpose unclear/foundational. |
| **M7 Functional Paragraph** (676–682) | **B** | Diagnostic lens; run only when the route/dimension is paragraph focus/coherence. |
| **M8 Functional Evidence** (684–689) | **B** | Run only when route = evidence / interpretation. |
| **M9 Transitions & Coherence** (691–696) | **B** | Run only when route = coherence/organization. |
| **M10 Conclusion** (698–704) | **B** | Run only when route = conclusion completion. |
| **M11 Master Loop** steps 1–4 "DIAGNOSE across ALL frameworks → prioritize one" (706–710) | **B** (mostly) | The broad multi-framework diagnosis is the main inherited cost; triage already produces unit + priority + one target. Keep step-4 "exactly ONE target" as [A]; make steps 1–3 conditional. |
| **M11** step 5 choose instructional mode (711) | **A** | Mode selection is part of the coaching-move contract every turn. |
| **M11** steps 6–8 evaluate / consolidate / return control (712–714) | **A** | Response-evaluation + return-of-control are invariant. |
| **M11 Stopping rules** — independence request, diminishing returns (715) | **A** | Hard constitutional safeguards (mandatory, "not optional"). Always on. |
| **M11** future_opportunity (716) | **D** | A reported field; not reasoning. |
| **M12 Reader Construction** (718–725) | **B** | Reader model runs only when the dimension is reader-facing (clarity/elaboration/coherence/precision). |
| **M13 Revision-as-Development** (727–733) | **B (conditional on revise)** | Already conditional (prior draft exists); keep conditional. |
| **M14 Integration & Calibration** — integrated reasoning / consistency (735–739, 741) | **B** | Cross-framework integration needs multiple lenses; largely moot once one target is fixed. |
| **M14 calibration_check** — proportionality / restraint / no over-teaching (737) | **A** | Restraint is constitutional; keep as a single always-on self-check on the chosen target. |
| **Governed Canonical Instruction** IO 12-step sequence (743–754) | **B** | Deep per-element diagnosis from instructional objects; run for the triaged element only. |
| Canonical-Knowledge Governance: student thinking leads, culture leads instruction (757) | **A** | Constitutional stance. |
| **ANSWER-THE-ASSIGNMENT CHECK** (758) | **A** | Off-task detection is a safeguard + a foundational trigger; must run every turn. |
| TEACH-don't-only-ask; supported performance; never perform for them (759–761) | **A** | Anti-coauthoring / learner-ownership; always on. |
| Student-facing response shape A–E (763) | **A/D** | The shape contract ([A]); the specific composition is [D] output guidance. |
| **W-A Consolidation by principle** (767) | **A** | Mandatory transfer commitment on success; always on. |
| **W-B Restraint on competent performance** (768) | **A** | Constitutional anti-over-teaching; always on. |
| **W-C No copyable content** (769) | **A** | Hard anti-coauthoring boundary; always on. |
| **W-D Honor teacher purpose & developmental priority** (770) | **A (commitment) → triage** | The commitment stays [A]; the *mechanism* now lives in triage dimension selection (fixed the TC15 miss). |
| DRAFT RULE — a differing draft = a revision (781) | **A** | Interpretive safeguard; always on. |
| **Recursive Loop** steps 1–6 (state telos, organization, differentiation, evidence for/against, change, reorganizations) (783–789) | **B** | The broad theory-rebuild; make conditional (consume incremental learner model instead of rebuilding). |
| **Recursive Loop** steps 7–8 generate 2–3 candidates, select by coherence (790–791) | **A (thin)** | "Deliberate among options, pick by coherence not optimality" is a quality invariant; the *count* is [D] and can be reduced. |
| **Recursive Loop** step 9 one concise invitation (792) | **A** | One-invitation rule. |
| **Recursive Loop** step 10 revise full theory (793) | **C** | Learner-model update. |
| Student-facing invitation rules (795) | **A** | Voice/length/no-grading safeguards; always on. |
| **M5A Writing Instruction Boundary** — writing vs content targets, anti-coauthoring rule, self-check, content mode (797–802) | **A** | THE central constitutional layer. Never conditional. |
| Developmental Instruction Layer — intervention types + timing + RESTRAINT (804–812) | **A** | Intervention-type selection + restraint are invariant coaching-contract rules. |
| OUTPUT FORMAT JSON schema (814–862) | **D** | Serialization. The per-framework theory blocks are only *emitted* when their [B] lens ran. |
| Provide 2–3 candidates / no scores (863) | **D** | Output guidance (count reducible). |
| developmental_profile_update (859–864) | **C** | Learner-model update. |
| BREVITY (866) | **D** | Output guidance. |

## Resulting architecture (proposed, not implemented)
- **Constitutional Core [A]** — a compact, always-run block: interpretive stance, no-deficit-labeling, M5A anti-coauthoring + W-A/W-B/W-C, learner ownership, one-target + one-invitation rules, restraint/calibration self-check, stopping-rules (independence / diminishing returns), answer-the-assignment check, developmental sequencing (inside→outside commitment), instructional-contract voice rules. This IS the constitution; it never varies.
- **Conditional Diagnostic Layer [B]** — the framework lenses (M6-deep, M7–M10, M12, M13, IO 12-step, M11 broad diagnosis, recursive-loop theory rebuild). The triage route/dimension selects WHICH lenses run; the rest stay dormant. E.g. route=`evidence` → run M8 (+ M6 thin, reader model if interpretation-facing); route=`coherence` → M9 (+ reader); route=`stall_support` → none beyond the core.
- **Learner-Model Update [C]** — revision theory + developmental_profile_update, applied incrementally.
- **Reporting [D]** — emit only the fields whose [B] lens executed, plus the core fields.

## Why this is decomposition, not weakening
Every **[A]** commitment runs on every turn exactly as today. Nothing in category A becomes conditional. Only **[B] diagnostic breadth** — which framework lenses to *run* — becomes governed by the triage route instead of "run all, every turn." This is the same selectivity a skilled human coach uses: the constitution is constant; the diagnosis focuses on the live edge. The retest evidence (Stage 1 ~3.8s, Stage 2 ~33s = 88%, and R3/preview trims) shows the [B] breadth is where the latency and the residual over-reasoning live.

## Open design questions for review (before any prompt edit)
1. Should the Constitutional Core be a **separate system message** (cleanest) or a clearly-delimited always-on section of one prompt?
2. How should route→lens activation be expressed — an explicit "run only these lenses" directive injected per turn (current override style) vs. a structured core+module prompt assembly?
3. Minimum lens set that must ALWAYS run for safety (candidate: M6-thin + M5A + answer-the-assignment + restraint) even on a `stall_support` route?
4. Candidate-invitation count: keep "2–3" as an [A] deliberation quality rule, or allow 1 when triage confidence is high?

**No prompt changes will be made until this decomposition and these questions are reviewed and approved.** Post-approval, the refactor must clear the full 66-case Compare-Two-Runs vs `fd0dec0c`, judged on constitutional behavior, not textual similarity.
