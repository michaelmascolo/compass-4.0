"""4.9.2 contrast/regression check (1 case): thin underdeveloped paragraph must still DEVELOP,
not be pruned by the broadened structural-imbalance trigger."""
import time, json, requests
API = "http://localhost:8001/api"
THIN = ("I think schools should teach students how to use AI responsibly instead of banning it. "
        "Banning does not really work anyway.")
sid = requests.post(f"{API}/sessions/preview", json={"assignment": "What should we do about AI in education?", "canonical": True}, timeout=30).json()["id"]
print("SESSION", sid)
requests.post(f"{API}/sessions/{sid}/interact", json={"content": THIN, "kind": "writing"}, timeout=30)
turn=None; deadline=time.time()+700
while time.time()<deadline:
    time.sleep(5)
    r=requests.get(f"{API}/sessions/{sid}", timeout=30).json()
    ai=[t for t in r.get("turns",[]) if t["role"]=="ai" and t.get("status")=="complete" and t.get("content")]
    if ai: turn=ai[-1]; break
tr=requests.get(f"{API}/dev/functional-v3-trace/{sid}", timeout=30).json().get("trace",[])
dco=(tr[-1].get("developmental_cognition") or {}) if tr else {}
s=dco.get("structural_load_analysis") or {}
op=(turn or {}).get("instructional_operation")
print("structural_load_status:", s.get("structural_load_status"), "| secondary:", json.dumps(s.get("secondary_trajectories"))[:120], "| competing:", json.dumps(s.get("competing_structural_work"))[:80])
print(">> instructional_operation:", op)
print("COACH:", ((turn or {}).get("content") or "")[:300])
print("\nNOT PRUNED (op not structural_selection/condense):", op not in ("structural_selection","condense_and_integrate"))
print("DONE")
