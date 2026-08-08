import { useState } from "react";
import { createSentenceCraftTest } from "@/lib/api";

// DEVELOPER-ONLY (?sctest) — direct entry into the production Sentence Craft experience.
// Bypasses ONLY the composition scaffolding: it creates a synthetic structurally-ready session and
// then hands off to the SAME learner Sentence Craft UI (PublicPreview writing view) by resuming the
// session it just created. Never shown on the normal learner path.
const SAMPLE = {
  assignment: "Argue whether schools should reduce the amount of homework they assign.",
  paragraph:
    "Homework assigned in large amounts harms students more than it helps them. When children spend hours on assignments every night, they lose the rest and free time that growing minds need. It is bad. Teachers should assign less so students can recover and absorb what they learned.",
};

export default function SentenceCraftTest() {
  const [f, setF] = useState({
    assignment: "", paragraph: "", thesis: "", grade_level: "",
    known_pattern: "", pattern_confidence: "", scaffold_level: "", start_sentence: 1,
  });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const set = (k) => (e) => setF((p) => ({ ...p, [k]: e.target.value }));

  const start = async () => {
    setErr("");
    if (!f.assignment.trim() || !f.paragraph.trim()) {
      setErr("Assignment and paragraph are required.");
      return;
    }
    setBusy(true);
    try {
      const s = await createSentenceCraftTest({
        ...f,
        start_sentence: parseInt(f.start_sentence, 10) || 1,
      });
      // hand off to the EXACT production Sentence Craft learner UI by resuming this session.
      localStorage.setItem("compass_student_session", JSON.stringify({ id: s.id, mode: "writing" }));
      window.location.href = "?preview=writing";
    } catch (e) {
      setErr(e?.response?.data?.detail || "Could not start the Sentence Craft test. Please try again.");
      setBusy(false);
    }
  };

  const field = "w-full rounded-sm border border-stone-300 bg-white px-3 py-2 text-[14px] text-stone-800 focus:border-[#8C3A2A] focus:outline-none";
  const label = "block text-[11px] uppercase tracking-[0.16em] text-stone-500 font-mono-panel mb-1";

  return (
    <div className="min-h-screen paper-grain flex items-start justify-center py-12 px-4">
      <div className="w-full max-w-2xl" data-testid="sctest-page">
        <div className="mb-6">
          <div className="text-[11px] uppercase tracking-[0.18em] text-[#8C3A2A] font-mono-panel">
            Developer · Testing Shortcut
          </div>
          <h1 className="font-serif-display text-3xl text-stone-800 mt-1">Test Sentence Craft</h1>
          <p className="text-[13px] text-stone-500 mt-2 leading-relaxed">
            Jump straight into the real production Sentence Craft experience with any paragraph — no
            conceptual development or structural scaffolding first. Runs the actual sentence-level
            cognition, controller, coaching, pattern logic, and upward routing.
          </p>
        </div>

        <div className="space-y-4 bg-white/70 border border-stone-200 rounded-md p-5">
          <div>
            <label className={label}>Assignment / writing purpose *</label>
            <textarea data-testid="sctest-assignment" className={field} rows={2}
              value={f.assignment} onChange={set("assignment")}
              placeholder="e.g. Argue whether schools should reduce homework." />
          </div>
          <div>
            <label className={label}>Paragraph to test *</label>
            <textarea data-testid="sctest-paragraph" className={field} rows={6}
              value={f.paragraph} onChange={set("paragraph")}
              placeholder="Paste the paragraph you want to work on sentence by sentence." />
          </div>
          <div>
            <label className={label}>Thesis / main point (optional — inferred if blank)</label>
            <input data-testid="sctest-thesis" className={field} value={f.thesis} onChange={set("thesis")}
              placeholder="Leave blank to let Compass infer a provisional main point." />
          </div>

          <details className="group">
            <summary className="cursor-pointer text-[12px] uppercase tracking-[0.14em] text-stone-500 font-mono-panel select-none">
              Optional test context ▾
            </summary>
            <div className="grid grid-cols-2 gap-3 mt-3">
              <div>
                <label className={label}>Start with sentence</label>
                <input data-testid="sctest-start" type="number" min={1} className={field}
                  value={f.start_sentence} onChange={set("start_sentence")} />
              </div>
              <div>
                <label className={label}>Grade / learner level</label>
                <input data-testid="sctest-grade" className={field} value={f.grade_level} onChange={set("grade_level")}
                  placeholder="e.g. Grade 9" />
              </div>
              <div>
                <label className={label}>Known recurring pattern</label>
                <input data-testid="sctest-pattern" className={field} value={f.known_pattern} onChange={set("known_pattern")}
                  placeholder="e.g. leaves causal links implicit" />
              </div>
              <div>
                <label className={label}>Pattern confidence</label>
                <select data-testid="sctest-pattern-confidence" className={field}
                  value={f.pattern_confidence} onChange={set("pattern_confidence")}>
                  <option value="">—</option>
                  <option value="tentative">tentative</option>
                  <option value="moderate">moderate</option>
                  <option value="high">high</option>
                </select>
              </div>
              <div className="col-span-2">
                <label className={label}>Initial scaffold level</label>
                <select data-testid="sctest-scaffold" className={field}
                  value={f.scaffold_level} onChange={set("scaffold_level")}>
                  <option value="">—</option>
                  <option value="more_support">more_support</option>
                  <option value="guided_attention">guided_attention</option>
                  <option value="self_monitoring">self_monitoring</option>
                  <option value="independent_check">independent_check</option>
                </select>
              </div>
            </div>
          </details>

          {err && <div data-testid="sctest-error" className="text-[13px] text-red-600">{err}</div>}

          <div className="flex items-center gap-3 pt-1">
            <button data-testid="sctest-start-button" onClick={start} disabled={busy}
              className="rounded-full bg-[#8C3A2A] text-white px-6 py-2.5 text-[14px] font-medium hover:bg-[#75301f] transition-colors disabled:opacity-50">
              {busy ? "Starting…" : "Start Sentence Craft"}
            </button>
            <button data-testid="sctest-sample-button" onClick={() => setF((p) => ({ ...p, ...SAMPLE }))}
              className="text-[13px] text-stone-500 hover:text-stone-700 underline underline-offset-2">
              Load sample
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
