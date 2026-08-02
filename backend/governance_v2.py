"""Compass Governance v2 — three-pass instructional orchestrator (behind
reasoning_mode="governance_v2"). Authoritative contract:
/app/memory/COMPASS_GOVERNANCE_V2_ARCHITECTURE.md

Control-architecture change, NOT a knowledge rewrite. The frozen SYSTEM_MESSAGE
is the instructional Knowledge Base (used verbatim as the Pass-3 system message);
this orchestrator owns the reasoning SEQUENCE and emits the reasoning ledger.

Passes (7 conceptual stages, 3 model calls):
  Pass 1 (S1 Purpose · S2 Writing Unit · S3 Canonical Functional Model)
  Pass 2 (S4 Functional Interpretation · S5 Single Instructional Target)
  Pass 3 (S6 Developmental Strategy · S7 Dialogue / Explicit Teaching)  -> KB
Branches: B1 Purpose-Unclear, B2 Prewriting, B3 Foundational Fallback,
plus the bounded assignment-understanding repair (§10.9).
"""
import json
import time

import server
from server import (
    Session, InteractRequest, LlmChat, UserMessage, EMERGENT_LLM_KEY,
    SYSTEM_MESSAGE, _extract_json, _parse_engine_output,
)


def _tok(s: str) -> int:
    return int(len(s or "") / 4)


async def _chat(system_message: str, user: str, sid: str) -> str:
    chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=sid,
                   system_message=system_message).with_model("anthropic", "claude-sonnet-4-6")
    return await chat.send_message(UserMessage(text=user))


def _ctx(session: Session, req: InteractRequest) -> str:
    t = session.telos
    prior = ""
    drafts = [x.content for x in session.turns if x.role == "student" and x.kind in server.DRAFT_KINDS]
    if drafts:
        prior = drafts[-1]
    return (
        f"ASSIGNMENT (teacher): {t.assignment_context or session.assignment}\n"
        f"TEACHER PEDAGOGICAL PURPOSE: {t.governing_pedagogical_purpose or session.pedagogical_purpose}\n"
        f"IMMEDIATE TASK: {t.immediate_task_purpose or session.current_writing_task}\n"
        f"TEACHER NOTES: {(session.teacher_notes or '')[:1200]}\n"
        f"PRIOR STUDENT DRAFT (if any): {prior[:1500]}\n"
        f"CURRENT STUDENT SUBMISSION ({req.kind}):\n{req.content}\n"
    )


# ---------------------------------------------------------------------------
# PASS 1 — S1 Purpose · S2 Writing Unit · S3 Canonical Functional Model
# Dedicated v2 prompt (NOT the v1 triage pass). Interpret-before-instruct: this
# pass ONLY orients; it does not diagnose quality, model the learner, or teach.
# ---------------------------------------------------------------------------
_P1_SYSTEM = (
    "You are the ORIENTATION pass of Compass Governance v2, a developmental writing tutor. "
    "Your ONLY job this pass is to establish the instructional context for a single student turn. "
    "You do NOT judge writing quality, do NOT model the learner, do NOT select a coaching target, "
    "and do NOT teach. Work strictly in this order and record what you find:\n"
    "S1 PURPOSE — determine two purposes SEPARATELY: (a) ASSIGNMENT PURPOSE = what the teacher is asking "
    "students to accomplish; (b) STUDENT PURPOSE = what the student's writing suggests THEY believe they are "
    "trying to accomplish. Compute purpose_alignment (aligned|partial|divergent). Divergence is recorded as a "
    "signal, not acted on here.\n"
    "S2 WRITING UNIT — identify the current instructional object the student is working on "
    "(prewriting, thesis, introduction, body_paragraph, evidence, transition, conclusion, whole_draft).\n"
    "S3 CANONICAL FUNCTIONAL MODEL — list the communicative FUNCTIONS that unit must perform FOR A READER "
    "(function over form: these are communicative tools, not a rigid template; multiple realizations are valid), "
    "and what the reader needs from this unit.\n"
    "Reader-centered throughout. Respond with ONLY a compact JSON object."
)


def _p1_prompt(session: Session, req: InteractRequest) -> str:
    return (
        _ctx(session, req)
        + "\nReturn ONLY this JSON:\n"
        '{\n'
        '  "assignment_purpose": "what the teacher is asking students to accomplish",\n'
        '  "student_purpose": "what the student appears to believe they are trying to accomplish",\n'
        '  "purpose_alignment": "aligned|partial|divergent",\n'
        '  "purpose_confidence": 0.0,\n'
        '  "purpose_source": "teacher|student_stated|inferred",\n'
        '  "assignment_alignment": "on_task|drift|off_task",\n'
        '  "student_purpose_indeterminate": false,\n'
        '  "writing_unit": "thesis|introduction|body_paragraph|evidence|transition|conclusion|whole_draft|prewriting",\n'
        '  "unit_scope": "local|whole_draft",\n'
        '  "unit_confidence": 0.0,\n'
        '  "functional_model": ["communicative function this unit performs for a reader", "..."],\n'
        '  "reader_needs": ["what the reader needs from this unit", "..."]\n'
        '}'
    )


