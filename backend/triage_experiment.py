"""
EXPERIMENTAL — Conditional Triage Architecture (latency workstream).

This module is an ADDITIVE, experimental reasoning path that runs ALONGSIDE the
frozen production engine (server._run_engine). It NEVER modifies the frozen
SYSTEM_MESSAGE or the constitutional commitments. STAGE 2 still uses the frozen
SYSTEM_MESSAGE verbatim; triage only (a) narrows what STAGE 2 must analyze and
(b) trims the serialized output — exactly the levers approved for the preview R3
trim, now generalized behind an explicit rapid-triage decision.

Pipeline:
  STAGE 1  RAPID TRIAGE (new, tiny system message, tiny output)
           -> what changed, prior-target status, learner state, instructional
              route, inside/outside, foundational?, highest-leverage dimension,
              relevant instructional objects, confidence.  (replaces STAGE-A)
  early-exit routing (code): stall -> stall support; unchanged prior target ->
           keep target; resolved -> assess fade/advance; foundational -> FULL
           exhaustive fallback (broad reassessment via server._run_engine).
  STAGE 2  FOCUSED ANALYSIS (frozen SYSTEM_MESSAGE + focused user prompt +
           trimmed output) -> the single coaching move for the triaged dimension.
"""
import json
import time
import asyncio

import server
from server import (
    SYSTEM_MESSAGE, EMERGENT_LLM_KEY, LlmChat, UserMessage,
    Session, Telos, InteractRequest, Turn, DevelopmentalObservation,
    _extract_json, _parse_engine_output, _compact_theory,
    get_relevant_domain_data, get_relevant_instructional_objects,
    build_instructional_network, _developmental_profile_summary,
    _latest_block, _previous_draft, SHARED_DEV_RESOURCES, _DOMAINS_BY_NAME,
)

MODEL = ("anthropic", "claude-sonnet-4-6")


def _tok(s: str) -> int:
    """Approximate token count (chars/4) — LlmChat does not surface usage."""
    return round(len(s or "") / 4)


# ---------------------------------------------------------------------------
# STAGE 1 — RAPID INSTRUCTIONAL TRIAGE
# ---------------------------------------------------------------------------
TRIAGE_SYSTEM_MESSAGE = """You are the RAPID INSTRUCTIONAL TRIAGE stage of a developmental writing coach (Compass). You do NOT coach the student and you do NOT write any student-facing text. Your only job is to decide, quickly and with minimal analysis, what the single highest-leverage next coaching move is and which narrow analysis the deep stage should perform. Eliminate irrelevant branches.

You are given a compact, incrementally-maintained learner state (not the full transcript) and the student's latest submission. Answer ONLY the triage questions. Prefer a plausible focused hypothesis over exhaustive certainty; the coach will observe the learner's next action and revise.

DECISIONS:
1. text_changed: what changed since the previous draft (or "first draft").
2. prev_target_status: resolved | partially_resolved | unchanged | worse | none.
3. learner_state: engaged | stalled | confused | finished_with_target.
4. instructional_route: exactly one of — stall_support | inside_out_clarification | outside_in_reader_task | convention_instruction | transfer_test | support_fading.
5. inside_or_outside: inside_out (learner does not yet have sufficient control of intended meaning / purpose / position / idea) | outside_in (minimally adequate intention is present, so test how the writing functions for a reader / task / convention). ROUTING INVARIANT: do NOT stay inside_out once intended meaning is sufficiently clear — move promptly to an outside_in test.
6. foundational_problem: true ONLY when a BROAD reassessment across many dimensions is genuinely required — this should be RARE (expect well under a quarter of turns). Set true only if ANY: (a) the draft does not actually address the assignment / is off-task; (b) the writer's basic intended meaning or overall communicative purpose cannot be determined at all; (c) the writing is so incoherent across ideas that no single dimension can be worked in isolation. Do NOT set foundational just because the draft is weak, missing a thesis, imperfect, or not yet succeeding at the assignment's named skill — those are handled by selecting the RIGHT single dimension in (7), NOT by broad reassessment. When one dimension is clearly highest-leverage, foundational_problem is false even if the draft is quite weak.
7. highest_leverage_dimension: the ONE dimension to work. ANTI-NARROWING RULE — do NOT default to "central claim"/"thesis"/"purpose alignment" out of habit. Choose central claim ONLY when the writer genuinely lacks a claim/position or the claim is absent/unarguable. If the draft ALREADY presents a workable claim/position, select the LIVE DOWNSTREAM EDGE instead (e.g., evidence-interpretation, causal reasoning, paragraph focus, transitions/coherence, point-of-view consistency, conclusion completion, sentence clarity, convention). If a PRIOR coaching target on a downstream element is unresolved, keep working THAT element — do not retreat upstream to the claim. Always honor the ASSIGNMENT PURPOSE: if it names a specific element, that element (not a generic thesis) is the default focus.
8. relevant_instructional_objects: 1-2 canonical element names most relevant to the dimension (e.g., "Thesis", "Central Claim", "Evidence", "Paragraph", "Introduction", "Purpose", "Reader", "Organization", "Transitions", "Conclusion").
9. route_confidence: 0.0-1.0.
10. rationale: one sentence.

Respond with ONLY this compact JSON (no prose, no code fence):
{"text_changed":"...","prev_target_status":"...","learner_state":"...","instructional_route":"...","inside_or_outside":"...","foundational_problem":false,"highest_leverage_dimension":"...","relevant_instructional_objects":["..."],"route_confidence":0.0,"rationale":"..."}"""


