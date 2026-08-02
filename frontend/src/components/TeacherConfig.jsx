import { useState, useEffect } from "react";
import { Toaster, toast } from "sonner";
import { motion } from "framer-motion";
import { Lock, ShieldCheck, Sparkles, ArrowRight, ArrowLeft, Loader2, Compass, AlertTriangle, CheckCircle2, Copy, Check } from "lucide-react";
import {
  getConstitution, createTeacherConfig, updateTeacherConfig,
  validateConfiguration, activateConfiguration, validateRequest,
} from "@/lib/api";

const STORAGE_KEY = "dws_session_id";
const goHome = () => { window.location.search = "?teacher"; };
const inputCls =
  "w-full bg-white border border-stone-300 rounded-sm px-3.5 py-2.5 text-[15px] text-stone-900 placeholder:text-stone-400 outline-none focus:ring-1 focus:ring-[#8C3A2A] focus:border-[#8C3A2A] transition-colors";

const FEEDBACK_OPTS = ["purpose", "reader understanding", "organization", "evidence", "sentence clarity", "voice"];
const EMPHASIS_OPTS = ["ideas", "organization", "evidence", "reasoning", "clarity", "mechanics"];
const STAGE_OPTS = ["Plan", "Draft", "Revise", "Submit", "Peer review", "Reflect"];

const initial = {
  classContext: { course: "English Language Arts", gradeLevel: 9, ageRange: "14-15", classSection: "" },
  assignment: { title: "", directions: "", purpose: "", audience: "Classmates and teacher", genre: "", requiredLength: "", dueDate: "", stages: ["Plan", "Draft", "Revise", "Submit"], revisionCycles: 2 },
  learning: { objectives: [], requiredContentKnowledge: [], requiredReadings: [], standards: [], teacherRubric: "" },
  guidance: { scaffoldingLevel: "adaptive-moderate", questionExplanationBalance: "balanced", feedbackPriorities: ["purpose", "evidence", "organization", "sentence clarity"], instructionalEmphases: [], grammarEmphasis: "moderate", mechanicsEmphasis: "moderate", modelsEnabled: true },
  classroom: { workMode: "individual", norms: "", approvedAccommodations: [], teacherPrompts: [], teacherExemplars: [], teacherNotes: "" },
  gradeCalibration: { profile: "grade-9", profileVersion: "1.0" },
};

const lines = (s) => s.split("\n").map((x) => x.trim()).filter(Boolean);
const joinLines = (a) => (a || []).join("\n");

