#!/usr/bin/env python3
"""test_bench_core.py -- verificari pentru nucleul campaniei C1."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bench_core import (make_payload, rtt_stats, netem_cmd, netem_clear_cmd,
                        build_plan, mission_done_time, CONDITIONS)

N = 0
def check(c, m):
    global N; assert c, m; N += 1; print(f"  [ok] {m}")

check(len(make_payload(4096)) == 4096 and make_payload(0) == "",
      "sarcina utila are exact dimensiunea ceruta")
st = rtt_stats([10, 20, 30, 40, 100], sent=10, received=5)
check(st["loss"] == 0.5 and st["mean_ms"] == 40.0 and st["p50_ms"] == 30
      and st["p95_ms"] == 100 and st["min_ms"] == 10,
      "statistici: pierdere, medie, p50, p95 corecte")
check(rtt_stats([], 20, 0)["loss"] == 1.0, "zero raspunsuri -> pierdere 100%")
cmd = netem_cmd("lo", dict(base_ms=200, jitter_ms=50, loss=0.15))
check(cmd == "tc qdisc replace dev lo root netem delay 200ms 50ms loss 15.0%",
      "comanda tc construita exact")
check(netem_cmd("lo", dict(base_ms=0, jitter_ms=0, loss=0.25, corr=0.50))
      == "tc qdisc replace dev lo root netem delay 0ms 0ms loss 25.0% 50.0%",
      "comanda tc cu pierdere corelata (rafala)")
check(netem_cmd("lo", dict(base_ms=0, jitter_ms=0, loss=0.30, type="gilbert", p=0.0857, r=0.2000))
      == "tc qdisc replace dev lo root netem delay 0ms 0ms loss gemodel 8.570% 20.000% 100% 0%",
      "comanda tc gilbert (gemodel) -- paritate de model SIL<->HIL")
check(netem_clear_cmd("eth0") == "tc qdisc del dev eth0 root",
      "comanda de curatare tc")

plan = build_plan(["cyclonedds", "zenoh"], CONDITIONS, reps=5)
check(len(plan) == 2 * len(CONDITIONS) * 5 * 2,
      "planul: 2 RMW x %d conditii x 5 rep x 2 straturi" % len(CONDITIONS))
check(all(p["needs_router"] == (p["rmw"] == "zenoh") for p in plan),
      "routerul Zenoh cerut doar pentru blocul zenoh")
check(plan[0]["rmw"] == "cyclonedds" and plan[-1]["rmw"] == "zenoh"
      and plan[0]["condition"] == "ideal",
      "ordinea: blocat pe RMW, conditiile de la usor la sever")
try:
    build_plan(["mqtt"], CONDITIONS, 1); ok = False
except ValueError:
    ok = True
check(ok, "RMW necunoscut respins")

csvtxt = "t_s,coverage,victims_found,cohesion,drones_in_fallback\n" \
         "10.0,0.50,2,0.9,0\n95.5,0.96,5,0.8,0\n100.0,0.97,5,0.8,0\n"
check(mission_done_time(csvtxt) == 95.5, "timpul de finalizare extras corect")
check(mission_done_time(csvtxt, victims_total=6) is None,
      "misiune neterminata -> None (plafon)")
print(f"\nTOATE TESTELE C1 AU TRECUT: {N} verificari.")