def _prev_target(session: Session) -> str:
    sc = session.theory.scaffolding_control
    return sc.primary_target or ""


def _triage_state_summary(session: Session, req: InteractRequest) -> str:
    """Compact, incrementally-derived learner state — NOT the full transcript."""
    th = session.theory
    prof = session.developmental_profile
    prev = _previous_draft(session)
    strengths = [f"{o.element}: {o.control_statement} ({o.trend})" for o in prof if o.trend in ("consolidating", "independent")]
    needs = [f"{o.element}: {o.control_statement} ({o.trend})" for o in prof if o.trend in ("confused", "emerging", "developing")]
    cp = th.communicative_purpose
    lines = [
        f"ASSIGNMENT PURPOSE (telos): {session.telos.governing_pedagogical_purpose or session.pedagogical_purpose}",
        f"IMMEDIATE TASK: {session.telos.immediate_task_purpose or session.current_writing_task}",
        f"INFERRED COMMUNICATIVE PURPOSE: primary={getattr(cp,'primary','') or '?'} secondary={getattr(cp,'secondary',[]) or []}",
        f"ACTIVE COACHING TARGET (prior turn): {_prev_target(session) or '(none yet)'}",
        f"PRIOR INSTRUCTIONAL MODE: {th.scaffolding_control.instructional_mode or '(none)'}",
        f"KNOWN STRENGTHS: {strengths or '(none recorded)'}",
        f"UNRESOLVED DEVELOPMENTAL NEEDS: {needs or '(none recorded)'}",
        f"SUBMISSION KIND: {req.kind}",
    ]
    if req.kind in server.DRAFT_KINDS:
        lines.append(f"PREVIOUS DRAFT:\n{prev if prev else '(none — first draft)'}")
        lines.append(f"CURRENT DRAFT:\n{req.content}")
    else:
        lines.append(f"STUDENT REPLY (not a new draft): {req.content}")
    return "\n".join(lines)


async def run_triage(session: Session, req: InteractRequest) -> dict:
    prompt = _triage_state_summary(session, req)
    chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"triage-{session.id}",
                   system_message=TRIAGE_SYSTEM_MESSAGE).with_model(*MODEL)
    t0 = time.perf_counter()
    raw = await chat.send_message(UserMessage(text=prompt))
    dt = time.perf_counter() - t0
    data = _extract_json(raw)
    data["_prompt_tokens"] = _tok(prompt)
    data["_output_tokens"] = _tok(raw)
    data["_latency_s"] = round(dt, 2)
    return data


# ===========================================================================
# STAGE 2 — FOCUSED ANALYSIS (frozen SYSTEM_MESSAGE + governed focused prompt)
# ===========================================================================
# COMPASS GOVERNANCE IMPLEMENTATION v1 — Stage-2 Decomposition.
# Canonical reference: /app/memory/COMPASS_GOVERNANCE_ARCHITECTURE.md
#
# Authority flows downward L1 -> L5. The frozen SYSTEM_MESSAGE remains the
# AUTHORITATIVE source of Layer 1 (Constitutional Commitments) and Layer 2
# (Developmental Policy). This module NEVER paraphrases them into a competing
# constitution; it only (a) FOREGROUNDS the applicable invariants so they
# govern the focused turn, and (b) makes Layer 3 (Diagnostic Reasoning)
# CONDITIONAL on the triage route. Layer 4 (Learner Model) and Layer 5
# (Presentation) are unchanged in behavior; tagged here for traceability.
# The route->lens map below is the SINGLE implementation source of truth for
# conditional diagnostic activation and is pure + unit-testable.
# ---------------------------------------------------------------------------

