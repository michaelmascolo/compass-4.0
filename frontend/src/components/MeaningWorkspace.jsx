import {
  useState,
  useEffect,
  useRef,
  useCallback,
  createContext,
  useContext,
} from "react";
import {
  ReactFlow,
  ReactFlowProvider,
  Background,
  BackgroundVariant,
  Controls,
  useNodesState,
  useEdgesState,
  addEdge,
  useReactFlow,
  Handle,
  Position,
  NodeResizer,
  EdgeLabelRenderer,
  BaseEdge,
  getBezierPath,
  MarkerType,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Toaster, toast } from "sonner";
import {
  ArrowLeft,
  Plus,
  Group as GroupIcon,
  Sparkles,
  MessageSquareQuote,
  X,
  ChevronRight,
  Loader2,
  Trash2,
  StickyNote,
  ArrowRightLeft,
} from "lucide-react";
import {
  getMeaningMap,
  saveMeaningMap,
  coachMeaningMap,
  logMeaningEvents,
} from "@/lib/api";

// ---------------------------------------------------------------------------
// Palette — light, paper-like tints. Objects stay lightweight and movable.
// ---------------------------------------------------------------------------
const COLORS = [
  { name: "paper", bg: "#ffffff", ring: "#e7e5e4" },
  { name: "terracotta", bg: "#f4e3dd", ring: "#e0c6bd" },
  { name: "sage", bg: "#e7ede4", ring: "#cdd8c9" },
  { name: "sky", bg: "#e1e9ef", ring: "#c6d6e0" },
  { name: "sand", bg: "#f1ebde", ring: "#ded2bb" },
].map((c) => ({ ...c, bg: c.bg.replace(" ", "") }));

const EDGE_STROKE = "#a8a29e";
const OBJ_W = 200;
const OBJ_H = 92;

const MeaningCtx = createContext(null);

