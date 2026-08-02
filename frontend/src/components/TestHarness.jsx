import { useState, useEffect, useRef, useCallback } from "react";
import {
  listTestCases,
  startTestRun,
  getTestRun,
  listTestRuns,
  renameTestRun,
  exportTestRunUrl,
} from "@/lib/api";
import {
  Play,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Download,
  ChevronDown,
  ChevronRight,
  FlaskConical,
  History,
  GitCompare,
  Pencil,
} from "lucide-react";

const VERDICT = {
  pass: { icon: CheckCircle2, cls: "text-emerald-400", badge: "bg-emerald-950 text-emerald-300 border-emerald-800" },
  partial: { icon: AlertTriangle, cls: "text-amber-400", badge: "bg-amber-950 text-amber-300 border-amber-800" },
  fail: { icon: XCircle, cls: "text-rose-400", badge: "bg-rose-950 text-rose-300 border-rose-800" },
  error: { icon: XCircle, cls: "text-stone-400", badge: "bg-stone-800 text-stone-400 border-stone-700" },
};

const StatBadge = ({ label, value, cls }) => (
  <div className={`px-3 py-2 rounded-md border ${cls}`}>
    <div className="text-2xl font-semibold leading-none">{value}</div>
    <div className="text-[10px] uppercase tracking-widest mt-1 opacity-80">{label}</div>
  </div>
);

const VBadge = ({ v }) => {
  const m = VERDICT[v] || VERDICT.error;
  return (
    <span className={`text-[10px] uppercase tracking-widest px-2 py-0.5 rounded border ${m.badge}`}>
      {v || "—"}
    </span>
  );
};

function diffRuns(prev, next) {
  const pById = Object.fromEntries((prev.results || []).map((r) => [r.case_id, r]));
  const nById = Object.fromEntries((next.results || []).map((r) => [r.case_id, r]));
  const ids = Array.from(new Set([...Object.keys(pById), ...Object.keys(nById)])).sort(
    (a, b) => parseInt(a.replace(/\D/g, "")) - parseInt(b.replace(/\D/g, ""))
  );
  return ids.map((id) => {
    const p = pById[id];
    const n = nById[id];
    const pc = Object.fromEntries((p?.evaluation?.criteria || []).map((c) => [c.name, c.verdict]));
    const changed = (n?.evaluation?.criteria || [])
      .filter((c) => pc[c.name] !== undefined && pc[c.name] !== c.verdict)
      .map((c) => ({ name: c.name, from: pc[c.name], to: c.verdict, note: c.note }));
    return {
      id,
      name: n?.name || p?.name || id,
      pv: p?.status,
      nv: n?.status,
      moved: (p?.status || "") !== (n?.status || ""),
      changed,
      explanation: n?.evaluation?.summary || "",
      gov: n?.turns?.[0]?.governance_trace || null,
      govNote: n?.governance_note || "",
      path: n?.turns?.[0]?.reasoning_path || "",
    };
  });
}

const LensChips = ({ items, tone }) => (
  <div className="flex flex-wrap gap-1">
    {(items || []).length === 0 ? (
      <span className="text-[11px] text-stone-600 italic">constitutional / policy core only</span>
    ) : (
      items.map((x, i) => (
        <span
          key={i}
          className={`text-[10px] px-1.5 py-0.5 rounded border ${
            tone === "active"
              ? "border-emerald-800 bg-emerald-950/50 text-emerald-300"
              : "border-stone-700 bg-stone-900 text-stone-500 line-through decoration-stone-600"
          }`}
        >
          {x}
        </span>
      ))
    )}
  </div>
);