# [L3] Diagnostic lenses (frozen SYSTEM_MESSAGE frameworks). Named here ONLY to
# ACTIVATE / hold dormant per route; their definitions live in SYSTEM_MESSAGE.
LENS = {
    "M6":   "M6 communicative-purpose re-inference",
    "M7":   "M7 functional paragraph analysis",
    "M8":   "M8 functional evidence & support analysis",
    "M9":   "M9 transitions & coherence analysis",
    "M10":  "M10 conclusion / completion analysis",
    "M12":  "M12 reader construction",
    "M13":  "M13 revision-as-development analysis",
    "IO":   "IO 12-step canonical element analysis",
    "CONV": "sentence-level analysis of the single convention at issue",
}
ALL_CONTENT_LENSES = ["M6", "M7", "M8", "M9", "M10", "M12", "IO", "CONV"]

# [L1 + governing L2] Minimum always-govern safety set. "Always run" = these
# ALWAYS GOVERN the output; they do NOT require lengthy written analysis of each
# item. Kept short deliberately so the always-on core never recreates latency.
MIN_SAFETY_SET = [
    "M6-thin: confirm the communicative purpose before instructing",
    "M5A anti-coauthoring boundary (never write/rewrite/supply copyable content)",
    "answer-the-assignment check (honor the teacher's named purpose; surface drift)",
    "restraint on competent performance (invent no deficiencies; proportional intervention)",
    "one instructional target + one learner-facing invitation; no scores",
    "stopping rules (honor independence requests / diminishing returns)",
]

# [L3] Route -> lens activation map. SINGLE SOURCE OF TRUTH for conditional
# diagnostic activation, keyed on the triage `instructional_route`. Each entry:
#   active_lenses        lenses that run this route (codes into LENS)
#   dimension_selected   whether a content lens is chosen from the dimension
#   permitted_moves      instructional move types allowed on this route
#   may_select_new_target whether a NEW target may be opened
#   consolidation_allowed / fading_allowed
#   fallback_if          the condition that forces the full-engine fallback
ROUTE_LENS_MAP = {
    "stall_support": {
        "active_lenses": [],  # no new broad diagnostic search
        "dimension_selected": False,
        "permitted_moves": ["developmental_question", "brief_demonstration", "reflection"],
        "may_select_new_target": False,
        "consolidation_allowed": False,
        "fading_allowed": False,
        "fallback_if": "the stall cannot be explained locally on the current edge and genuinely needs broad reassessment",
    },
    "inside_out_clarification": {
        "active_lenses": ["M6", "IO"],
        "dimension_selected": False,
        "permitted_moves": ["developmental_question", "explicit_instruction", "brief_demonstration"],
        "may_select_new_target": True,
        "consolidation_allowed": False,
        "fading_allowed": False,
        "fallback_if": "the learner's basic intended meaning / overall communicative purpose cannot be determined at all",
    },
    "outside_in_reader_task": {
        "active_lenses": ["M12"],  # reader model + the dimension-selected content lens
        "dimension_selected": True,
        "permitted_moves": ["developmental_question", "explicit_instruction", "brief_demonstration", "guided_revision"],
        "may_select_new_target": True,
        "consolidation_allowed": False,
        "fading_allowed": False,
        "fallback_if": "the writing is so incoherent across ideas that no single dimension can be worked in isolation",
    },
    "convention_instruction": {
        "active_lenses": ["CONV"],
        "dimension_selected": False,
        "permitted_moves": ["explicit_instruction", "brief_demonstration", "developmental_question"],
        "may_select_new_target": True,
        "consolidation_allowed": False,
        "fading_allowed": False,
        "fallback_if": "the convention problem is actually a symptom of a deeper meaning / organization problem",
    },
    "transfer_test": {
        "active_lenses": ["M13"],
        "dimension_selected": False,
        "permitted_moves": ["reflection", "developmental_question", "consolidation"],
        "may_select_new_target": False,
        "consolidation_allowed": True,
        "fading_allowed": True,
        "fallback_if": "the transfer test reveals the prior gain did not hold and a new foundational issue emerged",
    },
    "support_fading": {
        "active_lenses": ["M13"],
        "dimension_selected": False,
        "permitted_moves": ["consolidation", "reflection", "developmental_question"],
        "may_select_new_target": False,
        "consolidation_allowed": True,
        "fading_allowed": True,
        "fallback_if": "fading reveals the target was not actually consolidated (regression)",
    },
}
_DEFAULT_ROUTE = "outside_in_reader_task"

