"""P0 LATENCY DIAGNOSIS (read-only instrumentation; no production code changed).

Monkeypatches LlmChat.send_message to record, per LLM call on the critical path:
  call type (from session_id prefix) · model · prompt chars · output chars · wall seconds
Then drives ONE representative learner turn through the REAL engine `functional_v3.run()`
for each major mode (conceptual-develop, structural-selection, sentence-craft) and reports:
  - per-call breakdown (sequential LLM calls)
  - total run() wall time
  - non-LLM remainder (state load + audit/DB writes + deterministic python + persistence)
So we can separate "production Compass runtime" from "everything else".

Run: cd /app/backend && set -a && source .env && set +a && python tests/latency_profile.py
"""
import asyncio, sys, time, json
sys.path.insert(0, "/app/backend")
import httpx
from emergentintegrations.llm.chat import LlmChat
import functional_v3 as fv3
import compass_foundation as cf

API = "http://localhost:8001/api"

# ---- monkeypatch the LLM client to time every call ----
_orig_send = LlmChat.send_message
_CALLS = []  # per-turn accumulator (reset before each turn)

async def _timed_send(self, message):
    sid = getattr(self, "session_id", "?")
    ctype = sid.rsplit("-", 5)[0] if "-" in sid else sid  # strip the uuid tail
    # normalize known prefixes
    for pref in ("fn-sel", "rp5-dlg", "rp5-close", "dco-tail", "contract-judge",
                 "sentence-craft", "canon-sel", "rp5-sel"):
        if sid.startswith(pref):
            ctype = pref; break
    model = getattr(self, "model_name", None) or getattr(self, "_model", "?")
    prompt_chars = len(getattr(message, "text", "") or "")
    t0 = time.perf_counter()
    out = await _orig_send(self, message)
    dt = time.perf_counter() - t0
    _CALLS.append({"call": ctype, "model": str(model), "prompt_chars": prompt_chars,
                   "out_chars": len(out or ""), "sec": round(dt, 2)})
    return out

LlmChat.send_message = _timed_send


THIN = ("I think homework is bad. It makes students tired and they do not like it. "
        "Schools should give less homework.")

SPRAWL = (
    "Homework harms students in many ways and schools should reduce it. When students get too much "
    "homework they lose sleep, and sleep is essential for memory consolidation and the brain forms "
    "long-term memories during deep sleep cycles. Also, homework creates family stress because parents "
    "end up fighting with children about finishing it, which damages relationships at home. Furthermore, "
    "wealthy students have quiet study spaces and tutors while poorer students do not, so homework widens "
    "inequality between socioeconomic groups. There is also the motivation problem: research on intrinsic "
    "motivation shows that excessive external tasks undermine a child's natural curiosity and love of "
    "learning, replacing it with compliance. Finally, teachers are overworked grading it all, which is a "
    "separate systemic issue about teacher burnout and retention in the profession.")

COMPLETE = (
    "Homework assigned in large amounts harms students more than it helps them. "
    "When children spend hours on assignments every night, they lose the rest and free time "
    "that growing minds genuinely need. It is bad because tired students cannot focus the next day, "
    "and their learning suffers as a result. Teachers should assign less so that students can "
    "recover and actually absorb what they have already learned in class.")


async def profile_turn(c, label, draft, kind, force_sc=False):
    global _CALLS
    r = await c.post(f"{API}/sessions/preview", json={})
    r.raise_for_status()
    sess = r.json()
    # seed the draft as current text so run() has a paragraph
    state = await cf.get_or_create_state_for_session(sess)
    from compass_foundation import RevisionEntry
    state.revision_history.append(RevisionEntry(text=draft))
    state.current_student_text = draft
    if force_sc:
        state.sc_active = True; state.sc_complete = False; state.sc_index = 0; state.sc_transitioned = False
    await cf._save_state(state)
    # reload the session doc the way the server would
    sess_doc = (await c.get(f"{API}/sessions/{sess['id']}")).json()

    _CALLS = []
    t0 = time.perf_counter()
    result = await fv3.run(sess_doc, draft, kind)
    total = time.perf_counter() - t0
    llm_sum = sum(x["sec"] for x in _CALLS)
    dco = (result.get("decision", {}) or {}).get("developmental_cognition") or {}
    op = ((dco.get("episode_closure") or {}).get("instructional_operation")) or ""
    sc = (result.get("decision", {}) or {}).get("sentence_craft")
    return {"label": label, "kind": kind, "instructional_operation": op or ("sentence_craft" if sc else ""),
            "calls": list(_CALLS), "llm_sum": round(llm_sum, 2),
            "total_run_s": round(total, 2), "non_llm_s": round(total - llm_sum, 2)}


async def main():
    async with httpx.AsyncClient(timeout=200) as c:
        results = []
        results.append(await profile_turn(c, "CONCEPTUAL (thin→develop)", THIN, "writing"))
        results.append(await profile_turn(c, "STRUCTURAL (sprawl→selection)", SPRAWL, "writing"))
        results.append(await profile_turn(c, "SENTENCE CRAFT (complete→SC)", COMPLETE, "revise", force_sc=True))

        print("\n" + "=" * 78)
        print("LATENCY DIAGNOSIS — per-turn LLM call breakdown (backend run() only)")
        print("=" * 78)
        for r in results:
            print(f"\n### {r['label']}  |  op={r['instructional_operation']}")
            print(f"{'call':<16}{'model':<28}{'prompt_ch':>10}{'out_ch':>9}{'sec':>8}")
            for x in r["calls"]:
                print(f"{x['call']:<16}{x['model'][:27]:<28}{x['prompt_chars']:>10}{x['out_chars']:>9}{x['sec']:>8}")
            print(f"{'':<16}{'':<28}{'':>10}{'LLM sum:':>9}{r['llm_sum']:>8}")
            print(f"  sequential LLM calls: {len(r['calls'])}   "
                  f"non-LLM (state/audit/db/python): {r['non_llm_s']}s   TOTAL run(): {r['total_run_s']}s")
        print("\nRAW:", json.dumps(results))

asyncio.run(main())
