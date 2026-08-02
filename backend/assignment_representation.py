"""
Compass 2.0 — Sprint 1: Assignment Representation.

A self-contained vertical slice. Compass helps the student build an adequate
REPRESENTATION of what an assignment requires before any knowledge gathering or
writing. It leads with assignment demands, uses the student's words diagnostically,
scaffolds ONE high-leverage demand at a time, and never writes the response.

This module owns its own APIRouter + Mongo collection (`assignment_sessions`) and
reuses the shared LLM client + helpers from server.py. It does NOT touch the
existing Milestone writing engine or the Meaning Workspace.
"""
import json
import uuid
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from emergentintegrations.llm.chat import LlmChat, UserMessage

router = APIRouter(prefix="/api/assignment", tags=["assignment-representation"])

# Injected by server.py at import time to avoid duplicate Mongo clients / circular imports.
_db = None
_llm_key = None
_now_iso = None


def init(db, llm_key, now_iso):
    global _db, _llm_key, _now_iso
    _db = db
    _llm_key = llm_key
    _now_iso = now_iso


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------
class AssignmentDemand(BaseModel):
    id: str = Field(default_factory=lambda: f"dem_{uuid.uuid4()}")
    label: str
    description: str = ""
    source: str = "explicit"                 # explicit | inferred
    supporting_wording: str = ""             # exact quote from the assignment (explicit) or "" (inferred)
    operation: str = ""                      # STABLE developmental operation, assigned once at analysis
    concepts: List[str] = Field(default_factory=list)
    category: str = "operational"            # conceptual | operational | constraint | formatting | resource
    status: str = "unconfirmed"              # understood | developing | needs_attention | unconfirmed
    priority: str = "essential"              # essential | important | helpful | optional
    learner_evidence: str = ""
    confidence: float = 0.0                  # INTERNAL ONLY — never exposed in the UI
    derivable_from_assignment: bool = True   # is the needed understanding discoverable from the assignment text itself?
    scaffold_level: int = 0
    scaffold_attempts: int = 0
    escalations_this_visit: int = 0          # resets when a demand becomes the active target (anti-fixation)
    awaiting_reconstruction: bool = False    # a concept was taught & performed; we asked for own-words reconstruction once


# Categories that actually drive developmental scaffolding.
SCAFFOLDABLE = {"conceptual", "operational"}
# Priority ordering for target selection.
PRIORITY_RANK = {"essential": 0, "important": 1, "helpful": 2, "optional": 3}


class Scaffold(BaseModel):
    demand_id: str = ""
    level: int = 1                           # 0 independent · 1 attention cue · 2 guided construction · 3 direct teaching
    instructionType: str = ""                # independent | attention_cue | guided_construction | direct_teaching
    targetOperation: str = ""
    concepts: List[str] = Field(default_factory=list)
    relevant_wording: str = ""               # the assignment wording this scaffold points at
    studentTask: str = ""                    # what the student must DO (performs the operation)
    expectedEvidence: str = ""               # what a successful performance looks like
    nextIfSuccessful: str = ""
    nextIfUnsuccessful: str = ""
    requires_reconstruction: bool = False    # level 3: learner must reconstruct the concept in their own words


class InteractionRecord(BaseModel):
    id: str = Field(default_factory=lambda: f"int_{uuid.uuid4()}")
    kind: str                                # interpretation | operation | restatement
    student_text: str = ""
    target_demand_id: str = ""
    scaffold: dict = Field(default_factory=dict)   # snapshot of the scaffold the student was responding to
    evaluation: dict = Field(default_factory=dict)
    created_at: str = ""


class KnowledgeState(BaseModel):
    """TRANSIENT conceptual-readiness state for the Knowledge Loop (Stage-1 Orientation
    extension). Tracks ONLY what supports writing — never a comprehensive concept map."""
    status: str = "unassessed"                                # unassessed | not_needed | active | ready
    limiting_concept: str = ""                                # the prerequisite/idea blocking productive writing
    reason: str = ""                                          # why activated / bypassed (dev-facing)
    current_prompt: str = ""                                  # the coach's current developmental prompt shown now
    concepts_understood: List[str] = Field(default_factory=list)
    concepts_uncertain: List[str] = Field(default_factory=list)
    misconceptions: List[str] = Field(default_factory=list)
    unresolved_questions: List[str] = Field(default_factory=list)
    relationships: List[str] = Field(default_factory=list)
    learner_explanations: List[dict] = Field(default_factory=list)   # [{concept, text}] — learner's OWN words
    turns: List[dict] = Field(default_factory=list)                  # [{role: coach|learner, text, created_at}]
    turn_count: int = 0


class AssignmentSession(BaseModel):
    id: str = Field(default_factory=lambda: f"asg_{uuid.uuid4()}")
    assignment_text: str
    title: str = ""                                                   # short title (analysis)
    subject: str = ""                                                 # e.g. Biology (analysis, "if known")
    educational_level: str = ""                                       # e.g. Grade 9 (analysis, "if known")
    demands: List[AssignmentDemand] = Field(default_factory=list)
    important_distinctions: List[str] = Field(default_factory=list)   # AI analysis: key distinctions the task hinges on
    ambiguities: List[str] = Field(default_factory=list)              # AI analysis: genuinely ambiguous points
    interactions: List[InteractionRecord] = Field(default_factory=list)
    student_interpretation: str = ""
    active_target_id: str = ""
    active_target_reason: str = ""                                    # why this demand is the current target (dev-mode)
    control_decision: Optional[dict] = None                           # last Control Engine decision (dev-mode)
    current_scaffold: Optional[dict] = None
    stage: str = "interpret"                 # interpret | mapping | restatement | adequate
    representation_adequate: bool = False
    restart_count: int = 0
    developer_notes: str = ""                                         # PRIVATE — never shown to students
    developer_summary: str = ""                                       # PRIVATE — concise 2-4 sentence lesson from the session
    sprint_recommendation: str = ""                                   # PRIVATE — one of SPRINT_RECOMMENDATIONS
    writing_session_id: str = ""                                      # BRIDGE — the Milestone-engine writing session spawned from this representation (resume, no dupe)
    knowledge_state: KnowledgeState = Field(default_factory=KnowledgeState)   # KNOWLEDGE LOOP — transient conceptual-readiness state (Stage-1 Orientation)
    created_at: str = ""
    updated_at: str = ""


SPRINT_RECOMMENDATIONS = [
    "No change needed",
    "Prompt revision",
    "New scaffold",
    "New developmental operation",
    "Developmental Control Engine revision",
    "UI revision",
    "Other",
]


class CreateReq(BaseModel):
    assignment_text: str


class TextReq(BaseModel):
    text: str


# ---------------------------------------------------------------------------
# LLM plumbing
# ---------------------------------------------------------------------------
_TONE = (
    "TONE: You are Compass, an expert tutor — warm, calm, economical, purposeful. Every sentence moves "
    "learning forward. NEVER use praise or filler ('Great job!', 'Excellent!', 'Nice work!'). No long "
    "monologues. Keep language plain and short."
)

_BOUNDARY = (
    "BOUNDARY — TASK REQUIREMENTS, NOT ANSWER CONTENT: Compass helps the learner build an adequate "
    "REPRESENTATION of what the assignment requires. Work ONLY at the level of TASK REQUIREMENTS: what the "
    "assignment asks for, what unstated work is necessary, which intellectual operations must be performed, "
    "and what must be established before later work can succeed. You MUST NOT supply the substantive content "
    "of the answer. "
    "Distinguish EXPLICIT requirements (stated in the assignment — quote the wording) from INFERRED "
    "requirements (implied by the task). Scaffold ONE high-leverage requirement at a time and require the "
    "learner to PERFORM the operation. "
    "ALLOWED example: 'To compare two ideas meaningfully, a reader first needs to understand what each idea "
    "is. What additional work does that imply for this assignment?' "
    "NOT ALLOWED example: 'A fixed mindset is the belief that abilities cannot change.' "
    "You MAY identify, explain, and REQUEST the required work; you MAY NOT perform the substantive "
    "intellectual work for the learner. Once the learner has inferred that (for example) a definition is "
    "necessary, you MAY ask the learner to provide that definition — the LEARNER performs the work, never "
    "you. Do NOT write the assignment response, a thesis, an outline, an essay, or a polished answer."
)

