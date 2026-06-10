#!/usr/bin/env python3
"""plot_trace.py — figura unei rulari REALE (ROS/Gazebo) din jurnalul-traseu
al robotului: traiectoria pe traseu + CTE si varsta comenzii in timp.
Rulare: python3 plot_trace.py ~/teleop_data/robot_log.csv"""
import csv, os, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rover_core import Course

path = sys.argv[1]
rows = list(csv.DictReader(open(os.path.expanduser(path))))
t = [float(r["t_s"]) for r in rows]
x = [float(r["x"]) for r in rows]
y = [float(r["y"]) for r in rows]
cte = [float(r["cte"]) for r in rows]
age = [float(r["cmd_age"]) if r["cmd_age"] else None for r in rows]
stp = [(float(r["x"]), float(r["y"])) for r in rows if r["stopped"] == "1"]
c = Course()
fig, ax = plt.subplots(1, 2, figsize=(12, 4.5))
fig.suptitle("Teleoperare — rulare reala (jurnalul robotului)", fontweight="bold")
ax[0].plot([p[0] for p in c.pts], [p[1] for p in c.pts], "o--", color="#888",
           label="traseul")
ax[0].plot(x, y, color="#2E73CC", lw=1.8, label="drumul roverului")
if stp:
    ax[0].plot([p[0] for p in stp], [p[1] for p in stp], ".",
               color="#c0392b", ms=3, label="oprit (watchdog)")
ax[0].set_aspect("equal"); ax[0].legend(); ax[0].set_title("traiectoria")
ax[1].plot(t, cte, color="#d8702e", label="CTE [m]")
ax[1].plot(t, [a if a is not None else 0 for a in age], color="#2E8B57",
           ls="--", label="varsta comenzii [s]")
ax[1].set_xlabel("timp [s]"); ax[1].grid(alpha=0.3); ax[1].legend()
out = os.path.splitext(os.path.expanduser(path))[0] + "_traj.png"
fig.tight_layout(); fig.savefig(out, dpi=130)
print(f"[ok] figura: {out}")
