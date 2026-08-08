"""FOCUSED live verification of the Sentence Craft path (one session, real LLM).

Creates a preview session, forces the persisted instructional state into Sentence Craft
(sc_active=True), submits a complete well-formed paragraph, then polls the durable-processing
turn and prints the surfaced turn.sentence_craft payload + instructional_operation so we can
confirm the end-to-end live path AND that the payload architecture is correct.

Run:  cd /app/backend && set -a && source .env && set +a && python tests/live_sc_path.py
"""
import asyncio, sys, time, json
sys.path.insert(0, "/app/backend")
import httpx
import compass_foundation as cf

API = "http://localhost:8001/api"

PARAGRAPH = (
    "Homework assigned in large amounts harms students more than it helps them. "
    "When children spend hours on assignments every night, they lose the rest and free time "
    "that growing minds genuinely need. It is bad because tired students cannot focus the next day, "
    "and their learning suffers as a result. Teachers should assign less so that students can "
    "recover and actually absorb what they have already learned in class."
)


async def main():
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post(f"{API}/sessions/preview", json={})
        r.raise_for_status()
        sess = r.json()
        sid = sess["id"]
        print("preview session:", sid)

        # Force the persisted instructional state into Sentence Craft mode.
        state = await cf.get_or_create_state_for_session(sess)
        state.sc_active = True
        state.sc_complete = False
        state.sc_index = 0
        state.sc_transitioned = False
        state.current_student_text = PARAGRAPH
        await cf._save_state(state)
        print("forced sc_active=True on state", state.id)

        # Submit the paragraph (durable processing returns immediately).
        r = await c.post(f"{API}/sessions/{sid}/interact",
                         json={"content": PARAGRAPH, "kind": "revise"})
        r.raise_for_status()
        print("interact accepted; polling for completion...")

        deadline = time.time() + 180
        ai = None
        while time.time() < deadline:
            await asyncio.sleep(3)
            s = (await c.get(f"{API}/sessions/{sid}")).json()
            ai = next((t for t in s["turns"] if t["role"] == "ai" and t["status"] == "complete" and t["content"]), None)
            proc = any(t["status"] == "processing" for t in s["turns"])
            if ai and not proc:
                break
        if not ai:
            print("TIMEOUT — no completed AI turn"); return

        print("\n=== instructional_operation:", ai.get("instructional_operation"))
        sc = ai.get("sentence_craft")
        print("=== sentence_craft payload ===")
        print(json.dumps(sc, indent=2))
        print("\n=== coach invitation (first 400 chars) ===")
        print((ai.get("content") or "")[:400])

        # assertions
        ok = True
        if ai.get("instructional_operation") != "sentence_craft":
            print("FAIL: instructional_operation != sentence_craft"); ok = False
        if not sc or not sc.get("active"):
            print("FAIL: sentence_craft payload missing/not active"); ok = False
        else:
            for k in ("decision", "active_sentence_text", "focus_label", "operation",
                      "scaffold_level", "pattern", "pattern_influenced_operation", "evidence_of_control"):
                if k not in sc:
                    print(f"FAIL: payload missing '{k}'"); ok = False
            if sc.get("decision") == "operate" and not (sc.get("active_sentence_text") or "").strip():
                print("FAIL: operate turn without active_sentence_text"); ok = False
            # active sentence text must be locatable in the paragraph (UI highlight depends on this)
            if sc.get("active_sentence_text") and sc["active_sentence_text"].strip() not in PARAGRAPH:
                print("WARN: active_sentence_text not a verbatim substring (UI locates fuzzily):",
                      sc["active_sentence_text"])
        print("\nRESULT:", "PASS" if ok else "FAIL")
        print("SESSION_ID_FOR_SCREENSHOT:", sid)


if __name__ == "__main__":
    asyncio.run(main())
