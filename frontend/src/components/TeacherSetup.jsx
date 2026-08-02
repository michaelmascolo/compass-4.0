import { useState } from "react";
import { motion } from "framer-motion";
import { PenLine, ArrowRight, Loader2 } from "lucide-react";

const FIELDS = [
  {
    key: "assignment",
    label: "Assignment",
    placeholder: "e.g. Write an argumentative essay on whether cities should ban cars from downtown cores.",
    hint: "The overall piece of work the student is producing.",
    multiline: false,
  },
  {
    key: "assignment_prompt",
    label: "Assignment Prompt",
    placeholder: "e.g. Should cities ban cars from their downtown cores? Take a position and defend it.",
    hint: "The question the student is answering. Stays visible the whole session to keep them on track. (optional)",
    multiline: true,
  },
  {
    key: "pedagogical_purpose",
    label: "Pedagogical Purpose",
    placeholder: "e.g. Students should learn to organize an argument so each paragraph advances a single claim toward the thesis.",
    hint: "What you want the student to develop as a writer. Everything the coach does returns to this.",
    multiline: true,
  },
  {
    key: "current_writing_task",
    label: "Current Writing Task",
    placeholder: "e.g. Draft the opening two paragraphs establishing your position.",
    hint: "The concrete slice of the assignment the student works on right now.",
    multiline: false,
  },
  {
    key: "teacher_notes",
    label: "Teacher Notes",
    placeholder: "e.g. This student tends to list ideas rather than connect them. (optional)",
    hint: "Optional context that shapes how the coach reads the writing.",
    multiline: true,
  },
];

export default function TeacherSetup({ onBegin, submitting, onQuickStart }) {
  const [form, setForm] = useState({
    assignment: "",
    assignment_prompt: "",
    pedagogical_purpose: "",
    current_writing_task: "",
    teacher_notes: "",
  });

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });
  const ready =
    form.assignment.trim() &&
    form.pedagogical_purpose.trim() &&
    form.current_writing_task.trim();

  const submit = (e) => {
    e.preventDefault();
    if (ready && !submitting) onBegin(form);
  };

  return (
    <div className="min-h-screen grid grid-cols-1 lg:grid-cols-12">
      {/* Left — editorial hero */}
      <div className="hidden lg:block lg:col-span-5 relative border-r border-stone-200">
        <img
          src="https://images.unsplash.com/photo-1765652583547-122f44c53d2f?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjAzMzJ8MHwxfHNlYXJjaHwzfHxhY2FkZW1pYyUyMGxpYnJhcnklMjBkZXNrJTIwdmludGFnZXxlbnwwfHx8fDE3ODQzMDgyMTB8MA&ixlib=rb-4.1.0&q=85"
          alt="A vintage typewriter resting on a shelf of well-worn books"
          className="absolute inset-0 h-full w-full object-cover"
        />
        <div className="absolute inset-0 bg-stone-900/55" />
        <div className="relative h-full flex flex-col justify-between p-12 xl:p-16 text-stone-50">
          <div className="flex items-center gap-2 text-sm tracking-widest uppercase font-mono-panel text-amber-300/90">
            <PenLine className="h-4 w-4" />
            <span>Developmental Writing Studio</span>
          </div>
          <div>
            <h1 className="font-serif-display text-4xl xl:text-6xl leading-[1.05] tracking-tight">
              We don't fix the writing.
              <br />
              <span className="text-amber-300">We develop the writer.</span>
            </h1>
            <p className="mt-6 max-w-md text-stone-200 leading-relaxed">
              Define the purpose behind the assignment. The coach reads every
              draft against that purpose and offers one focused invitation at a
              time — never a correction, never a rewrite.
            </p>
          </div>
        </div>
      </div>

      {/* Right — form */}
      <div className="lg:col-span-7 paper-grain flex items-center justify-center px-6 py-14 sm:px-12">
        <motion.form
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          onSubmit={submit}
          className="w-full max-w-xl"
          data-testid="teacher-setup-form"
        >
          <p className="font-mono-panel text-xs uppercase tracking-[0.2em] text-[#8C3A2A]">
            Screen 1 — Teacher Setup
          </p>
          <h2 className="font-serif-display text-3xl sm:text-4xl tracking-tight text-stone-900 mt-2">
            Frame the session
          </h2>
          <p className="text-stone-500 mt-2 text-sm">
            The purpose you set here governs the entire conversation.
          </p>

          <div className="mt-9 space-y-7">
            {FIELDS.map((f) => (
              <div key={f.key}>
                <label
                  htmlFor={f.key}
                  className="block font-mono-panel text-xs uppercase tracking-[0.15em] text-stone-700 mb-2"
                >
                  {f.label}
                  {f.key !== "teacher_notes" && f.key !== "assignment_prompt" && (
                    <span className="text-[#8C3A2A]"> *</span>
                  )}
                </label>
                {f.multiline ? (
                  <textarea
                    id={f.key}
                    data-testid={`input-${f.key}`}
                    value={form[f.key]}
                    onChange={set(f.key)}
                    placeholder={f.placeholder}
                    rows={3}
                    className="w-full bg-white border border-stone-300 rounded-sm p-4 text-stone-900 placeholder:text-stone-400 outline-none focus:ring-1 focus:ring-stone-900 focus:border-stone-900 transition-colors resize-none leading-relaxed"
                  />
                ) : (
                  <input
                    id={f.key}
                    data-testid={`input-${f.key}`}
                    value={form[f.key]}
                    onChange={set(f.key)}
                    placeholder={f.placeholder}
                    className="w-full bg-white border border-stone-300 rounded-sm p-4 text-stone-900 placeholder:text-stone-400 outline-none focus:ring-1 focus:ring-stone-900 focus:border-stone-900 transition-colors"
                  />
                )}
                <p className="mt-1.5 text-xs text-stone-500">{f.hint}</p>
              </div>
            ))}
          </div>

          <button
            type="submit"
            data-testid="begin-session-button"
            disabled={!ready || submitting}
            className="group mt-9 inline-flex items-center gap-2 bg-[#8C3A2A] text-white px-7 py-3.5 rounded-sm font-medium tracking-wide hover:bg-[#6B2C20] enabled:hover:-translate-y-px transition-[background-color,transform] disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {submitting ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Opening studio…
              </>
            ) : (
              <>
                Begin Session
                <ArrowRight className="h-4 w-4 transition-transform group-enabled:group-hover:translate-x-0.5" />
              </>
            )}
          </button>

          {onQuickStart && (
            <button
              type="button"
              data-testid="quick-test-start-button"
              onClick={() => !submitting && onQuickStart()}
              disabled={submitting}
              className="mt-4 block text-xs font-mono-panel uppercase tracking-[0.15em] text-stone-500 hover:text-[#8C3A2A] underline underline-offset-4 decoration-stone-300 hover:decoration-[#8C3A2A] transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Skip setup — quick test start →
            </button>
          )}
        </motion.form>
      </div>
    </div>
  );
}