export default function TeacherConfig() {
  const [c, setC] = useState(initial);
  const [configId, setConfigId] = useState(null);
  const [constitution, setConstitution] = useState(null);
  const [busy, setBusy] = useState(false);
  const [validation, setValidation] = useState(null);
  const [reqText, setReqText] = useState("");
  const [checking, setChecking] = useState(false);
  const [verdict, setVerdict] = useState(null);
  const [created, setCreated] = useState(null);

  useEffect(() => { getConstitution().then(setConstitution).catch(() => {}); }, []);

  const upd = (section, patch) => setC((prev) => ({ ...prev, [section]: { ...prev[section], ...patch } }));
  const toggle = (section, key, opt) => setC((prev) => {
    const cur = prev[section][key] || [];
    return { ...prev, [section]: { ...prev[section], [key]: cur.includes(opt) ? cur.filter((x) => x !== opt) : [...cur, opt] } };
  });

  const persist = async () => {
    const saved = configId ? await updateTeacherConfig(configId, c) : await createTeacherConfig(c);
    setConfigId(saved.id);
    return saved.id;
  };

  const saveDraft = async () => {
    setBusy(true);
    try { await persist(); toast.success("Draft saved."); }
    catch { toast.error("Could not save the draft."); }
    finally { setBusy(false); }
  };

  const runValidation = async () => {
    setBusy(true);
    try {
      const id = configId || (await persist());
      if (configId) await updateTeacherConfig(id, c);
      const v = await validateConfiguration(id);
      setValidation(v);
      if (v.valid) toast.success("Configuration is valid.");
      else toast.error("Please resolve the items below before activating.");
      return v;
    } catch { toast.error("Validation failed."); }
    finally { setBusy(false); }
  };

  const activate = async () => {
    setBusy(true);
    try {
      const id = configId || (await persist());
      await updateTeacherConfig(id, c);
      const cfg = await activateConfiguration(id);
      // Teacher product: creating an assignment returns to the workspace with a
      // shareable join code — it does NOT start a student session here.
      setCreated(cfg);
      toast.success("Assignment created.");
    } catch (e) {
      const detail = e?.response?.data?.detail;
      if (detail && typeof detail === "object") { setValidation(detail); toast.error("Resolve the items below before creating."); }
      else toast.error("Could not create the assignment.");
    } finally { setBusy(false); }
  };

  const checkRequest = async () => {
    if (!reqText.trim() || checking) return;
    setChecking(true); setVerdict(null);
    try { setVerdict(await validateRequest(reqText.trim())); }
    catch { toast.error("Could not evaluate that request."); }
    finally { setChecking(false); }
  };

  const Field = ({ label, children }) => (
    <div>
      <label className="block font-mono-panel text-[11px] uppercase tracking-[0.14em] text-stone-500 mb-1.5">{label}</label>
      {children}
    </div>
  );
  const Sec = ({ name, children }) => (
    <section data-testid={`config-section-${name.toLowerCase().replace(/\s+/g, "-")}`}>
      <h2 className="font-serif-display text-lg text-stone-800 border-b border-stone-200 pb-2 mb-4">{name}</h2>
      <div className="space-y-4">{children}</div>
    </section>
  );
  const Chips = ({ opts, sel, on }) => (
    <div className="flex flex-wrap gap-2">
      {opts.map((o) => (
        <button key={o} type="button" onClick={() => on(o)} data-testid={`chip-${o.toLowerCase().replace(/\s+/g, "-")}`}
          className={`text-sm px-3 py-1.5 rounded-sm border transition-colors ${(sel || []).includes(o) ? "bg-stone-900 text-white border-stone-900" : "bg-transparent text-stone-600 border-stone-300 hover:border-stone-900"}`}>{o}</button>
      ))}
    </div>
  );

  if (created) {
    const code = created.code || "";
    return (
      <div className="min-h-screen paper-grain flex items-center justify-center px-6" data-testid="assignment-created">
        <Toaster position="top-center" richColors />
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}
          className="max-w-lg w-full text-center">
          <div className="inline-flex items-center justify-center h-14 w-14 rounded-full bg-emerald-50 border border-emerald-200 mb-6">
            <CheckCircle2 className="h-7 w-7 text-emerald-600" />
          </div>
          <h1 className="font-serif-display text-3xl md:text-4xl tracking-tight text-stone-900">Assignment created</h1>
          <p className="text-stone-600 mt-3 text-[15px] leading-relaxed">
            “{created.assignment?.title || "Your assignment"}” is ready. Share the join code below — each student
            starts their own writing session with it.
          </p>
          <div className="mt-7 border border-stone-300 rounded-md bg-white p-6">
            <p className="font-mono-panel text-[11px] uppercase tracking-[0.18em] text-stone-400 mb-2">Student join code</p>
            <button
              data-testid="created-join-code"
              onClick={async () => { try { await navigator.clipboard.writeText(code); toast.success(`Code ${code} copied.`); } catch { /* noop */ } }}
              className="inline-flex items-center gap-3 font-mono text-3xl tracking-[0.3em] text-stone-900 hover:text-[#8C3A2A] transition-colors"
              title="Copy code"
            >
              {code}
              <Copy className="h-5 w-5 text-stone-400" />
            </button>
          </div>
          <div className="flex items-center justify-center gap-3 mt-8">
            <button data-testid="created-go-home" onClick={goHome}
              className="inline-flex items-center gap-2 bg-[#8C3A2A] text-white text-[15px] px-5 py-3 rounded-sm hover:bg-[#6B2C20] transition-colors">
              Go to workspace <ArrowRight className="h-4 w-4" />
            </button>
            <button data-testid="created-create-another"
              onClick={() => { setCreated(null); setConfigId(null); setC(initial); setValidation(null); window.scrollTo(0, 0); }}
              className="text-[14px] text-stone-600 hover:text-stone-900 border border-stone-300 hover:border-stone-900 rounded-sm px-4 py-3 transition-colors">
              Create another
            </button>
          </div>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="min-h-screen paper-grain">
      <Toaster position="top-center" richColors />
      <header className="flex items-center justify-between px-8 md:px-12 py-5 border-b border-stone-200 bg-[#faf9f6] sticky top-0 z-20">
        <div className="flex items-center gap-4">
          <button onClick={goHome} data-testid="config-back-home"
            className="inline-flex items-center gap-1.5 text-xs font-mono-panel uppercase tracking-[0.14em] text-stone-500 hover:text-stone-900 transition-colors">
            <ArrowLeft className="h-3.5 w-3.5" /> Workspace
          </button>
          <div className="flex items-center gap-2 font-serif-display text-xl text-stone-900"><Compass className="h-5 w-5 text-[#8C3A2A]" />Compass</div>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={saveDraft} disabled={busy} data-testid="config-save-draft"
            className="text-xs font-mono-panel uppercase tracking-[0.15em] text-stone-500 hover:text-stone-900 border border-stone-300 hover:border-stone-900 rounded-sm px-3 py-1.5 transition-colors disabled:opacity-40">Save draft</button>
          <button onClick={runValidation} disabled={busy} data-testid="config-validate"
            className="text-xs font-mono-panel uppercase tracking-[0.15em] text-stone-700 border border-stone-400 hover:border-stone-900 rounded-sm px-3 py-1.5 transition-colors disabled:opacity-40">Check</button>
          <button onClick={activate} disabled={busy} data-testid="config-activate"
            className="inline-flex items-center gap-2 bg-[#8C3A2A] text-white text-sm px-4 py-1.5 rounded-sm hover:bg-[#6B2C20] transition-colors disabled:opacity-40">
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowRight className="h-4 w-4" />}Create assignment</button>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-8 md:px-12 py-12 grid grid-cols-1 lg:grid-cols-12 gap-12">
        <main className="lg:col-span-7 space-y-11" data-testid="config-form">
          <div>
            <p className="font-mono-panel text-xs uppercase tracking-[0.2em] text-[#8C3A2A] mb-2">New assignment · Grade 9</p>
            <h1 className="font-serif-display text-4xl md:text-5xl tracking-tight text-stone-900 leading-tight">Create an assignment.</h1>
            <p className="text-stone-600 mt-3 text-[15px] leading-relaxed max-w-xl">You decide <span className="text-stone-900 font-medium">what</span>, <span className="text-stone-900 font-medium">why</span>, and <span className="text-stone-900 font-medium">when</span> students learn — and how Compass is used. Compass keeps the developmental method intact.</p>
          </div>

          <Sec name="Class and Learners">
            <Field label="Course / subject"><input data-testid="cfg-course" className={inputCls} value={c.classContext.course} onChange={(e) => upd("classContext", { course: e.target.value })} /></Field>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Grade level"><select data-testid="cfg-grade" className={inputCls} value={c.classContext.gradeLevel} onChange={(e) => upd("classContext", { gradeLevel: parseInt(e.target.value, 10) })}><option value={9}>Grade 9</option></select></Field>
              <Field label="Student age range"><select data-testid="cfg-age" className={inputCls} value={c.classContext.ageRange} onChange={(e) => upd("classContext", { ageRange: e.target.value })}><option>14-15</option></select></Field>
            </div>
            <Field label="Class / section"><input data-testid="cfg-section" className={inputCls} value={c.classContext.classSection} onChange={(e) => upd("classContext", { classSection: e.target.value })} /></Field>
            <Field label="Individual or collaborative"><select data-testid="cfg-workmode" className={inputCls} value={c.classroom.workMode} onChange={(e) => upd("classroom", { workMode: e.target.value })}><option value="individual">Individual</option><option value="collaborative">Collaborative</option></select></Field>
          </Sec>

          <Sec name="Assignment and Purpose">
            <Field label="Assignment title *"><input data-testid="cfg-title" className={inputCls} value={c.assignment.title} onChange={(e) => upd("assignment", { title: e.target.value })} /></Field>
            <Field label="Assignment directions *"><textarea data-testid="cfg-directions" rows={4} className={`${inputCls} resize-none`} value={c.assignment.directions} onChange={(e) => upd("assignment", { directions: e.target.value })} /></Field>
            <Field label="Purpose of the assignment *"><textarea data-testid="cfg-purpose" rows={2} className={`${inputCls} resize-none`} placeholder="What are students expected to accomplish?" value={c.assignment.purpose} onChange={(e) => upd("assignment", { purpose: e.target.value })} /></Field>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Intended audience"><input data-testid="cfg-audience" className={inputCls} value={c.assignment.audience} onChange={(e) => upd("assignment", { audience: e.target.value })} /></Field>
              <Field label="Genre / form"><input data-testid="cfg-genre" className={inputCls} placeholder="e.g. position paper" value={c.assignment.genre} onChange={(e) => upd("assignment", { genre: e.target.value })} /></Field>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Required length"><input data-testid="cfg-length" className={inputCls} value={c.assignment.requiredLength} onChange={(e) => upd("assignment", { requiredLength: e.target.value })} /></Field>
              <Field label="Due date"><input data-testid="cfg-due" className={inputCls} placeholder="YYYY-MM-DD" value={c.assignment.dueDate} onChange={(e) => upd("assignment", { dueDate: e.target.value })} /></Field>
            </div>
          </Sec>

          <Sec name="Learning Goals">
            <Field label="Learning objectives * (one per line)"><textarea data-testid="cfg-objectives" rows={3} className={`${inputCls} resize-none`} value={joinLines(c.learning.objectives)} onChange={(e) => upd("learning", { objectives: lines(e.target.value) })} /></Field>
            <Field label="Required readings / sources (one per line)"><textarea data-testid="cfg-readings" rows={2} className={`${inputCls} resize-none`} value={joinLines(c.learning.requiredReadings)} onChange={(e) => upd("learning", { requiredReadings: lines(e.target.value) })} /></Field>
            <Field label="Required content knowledge (one per line)"><textarea data-testid="cfg-content" rows={2} className={`${inputCls} resize-none`} value={joinLines(c.learning.requiredContentKnowledge)} onChange={(e) => upd("learning", { requiredContentKnowledge: lines(e.target.value) })} /></Field>
          </Sec>

          <Sec name="Standards and Evaluation">
            <Field label="Writing standards (one per line)"><textarea data-testid="cfg-standards" rows={2} className={`${inputCls} resize-none`} value={joinLines(c.learning.standards)} onChange={(e) => upd("learning", { standards: lines(e.target.value) })} /></Field>
            <Field label="Teacher rubric (paste or describe — orientation, not for scoring the student)"><textarea data-testid="cfg-rubric" rows={3} className={`${inputCls} resize-none`} value={c.learning.teacherRubric || ""} onChange={(e) => upd("learning", { teacherRubric: e.target.value })} /></Field>
          </Sec>

          <Sec name="Guidance and Feedback">
            <Field label="Degree of scaffolding"><select data-testid="cfg-scaffolding" className={inputCls} value={c.guidance.scaffoldingLevel} onChange={(e) => upd("guidance", { scaffoldingLevel: e.target.value })}>
              <option value="low">Low (begins with less visible support)</option><option value="moderate">Moderate</option><option value="high">High</option><option value="adaptive-moderate">Adaptive (starts moderate)</option></select>
              <p className="text-xs text-stone-500 mt-1">Scaffolding cannot be turned off entirely — Compass adds support when a student cannot proceed and fades it as they gain control.</p></Field>
            <Field label="Questioning vs. explanation"><select data-testid="cfg-qeb" className={inputCls} value={c.guidance.questionExplanationBalance} onChange={(e) => upd("guidance", { questionExplanationBalance: e.target.value })}><option value="mostly-questions">Mostly questions</option><option value="balanced">Balanced</option><option value="more-explanation">More explanation</option></select></Field>
            <Field label="Feedback priorities *"><Chips opts={FEEDBACK_OPTS} sel={c.guidance.feedbackPriorities} on={(o) => toggle("guidance", "feedbackPriorities", o)} /></Field>
            <Field label="Instructional emphases"><Chips opts={EMPHASIS_OPTS} sel={c.guidance.instructionalEmphases} on={(o) => toggle("guidance", "instructionalEmphases", o)} /></Field>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Grammar emphasis"><select data-testid="cfg-grammar" className={inputCls} value={c.guidance.grammarEmphasis} onChange={(e) => upd("guidance", { grammarEmphasis: e.target.value })}><option>low</option><option>moderate</option><option>high</option></select></Field>
              <Field label="Spelling & mechanics emphasis"><select data-testid="cfg-mechanics" className={inputCls} value={c.guidance.mechanicsEmphasis} onChange={(e) => upd("guidance", { mechanicsEmphasis: e.target.value })}><option>low</option><option>moderate</option><option>high</option></select></Field>
            </div>
            <label className="flex items-center gap-2 text-[15px] text-stone-700 cursor-pointer">
              <input type="checkbox" data-testid="cfg-models" checked={c.guidance.modelsEnabled} onChange={(e) => upd("guidance", { modelsEnabled: e.target.checked })} className="accent-[#8C3A2A] h-4 w-4" />
              Enable models (used to teach — never text for submission)</label>
          </Sec>

          <Sec name="Revision Expectations">
            <Field label="Revision cycles (minimum 1 substantive revision)"><input data-testid="cfg-revcycles" type="number" min={1} className={inputCls} value={c.assignment.revisionCycles} onChange={(e) => upd("assignment", { revisionCycles: parseInt(e.target.value || "0", 10) })} /></Field>
            <Field label="Assignment stages"><Chips opts={STAGE_OPTS} sel={c.assignment.stages} on={(o) => toggle("assignment", "stages", o)} /></Field>
          </Sec>

          <Sec name="Classroom">
            <Field label="Classroom norms"><textarea data-testid="cfg-norms" rows={2} className={`${inputCls} resize-none`} value={c.classroom.norms} onChange={(e) => upd("classroom", { norms: e.target.value })} /></Field>
            <Field label="Teacher prompts (one per line)"><textarea data-testid="cfg-prompts" rows={2} className={`${inputCls} resize-none`} value={joinLines(c.classroom.teacherPrompts)} onChange={(e) => upd("classroom", { teacherPrompts: lines(e.target.value) })} /></Field>
            <Field label="Teacher exemplars (one per line — instructional models)"><textarea data-testid="cfg-exemplars" rows={2} className={`${inputCls} resize-none`} value={joinLines(c.classroom.teacherExemplars)} onChange={(e) => upd("classroom", { teacherExemplars: lines(e.target.value) })} /></Field>
            <Field label="Approved accommodations (one per line — support access, not lower expectations)"><textarea data-testid="cfg-accommodations" rows={2} className={`${inputCls} resize-none`} value={joinLines(c.classroom.approvedAccommodations)} onChange={(e) => upd("classroom", { approvedAccommodations: lines(e.target.value) })} /></Field>
            <Field label="Notes to Compass"><textarea data-testid="cfg-notes" rows={2} className={`${inputCls} resize-none`} value={c.classroom.teacherNotes} onChange={(e) => upd("classroom", { teacherNotes: e.target.value })} /></Field>
          </Sec>
        </main>

        <aside className="lg:col-span-5 space-y-8">
          {/* Review & Activate preview */}
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}
            className="border border-stone-300 rounded-sm p-6 bg-white sticky top-24" data-testid="config-preview">
            <p className="font-mono-panel text-[11px] uppercase tracking-[0.18em] text-[#8C3A2A] mb-3">Assignment summary</p>
            <dl className="text-[14px] text-stone-700 space-y-1.5">
              <Row k="Class" v={`Grade ${c.classContext.gradeLevel} ${c.classContext.course}`} />
              <Row k="Assignment" v={c.assignment.title || "—"} />
              <Row k="Purpose" v={c.assignment.purpose || "—"} />
              <Row k="Audience" v={c.assignment.audience || "—"} />
              <Row k="Objectives" v={c.learning.objectives.length ? c.learning.objectives.join(", ") : "—"} />
              <Row k="Scaffolding" v={c.guidance.scaffoldingLevel} />
              <Row k="Feedback" v={c.guidance.feedbackPriorities.join(", ") || "—"} />
              <Row k="Grammar" v={`${c.guidance.grammarEmphasis}, meaning-centered`} />
              <Row k="Revision" v={`${c.assignment.revisionCycles} cycle(s)`} />
              <Row k="Models" v={c.guidance.modelsEnabled ? "Enabled" : "Off"} />
            </dl>

            {validation && (
              <div className="mt-4 border-t border-stone-200 pt-3" data-testid="validation-result">
                {validation.valid ? (
                  <div className="flex items-center gap-2 text-emerald-700 text-sm"><CheckCircle2 className="h-4 w-4" />Valid — ready to activate.</div>
                ) : (
                  <div className="space-y-1.5">
                    {[...validation.errors, ...validation.conflicts].map((it, i) => (
                      <div key={i} className="flex items-start gap-2 text-[#8C3A2A] text-[13px]" data-testid="validation-error"><AlertTriangle className="h-3.5 w-3.5 mt-0.5 shrink-0" /><span>{it.message}</span></div>
                    ))}
                  </div>
                )}
                {validation.warnings?.map((w, i) => (
                  <div key={`w${i}`} className="flex items-start gap-2 text-amber-700 text-[13px] mt-1"><AlertTriangle className="h-3.5 w-3.5 mt-0.5 shrink-0" /><span>{w.message}</span></div>
                ))}
              </div>
            )}
          </motion.div>

          {/* Constitution (locked) */}
          <div className="border border-stone-300 bg-[#f0ede6] rounded-sm p-6" data-testid="constitution-panel">
            <div className="flex items-center gap-2 text-[#8C3A2A] mb-1"><ShieldCheck className="h-4 w-4" /><span className="font-mono-panel text-[11px] uppercase tracking-[0.18em]">Always active — Compass commitments</span></div>
            <p className="text-stone-600 text-sm leading-relaxed mb-4">Not settings. They cannot be turned off. Students remain the authors; Compass guides, it never does the work.</p>
            {constitution && (<>
              <div className="space-y-1.5 mb-4">{constitution.locked_principles.slice(0, 7).map((p) => (
                <div key={p} className="flex items-start gap-2" data-testid="locked-principle"><Lock className="h-3.5 w-3.5 text-stone-500 mt-0.5 shrink-0" /><span className="text-[14px] text-stone-800">{p}</span></div>))}</div>
              <p className="font-mono-panel text-[10px] uppercase tracking-[0.16em] text-stone-500 mb-2">Compass will never</p>
              <div className="flex flex-wrap gap-1.5">{constitution.never_provides.map((n) => (
                <span key={n} className="text-[12px] text-stone-500 line-through decoration-stone-400/70 bg-white/60 border border-stone-200 rounded-sm px-2 py-0.5">{n}</span>))}</div>
            </>)}
          </div>

          {/* Ask Compass (Part VI) */}
          <div className="border border-stone-200 rounded-sm p-6 bg-white" data-testid="request-checker">
            <div className="flex items-center gap-2 mb-1"><Sparkles className="h-4 w-4 text-[#8C3A2A]" /><span className="font-mono-panel text-[11px] uppercase tracking-[0.18em] text-stone-700">Want Compass to do something specific?</span></div>
            <p className="text-stone-500 text-sm mb-3">Describe it. If it would take the thinking away from students, Compass offers the closest way to meet the same goal.</p>
            <textarea data-testid="request-input" rows={2} className={`${inputCls} resize-none`} placeholder="e.g. Rewrite weak introductions for my students." value={reqText} onChange={(e) => setReqText(e.target.value)} />
            <button onClick={checkRequest} disabled={!reqText.trim() || checking} data-testid="request-submit" className="mt-3 inline-flex items-center gap-2 bg-stone-900 text-white text-sm px-4 py-2 rounded-sm hover:bg-stone-700 transition-colors disabled:opacity-40">
              {checking ? <><Loader2 className="h-4 w-4 animate-spin" /> Asking Compass…</> : "Ask Compass"}</button>
            {verdict && (
              <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }} className="mt-5 border-t border-stone-200 pt-4" data-testid="request-verdict">
                <span className={`inline-block font-mono-panel text-[10px] uppercase tracking-[0.14em] px-2 py-1 rounded-sm mb-3 ${verdict.allowed ? "bg-emerald-50 text-emerald-700 border border-emerald-200" : "bg-[#8C3A2A]/10 text-[#8C3A2A] border border-[#8C3A2A]/25"}`}>{verdict.allowed ? "You can set this" : "Preserved by Compass"}</span>
                <p className="text-[15px] text-stone-800 leading-relaxed whitespace-pre-wrap" data-testid="request-response">{verdict.compass_response}</p>
                {!verdict.allowed && verdict.closest_alternatives?.length > 0 && (
                  <ul className="mt-3 space-y-1.5" data-testid="request-alternatives">{verdict.closest_alternatives.map((a, i) => (
                    <li key={i} className="flex items-start gap-2 text-[14px] text-stone-700"><ArrowRight className="h-3.5 w-3.5 text-[#8C3A2A] mt-1 shrink-0" /><span>{a}</span></li>))}</ul>)}
              </motion.div>)}
          </div>
        </aside>
      </div>
    </div>
  );
}

const Row = ({ k, v }) => (
  <div className="flex gap-2"><dt className="font-mono-panel text-[10px] uppercase tracking-[0.12em] text-stone-400 w-24 shrink-0 pt-0.5">{k}</dt><dd className="text-stone-800 flex-1">{v}</dd></div>
);
