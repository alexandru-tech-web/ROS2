#!/usr/bin/env python3
"""test_nav_core.py — verificari pentru nucleul cu 4 roti + go-to-goal."""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nav_core import SkidSteer4W, goto_command, goal_reached
from rover_core import V_MAX, W_MAX

N = 0
def check(c, m):
    global N; assert c, m; N += 1; print(f"  [ok] {m}")

# cinematica skid-steer: fara patinare = identic cu diferentialul
r = SkidSteer4W()
for _ in range(100): r.step(1.0, 0.0, 0.01)
check(abs(r.x - 1.0) < 1e-6 and abs(r.y) < 1e-9, "skid fara slip: 1 m in 1 s drept")
r = SkidSteer4W()
for _ in range(100): r.step(0.0, 1.0, 0.01)
check(abs(r.th - 1.0) < 1e-6, "skid fara slip: 1 rad in 1 s pe loc")

# patinarea reduce miscarea efectiva
r = SkidSteer4W(slip=0.5)
for _ in range(100): r.step(1.0, 0.0, 0.01)
check(abs(r.x - 0.5) < 1e-6, "slip=0.5 injumatateste distanta parcursa")
r = SkidSteer4W(w_slip=0.25)
for _ in range(100): r.step(0.0, 1.0, 0.01)
check(abs(r.th - 0.75) < 1e-6, "w_slip=0.25 reduce rotirea efectiva la 0.75 rad")

# limite si rampa de acceleratie (mostenite din tiparul DiffDrive)
r = SkidSteer4W()
v, w = r.step(99, -99, 0.01)
check(v == V_MAX and w == -W_MAX, "skid: limitele v/w sunt impuse")
r = SkidSteer4W(a_max=1.5)
v, _ = r.step(1.2, 0.0, 0.2)
check(abs(v - 0.3) < 1e-9, "skid a_max: viteza creste in rampa (0.3 m/s dupa 0.2 s)")

# go-to-goal: comportamentul controlerului
check(goto_command(0, 0, 0, 0.1, 0.0)[2], "in raza de sosire -> arrived=True")
v, w, ar = goto_command(0, 0, 0, 0.0, 5.0)   # tinta perpendicular stanga
check(abs(v) < 1e-9 and w > 0 and not ar,
      "tinta mult in lateral -> pivot pe loc (v=0, w>0)")
v_near, _, _ = goto_command(0, 0, 0, 1.0, 0.0)   # tinta aproape, in fata
v_far, _, _ = goto_command(0, 0, 0, 5.0, 0.0)    # tinta departe, in fata
check(v_near < v_far and v_far <= V_MAX, "decelerare la apropiere de tinta")
check(not goal_reached(0, 0, 5, 0) and goal_reached(4.7, 0.1, 5, 0),
      "goal_reached: prag de sosire corect")

# bucla inchisa PURA: go-to-goal conduce skid-steer-ul pana la tinta (fara ROS)
r = SkidSteer4W()
gx, gy = 5.0, 3.0
t, done = 0.0, False
while t < 30.0:
    v, w, ar = goto_command(r.x, r.y, r.th, gx, gy)
    r.step(v, w, 0.02)
    if ar:
        done = True; break
    t += 0.02
check(done and goal_reached(r.x, r.y, gx, gy),
      f"SIL: skid-steer ajunge la (5,3) cu go-to-goal in {t:.1f} s")

print(f"\nTOATE TESTELE NAV AU TRECUT: {N} verificari.")
