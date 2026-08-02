# Compass — Canonical Student Workspace Design (Phase 3, revised)

> The heart of Compass. Design only — no build. The instructional engine, decision model, and developmental method are unchanged; this maps a **document-centered, anchored-coaching** experience onto the existing turn kinds (`writing`, `revise`, `answer`, `explain`) and durable polling.

## First principle
**Compass coaches the document, not a separate conversation about the document.** The learner's writing is the visual and cognitive center at all times. Coaching is **anchored directly to the relevant sentence or span** of the draft. There is normally **one active coaching target** at a time. The learner revises the text in place; when they do, the marker resolves and Compass moves to the next target.

## The canonical cycle
Write → Compass anchors ONE coaching marker to the relevant span → learner opens it and reads a short prompt adjacent to the writing → learner **revises that span in place** → the marker resolves → Compass responds and anchors the next single target → revise again. The document evolves continuously; it is never re-created, and coaching never becomes a side chat.

---

## 1. Layout (desktop)
Document-centered, single-focus. The writing fills the primary canvas; coaching attaches to it.

- **Top bar (slim):** assignment title + current writing task (one line each) and a quiet **revision progress** indicator ("Revision 1 of 2"). No dev tools, no score.
- **Document canvas (dominant, center, ~70%+):** the living draft on a paper surface — large serif body type, generous margins, autosave, live word count. The learner edits here, in place, throughout the whole session.
  - **Anchored coaching marker:** when Compass has a target, a single lightweight marker appears against the relevant sentence/span (e.g., a slim margin dot / underline on the span). It is calm, not alarming.
  - **Inline coaching prompt:** selecting the marker reveals a short developmental prompt **immediately adjacent to that span** (an inline popover/gutter card touching the text) — one focused invitation, in the coach's voice. From here the learner can edit the span right away.
  - **Primary action bar** (anchored to the document): **"Send to coach"** (first pass) / **"Send revision"** (after edits).
- **Right rail (secondary, ~28–30%, redefined — NOT the primary instructional surface):**
  - recent **coaching history** (resolved targets);
  - **revision history** (draft-to-draft);
  - optional **expanded explanations** (when the learner wants more on the current target);
  - **teacher-facing information** when appropriate.
  The rail is quiet and recessed; it supports and records, it does not host the primary interaction.

## 2. Visual hierarchy
The document is unmistakably the center — largest type, brightest surface, most space. The **single active marker/inline prompt** is the one terracotta accent and the only element competing for attention, and it sits *on the writing*. The right rail is muted stone and clearly secondary. Motion is minimal: the marker fades in on its span; on resolution it settles into rail history; the next target appears only after the current one is addressed.

## 3. Primary controls
- The **editable document** (always focusable/editable, even while the coach is thinking).
- The **anchored marker → inline prompt**, with the span editable immediately beneath/beside it.
- **Send to coach / Send revision** button. First submission → `writing`; every later submission of the edited document → `revise`.
- **Revision progress** (reads the assignment's revision expectations from the saved configuration).

## 4. Secondary controls (right rail + inline)
- **Coaching history** and **revision history** (review, and "what changed since last revision" diff highlight in the document).
- **Expanded explanation** for the current target (`explain`), and a compact **reply to the coach** (`answer`) for thinking aloud *without* changing the document — a genuine side channel, never the way revision happens.
- **"Show me more support"** — a gentle request for more scaffolding on the current target (engine still decides; never produces text for the learner).
- Assignment details expander; collapse/expand rail.

## 5. One target at a time (rule)
Compass normally surfaces **only one active coaching marker**. Do not distribute multiple simultaneous markers across the document. Maintain a single instructional focus until the learner has revised that portion of the draft; only then resolve it and anchor the next. (If the learner ignores it and edits elsewhere, the marker persists on its span until addressed or explicitly set aside.)

## 6. Empty states
- **No writing yet:** document shows a calm placeholder ("Begin your draft here — write what you actually think."). No marker, no rail chatter. A single quiet line near the canvas: *"Write something and I'll read it as a reader would. I won't write it for you."*
- **Coach thinking (durable polling):** a quiet in-document indicator ("Reading your draft…"); the document stays fully editable while the learner waits.
- **Between targets:** after a marker resolves and before the next arrives, the canvas is clean; the rail shows the just-resolved item. The learner is never stranded with an empty instructional surface.

## 7. Error states (never destroy the draft, never break focus)
- **Submission/engine failure:** the draft is preserved (local + autosave); a non-destructive retry appears near the document ("I couldn't read that just now — try again"). No lost text, no half-shown coaching.
- **Anti-coauthoring request:** the coach declines in character in the inline prompt and returns exactly one decision; the span is never auto-filled or auto-edited.
- **Empty/unchanged submission:** Send disabled with a hint ("Add or change something in your draft first") — protects the meaning of the revise loop.
- **Connectivity loss:** autosave preserves the draft; a quiet banner notes unsynced changes; submissions queue and send on reconnect.

## 8. Mobile considerations
The document is the default full-screen surface. The **single anchored marker** appears on its span; tapping it opens the short prompt as a compact card **adjacent to that span** (not a full-screen takeover), with the span editable right there. The right rail (history/explanations) lives behind one tab and is never required for the core cycle. **Send revision** is a sticky bottom button. The draft is never hidden behind coaching.

## 9. Mapping to the (frozen) engine — no engine change
- First document submission → `writing`; each subsequent submission of the edited document → `revise`.
- Inline "explain more" → `explain`; rail "reply to coach" → `answer`.
- The engine already surfaces a single instructional target per turn; the UI simply **anchors that one target to the span** its reasoning refers to. Durable polling drives responses; the document stays editable throughout.
- The document is a client-persistent, autosaved evolving object; each *submitted* version becomes a versioned turn server-side — consistent with the current architecture; no engine or API change.

## 10. Future expansion points
- Draft **version scrubber**; span-level revision replay feeding Revision Analytics.
- Multiple *dormant* targets queued (still shown one at a time) once single-focus is proven.
- Long-document section outline/navigation.
- Accommodations: adjustable type size, read-aloud, dyslexia-friendly font (support access, not lower expectations).
- Teacher replay of the anchored coaching + revision record (powers Dashboard / Analytics).

## What must never appear
Scores/grades/rubric-as-verdict; Compass writing/rewriting/auto-editing/auto-correcting the draft; engine internals or a Dev Panel; a chat stream that displaces the document or becomes the primary surface; multiple simultaneous coaching markers; any implication that revision is optional.

## Design goal (restated)
The learner experiences Compass as **coaching the writing itself** — one target, anchored to the text, revised in place — not as a separate conversation about writing. The document is always the center of attention.