# [L3] dimension keyword -> content lens, used only when dimension_selected.
# M12 (reader) is the baseline for outside-in, so it is NOT listed here.
DIMENSION_LENS_KEYWORDS = [
    ("M8",  ("evidence", "support", "cite", "citation", "quotation", "quote", "source", "data", "proof", "attribut", "integrat", "synthes")),
    ("M9",  ("transition", "coheren", "cohesion", "organiz", "flow", "connect", "sequenc", "order", "structur", "parallel")),
    ("M10", ("conclusion", "ending", "closing", "completion", "resolve", "resolution")),
    ("M7",  ("paragraph", "topic sentence", "unity", "development", "showing", "scene", "pacing")),
]

# prev_target_status -> the L2/L3 handling rule foregrounded in the directive.
_PREV_TARGET_RULES = {
    "unchanged": "keep the SAME prior coaching target; do not search for a new one.",
    "partially_resolved": "the prior target is only partially met; keep working THAT element.",
    "resolved": "the prior target is resolved; consolidate the gain and only advance if a clearly more important target has become primary.",
    "worse": "the prior target regressed; return to it with a DIFFERENT scaffold.",
    "none": "no prior target; select the single highest-leverage target for the triaged dimension.",
}


def select_content_lens(triage: dict) -> str:
    """Pick ONE content lens (M7/M8/M9/M10) for a dimension-selected route from
    the triaged dimension + instructional-object names. Returns '' when the
    reader model (M12) alone suffices. Pure + unit-testable."""
    io_names = [n for n in (triage.get("relevant_instructional_objects") or []) if isinstance(n, str)]
    dims = " ".join([str(triage.get("highest_leverage_dimension", ""))] + io_names).lower()
    for code, kws in DIMENSION_LENS_KEYWORDS:
        if any(k in dims for k in kws):
            return code
    return ""


def resolve_route_activation(triage: dict, has_prior_draft: bool) -> dict:
    """Resolve the concrete L3 lens activation + move policy for THIS turn from
    ROUTE_LENS_MAP (single source of truth). Pure + unit-testable."""
    route = (triage.get("instructional_route") or "").strip() or _DEFAULT_ROUTE
    base = ROUTE_LENS_MAP.get(route) or ROUTE_LENS_MAP[_DEFAULT_ROUTE]
    active = list(base["active_lenses"])
    if base.get("dimension_selected"):
        lens = select_content_lens(triage)
        if lens and lens not in active:
            active.append(lens)
    # M13 revision lens is conditional-on-revise regardless of route.
    if has_prior_draft and "M13" not in active:
        active.append("M13")
    dormant = [c for c in (ALL_CONTENT_LENSES + ["M13"]) if c not in active]
    may_new = base["may_select_new_target"]
    consolidation = base["consolidation_allowed"]
    fading = base["fading_allowed"]
    prev = (triage.get("prev_target_status") or "none").strip()
    if prev not in _PREV_TARGET_RULES:
        prev = "none"
    if prev == "unchanged":
        may_new = False
    elif prev == "resolved":
        consolidation = True
    return {
        "route": route,
        "active_lenses": active,
        "dormant_lenses": dormant,
        "permitted_moves": base["permitted_moves"],
        "may_select_new_target": may_new,
        "consolidation_allowed": consolidation,
        "fading_allowed": fading,
        "fallback_if": base["fallback_if"],
        "prev_target_status": prev,
    }


