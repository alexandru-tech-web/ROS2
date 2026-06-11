#!/usr/bin/env python3
"""test_rover_core.py — verificari pentru nucleul teleoperarii."""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rover_core import (DiffDrive, Course, PilotModel, SafetyGate,
                        V_MAX, W_MAX, summarize)

N = 0
def check(c, m):
    global N; assert c, m; N += 1; print(f"  [ok] {m}")

# cinematica
r = DiffDrive()
for _ in range(100): r.step(1.0, 0.0, 0.01)
check(abs(r.x - 1.0) < 1e-6 and abs(r.y) < 1e-9, "mers drept: 1 m in 1 s")
r = DiffDrive()
for _ in range(100): r.step(0.0, 1.0, 0.01)
check(abs(r.th - 1.0) < 1e-6, "rotire pe loc: 1 rad in 1 s (sub limita)")
r = DiffDrive()
v, w = r.step(99, -99, 0.01)
check(v == V_MAX and w == -W_MAX, "limitele v/w sunt impuse")

# actuatorul realist (limite de acceleratie, opt-in)
r = DiffDrive(a_max=1.5)
v, _ = r.step(1.2, 0.0, 0.2)
check(abs(v - 0.3) < 1e-9, "a_max: viteza creste in rampa (0.3 m/s dupa 0.2 s)")
r2 = DiffDrive()
v2, _ = r2.step(1.2, 0.0, 0.2)
check(v2 == 1.2, "fara a_max: raspuns instantaneu (comportamentul vechi intact)")

# traseul + CTE
c = Course([(4, 0), (8, 0)])
check(abs(c.cross_track(2, 1.5) - 1.5) < 1e-9, "CTE fata de segment drept")
check(not c.advance(2, 0), "tinta neatinsa: traseul continua")
check(not c.advance(4.2, 0.1) and c.i == 2, "punct atins -> avans la urmatorul")
check(c.advance(8.1, 0.0), "ultimul punct atins -> traseu terminat")
check(abs(Course().length() - sum(math.hypot(*[a-b for a, b in zip(p, q)])
      for p, q in zip([(0,0)]+__import__('rover_core').COURSE[:-1],
                      __import__('rover_core').COURSE))) < 1e-9,
      "lungimea traseului insumata corect")

# siguranta: watchdog + comenzi invechite
g = SafetyGate()
check(g.output(0.0)[2] and g.stop_events == 0, "fara comenzi: oprit din start")
check(g.on_command(1.0, 0.9, 0.5, 0.1), "comanda proaspata acceptata")
v, w, st = g.output(1.1)
check((v, w, st) == (0.5, 0.1, False), "comanda valida e aplicata")
check(g.output(1.6)[2] and g.stop_events == 1,
      "watchdog: stop dupa 0.4 s fara comenzi (numarat)")
check(not g.on_command(5.0, 3.0, 1.0, 0.0), "comanda invechita (2 s) ignorata")
check(g.output(5.0)[2], "dupa comanda invechita robotul ramane oprit")
g.on_command(6.0, 5.9, 0.3, 0.0)
check(not g.output(6.1)[2] and g.stop_events == 1,
      "comanda noua reporneste miscarea fara opriri suplimentare")

# pilotul inchide bucla pe legatura IDEALA (sanity end-to-end pur)
from rover_core import Course as C2
rr, cc = DiffDrive(), C2()
pil = PilotModel(cc)
t, done = 0.0, False
while t < 90.0:
    v, w = pil.command(rr.x, rr.y, rr.th)
    rr.step(v, w, 0.02)
    if cc.advance(rr.x, rr.y):
        done = True; break
    t += 0.02
check(done and t < 60.0, f"pilotul termina slalomul pe legatura ideala ({t:.1f} s)")
ctes = [C2().cross_track(0, 0)]
check(summarize([(0.1, 0.05), (0.3, None)])["cte_p95"] == 0.3,
      "summarize: p95 si varste optionale")

print(f"\nTOATE TESTELE ROVER AU TRECUT: {N} verificari.")