const GovernancePanel = ({ gov, govNote }) => {
  if (!gov) {
    return (
      <div className="text-[11px] text-stone-500 italic">
        No triage governance trace (baseline run is the exhaustive frozen engine).
      </div>
    );
  }
  const Row = ({ k, v }) => (
    <div className="flex gap-2 text-[11px]">
      <span className="text-stone-500 w-40 shrink-0">{k}</span>
      <span className="text-stone-300">{v}</span>
    </div>
  );
  return (
    <div className="space-y-3" data-testid="governance-panel">
      {govNote && (
        <div className="text-[11px] text-amber-200 border border-amber-800/60 bg-amber-950/30 rounded px-2.5 py-2" data-testid="governance-note">
          <span className="uppercase tracking-widest text-[9px] text-amber-400/80">Why triage better</span>
          <div className="mt-1 leading-relaxed">{govNote}</div>
        </div>
      )}
      <Row k="Triage route" v={<span className="text-sky-300">{gov.route || "—"}</span>} />
      <Row k="Inside / outside" v={gov.inside_outside || "—"} />
      <Row k="Triaged dimension" v={gov.dimension || "—"} />
      <div>
        <div className="text-[10px] uppercase tracking-widest text-stone-500 mb-1">L3 active lenses</div>
        <LensChips items={gov.active_lenses} tone="active" />
      </div>
      <div>
        <div className="text-[10px] uppercase tracking-widest text-stone-500 mb-1">L3 dormant lenses (held off)</div>
        <LensChips items={gov.dormant_lenses} tone="dormant" />
      </div>
      <Row k="Permitted moves" v={(gov.permitted_moves || []).join(", ") || "—"} />
      <Row k="May open new target" v={gov.may_select_new_target ? "yes" : "no — keep current"} />
      <Row k="Consolidation / fading" v={`${gov.consolidation_allowed ? "consolidate" : "—"} / ${gov.fading_allowed ? "fade" : "—"}`} />
      <Row
        k="Fallback"
        v={
          gov.fallback_occurred ? (
            <span className="text-rose-300">{gov.fallback_kind}{gov.fallback_reason ? ` — ${gov.fallback_reason}` : ""}</span>
          ) : (
            <span className="text-emerald-300">none (focused path)</span>
          )
        }
      />
      <div>
        <div className="text-[10px] uppercase tracking-widest text-stone-500 mb-1">Candidate deliberation</div>
        {(gov.candidate_invitations || []).length > 0 ? (
          <ul className="space-y-1">
            {gov.candidate_invitations.map((c, i) => (
              <li key={i} className={`text-[11px] px-2 py-1 rounded border ${c === gov.selected_invitation ? "border-emerald-800 bg-emerald-950/40 text-emerald-200" : "border-stone-800 bg-stone-900 text-stone-400"}`}>
                {c === gov.selected_invitation && <span className="text-[9px] uppercase tracking-widest text-emerald-400 mr-1">selected</span>}
                {c}
              </li>
            ))}
          </ul>
        ) : (
          <span className="text-[11px] text-stone-600 italic">Not captured in this run (available in runs recorded after Governance v1 tracing).</span>
        )}
      </div>
      <div>
        <div className="text-[10px] uppercase tracking-widest text-stone-500 mb-1">Governance layer trace</div>
        <ol className="space-y-0.5">
          {(gov.governance_layers || []).map((l, i) => (
            <li key={i} className="text-[10px] text-stone-400 leading-relaxed">{l}</li>
          ))}
        </ol>
      </div>
    </div>
  );
};