# ---------------------------------------------------------------------------
# PASS 2 — S4 Functional Interpretation · S5 Single Instructional Target
# Produces a functional REPRESENTATION (not quality labels). Understand, then
# select exactly ONE target (greatest leverage AND preserves forward progress).
# ---------------------------------------------------------------------------
_P2_SYSTEM = (
    "You are the INTERPRETATION-AND-TARGET pass of Compass Governance v2. You have been given the "
    "communicative purpose, the current writing unit, and that unit's canonical functional model. "
    "Work in order:\n"
    "S4 FUNCTIONAL INTERPRETATION — produce a functional REPRESENTATION of what the student's writing is "
    "currently DOING (or attempting) for a reader, interpreted against the functional model. Describe function, "
    "not quality. Do NOT write quality labels like 'thesis weak'; instead describe communicative work, e.g. "
    "'the writer appears to be attempting to state a position, but the statement does not yet organize the essay "
    "for the reader.' RESTRAINT: never invent a deficiency; respect competent work.\n"
    "S5 INSTRUCTIONAL TARGET — select EXACTLY ONE target: the issue with the greatest developmental leverage "
    "that ALSO preserves forward progress toward completing the assignment (do not send the student into an "
    "unbounded detour). Do NOT model the learner and do NOT teach yet.\n"
    "Also flag: whether the weakness reflects INSUFFICIENT CONCEPTUAL ORGANIZATION (no developed idea for the "
    "unit's functions to organize — NOT merely weak prose); whether the writing is OFF-TASK or incoherent across "
    "ideas; and whether an assignment misunderstanding is so severe it BLOCKS meaningful work on the unit. "
    "Respond with ONLY a compact JSON object."
)


def _p2_prompt(session: Session, req: InteractRequest, l1: dict) -> str:
    return (
        _ctx(session, req)
        + "\nPASS-1 ORIENTATION (do not re-derive):\n" + json.dumps({
            k: l1.get(k) for k in ("assignment_purpose", "student_purpose", "purpose_alignment",
                                   "writing_unit", "unit_scope", "functional_model", "reader_needs")
        }, indent=2)
        + "\n\nReturn ONLY this JSON:\n"
        '{\n'
        '  "functional_representation": "prose account of what the writing is currently doing for a reader",\n'
        '  "function_status": [{"function": "...", "functional_reading": "what this part is doing/attempting for the reader", "status": "working|attempting|absent", "evidence": "quote or span"}],\n'
        '  "reader_gap_summary": "what the reader still needs",\n'
        '  "conceptual_organization": "sufficient|insufficient",\n'
        '  "off_task_or_incoherent": false,\n'
        '  "assignment_misunderstanding_blocks": false,\n'
        '  "primary_target": "the single function/aspect of the unit to work on",\n'
        '  "leverage_rationale": "why this has the greatest developmental leverage",\n'
        '  "forward_progress_rationale": "how addressing this keeps the student moving toward completing the assignment",\n'
        '  "target_continuity": "new|continued|resolved_advance"\n'
        '}'
    )


