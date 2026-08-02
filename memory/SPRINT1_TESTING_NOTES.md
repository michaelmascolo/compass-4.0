# Sprint 1 — Testing & Refinement Log

Purpose: capture observations from real testing of the Question Loop so Sprint 2 is
driven by observed learner behavior, not additional theoretical design.
Rule: no new feature unless it solves a problem actually observed here.

## Instruments available for testing
- **Developer Mode** (hidden): toggle with `Ctrl/Cmd+Shift+D`, or open `?represent&dev`.
  Shows the Developmental Control Engine state (Current Loop, Dev. Operation, Target
  Demand, Scaffold Level, Instruction Type, Reason, Next-if-Successful/Unsuccessful,
  Requires Reconstruction). Never visible to students.
- **Developer Notes** (private, per session): editable in the Developer Mode panel.
- **Development Session record**: `GET /api/assignment/sessions/{id}/record?format=json|markdown`
  (also the JSON/MD buttons in the Developer panel). A complete research case:
  assignment, AI analysis (explicit/inferred demands + important distinctions + ambiguities),
  student (interpretation + every response + final restatement), developmental history
  (per scaffold: target, operation, level, performed?, reason, final status), final
  Question Map, and metadata (length, #scaffolds, #Level-3, "I don't know" occurred,
  restart occurred).

## Generalization sweep — analyze_assignment across the matrix (2026-06)
Ran the analysis stage on 8 assignments spanning Grade 4 → Graduate and Literature,
History, Biology, Chemistry, Psychology(reflective), Business, plus assignment types
short-answer / creative / argument / experiment-design / lab report / reflective /
synthesis / analysis.

Result: robust. 5–6 demands each; explicit/inferred split behaves sensibly (History &
Business correctly skew INFERRED because they demand argumentative structure that is not
literally stated); operation vocabulary stays varied and apt (Define, Explain, Compare,
Differentiate, Analyze, Evaluate, Exemplify, Relate); every case produced useful
important_distinctions and ambiguities.

Highlights of quality:
- Grade 4 ("draw + 2 sentences"): stayed simple; surfaced "describing the animal vs.
  explaining WHY you like it — sentences must give reasons, not just facts." Age-apt.
- History ("explain causes + evaluate most important"): surfaced "explaining a cause vs.
  evaluating its importance — description is not argument" and proximate-vs-underlying
  cause distinction; marked "define criteria for 'importance'" as an inferred demand.

## Observations / candidate issues (for Sprint 2 consideration — DO NOT build yet)
1. **Operation mislabel on pure constraints.** For "write two sentences", the analyzer
   tagged a length/format constraint with operation `Define`. Format/length constraints
   are not developmental operations. Sprint 2 candidate: a `constraint` demand kind that
   is tracked but not scaffolded as an operation.
2. **Verify young-learner scaffold register.** Analysis is age-appropriate; still need to
   run full multi-turn Grade-4 sessions to confirm scaffold LANGUAGE (not just demands)
   stays simple at levels 2–3.
3. **"I don't know" handling confirmed correct** on the mindset assignment: for a
   non-derivable demand it escalated to Level 3 direct teaching + mandatory own-words
   reconstruction, and never wrote the answer. Re-test across disciplines.
4. **Anti-trap** (≥3 failed attempts at Level 3 → mark demand 'developing' and advance)
   prevents dead-ends; watch whether it ever advances too early.

## Still to test (recommend doing interactively with real learners)
- Full multi-turn sessions for each of the 5 required mindset learner variants + the
  discipline matrix, watching whether the Question Loop consistently yields a MORE
  ADEQUATE representation (the real success criterion — not whether the AI is "right").
- Edit/restart mid-session; resume-after-refresh; long assignments; vague/1-line
  assignments; assignments with no clear operation.

_Log started 2026-06. Append findings here as sessions are reviewed._

# =====================================================================
# TESTING ROUND 1 — 6 Development Sessions (2026-06)
# =====================================================================
Method: agent-run sessions with deliberately imperfect, scripted learner personas
across levels/disciplines/types. Records saved in /tmp/dev_sessions/ and in the
Development Session Library (each with Developer Summary + Notes + Sprint Recommendation).
CAVEAT: personas were short (3-4 turns), so most sessions ended mid-loop (stage=mapping,
not adequate). This limits observations about final-restatement TRANSFER — but the
Control-Engine behavior observed below is real and consistent.

