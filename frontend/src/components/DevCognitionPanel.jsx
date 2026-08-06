import { useState, useEffect, useCallback, useRef } from "react";
import { getFunctionalTrace } from "@/lib/api";

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
  const prevLenRef = useRef(0);

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
      </div>
    </div>
  );
}

const btnStyle = {
  background: "#1c1917", color: "#e7e5e4", border: "1px solid #57534e", borderRadius: 5,
  minWidth: 22, height: 22, cursor: "pointer", fontSize: 12, lineHeight: 1,
};