# ---------------------------------------------------------------------------
# PASS 3 — S6 Developmental Strategy · S7 Dialogue / Explicit Teaching
# Uses the FROZEN SYSTEM_MESSAGE as the Knowledge Base (system message). Learner
# modeling + developmental reasoning BEGIN here. Explicit, reader-centered
# teaching via the 5-step pattern. Emits the frozen output contract + ledger.
# ---------------------------------------------------------------------------
def _p3_prompt(session: Session, req: InteractRequest, l1: dict, l2: dict, mode: str) -> str:
    mode_directive = {
        "normal": "MODE: normal. Teach the selected target for the current writing unit.",
        "prewriting": (
            "MODE: PREWRITING. The interpretation found INSUFFICIENT CONCEPTUAL ORGANIZATION (not merely weak "
            "prose). Temporarily treat the unit as PREWRITING: the target is to help the student organize their "
            "thinking (generate/clarify the idea, form the claim, structure the thought) BEFORE returning to "
            "drafting. Explicitly teach the prewriting move; the student does the thinking."),
        "assignment_repair": (
            "MODE: ASSIGNMENT-UNDERSTANDING REPAIR. The student's purpose diverges from the assignment purpose "
            "so substantially that productive instruction cannot proceed. BRIEFLY repair the student's "
            "understanding of what the assignment is asking (reader-centered), then point them back toward "
            "productive work. Keep this bounded — do not abandon the writing; one invitation."),
    }[mode]
    return (
        "=== COMPASS GOVERNANCE v2 — PASS 3 (Developmental Strategy + Explicit Teaching) ===\n"
        "The orientation (S1-S3) and interpretation/target (S4-S5) stages have ALREADY run. Their outputs are the "
        "authoritative context below. Do NOT re-diagnose broadly and do NOT change the selected target; your job is "
        "S6 (invoke the learner model / ZPD / scaffolding for THIS target only) then S7 (generate ONE learner-facing "
        "coaching turn). Honor every constitutional commitment in your system message EXACTLY (anti-coauthoring, one "
        "target, one invitation, restraint, no scores, stopping rules, honor the teacher's purpose).\n\n"
        + _ctx(session, req)
        + "\nS1-S3 ORIENTATION:\n" + json.dumps({
            k: l1.get(k) for k in ("assignment_purpose", "student_purpose", "purpose_alignment",
                                   "writing_unit", "functional_model", "reader_needs")}, indent=2)
        + "\n\nS4-S5 INTERPRETATION & TARGET (authoritative — use this target):\n" + json.dumps({
            k: l2.get(k) for k in ("functional_representation", "reader_gap_summary", "primary_target",
                                   "leverage_rationale", "forward_progress_rationale", "target_continuity")}, indent=2)
        + f"\n\n{mode_directive}\n\n"
        "S7 EXPLICIT-TEACHING PATTERN (one coherent turn, in the coach's voice):\n"
        "  1. ORIENT — where we are (the unit) and why it matters for the reader.\n"
        "  2. TEACH — explicitly explain the target concept FROM THE READER'S PERSPECTIVE (what it does for the "
        "reader), e.g. 'A thesis helps readers understand the central idea that will organize the essay' — NOT a bare "
        "definition. Teach the concept; do NOT produce the student's content.\n"
        "  3. LOCATE — point to the student's closest current attempt and explain why it works or where its function "
        "is incomplete.\n"
        "  4. INVITE — one developmental invitation to apply the concept to THEIR OWN writing (the student does the work).\n"
        "  5. REFLECT — set up brief reflection on how the revision improves communication.\n"
        "COGNITIVE-SUBSTITUTION GUARD: a student must NOT be able to submit the assignment after reading your "
        "response without doing the intended cognitive work. Teach the concept; never supply copyable content.\n\n"
        "Return ONLY this JSON (compact):\n"
        '{\n'
        '  "student_facing_invitation": "the ONE coaching turn shown to the student (orient+teach+locate+invite+reflect woven together, 3-6 sentences)",\n'
        '  "teaching_content": "the explicit concept explanation given, reader-centered (short)",\n'
        '  "theory": {"communicative_purpose": {...}, "scaffolding_control": {"primary_target": "MUST equal the selected primary_target", "instructional_mode": "...", "cycle_status": "..."}, "instructional_reasoning": {...}, "revision_development": {...}},\n'
        '  "candidate_invitations": [{"invitation": "...", "rationale": "..."}, {"invitation": "...", "rationale": "..."}],\n'
        '  "selected_invitation": {"invitation": "equals student_facing_invitation", "why": "..."},\n'
        '  "intervention": {"type": "...", "focus": "writing"},\n'
        '  "transparency_state": {"where_you_are": "...", "current_unit": "...", "why_it_matters": "reader-centered", "why_this_now": "why we work on this before something else", "todays_goal": "the one target as a student goal", "whats_next": "the anticipated next step"}\n'
        '}\n'
        "Generate EXACTLY TWO internal candidate_invitations, select ONE. theory.scaffolding_control MUST hold exactly "
        "one primary_target (the selected target). Include theory.revision_development only when a prior draft exists."
    )


