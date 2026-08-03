import { useState, useEffect, useCallback } from "react";
import { getFunctionalTrace } from "@/lib/api";

// DEV-ONLY (Sprint 4.0-2). Shows the COMPLETE hidden Developmental Cognition Object for the latest
// turn — estimate + confidence + evidence per field, plus the raw object verbatim — so the developer
// can calibrate Compass's developmental reasoning after every interaction. Gated behind ?dco; never
// part of the learner experience. Reads GET /api/dev/functional-v3-trace/{sessionId}.

const FIELDS = [
  ["orientation_target_interpretation", "Orientation target — Compass's interpretation"],
  ["orientation_target_confirmed", "Orientation target — confirmed / revised by student"],
  ["conceptual_organization", "Conceptual organization"],
  ["communicative_organization", "Communicative organization"],
  ["coordinative_capacity", "Coordinative capacity (Fischer)"],
  ["instructional_horizon", "Instructional horizon"],
  ["reachable_next_move", "Reachable next move"],
  ["beyond_horizon", "Beyond the horizon"],
];

const confColor = (c) =>
  c === "high" ? "#4ade80" : c === "medium" ? "#fbbf24" : c === "low" ? "#f87171" : "#78716c";

export default function DevCognitionPanel({ sessionId, turnKey, onClose }) {
  const [rec, setRec] = useState(null);
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showRaw, setShowRaw] = useState(false);

  const load = useCallback(async () => {
    if (!sessionId) return;
    setLoading(true);
    setError("");
    try {
      const data = await getFunctionalTrace(sessionId);
      const trace = data?.trace || [];
      setCount(trace.length);
      setRec(trace.length ? trace[trace.length - 1] : null);
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

  if (!sessionId) return null;

  const dco = rec?.developmental_cognition || null;
  const conf = dco?.confidence || {};
  const evidence = dco?.evidence || {};

  return (
    <div
      data-testid="dev-cognition-panel"
      style={{
        position: "fixed",
        right: 16,
        bottom: 16,
        zIndex: 60,
        width: 420,
        maxHeight: "84vh",
        display: "flex",
        flexDirection: "column",
        fontFamily: "ui-monospace, 'IBM Plex Mono', monospace",
        fontSize: 11,
        lineHeight: 1.5,
        color: "#e7e5e4",
        background: "rgba(23,23,23,0.98)",
        border: "1px solid #57534e",
        borderRadius: 8,
        boxShadow: "0 10px 30px rgba(0,0,0,0.45)",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 8,
          padding: "9px 11px",
          background: "#292524",
          borderBottom: "1px solid #57534e",
        }}
      >
        <span style={{ letterSpacing: "0.12em", textTransform: "uppercase", color: "#a8a29e", fontWeight: 600 }}>
          Developmental Cognition · dev
        </span>
        <span style={{ display: "flex", gap: 6 }}>
          <button data-testid="dev-cognition-refresh" onClick={load} title="Refresh" style={btnStyle}>
            {loading ? "…" : "↻"}
          </button>
          <button
            data-testid="dev-cognition-raw"
            onClick={() => setShowRaw((v) => !v)}
            title="Toggle raw object"
            style={{ ...btnStyle, width: "auto", padding: "0 6px" }}
          >
            {showRaw ? "fields" : "raw"}
          </button>
          <button data-testid="dev-cognition-close" onClick={onClose} title="Close" style={btnStyle}>
            ✕
          </button>
        </span>
      </div>

      <div style={{ padding: "10px 12px", overflowY: "auto" }}>
        <div style={{ color: "#78716c", marginBottom: 8 }}>
          turn {count} · {rec?.turn_kind || "—"} · module: {rec?.reasoning_module_selected || "—"}
        </div>

        {error && <div style={{ color: "#f87171" }}>error: {error}</div>}
        {!error && !dco && (
          <div style={{ color: "#a8a29e" }}>
            No developmental_cognition yet. Complete a turn, then press ↻.
          </div>
        )}

        {dco && showRaw && (
          <pre
            data-testid="dco-raw"
            style={{
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
              background: "#0c0a09",
              border: "1px solid #44403c",
              borderRadius: 6,
              padding: 10,
              margin: 0,
              color: "#d6d3d1",
            }}
          >
            {JSON.stringify(dco, null, 2)}
          </pre>
        )}

        {dco &&
          !showRaw &&
          FIELDS.map(([key, label]) => {
            const val = dco[key];
            const c = conf[key];
            const ev = Array.isArray(evidence[key]) ? evidence[key] : [];
            return (
              <div
                key={key}
                data-testid={`dco-${key}`}
                style={{ marginBottom: 12, paddingBottom: 10, borderBottom: "1px solid #292524" }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                  <span style={{ color: "#a8a29e", fontWeight: 600, textTransform: "uppercase", fontSize: 9, letterSpacing: "0.1em" }}>
                    {label}
                  </span>
                  {c && (
                    <span style={{ color: confColor(c), fontWeight: 700, textTransform: "uppercase", fontSize: 9 }}>
                      {c}
                    </span>
                  )}
                </div>
                <div style={{ color: val ? "#f5f5f4" : "#78716c", marginTop: 3, fontSize: 12 }}>
                  {val || "—"}
                </div>
                {ev.length > 0 && (
                  <ul style={{ margin: "5px 0 0", paddingLeft: 16, color: "#a8a29e" }}>
                    {ev.map((e, i) => (
                      <li key={i} style={{ marginBottom: 2 }}>
                        {e}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            );
          })}

        <div style={{ marginTop: 4, color: "#57534e" }}>
          GET /api/dev/functional-v3-trace/{sessionId}
        </div>
      </div>
    </div>
  );
}

const btnStyle = {
  background: "#1c1917",
  color: "#e7e5e4",
  border: "1px solid #57534e",
  borderRadius: 5,
  minWidth: 22,
  height: 22,
  cursor: "pointer",
  fontSize: 12,
  lineHeight: 1,
};
