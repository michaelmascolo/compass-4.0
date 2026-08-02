# Compass — Canonical Product Design Specification

> The single source of truth every implementation follows. Instructional architecture, decision engine, and developmental model are treated as provisionally stable and are NOT redesigned here. This document is workflow / interaction / experience design only.
>
> Governing principle (carried from prior work): **each screen answers exactly one psychological question**, shows the evidence that answers it, and offers one action that naturally follows.
>
> Status: **PHASE 1 (complete journey map) — for approval.** Phases 2 (per-screen design), 3 (canonical Student Workspace — highest priority), and 4 (Preview redesign) follow after approval.

---

## Cross-cutting frame

- **Two entry paths:** Discovery (Landing → Preview → Bridge → Auth → Teacher Home) and Direct (Auth/Role gateway → Teacher Home or Student Join). The preview is never forced on returning users.
- **Roles:** Teacher (authoring + monitoring) and Student (writing). Engine internals / Dev Panel never appear to either.
- **Constitutional spine:** every authoring screen reaffirms the teacher-decides / Compass-decides distinction; students never see scores or rubrics as verdicts.
- **The writing is the primary object.** Conversation exists only to develop the writing. This principle governs Screen 10 and the Preview.

---

# PHASE 1 — The Complete Experience

Each screen: **Purpose · User's question · Information displayed · Primary action · Secondary actions · Transition.**

---

## 1. Landing Page
- **Purpose:** Communicate what Compass is (a writing *teacher*, not a text generator) and route to the two doors.
- **User's question:** "Should I care?"
- **Information:** One-line value proposition; the anti-coauthoring difference stated plainly; a single invitation to *participate*, not read.
- **Primary action:** Try the Preview.
- **Secondary actions:** Open Compass (sign in / go to app).
- **Transition:** Preview (S2) or Auth (S4).
- **Must not appear:** method/architecture explanation, jargon, feature dumps, pricing walls, slogans implying Compass leads students to predetermined answers.

## 2. Public Preview
- **Purpose:** Let a teacher *experience* the real interaction model in miniature by developing a short Grade-9 passage.
- **User's question:** "Does Compass really teach differently?"
- **Information:** The passage the user enters; Compass's developmental responses; the user's own revisions. (Post Phase 4: a miniature of the real writing workspace, not a chat.)
- **Primary action:** Enter/revise the passage ("Try Compass").
- **Secondary actions:** Optional essay context + passage type; "Bring your own writing" exit.
- **Transition:** Preview → Real Bridge (S3).
- **Must not appear:** scoring, rubric, jargon-first, Dev Panel, Compass meta-explanation, account wall before value.

## 3. Preview → Real Bridge
- **Purpose:** Convert the felt experience into intent to use Compass for real classroom work.
- **User's question:** "Could I use this with my own students?"
- **Information:** A reflection grounded only in what just happened (never fabricated claims about their students).
- **Primary action:** Continue with a real assignment.
- **Secondary actions:** Not now / back to Landing.
- **Transition:** Auth (S4), then Teacher Home / Create flow.
- **Must not appear:** feature list, hard paywall, a summary that states the writing principle *for* them.

## 4. Account Creation / Sign In
- **Purpose:** Create or resume a teacher account so work persists.
- **User's question:** "How do I get in — and will my preview carry over?"
- **Information:** Sign-up vs sign-in; reassurance that preview intent carries forward; minimal fields.
- **Primary action:** Create account / Sign in.
- **Secondary actions:** Toggle sign-up/sign-in; (later) SSO.
- **Transition:** First-time → Teacher Home with guided Create; returning → Teacher Home.
- **Must not appear:** forcing the preview on returning users; long profile forms; role ambiguity.

## 5. Teacher Home
- **Purpose:** The teacher's hub — classes, assignments, and where students are developmentally, at a glance.
- **User's question:** "Can I get started quickly — and what needs my attention?"
- **Information:** Classes & assignments list; recent student activity; clear empty state for first-timers.
- **Primary action:** Create a class / assignment (dominant for first-timers); open an existing class or dashboard (returning).
- **Secondary actions:** Account/settings; revisit preview.
- **Transition:** Create Class (S6) or an assignment's Dashboard (S11).
- **Must not appear:** the preview experience; student-facing writing UI; engine internals.

## 6. Create Class
- **Purpose:** Establish a class container and a shareable join code for students.
- **User's question:** "How do my students get in?"
- **Information:** Class name/section; generated class code / invite link; roster placeholder.
- **Primary action:** Create class & reveal code.
- **Secondary actions:** Edit details; skip (attach assignment later).
- **Transition:** Create Assignment (S7).
- **Must not appear:** heavy roster management (deferred); engine settings.

