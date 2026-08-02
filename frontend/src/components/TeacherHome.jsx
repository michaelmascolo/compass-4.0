import { useEffect, useState } from "react";
import { Toaster, toast } from "sonner";
import { motion } from "framer-motion";
import {
  Compass, Plus, Loader2, Users, Activity, Copy, Check, ArrowRight,
  FileText, Clock, GraduationCap,
} from "lucide-react";
import { listTeacherAssignments } from "@/lib/api";

const accent = "#8C3A2A";

const goCreate = () => { window.location.search = "?config"; };
const goDashboard = (id) => {
  // Per-assignment Teacher Dashboard is the next increment; guide to the working action.
  toast.message("Student dashboard is coming in the next step.", {
    description: "For now, share the join code below so students can start writing.",
  });
};

const fmtDate = (iso) => {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });
  } catch { return "—"; }
};

const StatusBadge = ({ status }) => (
  <span
    data-testid="assignment-status"
    className={`text-[10px] uppercase tracking-widest px-2 py-0.5 rounded-full border ${
      status === "active"
        ? "border-emerald-700/40 bg-emerald-50 text-emerald-800"
        : "border-stone-300 bg-stone-100 text-stone-500"
    }`}
  >
    {status}
  </span>
);

const CopyCode = ({ code }) => {
  const [done, setDone] = useState(false);
  const copy = async (e) => {
    e.stopPropagation();
    try {
      await navigator.clipboard.writeText(code);
      setDone(true);
      toast.success(`Code ${code} copied — students join with this.`);
      setTimeout(() => setDone(false), 1600);
    } catch { toast.error("Could not copy the code."); }
  };
  return (
    <button
      data-testid={`copy-code-${code}`}
      onClick={copy}
      className="inline-flex items-center gap-1.5 font-mono text-[13px] tracking-wider text-stone-700 bg-stone-100 hover:bg-stone-200 border border-stone-300 rounded px-2 py-1 transition-colors"
      title="Copy assignment code"
    >
      {code}
      {done ? <Check className="h-3.5 w-3.5 text-emerald-600" /> : <Copy className="h-3.5 w-3.5 text-stone-400" />}
    </button>
  );
};

const Stat = ({ icon: Icon, value, label }) => (
  <div className="flex items-center gap-1.5 text-stone-600">
    <Icon className="h-3.5 w-3.5 text-stone-400" />
    <span className="text-[15px] font-medium text-stone-800">{value}</span>
    <span className="text-[12px] text-stone-500">{label}</span>
  </div>
);

const AssignmentCard = ({ a, i }) => (
  <motion.div
    data-testid={`assignment-card-${a.code}`}
    role="button"
    tabIndex={0}
    initial={{ opacity: 0, y: 12 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ delay: i * 0.05, duration: 0.35 }}
    onClick={() => goDashboard(a.id)}
    onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); goDashboard(a.id); } }}
    className="group text-left w-full cursor-pointer bg-white border border-stone-200 hover:border-stone-300 rounded-md p-5 transition-all hover:shadow-[0_2px_20px_rgba(0,0,0,0.05)] focus:outline-none focus:ring-2 focus:ring-[#8C3A2A]/30"
  >
    <div className="flex items-start justify-between gap-3">
      <div className="min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <StatusBadge status={a.status} />
          {a.genre && <span className="text-[11px] text-stone-400">{a.genre}</span>}
        </div>
        <h3 className="text-[17px] font-medium text-stone-900 leading-snug truncate" title={a.title}>
          {a.title}
        </h3>
        {a.purpose && (
          <p className="text-[13px] text-stone-500 mt-1 line-clamp-2 leading-relaxed">{a.purpose}</p>
        )}
      </div>
      <ArrowRight className="h-4 w-4 text-stone-300 group-hover:text-stone-500 group-hover:translate-x-0.5 transition-all shrink-0 mt-1" />
    </div>

    <div className="flex flex-wrap items-center gap-x-5 gap-y-2 mt-4 pt-4 border-t border-stone-100">
      <Stat icon={Users} value={a.student_count} label={a.student_count === 1 ? "student" : "students"} />
      <Stat icon={Activity} value={a.active_count} label="active" />
      {a.gradeLevel != null && <Stat icon={GraduationCap} value={`G${a.gradeLevel}`} label="" />}
      <div className="flex items-center gap-1.5 text-stone-500 ml-auto">
        <Clock className="h-3.5 w-3.5 text-stone-400" />
        <span className="text-[12px]">{a.last_activity ? fmtDate(a.last_activity) : "no activity"}</span>
      </div>
    </div>

    <div className="flex items-center justify-between mt-3">
      <span className="text-[11px] uppercase tracking-widest text-stone-400">join code</span>
      <CopyCode code={a.code} />
    </div>
  </motion.div>
);

