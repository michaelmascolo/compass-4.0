# Compass — Public Preview Redesign (Phase 4)

> The Preview must become a **faithful, shortened version of the canonical Student Workspace** (anchored, document-centered coaching) — not a separate chat model. Design only. Same frozen engine, same turn kinds, same durable polling. What differs from the full workspace is only scope and framing, never the interaction model.

## Principle
A teacher/evaluator should leave the Preview having experienced the *real* Compass interaction in miniature: they enter a short Grade-9 passage, Compass anchors ONE coaching target to a span, they revise that span in place, Compass reacts, and support fades. No chat surface. No simplified stand-in.

## What carries over unchanged (fidelity)
- **Document is the center.** The entered passage sits on the same paper canvas and is **editable in place**.
- **Anchored coaching.** One coaching marker attaches to the relevant span; selecting it reveals a short prompt adjacent to the text; the user revises right there; the marker resolves; the next single target appears.
- **One target at a time.** Same single-focus rule.
- **Same cycle & engine mapping.** First submit → `writing`; edited-passage resubmit → `revise`; "explain more" → `explain`. Durable polling; document stays editable while Compass reads.
- **Constitutional behavior.** Never rewrites/auto-corrects; declines coauthoring in character; no scores.

## What is intentionally shortened for the Preview (scope, not model)
- **Entry framing (unique to preview):** the existing setup screen stays — "Try Compass with a short piece of Grade 9 writing," optional essay-about + passage-type. This is the only place that explains it is a demonstration.
- **Scope:** a short passage (≈100–250 words), not a full essay; expect ~1–3 anchored targets total, then a graceful close.
- **Right rail:** minimal or hidden — coaching history/revision history are optional in the preview; the anchored inline coaching is the whole experience. (No teacher-facing info here.)
- **No top-bar assignment/progress chrome** beyond a calm minimal header; no dev tools.
- **Close/bridge:** after a target or two is revised and support fades, the "Bring your own writing / Continue" affordance leads to the Preview → Real Bridge (S3), grounded only in what the user just did.

## Layout (preview)
- **Setup screen (unchanged framing):** heading + instruction + optional context/type + large passage textarea + "Try Compass."
- **On submit → the miniature workspace:**
  - The passage renders on the **document canvas**, editable in place.
  - Compass reads (in-character "Reading your draft…"), then anchors **one marker** to the relevant span.
  - Selecting the marker shows the short inline prompt adjacent to the span; the user edits the span and clicks **Send revision**.
  - Compass reacts to the revision, resolves the marker, and either anchors the next single target or, once support has faded, offers the closing bridge.
- **No separate chat column.** A single optional "reply/explain" affordance may exist inline for thinking aloud, mirroring the full workspace's side channel — but revision happens in the document.

## States
- **Empty passage:** "Try Compass" disabled with hint "Enter a short passage to continue."
- **Thinking:** in-document "Reading your draft…"; passage stays editable.
- **Error:** passage never lost; quiet retry.
- **Coauthoring request:** in-character decline in the inline prompt; passage never auto-filled.
- **Close:** after ~1–3 resolved targets, a calm bridge card grounded in the user's own revisions.

## Mobile
Identical to the canonical workspace mobile behavior: document full-screen; the single marker opens a compact adjacent card; revision in place; sticky "Send revision"; optional history behind a tab.

## Engine mapping (no change)
Reuses `/interact` exactly: `writing` → `revise` → (`explain`/`answer` optional). The current preview-only Telos framing (Grade-9 passage, infer purpose, one target, never rewrite, invite revision, fade support) already matches this model; only the front-end presentation moves from the current single-column chat to the anchored document canvas.

## Migration note (for the future build, not now)
The current `PublicPreview.jsx` renders a single-column chat and sends replies as `answer`. Phase-4 implementation replaces that presentation with the anchored document canvas and uses `revise` for edited-passage resubmissions — bringing the Preview into full fidelity with the canonical Student Workspace. The backend requires no change.

## Deliverable status
Phase 4 Preview redesign — **for approval.** After approval, the remaining product (Teacher Home, the merged Create-Assignment authoring flow, Teacher Dashboard, Revision Analytics, Assignment Complete) is designed around this canonical student experience, and implementation can begin — starting with the canonical Student Workspace itself.