## 7. Create an Assignment  *(one coherent authoring workflow)*
- **Purpose:** In a single task, the teacher defines the instructional context for an assignment; Compass internally constructs the instructional contract and confirms consistency before activation. The teacher experiences ONE process, not separate phases.
- **User's question:** "How do I set up this assignment — and what will Compass do with it?"
- **Information (progressive within one flow):**
  1. **Configure** — sectioned form: Class & Learners, Assignment & Purpose, Learning Goals, Standards & Evaluation, Guidance & Feedback, Revision (Grade-9 calibration applied by default).
  2. **Contract (surfaced inline, constructed by the system)** — a compact, always-visible affirmation of the teacher-decides / Compass-always-protects distinction; any setting that brushed a constitutional boundary is shown with the compatible alternative Compass will use. Not a separate gate; part of the same page.
  3. **Review & activate** — concise summary + validation (required-field errors, conflicts, warnings) each with a clear resolution.
- **Primary action:** Activate assignment.
- **Secondary actions:** Save draft; "Ask Compass" (test a request against the constitution); edit any section.
- **Transition:** Activation → students can join (S8 Student Workspace); teacher lands on the Dashboard (S9).
- **Must not appear:** the commitments as toggles; engine reasoning fields/test harness; activation while errors/conflicts remain unresolved; silent discarding of teacher choices.

> Note: former S8 (Instructional Contract) and S9 (Assignment Review) are now merged into this single S7 workflow. Subsequent screens shift accordingly: Student Workspace, Teacher Dashboard, Revision Analytics, Assignment Complete.

## 10. Student Experience  *(the canonical Student Workspace — Phase 3, highest priority)*
- **Purpose:** The student develops their own writing through continuous Write → coach → revise cycles, with the document always the primary object.
- **User's question:** "What is this asking of me, and how do I make my writing better — myself?"
- **Information:** The assignment purpose/task; the **persistent, continuously editable draft** (primary); the coach's one-at-a-time developmental invitations tied to the draft; the student's own revisions and their history.
- **Primary action:** Write / revise the document.
- **Secondary actions:** Answer or explain to the coach; request more support; view what changed since the last revision.
- **Transition:** On meeting the assignment's revision expectations → Assignment Complete (S13); progress streams to the Teacher Dashboard (S11).
- **Must not appear:** scores/grades/rubric-as-verdict; Compass rewriting/auto-correcting; engine internals; a chat that displaces the document.

## 11. Teacher Dashboard
- **Purpose:** Show the teacher what they can now *see that they couldn't before* — developmental participation across the class, not just finished products.
- **User's question:** "What is now visible to me that I couldn't see before?"
- **Information:** Per-student and class-level signals grounded in participation — attempts, revision quality, use of feedback, explanation, evidence of transfer, degree of prompting required; flags for who needs attention. Reads from the saved configuration (objectives, priorities, rubric) — never re-asks.
- **Primary action:** Open a student's development (→ S12).
- **Secondary actions:** Filter by objective/priority; export a class summary.
- **Transition:** Revision Analytics for a student (S12).
- **Must not appear:** a single polished-paper grade as the headline; inference of capability from the final draft alone; engine internals.

## 12. Revision Analytics
- **Purpose:** Show one student's developmental trajectory across revisions for this assignment.
- **User's question:** "How is *this* student actually developing as a writer?"
- **Information:** Draft-to-draft progression; where the coach intervened and how the student responded; independence trend (support increasing vs. fading); evidence of explanation and transfer; the writing itself at each stage.
- **Primary action:** Open a specific draft/exchange in context.
- **Secondary actions:** Add a teacher note; compare two drafts.
- **Transition:** Back to Dashboard (S11) or into a draft view.
- **Must not appear:** capability inferred from grade level or polish alone; auto-generated verdicts.

## 13. Assignment Complete
- **Purpose:** Close the loop developmentally — mark completion around what the student *developed*, not merely produced.
- **User's question (student):** "What did I actually learn to do?" / **(teacher):** "What did this class develop?"
- **Information:** The final draft; a developmental summary grounded in the student's own trajectory (what they can now do more independently); connection back to the assignment purpose.
- **Primary action (student):** Submit / finish. **(teacher):** Review class outcomes.
- **Secondary actions:** Reflect; carry an insight toward the next assignment; export.
- **Transition:** Teacher → Dashboard / next assignment; Student → Teacher Home or next assigned task.
- **Must not appear:** a bare score as the sole outcome; language claiming Compass wrote or fixed the work.

---

## Psychological progression (the spine)
Should I care? → Does it really teach differently? → Could I use this with my students? → How do I get in? → Can I start quickly? → How do students join? → How do I tell Compass the assignment? → What will Compass do and refuse? → Is this right and consistent? → How do I make my writing better myself? → What can I now see? → How is this student developing? → What did we develop?

---

## Deferred / future expansion (noted, not designed now)
Role gateway for direct student entry; SSO; multi-class roster management; notifications; assignment templates library; multi-grade calibration UI (profiles beyond Grade 9); accommodations management; standards-library integrations.

---

## Next phases (gated on approval of this map)
- **Phase 2:** per-screen design (layout, hierarchy, primary/secondary controls, empty/error states, mobile, expansion points) for all 13.
- **Phase 3 (highest priority):** the canonical Student Workspace (S10) — begin from writing, document continuously visible/editable, continuous revision cycles.
- **Phase 4:** redesign the Public Preview (S2) as a faithful miniature of the Phase-3 workspace, replacing the current simplified chat.