_REGISTER = (
    "REGISTER (fixed): Calibrate ALL language to one fixed level — a competent high-school graduate entering "
    "college or skilled work (Grade 10-12 / College). Do NOT simplify for young learners and do NOT adapt to "
    "any detected grade level. Use precise, plain academic language at this fixed register."
)


def _extract_json(text: str) -> dict:
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1] if "```" in text else text
        if text.startswith("json"):
            text = text[4:]
        text = text.strip("` \n")
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        text = text[start:end + 1]
    return json.loads(text)


async def _llm(system: str, user: str, sid: str) -> dict:
    chat = LlmChat(api_key=_llm_key, session_id=sid, system_message=system).with_model(
        "anthropic", "claude-sonnet-4-6"
    )
    raw = await chat.send_message(UserMessage(text=user))
    return _extract_json(raw)


# ---------------------------------------------------------------------------
# Backend functions
# ---------------------------------------------------------------------------
async def analyze_assignment(assignment_text: str, sid: str):
    system = (
        "You analyze an assignment to extract the DEMANDS it places on the student — the TASK REQUIREMENTS the "
        "student must recognize and DO to represent the task adequately. These are requirements about the WORK "
        "(operations, distinctions, unstated prerequisites), never the substantive answer content. "
        + _BOUNDARY + " " + _REGISTER + " " + _TONE + "\n\n"
        "For EACH demand return: label (short), description (one sentence), source ('explicit'|'inferred'), "
        "supporting_wording (exact quote from the assignment if explicit, else \"\"), operation (the single "
        "developmental operation the student must perform: e.g. Differentiate, Compare, Define, Explain, "
        "Exemplify, Relate, Analyze, Evaluate), concepts (1-3 key concepts), category (one of: 'conceptual' = a "
        "conceptual distinction/understanding the task hinges on; 'operational' = a thinking operation to perform; "
        "'constraint' = a length/quantity/scope limit like 'write two sentences' or 'use at least three sources'; "
        "'formatting' = presentation like 'APA style','double spaced'; 'resource' = required source type like "
        "'peer-reviewed sources'), priority (one of 'essential','important','helpful','optional'), "
        "derivable_from_assignment (true if a careful reading of the assignment gives enough to discover this; "
        "false if it needs outside concept knowledge). Extract 3-6 demands. IMPORTANT: constraints, formatting and "
        "resource requirements are almost never 'essential' developmental demands — mark them 'helpful' or 'optional' "
        "unless the assignment's whole point is the constraint. ALSO return important_distinctions "
        "(the key conceptual distinctions the task hinges on, e.g. 'learning process vs. learning outcome') and "
        "ambiguities (genuinely unclear points a student could reasonably read more than one way). ALSO classify: "
        "title (a concise 3-6 word title for the assignment), subject (e.g. 'Biology','History','Literature' — or "
        "\"\" if unclear), educational_level (best guess e.g. 'Grade 4','Grade 8','Grade 12','College','Graduate' — "
        "or \"\" if unclear). Return ONLY JSON: "
        '{"title":"","subject":"","educational_level":"","demands":[{"label":"","description":"","source":"",'
        '"supporting_wording":"","operation":"","concepts":[],"category":"","priority":"",'
        '"derivable_from_assignment":true}],"important_distinctions":[],"ambiguities":[]}'
    )
    data = await _llm(system, f"ASSIGNMENT:\n{assignment_text}", sid)
    out = []
    _cats = {"conceptual", "operational", "constraint", "formatting", "resource"}
    _prios = {"essential", "important", "helpful", "optional"}
    for d in data.get("demands", []):
        cat = str(d.get("category", "")).lower().strip()
        prio = str(d.get("priority", "")).lower().strip()
        out.append(AssignmentDemand(
            label=d.get("label", "").strip() or "Requirement",
            description=d.get("description", ""),
            source="inferred" if str(d.get("source", "")).lower().startswith("infer") else "explicit",
            supporting_wording=d.get("supporting_wording", "") or "",
            operation=d.get("operation", ""),
            concepts=d.get("concepts", []) or [],
            category=cat if cat in _cats else "operational",
            priority=prio if prio in _prios else "essential",
            derivable_from_assignment=bool(d.get("derivable_from_assignment", True)),
        ))
    meta = {
        "title": (data.get("title") or "").strip(),
        "subject": (data.get("subject") or "").strip(),
        "educational_level": (data.get("educational_level") or "").strip(),
    }
    return out, data.get("important_distinctions", []) or [], data.get("ambiguities", []) or [], meta


_STATUS = {"understood", "developing", "needs_attention", "unconfirmed"}


def _norm_status(s: str, default: str = "unconfirmed") -> str:
    s = str(s or "").lower().replace(" ", "_")
    return s if s in _STATUS else default


async def compare_interpretation(sess: AssignmentSession, interpretation: str) -> dict:
    demands_brief = [
        {"id": d.id, "label": d.label, "operation": d.operation, "source": d.source,
         "description": d.description} for d in sess.demands
    ]
    system = (
        "The student has explained, in their own words, what they think the assignment asks. Compare this "
        "explanation DIAGNOSTICALLY against each demand. Do NOT teach or correct here — only diagnose. " + _BOUNDARY + "\n\n"
        "For each demand id return status and learner_evidence (what in the student's words shows understanding "
        "or misunderstanding). status: 'understood' (clearly grasped), 'developing' (partial/implicit), "
        "'needs_attention' (addressed but misunderstood/confused), 'unconfirmed' (not addressed). Also confidence "
        "0.0-1.0 (internal). Return ONLY JSON: "
        '{"demands":[{"id":"","status":"","learner_evidence":"","confidence":0.0}]}'
    )
    user = (f"ASSIGNMENT:\n{sess.assignment_text}\n\nDEMANDS:\n{json.dumps(demands_brief)}\n\n"
            f"STUDENT EXPLANATION:\n{interpretation}")
    return await _llm(system, user, sess.id)