# Directive template. Uses @@..@@ placeholders (NOT .format) so the literal JSON
# braces in the output contract need no escaping.
_FOCUSED_OVERRIDE_TEMPLATE = """

=== FOCUSED ANALYSIS DIRECTIVE — COMPASS GOVERNANCE v1 (rapid triage already ran) ===
This directive narrows the diagnostic work required for the current route. It does not replace, revise, weaken, or supersede any constitutional commitment or developmental policy in the governing SYSTEM_MESSAGE.

[L1 CONSTITUTIONAL COMMITMENTS + L2 DEVELOPMENTAL POLICY — ALWAYS GOVERN, on every route]
Your governing SYSTEM_MESSAGE remains fully in force and is authoritative. Let these invariants GOVERN this turn — govern the decision; do NOT write a long analysis of each: anti-coauthoring (never write, rewrite, or supply copyable content); the learner owns the writing; answer-the-assignment and honor the teacher's named purpose; function before convention; EXACTLY ONE instructional target and ONE learner-facing invitation; restraint on competent performance (invent no deficiencies; keep intervention proportional); no scores; honor stopping rules (independence request / diminishing returns); move promptly from inside-out clarification to an outside-in test once intended meaning is sufficiently clear.

[L3 DIAGNOSTIC REASONING — CONDITIONAL on the triage route THIS turn]
Run ONLY the diagnostic lens(es) listed ACTIVE below. Hold the DORMANT lenses off — do not scan, diagnose, or serialize them. Read only the minimum context needed to interpret the active lens.
ROUTE: @@ROUTE@@
ACTIVE lens(es): @@ACTIVE@@
DORMANT lens(es) (do not run): @@DORMANT@@
Permitted instructional move(s): @@MOVES@@
May select a NEW instructional target this turn: @@NEWTARGET@@
Consolidation allowed: @@CONSOLIDATION@@ | Support-fading allowed: @@FADING@@
prev_target_status = @@PREV@@ -> @@PREVRULE@@

[L3 ANTI-SUPPRESSION FALLBACK — the route may NOT hide a foundational problem]
If, while analyzing, you find evidence INCONSISTENT with this route — specifically that @@FALLBACKIF@@, or the draft does not actually address the assignment — do NOT force the material into the active lens and do NOT fabricate a focused answer. Instead set "route_fallback_required": true with a one-sentence "route_fallback_reason"; the system will then re-run the full exhaustive engine for a broad reassessment. Use this ONLY for a genuine foundational mismatch (rare).

[L4 LEARNER MODEL] Record observed learner state + revision evidence truthfully; never fabricate growth or a conclusion the text does not support.
[L5 PRESENTATION] Produce exactly ONE learner-facing invitation in the coach's voice, anchored to the learner's document; no scores, no rewriting.

TRIAGE DECISION:
@@TRIAGE@@

[L5 OUTPUT CONTRACT] Serialize ONLY these top-level keys (omit all others — they are not needed this turn and omitting them changes nothing about your judgment):
{
  "route_fallback_required": false,
  "route_fallback_reason": "",
  "student_facing_invitation": "...",
  "theory": {
    "communicative_purpose": {...},
    "scaffolding_control": {...},
    "instructional_reasoning": {...},
    "revision_development": {...}
  },
  "candidate_invitations": [...],
  "selected_invitation": {...},
  "intervention": {...}
}
Generate EXACTLY TWO internal candidate_invitations, then select ONE — the two candidates remain internal and only the single student_facing_invitation reaches the learner. theory.scaffolding_control MUST contain exactly one primary_target (the triaged dimension). Include theory.revision_development only when a prior draft exists to compare. Output compact JSON."""


def build_focused_override(triage: dict, has_prior_draft: bool) -> str:
    """Generate the governed Stage-2 directive from ROUTE_LENS_MAP (L1/L2 always
    on; L3 conditional). Everything is derived from the map — no free-text
    routing table is maintained separately."""
    act = resolve_route_activation(triage, has_prior_draft)

    def _names(codes):
        return ", ".join(LENS[c] for c in codes) if codes else "(none — constitutional/policy core only)"

    triage_json = json.dumps({k: triage.get(k) for k in (
        "instructional_route", "inside_or_outside", "prev_target_status",
        "learner_state", "highest_leverage_dimension", "route_confidence", "rationale")}, indent=2)
    repl = {
        "@@ROUTE@@": act["route"],
        "@@ACTIVE@@": _names(act["active_lenses"]),
        "@@DORMANT@@": _names(act["dormant_lenses"]),
        "@@MOVES@@": ", ".join(act["permitted_moves"]),
        "@@NEWTARGET@@": "yes" if act["may_select_new_target"] else "no — keep the current target",
        "@@CONSOLIDATION@@": "yes" if act["consolidation_allowed"] else "no",
        "@@FADING@@": "yes" if act["fading_allowed"] else "no",
        "@@FALLBACKIF@@": act["fallback_if"],
        "@@PREV@@": act["prev_target_status"],
        "@@PREVRULE@@": _PREV_TARGET_RULES[act["prev_target_status"]],
        "@@TRIAGE@@": triage_json,
    }
    out = _FOCUSED_OVERRIDE_TEMPLATE
    for k, v in repl.items():
        out = out.replace(k, v)
    return out