Sample: Grade4 Reflective (favorite animal) · Grade8 History (Civil War causes) ·
Grade12 Biology lab (enzyme experiment) · College Psychology compare/contrast (mindsets) ·
College Business argument (remote work) · Graduate Psychology synthesis (attachment).

Sprint Recommendations tally: Developmental Control Engine revision ×4 · New scaffold ×1 ·
No change needed ×1.

## RECURRING PROBLEMS (these — not new theory — should define Sprint 2)

P1. CONSTRAINTS MISLABELED AS OPERATIONS (high priority, seen g4, col_remotework).
    Format/length/quantity constraints ("write two sentences", "use >=3 peer-reviewed
    sources") are extracted as demands with a developmental operation (e.g. Define) and
    then SCAFFOLDED as if they were cognitive operations. In Grade4 this derailed the
    whole session. Fix direction: a distinct `constraint` demand kind — tracked/checked
    but never scaffolded as an operation.

P2. TARGET FIXATION (high, seen in 5/6). The engine stays on ONE demand for up to 3
    attempts (L2 -> L3 -> L3 -> anti-trap 'developing') before moving on. Result: over-
    scaffolding, long loops, and the learner never reaches the substantive work. Fix
    direction: move on after 1-2 attempts, and/or interleave demands rather than drilling.

P3. L3 "MANDATORY RECONSTRUCTION" MISFIRES (high, seen g4). Reconstruction is demanded
    even when no CONCEPT was taught (doing-tasks), and a genuinely adequate learner answer
    was failed as reason='no_reconstruction'. Fix: require reconstruction ONLY after a
    concept was explicitly taught; never fail a correct performance for lacking it.

P4. OPERATION LABEL INSTABILITY (med, seen g8). The scaffold generator invents a NEW long
    'operation' string each turn for the same demand ("Identify causation - selecting
    specific historical conditions...") instead of using the demand's fixed operation. Fix:
    anchor targetOperation to the demand; keep it stable.

P5. OVER-ESCALATION ON SIMPLE/DERIVABLE DEMANDS (med-high, g4/g12). A single weak answer +
    one "I don't know" jumps to L3 direct teaching. Too aggressive for derivable and/or
    young-level demands. Fix: gentler escalation; more time at L1/L2 for derivable demands.

P6. DIAGNOSTIC MIS-ATTRIBUTION (med, col_mindset). A response that demonstrates demand X is
    judged only against the ACTIVE target Y (and scored 'misconception'), so the learner
    gets no credit for X. Fix: after every response, re-diagnose ALL demands, not just the
    active target.

P7. TOO MANY / MARGINAL ESSENTIAL DEMANDS (med). 5-6 demands each, including padding (Grade4
    "Connect drawing to writing (Relate)"). Long loops, fatigue risk. Fix: cap essential
    demands; demote marginal inferred ones to 'supporting'.

P8. REGISTER NOT AGE-CALIBRATED (med). Scaffolds use adult metacognitive phrasing ("reconstruct
    it in your own words") at Grade 4; L3 teaching too elementary at Graduate. Fix: calibrate
    scaffold language to educational_level (already captured).

## What worked
- Explicit/inferred split, important_distinctions, ambiguities: consistently strong.
- Target SELECTION (which demand matters most) was usually right; the problems are in
  PACING/ESCALATION, credit attribution, operation anchoring, and constraint handling.
- The best-paced case (college argument) shows the loop works well when demands are
  genuine operations and escalation stays measured.

## Recommendation for Sprint 2 scoping review
Before any Knowledge-Loop work, the evidence says the highest-leverage fixes are to the
Developmental Control Engine (P2, P5, P6) plus P1 (constraint kind) and P3 (reconstruction
gating). These are REFINEMENTS to Sprint 1, and by the project rule they are now justified
by observed behavior. Run more sessions (esp. full-length, reaching restatement, and more
Grade-4/8 cases) to confirm P2/P3/P5 before committing.