async def generate_scaffold(sess: AssignmentSession, demand: AssignmentDemand, level: int) -> Scaffold:
    ladder = (
        "SCAFFOLD LADDER — EVERY level scaffolds TASK INTERPRETATION and INFERENCE, never answer content:\n"
        "0 Independent task representation — ask the learner to identify what the assignment requires.\n"
        "1 Attention cue — direct the learner's attention to important wording, relationships, or omitted / "
        "unstated parts of the task; do NOT teach.\n"
        "2 Guided task inference — help the learner infer an unstated requirement WITHOUT supplying answer "
        "content (offer a frame or contrast about the WORK to be done, never about the concept itself).\n"
        "3 Direct teaching of the TASK PRINCIPLE — explicitly teach how the assignment or the intellectual "
        "operation works (e.g. 'To compare two ideas, you first establish what each one is, then identify "
        "meaningful similarities or differences'). This teaches HOW THE TASK WORKS, NEVER the substantive "
        "concept. THEN require the learner to reconstruct the TASK REQUIREMENT in their own words "
        "(set requires_reconstruction=true). Do NOT require reconstruction of conceptual content Compass has "
        "not taught (and Compass never teaches concept content)."
    )
    system = (
        "Produce ONE developmental scaffold for the TARGET demand at the given LEVEL. " + _BOUNDARY + " "
        + _REGISTER + " " + _TONE + "\n\n"
        + ladder + "\n\n"
        "Every scaffold MUST name the developmental operation being taught and execute a developmental MOVE — not "
        "a free-form chat. Return ONLY JSON with EXACTLY these fields: "
        '{"instructionType":"independent|attention_cue|guided_construction|direct_teaching","targetOperation":"",'
        '"concepts":[],"relevant_wording":"the assignment wording this points at","studentTask":"what the student '
        'must DO now (must require performing the operation)","expectedEvidence":"what a successful performance '
        'shows","nextIfSuccessful":"","nextIfUnsuccessful":"","requires_reconstruction":false}. '
        "studentTask is the message shown to the student: it names or points at the required WORK (more explicitly "
        "at higher levels) but MUST end by asking the student to perform an operation — EITHER identifying / "
        "inferring a task requirement, OR performing required work they have already recognized is necessary "
        "(e.g. providing a definition they themselves inferred was needed). At level 3 you TEACH the TASK "
        "PRINCIPLE, then require the learner to reconstruct the TASK REQUIREMENT in their own words. NEVER supply "
        "the substantive answer content or perform the work for them. Keep it short."
    )
    user = (f"ASSIGNMENT:\n{sess.assignment_text}\n\nTARGET DEMAND:\n"
            f"{json.dumps({'label': demand.label, 'description': demand.description, 'operation': demand.operation, 'concepts': demand.concepts, 'source': demand.source, 'supporting_wording': demand.supporting_wording, 'status': demand.status, 'learner_evidence': demand.learner_evidence, 'derivable_from_assignment': demand.derivable_from_assignment})}\n\n"
            f"SCAFFOLD LEVEL: {level}\n"
            f"PRIOR ATTEMPTS ON THIS DEMAND: {demand.scaffold_attempts}")
    data = await _llm(system, user, sess.id)
    itype = data.get("instructionType", "") or ["independent", "attention_cue", "guided_construction", "direct_teaching"][min(level, 3)]
    return Scaffold(
        demand_id=demand.id,
        level=level,
        instructionType=itype,
        targetOperation=demand.operation,          # P4: operation is STABLE — anchored to the demand
        concepts=demand.concepts,                  # P4: concepts stable too
        relevant_wording=data.get("relevant_wording", demand.supporting_wording) or demand.supporting_wording,
        studentTask=data.get("studentTask", ""),
        expectedEvidence=data.get("expectedEvidence", ""),
        nextIfSuccessful=data.get("nextIfSuccessful", ""),
        nextIfUnsuccessful=data.get("nextIfUnsuccessful", ""),
        requires_reconstruction=bool(data.get("requires_reconstruction", level >= 3)),
    )


async def evaluate_operation(sess: AssignmentSession, demand: AssignmentDemand, scaffold: dict, student_text: str) -> dict:
    other = [{"id": d.id, "label": d.label, "operation": d.operation}
             for d in sess.demands if d.id != demand.id and d.category in SCAFFOLDABLE]
    system = (
        "Determine whether the student PERFORMED the target operation — EITHER correctly identifying / inferring "
        "the TASK REQUIREMENT, OR performing required work they recognized is necessary (e.g. producing a "
        "definition they inferred was needed). Diagnose only; do NOT reveal or supply the answer, and do NOT "
        "perform the work for them. " + _BOUNDARY + "\n\n"
        "Report TWO things separately: operation_performed (did they perform the operation / show the required "
        "understanding of the TASK, regardless of wording) and reconstruction_present (did they restate the TASK "
        "REQUIREMENT or task-reading principle in their OWN WORDS). ACCEPT reconstruction whenever the learner "
        "demonstrates the underlying requirement accurately in their own language — NEVER fail them for mere "
        "wording differences. "
        "reason: 'no_attempt' (e.g. 'I don't know' / no real attempt), 'misconception' (attempted but wrong/confused), "
        "'partial', or 'success'. status is the resulting status for THIS demand "
        "(understood|developing|needs_attention). "
        "CREDIT EVERYTHING: if the response ALSO demonstrates any OTHER listed demand, report it in other_demands "
        "with that demand's id, a status, and the evidence. Never discard demonstrated understanding just because it "
        "was not the current target. Return ONLY JSON: "
        '{"operation_performed":true,"reconstruction_present":true,"status":"understood|developing|needs_attention",'
        '"learner_evidence":"","reason":"","confidence":0.0,"other_demands":[{"id":"","status":"","learner_evidence":""}]}'
    )
    user = (f"ASSIGNMENT:\n{sess.assignment_text}\n\nTARGET DEMAND:\n"
            f"{json.dumps({'label': demand.label, 'operation': demand.operation, 'description': demand.description})}\n\n"
            f"OTHER DEMANDS (credit if demonstrated):\n{json.dumps(other)}\n\n"
            f"SCAFFOLD:\n{json.dumps({'studentTask': scaffold.get('studentTask'), 'expectedEvidence': scaffold.get('expectedEvidence'), 'requires_reconstruction': scaffold.get('requires_reconstruction')})}\n\n"
            f"STUDENT RESPONSE:\n{student_text}")
    return await _llm(system, user, sess.id)


async def evaluate_restatement(sess: AssignmentSession, restatement: str) -> dict:
    demands_brief = [{"id": d.id, "label": d.label, "operation": d.operation,
                      "priority": d.priority, "source": d.source} for d in sess.demands
                     if d.category in SCAFFOLDABLE]
    system = (
        "The student has restated the WHOLE assignment in their own words. Evaluate whether their representation "
        "is ADEQUATE FOR NOW — meaning every ESSENTIAL demand is at least developing and none is missing or "
        "misunderstood. Adequate-for-now does NOT mean perfect. " + _BOUNDARY + "\n\n"
        "Return per-demand status + learner_evidence, an overall 'adequate' boolean, and 'unresolved' (ids of "
        "essential demands still needing attention). Return ONLY JSON: "
        '{"adequate":true,"demands":[{"id":"","status":"","learner_evidence":""}],"unresolved":[]}'
    )
    user = (f"ASSIGNMENT:\n{sess.assignment_text}\n\nDEMANDS:\n{json.dumps(demands_brief)}\n\n"
            f"STUDENT RESTATEMENT:\n{restatement}")
    return await _llm(system, user, sess.id)


# ---------------------------------------------------------------------------
# Control logic (deterministic — no LLM)
# ---------------------------------------------------------------------------
UNRESOLVED = {"needs_attention", "unconfirmed"}


def _scaffoldable(sess: AssignmentSession) -> List[AssignmentDemand]:
    """Only conceptual & operational demands drive scaffolding (P3)."""
    return [d for d in sess.demands if d.category in SCAFFOLDABLE]


def _focus_priorities(sess: AssignmentSession):
    """Priorities the engine will actively pursue: essential first, then important (P6).
    Helpful/optional demands are monitored but never force the session to run long."""
    scaff = _scaffoldable(sess)
    essential = [d for d in scaff if d.priority == "essential" and d.status in UNRESOLVED]
    important = [d for d in scaff if d.priority == "important" and d.status in UNRESOLVED]
    return essential, important


def _unresolved_focus(sess: AssignmentSession) -> List[AssignmentDemand]:
    essential, important = _focus_priorities(sess)
    return essential or important  # only drop to 'important' once all essential are resolved


def _pick_target(sess: AssignmentSession, exclude_id: str = "") -> Optional[AssignmentDemand]:
    """Highest-leverage unresolved focus demand. A misunderstanding (needs_attention)
    outranks an unaddressed one (unconfirmed); higher priority first; then original order."""
    pool = [d for d in _unresolved_focus(sess) if d.id != exclude_id]
    if not pool:
        pool = [d for d in _unresolved_focus(sess)]  # allow staying if it's the only one
    if not pool:
        return None
    pool.sort(key=lambda d: (PRIORITY_RANK.get(d.priority, 9),
                             0 if d.status == "needs_attention" else 1,
                             sess.demands.index(d)))
    return pool[0]


def _start_level(demand: AssignmentDemand) -> int:
    """First scaffold level for a freshly-selected target. Gentle by default (P5):
    derivable demands begin with an attention cue; only non-derivable or already-
    misunderstood demands begin at guided construction."""
    if not demand.derivable_from_assignment:
        return 2
    return 2 if demand.status == "needs_attention" else 1


