import { useState, useRef, useEffect, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  ArrowRight,
  Loader2,
  Sparkles,
  BookOpen,
  RotateCcw,
  FlaskConical,
  MessageSquareQuote,
  X,
  History,
  ChevronRight,
  CornerDownRight,
  Waypoints,
} from "lucide-react";

const draftKey = (id) => `dws_draft_${id}`;

export default function StudentWorkspace({
  session,
  onSubmit,
  loading,
  onOpenPanel,
  onNewSession,
  onNewAssignment,
}) {
  const allTurns = session.turns || [];
  const studentTurns = allTurns.filter((t) => t.role === "student");
  const completedAi = allTurns.filter(
    (t) => t.role === "ai" && t.status === "complete" && t.content
  );
  // A turn mid-stream: its invitation is rendering progressively.
  const streamingTurn = allTurns.find(
    (t) => t.role === "ai" && t.status === "streaming" && t.content
  );
  const streaming = !!streamingTurn;
  const started = studentTurns.length > 0;
  const reviseCount = studentTurns.filter((t) => t.kind === "revise").length;

  // The single active coaching target = the streaming turn, else the most recent
  // completed AI turn.
  const activeCoaching = streamingTurn
    || (completedAi.length ? completedAi[completedAi.length - 1] : null);
  // Everything earlier is resolved coaching (right-rail history), newest first.
  const resolvedCoaching = useMemo(
    () => completedAi.slice(0, Math.max(0, completedAi.length - 1)).reverse(),
    [completedAi]
  );

  const [draft, setDraft] = useState("");
  const [markerOpen, setMarkerOpen] = useState(true);
  const [openCoachingId, setOpenCoachingId] = useState(null);
  const [replyOpen, setReplyOpen] = useState(false);
  const [reply, setReply] = useState("");
  const [railOpen, setRailOpen] = useState(true);
  const canvasRef = useRef(null);

  // Initialise / restore the living draft once per session. Autosave keeps the
  // document alive across reloads; it evolves in place, never re-created.
  useEffect(() => {
    if (!session?.id) return;
    const saved = localStorage.getItem(draftKey(session.id));
    if (saved !== null && saved !== undefined) {
      setDraft(saved);
    } else {
      const lastStudent = studentTurns[studentTurns.length - 1];
      setDraft(lastStudent?.content || "");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session?.id]);

  useEffect(() => {
    if (session?.id) localStorage.setItem(draftKey(session.id), draft);
  }, [draft, session?.id]);

  // During streaming, auto-open the card so the invitation renders live.
  useEffect(() => {
    if (streamingTurn) {
      setMarkerOpen(true);
      setOpenCoachingId(streamingTurn.id);
    }
  }, [streamingTurn?.id]);

  // A newly completed coaching that did NOT stream surfaces marker-first; a
  // streamed one stays open through completion (same turn id). Exception: the
  // very FIRST invitation (e.g. right after a handoff from the Question Loop)
  // auto-opens so the learner sees it without hunting for the marker.
  useEffect(() => {
    if (activeCoaching && !streaming) {
      setMarkerOpen(true);
      const isFirstInvitation = completedAi.length === 1;
      setOpenCoachingId((prev) =>
        prev === activeCoaching.id ? prev : (isFirstInvitation ? activeCoaching.id : null));
    }
  }, [activeCoaching?.id, streaming, completedAi.length]);

  const wordCount = draft.trim() ? draft.trim().split(/\s+/).length : 0;
  const dirty = started
    ? draft.trim() !== (studentTurns[studentTurns.length - 1]?.content || "").trim()
    : draft.trim().length > 0;

  const submitDraft = () => {
    if (!draft.trim() || loading || streaming || !dirty) return;
    onSubmit(started ? "revise" : "writing", draft.trim());
    setMarkerOpen(false);
  };

  const submitExplain = () => {
    if (loading) return;
    onSubmit("explain", "Can you say a little more about what you mean here?");
  };

  const submitReply = () => {
    if (!reply.trim() || loading) return;
    onSubmit("answer", reply.trim());
    setReply("");
    setReplyOpen(false);
  };

  return (
    <div className="min-h-screen paper-grain flex flex-col">
      {/* Slim top bar — assignment + task + revision progress. Quiet, no chrome. */}
      <header className="flex items-start justify-between gap-4 px-6 sm:px-10 py-4 border-b border-stone-200 bg-[#faf9f6]/90 backdrop-blur-sm sticky top-0 z-30">
        <div className="min-w-0">
          <div className="flex items-center gap-2 font-serif-display text-lg text-stone-900">
            <BookOpen className="h-4.5 w-4.5 text-[#8C3A2A]" />
            <span className="truncate" data-testid="workspace-assignment-title">
              {session.assignment}
            </span>
          </div>
          <p className="text-xs text-stone-500 mt-0.5 truncate" data-testid="workspace-task">
            {session.current_writing_task}
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span
            data-testid="revision-progress"
            className="hidden sm:inline-flex items-center text-[10px] font-mono-panel uppercase tracking-[0.18em] text-stone-500 border border-stone-300 rounded-sm px-2.5 py-1"
          >
            {reviseCount > 0 ? `Revision ${reviseCount}` : "First draft"}
          </span>
          {onNewAssignment && (
            <button
              onClick={() => !loading && onNewAssignment()}
              disabled={loading}
              data-testid="new-assignment-button"
              className="hidden md:inline-flex items-center gap-1.5 text-[10px] font-mono-panel uppercase tracking-[0.15em] text-stone-400 hover:text-[#8C3A2A] transition-colors disabled:opacity-40"
              title="Set up a new teacher assignment"
            >
              New
            </button>
          )}
          {onNewSession && (
            <button
              onClick={() => !loading && onNewSession()}
              disabled={loading}
              data-testid="reset-to-sample-button"
              className="hidden md:inline-flex items-center gap-1 text-[10px] font-mono-panel uppercase tracking-[0.15em] text-stone-400 hover:text-[#8C3A2A] transition-colors disabled:opacity-40"
              title="Reset to the sample assignment"
            >
              <RotateCcw className="h-3 w-3" />
            </button>
          )}
          <button
            onClick={() => (window.location.href = `?meaning=${session.id}`)}
            data-testid="open-meaning-workspace-button"
            className="inline-flex items-center gap-1.5 text-[10px] font-mono-panel uppercase tracking-[0.15em] text-stone-500 hover:text-[#8C3A2A] transition-colors border border-stone-300 rounded-sm px-2.5 py-1"
            title="Open the Meaning Workspace — a visual space to think before you write"
          >
            <Waypoints className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Meaning Workspace</span>
          </button>
          <button
            onClick={onOpenPanel}
            data-testid="open-dev-panel-button"
            className="inline-flex items-center gap-1.5 text-[10px] font-mono-panel uppercase tracking-[0.15em] text-stone-400 hover:text-stone-900 transition-colors"
            title="Teacher / developer reasoning panel"
          >
            <FlaskConical className="h-3.5 w-3.5" />
          </button>
        </div>
      </header>

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12">
        {/* ============ DOCUMENT CANVAS (dominant, center) ============ */}
        <section className="lg:col-span-8 xl:col-span-9 flex flex-col items-center px-4 sm:px-10 py-10">
          <div className="w-full max-w-3xl relative">
            {session.assignment_prompt ? (
              <div
                data-testid="assignment-prompt"
                className="mb-6 border-l-2 border-[#8C3A2A] pl-4"
              >
                <p className="font-mono-panel text-[10px] uppercase tracking-[0.2em] text-[#8C3A2A]">
                  Prompt — the question you're answering
                </p>
                <p className="text-stone-800 mt-1 leading-relaxed font-serif-display text-lg">
                  {session.assignment_prompt}
                </p>
              </div>
            ) : null}

            {session.origin_representation?.suggested_initial_component ? (
              <div
                data-testid="focus-strip"
                className="mb-6 rounded-sm border border-stone-200 bg-[#f7efe9] px-4 py-3"
              >
                <p className="font-mono-panel text-[10px] uppercase tracking-[0.2em] text-stone-500">
                  Working on now
                </p>
                <p className="mt-1 text-[15px] leading-snug text-stone-800">
                  {session.origin_representation.suggested_initial_component.name}
                </p>
                {(session.origin_representation.unresolved_questions || []).length > 0 ? (
                  <p className="mt-2 text-[12px] leading-snug text-stone-500">
                    <span className="font-medium text-stone-600">Still open:</span>{" "}
                    {session.origin_representation.unresolved_questions.map((q) => q.value).join(" · ")}
                  </p>
                ) : null}
              </div>
            ) : null}

            {/* The living draft — paper surface, editable in place at all times. */}
            <div className="relative bg-white border border-stone-300 rounded-sm">
              <textarea
                ref={canvasRef}
                id="draft"
                data-testid="writing-area"
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                placeholder="Begin your draft here — write what you actually think. I won't write it for you."
                className="block w-full min-h-[52vh] bg-transparent px-8 sm:px-14 py-10 text-[18px] leading-9 text-stone-900 placeholder:text-stone-400 outline-none resize-none custom-scroll font-serif-display"
              />

              {/* Anchored coaching marker — a single calm dot on the document's
                  right margin, near the most recent writing. Only one at a time. */}
              <AnimatePresence>
                {activeCoaching && !loading && markerOpen && openCoachingId !== activeCoaching.id && (
                  <motion.button
                    key={`marker-${activeCoaching.id}`}
                    initial={{ opacity: 0, scale: 0.6 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.6 }}
                    onClick={() => setOpenCoachingId(activeCoaching.id)}
                    data-testid="coaching-marker"
                    className="absolute right-[-14px] bottom-10 group flex items-center gap-2 p-2 -m-2"
                    title="Your coach has a note on this draft"
                  >
                    <span className="coach-pulse h-3.5 w-3.5 rounded-full bg-[#8C3A2A] ring-4 ring-[#8C3A2A]/15" />
                    <span className="hidden group-hover:inline-block text-[10px] font-mono-panel uppercase tracking-[0.15em] text-[#8C3A2A] bg-white border border-[#8C3A2A]/30 rounded-sm px-2 py-1">
                      Coach note
                    </span>
                  </motion.button>
                )}
              </AnimatePresence>
            </div>

            {/* In-document thinking state — draft stays fully editable. */}
            {loading && (
              <div
                data-testid="coach-thinking"
                className="mt-4 flex items-center gap-2 text-sm text-stone-500"
              >
                <Loader2 className="h-4 w-4 animate-spin text-[#8C3A2A]" />
                Reading your draft…
              </div>
            )}

            {/* Inline coaching prompt — appears adjacent to the document, in the
                coach's voice. One focused invitation; revise the draft above. */}
            <AnimatePresence>
              {activeCoaching && openCoachingId === activeCoaching.id && !loading && (
                <motion.div
                  key={`card-${activeCoaching.id}`}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 8 }}
                  transition={{ duration: 0.35, ease: "easeOut" }}
                  data-testid="coaching-card"
                  className="mt-5 bg-white border-l-2 border-[#8C3A2A] border-y border-r border-stone-200 rounded-sm p-5 shadow-none"
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-[0.18em] text-[#8C3A2A] font-mono-panel">
                      <MessageSquareQuote className="h-3.5 w-3.5" />
                      Your coach
                    </div>
                    <button
                      onClick={() => setOpenCoachingId(null)}
                      data-testid="coaching-card-collapse"
                      className="text-stone-400 hover:text-stone-700"
                      aria-label="Set this note aside"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                  <p
                    data-testid="coaching-invitation"
                    className="text-stone-800 leading-relaxed text-[15px] whitespace-pre-wrap"
                  >
                    {activeCoaching.content}
                    {streaming && (
                      <span className="stream-caret inline-block w-[2px] h-[1.05em] align-[-0.15em] ml-0.5 bg-[#8C3A2A]" />
                    )}
                  </p>
                  <div className="mt-4 flex flex-wrap items-center gap-4">
                    <span className="inline-flex items-center gap-1.5 text-[11px] text-stone-500">
                      <CornerDownRight className="h-3.5 w-3.5" />
                      Revise your draft above, then send it back.
                    </span>
                    <button
                      onClick={submitExplain}
                      disabled={loading}
                      data-testid="explain-more-button"
                      className="text-[11px] font-mono-panel uppercase tracking-[0.14em] text-stone-500 hover:text-[#8C3A2A] transition-colors disabled:opacity-40"
                    >
                      Explain more
                    </button>
                    <button
                      onClick={() => setReplyOpen((v) => !v)}
                      data-testid="reply-to-coach-toggle"
                      className="text-[11px] font-mono-panel uppercase tracking-[0.14em] text-stone-500 hover:text-[#8C3A2A] transition-colors"
                    >
                      Reply
                    </button>
                  </div>

                  {/* Genuine side channel: think aloud WITHOUT changing the draft. */}
                  {replyOpen && (
                    <div className="mt-3 flex items-end gap-2">
                      <textarea
                        data-testid="reply-input"
                        value={reply}
                        onChange={(e) => setReply(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) submitReply();
                        }}
                        rows={2}
                        placeholder="Think aloud to your coach (this doesn't change your draft)…"
                        className="flex-1 bg-[#faf9f6] border border-stone-300 rounded-sm p-2.5 text-sm text-stone-900 placeholder:text-stone-400 outline-none focus:ring-1 focus:ring-stone-900 resize-none"
                      />
                      <button
                        onClick={submitReply}
                        data-testid="send-reply-button"
                        disabled={!reply.trim() || loading}
                        className="shrink-0 bg-stone-900 text-white text-xs px-3 py-2 rounded-sm hover:bg-stone-700 transition-colors disabled:opacity-40"
                      >
                        Send
                      </button>
                    </div>
                  )}
                </motion.div>
              )}
            </AnimatePresence>

            {/* Empty-state helper line before any writing. */}
            {!started && !draft.trim() && (
              <p
                data-testid="empty-state-hint"
                className="mt-4 text-sm text-stone-400 italic font-serif-display"
              >
                Write something and I'll read it as a reader would. I won't write it for you.
              </p>
            )}

            {/* Primary action bar — anchored to the document. */}
            <div className="mt-6 flex items-center justify-between">
              <span className="text-xs text-stone-500 font-mono-panel" data-testid="word-count">
                {wordCount} words
              </span>
              <button
                onClick={submitDraft}
                data-testid="submit-draft-button"
                disabled={!draft.trim() || loading || streaming || !dirty}
                className="group inline-flex items-center gap-2 bg-[#8C3A2A] text-white px-6 py-3 rounded-sm font-medium tracking-wide hover:bg-[#6B2C20] enabled:hover:-translate-y-px transition-[background-color,transform] disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Reading…
                  </>
                ) : (
                  <>
                    {started ? "Send revision" : "Send to coach"}
                    <ArrowRight className="h-4 w-4 transition-transform group-enabled:group-hover:translate-x-0.5" />
                  </>
                )}
              </button>
            </div>
            {started && !dirty && !loading && (
              <p className="mt-2 text-right text-[11px] text-stone-400">
                Add or change something in your draft to send a revision.
              </p>
            )}
          </div>
        </section>

        {/* ============ RIGHT RAIL (secondary — history, recessed) ============ */}
        <aside className="lg:col-span-4 xl:col-span-3 border-l border-stone-200 bg-stone-50/60">
          <div className="sticky top-[73px]">
            <button
              onClick={() => setRailOpen((v) => !v)}
              data-testid="rail-toggle"
              className="w-full flex items-center justify-between px-5 py-4 border-b border-stone-200 text-left"
            >
              <span className="flex items-center gap-2 font-serif-display text-base text-stone-700">
                <History className="h-4 w-4 text-stone-400" />
                Coaching &amp; revisions
              </span>
              <ChevronRight
                className={`h-4 w-4 text-stone-400 transition-transform ${railOpen ? "rotate-90" : ""}`}
              />
            </button>

            {railOpen && (
              <div
                className="px-5 py-5 space-y-6 overflow-y-auto custom-scroll max-h-[calc(100vh-130px)]"
                data-testid="coaching-rail"
              >
                {resolvedCoaching.length === 0 && studentTurns.length <= 1 && (
                  <p className="text-xs text-stone-400 leading-relaxed">
                    Resolved coaching notes and your revision history will collect here as you work. Your active note stays on the document.
                  </p>
                )}

                {resolvedCoaching.length > 0 && (
                  <div data-testid="coaching-history">
                    <p className="font-mono-panel text-[10px] uppercase tracking-[0.2em] text-stone-500 mb-2">
                      Resolved coaching
                    </p>
                    <div className="space-y-2.5">
                      {resolvedCoaching.map((t, i) => (
                        <div
                          key={t.id}
                          data-testid={`coaching-history-item-${i}`}
                          className="border-l-2 border-stone-300 pl-3 py-0.5"
                        >
                          <p className="text-[13px] text-stone-600 leading-relaxed line-clamp-4">
                            {t.content}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {studentTurns.length > 0 && (
                  <div data-testid="revision-history">
                    <p className="font-mono-panel text-[10px] uppercase tracking-[0.2em] text-stone-500 mb-2">
                      Revision history
                    </p>
                    <div className="space-y-2.5">
                      {studentTurns
                        .filter((t) => t.kind === "writing" || t.kind === "revise")
                        .map((t, i, arr) => (
                          <div
                            key={t.id}
                            data-testid={`revision-history-item-${i}`}
                            className="border border-stone-200 rounded-sm px-3 py-2 bg-white"
                          >
                            <p className="font-mono-panel text-[9px] uppercase tracking-[0.18em] text-stone-400 mb-1">
                              {i === 0 ? "First draft" : `Revision ${i}`}
                            </p>
                            <p className="text-[12px] text-stone-600 leading-snug line-clamp-3">
                              {t.content}
                            </p>
                          </div>
                        ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}
