#!/usr/bin/env python3
"""test_operator_core.py -- verificari pentru stratul de comanda al
operatorului (om-in-bucla). Rulare: python3 test_operator_core.py"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from operator_core import (OperatorState, AUTO, HOLD, GOTO, RTH,
                           IDLE, RUNNING, PAUSED, ABORTED)

IDS = ["d1", "d2", "d3", "d4"]
N = 0


def check(cond, msg):
    global N
    assert cond, msg
    N += 1
    print(f"  [ok] {msg}")


def fresh(autostart=True):
    return OperatorState(IDS, autostart=autostart)


# 1) starea initiala
s = fresh(autostart=True)
check(s.mission == RUNNING and s.auto_eligible() == set(IDS),
      "autostart=true -> RUNNING, toate dronele eligibile")
s = fresh(autostart=False)
check(s.mission == IDLE and s.auto_eligible() == set(),
      "autostart=false -> IDLE, nicio alocare automata")

# 2) start din IDLE
out = s.handle({"type": "mission", "action": "start"})
check(s.mission == RUNNING and len(out) == 4
      and all(p["a"] == "resume" for _, p in out),
      "start din IDLE -> RUNNING + resume catre toate dronele AUTO")

# 3) pauza trimite hold doar dronelor AUTO si blocheaza alocarea
s.handle({"type": "drone", "id": "d2", "action": "hold"})
out = s.handle({"type": "mission", "action": "pause"})
check(s.mission == PAUSED and {d for d, _ in out} == {"d1", "d3", "d4"}
      and all(p["a"] == "hold" for _, p in out),
      "pauza -> hold doar catre dronele AUTO (d2 era deja manual)")
check(s.auto_eligible() == set(), "in PAUSED nimeni nu primeste alocari")

# 4) reluarea restaureaza doar dronele AUTO
out = s.handle({"type": "mission", "action": "resume"})
check(s.mission == RUNNING and {d for d, _ in out} == {"d1", "d3", "d4"},
      "reluare -> resume doar catre dronele AUTO")
check(s.auto_eligible() == {"d1", "d3", "d4"},
      "drona tinuta manual (d2) ramane in afara alocarii automate")

# 5) goto: mod + payload cu celula intreaga
out = s.handle({"type": "drone", "id": "d3", "action": "goto",
                "cell": [12.7, 40.2]})
check(s.mode["d3"] == GOTO and out[0][0] == "d3"
      and out[0][1]["a"] == "goto" and out[0][1]["cell"] == [12, 40],
      "goto seteaza modul GOTO si trunchiaza celula la intregi")
check(s.auto_eligible() == {"d1", "d4"},
      "drona in GOTO nu mai primeste frontiere automate")

# 6) done/fail pe goto -> HOLD (ramane pe loc)
s.on_event("d3", "ack")
check(s.mode["d3"] == GOTO, "ack nu schimba modul")
s.on_event("d3", "done")
check(s.mode["d3"] == HOLD, "done pe goto -> drona ramane in HOLD")
s.handle({"type": "drone", "id": "d3", "action": "resume"})
check(s.mode["d3"] == AUTO and "d3" in s.auto_eligible(),
      "Auto readuce drona in alocarea automata")

# 7) abort -> toate RTH, misiune ABORTED
out = s.handle({"type": "mission", "action": "abort"})
check(s.mission == ABORTED and len(out) == 4
      and all(p["a"] == "rth" for _, p in out)
      and all(m == RTH for m in s.mode.values()),
      "abort -> RTH catre toate dronele, misiune ABORTED")
check(s.auto_eligible() == set(), "dupa abort nu se mai aloca nimic")

# 8) start dupa abort = restart complet (toate inapoi pe AUTO)
out = s.handle({"type": "mission", "action": "start"})
check(s.mission == RUNNING and all(m == AUTO for m in s.mode.values())
      and len(out) == 4,
      "start dupa abort reseteaza toate dronele pe AUTO")

# 9) cmd_id strict crescator (jurnalul sent->ack->done se leaga pe el)
ids = [p["cmd_id"] for _, p in
       s.handle({"type": "mission", "action": "abort"})]
check(ids == sorted(ids) and len(set(ids)) == len(ids),
      "cmd_id unic si strict crescator")

# 10) comenzi invalide: ignorate, starea neatinsa
before = (s.mission, dict(s.mode))
for bad in [None, 42, {}, {"type": "drone", "id": "d9", "action": "hold"},
            {"type": "drone", "id": "d1", "action": "teleport"},
            {"type": "mission", "action": "pause"},      # din ABORTED
            {"type": "fault", "action": "isolate", "id": "d1"}]:
    check(s.handle(bad) == [], f"comanda invalida ignorata: {bad!r}")
check((s.mission, dict(s.mode)) == before,
      "starea ramane neschimbata dupa comenzi invalide")

print(f"\nTOATE TESTELE OPERATOR AU TRECUT: {N} verificari.")
