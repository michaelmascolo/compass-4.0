"""R2b — Sentence Craft CONTINUATION fast-path: multi-turn regression + latency (spec §7,§8).

Drives the REAL engine `functional_v3.run()`, monkeypatching the LLM to prove the light path makes
NO fn-sel (conceptual DCO) call. Invariant under test (decision-agnostic): a genuine SC continuation
turn skips fn-sel and runs ONLY sentence_craft_cognition, whatever the SC decision (operate /
route_upward / complete). Also verifies: entry uses full path + captures governing context; the
force-full (upward-routing) flag routes the next turn back to full; missing context falls back.

Run: cd /app/backend && set -a && source .env && set +a && python tests/test_r2b_sc_light.py
"""
import asyncio, sys, time
sys.path.insert(0, "/app/backend")
import httpx
from emergentintegrations.llm.chat import LlmChat
import functional_v3 as fv3
import compass_foundation as cf

API = "http://localhost:8001/api"
_orig = LlmChat.send_message
_CALLS = []
async def _timed(self, message):
    sid = getattr(self, "session_id", "?")
    pref = next((p for p in ("fn-sel", "rp5-dlg", "sentence-craft", "contract-judge", "dco-tail")
                 if sid.startswith(p)), "other")
    t0 = time.perf_counter()
    out = await _orig(self, message)
    _CALLS.append(pref)
    return out
LlmChat.send_message = _timed

PARA = ("Homework assigned in large amounts harms students more than it helps them. "
        "When children spend hours on assignments every night, they lose the rest and free time "
        "that growing minds genuinely need. It is bad. Teachers should assign less so that students "
        "can recover and absorb what they learned.")
PARA2 = PARA.replace("It is bad.", "Tired students cannot focus the next day, so their learning suffers.")

fails = []
def ok(name, cond):
    print(("PASS " if cond else "FAIL ") + name); (fails.append(name) if not cond else None)

async def turn(sess, text, kind="revise"):
    global _CALLS
    _CALLS = []
    t0 = time.perf_counter()
    res = await fv3.run(sess, text, kind)
    dt = round(time.perf_counter() - t0, 2)
    sc = (res.get("decision", {}) or {}).get("sentence_craft") or {}
    return {"dt": dt, "calls": list(_CALLS), "sc": sc, "invitation": res.get("invitation", "")}

async def make_session(c):
    sess = (await c.post(f"{API}/sessions/preview", json={})).json()
    sess["assignment"] = "Argue whether schools should reduce homework."
    return sess

async def force_continuation_state(sess, gov):
    st = await cf.get_or_create_state_for_session(sess)
    st.sc_active = True; st.sc_transitioned = True; st.sc_complete = False
    st.sc_index = 0; st.sc_force_full_next = False
    st.sc_governing_context = gov
    await cf._save_state(st)