// ===========================================================================
// Custom node — a "Meaning Object": a small, lightweight note/card.
// ===========================================================================
function MeaningObjectNode({ id, data, selected }) {
  const ctx = useContext(MeaningCtx);
  const { editingId, setEditingId, updateObject, deleteObject } = ctx;
  const editing = editingId === id;
  const [notesOpen, setNotesOpen] = useState(!!data.notes);
  const focusSnap = useRef("");
  const textRef = useRef(null);

  useEffect(() => {
    if (editing && textRef.current) {
      textRef.current.focus();
      textRef.current.select?.();
    }
  }, [editing]);

  const color = data.color || "#ffffff";

  return (
    <div
      data-testid={`meaning-object-${id}`}
      className="group/obj relative h-full w-full"
    >
      <NodeResizer
        isVisible={selected}
        minWidth={150}
        minHeight={70}
        lineClassName="!border-[#8C3A2A]/40"
        handleClassName="!h-2 !w-2 !bg-white !border !border-[#8C3A2A]/60"
      />
      <Handle
        type="target"
        position={Position.Left}
        className="!h-3 !w-3 !border-2 !border-stone-400 !bg-white !opacity-70 transition hover:!border-[#8C3A2A] hover:!opacity-100"
      />
      <div
        className="flex h-full flex-col overflow-y-auto nowheel rounded-md px-3 py-2.5 transition-shadow"
        style={{
          background: color,
          border: `1px solid ${selected ? "#8C3A2A" : "#e7e5e4"}`,
          boxShadow: selected ? "0 1px 0 rgba(140,58,42,0.12)" : "none",
          minHeight: OBJ_H,
        }}
      >
        {editing ? (
          <textarea
            ref={textRef}
            data-testid={`meaning-object-input-${id}`}
            className="nodrag nowheel w-full resize-none bg-transparent text-[13px] leading-snug text-stone-900 outline-none placeholder:text-stone-400"
            rows={3}
            defaultValue={data.text || ""}
            onFocus={(e) => (focusSnap.current = e.target.value)}
            onKeyDown={(e) => e.stopPropagation()}
            onBlur={(e) => {
              const val = e.target.value;
              updateObject(
                id,
                { text: val },
                val !== focusSnap.current
                  ? { event: "edited_object", data: { field: "text" }, meaningful: true }
                  : null
              );
              setEditingId(null);
            }}
            placeholder="a thought, claim, question, example…"
          />
        ) : (
          <div
            data-testid={`meaning-object-text-${id}`}
            onDoubleClick={(e) => {
              e.stopPropagation();
              setEditingId(id);
            }}
            className="min-h-[42px] cursor-text whitespace-pre-wrap text-[13px] leading-snug text-stone-900"
          >
            {data.text ? (
              data.text
            ) : (
              <span className="italic text-stone-400">double-click to write…</span>
            )}
          </div>
        )}

        {(notesOpen || data.notes) && (
          <textarea
            data-testid={`meaning-object-notes-${id}`}
            className="nodrag nowheel mt-2 w-full resize-none border-t border-stone-200/70 bg-transparent pt-1.5 text-[11px] leading-snug text-stone-500 outline-none placeholder:text-stone-400"
            rows={2}
            defaultValue={data.notes || ""}
            onFocus={(e) => (focusSnap.current = e.target.value)}
            onKeyDown={(e) => e.stopPropagation()}
            onBlur={(e) => {
              const val = e.target.value;
              updateObject(
                id,
                { notes: val },
                val !== focusSnap.current
                  ? { event: "edited_object", data: { field: "notes" } }
                  : null
              );
            }}
            placeholder="a note to yourself (optional)…"
          />
        )}
      </div>

      {/* Lightweight toolbar — only when selected. No heavy chrome. */}
      {selected && (
        <div className="nodrag absolute -top-9 left-0 flex items-center gap-1.5 rounded-sm border border-stone-200 bg-white px-1.5 py-1 shadow-sm">
          {COLORS.map((c) => (
            <button
              key={c.name}
              data-testid={`meaning-object-color-${c.name}-${id}`}
              onClick={() =>
                updateObject(id, { color: c.bg }, { event: "edited_object", data: { field: "color" } })
              }
              title={c.name}
              className="h-3.5 w-3.5 rounded-full transition-transform hover:scale-110"
              style={{ background: c.bg, border: `1px solid ${c.ring}` }}
            />
          ))}
          <span className="mx-0.5 h-4 w-px bg-stone-200" />
          <button
            data-testid={`meaning-object-notes-toggle-${id}`}
            onClick={() => setNotesOpen((v) => !v)}
            title="Add a note"
            className="text-stone-400 hover:text-stone-700"
          >
            <StickyNote className="h-3.5 w-3.5" />
          </button>
          <button
            data-testid={`meaning-object-delete-${id}`}
            onClick={() => deleteObject(id)}
            title="Delete"
            className="text-stone-400 hover:text-[#8C3A2A]"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      <Handle
        type="source"
        position={Position.Right}
        className="!h-3 !w-3 !border-2 !border-stone-400 !bg-white !opacity-70 transition hover:!border-[#8C3A2A] hover:!opacity-100"
      />
    </div>
  );
}

// ===========================================================================
// Custom node — a spatial Group container. Very light boundary; suggests
// organization without feeling rigid. Objects drift in and out freely.
// ===========================================================================
function GroupNode({ id, data, selected }) {
  const ctx = useContext(MeaningCtx);
  const { editingId, setEditingId, updateObject, deleteObject } = ctx;
  const editing = editingId === id;
  const inputRef = useRef(null);
  const snap = useRef("");

  useEffect(() => {
    if (editing && inputRef.current) inputRef.current.focus();
  }, [editing]);

  return (
    <div
      data-testid={`meaning-group-${id}`}
      className="h-full w-full rounded-lg"
      style={{
        background: "rgba(240,237,230,0.45)",
        border: `1px dashed ${selected ? "#c9a99f" : "#d6d3d1"}`,
      }}
    >
      <NodeResizer
        isVisible={selected}
        minWidth={200}
        minHeight={140}
        lineClassName="!border-stone-300"
        handleClassName="!h-2 !w-2 !bg-white !border !border-stone-400"
      />
      <div className="absolute left-3 top-2 flex items-center gap-2">
        {editing ? (
          <input
            ref={inputRef}
            data-testid={`meaning-group-input-${id}`}
            className="nodrag bg-transparent text-[11px] font-mono-panel uppercase tracking-[0.18em] text-stone-500 outline-none"
            defaultValue={data.label || ""}
            onFocus={(e) => (snap.current = e.target.value)}
            onKeyDown={(e) => {
              e.stopPropagation();
              if (e.key === "Enter") e.currentTarget.blur();
            }}
            onBlur={(e) => {
              const val = e.target.value;
              updateObject(
                id,
                { label: val },
                val !== snap.current ? { event: "edited_object", data: { field: "group_label" } } : null
              );
              setEditingId(null);
            }}
            placeholder="name this cluster…"
          />
        ) : (
          <span
            data-testid={`meaning-group-label-${id}`}
            onDoubleClick={(e) => {
              e.stopPropagation();
              setEditingId(id);
            }}
            className="cursor-text text-[11px] font-mono-panel uppercase tracking-[0.18em] text-stone-400"
          >
            {data.label || "cluster"}
          </span>
        )}
        {selected && (
          <button
            data-testid={`meaning-group-delete-${id}`}
            onClick={() => deleteObject(id)}
            className="nodrag text-stone-300 hover:text-[#8C3A2A]"
            title="Remove cluster (ideas stay)"
          >
            <X className="h-3 w-3" />
          </button>
        )}
      </div>
    </div>
  );
}

// ===========================================================================
// Custom edge — a subtle connection with an editable relationship label and a
// directed/undirected toggle. Stays visually quiet.
// ===========================================================================
function EditableEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
  markerEnd,
  selected,
}) {
  const ctx = useContext(MeaningCtx);
  const { updateEdgeLabel, toggleEdgeDirected, deleteEdge } = ctx;
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        markerEnd={markerEnd}
        style={{ stroke: selected ? "#8C3A2A" : EDGE_STROKE, strokeWidth: 1.5 }}
      />
      <EdgeLabelRenderer>
        <div
          className="nodrag nopan absolute flex items-center gap-1"
          style={{ transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)` }}
          data-testid={`meaning-edge-${id}`}
        >
          <input
            data-testid={`meaning-edge-label-${id}`}
            className="w-[92px] rounded-sm border border-stone-200 bg-[#faf9f6]/95 px-1.5 py-0.5 text-center text-[10px] text-stone-600 outline-none placeholder:text-stone-300 focus:border-[#8C3A2A]"
            defaultValue={data?.label || ""}
            onKeyDown={(e) => e.stopPropagation()}
            onBlur={(e) => updateEdgeLabel(id, e.target.value)}
            placeholder="relationship"
          />
          <button
            data-testid={`meaning-edge-direction-${id}`}
            onClick={() => toggleEdgeDirected(id)}
            title={data?.directed ? "Directed — click for mutual" : "Undirected — click for arrow"}
            className={`rounded-sm border px-1 py-0.5 ${
              data?.directed
                ? "border-[#8C3A2A]/40 text-[#8C3A2A]"
                : "border-stone-200 text-stone-400"
            }`}
          >
            <ArrowRightLeft className="h-2.5 w-2.5" />
          </button>
          {selected && (
            <button
              data-testid={`meaning-edge-delete-${id}`}
              onClick={() => deleteEdge(id)}
              className="text-stone-300 hover:text-[#8C3A2A]"
              title="Remove connection"
            >
              <X className="h-3 w-3" />
            </button>
          )}
        </div>
      </EdgeLabelRenderer>
    </>
  );
}

const nodeTypes = { meaningObject: MeaningObjectNode, group: GroupNode };
const edgeTypes = { editable: EditableEdge };

const arrowMarker = { type: MarkerType.ArrowClosed, color: EDGE_STROKE, width: 16, height: 16 };

// ---------------------------------------------------------------------------
// Serialization between React Flow state and the backend meaning-map schema.
// ---------------------------------------------------------------------------
function toBackend(nodes, edges) {
  const objects = [];
  const groups = [];
  for (const n of nodes) {
    if (n.type === "group") {
      groups.push({
        id: n.id,
        label: n.data?.label || "",
        color: n.data?.color || "",
        x: n.position.x,
        y: n.position.y,
        width: parseFloat(n.style?.width) || n.width || n.measured?.width || 260,
        height: parseFloat(n.style?.height) || n.height || n.measured?.height || 180,
      });
    } else {
      const w = parseFloat(n.style?.width) || n.width || n.measured?.width || OBJ_W;
      const h = parseFloat(n.style?.height) || n.height || n.measured?.height || 0;
      objects.push({
        id: n.id,
        text: n.data?.text || "",
        notes: n.data?.notes || "",
        color: n.data?.color || "#ffffff",
        group_id: n.data?.group_id || "",
        x: n.position.x,
        y: n.position.y,
        width: w,
        ...(h ? { height: h } : {}),
      });
    }
  }
  const connections = edges.map((e) => ({
    id: e.id,
    from_id: e.source,
    to_id: e.target,
    directed: !!e.data?.directed,
    label: e.data?.label || "",
  }));
  return { objects, connections, groups };
}

function fromBackend(map) {
  const groupNodes = (map.groups || []).map((g) => ({
    id: g.id,
    type: "group",
    position: { x: g.x || 0, y: g.y || 0 },
    data: { label: g.label || "", color: g.color || "" },
    style: { width: g.width || 260, height: g.height || 180 },
    zIndex: 0,
  }));
  const objNodes = (map.objects || []).map((o) => ({
    id: o.id,
    type: "meaningObject",
    position: { x: o.x || 0, y: o.y || 0 },
    data: {
      text: o.text || "",
      notes: o.notes || "",
      color: o.color || "#ffffff",
      group_id: o.group_id || "",
    },
    style: { width: o.width || OBJ_W, ...(o.height ? { height: o.height } : {}) },
    zIndex: 1,
  }));
  const edges = (map.connections || []).map((c) => ({
    id: c.id,
    source: c.from_id,
    target: c.to_id,
    type: "editable",
    data: { directed: !!c.directed, label: c.label || "" },
    markerEnd: c.directed ? arrowMarker : undefined,
  }));
  return { nodes: [...groupNodes, ...objNodes], edges };
}

// Globally-unique, immutable-for-life IDs for semantic objects/groups/connections.
// A readable prefix (obj_/grp_/edge_) is kept for legibility; the body is a UUID.
// Contract: an id, once assigned, is NEVER regenerated or migrated — future
// workspaces (Writing Plan, Draft, Revision, Teacher tools, analytics) reference
// these ids and must not duplicate the semantic object. ("One semantic object,
// many representations.") Existing legacy ids are preserved on load, never rewritten.
const uuid = () =>
  typeof crypto !== "undefined" && crypto.randomUUID
    ? crypto.randomUUID()
    : `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
const newId = (p) => `${p}_${uuid()}`;

// ===========================================================================
// Inner canvas (inside ReactFlowProvider).
// ===========================================================================
function Flow({ sessionId }) {
  const rf = useReactFlow();
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [mapId, setMapId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState(null);

  // Coach state
  const [observations, setObservations] = useState([]);
  const [dismissed, setDismissed] = useState(new Set());
  const [coachOpen, setCoachOpen] = useState(true);
  const [coachBusy, setCoachBusy] = useState(false);
  const [replyText, setReplyText] = useState("");
  const threadEndRef = useRef(null);

  // Refs for cadence + queues
  const mapIdRef = useRef(null);
  const saveTimer = useRef(null);
  const eventQueue = useRef([]);
  const flushTimer = useRef(null);
  const dragRef = useRef(null);
  // Ambient coach cadence: settle 20s after a meaningful change, cap 1 / 90s.
  const pendingObserve = useRef(false);
  const lastChangeAt = useRef(0);
  const lastCoachAt = useRef(0);

  // ---- event logging (append-only thinking trace) ----
  const flushEvents = useCallback(async () => {
    if (!mapIdRef.current || eventQueue.current.length === 0) return;
    const batch = eventQueue.current.splice(0, eventQueue.current.length);
    try {
      await logMeaningEvents(mapIdRef.current, batch);
    } catch (e) {
      // non-critical; re-queue for the next flush
      eventQueue.current.unshift(...batch);
    }
  }, []);

  const logEvent = useCallback(
    (type, data) => {
      eventQueue.current.push({ type, at: new Date().toISOString(), data: data || {} });
      if (flushTimer.current) clearTimeout(flushTimer.current);
      flushTimer.current = setTimeout(flushEvents, 1500);
    },
    [flushEvents]
  );

  const markChange = useCallback(() => {
    pendingObserve.current = true;
    lastChangeAt.current = Date.now();
  }, []);

  // ---- autosave (debounced full-map PUT) ----
  const saveNow = useCallback(async () => {
    if (!mapIdRef.current) return;
    const payload = toBackend(rf.getNodes(), rf.getEdges());
    try {
      await saveMeaningMap(mapIdRef.current, payload);
    } catch (e) {
      /* transient; next change re-saves */
    }
  }, [rf]);

  const scheduleSave = useCallback(() => {
    if (saveTimer.current) clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(saveNow, 900);
  }, [saveNow]);

  // ---- object/group/edge mutators (context) ----
  const updateObject = useCallback(
    (id, patch, opts) => {
      setNodes((ns) => ns.map((n) => (n.id === id ? { ...n, data: { ...n.data, ...patch } } : n)));
      if (opts?.event) logEvent(opts.event, { id, ...(opts.data || {}) });
      if (opts?.meaningful) markChange();
      scheduleSave();
    },
    [setNodes, logEvent, markChange, scheduleSave]
  );

  const deleteObject = useCallback(
    (id) => {
      rf.deleteElements({ nodes: [{ id }] });
    },
    [rf]
  );

  const deleteEdge = useCallback(
    (id) => {
      rf.deleteElements({ edges: [{ id }] });
    },
    [rf]
  );

  const updateEdgeLabel = useCallback(
    (id, label) => {
      setEdges((es) => es.map((e) => (e.id === id ? { ...e, data: { ...e.data, label } } : e)));
      logEvent("edited_connection", { id, field: "label" });
      scheduleSave();
    },
    [setEdges, logEvent, scheduleSave]
  );

  const toggleEdgeDirected = useCallback(
    (id) => {
      setEdges((es) =>
        es.map((e) => {
          if (e.id !== id) return e;
          const directed = !e.data?.directed;
          return { ...e, data: { ...e.data, directed }, markerEnd: directed ? arrowMarker : undefined };
        })
      );
      logEvent("edited_connection", { id, field: "directed" });
      scheduleSave();
    },
    [setEdges, logEvent, scheduleSave]
  );

  const ctxValue = {
    editingId,
    setEditingId,
    updateObject,
    deleteObject,
    updateEdgeLabel,
    toggleEdgeDirected,
    deleteEdge,
  };

  // ---- initial load ----
  useEffect(() => {
    let alive = true;
    if (!sessionId) {
      setLoading(false);
      return;
    }
    getMeaningMap(sessionId)
      .then((map) => {
        if (!alive) return;
        mapIdRef.current = map.id;
        setMapId(map.id);
        const { nodes: n, edges: e } = fromBackend(map);
        setNodes(n);
        setEdges(e);
        setObservations([...(map.coach_log || [])]);
      })
      .catch(() => toast.error("Could not open the Meaning Workspace."))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  // ---- coach firing ----
  const fireCoach = useCallback(
    async (trigger) => {
      if (!mapIdRef.current || coachBusy) return;
      pendingObserve.current = false;
      lastCoachAt.current = Date.now();
      if (trigger === "on_demand") logEvent("requested_coach_help", {});
      setCoachBusy(true);
      try {
        await flushEvents();
        await saveNow(); // ensure the snapshot the coach reads is current
        const note = await coachMeaningMap(mapIdRef.current, trigger);
        setObservations((o) => [...o, note]);
        logEvent("coach_observation_received", { trigger, note_id: note.id, kind: note.kind });
      } catch (e) {
        if (trigger === "on_demand") toast.error("The coach couldn't respond just now.");
      } finally {
        setCoachBusy(false);
      }
    },
    [coachBusy, logEvent, flushEvents, saveNow]
  );

  // ---- learner engages the coach (reply) ----
  const sendReply = useCallback(async () => {
    const msg = replyText.trim();
    if (!msg || !mapIdRef.current || coachBusy) return;
    setReplyText("");
    lastCoachAt.current = Date.now();
    const localId = `local_${uuid()}`;
    // optimistic learner bubble
    setObservations((o) => [
      ...o,
      { id: localId, kind: "learner", text: msg, trigger: "reply", created_at: new Date().toISOString() },
    ]);
    logEvent("answered_coach", {});
    setCoachBusy(true);
    try {
      await flushEvents();
      await saveNow();
      const note = await coachMeaningMap(mapIdRef.current, "reply", msg);
      setObservations((o) => {
        // replace the optimistic learner bubble with the server-persisted one, then add the coach reply
        const arr = o.filter((x) => x.id !== localId);
        if (note.learner_note) arr.push(note.learner_note);
        else arr.push({ id: localId, kind: "learner", text: msg, trigger: "reply", created_at: new Date().toISOString() });
        arr.push(note);
        return arr;
      });
      logEvent("coach_observation_received", { trigger: "reply", note_id: note.id, kind: note.kind });
    } catch (e) {
      toast.error("The coach couldn't respond just now.");
    } finally {
      setCoachBusy(false);
    }
  }, [replyText, coachBusy, logEvent, flushEvents, saveNow]);

  // ---- ambient cadence loop ----
  useEffect(() => {
    const t = setInterval(() => {
      const now = Date.now();
      if (
        pendingObserve.current &&
        now - lastChangeAt.current >= 20000 &&
        now - lastCoachAt.current >= 90000 &&
        !coachBusy
      ) {
        fireCoach("ambient");
      }
    }, 3000);
    return () => clearInterval(t);
  }, [fireCoach, coachBusy]);

  // periodic event flush safety net
  useEffect(() => {
    const t = setInterval(flushEvents, 5000);
    return () => {
      clearInterval(t);
      flushEvents();
    };
  }, [flushEvents]);

  // auto-scroll the coach thread to the newest message
  useEffect(() => {
    threadEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [observations, coachBusy]);

  // ---- canvas interactions ----
  const onConnect = useCallback(
    (params) => {
      const id = newId("edge");
      setEdges((eds) =>
        addEdge(
          { ...params, id, type: "editable", data: { directed: true, label: "" }, markerEnd: arrowMarker },
          eds
        )
      );
      logEvent("created_connection", { id, from_id: params.source, to_id: params.target });
      markChange();
      scheduleSave();
    },
    [setEdges, logEvent, markChange, scheduleSave]
  );

  const addObjectAt = useCallback(
    (flowPos) => {
      const id = newId("obj");
      const node = {
        id,
        type: "meaningObject",
        position: flowPos,
        data: { text: "", notes: "", color: "#ffffff", group_id: "" },
        style: { width: OBJ_W },
        zIndex: 1,
      };
      setNodes((ns) => [...ns, node]);
      setEditingId(id);
      logEvent("created_object", { id });
      markChange();
      scheduleSave();
    },
    [setNodes, logEvent, markChange, scheduleSave]
  );

  const addObjectCenter = useCallback(() => {
    const c = rf.screenToFlowPosition({
      x: window.innerWidth / 2,
      y: window.innerHeight / 2,
    });
    addObjectAt({ x: c.x - OBJ_W / 2, y: c.y - OBJ_H / 2 });
  }, [rf, addObjectAt]);

  const addGroup = useCallback(() => {
    const id = newId("grp");
    const c = rf.screenToFlowPosition({ x: window.innerWidth / 2, y: window.innerHeight / 2 });
    setNodes((ns) => [
      {
        id,
        type: "group",
        position: { x: c.x - 150, y: c.y - 110 },
        data: { label: "", color: "" },
        style: { width: 300, height: 220 },
        zIndex: 0,
      },
      ...ns,
    ]);
    logEvent("created_group", { id });
    markChange();
    scheduleSave();
  }, [rf, setNodes, logEvent, markChange, scheduleSave]);

  const onPaneDoubleClick = useCallback(
    (e) => {
      if (!e.target.classList?.contains("react-flow__pane")) return;
      const pos = rf.screenToFlowPosition({ x: e.clientX, y: e.clientY });
      addObjectAt({ x: pos.x - OBJ_W / 2, y: pos.y - OBJ_H / 2 });
    },
    [rf, addObjectAt]
  );

  // group membership by spatial containment (loose, non-parent grouping)
  const containingGroup = useCallback(
    (node) => {
      const w = node.measured?.width || OBJ_W;
      const h = node.measured?.height || OBJ_H;
      const cx = node.position.x + w / 2;
      const cy = node.position.y + h / 2;
      for (const g of rf.getNodes().filter((n) => n.type === "group")) {
        const gw = parseFloat(g.style?.width) || g.width || g.measured?.width || 300;
        const gh = parseFloat(g.style?.height) || g.height || g.measured?.height || 220;
        if (cx >= g.position.x && cx <= g.position.x + gw && cy >= g.position.y && cy <= g.position.y + gh)
          return g.id;
      }
      return "";
    },
    [rf]
  );

  const onNodeDragStart = useCallback(
    (_e, node) => {
      if (node.type === "group") {
        const members = {};
        rf.getNodes().forEach((n) => {
          if (n.data?.group_id === node.id) members[n.id] = { ...n.position };
        });
        dragRef.current = { id: node.id, start: { ...node.position }, members };
      }
    },
    [rf]
  );

  const onNodeDrag = useCallback(
    (_e, node) => {
      // moving a cluster carries its members along
      if (node.type === "group" && dragRef.current?.id === node.id) {
        const dx = node.position.x - dragRef.current.start.x;
        const dy = node.position.y - dragRef.current.start.y;
        const m = dragRef.current.members;
        setNodes((ns) =>
          ns.map((n) =>
            m[n.id] ? { ...n, position: { x: m[n.id].x + dx, y: m[n.id].y + dy } } : n
          )
        );
      }
    },
    [setNodes]
  );

  const onNodeDragStop = useCallback(
    (_e, node) => {
      if (node.type === "meaningObject") {
        const prev = node.data?.group_id || "";
        const gid = containingGroup(node);
        logEvent("moved_object", { id: node.id, x: Math.round(node.position.x), y: Math.round(node.position.y) });
        if (gid !== prev) {
          setNodes((ns) =>
            ns.map((n) => (n.id === node.id ? { ...n, data: { ...n.data, group_id: gid } } : n))
          );
          logEvent(gid ? "grouped_object" : "ungrouped_object", { id: node.id, group_id: gid });
          markChange();
        }
      } else if (node.type === "group") {
        logEvent("moved_group", { id: node.id });
      }
      dragRef.current = null;
      scheduleSave();
    },
    [containingGroup, setNodes, logEvent, markChange, scheduleSave]
  );

  const onNodesDelete = useCallback(
    (deleted) => {
      deleted.forEach((n) =>
        logEvent(n.type === "group" ? "deleted_group" : "deleted_object", { id: n.id })
      );
      markChange();
      scheduleSave();
    },
    [logEvent, markChange, scheduleSave]
  );

  const onEdgesDelete = useCallback(
    (deleted) => {
      deleted.forEach((e) => logEvent("deleted_connection", { id: e.id }));
      markChange();
      scheduleSave();
    },
    [logEvent, markChange, scheduleSave]
  );

  const dismissObservation = useCallback(
    (id) => {
      setDismissed((s) => new Set(s).add(id));
      logEvent("dismissed_coach_observation", { note_id: id });
    },
    [logEvent]
  );

  const visibleObs = observations.filter((o) => !dismissed.has(o.id));

  return (
    <div className="relative h-screen w-screen overflow-hidden bg-[#faf9f6]">
      <Toaster position="top-center" richColors />

      {/* Top-left: return + creation tools. Quiet, editorial. */}
      <div className="absolute left-4 top-4 z-20 flex items-center gap-2">
        <button
          data-testid="meaning-back-button"
          onClick={() => (window.location.href = "?app")}
          className="inline-flex items-center gap-1.5 rounded-sm border border-stone-300 bg-white/90 px-3 py-2 text-[11px] font-mono-panel uppercase tracking-[0.15em] text-stone-500 backdrop-blur-sm transition-colors hover:text-[#8C3A2A]"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Writing
        </button>
        <div className="flex items-center gap-1 rounded-sm border border-stone-300 bg-white/90 px-1.5 py-1 backdrop-blur-sm">
          <button
            data-testid="meaning-add-object-button"
            onClick={addObjectCenter}
            className="inline-flex items-center gap-1.5 rounded-sm px-2.5 py-1.5 text-[11px] font-mono-panel uppercase tracking-[0.14em] text-stone-600 transition-colors hover:bg-stone-100 hover:text-[#8C3A2A]"
          >
            <Plus className="h-3.5 w-3.5" /> Idea
          </button>
          <span className="h-4 w-px bg-stone-200" />
          <button
            data-testid="meaning-add-group-button"
            onClick={addGroup}
            className="inline-flex items-center gap-1.5 rounded-sm px-2.5 py-1.5 text-[11px] font-mono-panel uppercase tracking-[0.14em] text-stone-600 transition-colors hover:bg-stone-100 hover:text-[#8C3A2A]"
          >
            <GroupIcon className="h-3.5 w-3.5" /> Cluster
          </button>
        </div>
      </div>

      {/* Title watermark — idea-centered, not document-centered. */}
      <div className="pointer-events-none absolute left-1/2 top-4 z-10 -translate-x-1/2 text-center">
        <p className="font-serif-display text-lg text-stone-400">Meaning Workspace</p>
      </div>

      {loading ? (
        <div className="flex h-full items-center justify-center">
          <p className="font-serif-display text-2xl text-stone-400">Opening the canvas…</p>
        </div>
      ) : (
        <MeaningCtx.Provider value={ctxValue}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeDragStart={onNodeDragStart}
            onNodeDrag={onNodeDrag}
            onNodeDragStop={onNodeDragStop}
            onNodesDelete={onNodesDelete}
            onEdgesDelete={onEdgesDelete}
            onDoubleClick={onPaneDoubleClick}
            nodeTypes={nodeTypes}
            edgeTypes={edgeTypes}
            zoomOnDoubleClick={false}
            fitView
            proOptions={{ hideAttribution: true }}
            defaultEdgeOptions={{ type: "editable" }}
          >
            <Background variant={BackgroundVariant.Dots} gap={28} size={1} color="#e0ddd5" />
            <Controls showInteractive={false} className="!shadow-none" />
          </ReactFlow>
        </MeaningCtx.Provider>
      )}

      {/* Empty-state nudge over the canvas. */}
      {!loading && nodes.length === 0 && (
        <div className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center">
          <div className="text-center">
            <p className="font-serif-display text-2xl text-stone-400">
              Put a thought down to begin.
            </p>
            <p className="mt-2 text-sm text-stone-400">
              Double-click anywhere, or press <span className="font-mono-panel">Idea</span>. Drag to
              arrange. Draw lines between ideas. Nothing here is permanent.
            </p>
          </div>
        </div>
      )}

      {/* ---- Coach side rail (right). Collapsible, never dominant. ---- */}
      <div
        className={`absolute right-0 top-0 z-20 flex h-full flex-col transition-transform ${
          coachOpen ? "translate-x-0" : "translate-x-[calc(100%-2.75rem)]"
        }`}
        data-testid="meaning-coach-rail"
      >
        <div className="flex h-full">
          {/* spine / toggle */}
          <button
            data-testid="meaning-coach-toggle"
            onClick={() => setCoachOpen((v) => !v)}
            className="flex w-11 shrink-0 flex-col items-center gap-2 border-l border-stone-200 bg-[#faf9f6]/95 py-4 backdrop-blur-sm"
            title={coachOpen ? "Hide coach" : "Show coach"}
          >
            <ChevronRight
              className={`h-4 w-4 text-stone-400 transition-transform ${coachOpen ? "" : "rotate-180"}`}
            />
            <span
              className="mt-1 text-[10px] font-mono-panel uppercase tracking-[0.2em] text-stone-400"
              style={{ writingMode: "vertical-rl" }}
            >
              Coach
            </span>
          </button>

          <div className="flex w-80 flex-col border-l border-stone-200 bg-white/95 backdrop-blur-sm">
            <div className="flex items-center justify-between border-b border-stone-200 px-4 py-3">
              <span className="flex items-center gap-2 font-serif-display text-base text-stone-700">
                <MessageSquareQuote className="h-4 w-4 text-[#8C3A2A]" />
                Thinking coach
              </span>
              <button
                data-testid="meaning-help-button"
                onClick={() => fireCoach("on_demand")}
                disabled={coachBusy}
                className="inline-flex items-center gap-1.5 rounded-sm bg-[#8C3A2A] px-2.5 py-1.5 text-[10px] font-mono-panel uppercase tracking-[0.14em] text-white transition-colors hover:bg-[#6B2C20] disabled:opacity-50"
              >
                {coachBusy ? (
                  <Loader2 className="h-3 w-3 animate-spin" />
                ) : (
                  <Sparkles className="h-3 w-3" />
                )}
                Help me think
              </button>
            </div>

            <p className="border-b border-stone-100 px-4 py-2 text-[11px] leading-relaxed text-stone-400">
              I only notice and ask. I won't organize your ideas or tell you what to write — that
              thinking is yours.
            </p>

            <div
              className="flex-1 space-y-3 overflow-y-auto px-4 py-4 custom-scroll"
              data-testid="meaning-coach-observations"
            >
              {visibleObs.length === 0 && !coachBusy && (
                <p className="text-xs italic leading-relaxed text-stone-400">
                  Observations will appear here as your map grows — ask me anytime with “Help me
                  think,” and reply below to think it through together.
                </p>
              )}
              {visibleObs.map((o, i) =>
                o.kind === "learner" ? (
                  <div
                    key={o.id || i}
                    data-testid={`meaning-learner-message-${i}`}
                    className="ml-8 rounded-sm bg-stone-900 px-3 py-2 text-[13px] leading-relaxed text-stone-50"
                  >
                    {o.text}
                    <div className="mt-1 text-right text-[9px] font-mono-panel uppercase tracking-[0.14em] text-stone-400">
                      You
                      {o.created_at
                        ? " · " +
                          new Date(o.created_at).toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                          })
                        : ""}
                    </div>
                  </div>
                ) : (
                  <div
                    key={o.id || i}
                    data-testid={`meaning-observation-${i}`}
                    className="group/obs mr-4 rounded-sm border-l-2 border-[#8C3A2A]/50 bg-[#faf9f6] py-2 pl-3 pr-2"
                  >
                    <div className="mb-1 flex items-center justify-between">
                      <span className="text-[9px] font-mono-panel uppercase tracking-[0.16em] text-stone-400">
                        {o.kind === "question" ? "Question" : "Observation"}
                        {o.trigger === "on_demand" ? " · on request" : ""}
                        {" · "}
                        {o.created_at
                          ? new Date(o.created_at).toLocaleTimeString([], {
                              hour: "2-digit",
                              minute: "2-digit",
                            })
                          : ""}
                      </span>
                      <button
                        data-testid={`meaning-observation-dismiss-${i}`}
                        onClick={() => dismissObservation(o.id)}
                        className="text-stone-300 opacity-0 transition-opacity hover:text-stone-600 group-hover/obs:opacity-100"
                        title="Set aside (kept in history)"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </div>
                    <p className="text-[13px] leading-relaxed text-stone-700">{o.text}</p>
                  </div>
                )
              )}
              {coachBusy && (
                <div className="flex items-center gap-2 text-xs text-stone-400">
                  <Loader2 className="h-3.5 w-3.5 animate-spin text-[#8C3A2A]" /> Thinking with you…
                </div>
              )}
              <div ref={threadEndRef} />
            </div>

            {/* Reply — think it through with the coach. Never mutates the map. */}
            <div className="border-t border-stone-200 p-3">
              <div className="flex items-end gap-2">
                <textarea
                  data-testid="meaning-coach-reply-input"
                  value={replyText}
                  onChange={(e) => setReplyText(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      sendReply();
                    }
                  }}
                  rows={2}
                  placeholder="Reply to your coach / think aloud…"
                  className="flex-1 resize-none rounded-sm border border-stone-300 bg-[#faf9f6] px-2.5 py-1.5 text-[13px] text-stone-900 outline-none placeholder:text-stone-400 focus:border-[#8C3A2A]"
                />
                <button
                  data-testid="meaning-coach-reply-send"
                  onClick={sendReply}
                  disabled={!replyText.trim() || coachBusy}
                  className="shrink-0 rounded-sm bg-stone-900 px-3 py-2 text-xs text-white transition-colors hover:bg-stone-700 disabled:opacity-40"
                >
                  Send
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function MeaningWorkspace({ sessionId }) {
  if (!sessionId) {
    return (
      <div className="flex h-screen items-center justify-center bg-[#faf9f6]">
        <div className="text-center">
          <p className="font-serif-display text-2xl text-stone-500">No session open.</p>
          <button
            onClick={() => (window.location.href = "?app")}
            data-testid="meaning-no-session-back"
            className="mt-4 rounded-sm bg-[#8C3A2A] px-5 py-2.5 text-sm text-white hover:bg-[#6B2C20]"
          >
            Go to the studio
          </button>
        </div>
      </div>
    );
  }
  return (
    <ReactFlowProvider>
      <Flow sessionId={sessionId} />
    </ReactFlowProvider>
  );
}