def _focused_prompt(session: Session, req: InteractRequest, triage: dict, selections: list, io_names: list) -> str:
    full_domain_data = get_relevant_domain_data(selections)
    io_objects = get_relevant_instructional_objects(io_names or [])
    io_network = build_instructional_network(io_objects)
    has_prior = req.kind in server.DRAFT_KINDS and bool(_previous_draft(session))
    override = build_focused_override(triage, has_prior)
    return f"""CURRENT DEVELOPMENTAL TELOS (component A — provisional, revisable):
{json.dumps(session.telos.model_dump(), indent=2)}

COMPACT CURRENT DEVELOPMENTAL THEORY (component C — your evolving theory so far):
{json.dumps(_compact_theory(session.theory), indent=2)}

TRIAGED DIMENSION FOR THIS TURN (analyze ONLY this): {triage.get('highest_leverage_dimension')}
ROUTE: {triage.get('instructional_route')} | {triage.get('inside_or_outside')} | prior target status: {triage.get('prev_target_status')} | learner: {triage.get('learner_state')}

RELEVANT CANONICAL DOMAIN DATA (cultural resources loaded as DATA for the triaged dimension):
{json.dumps(full_domain_data, indent=2)}

RETRIEVED INSTRUCTIONAL OBJECTS (canonical knowledge that GOVERNS instruction — reason FROM these):
{json.dumps(io_objects, indent=2)}

INSTRUCTIONAL NETWORK (related elements — use for coherence only; still ONE target):
{json.dumps(io_network, indent=2)}

DEVELOPMENTAL PROFILE (accumulated control across prior episodes — scaffold from here):
{_developmental_profile_summary(session)}

SHARED DEVELOPMENTAL RESOURCE MENU:
{json.dumps(SHARED_DEV_RESOURCES, indent=2)}

{_latest_block(session, req)}

Run the governed instructional reasoning FOR THE TRIAGED DIMENSION ONLY, then respond with ONLY the JSON object described in your instructions.{override}"""


def _resolve_io(triage: dict):
    """Map triage's element names to (selections, io_names) without a STAGE-A call.
    Falls back to a whole-essay-purpose default when nothing matches."""
    io_names = [n for n in (triage.get("relevant_instructional_objects") or []) if isinstance(n, str)][:2]
    # map to canonical domains by loose containment
    dims = " ".join([triage.get("highest_leverage_dimension", "")] + io_names).lower()
    sel = []
    KEY = [
        ("Central Claim / Thesis", ("thesis", "claim", "position")),
        ("Opening / Introduction", ("intro", "opening", "hook")),
        ("Paragraph Purpose", ("paragraph", "topic sentence")),
        ("Whole Essay Purpose", ("purpose", "assignment", "whole")),
        ("Audience Awareness", ("reader", "audience")),
    ]
    for dom, kws in KEY:
        if dom in _DOMAINS_BY_NAME and any(k in dims for k in kws):
            sel.append({"domain_name": dom, "sections": []})
    if not sel:
        sel = [{"domain_name": "Whole Essay Purpose", "sections": []}] if "Whole Essay Purpose" in _DOMAINS_BY_NAME else []
    if not io_names:
        io_names = ["Thesis"]
    return sel[:3], io_names


async def run_focused(session: Session, req: InteractRequest, triage: dict) -> dict:
    selections, io_names = _resolve_io(triage)
    prompt = _focused_prompt(session, req, triage, selections, io_names)
    t0 = time.perf_counter()
    last_err = None
    raw = ""
    # Single retry on recoverable (unreadable / no-invitation) failures — parity
    # with the exhaustive path's retry. No other architectural change.
    for attempt in range(2):
        chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"focused-{session.id}-{attempt}",
                       system_message=SYSTEM_MESSAGE).with_model(*MODEL)
        raw = await chat.send_message(UserMessage(text=prompt))
        try:
            parsed = _parse_engine_output(session, raw)
            break
        except ValueError as e:
            last_err = e
            continue
    else:
        raise last_err
    dt = time.perf_counter() - t0
    # [L3] anti-suppression fallback signal — the focused pass may flag when the
    # triage route cannot contain the actual problem (a foundational mismatch).
    fb_required, fb_reason = False, ""
    try:
        _fb = _extract_json(raw)
        fb_required = bool(_fb.get("route_fallback_required"))
        fb_reason = (_fb.get("route_fallback_reason") or "") if fb_required else ""
    except Exception:
        pass
    parsed["_route_fallback"] = fb_required
    parsed["_route_fallback_reason"] = fb_reason
    parsed["_meta"] = {
        "focused_prompt_tokens": _tok(prompt),
        "focused_output_tokens": _tok(raw),
        "t_focused_s": round(dt, 2),
        "reasoner_prompt_bytes": len(prompt),
        "reasoner_output_bytes": len(raw),
        "candidate_count_directive": 2,  # L2: exactly two internal candidates
    }
    return parsed


