# Compass — Whole-Product Screen & Route Map (v0)

> Minimal, visualizable map only. NOT a build. Covers both entry paths. Each screen specifies: (1) purpose, (2) primary user, (3) essential info shown, (4) primary action, (5) secondary action (only if truly needed), (6) next destination, (7) what must not appear. Teacher Workspace settings are deliberately NOT designed yet.

## Route flow (both paths)

```
DISCOVERY PATH
  S1 Landing (/)  ──Try the Preview──▶  S2 Public Preview (/preview)
        │                                     │
   Open Compass                        Continue with real work
        │                                     ▼
        ▼                              S3 Preview→Real Bridge
  S5 Role Gateway (/open) ◀────────────────── │
        │                                     ▼
        │                              S4 Auth (/signin, /signup)
        ▼                                     │
  ┌─────┴───────────────┐                     ▼
  ▼                     ▼              S6 Teacher Workspace Home (/teacher)
S6 Teacher Home    S8 Student Join            │
  │                     │              (first-time ▶ S7 guided create)
  ▼                     ▼                      │
S7 Create (class/       S9 Student Workspace   ▼
   assignment)          (/write)          S7 Create → assign
```

```
DIRECT APP PATH
  S5 Role Gateway (/open)
     ├─ "I'm a teacher"  ──▶ S4 Auth ──▶ S6 Teacher Workspace Home
     └─ "I'm a student"  ──▶ S8 Student Join (class/assignment code) ──▶ S9 Student Workspace
```

---

## S1 — Compass Landing (`/`)
1. **Purpose:** communicate what Compass is (a writing *teacher*, not a text generator) and route to the two entry points.
2. **Primary user:** first-time visitor (teacher / evaluator).
3. **Essential info:** one-line value proposition; a short "what it feels like" cue (participation, not demo); the two doors.
4. **Primary action:** **Try the Preview** → S2.
5. **Secondary action:** **Open Compass** (sign in / go to app) → S5.
6. **Next destination:** S2 (preview) or S5 (gateway).
7. **Must NOT appear:** architecture/method explanation, jargon (thesis/rubric), pricing walls before value, "AI writing assistant" framing, feature-list dump.

## S2 — Public Preview (`/preview`) — EXISTS
1. **Purpose:** the 3–5 min in-character experience where the visitor teaches themselves one owned insight about introductions.
2. **Primary user:** first-time teacher/evaluator (treated as a writer).
3. **Essential info:** only the seed invitation, then the conversation.
4. **Primary action:** write the seed / reply in the exchange.
5. **Secondary action:** none during the arc (stay in character).
6. **Next destination:** S3 (bridge) after the transfer beat / exit.
7. **Must NOT appear:** scoring, rubric, jargon-first, Dev Panel, any Compass meta-explanation, account wall before the aha.