async def run_governance_v2(session: Session, req: InteractRequest) -> dict:
    """Three-pass Governance v2 pipeline. Returns the frozen result shape (via
    _parse_engine_output) enriched with _governance_v2 (the reasoning ledger) and
    _triage_meta (path + latency) so the existing finalize machinery is unchanged."""
    t0 = time.perf_counter()
    sid = f"gv2-{session.id}"

    # ---- Pass 1 --------------------------------------------------------
    tp1 = time.perf_counter()
    raw1 = await _chat(_P1_SYSTEM, _p1_prompt(session, req), sid + "-p1")
    l1 = _extract_json(raw1)
    t_p1 = time.perf_counter() - tp1

    # B1 Purpose-Unclear -> record and let Pass 2/3 clarify (bounded, not a hard stop).
    purpose_unclear = bool(l1.get("student_purpose_indeterminate")) or (l1.get("purpose_confidence") or 1) < 0.35

    # ---- Pass 2 --------------------------------------------------------
    tp2 = time.perf_counter()
    raw2 = await _chat(_P2_SYSTEM, _p2_prompt(session, req, l1), sid + "-p2")
    l2 = _extract_json(raw2)
    t_p2 = time.perf_counter() - tp2

    # B3 Foundational Fallback — off-task/incoherent -> escalate to the frozen engine.
    if bool(l2.get("off_task_or_incoherent")):
        full = await server._run_engine(session, req)
        full["_governance_v2"] = {"branch": "foundational_fallback", "purpose": l1, "interpretation": l2}
        full["_triage_meta"] = {
            "path": "gv2_foundational_fallback",
            "total_latency_s": round(time.perf_counter() - t0, 2),
            "t_pass1_s": round(t_p1, 2), "t_pass2_s": round(t_p2, 2),
            "num_model_calls": 4,
        }
        return full

    # Branch / mode selection (§10.9: divergence is observed; repair only when it BLOCKS).
    conceptual_insufficient = str(l2.get("conceptual_organization", "")).lower().startswith("insuff")
    align = str(l1.get("purpose_alignment", "aligned")).lower()
    repair = bool(l2.get("assignment_misunderstanding_blocks")) and align in ("partial", "divergent")
    if repair:
        mode = "assignment_repair"
    elif conceptual_insufficient:
        mode = "prewriting"
    else:
        mode = "normal"

    # ---- Pass 3 (KB = frozen SYSTEM_MESSAGE) ---------------------------
    tp3 = time.perf_counter()
    raw3 = await _chat(SYSTEM_MESSAGE, _p3_prompt(session, req, l1, l2, mode), sid + "-p3")
    parsed = _parse_engine_output(session, raw3)
    t_p3 = time.perf_counter() - tp3

    d3 = _extract_json(raw3)
    transparency = d3.get("transparency_state", {}) if isinstance(d3, dict) else {}
    teaching = d3.get("teaching_content", "") if isinstance(d3, dict) else ""

    trace = {
        "branch": "purpose_unclear" if purpose_unclear else ("prewriting" if mode == "prewriting" else ("assignment_repair" if mode == "assignment_repair" else "none")),
        "mode": mode,
        "purpose": {
            "assignment_purpose": l1.get("assignment_purpose"),
            "student_purpose": l1.get("student_purpose"),
            "purpose_alignment": l1.get("purpose_alignment"),
            "purpose_confidence": l1.get("purpose_confidence"),
            "assignment_alignment": l1.get("assignment_alignment"),
        },
        "writing_unit": {"unit": l1.get("writing_unit"), "scope": l1.get("unit_scope"),
                         "confidence": l1.get("unit_confidence")},
        "functional_model": {"functions": l1.get("functional_model"), "reader_needs": l1.get("reader_needs")},
        "functional_interpretation": {
            "functional_representation": l2.get("functional_representation"),
            "function_status": l2.get("function_status"),
            "reader_gap_summary": l2.get("reader_gap_summary"),
            "conceptual_organization": l2.get("conceptual_organization"),
        },
        "target": {"primary_target": l2.get("primary_target"),
                   "leverage_rationale": l2.get("leverage_rationale"),
                   "forward_progress_rationale": l2.get("forward_progress_rationale"),
                   "target_continuity": l2.get("target_continuity")},
        "teaching_content": teaching,
        "transparency_state": transparency,
    }

    parsed["_governance_v2"] = trace
    parsed["_meta"] = {
        "reasoner_prompt_bytes": len(raw3),
        "reasoner_output_bytes": len(raw3),
        "t_pass1_s": round(t_p1, 2), "t_pass2_s": round(t_p2, 2), "t_pass3_s": round(t_p3, 2),
    }
    parsed["_triage_meta"] = {
        "path": f"gv2_{mode}",
        "governance": "v2",
        "branch": trace["branch"],
        "writing_unit": l1.get("writing_unit"),
        "purpose_alignment": l1.get("purpose_alignment"),
        "total_latency_s": round(time.perf_counter() - t0, 2),
        "t_pass1_s": round(t_p1, 2), "t_pass2_s": round(t_p2, 2), "t_pass3_s": round(t_p3, 2),
        "num_model_calls": 3,
        "prompt_tokens": _tok(raw1) + _tok(raw2) + _tok(raw3),
        "output_tokens": _tok(raw1) + _tok(raw2) + _tok(raw3),
        "transparency_state": transparency,
    }
    return parsed