async def run_triage_pipeline(session: Session, req: InteractRequest) -> dict:
    """STAGE 1 triage -> early-exit routing -> STAGE 2 focused (or full fallback)."""
    t0 = time.perf_counter()
    triage = await run_triage(session, req)
    foundational = bool(triage.get("foundational_problem"))
    if foundational:
        # broad reassessment genuinely required -> use the full frozen engine
        result = await server._run_engine(session, req)
        m = result.get("_meta", {})
        result["_triage"] = triage
        result["_triage_meta"] = {
            "path": "foundational_fallback_full",
            "triage_latency_s": triage["_latency_s"],
            "triage_prompt_tokens": triage["_prompt_tokens"],
            "triage_output_tokens": triage["_output_tokens"],
            "focused_latency_s": None,
            "total_latency_s": round(time.perf_counter() - t0, 2),
            "num_model_calls": 1 + 1,  # triage + full stage-B (full also runs its own stage-A)
            "prompt_tokens": triage["_prompt_tokens"] + _tok("") + int((m.get("reasoner_prompt_bytes") or 0) / 4),
            "output_tokens": triage["_output_tokens"] + int((m.get("reasoner_output_bytes") or 0) / 4),
        }
        return result
    result = await run_focused(session, req, triage)
    # [L3] anti-suppression: the route may not hide a foundational problem. If
    # the focused pass flagged a genuine mismatch, escalate to the full engine.
    if result.get("_route_fallback"):
        focused_latency = result.get("_meta", {}).get("t_focused_s")
        full = await server._run_engine(session, req)
        m = full.get("_meta", {})
        full["_triage"] = triage
        full["_triage_meta"] = {
            "path": "route_fallback_full",
            "route_fallback_reason": result.get("_route_fallback_reason", ""),
            "triage_latency_s": triage["_latency_s"],
            "focused_latency_s": focused_latency,
            "total_latency_s": round(time.perf_counter() - t0, 2),
            "num_model_calls": 4,  # triage + focused + full stage-A + full stage-B
            "prompt_tokens": triage["_prompt_tokens"] + int((m.get("reasoner_prompt_bytes") or 0) / 4),
            "output_tokens": triage["_output_tokens"] + int((m.get("reasoner_output_bytes") or 0) / 4),
        }
        return full
    fm = result["_meta"]
    result["_triage"] = triage
    result["_triage_meta"] = {
        "path": "triage_focused",
        "triage_latency_s": triage["_latency_s"],
        "focused_latency_s": fm["t_focused_s"],
        "total_latency_s": round(time.perf_counter() - t0, 2),
        "num_model_calls": 2,
        "prompt_tokens": triage["_prompt_tokens"] + fm["focused_prompt_tokens"],
        "output_tokens": triage["_output_tokens"] + fm["focused_output_tokens"],
    }
    return result


async def run_exhaustive(session: Session, req: InteractRequest) -> dict:
    t0 = time.perf_counter()
    result = await server._run_engine(session, req)
    m = result.get("_meta", {})
    result["_exhaustive_meta"] = {
        "path": "exhaustive_full",
        "stage_a_latency_s": m.get("t_stage_a_selector_s"),
        "stage_b_latency_s": m.get("t_stage_b_reasoner_s"),
        "total_latency_s": round(time.perf_counter() - t0, 2),
        "num_model_calls": 2,
        "prompt_tokens": int((m.get("reasoner_prompt_bytes") or 0) / 4),
        "output_tokens": int((m.get("reasoner_output_bytes") or 0) / 4),
    }
    return result


# ---------------------------------------------------------------------------
# STREAMING (perceived-latency only; does NOT alter the instructional decision)
# ---------------------------------------------------------------------------
def _extract_partial_invitation(raw: str) -> str:
    """Extract the in-progress value of the FIRST-emitted student_facing_invitation
    field from a partially-streamed JSON string."""
    key = raw.find('"student_facing_invitation"')
    if key == -1:
        return ""
    colon = raw.find(":", key)
    if colon == -1:
        return ""
    q = raw.find('"', colon)
    if q == -1:
        return ""
    out, i = [], q + 1
    esc = {"n": "\n", "t": "\t", '"': '"', "\\": "\\"}
    while i < len(raw):
        c = raw[i]
        if c == "\\" and i + 1 < len(raw):
            out.append(esc.get(raw[i + 1], raw[i + 1]))
            i += 2
            continue
        if c == '"':
            break
        out.append(c)
        i += 1
    return "".join(out)