const CompareRow = ({ r }) => {
  const [open, setOpen] = useState(false);
  const hasGov = !!r.gov || !!r.govNote;
  return (
    <div
      data-testid={`compare-row-${r.id}`}
      className={`border-t border-stone-800 text-[12px] ${r.moved ? "bg-stone-900/60" : ""}`}
    >
      <div className="grid grid-cols-[70px_1fr_90px_90px_1.4fr_40px] gap-2 px-3 py-2.5 items-start">
        <div className="text-stone-500">{r.id}</div>
        <div className="text-stone-300 truncate">{r.name}</div>
        <div><VBadge v={r.pv} /></div>
        <div><VBadge v={r.nv} /></div>
        <div className="text-stone-400">
          {r.changed.length > 0 && (
            <ul className="mb-1 space-y-0.5">
              {r.changed.map((c, i) => (
                <li key={i}>
                  <span className="text-stone-500">{c.name}:</span>{" "}
                  <span className="text-rose-300">{c.from}</span>→<span className="text-emerald-300">{c.to}</span>
                </li>
              ))}
            </ul>
          )}
          <span className="text-stone-500">{r.explanation}</span>
        </div>
        <div>
          <button
            data-testid={`compare-gov-toggle-${r.id}`}
            onClick={() => setOpen((o) => !o)}
            aria-expanded={open}
            className={`inline-flex items-center justify-center h-6 w-6 rounded border transition-colors ${hasGov ? "border-sky-800 text-sky-300 hover:bg-sky-950/40" : "border-stone-800 text-stone-600"}`}
            title="Governance trace"
          >
            {open ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
          </button>
        </div>
      </div>
      {open && (
        <div className="px-3 pb-3 pt-1 border-t border-stone-800/60 bg-stone-950/40" data-testid={`compare-gov-detail-${r.id}`}>
          <GovernancePanel gov={r.gov} govNote={r.govNote} />
        </div>
      )}
    </div>
  );
};

const CompareView = ({ runs }) => {
  const [aId, setAId] = useState("");
  const [bId, setBId] = useState("");
  const [runA, setRunA] = useState(null);
  const [runB, setRunB] = useState(null);
  const [rows, setRows] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const runCompare = async () => {
    if (!aId || !bId) return;
    setLoading(true);
    setError("");
    try {
      const [a, b] = await Promise.all([getTestRun(aId), getTestRun(bId)]);
      setRunA(a);
      setRunB(b);
      setRows(diffRuns(a, b));
    } catch (e) {
      setError("Could not load one or both runs. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const label = (r) =>
    `${r.label ? r.label + " · " : ""}${new Date(r.created_at).toLocaleString()} · ${r.total} cases${
      r.summary?.pass_rate != null ? ` · ${r.summary.pass_rate}%` : ""
    }`;

  const moved = (rows || []).filter((r) => r.moved);

  return (
    <div className="space-y-5" data-testid="compare-view">
      <div className="flex flex-wrap items-end gap-3">
        <div>
          <div className="text-[10px] uppercase tracking-widest text-stone-500 mb-1">Previous run</div>
          <select
            data-testid="compare-select-prev"
            value={aId}
            onChange={(e) => setAId(e.target.value)}
            className="bg-stone-900 border border-stone-700 rounded px-3 py-2 text-[12px] text-stone-200 min-w-[280px]"
          >
            <option value="">Select…</option>
            {runs.map((r) => (
              <option key={r.id} value={r.id}>
                {label(r)}
              </option>
            ))}
          </select>
        </div>
        <div>
          <div className="text-[10px] uppercase tracking-widest text-stone-500 mb-1">New run</div>
          <select
            data-testid="compare-select-new"
            value={bId}
            onChange={(e) => setBId(e.target.value)}
            className="bg-stone-900 border border-stone-700 rounded px-3 py-2 text-[12px] text-stone-200 min-w-[280px]"
          >
            <option value="">Select…</option>
            {runs.map((r) => (
              <option key={r.id} value={r.id}>
                {label(r)}
              </option>
            ))}
          </select>
        </div>
        <button
          onClick={runCompare}
          disabled={!aId || !bId || loading}
          data-testid="compare-run-button"
          className="inline-flex items-center gap-1.5 text-[11px] uppercase tracking-widest px-3 py-2 rounded bg-amber-600 text-stone-950 font-semibold hover:bg-amber-500 disabled:opacity-40 transition-colors"
        >
          {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <GitCompare className="h-3.5 w-3.5" />}
          Compare
        </button>
      </div>

      {error && (
        <div data-testid="compare-error" className="text-[12px] text-rose-300 border border-rose-800 bg-rose-950/40 rounded px-3 py-2">
          {error}
        </div>
      )}
      {rows && (
        <>
          <div className="flex flex-wrap gap-3" data-testid="compare-summary">
            <StatBadge label="Prev pass rate" value={`${runA?.summary?.pass_rate ?? "—"}%`} cls="border-stone-700 text-stone-300" />
            <StatBadge label="New pass rate" value={`${runB?.summary?.pass_rate ?? "—"}%`} cls="border-amber-700 text-amber-300" />
            <StatBadge label="Cases moved" value={moved.length} cls="border-sky-800 text-sky-300" />
          </div>

          <div className="border border-stone-800 rounded-md overflow-hidden">
            <div className="grid grid-cols-[70px_1fr_90px_90px_1.4fr_40px] gap-2 px-3 py-2 bg-stone-900 text-[10px] uppercase tracking-widest text-stone-500">
              <div>Case</div><div>Name</div><div>Prev</div><div>New</div><div>Changed criteria / explanation</div><div>Gov</div>
            </div>
            {rows.map((r) => (
              <CompareRow key={r.id} r={r} />
            ))}
          </div>
        </>
      )}
    </div>
  );
};

const CaseResultCard = ({ result }) => {
  const [open, setOpen] = useState(false);
  const v = VERDICT[result.status] || VERDICT.error;
  const Icon = v.icon;
  const ev = result.evaluation || {};
  return (
    <div
      data-testid={`result-card-${result.case_id}`}
      className="border border-stone-800 rounded-md bg-stone-900/60 overflow-hidden"
    >
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-stone-800/50 transition-colors"
        data-testid={`result-toggle-${result.case_id}`}
      >
        {open ? <ChevronDown className="h-4 w-4 text-stone-500" /> : <ChevronRight className="h-4 w-4 text-stone-500" />}
        <Icon className={`h-4 w-4 shrink-0 ${v.cls}`} />
        <span className="text-xs text-stone-500 w-12 shrink-0">{result.case_id}</span>
        <span className="text-sm text-stone-200 flex-1 truncate">{result.name}</span>
        <span className={`text-[10px] uppercase tracking-widest px-2 py-0.5 rounded border ${v.badge}`}>
          {result.status}
        </span>
      </button>
      {open && (
        <div className="px-4 pb-4 pt-1 border-t border-stone-800 space-y-3">
          {ev.summary && <p className="text-[13px] text-stone-300 italic leading-relaxed">{ev.summary}</p>}
          {(ev.criteria || []).map((c, i) => {
            const cv = VERDICT[c.verdict] || VERDICT.error;
            const CI = cv.icon;
            return (
              <div key={i} className="flex items-start gap-2 text-[12px]">
                <CI className={`h-3.5 w-3.5 mt-0.5 shrink-0 ${cv.cls}`} />
                <div>
                  <span className="text-stone-400">{c.name}</span>{" "}
                  <span className={cv.cls}>[{c.verdict}]</span>
                  <div className="text-stone-500">{c.note}</div>
                </div>
              </div>
            );
          })}
          {result.error && <div className="text-rose-400 text-[12px]">Error: {result.error}</div>}
          <div className="space-y-3 pt-2">
            {(result.turns || []).map((t, i) => (
              <div key={i} className="border border-stone-800 rounded p-3 bg-stone-950/40 text-[12px] space-y-1">
                <div className="text-[10px] uppercase tracking-widest text-amber-500">
                  Turn {i + 1} · {t.kind} · {t.latency_s}s · prompt {t.reasoner_prompt_bytes}B
                </div>
                <div><span className="text-stone-500">Student:</span> <span className="text-stone-300">{t.student_input}</span></div>
                <div><span className="text-stone-500">Tutor:</span> <span className="text-stone-200">{t.invitation}</span></div>
                <div className="grid grid-cols-2 gap-x-4 gap-y-0.5 pt-1 text-stone-400">
                  <div><span className="text-stone-600">element:</span> {t.active_instructional_element || "—"}</div>
                  <div><span className="text-stone-600">focus:</span> {t.intervention_focus}</div>
                  <div className="col-span-2"><span className="text-stone-600">target:</span> {t.primary_target || "—"}</div>
                  <div><span className="text-stone-600">cycle:</span> {t.cycle_status || "—"}</div>
                  <div><span className="text-stone-600">control:</span> {t.degree_of_student_control || "—"}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default function TestHarness() {
  const [cases, setCases] = useState([]);
  const [selected, setSelected] = useState(new Set());
  const [run, setRun] = useState(null);
  const [runs, setRuns] = useState([]);
  const [starting, setStarting] = useState(false);
  const [mode, setMode] = useState("run");
  const [runLabel, setRunLabel] = useState("");
  const pollRef = useRef(null);

  const refreshRuns = useCallback(() => {
    listTestRuns().then(setRuns).catch(() => {});
  }, []);

  useEffect(() => {
    listTestCases().then(setCases).catch(() => {});
    refreshRuns();
  }, [refreshRuns]);

  // poll the active run while it's still running
  useEffect(() => {
    if (!run?.id || run.status !== "running") {
      if (pollRef.current) clearInterval(pollRef.current);
      return;
    }
    pollRef.current = setInterval(async () => {
      try {
        const r = await getTestRun(run.id);
        setRun(r);
        if (r.status !== "running") {
          clearInterval(pollRef.current);
          refreshRuns();
        }
      } catch (e) {
        /* keep polling */
      }
    }, 3000);
    return () => pollRef.current && clearInterval(pollRef.current);
  }, [run?.id, run?.status, refreshRuns]);

  const toggleCase = (id) => {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const doRun = async (caseIds) => {
    setStarting(true);
    try {
      const r = await startTestRun(caseIds, runLabel);
      setRunLabel("");
      setRun(await getTestRun(r.id));
    } catch (e) {
      /* noop */
    } finally {
      setStarting(false);
    }
  };

  const loadRun = async (id) => {
    setRun(await getTestRun(id));
  };

  const doRename = async (r) => {
    const next = window.prompt("Label for this run:", r.label || "");
    if (next === null) return;
    await renameTestRun(r.id, next);
    refreshRuns();
    if (run?.id === r.id) setRun({ ...run, label: next });
  };

  const s = run?.summary || {};
  const isRunning = run?.status === "running";
  const progress = run ? Math.round(((run.completed_count || 0) / (run.total || 1)) * 100) : 0;

  return (
    <div className="min-h-screen bg-stone-950 text-stone-200 font-mono-panel" data-testid="tests-page">
      <header className="border-b border-stone-800 px-6 py-4 flex items-center gap-3 sticky top-0 bg-stone-950/95 backdrop-blur z-10">
        <FlaskConical className="h-5 w-5 text-amber-500" />
        <div>
          <h1 className="text-sm uppercase tracking-[0.2em] text-stone-100">Instructional Test Harness</h1>
          <p className="text-[11px] text-stone-500">Developer-only · runs the real production engine + LLM evaluator</p>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <div className="flex items-center rounded border border-stone-700 overflow-hidden mr-1">
            <button
              onClick={() => setMode("run")}
              data-testid="mode-run-button"
              className={`text-[11px] uppercase tracking-widest px-3 py-2 transition-colors ${
                mode === "run" ? "bg-stone-800 text-amber-300" : "text-stone-400 hover:text-stone-200"
              }`}
            >
              Run
            </button>
            <button
              onClick={() => setMode("compare")}
              data-testid="mode-compare-button"
              className={`inline-flex items-center gap-1.5 text-[11px] uppercase tracking-widest px-3 py-2 transition-colors ${
                mode === "compare" ? "bg-stone-800 text-amber-300" : "text-stone-400 hover:text-stone-200"
              }`}
            >
              <GitCompare className="h-3.5 w-3.5" /> Compare
            </button>
          </div>
          <input
            type="text"
            value={runLabel}
            onChange={(e) => setRunLabel(e.target.value)}
            placeholder="Run label (optional)"
            data-testid="run-label-input"
            disabled={mode === "compare"}
            className="bg-stone-900 border border-stone-700 rounded px-3 py-2 text-[12px] text-stone-200 placeholder:text-stone-600 w-44 disabled:opacity-40"
          />
          <button
            onClick={() => doRun([...selected])}
            disabled={starting || isRunning || selected.size === 0 || mode === "compare"}
            data-testid="run-selected-button"
            className="inline-flex items-center gap-1.5 text-[11px] uppercase tracking-widest px-3 py-2 rounded border border-stone-700 text-stone-300 hover:border-amber-600 hover:text-amber-300 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <Play className="h-3.5 w-3.5" /> Run Selected ({selected.size})
          </button>
          <button
            onClick={() => doRun(null)}
            disabled={starting || isRunning || mode === "compare"}
            data-testid="run-all-button"
            className="inline-flex items-center gap-1.5 text-[11px] uppercase tracking-widest px-3 py-2 rounded bg-amber-600 text-stone-950 font-semibold hover:bg-amber-500 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            {starting || isRunning ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
            Run All ({cases.length})
          </button>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-[300px_1fr] gap-0">
        {/* left rail: cases + history */}
        <aside className="border-r border-stone-800 p-4 space-y-6 lg:h-[calc(100vh-73px)] lg:overflow-y-auto">
          <div>
            <div className="text-[10px] uppercase tracking-widest text-stone-500 mb-2">Test Cases</div>
            <div className="space-y-1">
              {cases.map((c) => (
                <label
                  key={c.id}
                  className="flex items-start gap-2 text-[12px] px-2 py-1.5 rounded hover:bg-stone-900 cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={selected.has(c.id)}
                    onChange={() => toggleCase(c.id)}
                    data-testid={`case-checkbox-${c.id}`}
                    className="mt-0.5 accent-amber-600"
                  />
                  <span className="text-stone-600 w-9 shrink-0">{c.id}</span>
                  <span className="text-stone-300 leading-tight">{c.name}</span>
                </label>
              ))}
            </div>
          </div>

          <div>
            <div className="text-[10px] uppercase tracking-widest text-stone-500 mb-2 flex items-center gap-1.5">
              <History className="h-3 w-3" /> Past Runs
            </div>
            <div className="space-y-1">
              {runs.length === 0 && <div className="text-[11px] text-stone-600">No runs yet.</div>}
              {runs.map((r) => (
                <div
                  key={r.id}
                  data-testid={`past-run-${r.id}`}
                  onClick={() => loadRun(r.id)}
                  className={`w-full text-left text-[11px] px-2 py-1.5 rounded hover:bg-stone-900 cursor-pointer ${
                    run?.id === r.id ? "bg-stone-900 border border-stone-700" : ""
                  }`}
                >
                  <div className="flex items-center justify-between gap-1">
                    <span className="text-stone-300 font-medium truncate">
                      {r.label ? r.label : new Date(r.created_at).toLocaleString()}
                    </span>
                    <div className="flex items-center gap-1 shrink-0">
                      <button
                        type="button"
                        data-testid={`rename-run-${r.id}`}
                        onClick={(e) => {
                          e.stopPropagation();
                          doRename(r);
                        }}
                        className="text-stone-500 hover:text-amber-300"
                        title="Rename run"
                      >
                        <Pencil className="h-3 w-3" />
                      </button>
                      <span className={r.status === "running" ? "text-amber-400" : "text-emerald-400"}>{r.status}</span>
                    </div>
                  </div>
                  <div className="text-stone-600">
                    {r.label ? `${new Date(r.created_at).toLocaleDateString()} · ` : ""}
                    {r.total} cases {r.summary?.pass_rate != null ? `· ${r.summary.pass_rate}% pass` : ""}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </aside>

        {/* main: run results */}
        <main className="p-6 space-y-5">
          {mode === "compare" ? (
            <CompareView runs={runs} />
          ) : (
          <>
          {!run && (
            <div className="text-stone-500 text-sm py-20 text-center">
              Select cases and press <span className="text-amber-400">Run Selected</span>, or{" "}
              <span className="text-amber-400">Run All</span> to start a full instructional evaluation.
            </div>
          )}

          {run && (
            <>
              <div className="flex flex-wrap items-center gap-3" data-testid="test-summary">
                <StatBadge label="Total" value={run.total} cls="border-stone-700 text-stone-200" />
                <StatBadge label="Pass" value={s.pass ?? 0} cls="border-emerald-800 text-emerald-300" />
                <StatBadge label="Partial" value={s.partial ?? 0} cls="border-amber-800 text-amber-300" />
                <StatBadge label="Fail" value={s.fail ?? 0} cls="border-rose-800 text-rose-300" />
                <StatBadge label="Error" value={s.error ?? 0} cls="border-stone-700 text-stone-400" />
                {s.pass_rate != null && (
                  <StatBadge label="Pass Rate" value={`${s.pass_rate}%`} cls="border-amber-700 text-amber-300" />
                )}
                <div className="ml-auto flex items-center gap-2">
                  <a
                    href={exportTestRunUrl(run.id, "json")}
                    data-testid="export-run-json"
                    className="inline-flex items-center gap-1.5 text-[11px] uppercase tracking-widest px-3 py-2 rounded border border-stone-700 text-stone-300 hover:border-stone-500 transition-colors"
                  >
                    <Download className="h-3.5 w-3.5" /> JSON
                  </a>
                  <a
                    href={exportTestRunUrl(run.id, "markdown")}
                    data-testid="export-run-md"
                    className="inline-flex items-center gap-1.5 text-[11px] uppercase tracking-widest px-3 py-2 rounded border border-stone-700 text-stone-300 hover:border-stone-500 transition-colors"
                  >
                    <Download className="h-3.5 w-3.5" /> Markdown
                  </a>
                </div>
              </div>

              <div data-testid="test-progress">
                <div className="flex items-center justify-between text-[11px] text-stone-500 mb-1">
                  <span>
                    {isRunning ? (
                      <span className="inline-flex items-center gap-1.5 text-amber-400">
                        <Loader2 className="h-3 w-3 animate-spin" /> Running…
                      </span>
                    ) : (
                      "Complete"
                    )}
                  </span>
                  <span>
                    {run.completed_count || 0} / {run.total}
                  </span>
                </div>
                <div className="h-1.5 bg-stone-800 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-amber-500 transition-all duration-500"
                    style={{ width: `${progress}%` }}
                  />
                </div>
              </div>

              <div className="space-y-2">
                {(run.results || []).map((r) => (
                  <CaseResultCard key={r.case_id} result={r} />
                ))}
                {isRunning && (
                  <div className="text-[12px] text-stone-500 py-3 text-center">
                    Reasoning through the remaining cases with the live engine…
                  </div>
                )}
              </div>
            </>
          )}
          </>
          )}
        </main>
      </div>
    </div>
  );
}
