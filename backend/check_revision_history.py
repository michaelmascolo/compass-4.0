"""E2E check of the revision-history architecture against the real engine.
Creates a session, submits a first draft (writing), polls to completion, then
submits a substantive revision (revise), polls, and inspects revision-history."""
import asyncio, json, time
import server
from server import Session, InteractRequest, SessionCreate

DRAFT1 = ("Social media is bad for teen friendships. Teens spend too much time on their phones. "
          "They do not talk in person anymore.")
DRAFT2 = ("Social media weakens teen friendships because it replaces the shared, in-person time that "
          "actually builds trust. When teens scroll instead of talking, they trade real conversation for "
          "quick reactions, and over time the friendship becomes shallower. That is the cost we do not see.")


async def run_turn(session_id, kind, content):
    doc = await server.db.sessions.find_one({"id": session_id}, {"_id": 0})
    session = Session(**doc)
    session.turns.append(server.Turn(role="student", kind=kind, content=content, status="complete"))
    ai = server.Turn(role="ai", kind="pending", content="", status="processing")
    session.turns.append(ai)
    await server.db.sessions.update_one({"id": session_id},
        {"$set": {"turns": [t.model_dump() for t in session.turns]}})
    await server._run_reasoning(session_id, ai.id, InteractRequest(content=content, kind=kind))


async def main():
    sc = SessionCreate(assignment="Argue whether social media improves or harms teen friendships.",
                       pedagogical_purpose="Help the student form and clarify a central claim.",
                       current_writing_task="Draft your essay.")
    s = Session(**sc.model_dump())
    s.telos = server.Telos(governing_pedagogical_purpose=sc.pedagogical_purpose,
                           immediate_task_purpose=sc.current_writing_task,
                           teacher_intentions=sc.teacher_notes or "", assignment_context=sc.assignment)
    await server.db.sessions.insert_one(s.model_dump())
    sid = s.id
    print("session", sid, flush=True)

    t0 = time.time(); await run_turn(sid, "writing", DRAFT1)
    print(f"draft1 done in {time.time()-t0:.0f}s", flush=True)
    t0 = time.time(); await run_turn(sid, "revise", DRAFT2)
    print(f"revise done in {time.time()-t0:.0f}s", flush=True)

    doc = await server.db.sessions.find_one({"id": sid}, {"_id": 0})
    rh = doc.get("revision_history", [])
    print("REVISION_HISTORY count:", len(rh), flush=True)
    if rh:
        r = rh[0]
        print(json.dumps({k: (v[:120] + "…" if isinstance(v, str) and len(v) > 120 else v)
                          for k, v in r.items()}, indent=2), flush=True)
    json.dump(rh, open("/app/test_reports/revision_history_check.json", "w"), indent=2)
    print("WROTE", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