def _target_reason(d: AssignmentDemand) -> str:
    if d.status == "needs_attention":
        base = "Student addressed this but misunderstood it."
    elif d.status == "unconfirmed":
        base = "Student did not address this in their interpretation."
    elif d.status == "developing":
        base = "Student showed partial understanding; sharpening it."
    else:
        base = "Selected as the current developmental target."
    if d.learner_evidence:
        base += f" ({d.learner_evidence})"
    return base


def _alternatives_reason(sess: AssignmentSession, chosen_id: str) -> str:
    """Dev-mode: why the other focus demands were not chosen this turn."""
    others = [d for d in _unresolved_focus(sess) if d.id != chosen_id]
    if not others:
        return "No other unresolved focus demands remain."
    bits = []
    for d in others[:4]:
        bits.append(f"{d.label} [{d.priority}/{d.status}]")
    return "Deferred (lower leverage now): " + "; ".join(bits)


def _set_target(sess: AssignmentSession, demand: AssignmentDemand, level: int, action: str):
    demand.scaffold_level = level
    if sess.active_target_id != demand.id:
        demand.escalations_this_visit = 0          # fresh visit → reset anti-fixation counter
    sess.active_target_id = demand.id
    sess.active_target_reason = _target_reason(demand)
    sess.control_decision = {
        "action": action,
        "reason": sess.active_target_reason,
        "alternatives_reason": _alternatives_reason(sess, demand.id),
        "next_if_successful": "Move to the next unresolved demand (or the integrated restatement).",
        "next_if_unsuccessful": ("Give one stronger scaffold, then switch to another demand rather than drilling."
                                 if demand.escalations_this_visit < 1 else
                                 "Switch to a different demand and revisit this one later."),
        "demand_category": demand.category,
        "demand_priority": demand.priority,
    }


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------
def _demand_by_id(sess: AssignmentSession, did: str) -> Optional[AssignmentDemand]:
    return next((d for d in sess.demands if d.id == did), None)


