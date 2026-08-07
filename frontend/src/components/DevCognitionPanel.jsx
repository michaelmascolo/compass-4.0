import { useState, useEffect, useCallback, useRef } from "react";
import { getFunctionalTrace, getSentenceCraft } from "@/lib/api";

// DEV-ONLY (Sprint 4.0-2). Shows the COMPLETE hidden Developmental Cognition Object — estimate +
// confidence + evidence per field, plus the raw object verbatim — with TURN HISTORY (step back
// through earlier turns' diagnoses) and a COPY JSON button, so the developer can calibrate
// Compass's developmental reasoning after every interaction. Gated behind ?dco; never a student
// feature. Reads GET /api/dev/functional-v3-trace/{sessionId}.

const FIELDS = [
  ["communicative_task", "Communicative task (what the assignment requires)"],
  ["apparent_orientation_target", "Apparent orientation target (what the writing is constructing)"],
  ["orientation_target_interpretation", "Orientation target — Compass's interpretation"],
  ["orientation_target_confirmed", "Orientation target — confirmed / revised by student"],
  ["task_orientation_relation", "Task ↔ orientation relation"],
  ["content_relations_and_dependencies", "Content relations & dependencies (task meaning-relations)"],
  ["structural_relations_and_dependencies", "Structural relations & dependencies (organization required)"],
  ["current_relational_structure", "Current relational structure (organization present)"],
  ["conceptual_organization", "Conceptual organization"],
  ["communicative_organization", "Communicative organization"],
  ["coordinative_capacity", "Coordinative capacity (form + quality, Fischer)"],
  ["developmental_constraint", "Developmental constraint (what limits progress)"],
  ["developmental_possibilities", "Developmental possibilities (range constructible next)"],
  ["task_required_content_relations", "Task-required content relations (for the reader)"],
  ["task_required_structural_relations", "Task-required structural relations (coherent whole)"],
  ["whole_communication_requirements", "Whole-communication requirements (minimum organization)"],
  ["provisional_whole_communication", "Provisional whole communication (constructible by THIS learner)"],
  ["integrated_instructional_problem_space", "Integrated instructional problem space (the synthesis)"],
  ["instructional_horizon", "Instructional horizon (upper boundary of the possibilities)"],
  ["instructional_center", "Instructional center (next necessary coordination)"],
  ["local_instruction_constraints", "Local instruction constraints (local-in-whole limits)"],
  ["reachable_next_move", "Reachable next move"],
  ["current_instructional_sufficiency", "Current instructional sufficiency (enough for the whole)"],
  ["deferred_or_excluded_complexity", "Deferred / excluded complexity"],
  ["beyond_horizon", "Beyond the horizon"],
];

const confColor = (c) =>
  c === "high" ? "#4ade80" : c === "medium" ? "#fbbf24" : c === "low" ? "#f87171" : "#78716c";

const ORIENT_FIELDS = [
  ["current_direction", "Current direction (the whole we're building)"],
  ["where_we_are", "Where we are"],
  ["current_work", "Current work — and why it matters"],
  ["likely_next_step", "Likely next step"],
  ["estimated_remaining_moves", "Estimated remaining moves"],
  ["orientation_revision_reason", "Why the plan changed"],
];