## S3 — Preview → Real Bridge (post-preview CTA)
1. **Purpose:** convert the just-experienced aha into intent to use Compass for real work (fires the `preview-continue` signal).
2. **Primary user:** a teacher who just finished the preview.
3. **Essential info:** one line grounded in *what they just did*; a single invitation to bring a real assignment.
4. **Primary action:** **Continue with a real assignment** → S4 (auth) then S7.
5. **Secondary action:** **Not now / back to home** → S1.
6. **Next destination:** S4 (sign up/in) → S6/S7.
7. **Must NOT appear:** feature list, hard paywall, any claim Compass cannot know (e.g. about the learner's students), a summary that states the principle *for* them.

## S4 — Auth (`/signin`, `/signup`)
1. **Purpose:** create or resume a teacher account so work persists.
2. **Primary user:** first-time or returning teacher.
3. **Essential info:** email / sign-in method; clear sign-up vs sign-in toggle; reassurance that preview progress can carry forward.
4. **Primary action:** **Sign in** (returning) / **Create account** (first-time).
5. **Secondary action:** switch between sign-in / sign-up.
6. **Next destination:** returning → S6; first-time → S6 then guided S7.
7. **Must NOT appear:** forcing the preview on existing/returning users; role ambiguity; long profile forms before entry.

## S5 — Role Gateway / Open Compass (`/open`)
1. **Purpose:** the standalone-app front door for people who did NOT come through the landing/preview.
2. **Primary user:** returning teacher; student with a code; anyone opening the app directly.
3. **Essential info:** two clear choices — teacher vs student; a subtle "New here? See the preview" link (never forced).
4. **Primary action:** choose role — **I'm a teacher** → S4; **I'm a student** → S8.
5. **Secondary action:** **Try the Preview** (optional) → S2.
6. **Next destination:** S4 (teacher) or S8 (student).
7. **Must NOT appear:** mandatory preview, marketing copy, method explanation.

## S6 — Teacher Workspace Home (`/teacher`)
1. **Purpose:** the teacher's hub — see classes/assignments and student progress at a glance.
2. **Primary user:** signed-in teacher (returning) / newly-signed-up teacher (first-time).
3. **Essential info:** list of classes & assignments; recent student activity / where students are developmentally (dashboard entry points). First-time: an empty state that guides to create the first class.
4. **Primary action:** **Create class / assignment** → S7 (dominant for first-time); open an existing class/dashboard (returning).
5. **Secondary action:** account/settings.
6. **Next destination:** S7 (create) or the instructional dashboard (later spec).
7. **Must NOT appear:** the preview experience; student-facing writing UI; engine internals / Dev Panel.

## S7 — Create Class / Assignment (guided)
1. **Purpose:** set up a class and define an assignment (teacher's pedagogical purpose + task) for students.
2. **Primary user:** teacher (first-time onboarding or adding new work).
3. **Essential info:** class name / code; assignment prompt; pedagogical purpose & current task (maps to the existing Telos fields).
4. **Primary action:** **Create & get class code / assign** → shareable code/link.
5. **Secondary action:** save as draft.
6. **Next destination:** back to S6 (with the new class), or share code for students (S8).
7. **Must NOT appear:** engine reasoning fields, evaluator/test harness, jargon overload.

## S8 — Student Join (`/join`)
1. **Purpose:** let a student enter by class code or assignment link.
2. **Primary user:** student.
3. **Essential info:** code/link entry; the assignment they're joining (confirmation).
4. **Primary action:** **Join / Start writing** → S9.
5. **Secondary action:** none (keep frictionless).
6. **Next destination:** S9 (student workspace).
7. **Must NOT appear:** teacher tools, account-creation friction if the code suffices, the preview.

## S9 — Student Workspace (`/write`) — largely EXISTS (StudentWorkspace)
1. **Purpose:** the student writes and works with Compass on their real assignment.
2. **Primary user:** student.
3. **Essential info:** assignment prompt + current task; the writing canvas; the developmental conversation.
4. **Primary action:** write / revise / reply to the coach.
5. **Secondary action:** none essential (Dev Panel is developer-only, hidden from students).
6. **Next destination:** stays in-session; progress feeds the teacher dashboard (later spec).
7. **Must NOT appear:** scores/grades/rubric, engine internals, teacher-only controls.

---

## Product invariants (carry into every screen)
- A **public landing** with a prominent **Try the Preview** and a **separate Open Compass** door.
- A **direct standalone-app gateway** (S5) that does **not** force the preview.
- Distinct **returning-teacher** vs **first-time-teacher** entry (S4 → S6 vs S4 → S6+S7).
- **Student entry** by assignment link or class code (S8), frictionless.
- A clean **preview → real use** transition (S3 → S4 → S7) that never forces the preview on existing users.
- The **preview is never shown inside authenticated teacher/student work**, and engine internals/Dev Panel never appear to end users.

> Deferred (not designed here): full Teacher Workspace settings, the instructional dashboard detail, roster management, notifications, and any auth mechanism choice.