async def _load(session_id: str) -> AssignmentSession:
    doc = await _db.assignment_sessions.find_one({"id": session_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Assignment session not found")
    return AssignmentSession(**doc)


async def _save(sess: AssignmentSession) -> AssignmentSession:
    sess.updated_at = _now_iso()
    await _db.assignment_sessions.update_one(
        {"id": sess.id}, {"$set": sess.model_dump()}, upsert=True
    )
    return sess


async def _open_target_or_restatement(sess: AssignmentSession, exclude_id: str = "", action: str = "next_demand"):
    """Pick the next focus target and generate its scaffold, or move to restatement
    when no focus demand remains unresolved."""
    target = _pick_target(sess, exclude_id=exclude_id)
    if target is None:
        sess.active_target_id = ""
        sess.current_scaffold = None
        sess.stage = "restatement"
        sess.control_decision = {
            "action": "stop_scaffolding",
            "reason": "All essential/important demands are adequate for now.",
            "alternatives_reason": "", "next_if_successful": "Adequacy check on the integrated restatement.",
            "next_if_unsuccessful": "Return to the highest-leverage unresolved demand.",
            "demand_category": "", "demand_priority": "",
        }
        return
    _set_target(sess, target, _start_level(target), action)
    scaffold = await generate_scaffold(sess, target, target.scaffold_level)
    sess.current_scaffold = scaffold.model_dump()
    sess.stage = "mapping"


# Back-compat name used by the interpret endpoint.
async def _advance_after_diagnosis(sess: AssignmentSession):
    await _open_target_or_restatement(sess, action="switch_target")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.post("/sessions", response_model=AssignmentSession)
async def create_session(req: CreateReq):
    text = (req.assignment_text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Assignment text is required.")
    sess = AssignmentSession(assignment_text=text, created_at=_now_iso(), updated_at=_now_iso())
    sess.demands, sess.important_distinctions, sess.ambiguities, _meta = await analyze_assignment(text, sess.id)
    sess.title = _meta["title"]
    sess.subject = _meta["subject"]
    sess.educational_level = _meta["educational_level"]
    sess.stage = "interpret"
    await _save(sess)
    return sess


@router.get("/sessions/{session_id}", response_model=AssignmentSession)
async def get_session(session_id: str):
    return await _load(session_id)


@router.patch("/sessions/{session_id}", response_model=AssignmentSession)
async def edit_assignment(session_id: str, req: CreateReq):
    """Edit the assignment and restart analysis (learner is warned client-side first)."""
    sess = await _load(session_id)
    text = (req.assignment_text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Assignment text is required.")
    sess.assignment_text = text
    sess.demands, sess.important_distinctions, sess.ambiguities, _meta = await analyze_assignment(text, sess.id)
    sess.title = _meta["title"]
    sess.subject = _meta["subject"]
    sess.educational_level = _meta["educational_level"]
    sess.interactions = []
    sess.student_interpretation = ""
    sess.active_target_id = ""
    sess.active_target_reason = ""
    sess.current_scaffold = None
    sess.representation_adequate = False
    sess.restart_count += 1
    sess.stage = "interpret"
    await _save(sess)
    return sess


@router.post("/sessions/{session_id}/interpret", response_model=AssignmentSession)
async def interpret(session_id: str, req: TextReq):
    sess = await _load(session_id)
    text = (req.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Please explain the assignment first.")
    sess.student_interpretation = text
    diag = await compare_interpretation(sess, text)
    for d in diag.get("demands", []):
        dem = _demand_by_id(sess, d.get("id", ""))
        if dem:
            dem.status = _norm_status(d.get("status"), dem.status)
            dem.learner_evidence = d.get("learner_evidence", dem.learner_evidence)
            dem.confidence = float(d.get("confidence", dem.confidence) or 0.0)
    sess.interactions.append(InteractionRecord(
        kind="interpretation", student_text=text, evaluation=diag, created_at=_now_iso()))
    await _advance_after_diagnosis(sess)
    await _save(sess)
    return sess


@router.post("/sessions/{session_id}/operation", response_model=AssignmentSession)
async def operation(session_id: str, req: TextReq):
    sess = await _load(session_id)
    text = (req.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Please write your response first.")
    target = _demand_by_id(sess, sess.active_target_id)
    if not target or not sess.current_scaffold:
        raise HTTPException(status_code=409, detail="No active developmental target.")
    ev = await evaluate_operation(sess, target, sess.current_scaffold, text)
    scaffold_snapshot = dict(sess.current_scaffold or {})
    target.scaffold_attempts += 1

    # P5 — CREDIT EVERYTHING: apply evidence the response gives for OTHER demands.
    for od in ev.get("other_demands", []) or []:
        dem = _demand_by_id(sess, od.get("id", ""))
        if dem and dem.id != target.id and dem.category in SCAFFOLDABLE:
            new_status = _norm_status(od.get("status"), dem.status)
            # only upgrade (never downgrade a demand from a side-observation)
            rank = {"unconfirmed": 0, "needs_attention": 1, "developing": 2, "understood": 3}
            if rank.get(new_status, 0) > rank.get(dem.status, 0):
                dem.status = new_status
                if od.get("learner_evidence"):
                    dem.learner_evidence = od["learner_evidence"]

    op_done = bool(ev.get("operation_performed", ev.get("performed")))
    recon_present = bool(ev.get("reconstruction_present", True))
    needs_recon = bool(scaffold_snapshot.get("requires_reconstruction"))
    target.learner_evidence = ev.get("learner_evidence", target.learner_evidence)
    target.confidence = float(ev.get("confidence", target.confidence) or 0.0)

    sess.interactions.append(InteractionRecord(
        kind="operation", student_text=text, target_demand_id=target.id,
        scaffold=scaffold_snapshot, evaluation=ev, created_at=_now_iso()))

    # ---- P2: reconstruction gating (verify learning, never a trap) ----
    if op_done and needs_recon and not recon_present and not target.awaiting_reconstruction:
        # The operation is performed; ask for an own-words reconstruction ONCE.
        target.status = "developing"
        target.awaiting_reconstruction = True
        sess.active_target_reason = "Operation performed; asking for a one-time own-words reconstruction."
        recon = Scaffold(
            demand_id=target.id, level=target.scaffold_level, instructionType="reconstruction_check",
            targetOperation=target.operation, concepts=target.concepts,
            relevant_wording=scaffold_snapshot.get("relevant_wording", ""),
            studentTask="Good. Now, in one sentence, say in your own words what this means you'll need to DO in this assignment.",
            expectedEvidence="An accurate own-words restatement of the task requirement.",
            nextIfSuccessful="Move on.", nextIfUnsuccessful="Accept the demonstrated understanding and move on.",
            requires_reconstruction=True,
        )
        sess.current_scaffold = recon.model_dump()
        sess.control_decision = {
            "action": "request_reconstruction", "reason": sess.active_target_reason,
            "alternatives_reason": "", "next_if_successful": "Move to next demand.",
            "next_if_unsuccessful": "Do NOT re-fail — credit the demonstrated understanding and move on.",
            "demand_category": target.category, "demand_priority": target.priority,
        }
        sess.stage = "mapping"
        await _save(sess)
        return sess

    if op_done:
        # Success (or reconstruction now present, or we already asked once) — never re-trap.
        target.status = _norm_status(ev.get("status"), "developing")
        if target.status in UNRESOLVED:
            target.status = "developing"
        target.awaiting_reconstruction = False
        await _open_target_or_restatement(sess, exclude_id=target.id, action="next_demand")
        await _save(sess)
        return sess

    # ---- Not performed → dynamic move (P1: no fixation) ----
    target.status = _norm_status(ev.get("status"), "needs_attention")
    if target.status not in UNRESOLVED:
        target.status = "needs_attention"

    if target.escalations_this_visit < 1:
        # Give ONE stronger scaffold on this target, then we will switch next time.
        target.escalations_this_visit += 1
        target.scaffold_level = min(3, max(target.scaffold_level, scaffold_snapshot.get("level", 1)) + 1)
        sess.active_target_reason = "One stronger scaffold before switching (avoiding fixation)."
        scaffold = await generate_scaffold(sess, target, target.scaffold_level)
        sess.current_scaffold = scaffold.model_dump()
        sess.control_decision = {
            "action": "increase_support", "reason": sess.active_target_reason,
            "alternatives_reason": _alternatives_reason(sess, target.id),
            "next_if_successful": "Move to the next unresolved demand.",
            "next_if_unsuccessful": "Switch to a different demand and revisit this one later.",
            "demand_category": target.category, "demand_priority": target.priority,
        }
        sess.stage = "mapping"
    else:
        # Already escalated once this visit and still stuck → SWITCH targets to avoid drilling.
        # Leave this demand for later (revisitable). If it's the only one left, we stay.
        other = _pick_target(sess, exclude_id=target.id)
        if other is None:
            # only this demand remains: one final teach at L3, then treat as developing (adequate for now)
            if target.scaffold_level >= 3:
                target.status = "developing"
                await _open_target_or_restatement(sess, action="stop_scaffolding")
            else:
                target.scaffold_level = 3
                scaffold = await generate_scaffold(sess, target, 3)
                sess.current_scaffold = scaffold.model_dump()
                sess.active_target_reason = "Final direct teaching on the last remaining demand."
                sess.stage = "mapping"
        else:
            await _open_target_or_restatement(sess, exclude_id=target.id, action="switch_target")
    await _save(sess)
    return sess


@router.post("/sessions/{session_id}/restatement", response_model=AssignmentSession)
async def restatement(session_id: str, req: TextReq):
    sess = await _load(session_id)
    text = (req.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Please restate the assignment first.")
    ev = await evaluate_restatement(sess, text)
    for d in ev.get("demands", []):
        dem = _demand_by_id(sess, d.get("id", ""))
        if dem:
            dem.status = _norm_status(d.get("status"), dem.status)
            dem.learner_evidence = d.get("learner_evidence", dem.learner_evidence)
    sess.interactions.append(InteractionRecord(
        kind="restatement", student_text=text, evaluation=ev, created_at=_now_iso()))

    essential_left, _important = _focus_priorities(sess)
    # Adequacy-for-now is driven by the demand model itself: every ESSENTIAL demand is
    # at least 'developing'. (The LLM's separate 'adequate' flag can contradict this and
    # trap a learner whose restatement is actually complete, so we don't gate on it.)
    if not essential_left:
        sess.representation_adequate = True
        sess.active_target_id = ""
        sess.current_scaffold = None
        sess.stage = "adequate"
    else:
        # a genuine gap resurfaced in the restatement — return to the highest-leverage demand
        await _advance_after_diagnosis(sess)
    await _save(sess)
    return sess



# ---------------------------------------------------------------------------
# QUESTION-LOOP → WRITING BRIDGE (upstream task-representation service).
#
# This module is an UPSTREAM task-representation service, NOT an instructional
# engine. The functions below transform a completed/adequate assignment
# representation into a transient HANDOFF object that the canonical Milestone
# M1–M14 engine (backend/server.py) can consume. No teaching happens here; the
# first instructional invitation is produced by the Milestone engine after the
# handoff. Provenance is preserved so inference is never presented as fact.
# ---------------------------------------------------------------------------

# operation verb -> coarse communicative purpose (inference only; low confidence)
_OP_PURPOSE = {
    "compare": "compare", "differentiate": "compare/contrast", "contrast": "compare/contrast",
    "explain": "explain", "define": "explain", "exemplify": "explain/illustrate",
    "analyze": "analyze", "evaluate": "evaluate", "argue": "persuade", "relate": "explain",
}


def _infer_purpose(sess: "AssignmentSession") -> dict:
    """Coarse communicative-purpose inference from the demands' operations.
    Provenance is always 'inferred_by_compass' with explicit uncertainty."""
    ops = [(_OP_PURPOSE.get((d.operation or "").strip().lower())) for d in sess.demands]
    ops = [o for o in ops if o]
    if not ops:
        return {"value": "", "provenance": "unresolved", "uncertainty": "No clear operation signalled."}
    # most frequent
    top = max(set(ops), key=ops.count)
    return {"value": top, "provenance": "inferred_by_compass",
            "uncertainty": "Inferred from the task's operations; confirm with the learner if it matters."}


def assess_handoff_readiness(sess: "AssignmentSession") -> dict:
    """Determine whether there is ENOUGH information to begin productive work on ONE
    component. Not a demand for a perfect/exhaustive representation. Deterministic."""
    scaffoldable = [d for d in sess.demands if d.category in SCAFFOLDABLE]
    focus = [d for d in scaffoldable if d.priority in ("essential", "important")]
    enough_text = len((sess.assignment_text or "").split()) >= 4
    ready = bool(focus) and enough_text
    if ready:
        return {"ready": True, "clarifying_question": "", "reason": "A workable component was identified."}
    # Blocking: we cannot identify a component to work on now → ONE focused question.
    if sess.ambiguities:
        q = sess.ambiguities[0]
    elif not enough_text:
        q = "Can you paste the full assignment, and say what you're being asked to write and for whom?"
    else:
        q = "What exactly is this assignment asking you to produce — and for what reader?"
    return {"ready": False, "clarifying_question": q,
            "reason": "Not enough to identify a productive component yet."}


def _task_requirements(sess: "AssignmentSession") -> list:
    """The scaffoldable demand map, learner-facing, for goal selection at handoff."""
    out = []
    for d in sess.demands:
        if d.category in SCAFFOLDABLE:
            out.append({
                "demand_id": d.id, "label": d.label, "operation": d.operation,
                "concepts": d.concepts, "category": d.category, "priority": d.priority,
                "status": d.status, "source": d.source,
                "provenance": "explicit_teacher" if d.source == "explicit" else "inferred_by_compass",
            })
    return out


def build_handoff(sess: "AssignmentSession", learner_goal: str = "",
                  teacher_goal: str = "", existing_draft: str = "",
                  task_representation_override: str = "") -> dict:
    """Transform the assignment representation into a transient handoff object.
    Only fields the Milestone engine already expects, each carrying provenance.
    Provenance vocabulary: explicit_teacher | explicit_student | inferred_by_compass | unresolved."""
    task_rep = (task_representation_override or sess.student_interpretation or "").strip()
    constraints = [
        {"value": (d.description or d.label), "wording": d.supporting_wording,
         "provenance": "explicit_teacher" if d.source == "explicit" else "inferred_by_compass"}
        for d in sess.demands if d.category in ("constraint", "formatting", "resource")
    ]
    ks = sess.knowledge_state
    # Learner-owned understanding built in the Knowledge Loop — context only, never answer content.
    knowledge_clarified = None
    if ks and ks.status in ("active", "ready") and (ks.learner_explanations or ks.concepts_understood):
        knowledge_clarified = {
            "concepts_understood": list(ks.concepts_understood or []),
            "learner_explanations": [e.get("text", "") for e in (ks.learner_explanations or []) if e.get("text")],
            "provenance": "explicit_student",
        }
    ks_unresolved = list((ks.unresolved_questions if ks else []) or [])
    all_unresolved = list(sess.ambiguities or []) + [q for q in ks_unresolved if q not in (sess.ambiguities or [])]
    return {
        "assignment_prompt": {"value": sess.assignment_text, "provenance": "explicit_teacher"},
        "current_task_representation": {
            "value": task_rep,
            "provenance": "explicit_student" if task_rep else "unresolved"},
        "inferred_communicative_purpose": _infer_purpose(sess),
        "intended_reader": {"value": "", "provenance": "unresolved"},
        "required_form": {
            "value": sess.subject or "",
            "provenance": "inferred_by_compass" if sess.subject else "unresolved"},
        "important_constraints": constraints,
        "unresolved_questions": [{"value": a, "provenance": "unresolved"} for a in all_unresolved],
        "knowledge_clarified": knowledge_clarified,
        "learner_selected_goal": ({"value": learner_goal.strip(), "provenance": "explicit_student"}
                                  if learner_goal and learner_goal.strip() else None),
        "teacher_selected_goal": ({"value": teacher_goal.strip(), "provenance": "explicit_teacher"}
                                  if teacher_goal and teacher_goal.strip() else None),
        "existing_draft": ({"value": existing_draft.strip(), "provenance": "explicit_student"}
                           if existing_draft and existing_draft.strip() else None),
        "task_requirements": _task_requirements(sess),
        "important_distinctions": list(sess.important_distinctions or []),
        "educational_level": sess.educational_level or "",
        "title": sess.title or "",
        # suggested_initial_component is filled in by the Milestone side (KB mapping).
        "provenance_legend": {
            "explicit_teacher": "stated in the assignment / by the teacher",
            "explicit_student": "stated by the student",
            "inferred_by_compass": "Compass's inference — not confirmed fact",
            "unresolved": "not yet known",
        },
    }


@router.get("/sessions/{session_id}/handoff")
async def handoff_preview(session_id: str):
    """Readiness + editable-summary preview for the Question-Loop → writing bridge.
    Pure: no engine call, no side effects. The learner reviews/edits this before beginning."""
    sess = await _load(session_id)
    readiness = assess_handoff_readiness(sess)
    return {
        "assignment_session_id": sess.id,
        "ready": readiness["ready"],
        "clarifying_question": readiness["clarifying_question"],
        "reason": readiness["reason"],
        "writing_session_id": sess.writing_session_id or "",
        "handoff": build_handoff(sess),
    }


# ---------------------------------------------------------------------------
# KNOWLEDGE LOOP — Stage-1 (Orientation) EXTENSION ONLY.
#
# NOT an instructional engine, NOT a parallel workflow, NOT a second persistence
# model, NOT a new knowledge base. It lives entirely inside Orientation: when
# conceptual understanding is the limiting factor for productive writing, it
# helps the learner build JUST ENOUGH understanding, then control returns to the
# existing bridge → Milestone engine, exactly as before. The learner always does
# the intellectual work (same boundary philosophy as the Question Loop).
# ---------------------------------------------------------------------------
_KNOWLEDGE_MAX_TURNS = 4  # avoid long conceptual detours (readiness, not mastery)

_KNOWLEDGE_BOUNDARY = (
    "KNOWLEDGE-LOOP BOUNDARY: Your ONLY goal is to help the learner develop ENOUGH conceptual understanding to "
    "write productively — readiness, NOT mastery, NOT tutoring for its own sake. The LEARNER does the intellectual "
    "work. You MAY ask questions, compare ideas, help organize concepts, reveal misconceptions, request explanations, "
    "encourage examples, and prompt reflection. You MUST NOT: complete the learner's explanation, provide the "
    "assignment answer, DEFINE any concept the assignment asks the learner to define (see DO_NOT_DEFINE), write any "
    "part of the paper, or lecture by default. If a genuine PREREQUISITE obstacle blocks understanding, give only the "
    "MINIMUM support needed to clear it — never more. Keep every exchange short."
)
_KNOWLEDGE_RECONNECT = (
    "Keep an explicit tie to the writing task: how will this help the reader, how does it relate to the purpose, "
    "and which part of the paper will use this idea? Avoid long conceptual conversations detached from writing."
)


def _do_not_define(sess: "AssignmentSession") -> list:
    """Concepts the assignment asks the LEARNER to define/explain — Compass must never define these."""
    concepts = []
    for d in sess.demands:
        if d.category == "conceptual":
            concepts.extend(d.concepts or [])
            if d.label:
                concepts.append(d.label)
    # de-dupe, keep order
    seen, out = set(), []
    for c in concepts:
        k = c.strip().lower()
        if k and k not in seen:
            seen.add(k)
            out.append(c)
    return out


def _knowledge_signals(sess: "AssignmentSession") -> str:
    recent = []
    for i in sess.interactions[-6:]:
        if i.student_text:
            recent.append(f"[{i.kind}] {i.student_text}")
    return "\n".join(recent) or "(no learner responses yet)"


async def assess_knowledge_need(sess: "AssignmentSession") -> dict:
    """GATE: is conceptual understanding the LIMITING factor for productive writing?
    Activate ONLY for a genuine understanding gap — never for a mere factual question,
    and never if the learner already shows adequate working understanding."""
    system = (
        "You decide ONE thing: is the learner's CONCEPTUAL UNDERSTANDING the limiting factor that would prevent "
        "them from beginning productive writing on this task RIGHT NOW? " + _KNOWLEDGE_BOUNDARY + " " + _KNOWLEDGE_RECONNECT + "\n\n"
        "STRONG DEFAULT = BYPASS (needed=false). The writing engine itself develops and refines understanding as the "
        "learner writes, so activate ONLY when the learner genuinely CANNOT start productive writing due to a "
        "conceptual gap. If the learner can already list the relevant ideas, take a rough position, or produce even a "
        "weak first attempt, they are READY — bypass. This is readiness, NOT mastery: imperfect, incomplete, or "
        "roughly-articulated understanding is ENOUGH to begin. Do NOT activate to polish a mechanism, sharpen wording, "
        "deepen an already-present idea, or because an explanation is shallow — those are the writing engine's job. "
        "Activate (needed=true) ONLY when at least one is CLEARLY true and blocking: the learner explicitly says they "
        "don't understand and shows no working grasp; the learner cannot name or explain the central idea at all; the "
        "learner holds a clear MISCONCEPTION that would derail the writing; or a required PREREQUISITE idea is simply "
        "absent. DO NOT activate for a mere factual question. "
        "If needed, write ONE short opening developmental prompt that starts building understanding by asking the "
        "LEARNER to explain/compare/organize in their own words — never define anything for them — and tie it to the "
        "writing task. Return ONLY JSON: "
        '{"needed":false,"limiting_concept":"","reason":"","opening_prompt":""}'
    )
    user = (
        f"ASSIGNMENT:\n{sess.assignment_text}\n\n"
        f"DO_NOT_DEFINE (assigned to the learner): {json.dumps(_do_not_define(sess))}\n\n"
        f"TASK DEMANDS: {json.dumps([{'label': d.label, 'operation': d.operation, 'concepts': d.concepts, 'category': d.category, 'status': d.status, 'learner_evidence': d.learner_evidence} for d in sess.demands])}\n\n"
        f"IMPORTANT DISTINCTIONS: {json.dumps(sess.important_distinctions)}\n"
        f"AMBIGUITIES: {json.dumps(sess.ambiguities)}\n\n"
        f"LEARNER'S OWN WORDS SO FAR:\n{_knowledge_signals(sess)}"
    )
    return await _llm(system, user, sess.id)


async def evaluate_knowledge_turn(sess: "AssignmentSession", text: str) -> dict:
    """Interpret the learner's explanation, update understanding, and decide whether they now
    have ENOUGH understanding to perform the writing task (readiness, not mastery)."""
    ks = sess.knowledge_state
    system = (
        "You are running the Knowledge Loop: help the learner build JUST ENOUGH understanding to write, then hand "
        "back to writing. " + _KNOWLEDGE_BOUNDARY + " " + _KNOWLEDGE_RECONNECT + "\n\n"
        "Interpret what the learner actually demonstrated (diagnosis, not grading, no scores). Decide ready=true when "
        "the learner has ENOUGH working understanding to perform the current writing task — NOT perfect mastery. If "
        "not ready, write ONE short next developmental prompt that moves them forward by doing the work themselves "
        "(explain/compare/organize/give an example), never by you defining or completing it. When ready, write a "
        "brief consolidation that names what they now grasp and points to using it in the draft. "
        "capture the learner's OWN best explanation (their words) in captured_explanation. Return ONLY JSON: "
        '{"ready":false,"reason":"","coach_prompt":"","concepts_understood":[],"concepts_uncertain":[],'
        '"misconceptions":[],"unresolved_questions":[],"relationships":[],"captured_explanation":""}'
    )
    user = (
        f"ASSIGNMENT:\n{sess.assignment_text}\n\n"
        f"DO_NOT_DEFINE (assigned to the learner): {json.dumps(_do_not_define(sess))}\n"
        f"LIMITING CONCEPT: {ks.limiting_concept}\n\n"
        f"DIALOGUE SO FAR: {json.dumps(ks.turns[-6:])}\n\n"
        f"LEARNER'S NEW RESPONSE:\n{text}"
    )
    return await _llm(system, user, sess.id)


@router.get("/sessions/{session_id}/knowledge")
async def get_knowledge(session_id: str):
    """Current transient conceptual-readiness state (resume-safe)."""
    sess = await _load(session_id)
    return sess.knowledge_state.model_dump()


@router.post("/sessions/{session_id}/knowledge/assess")
async def knowledge_assess(session_id: str):
    """Decide whether the Knowledge Loop should activate. Idempotent: if already active/ready,
    returns current state without re-gating (supports resume)."""
    sess = await _load(session_id)
    ks = sess.knowledge_state
    if ks.status in ("active", "ready"):
        return ks.model_dump()
    try:
        data = await assess_knowledge_need(sess)
    except Exception:  # noqa: BLE001 — LLM/parse hiccup: fail OPEN to writing, never trap the learner
        data = {"needed": False, "reason": "assessment unavailable — proceeding to writing"}
    if data.get("needed"):
        ks.status = "active"
        ks.limiting_concept = data.get("limiting_concept", "")
        ks.reason = data.get("reason", "")
        ks.current_prompt = data.get("opening_prompt", "") or "Tell me, in your own words, what this idea means to you so far."
        ks.turns.append({"role": "coach", "text": ks.current_prompt, "created_at": _now_iso()})
    else:
        ks.status = "not_needed"
        ks.reason = data.get("reason", "")
    await _save(sess)
    return ks.model_dump()


@router.post("/sessions/{session_id}/knowledge/respond")
async def knowledge_respond(session_id: str, body: TextReq):
    """Learner performs conceptual work; Compass interprets and decides continue vs. ready.
    A hard turn cap forces readiness to prevent long conceptual detours."""
    sess = await _load(session_id)
    ks = sess.knowledge_state
    if ks.status != "active":
        raise HTTPException(status_code=400, detail="Knowledge Loop is not active for this session")
    text = (body.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty response")
    ks.turns.append({"role": "learner", "text": text, "created_at": _now_iso()})
    ks.turn_count += 1

    try:
        data = await evaluate_knowledge_turn(sess, text)
    except Exception:  # noqa: BLE001 — LLM/parse hiccup: hold the boundary, don't break the flow
        data = {"ready": False,
                "coach_prompt": "Stay with your own thinking for a moment — in your own words, what do you understand about this so far, and where does it get fuzzy?"}
    # merge understanding (de-dupe, keep only what supports writing)
    def _merge(field, new):
        cur = getattr(ks, field)
        for x in (new or []):
            if x and x not in cur:
                cur.append(x)
    _merge("concepts_understood", data.get("concepts_understood"))
    _merge("concepts_uncertain", data.get("concepts_uncertain"))
    _merge("misconceptions", data.get("misconceptions"))
    _merge("unresolved_questions", data.get("unresolved_questions"))
    _merge("relationships", data.get("relationships"))
    cap = (data.get("captured_explanation") or "").strip()
    if cap:
        ks.learner_explanations.append({"concept": ks.limiting_concept, "text": cap})

    forced = ks.turn_count >= _KNOWLEDGE_MAX_TURNS
    if data.get("ready") or forced:
        ks.status = "ready"
        ks.current_prompt = data.get("coach_prompt", "") or "You've got enough to start — let's put this to work in your draft."
        ks.reason = ("turn cap reached — enough to begin" if forced and not data.get("ready") else data.get("reason", ""))
        ks.turns.append({"role": "coach", "text": ks.current_prompt, "created_at": _now_iso()})
    else:
        ks.current_prompt = data.get("coach_prompt", "") or "Say a little more — what else do you notice?"
        ks.turns.append({"role": "coach", "text": ks.current_prompt, "created_at": _now_iso()})
    await _save(sess)
    return ks.model_dump()


@router.post("/sessions/{session_id}/knowledge/skip")
async def knowledge_skip(session_id: str):
    """Learner chooses to start writing now (learner-initiated exit)."""
    sess = await _load(session_id)
    ks = sess.knowledge_state
    ks.status = "ready"
    ks.reason = "learner chose to begin writing"
    await _save(sess)
    return ks.model_dump()


# ---------------------------------------------------------------------------
# Developer instruments — Development Session record + private notes.
# (Not analytics. Each session is a complete, human-analyzable research case.)
# ---------------------------------------------------------------------------
class NotesReq(BaseModel):
    developer_notes: Optional[str] = None
    developer_summary: Optional[str] = None
    sprint_recommendation: Optional[str] = None


def _duration_seconds(sess: AssignmentSession):
    try:
        from datetime import datetime
        a = datetime.fromisoformat(sess.created_at.replace("Z", "+00:00"))
        b = datetime.fromisoformat(sess.updated_at.replace("Z", "+00:00"))
        return max(0, int((b - a).total_seconds()))
    except Exception:
        return None


def build_record(sess: AssignmentSession) -> dict:
    explicit = [d for d in sess.demands if d.source == "explicit"]
    inferred = [d for d in sess.demands if d.source == "inferred"]

    def dbrief(d: AssignmentDemand):
        return {"label": d.label, "description": d.description, "operation": d.operation,
                "concepts": d.concepts, "category": d.category, "priority": d.priority,
                "supporting_wording": d.supporting_wording, "status": d.status,
                "learner_evidence": d.learner_evidence}

    ops = [i for i in sess.interactions if i.kind == "operation"]
    dev_history = []
    for i in ops:
        dem = _demand_by_id(sess, i.target_demand_id)
        sc = i.scaffold or {}
        ev = i.evaluation or {}
        dev_history.append({
            "target_demand": dem.label if dem else i.target_demand_id,
            "target_operation": sc.get("targetOperation") or (dem.operation if dem else ""),
            "scaffold_level": sc.get("level"),
            "instruction_type": sc.get("instructionType"),
            "student_response": i.student_text,
            "performed": bool(ev.get("performed")),
            "reason": ev.get("reason", ""),
            "final_demand_status": dem.status if dem else "",
        })

    responses = [{"kind": i.kind, "text": i.student_text} for i in sess.interactions if i.student_text]
    final_restatement = next(
        (i.student_text for i in reversed(sess.interactions) if i.kind == "restatement"), "")

    idk = any(
        (i.evaluation or {}).get("reason") == "no_attempt"
        or "don't know" in (i.student_text or "").lower()
        or "dont know" in (i.student_text or "").lower()
        or "do not know" in (i.student_text or "").lower()
        for i in ops
    )
    num_level3 = sum(1 for i in ops if (i.scaffold or {}).get("level") == 3)

    return {
        "session_id": sess.id,
        "assignment": {"original": sess.assignment_text},
        "ai_analysis": {
            "explicit_demands": [dbrief(d) for d in explicit],
            "inferred_demands": [dbrief(d) for d in inferred],
            "important_distinctions": sess.important_distinctions,
            "ambiguities": sess.ambiguities,
        },
        "student": {
            "initial_interpretation": sess.student_interpretation,
            "responses": responses,
            "final_integrated_restatement": final_restatement,
        },
        "developmental_history": dev_history,
        "final_question_map": [
            {"label": d.label, "source": d.source, "operation": d.operation,
             "category": d.category, "priority": d.priority, "status": d.status,
             "scaffold_level": d.scaffold_level, "scaffold_attempts": d.scaffold_attempts}
            for d in sess.demands
        ],
        "metadata": {
            "created_at": sess.created_at,
            "updated_at": sess.updated_at,
            "session_length_seconds": _duration_seconds(sess),
            "num_scaffold_attempts": len(ops),
            "num_scaffold_targets": len({i.target_demand_id for i in ops}),
            "num_level3_interventions": num_level3,
            "i_dont_know_occurred": idk,
            "restart_occurred": sess.restart_count > 0,
            "restart_count": sess.restart_count,
            "representation_adequate": sess.representation_adequate,
            "stage": sess.stage,
        },
        "developer_notes": sess.developer_notes,
        "developer_summary": sess.developer_summary,
        "sprint_recommendation": sess.sprint_recommendation,
    }


def _record_markdown(r: dict) -> str:
    L = ["# Development Session", "", f"_Session {r['session_id']}_", "",
         "## Assignment", r["assignment"]["original"], "", "## AI Analysis", "", "### Explicit demands"]
    for d in r["ai_analysis"]["explicit_demands"]:
        L.append(f"- **{d['label']}** ({d['operation']}) — {d['description']}  \n  wording: “{d['supporting_wording']}”  \n  final status: {d['status']}")
    L += ["", "### Inferred demands"]
    for d in r["ai_analysis"]["inferred_demands"]:
        L.append(f"- **{d['label']}** ({d['operation']}) — {d['description']}  \n  final status: {d['status']}")
    L += ["", "### Important distinctions"] + [f"- {x}" for x in r["ai_analysis"]["important_distinctions"]]
    L += ["", "### Ambiguities"] + [f"- {x}" for x in r["ai_analysis"]["ambiguities"]]
    L += ["", "## Student", "", "**Initial interpretation:** " + (r["student"]["initial_interpretation"] or "—"), "", "**Responses:**"]
    for resp in r["student"]["responses"]:
        L.append(f"- _{resp['kind']}_: {resp['text']}")
    L += ["", "**Final integrated restatement:** " + (r["student"]["final_integrated_restatement"] or "—"),
          "", "## Developmental history"]
    for h in r["developmental_history"]:
        L.append(f"- **{h['target_demand']}** · op={h['target_operation']} · level={h['scaffold_level']} "
                 f"· {'performed' if h['performed'] else 'not performed'} ({h['reason']}) → status {h['final_demand_status']}")
    L += ["", "## Final Question Map"]
    for d in r["final_question_map"]:
        L.append(f"- [{d['source']}/{d['priority']}·{d['category']}] **{d['label']}** ({d['operation']}) — {d['status']} "
                 f"(level {d['scaffold_level']}, {d['scaffold_attempts']} attempts)")
    m = r["metadata"]
    L += ["", "## Metadata",
          f"- Created: {m['created_at']}",
          f"- Length: {m['session_length_seconds']}s",
          f"- Scaffold attempts: {m['num_scaffold_attempts']} across {m['num_scaffold_targets']} demands",
          f"- Level-3 interventions: {m['num_level3_interventions']}",
          f"- 'I don't know' occurred: {m['i_dont_know_occurred']}",
          f"- Restart occurred: {m['restart_occurred']} (x{m['restart_count']})",
          f"- Representation adequate: {m['representation_adequate']}",
          "", "## Developer Summary", r.get("developer_summary") or "_(none)_",
          "", "## Sprint Recommendation", r.get("sprint_recommendation") or "_(none)_",
          "", "## Developer Notes", r["developer_notes"] or "_(none)_"]
    return "\n".join(L)


@router.get("/sessions/{session_id}/record")
async def development_record(session_id: str, format: str = "json"):
    from fastapi import Response
    sess = await _load(session_id)
    r = build_record(sess)
    if format == "markdown":
        return Response(_record_markdown(r), media_type="text/markdown",
                        headers={"Content-Disposition": f'attachment; filename="dev_session_{session_id[:12]}.md"'})
    return Response(json.dumps(r, indent=2, default=str), media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="dev_session_{session_id[:12]}.json"'})


@router.patch("/sessions/{session_id}/developer-notes", response_model=AssignmentSession)
async def set_developer_notes(session_id: str, req: NotesReq):
    sess = await _load(session_id)
    if req.developer_notes is not None:
        sess.developer_notes = req.developer_notes
    if req.developer_summary is not None:
        sess.developer_summary = req.developer_summary
    if req.sprint_recommendation is not None:
        sess.sprint_recommendation = req.sprint_recommendation
    await _save(sess)
    return sess


@router.get("/recommendation-options")
async def recommendation_options():
    return {"options": SPRINT_RECOMMENDATIONS}


@router.get("/library")
async def session_library():
    """Developer-only index of saved Development Sessions. NOT analytics —
    just a list of cases with enough metadata to choose one to open."""
    docs = await _db.assignment_sessions.find({}, {"_id": 0}).to_list(500)
    items = []
    for doc in docs:
        sess = AssignmentSession(**doc)
        ops = [i for i in sess.interactions if i.kind == "operation"]
        items.append({
            "id": sess.id,
            "created_at": sess.created_at,
            "updated_at": sess.updated_at,
            "title": sess.title or (sess.assignment_text[:60] + ("…" if len(sess.assignment_text) > 60 else "")),
            "subject": sess.subject,
            "educational_level": sess.educational_level,
            "assignment_first_line": sess.assignment_text.split("\n")[0][:120],
            "session_length_seconds": _duration_seconds(sess),
            "num_scaffold_attempts": len(ops),
            "num_level3_interventions": sum(1 for i in ops if (i.scaffold or {}).get("level") == 3),
            "has_developer_notes": bool(sess.developer_notes.strip()),
            "has_developer_summary": bool(sess.developer_summary.strip()),
            "sprint_recommendation": sess.sprint_recommendation,
            "stage": sess.stage,
            "representation_adequate": sess.representation_adequate,
        })
    items.sort(key=lambda x: x["updated_at"] or "", reverse=True)
    return {"sessions": items}
