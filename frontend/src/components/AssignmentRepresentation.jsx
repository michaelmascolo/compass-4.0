import { useState, useEffect, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Toaster, toast } from "sonner";
import {
  ArrowRight,
  ArrowLeft,
  Loader2,
  FileText,
  Compass as CompassIcon,
  Pencil,
  CornerDownRight,
  CircleDot,
  Code2,
  Download,
  ChevronDown,
  BookOpen,
  X,
  Clock,
  Layers,
} from "lucide-react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  createAssignmentSession,
  getAssignmentSession,
  editAssignment,
  submitInterpretation,
  submitOperation,
  submitRestatement,
  setDeveloperMeta,
  getSessionLibrary,
  assignmentRecordUrl,
  getHandoff,
  beginWorkingFromRepresentation,
  assessKnowledge,
  knowledgeRespond,
  knowledgeSkip,
} from "@/lib/api";

const STORE = "compass_rep_session";

const SPRINT_RECOMMENDATIONS = [
  "No change needed",
  "Prompt revision",
  "New scaffold",
  "New developmental operation",
  "Developmental Control Engine revision",
  "UI revision",
  "Other",
];

const SAMPLE =
  "Compare fixed and growth mindsets. Explain how each mindset affects both the process and outcomes of learning. Use relevant examples to support your explanation.";

const STATUS_META = {
  understood: { label: "Understood", dot: "#5b7a52", text: "text-[#41603a]", bg: "bg-[#eef2ea]" },
  developing: { label: "Developing", dot: "#b8863b", text: "text-[#8a6524]", bg: "bg-[#f6efe1]" },
  needs_attention: { label: "Needs Attention", dot: "#8C3A2A", text: "text-[#8C3A2A]", bg: "bg-[#f5e6e1]" },
  unconfirmed: { label: "Unconfirmed Requirement", dot: "#a8a29e", text: "text-stone-500", bg: "bg-stone-100" },
};

const meta = (s) => STATUS_META[s] || STATUS_META.unconfirmed;

// Non-developmental demand categories are monitored, not scaffolded.
const MONITORED = { constraint: "Constraint", formatting: "Formatting", resource: "Resource" };

// ---------------------------------------------------------------------------
function DemandRow({ d, active, flash }) {
  const m = meta(d.status);
  const monitored = MONITORED[d.category];
  return (
    <motion.div
      layout
      data-testid={`demand-${d.id}`}
      data-status={d.status}
      data-category={d.category}
      animate={flash ? { backgroundColor: ["#fff7ed", "#ffffff"] } : {}}
      transition={{ duration: 1.2 }}
      className={`relative rounded-sm bg-white pl-4 pr-3 py-3 ${
        active ? "ring-1 ring-[#8C3A2A]" : ""
      } ${monitored ? "opacity-80" : ""}`}
      style={{
        borderLeft: `3px ${d.source === "inferred" ? "dashed" : "solid"} ${
          active ? "#8C3A2A" : monitored ? "#e7e5e4" : "#d6d3d1"
        }`,
      }}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-serif-display text-[15px] leading-snug text-stone-900">
              {d.label}
            </span>
            <span
              className="shrink-0 rounded-sm border border-stone-200 px-1.5 py-px text-[9px] font-mono-panel uppercase tracking-[0.14em] text-stone-400"
              title={d.source === "inferred" ? "Inferred from the task" : "Stated in the assignment"}
            >
              {d.source === "inferred" ? "Inferred" : "Explicit"}
            </span>
          </div>
          {!monitored && d.operation && (
            <p className="mt-0.5 text-[11px] font-mono-panel uppercase tracking-[0.12em] text-stone-400">
              {d.operation}
            </p>
          )}
        </div>
        {monitored ? (
          <span
            className="inline-flex shrink-0 items-center gap-1.5 rounded-full border border-stone-200 px-2 py-1 text-[10px] font-mono-panel uppercase tracking-[0.1em] text-stone-400"
            title="A requirement to keep in mind — not a thinking task"
          >
            {monitored}
          </span>
        ) : (
          <span
            className={`inline-flex shrink-0 items-center gap-1.5 rounded-full px-2 py-1 text-[10px] font-mono-panel uppercase tracking-[0.1em] ${m.bg} ${m.text}`}
          >
            <span className="h-1.5 w-1.5 rounded-full" style={{ background: m.dot }} />
            {m.label}
          </span>
        )}
      </div>
      {active && (
        <div className="mt-1.5 inline-flex items-center gap-1 text-[10px] font-mono-panel uppercase tracking-[0.14em] text-[#8C3A2A]">
          <CircleDot className="h-3 w-3" /> Working on this
        </div>
      )}
    </motion.div>
  );
}

function QuestionMap({ session, flashIds }) {
  return (
    <div data-testid="question-map" className="space-y-2.5">
      <p className="mb-1 font-mono-panel text-[10px] uppercase tracking-[0.2em] text-stone-500">
        What this assignment asks
      </p>
      <AnimatePresence initial={false}>
        {session.demands.map((d) => (
          <DemandRow
            key={d.id}
            d={d}
            active={d.id === session.active_target_id}
            flash={flashIds.has(d.id)}
          />
        ))}
      </AnimatePresence>
      <p className="pt-1 text-[11px] leading-relaxed text-stone-400">
        Solid border = stated in the assignment · dashed = inferred. This map is adequate for now,
        not a permanent checklist.
      </p>
    </div>
  );
}