export default function DevCognitionPanel({ sessionId, turnKey, onClose }) {
  const [trace, setTrace] = useState([]);
  const [idx, setIdx] = useState(0); // selected turn index within trace
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showRaw, setShowRaw] = useState(false);
  const [copied, setCopied] = useState(false);
  const [sc, setSc] = useState(null);
  const [scLoading, setScLoading] = useState(false);
  const [scError, setScError] = useState("");
  const prevLenRef = useRef(0);

  const loadSC = useCallback(async () => {
    if (!sessionId) return;
    setScLoading(true);
    setScError("");
    try {
      const data = await getSentenceCraft(sessionId);
      setSc(data);
    } catch (e) {
      setScError(e?.response?.data?.detail || e.message || "failed");
    } finally {
      setScLoading(false);
    }
  }, [sessionId]);

  const load = useCallback(async () => {
    if (!sessionId) return;
    setLoading(true);
    setError("");
    try {
      const data = await getFunctionalTrace(sessionId);
      const t = data?.trace || [];
      setTrace(t);
      // Jump to the newest turn when a new one arrives; otherwise keep the developer's position.
      setIdx((cur) => {
        if (t.length === 0) return 0;
        if (t.length > prevLenRef.current) return t.length - 1;
        return Math.min(cur, t.length - 1);
      });
      prevLenRef.current = t.length;
    } catch (e) {
      setError(e?.response?.data?.detail || e?.message || "failed to load trace");
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  // Refetch after every interaction (turnKey changes when a new AI turn completes).
  useEffect(() => {
    if (!sessionId) return;
    const t = setTimeout(load, 400); // small delay so the trace line is flushed
    return () => clearTimeout(t);
  }, [sessionId, turnKey, load]);

  const copyJson = useCallback(async (obj) => {
    const text = JSON.stringify(obj, null, 2);
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand("copy"); } catch { /* ignore */ }
      document.body.removeChild(ta);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }, []);

  if (!sessionId) return null;

  const rec = trace.length ? trace[Math.min(idx, trace.length - 1)] : null;
  const dco = rec?.developmental_cognition || null;
  const conf = dco?.confidence || {};
  const evidence = dco?.evidence || {};
  const atLast = idx >= trace.length - 1;

  return (
    <div
      data-testid="dev-cognition-panel"
      style={{
        position: "fixed", right: 16, bottom: 16, zIndex: 60, width: 420, maxHeight: "84vh",
        display: "flex", flexDirection: "column",
        fontFamily: "ui-monospace, 'IBM Plex Mono', monospace", fontSize: 11, lineHeight: 1.5,
        color: "#e7e5e4", background: "rgba(23,23,23,0.98)", border: "1px solid #57534e",
        borderRadius: 8, boxShadow: "0 10px 30px rgba(0,0,0,0.45)", overflow: "hidden",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8,
        padding: "9px 11px", background: "#292524", borderBottom: "1px solid #57534e" }}>
        <span style={{ letterSpacing: "0.12em", textTransform: "uppercase", color: "#a8a29e", fontWeight: 600 }}>
          Developmental Cognition · dev
        </span>
        <span style={{ display: "flex", gap: 6 }}>
          <button data-testid="dev-cognition-copy" onClick={() => dco && copyJson(dco)}
            title="Copy this turn's Developmental Cognition Object as JSON"
            style={{ ...btnStyle, width: "auto", padding: "0 7px", color: copied ? "#4ade80" : "#e7e5e4" }}>
            {copied ? "Copied ✓" : "Copy JSON"}
          </button>
          <button data-testid="dev-cognition-refresh" onClick={load} title="Refresh" style={btnStyle}>
            {loading ? "…" : "↻"}
          </button>
          <button data-testid="dev-cognition-raw" onClick={() => setShowRaw((v) => !v)}
            title="Toggle raw object" style={{ ...btnStyle, width: "auto", padding: "0 6px" }}>
            {showRaw ? "fields" : "raw"}
          </button>
          <button data-testid="dev-cognition-close" onClick={onClose} title="Close" style={btnStyle}>✕</button>
        </span>
      </div>

      {/* Turn history navigator */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8,
        padding: "6px 11px", background: "#1c1917", borderBottom: "1px solid #292524", color: "#a8a29e" }}>
        <button data-testid="dev-cognition-prev" onClick={() => setIdx((i) => Math.max(0, i - 1))}
          disabled={idx <= 0} title="Previous turn"
          style={{ ...btnStyle, width: "auto", padding: "0 8px", opacity: idx <= 0 ? 0.4 : 1 }}>
          ‹ prev
        </button>
        <span data-testid="dev-cognition-turn-label" style={{ fontSize: 10 }}>
          {trace.length ? `turn ${idx + 1} / ${trace.length}` : "turn — / —"}
          {rec ? ` · ${rec.turn_kind || "—"}` : ""}
          {atLast && trace.length ? " · latest" : ""}
        </span>
        <button data-testid="dev-cognition-next" onClick={() => setIdx((i) => Math.min(trace.length - 1, i + 1))}
          disabled={atLast} title="Next turn"
          style={{ ...btnStyle, width: "auto", padding: "0 8px", opacity: atLast ? 0.4 : 1 }}>
          next ›
        </button>
      </div>

      <div style={{ padding: "10px 12px", overflowY: "auto" }}>
        <div style={{ color: "#78716c", marginBottom: 8 }}>
          module: {rec?.reasoning_module_selected || "—"}
        </div>

        {error && <div style={{ color: "#f87171" }}>error: {error}</div>}
        {!error && !dco && (
          <div style={{ color: "#a8a29e" }}>
            {trace.length ? "No developmental_cognition recorded for this turn." : "No turns yet. Complete a turn, then press ↻."}
          </div>
        )}

        {dco && showRaw && (
          <pre data-testid="dco-raw" style={{ whiteSpace: "pre-wrap", wordBreak: "break-word",
            background: "#0c0a09", border: "1px solid #44403c", borderRadius: 6, padding: 10, margin: 0, color: "#d6d3d1" }}>
            {JSON.stringify(dco, null, 2)}
          </pre>
        )}

        {dco && !showRaw && dco.structural_load_analysis && typeof dco.structural_load_analysis === "object" && (
          <div data-testid="dco-structural_load_analysis"
            style={{ marginBottom: 12, padding: "9px 11px", background: "#0c0a09",
              border: "1px solid #3f3f46", borderLeft: "3px solid #fb7185", borderRadius: 6 }}>
            {(() => {
              const s = dco.structural_load_analysis;
              const scol = s.structural_load_status === "proportionate" ? "#4ade80"
                : s.structural_load_status === "overloaded" ? "#f87171"
                : s.structural_load_status === "crowded" ? "#fbbf24"
                : s.structural_load_status === "underloaded" ? "#60a5fa" : "#a8a29e";
              const row = (label, val) => {
                if (val === null || val === undefined || val === "") return null;
                const text = Array.isArray(val)
                  ? val.map((v) => (typeof v === "object" ? JSON.stringify(v) : v)).join(" · ")
                  : (typeof val === "object" ? JSON.stringify(val) : String(val));
                if (!text) return null;
                return (
                  <div style={{ marginBottom: 4 }}>
                    <div style={{ color: "#a8a29e", textTransform: "uppercase", fontSize: 8.5, letterSpacing: "0.08em" }}>{label}</div>
                    <div style={{ color: "#f5f5f4", fontSize: 12 }}>{text}</div>
                  </div>
                );
              };
              return (
                <>
                  <div style={{ display: "flex", justifyContent: "space-between", gap: 8, marginBottom: 5 }}>
                    <span style={{ color: "#fb7185", fontWeight: 700, textTransform: "uppercase", fontSize: 9, letterSpacing: "0.1em" }}>Structural load (4.9)</span>
                    <span style={{ color: scol, fontWeight: 700, textTransform: "uppercase", fontSize: 9 }}>{s.structural_load_status || "—"}</span>
                  </div>
                  {row("Central movement", s.central_communicative_movement)}
                  {row("Required structural work", s.required_structural_work)}
                  {row("Current structural work", s.current_structural_work)}
                  {row("Redundant structural work", s.redundant_structural_work)}
                  {row("Competing structural work", s.competing_structural_work)}
                  {row("Secondary trajectories", s.secondary_trajectories)}
                  {row("Pruning needed", s.structural_pruning_needed)}
                  {row("Recommended operation", s.recommended_structural_operation)}
                  {row("Reason", s.reason)}
                </>
              );
            })()}
          </div>
        )}

        {dco && !showRaw && dco.episode_closure && typeof dco.episode_closure === "object" && (
          <div data-testid="dco-episode_closure"
            style={{ marginBottom: 12, padding: "9px 11px", background: "#0c0a09",
              border: "1px solid #3f3f46", borderLeft: "3px solid #a78bfa", borderRadius: 6 }}>
            {(() => {
              const e = dco.episode_closure;
              const dcol = e.episode_closure_decision === "continue_current_episode" ? "#4ade80"
                : (e.episode_closure_decision || "").startsWith("close") ? "#f87171"
                : e.episode_closure_decision === "reopen_only_if_material_gap" ? "#fbbf24" : "#a8a29e";
              const row = (label, val) => (val === "" || val === null || val === undefined) ? null : (
                <div style={{ marginBottom: 4 }}>
                  <div style={{ color: "#a8a29e", textTransform: "uppercase", fontSize: 8.5, letterSpacing: "0.08em" }}>{label}</div>
                  <div style={{ color: "#f5f5f4", fontSize: 12 }}>{String(val)}</div>
                </div>
              );
              return (
                <>
                  <div style={{ display: "flex", justifyContent: "space-between", gap: 8, marginBottom: 5 }}>
                    <span style={{ color: "#a78bfa", fontWeight: 700, textTransform: "uppercase", fontSize: 9, letterSpacing: "0.1em" }}>Episode closure (4.8)</span>
                    <span style={{ color: dcol, fontWeight: 700, textTransform: "uppercase", fontSize: 9 }}>{e.episode_closure_decision || "—"}</span>
                  </div>
                  {row("Instructional operation", e.instructional_operation)}
                  {row("Coaching permitted", e.coaching_permitted)}
                  {row("Remaining communicative budget", e.remaining_communicative_budget)}
                  {row("Learner transition request", e.learner_transition_request)}
                  {row("Reader can reconstruct", e.reader_can_reconstruct)}
                  {row("Candidate move classification", e.candidate_move_classification)}
                  {row("Burden of proof", e.burden_of_proof)}
                  {row("Material gap", e.material_gap)}
                  {row("Reason", e.reason)}
                </>
              );
            })()}
          </div>
        )}

        {dco && !showRaw && dco.communicative_capacity && typeof dco.communicative_capacity === "object" && (
          <div data-testid="dco-communicative_capacity"
            style={{ marginBottom: 12, padding: "9px 11px", background: "#0c0a09",
              border: "1px solid #3f3f46", borderLeft: "3px solid #f59e0b", borderRadius: 6 }}>
            {(() => {
              const cc = dco.communicative_capacity;
              const scol = cc.scope_status === "proportionate" ? "#4ade80"
                : cc.scope_status === "overloaded" ? "#f87171"
                : cc.scope_status === "approaching_capacity" ? "#fbbf24"
                : cc.scope_status === "underdeveloped" ? "#60a5fa" : "#a8a29e";
              const row = (label, val) => {
                if (val === null || val === undefined || val === "") return null;
                const text = Array.isArray(val)
                  ? val.map((v) => (typeof v === "object" ? JSON.stringify(v) : v)).join(" · ")
                  : (typeof val === "object" ? (val.value || JSON.stringify(val)) : String(val));
                if (!text) return null;
                return (
                  <div style={{ marginBottom: 4 }}>
                    <div style={{ color: "#a8a29e", textTransform: "uppercase", fontSize: 8.5, letterSpacing: "0.08em" }}>{label}</div>
                    <div style={{ color: "#f5f5f4", fontSize: 12 }}>{text}</div>
                  </div>
                );
              };
              return (
                <>
                  <div style={{ display: "flex", justifyContent: "space-between", gap: 8, marginBottom: 5 }}>
                    <span style={{ color: "#f59e0b", fontWeight: 700, textTransform: "uppercase", fontSize: 9, letterSpacing: "0.1em" }}>Communicative capacity (4.7)</span>
                    <span style={{ color: scol, fontWeight: 700, textTransform: "uppercase", fontSize: 9 }}>{cc.scope_status || "—"}</span>
                  </div>
                  {row("Writing unit", cc.writing_unit)}
                  {row("Unit purpose", cc.unit_purpose)}
                  {row("Expected functional range", cc.expected_functional_range)}
                  {row("Central communicative movement", cc.central_communicative_movement)}
                  {row("Current communicative load", cc.current_communicative_load)}
                  {row("Remaining capacity", cc.remaining_capacity)}
                  {row("Overload risk", cc.overload_risk)}
                  {row("Additions that still belong", cc.additions_that_still_belong)}
                  {row("Material to defer / exclude", cc.material_to_defer_or_exclude)}
                  {row("Unit scope disposition", cc.unit_scope_disposition)}
                  {row("Reason", cc.reason)}
                </>
              );
            })()}
          </div>
        )}

        {dco && !showRaw && (dco.instructional_contract || dco.instructional_contract_alignment) && (
          <div data-testid="dco-instructional_contract"
            style={{ marginBottom: 12, padding: "9px 11px", background: "#0c0a09",
              border: "1px solid #3f3f46", borderLeft: "3px solid #38bdf8", borderRadius: 6 }}>
            {(() => {
              const c = dco.instructional_contract || {};
              const a = dco.instructional_contract_alignment || {};
              const acol = a.alignment === "aligned" ? "#4ade80" : a.alignment === "misaligned" ? "#f87171"
                : a.alignment === "partially_aligned" ? "#fbbf24" : "#a8a29e";
              const row = (label, val) => (val || val === false) ? (
                <div style={{ marginBottom: 4 }}>
                  <div style={{ color: "#a8a29e", textTransform: "uppercase", fontSize: 8.5, letterSpacing: "0.08em" }}>{label}</div>
                  <div style={{ color: "#f5f5f4", fontSize: 12 }}>{String(val)}</div>
                </div>
              ) : null;
              return (
                <>
                  <div style={{ display: "flex", justifyContent: "space-between", gap: 8, marginBottom: 5 }}>
                    <span style={{ color: "#38bdf8", fontWeight: 700, textTransform: "uppercase", fontSize: 9, letterSpacing: "0.1em" }}>Instructional contract (4.6)</span>
                    <span style={{ color: acol, fontWeight: 700, textTransform: "uppercase", fontSize: 9 }}>{a.alignment || "—"}{a.in_scope ? " · in-scope" : ""}</span>
                  </div>
                  {row("Pinned episode target", dco.learner_relative_sufficiency && dco.learner_relative_sufficiency.learner_accessible_target)}
                  {row("Contract goal (student-facing, FIXED)", c.goal)}
                  {row("Where we are", c.where_we_are)}
                  {row("What happens next", c.what_happens_next)}
                  {row("Contract status", c.status)}
                  {row("Achieved", c.achieved)}
                  {row("Contract revision reason", c.revision_reason)}
                  <div style={{ borderTop: "1px dashed #3f3f46", margin: "6px 0 5px" }} />
                  {row("Selected coaching function", a.selected_function)}
                  {row("Contract function (in-scope)", a.contract_function)}
                  {row("Heuristic verdict", a.heuristic_verdict)}
                  {row("LLM escalated", a.llm_escalated)}
                  {row("Regeneration required", a.regeneration_required)}
                  {row("Regenerated", a.regenerated)}
                  {row("Reason", a.reason)}
                  {Array.isArray(a.evidence) && a.evidence.length ? row("Evidence", a.evidence.join(" · ")) : null}
                </>
              );
            })()}
          </div>
        )}

        {dco && !showRaw && dco.learner_relative_sufficiency && typeof dco.learner_relative_sufficiency === "object" && (
          <div data-testid="dco-learner_relative_sufficiency"
            style={{ marginBottom: 12, padding: "9px 11px", background: "#0c0a09",
              border: "1px solid #3f3f46", borderLeft: "3px solid #a3e635", borderRadius: 6 }}>
            {(() => {
              const x = dco.learner_relative_sufficiency;
              const vcol = x.value === "sufficient" ? "#4ade80" : x.value === "approaching_sufficiency" ? "#fbbf24"
                : x.value === "not_yet_sufficient" ? "#f87171" : "#a8a29e";
              const row = (label, val) => val ? (
                <div style={{ marginBottom: 4 }}>
                  <div style={{ color: "#a8a29e", textTransform: "uppercase", fontSize: 8.5, letterSpacing: "0.08em" }}>{label}</div>
                  <div style={{ color: "#f5f5f4", fontSize: 12 }}>{val}</div>
                </div>
              ) : null;
              return (
                <>
                  <div style={{ display: "flex", justifyContent: "space-between", gap: 8, marginBottom: 5 }}>
                    <span style={{ color: "#a3e635", fontWeight: 700, textTransform: "uppercase", fontSize: 9, letterSpacing: "0.1em" }}>Learner-relative sufficiency</span>
                    <span style={{ color: vcol, fontWeight: 700, textTransform: "uppercase", fontSize: 9 }}>{x.value || "—"}{x.confidence ? ` · ${x.confidence}` : ""}</span>
                  </div>
                  {row("Learner-accessible target", x.learner_accessible_target)}
                  {row("Episode target status", x.episode_target_status)}
                  {row("Episode target revision reason", x.episode_target_revision_reason)}
                  {row("Accessible target achieved", x.accessible_target_achieved)}
                  {row("Next developmental opportunity", x.next_developmental_opportunity)}
                  {row("Developmental advance", x.developmental_advance)}
                  {row("Organization stability", x.organization_stability)}
                  {row("Self-contained coherence", x.self_contained_coherence)}
                  {row("Task answered", x.task_answered)}
                  {row("Further growth potential", x.further_growth_potential)}
                  {row("Value of further instruction", x.likely_value_of_further_instruction)}
                  {row("Cost of further instruction", x.likely_cost_of_further_instruction)}
                  {row("Effectance risk", x.effectance_risk)}
                  {row("Transition recommendation", x.transition_recommendation)}
                  {row("Reason", x.reason)}
                </>
              );
            })()}
          </div>
        )}

        {dco && !showRaw && dco.task_relative_adequacy && typeof dco.task_relative_adequacy === "object" && (
          <div data-testid="dco-task_relative_adequacy"
            style={{ marginBottom: 12, padding: "9px 11px", background: "#0c0a09",
              border: "1px solid #3f3f46", borderLeft: "3px solid #f472b6", borderRadius: 6 }}>
            {(() => {
              const a = dco.task_relative_adequacy;
              const vcol = a.value === "adequate" ? "#4ade80" : a.value === "approaching_adequacy" ? "#fbbf24"
                : a.value === "inadequate" ? "#f87171" : "#a8a29e";
              const row = (label, val) => val ? (
                <div style={{ marginBottom: 4 }}>
                  <div style={{ color: "#a8a29e", textTransform: "uppercase", fontSize: 8.5, letterSpacing: "0.08em" }}>{label}</div>
                  <div style={{ color: "#f5f5f4", fontSize: 12 }}>{val}</div>
                </div>
              ) : null;
              const list = (label, arr) => Array.isArray(arr) && arr.length ? (
                <div style={{ marginBottom: 4 }}>
                  <div style={{ color: "#a8a29e", textTransform: "uppercase", fontSize: 8.5, letterSpacing: "0.08em" }}>{label}</div>
                  <ul style={{ margin: "1px 0 0", paddingLeft: 15, color: "#f5f5f4", fontSize: 12 }}>{arr.map((x,i)=><li key={i}>{x}</li>)}</ul>
                </div>
              ) : null;
              return (
                <>
                  <div style={{ display: "flex", justifyContent: "space-between", gap: 8, marginBottom: 5 }}>
                    <span style={{ color: "#f472b6", fontWeight: 700, textTransform: "uppercase", fontSize: 9, letterSpacing: "0.1em" }}>Task-relative adequacy</span>
                    <span style={{ color: vcol, fontWeight: 700, textTransform: "uppercase", fontSize: 9 }}>{a.value || "—"}{a.confidence ? ` · ${a.confidence}` : ""}</span>
                  </div>
                  {list("Task expectations", a.task_expectations)}
                  {list("Expectations met", a.expectations_met)}
                  {list("Expectations not yet met", a.expectations_not_yet_met)}
                  {row("Self-contained coherence", a.self_contained_coherence)}
                  {row("Material gap", a.material_gap || "— none")}
                  {row("Transition recommendation", a.transition_recommendation)}
                  {row("Reason", a.reason)}
                </>
              );
            })()}
            {dco.timely_success_status && typeof dco.timely_success_status === "object" && (
              <div data-testid="dco-timely_success_status" style={{ marginTop: 6, paddingTop: 6, borderTop: "1px solid #292524" }}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                  <span style={{ color: "#a8a29e", fontWeight: 600, textTransform: "uppercase", fontSize: 9, letterSpacing: "0.1em" }}>Timely success</span>
                  <span style={{ color: dco.timely_success_status.value === "achieved" ? "#4ade80"
                    : dco.timely_success_status.value === "within_reach" ? "#fbbf24"
                    : dco.timely_success_status.value === "missed_opportunity" ? "#f87171" : "#a8a29e",
                    fontWeight: 700, textTransform: "uppercase", fontSize: 9 }}>{dco.timely_success_status.value || "—"}</span>
                </div>
                {dco.timely_success_status.what_changed && <div style={{ color: "#f5f5f4", marginTop: 3, fontSize: 12 }}>changed: {dco.timely_success_status.what_changed}</div>}
                {dco.timely_success_status.how_it_improved && <div style={{ color: "#a8a29e", fontSize: 11 }}>improved: {dco.timely_success_status.how_it_improved}</div>}
                {dco.timely_success_status.reason && <div style={{ color: "#a8a29e", fontSize: 11 }}>{dco.timely_success_status.reason}</div>}
              </div>
            )}
          </div>
        )}

        {dco && !showRaw && dco.completion_readiness && typeof dco.completion_readiness === "object" && (
          <div data-testid="dco-completion_readiness"
            style={{ marginBottom: 12, padding: "9px 11px", background: "#0c0a09",
              border: "1px solid #3f3f46", borderLeft: "3px solid #22d3ee", borderRadius: 6 }}>
            <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
              <span style={{ color: "#a8a29e", fontWeight: 600, textTransform: "uppercase", fontSize: 9, letterSpacing: "0.1em" }}>
                Completion readiness
              </span>
              <span style={{ color: dco.completion_readiness.value === "ready" ? "#4ade80"
                : dco.completion_readiness.value === "nearly_ready" ? "#fbbf24"
                : dco.completion_readiness.value === "not_ready" ? "#f87171" : "#a8a29e",
                fontWeight: 700, textTransform: "uppercase", fontSize: 9 }}>
                {dco.completion_readiness.value || "—"}{dco.completion_readiness.confidence ? ` · ${dco.completion_readiness.confidence}` : ""}
              </span>
            </div>
            {dco.completion_readiness.reason && <div style={{ color: "#f5f5f4", marginTop: 3, fontSize: 12 }}>{dco.completion_readiness.reason}</div>}
            {dco.completion_message && (dco.completion_message.completion_statement || dco.completion_message.achievement_statement) && (
              <div data-testid="dco-completion_message" style={{ marginTop: 6, paddingTop: 6, borderTop: "1px solid #292524" }}>
                {[["completion_statement", "Completion"], ["achievement_statement", "Achievement"], ["boundary_statement", "Boundary"]].map(([k, lbl]) =>
                  dco.completion_message[k] ? (
                    <div key={k} style={{ marginBottom: 4 }}>
                      <div style={{ color: "#a8a29e", textTransform: "uppercase", fontSize: 8.5, letterSpacing: "0.08em" }}>{lbl}</div>
                      <div style={{ color: "#f5f5f4", fontSize: 12 }}>{dco.completion_message[k]}</div>
                    </div>
                  ) : null)}
              </div>
            )}
          </div>
        )}

        {dco && !showRaw && dco.learner_orientation && typeof dco.learner_orientation === "object" && (
          <div data-testid="dco-learner_orientation"
            style={{ marginBottom: 14, padding: "10px 11px", background: "#0c0a09",
              border: "1px solid #3f3f46", borderLeft: "3px solid #38bdf8", borderRadius: 6 }}>
            <div style={{ color: "#38bdf8", fontWeight: 700, textTransform: "uppercase", fontSize: 9,
              letterSpacing: "0.12em", marginBottom: 7 }}>
              Learner orientation · provisional (Stage 1, dev-only)
            </div>
            {ORIENT_FIELDS.map(([k, label]) => {
              const v = dco.learner_orientation[k];
              if (!v) return null;
              return (
                <div key={k} data-testid={`dco-orient-${k}`} style={{ marginBottom: 7 }}>
                  <div style={{ color: "#a8a29e", fontWeight: 600, textTransform: "uppercase",
                    fontSize: 8.5, letterSpacing: "0.09em" }}>{label}</div>
                  <div style={{ color: "#f5f5f4", marginTop: 2, fontSize: 12 }}>{v}</div>
                </div>
              );
            })}
          </div>
        )}

        {dco && !showRaw && dco.constructible_whole_map && Array.isArray(dco.constructible_whole_map.nodes)
          && dco.constructible_whole_map.nodes.length > 0 && (
          <div data-testid="dco-constructible_whole_map"
            style={{ marginBottom: 14, padding: "10px 11px", background: "#0c0a09",
              border: "1px solid #3f3f46", borderLeft: "3px solid #34d399", borderRadius: 6 }}>
            <div style={{ color: "#34d399", fontWeight: 700, textTransform: "uppercase", fontSize: 9,
              letterSpacing: "0.12em", marginBottom: 8 }}>
              Current direction · provisional (Stage 1, dev-only)
            </div>
            {dco.constructible_whole_map.question && (
              <>
                <div data-testid="dco-map-question" style={{ color: "#d6d3d1", textTransform: "uppercase",
                  fontSize: 9, letterSpacing: "0.1em", fontWeight: 600 }}>
                  {dco.constructible_whole_map.question}
                </div>
                <div style={{ color: "#57534e", textAlign: "center", fontSize: 12, margin: "1px 0" }}>↓</div>
              </>
            )}
            {dco.constructible_whole_map.nodes.slice(0, 5).map((n, i, arr) => {
              const st = (n.state || "").toLowerCase();
              const glyph = st === "established" ? "✓" : st === "current" ? "►" : st === "deferred" ? "⋯" : "○";
              const color = st === "established" ? "#4ade80" : st === "current" ? "#38bdf8"
                : st === "deferred" ? "#78716c" : "#d6d3d1";
              return (
                <div key={i} data-testid={`dco-map-node-${i}`}>
                  <div style={{ display: "flex", gap: 8, alignItems: "flex-start",
                    fontWeight: st === "current" ? 700 : 400, opacity: st === "deferred" ? 0.6 : 1 }}>
                    <span style={{ color, fontSize: 13, lineHeight: "18px", width: 12 }}>{glyph}</span>
                    <span style={{ color: st === "deferred" ? "#a8a29e" : "#f5f5f4", fontSize: 12 }}>{n.label}</span>
                  </div>
                  {i < Math.min(arr.length, 5) - 1 && (
                    <div style={{ color: "#57534e", textAlign: "center", fontSize: 12, margin: "1px 0 1px 5px" }}>↓</div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {dco && !showRaw && FIELDS.map(([key, label]) => {
          const raw = dco[key];
          const val = raw && typeof raw === "object" && !Array.isArray(raw) && "value" in raw ? raw.value : raw;
          const c = conf[key] || (raw && typeof raw === "object" ? raw.confidence : undefined);
          const evSrc = evidence[key] || (raw && typeof raw === "object" ? raw.evidence : undefined);
          const ev = Array.isArray(evSrc) ? evSrc : [];
          const valIsList = Array.isArray(val);
          const hasVal = valIsList ? val.length > 0 : Boolean(val);
          return (
            <div key={key} data-testid={`dco-${key}`}
              style={{ marginBottom: 12, paddingBottom: 10, borderBottom: "1px solid #292524" }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                <span style={{ color: "#a8a29e", fontWeight: 600, textTransform: "uppercase", fontSize: 9, letterSpacing: "0.1em" }}>
                  {label}
                </span>
                {c && <span style={{ color: confColor(c), fontWeight: 700, textTransform: "uppercase", fontSize: 9 }}>{c}</span>}
              </div>
              {valIsList ? (
                hasVal ? (
                  <ul style={{ margin: "4px 0 0", paddingLeft: 16, color: "#f5f5f4", fontSize: 12 }}>
                    {val.map((v, i) => (
                      <li key={i} style={{ marginBottom: 2,
                        color: String(v).trim().toLowerCase().startsWith("not yet") ? "#a8a29e" : "#f5f5f4" }}>{v}</li>
                    ))}
                  </ul>
                ) : (
                  <div style={{ color: "#78716c", marginTop: 3, fontSize: 12 }}>—</div>
                )
              ) : (
                <div style={{ color: hasVal ? "#f5f5f4" : "#78716c", marginTop: 3, fontSize: 12 }}>{val || "—"}</div>
              )}
              {ev.length > 0 && (
                <ul style={{ margin: "5px 0 0", paddingLeft: 16, color: "#a8a29e" }}>
                  {ev.map((e, i) => <li key={i} style={{ marginBottom: 2 }}>{e}</li>)}
                </ul>
              )}
            </div>
          );
        })}

        <div style={{ marginTop: 4, color: "#57534e" }}>GET /api/dev/functional-v3-trace/{sessionId}</div>

        {dco && !showRaw && (
          <div data-testid="sentence-craft-section" style={{ marginTop: 16, paddingTop: 12, borderTop: "1px solid #57534e" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8, marginBottom: 8 }}>
              <span style={{ color: "#c084fc", fontWeight: 700, textTransform: "uppercase", fontSize: 10, letterSpacing: "0.12em" }}>
                Sentence Craft · dev-only (Compass 4.3)
              </span>
              <button data-testid="sentence-craft-analyze" onClick={loadSC} disabled={scLoading}
                style={{ ...btnStyle, width: "auto", padding: "0 9px", color: "#e7e5e4",
                  borderColor: "#7e22ce", opacity: scLoading ? 0.5 : 1 }}>
                {scLoading ? "Analyzing…" : "Analyze sentences"}
              </button>
            </div>

            {(() => {
              const scr = dco.sentence_craft_readiness;
              if (!scr || typeof scr !== "object") return null;
              return (
                <div data-testid="dco-sentence_craft_readiness"
                  style={{ marginBottom: 10, padding: "8px 10px", background: "#0c0a09",
                    border: "1px solid #3f3f46", borderLeft: "3px solid #c084fc", borderRadius: 6 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                    <span style={{ color: "#a8a29e", fontWeight: 600, textTransform: "uppercase", fontSize: 9, letterSpacing: "0.1em" }}>
                      Sentence Craft readiness
                    </span>
                    <span style={{ color: scr.value === "ready" ? "#4ade80" : scr.value === "nearly_ready" ? "#fbbf24"
                      : scr.value === "not_ready" ? "#f87171" : "#a8a29e", fontWeight: 700, textTransform: "uppercase", fontSize: 9 }}>
                      {scr.value || "—"}{scr.confidence ? ` · ${scr.confidence}` : ""}
                    </span>
                  </div>
                  {scr.reason && <div style={{ color: "#f5f5f4", marginTop: 3, fontSize: 12 }}>{scr.reason}</div>}
                  {scr.developmental_work_remaining && (
                    <div style={{ color: "#a8a29e", marginTop: 3, fontSize: 11 }}>
                      remaining developmental work: {scr.developmental_work_remaining}
                    </div>
                  )}
                </div>
              );
            })()}

            {scError && <div style={{ color: "#f87171", fontSize: 11 }}>error: {scError}</div>}
            {!sc && !scError && !scLoading && (
              <div style={{ color: "#78716c", fontSize: 11 }}>
                Press "Analyze sentences" to run the dedicated Sentence Craft pass on the latest paragraph.
              </div>
            )}

            {sc?.sentence_craft_cognition?.selected_teaching && (() => {
              const t = sc.sentence_craft_cognition.selected_teaching;
              return (
                <div data-testid="sentence-craft-selected-teaching"
                  style={{ marginBottom: 10, padding: "9px 10px", background: "#0c0a09",
                    border: "1px solid #7e22ce", borderRadius: 6 }}>
                  <div style={{ color: "#c084fc", fontWeight: 700, textTransform: "uppercase", fontSize: 9,
                    letterSpacing: "0.1em", marginBottom: 6 }}>
                    Selected teaching · sentence #{t.sentence_index}
                  </div>
                  {[["pattern_noticed", "Pattern noticed"], ["instructional_principle", "Instructional principle"],
                    ["learner_invitation", "Learner invitation"], ["transferable_lesson", "Transferable lesson"]].map(([k, lbl]) =>
                    t[k] ? (
                      <div key={k} style={{ marginBottom: 5 }}>
                        <div style={{ color: "#a8a29e", textTransform: "uppercase", fontSize: 8.5, letterSpacing: "0.08em" }}>{lbl}</div>
                        <div style={{ color: "#f5f5f4", fontSize: 12 }}>{t[k]}</div>
                      </div>
                    ) : null)}
                  {Array.isArray(t.meaningful_alternatives) && t.meaningful_alternatives.length > 0 && (
                    <div>
                      <div style={{ color: "#a8a29e", textTransform: "uppercase", fontSize: 8.5, letterSpacing: "0.08em" }}>Meaningful alternatives</div>
                      <ul style={{ margin: "2px 0 0", paddingLeft: 16, color: "#f5f5f4", fontSize: 12 }}>
                        {t.meaningful_alternatives.map((a, i) => <li key={i}>{a}</li>)}
                      </ul>
                    </div>
                  )}
                </div>
              );
            })()}

            {Array.isArray(sc?.sentence_craft_cognition?.sentences) && sc.sentence_craft_cognition.sentences.map((s) => {
              const imp = (s.importance_to_whole || "").toLowerCase();
              const impColor = imp === "central" ? "#4ade80" : imp === "supporting" ? "#38bdf8"
                : imp === "distracting" ? "#f87171" : "#a8a29e";
              const prio = (s.teaching_priority || "").toLowerCase();
              const isTeach = prio === "teach_now";
              return (
                <div key={s.sentence_index} data-testid={`sentence-craft-sentence-${s.sentence_index}`}
                  style={{ marginBottom: 8, paddingBottom: 8, borderBottom: "1px solid #292524" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                    <span style={{ color: "#78716c", fontSize: 9 }}>#{s.sentence_index} · [{s.beginning_character_offset}-{s.ending_character_offset}]</span>
                    <span style={{ display: "flex", gap: 6 }}>
                      <span style={{ color: impColor, fontSize: 9, textTransform: "uppercase", fontWeight: 600 }}>{s.importance_to_whole || "—"}</span>
                      <span style={{ color: isTeach ? "#c084fc" : "#78716c", fontSize: 9, textTransform: "uppercase", fontWeight: 700 }}>{s.teaching_priority || "—"}</span>
                    </span>
                  </div>
                  <div style={{ color: "#e7e5e4", fontSize: 12, marginTop: 2, fontStyle: "italic" }}>"{s.exact_sentence_text}"</div>
                  {s.communicative_purpose && <div style={{ color: "#a8a29e", fontSize: 11, marginTop: 2 }}>purpose: {s.communicative_purpose}</div>}
                  {s.relation_to_constructible_whole && <div style={{ color: "#a8a29e", fontSize: 11 }}>role in whole: {s.relation_to_constructible_whole}</div>}
                  {Array.isArray(s.observed_sentence_patterns) && s.observed_sentence_patterns.length > 0 && (
                    <div style={{ color: "#fbbf24", fontSize: 11, marginTop: 2 }}>patterns: {s.observed_sentence_patterns.join("; ")}</div>
                  )}
                </div>
              );
            })}
            {sc && <div style={{ marginTop: 2, color: "#57534e" }}>GET /api/dev/sentence-craft/{sessionId}</div>}
          </div>
        )}
      </div>
    </div>
  );
}

const btnStyle = {
  background: "#1c1917", color: "#e7e5e4", border: "1px solid #57534e", borderRadius: 5,
  minWidth: 22, height: 22, cursor: "pointer", fontSize: 12, lineHeight: 1,
};