export default function TeacherHome() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listTeacherAssignments()
      .then(setData)
      .catch(() => toast.error("Could not load your assignments."))
      .finally(() => setLoading(false));
  }, []);

  const assignments = data?.assignments || [];
  const isEmpty = !loading && assignments.length === 0;

  return (
    <div className="min-h-screen paper-grain" data-testid="teacher-home">
      <Toaster position="top-center" richColors />
      {/* Header */}
      <header className="border-b border-stone-200 bg-white/70 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <Compass className="h-5 w-5" style={{ color: accent }} />
            <div className="leading-tight">
              <div className="text-[15px] font-semibold tracking-tight text-stone-900">Compass</div>
              <div className="text-[11px] uppercase tracking-widest text-stone-400">Teacher workspace</div>
            </div>
          </div>
          <button
            data-testid="create-assignment-button"
            onClick={goCreate}
            className="inline-flex items-center gap-2 text-white text-[14px] font-medium rounded-sm px-4 py-2.5 transition-transform hover:-translate-y-px active:translate-y-0"
            style={{ backgroundColor: accent }}
          >
            <Plus className="h-4 w-4" />
            Create assignment
          </button>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-10">
        {loading && (
          <div className="flex items-center justify-center py-32 text-stone-400" data-testid="teacher-home-loading">
            <Loader2 className="h-6 w-6 animate-spin" />
          </div>
        )}

        {isEmpty && (
          <motion.div
            data-testid="assignment-empty-state"
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center py-24 max-w-xl mx-auto"
          >
            <div className="inline-flex items-center justify-center h-14 w-14 rounded-full bg-stone-100 mb-6">
              <FileText className="h-6 w-6 text-stone-400" />
            </div>
            <h2 className="text-2xl font-medium text-stone-900 tracking-tight">Create your first assignment</h2>
            <p className="text-[15px] text-stone-500 mt-3 leading-relaxed">
              Set the purpose, guidance, and revision expectations. Compass coaches each student toward
              their own writing — you keep authorship with the student.
            </p>
            <button
              data-testid="create-assignment-empty-button"
              onClick={goCreate}
              className="mt-7 inline-flex items-center gap-2 text-white text-[15px] font-medium rounded-sm px-5 py-3 transition-transform hover:-translate-y-px"
              style={{ backgroundColor: accent }}
            >
              <Plus className="h-4 w-4" />
              Create assignment
            </button>
          </motion.div>
        )}

        {!loading && !isEmpty && (
          <>
            <div className="flex items-end justify-between mb-6">
              <div>
                <h1 className="text-2xl font-medium text-stone-900 tracking-tight">Your assignments</h1>
                <p className="text-[13px] text-stone-500 mt-1">
                  {data.assignment_count} assignment{data.assignment_count === 1 ? "" : "s"} · {data.student_total} student
                  {data.student_total === 1 ? "" : "s"} writing
                </p>
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4" data-testid="assignment-grid">
              {assignments.map((a, i) => <AssignmentCard key={a.id} a={a} i={i} />)}
            </div>
          </>
        )}
      </main>
    </div>
  );
}