function AssignmentPanel({ text, onEdit }) {
  return (
    <div className="rounded-sm border border-stone-200 bg-[#faf9f6] p-5">
      <div className="mb-2 flex items-center justify-between">
        <span className="flex items-center gap-1.5 font-mono-panel text-[10px] uppercase tracking-[0.2em] text-stone-500">
          <FileText className="h-3.5 w-3.5" /> The assignment
        </span>
        {onEdit && (
          <button
            onClick={onEdit}
            data-testid="edit-assignment-button"
            className="inline-flex items-center gap-1 text-[10px] font-mono-panel uppercase tracking-[0.14em] text-stone-400 transition-colors hover:text-[#8C3A2A]"
          >
            <Pencil className="h-3 w-3" /> Edit
          </button>
        )}
      </div>
      <p className="font-serif-display text-[17px] leading-relaxed text-stone-900">{text}</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
export default function AssignmentRepresentation() {
  const [session, setSession] = useState(null);
  const [assignmentText, setAssignmentText] = useState("");
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [booting, setBooting] = useState(true);
  const [editing, setEditing] = useState(false);
  const [restartOpen, setRestartOpen] = useState(false);
  const [knowledge, setKnowledge] = useState(false);
  const prevStatus = useRef({});
  const [flashIds, setFlashIds] = useState(new Set());
  const [devMode, setDevMode] = useState(
    () =>
      localStorage.getItem("compass_dev_mode") === "1" ||
      new URLSearchParams(window.location.search).has("dev")
  );
  const [savingNotes, setSavingNotes] = useState(false);
  const [libraryOpen, setLibraryOpen] = useState(false);

  // Question-Loop -> Writing bridge
  const [handoff, setHandoff] = useState(null);   // {ready, clarifying_question, handoff, writing_session_id}
  const [beginOpen, setBeginOpen] = useState(false);
  const [beginBusy, setBeginBusy] = useState(false);
  const [chosenGoal, setChosenGoal] = useState("");   // learner-selected component label (optional)
  const [editedRep, setEditedRep] = useState("");     // learner-edited task representation

  // Knowledge Loop (Stage-1 Orientation extension)
  const [knowledgeOpen, setKnowledgeOpen] = useState(false);
  const [knowledgeState, setKnowledgeState] = useState(null);
  const [klInput, setKlInput] = useState("");
  const [klBusy, setKlBusy] = useState(false);

  // Refresh handoff readiness whenever the representation changes (post-analysis).
  useEffect(() => {
    if (!session?.id || session.stage === "interpret") { setHandoff(null); return; }
    let cancelled = false;
    getHandoff(session.id)
      .then((h) => { if (!cancelled) setHandoff(h); })
      .catch(() => { if (!cancelled) setHandoff(null); });
    return () => { cancelled = true; };
  }, [session?.id, session?.stage, session?.interactions?.length]);

  const openBeginSummary = () => {
    const rep = handoff?.handoff?.current_task_representation?.value || session?.student_interpretation || "";
    setEditedRep(rep);
    setChosenGoal("");
    setBeginOpen(true);
  };

  const openBegin = async () => {
    if (!session) return;
    setBeginBusy(true);
    try {
      // Stage-1 gate: does the learner need to build conceptual understanding first?
      const ks = await assessKnowledge(session.id);
      if (ks.status === "active") {
        setKnowledgeState(ks);
        setKlInput("");
        setKnowledgeOpen(true);
        return;
      }
    } catch (e) {
      // fail open — proceed to the writing summary
    } finally {
      setBeginBusy(false);
    }
    openBeginSummary();
  };

  const submitKnowledge = async () => {
    if (!session || !klInput.trim()) return;
    setKlBusy(true);
    try {
      const ks = await knowledgeRespond(session.id, klInput.trim());
      setKnowledgeState(ks);
      setKlInput("");
    } catch (e) {
      toast.error("Something went wrong. Try again.");
    } finally {
      setKlBusy(false);
    }
  };

  const skipKnowledge = async () => {
    if (!session) return;
    setKlBusy(true);
    try {
      await knowledgeSkip(session.id);
      setKnowledgeOpen(false);
      openBeginSummary();
    } finally {
      setKlBusy(false);
    }
  };

  const proceedFromKnowledge = () => {
    setKnowledgeOpen(false);
    openBeginSummary();
  };

  const confirmBegin = async () => {
    if (!session) return;
    setBeginBusy(true);
    try {
      const res = await beginWorkingFromRepresentation({
        assignment_session_id: session.id,
        task_representation: editedRep,
        learner_selected_goal: chosenGoal || "",
      });
      if (res.ready === false) {
        toast.message("Let's clarify one thing first", { description: res.clarifying_question });
        setBeginOpen(false);
        return;
      }
      localStorage.setItem("dws_session_id", res.session_id);
      window.location.href = "?app";
    } catch (e) {
      toast.error("Could not open the writing workspace. Please try again.");
    } finally {
      setBeginBusy(false);
    }
  };

  const loadSessionById = useCallback((id) => {
    localStorage.setItem(STORE, id);
    prevStatus.current = {};
    return getAssignmentSession(id).then((s) => {
      (s.demands || []).forEach((d) => (prevStatus.current[d.id] = d.status));
      setSession(s);
      setKnowledge(false);
      setLibraryOpen(false);
    });
  }, []);

  // Hidden Developer Mode toggle — Ctrl/Cmd + Shift + D. Never exposed to students.
  useEffect(() => {
    const onKey = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === "D" || e.key === "d")) {
        e.preventDefault();
        setDevMode((v) => {
          localStorage.setItem("compass_dev_mode", v ? "0" : "1");
          return !v;
        });
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const saveNotes = useCallback(
    async (patch) => {
      if (!session) return;
      setSavingNotes(true);
      try {
        const s = await setDeveloperMeta(session.id, patch);
        setSession((prev) => ({
          ...prev,
          developer_notes: s.developer_notes,
          developer_summary: s.developer_summary,
          sprint_recommendation: s.sprint_recommendation,
        }));
        toast.success("Saved.");
      } catch (e) {
        toast.error("Could not save developer notes.");
      } finally {
        setSavingNotes(false);
      }
    },
    [session]
  );

  // apply a session update and flash any demands whose status changed
  const applySession = useCallback((s) => {
    const changed = new Set();
    (s.demands || []).forEach((d) => {
      if (prevStatus.current[d.id] && prevStatus.current[d.id] !== d.status) changed.add(d.id);
      prevStatus.current[d.id] = d.status;
    });
    setSession(s);
    setInput("");
    if (changed.size) {
      setFlashIds(changed);
      setTimeout(() => setFlashIds(new Set()), 1400);
    }
  }, []);

  useEffect(() => {
    const id = localStorage.getItem(STORE);
    if (!id) {
      setBooting(false);
      return;
    }
    getAssignmentSession(id)
      .then((s) => {
        (s.demands || []).forEach((d) => (prevStatus.current[d.id] = d.status));
        setSession(s);
      })
      .catch(() => localStorage.removeItem(STORE))
      .finally(() => setBooting(false));
  }, []);

  const runAnalyze = async () => {
    const text = assignmentText.trim();
    if (!text || busy) return;
    setBusy(true);
    try {
      let s;
      if (editing && session) {
        s = await editAssignment(session.id, text);
        toast.success("Assignment updated — analysis restarted.");
      } else {
        s = await createAssignmentSession(text);
      }
      localStorage.setItem(STORE, s.id);
      prevStatus.current = {};
      (s.demands || []).forEach((d) => (prevStatus.current[d.id] = d.status));
      setSession(s);
      setEditing(false);
      setKnowledge(false);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Could not analyze the assignment.");
    } finally {
      setBusy(false);
    }
  };

  const send = async (fn) => {
    const text = input.trim();
    if (!text || busy) return;
    setBusy(true);
    try {
      const s = await fn(session.id, text);
      applySession(s);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Something went wrong. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  const startEdit = () => {
    setAssignmentText(session.assignment_text);
    setRestartOpen(true);
  };
  const confirmEdit = () => {
    setEditing(true);
    setRestartOpen(false);
    setSession(null);
  };

  const Thinking = () => (
    <div data-testid="thinking-state" className="flex items-center gap-2 text-sm text-stone-500">
      <Loader2 className="h-4 w-4 animate-spin text-[#8C3A2A]" /> Thinking…
    </div>
  );

  if (booting) {
    return (
      <div className="flex min-h-screen items-center justify-center paper-grain">
        <p className="font-serif-display text-2xl text-stone-400">Opening Compass…</p>
      </div>
    );
  }

  // ============ Developer-only: Development Session Library ============
  if (devMode && libraryOpen) {
    return <LibraryView onOpen={loadSessionById} onClose={() => setLibraryOpen(false)} />;
  }

  // ============ Knowledge placeholder (Sprint 2 stub) ============
  if (knowledge) {
    return (
      <div className="min-h-screen paper-grain">
        <Header />
        <div className="mx-auto max-w-2xl px-6 py-24 text-center">
          <p className="font-mono-panel text-[11px] uppercase tracking-[0.2em] text-stone-400">
            Next
          </p>
          <h1 className="mt-3 font-serif-display text-4xl text-stone-900">The Knowledge Loop</h1>
          <p className="mx-auto mt-4 max-w-md text-stone-600">
            You've built an adequate representation of what this assignment asks. Gathering and
            organizing what you know comes next — that part of Compass is still being built.
          </p>
          <button
            onClick={() => setKnowledge(false)}
            data-testid="knowledge-back-button"
            className="mt-8 inline-flex items-center gap-2 text-sm text-stone-500 underline underline-offset-4 hover:text-[#8C3A2A]"
          >
            <ArrowLeft className="h-4 w-4" /> Back to the assignment
          </button>
        </div>
      </div>
    );
  }

  // ============ A. Assignment Entry ============
  if (!session) {
    return (
      <div className="min-h-screen paper-grain">
        <Toaster position="top-center" richColors />
        <Header />
        <div className="mx-auto max-w-2xl px-6 py-16">
          <p className="font-mono-panel text-[11px] uppercase tracking-[0.2em] text-[#8C3A2A]">
            {editing ? "Edit assignment" : "Start here"}
          </p>
          <h1 className="mt-3 font-serif-display text-4xl text-stone-900 sm:text-5xl">
            What does this assignment ask of you?
          </h1>
          <p className="mt-4 text-stone-600">
            Paste the assignment. Before gathering ideas or writing, Compass helps you understand
            exactly what it requires.
          </p>
          <textarea
            data-testid="assignment-input"
            value={assignmentText}
            onChange={(e) => setAssignmentText(e.target.value)}
            rows={6}
            placeholder="Paste the full assignment here…"
            className="mt-6 w-full resize-none rounded-sm border border-stone-300 bg-white p-4 font-serif-display text-[17px] leading-relaxed text-stone-900 outline-none focus:border-[#8C3A2A]"
          />
          <div className="mt-4 flex flex-wrap items-center gap-4">
            <button
              onClick={runAnalyze}
              disabled={!assignmentText.trim() || busy}
              data-testid="analyze-assignment-button"
              className="group inline-flex items-center gap-2 rounded-sm bg-[#8C3A2A] px-6 py-3 font-medium tracking-wide text-white transition-colors hover:bg-[#6B2C20] disabled:opacity-40"
            >
              {busy ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" /> Analyzing…
                </>
              ) : (
                <>
                  Analyze assignment
                  <ArrowRight className="h-4 w-4 transition-transform group-enabled:group-hover:translate-x-0.5" />
                </>
              )}
            </button>
            <button
              onClick={() => setAssignmentText(SAMPLE)}
              data-testid="sample-assignment-button"
              className="text-[11px] font-mono-panel uppercase tracking-[0.14em] text-stone-400 transition-colors hover:text-[#8C3A2A]"
            >
              Use sample assignment
            </button>
            {editing && (
              <button
                onClick={() => {
                  setEditing(false);
                  const id = localStorage.getItem(STORE);
                  if (id) getAssignmentSession(id).then(setSession);
                }}
                className="text-[11px] font-mono-panel uppercase tracking-[0.14em] text-stone-400 hover:text-stone-700"
              >
                Cancel
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  // ============ B. Student Interpretation ============
  if (session.stage === "interpret") {
    return (
      <div className="min-h-screen paper-grain">
        <Toaster position="top-center" richColors />
        <Header />
        <div className="mx-auto max-w-2xl px-6 py-12">
          <AssignmentPanel text={session.assignment_text} onEdit={startEdit} />
          <div className="mt-8">
            <p className="font-mono-panel text-[11px] uppercase tracking-[0.2em] text-[#8C3A2A]">
              In your own words
            </p>
            <h2 className="mt-2 font-serif-display text-2xl text-stone-900">
              What is this assignment asking you to do?
            </h2>
            <p className="mt-2 text-sm text-stone-600">
              Don't answer the assignment yet. Just explain what it requires, as you understand it.
            </p>
            <textarea
              data-testid="interpretation-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              rows={5}
              placeholder="Explain what the assignment is asking…"
              className="mt-4 w-full resize-none rounded-sm border border-stone-300 bg-white p-4 text-[15px] leading-relaxed text-stone-900 outline-none focus:border-[#8C3A2A]"
            />
            <div className="mt-4 flex items-center gap-4">
              <button
                onClick={() => send(submitInterpretation)}
                disabled={!input.trim() || busy}
                data-testid="compare-understanding-button"
                className="inline-flex items-center gap-2 rounded-sm bg-[#8C3A2A] px-6 py-3 font-medium text-white transition-colors hover:bg-[#6B2C20] disabled:opacity-40"
              >
                {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                Compare my understanding
              </button>
              {busy && <Thinking />}
            </div>
          </div>
        </div>
        {devMode && (
          <DeveloperPanel session={session} onSaveNotes={saveNotes} savingNotes={savingNotes} onOpenLibrary={() => setLibraryOpen(true)} />
        )}
        <RestartDialog open={restartOpen} setOpen={setRestartOpen} confirm={confirmEdit} />
      </div>
    );
  }

  // ============ C + D + E : two-column working view ============
  const scaffold = session.current_scaffold;
  return (
    <div className="min-h-screen paper-grain">
      <Toaster position="top-center" richColors />
      <Header />
      <div className="mx-auto grid max-w-6xl grid-cols-1 gap-8 px-6 py-10 lg:grid-cols-2">
        {/* LEFT — assignment + persistent Question Map */}
        <div className="space-y-6">
          <AssignmentPanel text={session.assignment_text} onEdit={startEdit} />
          <QuestionMap session={session} flashIds={flashIds} />
          {handoff?.ready && session.stage !== "adequate" && (
            <div
              data-testid="handoff-bar"
              className="flex items-center justify-between gap-3 rounded-sm border border-[#8C3A2A]/30 bg-[#f7efe9] px-4 py-3"
            >
              <p className="text-[13px] leading-snug text-stone-700">
                You have enough to start. You can begin working on one part now and keep clarifying as you go.
              </p>
              <button
                onClick={openBegin}
                data-testid="begin-working-bar-button"
                className="group inline-flex shrink-0 items-center gap-1.5 rounded-sm bg-[#8C3A2A] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[#6B2C20]"
              >
                Begin working on this
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
              </button>
            </div>
          )}
        </div>

        {/* RIGHT — active developmental work */}
        <div className="lg:sticky lg:top-6 lg:self-start">
          {session.stage === "mapping" && scaffold && (
            <div data-testid="scaffold-panel" className="rounded-sm border border-stone-200 bg-white p-6">
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-sm bg-[#8C3A2A] px-2 py-1 text-[10px] font-mono-panel uppercase tracking-[0.14em] text-white">
                  {scaffold.targetOperation || "Perform"}
                </span>
                {(scaffold.concepts || []).map((c) => (
                  <span
                    key={c}
                    className="rounded-sm border border-stone-200 px-2 py-1 text-[10px] font-mono-panel uppercase tracking-[0.1em] text-stone-500"
                  >
                    {c}
                  </span>
                ))}
              </div>
              {scaffold.relevant_wording && (
                <p className="mt-4 border-l-2 border-stone-300 pl-3 font-serif-display text-[15px] italic text-stone-600">
                  “{scaffold.relevant_wording}”
                </p>
              )}
              <p
                data-testid="scaffold-task"
                className="mt-4 whitespace-pre-wrap text-[16px] leading-relaxed text-stone-900"
              >
                {scaffold.studentTask}
              </p>
              {scaffold.requires_reconstruction && (
                <p className="mt-3 inline-flex items-center gap-1.5 text-[11px] font-mono-panel uppercase tracking-[0.12em] text-[#8C3A2A]">
                  <CornerDownRight className="h-3.5 w-3.5" /> Put this in your own words
                </p>
              )}
              <textarea
                data-testid="operation-input"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                rows={5}
                placeholder="Write your response…"
                className="mt-4 w-full resize-none rounded-sm border border-stone-300 bg-[#faf9f6] p-3.5 text-[15px] leading-relaxed text-stone-900 outline-none focus:border-[#8C3A2A]"
              />
              <div className="mt-3 flex items-center gap-4">
                <button
                  onClick={() => send(submitOperation)}
                  disabled={!input.trim() || busy}
                  data-testid="submit-operation-button"
                  className="inline-flex items-center gap-2 rounded-sm bg-[#8C3A2A] px-5 py-2.5 font-medium text-white transition-colors hover:bg-[#6B2C20] disabled:opacity-40"
                >
                  {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                  Submit response
                </button>
                {busy && <Thinking />}
              </div>
            </div>
          )}

          {session.stage === "restatement" && (
            <div data-testid="restatement-panel" className="rounded-sm border border-stone-200 bg-white p-6">
              <p className="font-mono-panel text-[11px] uppercase tracking-[0.2em] text-[#8C3A2A]">
                Pull it together
              </p>
              <h2 className="mt-2 font-serif-display text-2xl text-stone-900">
                Explain the whole assignment again, in your own words.
              </h2>
              <p className="mt-2 text-sm text-stone-600">
                Now that you've worked through the parts, restate what this assignment requires — all
                of it.
              </p>
              <textarea
                data-testid="restatement-input"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                rows={6}
                placeholder="Restate the full assignment…"
                className="mt-4 w-full resize-none rounded-sm border border-stone-300 bg-[#faf9f6] p-3.5 text-[15px] leading-relaxed text-stone-900 outline-none focus:border-[#8C3A2A]"
              />
              <div className="mt-3 flex items-center gap-4">
                <button
                  onClick={() => send(submitRestatement)}
                  disabled={!input.trim() || busy}
                  data-testid="submit-restatement-button"
                  className="inline-flex items-center gap-2 rounded-sm bg-[#8C3A2A] px-5 py-2.5 font-medium text-white transition-colors hover:bg-[#6B2C20] disabled:opacity-40"
                >
                  {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                  Check my representation
                </button>
                {busy && <Thinking />}
              </div>
            </div>
          )}

          {session.stage === "adequate" && (
            <div data-testid="adequate-panel" className="rounded-sm border border-[#5b7a52]/40 bg-[#eef2ea] p-6">
              <p className="font-mono-panel text-[11px] uppercase tracking-[0.2em] text-[#41603a]">
                Adequate for now
              </p>
              <h2 className="mt-2 font-serif-display text-2xl text-stone-900">
                You understand what this assignment requires.
              </h2>
              <p className="mt-2 text-sm text-stone-600">
                Your representation is solid enough to move forward. You can keep refining it later.
              </p>
              <div className="mt-6 flex flex-wrap items-center gap-4">
                <button
                  onClick={openBegin}
                  data-testid="begin-working-button"
                  className="group inline-flex items-center gap-2 rounded-sm bg-[#8C3A2A] px-6 py-3 font-medium text-white transition-colors hover:bg-[#6B2C20]"
                >
                  Begin working on this
                  <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
                </button>
                <button
                  onClick={() => setKnowledge(true)}
                  data-testid="continue-to-knowledge-button"
                  className="text-[11px] font-mono-panel uppercase tracking-[0.14em] text-stone-400 transition-colors hover:text-[#8C3A2A]"
                >
                  Continue to Knowledge (coming soon)
                </button>
              </div>
            </div>
          )}

          {/* Preserved learner responses */}
          {session.interactions?.length > 0 && (
            <div data-testid="response-history" className="mt-6">
              <p className="mb-2 font-mono-panel text-[10px] uppercase tracking-[0.2em] text-stone-400">
                Your responses
              </p>
              <div className="space-y-2">
                {session.interactions
                  .filter((i) => i.student_text)
                  .map((i, idx) => (
                    <div
                      key={i.id || idx}
                      data-testid={`response-history-item-${idx}`}
                      className="rounded-sm border border-stone-200 bg-white px-3 py-2"
                    >
                      <p className="font-mono-panel text-[9px] uppercase tracking-[0.16em] text-stone-400">
                        {i.kind}
                      </p>
                      <p className="mt-0.5 text-[13px] leading-snug text-stone-600 line-clamp-3">
                        {i.student_text}
                      </p>
                    </div>
                  ))}
              </div>
            </div>
          )}
        </div>
      </div>
      {devMode && (
        <DeveloperPanel session={session} onSaveNotes={saveNotes} savingNotes={savingNotes} onOpenLibrary={() => setLibraryOpen(true)} />
      )}
      <BeginWorkingModal
        open={beginOpen}
        onClose={() => setBeginOpen(false)}
        handoff={handoff?.handoff}
        editedRep={editedRep}
        setEditedRep={setEditedRep}
        chosenGoal={chosenGoal}
        setChosenGoal={setChosenGoal}
        busy={beginBusy}
        onConfirm={confirmBegin}
      />
      <KnowledgeLoopModal
        open={knowledgeOpen}
        onClose={() => setKnowledgeOpen(false)}
        knowledge={knowledgeState}
        input={klInput}
        setInput={setKlInput}
        busy={klBusy}
        onRespond={submitKnowledge}
        onSkip={skipKnowledge}
        onProceed={proceedFromKnowledge}
      />
      <RestartDialog open={restartOpen} setOpen={setRestartOpen} confirm={confirmEdit} />
    </div>
  );
}

// Editable summary of Compass's current understanding, shown before crossing into
// the writing workspace (spec §6). No engine names, no milestone numbers surfaced.
function BeginWorkingModal({ open, onClose, handoff, editedRep, setEditedRep, chosenGoal, setChosenGoal, busy, onConfirm }) {
  if (!open || !handoff) return null;
  const reqs = handoff.task_requirements || [];
  const unresolved = handoff.unresolved_questions || [];
  const purpose = handoff.inferred_communicative_purpose || {};
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" data-testid="begin-working-modal">
      <div className="max-h-[86vh] w-full max-w-lg overflow-y-auto rounded-sm border border-stone-200 bg-[#faf9f6] p-6 shadow-xl">
        <div className="flex items-start justify-between">
          <div>
            <p className="font-mono-panel text-[10px] uppercase tracking-[0.2em] text-stone-400">Before you begin</p>
            <h3 className="mt-1 font-serif-display text-xl text-stone-900">Here's how I understand this task</h3>
          </div>
          <button onClick={onClose} data-testid="begin-modal-close" className="text-stone-400 hover:text-stone-700">
            <X className="h-5 w-5" />
          </button>
        </div>

        <label className="mt-5 block font-mono-panel text-[10px] uppercase tracking-[0.16em] text-stone-500">
          What you're being asked to do (edit if this isn't right)
        </label>
        <textarea
          data-testid="begin-modal-representation"
          value={editedRep}
          onChange={(e) => setEditedRep(e.target.value)}
          rows={3}
          className="mt-2 w-full resize-none rounded-sm border border-stone-300 bg-white p-3 text-[14px] leading-relaxed text-stone-900 outline-none focus:border-[#8C3A2A]"
        />

        {purpose.value && (
          <p className="mt-3 text-[13px] text-stone-600">
            <span className="font-medium text-stone-800">Likely purpose:</span> {purpose.value}
            <span className="ml-1 text-stone-400">(my read — tell me if it's off)</span>
          </p>
        )}

        {reqs.length > 0 && (
          <>
            <label className="mt-5 block font-mono-panel text-[10px] uppercase tracking-[0.16em] text-stone-500">
              Where would you like to start? (optional — I'll otherwise pick the most useful part)
            </label>
            <div className="mt-2 space-y-1.5">
              <button
                onClick={() => setChosenGoal("")}
                data-testid="begin-goal-auto"
                className={`w-full rounded-sm border px-3 py-2 text-left text-[13px] transition-colors ${chosenGoal === "" ? "border-[#8C3A2A] bg-[#f7efe9] text-stone-900" : "border-stone-200 bg-white text-stone-600 hover:border-stone-300"}`}
              >
                Let Compass choose the best starting point
              </button>
              {reqs.map((r, i) => (
                <button
                  key={r.demand_id || i}
                  onClick={() => setChosenGoal(r.label)}
                  data-testid={`begin-goal-${i}`}
                  className={`w-full rounded-sm border px-3 py-2 text-left text-[13px] transition-colors ${chosenGoal === r.label ? "border-[#8C3A2A] bg-[#f7efe9] text-stone-900" : "border-stone-200 bg-white text-stone-600 hover:border-stone-300"}`}
                >
                  {r.label}
                </button>
              ))}
            </div>
          </>
        )}

        {unresolved.length > 0 && (
          <div className="mt-5 rounded-sm border border-stone-200 bg-white px-3 py-2.5">
            <p className="font-mono-panel text-[9px] uppercase tracking-[0.16em] text-stone-400">Open questions (we can settle these while working)</p>
            <ul className="mt-1 list-disc pl-4 text-[12px] leading-snug text-stone-600">
              {unresolved.map((q, i) => <li key={i}>{q.value}</li>)}
            </ul>
          </div>
        )}

        <div className="mt-6 flex items-center justify-end gap-4">
          <button onClick={onClose} data-testid="begin-modal-keep-clarifying" className="text-sm text-stone-500 hover:text-stone-800">
            Keep clarifying
          </button>
          <button
            onClick={onConfirm}
            disabled={busy}
            data-testid="begin-modal-confirm"
            className="inline-flex items-center gap-2 rounded-sm bg-[#8C3A2A] px-5 py-2.5 font-medium text-white transition-colors hover:bg-[#6B2C20] disabled:opacity-50"
          >
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            Start working
          </button>
        </div>
      </div>
    </div>
  );
}

// Knowledge Loop — a brief, boundary-safe conceptual-readiness dialogue that runs ONLY
// when understanding is the limiting factor, then returns the learner to writing.
function KnowledgeLoopModal({ open, onClose, knowledge, input, setInput, busy, onRespond, onSkip, onProceed }) {
  if (!open || !knowledge) return null;
  const ready = knowledge.status === "ready";
  const turns = knowledge.turns || [];
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" data-testid="knowledge-loop-modal">
      <div className="flex max-h-[86vh] w-full max-w-lg flex-col rounded-sm border border-stone-200 bg-[#faf9f6] shadow-xl">
        <div className="flex items-start justify-between border-b border-stone-200 p-6 pb-4">
          <div>
            <p className="font-mono-panel text-[10px] uppercase tracking-[0.2em] text-stone-400">Before you write</p>
            <h3 className="mt-1 font-serif-display text-xl text-stone-900">
              {ready ? "You're ready — let's use this" : "Let's make sure one idea is clear"}
            </h3>
          </div>
          <button onClick={onClose} data-testid="knowledge-close" className="text-stone-400 hover:text-stone-700">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="flex-1 space-y-3 overflow-y-auto px-6 py-4" data-testid="knowledge-dialogue">
          {turns.map((t, i) => (
            <div
              key={i}
              data-testid={`knowledge-turn-${t.role}-${i}`}
              className={t.role === "coach"
                ? "rounded-sm border-l-2 border-[#8C3A2A] bg-white px-3 py-2.5"
                : "ml-6 rounded-sm border border-stone-200 bg-[#f2efe9] px-3 py-2.5"}
            >
              <p className="font-mono-panel text-[9px] uppercase tracking-[0.16em] text-stone-400">
                {t.role === "coach" ? "Compass" : "You"}
              </p>
              <p className="mt-0.5 whitespace-pre-wrap text-[14px] leading-relaxed text-stone-800">{t.text}</p>
            </div>
          ))}
        </div>

        <div className="border-t border-stone-200 p-6 pt-4">
          {ready ? (
            <button
              onClick={onProceed}
              data-testid="knowledge-proceed-button"
              className="group inline-flex w-full items-center justify-center gap-2 rounded-sm bg-[#8C3A2A] px-5 py-3 font-medium text-white transition-colors hover:bg-[#6B2C20]"
            >
              Now let's use this in your draft
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
            </button>
          ) : (
            <>
              <textarea
                data-testid="knowledge-input"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                rows={3}
                placeholder="Answer in your own words…"
                className="w-full resize-none rounded-sm border border-stone-300 bg-white p-3 text-[15px] leading-relaxed text-stone-900 outline-none focus:border-[#8C3A2A]"
              />
              <div className="mt-3 flex items-center justify-between gap-4">
                <button
                  onClick={onSkip}
                  disabled={busy}
                  data-testid="knowledge-skip-button"
                  className="text-sm text-stone-500 hover:text-stone-800 disabled:opacity-50"
                >
                  I'm ready to write
                </button>
                <button
                  onClick={onRespond}
                  disabled={busy || !input.trim()}
                  data-testid="knowledge-respond-button"
                  className="inline-flex items-center gap-2 rounded-sm bg-[#8C3A2A] px-5 py-2.5 font-medium text-white transition-colors hover:bg-[#6B2C20] disabled:opacity-40"
                >
                  {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                  Respond
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}


function DeveloperPanel({ session, onSaveNotes, savingNotes, onOpenLibrary }) {
  const [open, setOpen] = useState(true);
  const [notes, setNotes] = useState(session.developer_notes || "");
  const [summary, setSummary] = useState(session.developer_summary || "");
  const [rec, setRec] = useState(session.sprint_recommendation || "");
  useEffect(() => {
    setNotes(session.developer_notes || "");
    setSummary(session.developer_summary || "");
    setRec(session.sprint_recommendation || "");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session.id]);
  const s = session.current_scaffold || {};
  const cd = session.control_decision || {};
  const target = session.demands.find((d) => d.id === session.active_target_id);
  const Row = ({ k, v }) =>
    v ? (
      <div className="grid grid-cols-[130px_1fr] gap-2 py-0.5">
        <span className="font-mono-panel text-[9px] uppercase tracking-[0.14em] text-stone-500">{k}</span>
        <span className="text-[12px] leading-snug text-stone-100">{v}</span>
      </div>
    ) : null;

  return (
    <div
      data-testid="developer-panel"
      className="fixed bottom-4 right-4 z-50 w-[390px] max-h-[86vh] overflow-auto rounded-sm border border-stone-700 bg-stone-900 text-stone-100 shadow-xl"
    >
      <div className="flex items-center justify-between border-b border-stone-700 px-3 py-2">
        <button
          onClick={() => setOpen((v) => !v)}
          data-testid="developer-panel-toggle"
          className="flex items-center gap-1.5 font-mono-panel text-[10px] uppercase tracking-[0.2em] text-amber-400"
        >
          <Code2 className="h-3.5 w-3.5" /> Developer Mode
        </button>
        <div className="flex items-center gap-3">
          <button
            onClick={onOpenLibrary}
            data-testid="open-library-button"
            className="inline-flex items-center gap-1 font-mono-panel text-[9px] uppercase tracking-[0.14em] text-stone-300 hover:text-amber-400"
          >
            <BookOpen className="h-3.5 w-3.5" /> Library
          </button>
          <button onClick={() => setOpen((v) => !v)}>
            <ChevronDown className={`h-4 w-4 text-stone-400 transition-transform ${open ? "" : "-rotate-90"}`} />
          </button>
        </div>
      </div>
      {open && (
        <div className="px-3 py-3">
          <p className="mb-1 font-mono-panel text-[9px] uppercase tracking-[0.16em] text-stone-500">
            Control Engine
          </p>
          <Row k="Current Loop" v="Question Loop" />
          <Row k="Stage" v={session.stage} />
          <Row k="Dev. Operation" v={s.targetOperation} />
          <Row k="Target Demand" v={target ? target.label : "—"} />
          <Row k="Demand Category" v={target ? target.category : (cd.demand_category || "")} />
          <Row k="Demand Priority" v={target ? target.priority : (cd.demand_priority || "")} />
          <Row k="Scaffold Level" v={s.level != null ? String(s.level) : "—"} />
          <Row k="Instruction Type" v={s.instructionType} />
          <Row k="Concepts" v={(s.concepts || []).join(", ")} />
          <Row k="Decision" v={cd.action} />
          <Row k="Reason for Decision" v={cd.reason || session.active_target_reason} />
          <Row k="Why Not Alternatives" v={cd.alternatives_reason} />
          <Row k="Expected Evidence" v={s.expectedEvidence} />
          <Row k="Next if Successful" v={cd.next_if_successful || s.nextIfSuccessful} />
          <Row k="Next if Unsuccessful" v={cd.next_if_unsuccessful || s.nextIfUnsuccessful} />
          <Row k="Requires Reconstr." v={s.requires_reconstruction ? "yes" : ""} />

          <div className="mt-3 border-t border-stone-700 pt-3">
            <p className="mb-1 font-mono-panel text-[9px] uppercase tracking-[0.14em] text-amber-400">
              Developer Summary (required)
            </p>
            <textarea
              data-testid="developer-summary-input"
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
              rows={3}
              placeholder="2–4 sentences: the major lesson from this session…"
              className="w-full resize-none rounded-sm border border-stone-700 bg-stone-800 p-2 text-[12px] text-stone-100 outline-none placeholder:text-stone-500 focus:border-amber-500"
            />

            <p className="mb-1 mt-3 font-mono-panel text-[9px] uppercase tracking-[0.14em] text-stone-500">
              Sprint Recommendation
            </p>
            <select
              data-testid="sprint-recommendation-select"
              value={rec}
              onChange={(e) => setRec(e.target.value)}
              className="w-full rounded-sm border border-stone-700 bg-stone-800 p-2 text-[12px] text-stone-100 outline-none focus:border-amber-500"
            >
              <option value="">— choose —</option>
              {SPRINT_RECOMMENDATIONS.map((o) => (
                <option key={o} value={o}>
                  {o}
                </option>
              ))}
            </select>

            <p className="mb-1 mt-3 font-mono-panel text-[9px] uppercase tracking-[0.14em] text-stone-500">
              Developer Notes (private)
            </p>
            <textarea
              data-testid="developer-notes-input"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
              placeholder="Observations (e.g. 'AI identified the wrong target', 'over-scaffolded')…"
              className="w-full resize-none rounded-sm border border-stone-700 bg-stone-800 p-2 text-[12px] text-stone-100 outline-none placeholder:text-stone-500 focus:border-amber-500"
            />
            <div className="mt-2 flex items-center justify-between">
              <button
                onClick={() =>
                  onSaveNotes({
                    developer_notes: notes,
                    developer_summary: summary,
                    sprint_recommendation: rec,
                  })
                }
                disabled={savingNotes}
                data-testid="developer-notes-save"
                className="rounded-sm bg-amber-500 px-3 py-1.5 text-[11px] font-medium text-stone-900 hover:bg-amber-400 disabled:opacity-50"
              >
                {savingNotes ? "Saving…" : "Save"}
              </button>
              <div className="flex items-center gap-3">
                <a
                  href={assignmentRecordUrl(session.id, "json")}
                  target="_blank"
                  rel="noreferrer"
                  data-testid="download-record-json"
                  className="inline-flex items-center gap-1 text-[10px] font-mono-panel uppercase tracking-[0.12em] text-stone-300 hover:text-amber-400"
                >
                  <Download className="h-3 w-3" /> JSON
                </a>
                <a
                  href={assignmentRecordUrl(session.id, "markdown")}
                  target="_blank"
                  rel="noreferrer"
                  data-testid="download-record-md"
                  className="inline-flex items-center gap-1 text-[10px] font-mono-panel uppercase tracking-[0.12em] text-stone-300 hover:text-amber-400"
                >
                  <Download className="h-3 w-3" /> MD
                </a>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function LibraryView({ onOpen, onClose }) {
  const [rows, setRows] = useState(null);
  useEffect(() => {
    getSessionLibrary()
      .then(setRows)
      .catch(() => setRows([]));
  }, []);
  const mins = (secs) => (secs == null ? "—" : `${Math.max(1, Math.round(secs / 60))} min`);
  const fmtDate = (iso) => {
    try {
      return new Date(iso).toLocaleDateString(undefined, { month: "long", day: "numeric", year: "numeric" });
    } catch {
      return "";
    }
  };

  return (
    <div className="min-h-screen bg-stone-950 text-stone-100" data-testid="library-view">
      <header className="flex items-center justify-between border-b border-stone-800 px-6 py-4">
        <span className="flex items-center gap-2 font-serif-display text-lg text-stone-100">
          <BookOpen className="h-5 w-5 text-amber-400" /> Development Session Library
        </span>
        <button
          onClick={onClose}
          data-testid="library-close-button"
          className="inline-flex items-center gap-1.5 rounded-sm border border-stone-700 px-3 py-1.5 text-[11px] font-mono-panel uppercase tracking-[0.14em] text-stone-300 hover:text-amber-400"
        >
          <X className="h-3.5 w-3.5" /> Close
        </button>
      </header>
      <div className="mx-auto max-w-3xl px-6 py-8">
        {rows === null && <p className="text-stone-400">Loading sessions…</p>}
        {rows && rows.length === 0 && (
          <p className="text-stone-400">No Development Sessions yet.</p>
        )}
        <div className="space-y-3">
          {rows?.map((r) => (
            <div
              key={r.id}
              data-testid={`library-row-${r.id}`}
              className="flex items-start justify-between gap-4 rounded-sm border border-stone-800 bg-stone-900 p-4"
            >
              <div className="min-w-0">
                <p className="font-mono-panel text-[10px] uppercase tracking-[0.16em] text-stone-500">
                  {fmtDate(r.created_at)}
                  {(r.educational_level || r.subject) &&
                    ` · ${[r.educational_level, r.subject].filter(Boolean).join(" ")}`}
                </p>
                <p className="mt-1 font-serif-display text-lg text-stone-100">
                  {r.title || r.assignment_first_line}
                </p>
                <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-[12px] text-stone-400">
                  <span className="inline-flex items-center gap-1">
                    <Clock className="h-3 w-3" /> {mins(r.session_length_seconds)}
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <Layers className="h-3 w-3" /> {r.num_scaffold_attempts} scaffolds
                  </span>
                  <span>{r.num_level3_interventions} Level-3</span>
                  {r.has_developer_notes && <span className="text-amber-400">Notes ✓</span>}
                  {r.has_developer_summary && <span className="text-amber-400">Summary ✓</span>}
                  {r.sprint_recommendation && (
                    <span className="rounded-sm border border-stone-700 px-1.5 py-px text-[10px] uppercase tracking-[0.1em] text-stone-300">
                      {r.sprint_recommendation}
                    </span>
                  )}
                </div>
              </div>
              <button
                onClick={() => onOpen(r.id)}
                data-testid={`library-open-${r.id}`}
                className="shrink-0 rounded-sm bg-amber-500 px-4 py-2 text-[11px] font-medium text-stone-900 hover:bg-amber-400"
              >
                Open
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function Header() {
  return (
    <header className="flex items-center justify-between border-b border-stone-200 bg-[#faf9f6]/90 px-6 py-4 backdrop-blur-sm sm:px-10">
      <a
        href="/"
        className="flex items-center gap-2 font-serif-display text-lg text-stone-900"
        data-testid="rep-home-link"
      >
        <CompassIcon className="h-5 w-5 text-[#8C3A2A]" />
        Compass
      </a>
      <span className="font-mono-panel text-[10px] uppercase tracking-[0.2em] text-stone-400">
        Understand the assignment
      </span>
    </header>
  );
}

function RestartDialog({ open, setOpen, confirm }) {
  return (
    <AlertDialog open={open} onOpenChange={setOpen}>
      <AlertDialogContent data-testid="restart-warning-dialog">
        <AlertDialogHeader>
          <AlertDialogTitle>Edit the assignment and restart?</AlertDialogTitle>
          <AlertDialogDescription>
            Changing the assignment restarts the analysis. Your current Question Map and responses
            for this assignment will be cleared.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel data-testid="restart-cancel">Keep working</AlertDialogCancel>
          <AlertDialogAction
            onClick={confirm}
            data-testid="restart-confirm"
            className="bg-[#8C3A2A] hover:bg-[#6B2C20]"
          >
            Edit &amp; restart
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