async def main():
    async with httpx.AsyncClient(timeout=200) as c:
        # ---- ENTRY (full path) — establishes + captures governing context ----
        sess = await make_session(c)
        st = await cf.get_or_create_state_for_session(sess)
        st.sc_active = True; st.sc_transitioned = False; st.sc_complete = False
        st.sc_index = 0; st.sc_patterns = []; st.sc_governing_context = {}; st.sc_force_full_next = False
        st.current_student_text = PARA
        await cf._save_state(st)
        t1 = await turn(sess, PARA)
        print(f"\n[ENTRY]  dt={t1['dt']}s calls={t1['calls']} decision={t1['sc'].get('decision')} light={t1['sc'].get('sc_light_path_used')}")
        ok("entry uses FULL path (fn-sel present)", "fn-sel" in t1["calls"])
        ok("entry sc_light_path_used == False", t1["sc"].get("sc_light_path_used") is False)
        st_after = await cf.get_or_create_state_for_session(sess)
        gov = dict(st_after.sc_governing_context or {})
        thesis = (gov.get("structural_load_analysis") or {}).get("central_communicative_movement", "")
        ok("entry set sc_transitioned=True", st_after.sc_transitioned is True)
        ok("entry captured governing context WITH thesis", bool(gov) and bool(thesis))
        print(f"         captured thesis='{thesis[:60]}'")

        # ---- CONTINUATION (light path) — reuse REAL captured gov; clear any force-full from entry ----
        await force_continuation_state(sess, gov)
        t2 = await turn(sess, PARA2)
        print(f"[CONT]   dt={t2['dt']}s calls={t2['calls']} decision={t2['sc'].get('decision')} light={t2['sc'].get('sc_light_path_used')}")
        ok("continuation skips fn-sel (LIGHT path)", "fn-sel" not in t2["calls"])
        ok("continuation runs ONLY sentence_craft_cognition", t2["calls"] == ["sentence-craft"])
        ok("continuation sc_light_path_used == True", t2["sc"].get("sc_light_path_used") is True)
        ok("continuation coaching + focus present", bool(t2["invitation"]) and bool(t2["sc"].get("focus_label")))
        ok("continuation faster than entry", t2["dt"] < t1["dt"])
        st_c = await cf.get_or_create_state_for_session(sess)
        ok("pattern state persists (list intact)", isinstance(st_c.sc_patterns, list))
        ok("active-sentence index tracked", isinstance(st_c.sc_index, int) and st_c.sc_index >= 0)

        # ---- COMPLETION via light path (force no actionable sentences -> completion branch) ----
        CLEAN = ("Excessive homework harms students by stealing the rest they need. "
                 "Because tired students cannot concentrate the next day, their learning steadily suffers. "
                 "Therefore schools should assign less so children can recover and truly absorb their lessons.")
        await force_continuation_state(sess, gov)
        st_cl = await cf.get_or_create_state_for_session(sess); st_cl.sc_index = 0; await cf._save_state(st_cl)
        _orig_actionable = fv3._sc_actionable
        fv3._sc_actionable = lambda s: False  # deterministically drive the completion branch
        try:
            tc = await turn(sess, CLEAN)
        finally:
            fv3._sc_actionable = _orig_actionable
        st_done = await cf.get_or_create_state_for_session(sess)
        print(f"[COMPL]  dt={tc['dt']}s calls={tc['calls']} decision={tc['sc'].get('decision')} sc_complete={st_done.sc_complete}")
        ok("completion path is LIGHT (no fn-sel)", "fn-sel" not in tc["calls"])
        reached = st_done.sc_complete and (tc["sc"].get("decision") == "complete") and ("one last read of the whole thing" in (tc["invitation"] or "").lower())
        ok("completion reaches holistic review via light path", reached)

        # ---- FALLBACK 1: sc_force_full_next -> next turn FULL ----
        await force_continuation_state(sess, gov)
        stff = await cf.get_or_create_state_for_session(sess); stff.sc_force_full_next = True; await cf._save_state(stff)
        t3 = await turn(sess, PARA2)
        print(f"[FORCE]  calls={t3['calls']}")
        ok("sc_force_full_next forces FULL path", "fn-sel" in t3["calls"])
        st3 = await cf.get_or_create_state_for_session(sess)
        ok("force-full flag cleared after full turn", st3.sc_force_full_next is False)

        # ---- FALLBACK 2: missing governing context -> _run_sc_light returns fallback ----
        sess_f = await make_session(c)
        stf = await cf.get_or_create_state_for_session(sess_f)
        stf.sc_transitioned = True; stf.sc_governing_context = {}
        await cf._save_state(stf)
        light, reason = await fv3._run_sc_light(stf, "a", PARA, "", "revise", time.perf_counter())
        ok("missing governing context -> safe fallback", light is None and reason == "missing_governing_context")

        print("\n=== R2b LATENCY (reported SEPARATELY per spec §8; do NOT average) ===")
        print(f"  SC ENTRY (full path):         {t1['dt']}s   calls={t1['calls']}")
        print(f"  SC CONTINUATION (light path): {t2['dt']}s   calls={t2['calls']}   reduction={round((1-t2['dt']/t1['dt'])*100)}%")
        print(f"  SC COMPLETION (light path):   {tc['dt']}s   calls={tc['calls']}")
        print("\nRESULT:", "PASS" if not fails else f"FAIL ({fails})")

asyncio.run(main())