async def run_focused_streaming(session: Session, req: InteractRequest, triage: dict, on_delta) -> dict:
    """Focused Stage 2, streamed. Emits the invitation to `on_delta` as it is
    generated (invitation is the first serialized field), then parses the full
    payload. Retries once non-streaming on unreadable output."""
    from emergentintegrations.llm.chat import TextDelta
    selections, io_names = _resolve_io(triage)
    prompt = _focused_prompt(session, req, triage, selections, io_names)
    t0 = time.perf_counter()
    raw = ""
    last_emit, last_len = 0.0, 0
    chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"focused-{session.id}",
                   system_message=SYSTEM_MESSAGE).with_model(*MODEL)
    try:
        async for ev in chat.stream_message(UserMessage(text=prompt)):
            if isinstance(ev, TextDelta) and ev.content:
                raw += ev.content
                partial = _extract_partial_invitation(raw)
                now = time.perf_counter()
                if partial and (len(partial) - last_len >= 12 or now - last_emit > 0.6):
                    last_emit, last_len = now, len(partial)
                    try:
                        await on_delta(partial)
                    except Exception:
                        pass
    except Exception:
        raw = ""  # streaming failed; fall through to non-streaming retry
    try:
        parsed = _parse_engine_output(session, raw)
    except ValueError:
        chat2 = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"focused-{session.id}-r",
                        system_message=SYSTEM_MESSAGE).with_model(*MODEL)
        raw = await chat2.send_message(UserMessage(text=prompt))
        parsed = _parse_engine_output(session, raw)
    dt = time.perf_counter() - t0
    fb_required, fb_reason = False, ""
    try:
        _fb = _extract_json(raw)
        fb_required = bool(_fb.get("route_fallback_required"))
        fb_reason = (_fb.get("route_fallback_reason") or "") if fb_required else ""
    except Exception:
        pass
    parsed["_route_fallback"] = fb_required
    parsed["_route_fallback_reason"] = fb_reason
    parsed["_meta"] = {
        "focused_prompt_tokens": _tok(prompt),
        "focused_output_tokens": _tok(raw),
        "t_focused_s": round(dt, 2),
        "reasoner_prompt_bytes": len(prompt),
        "reasoner_output_bytes": len(raw),
        "candidate_count_directive": 2,
    }
    return parsed


async def run_triage_pipeline_streaming(session: Session, req: InteractRequest, on_delta) -> dict:
    """Streaming variant of the triage pipeline. Foundational cases fall back to
    the full (non-streaming) frozen engine, exactly as the non-streaming path."""
    t0 = time.perf_counter()
    triage = await run_triage(session, req)
    if bool(triage.get("foundational_problem")):
        result = await server._run_engine(session, req)
        m = result.get("_meta", {})
        result["_triage"] = triage
        result["_triage_meta"] = {
            "path": "foundational_fallback_full",
            "triage_latency_s": triage["_latency_s"],
            "focused_latency_s": None,
            "total_latency_s": round(time.perf_counter() - t0, 2),
            "num_model_calls": 2,
            "prompt_tokens": triage["_prompt_tokens"] + int((m.get("reasoner_prompt_bytes") or 0) / 4),
            "output_tokens": triage["_output_tokens"] + int((m.get("reasoner_output_bytes") or 0) / 4),
        }
        return result
    result = await run_focused_streaming(session, req, triage, on_delta)
    # [L3] anti-suppression escalation (rare). In streaming, the full-engine
    # result supersedes the streamed focused invitation; emit the final text so
    # the surface reflects the finalized invitation.
    if result.get("_route_fallback"):
        focused_latency = result.get("_meta", {}).get("t_focused_s")
        full = await server._run_engine(session, req)
        try:
            await on_delta(full.get("invitation", ""))
        except Exception:
            pass
        m = full.get("_meta", {})
        full["_triage"] = triage
        full["_triage_meta"] = {
            "path": "route_fallback_full",
            "route_fallback_reason": result.get("_route_fallback_reason", ""),
            "triage_latency_s": triage["_latency_s"],
            "focused_latency_s": focused_latency,
            "total_latency_s": round(time.perf_counter() - t0, 2),
            "num_model_calls": 4,
            "prompt_tokens": triage["_prompt_tokens"] + int((m.get("reasoner_prompt_bytes") or 0) / 4),
            "output_tokens": triage["_output_tokens"] + int((m.get("reasoner_output_bytes") or 0) / 4),
        }
        return full
    fm = result["_meta"]
    result["_triage"] = triage
    result["_triage_meta"] = {
        "path": "triage_focused",
        "triage_latency_s": triage["_latency_s"],
        "focused_latency_s": fm["t_focused_s"],
        "total_latency_s": round(time.perf_counter() - t0, 2),
        "num_model_calls": 2,
        "prompt_tokens": triage["_prompt_tokens"] + fm["focused_prompt_tokens"],
        "output_tokens": triage["_output_tokens"] + fm["focused_output_tokens"],
    }
    return result
