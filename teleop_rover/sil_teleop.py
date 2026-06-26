#!/usr/bin/env python3
"""sil_teleop.py -- teleoperare in BUCLA INCHISA prin reteaua degradata,
fara ROS: pilotul (operatorul-model) vede DOAR pozele care au supravietuit
canalului (latenta+jitter+pierdere la intors), iar robotul primeste DOAR
comenzile care au supravietuit canalului la dus si trec de stratul de
siguranta (watchdog + comenzi invechite). Exact bucla reala de teleop.

    operator --cmd 20 Hz--> [canal degradat] --> SafetyGate --> rover
    operator <--poza 20 Hz-- [canal degradat] <-- senzor de pozitie

Rulare:
    python3 sil_teleop.py --lat 200 --jit 40 --loss 0.1 --plot
Iesiri: rezumat JSON in consola; cu --plot si results/run_lat..._traj.png
(+ --trace scrie si CSV-ul per-esantion, acelasi format ca ROS-ul).
"""
import argparse
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rover_core import DiffDrive, Course, PilotModel, SafetyGate, summarize
from netem_core import Channel

DT = 0.02            # fizica 50 Hz
CMD_HZ = 20.0
FB_HZ = 20.0
T_MAX = 120.0


def run(lat_ms=0.0, jit_ms=0.0, loss=0.0, seed=1, trace=None,
        a_max=None, w_acc=None):
    ch = Channel(["op", "rob"],
                 default={"base_ms": lat_ms, "jitter_ms": jit_ms,
                          "loss": loss},
                 overrides={}, store_and_forward=False, seed=seed)
    rover = DiffDrive(a_max=a_max, w_acc=w_acc)
    course = Course()
    pilot = PilotModel(course)
    gate = SafetyGate()
    known = (0.0, 0.0, 0.0)          # ultima poza ajunsa la operator
    known_t = 0.0
    t, next_cmd, next_fb = 0.0, 0.0, 0.0
    rows, done_t = [], None

    while t < T_MAX:
        # livrarile scadente pe ambele sensuri
        for src, dst, msg, t0, t_del in ch.deliver(t):
            if dst == "rob" and msg["k"] == "cmd":
                gate.on_command(t, t0, msg["v"], msg["w"])
            elif dst == "op" and msg["k"] == "pose":
                if t0 > known_t:                  # pastram cea mai noua
                    known = (msg["x"], msg["y"], msg["th"])
                    known_t = t0

        if t >= next_cmd:                         # operatorul decide
            next_cmd += 1.0 / CMD_HZ
            v, w = pilot.command(*known)
            ch.send("op", "rob", {"k": "cmd", "v": v, "w": w}, t)
        if t >= next_fb:                          # senzorul raporteaza
            next_fb += 1.0 / FB_HZ
            ch.send("rob", "op", {"k": "pose", "x": rover.x, "y": rover.y,
                                  "th": rover.th}, t)

        v, w, stopped = gate.output(t)
        rover.step(v, w, DT)

        cte = course.cross_track(rover.x, rover.y)
        age = (t - gate.t_rx) if gate.t_rx is not None else None
        rows.append((t, rover.x, rover.y, cte, age,
                     t - known_t, int(stopped)))
        if done_t is None and course.advance(rover.x, rover.y):
            done_t = t
            break
        t += DT

    res = summarize([(r[3], r[4]) for r in rows])
    res.update(lat_ms=lat_ms, jit_ms=jit_ms, loss=loss, seed=seed,
               completed=done_t is not None,
               time_s=round(done_t if done_t is not None else T_MAX, 2),
               stops=gate.stop_events,
               fb_age_mean=round(sum(r[5] for r in rows) / len(rows), 3))
    if trace:
        with open(trace, "w") as f:
            f.write("t_s,x,y,cte,cmd_age,fb_age,stopped\n")
            for r in rows:
                f.write(",".join("" if v is None else
                                 (str(v) if isinstance(v, int)
                                  else f"{v:.3f}") for v in r) + "\n")
    return res, rows


def plot(rows, res, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    c = Course()
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.5))
    fig.suptitle(f"Teleoperare prin canal degradat -- lat={res['lat_ms']:.0f} ms, "
                 f"jitter={res['jit_ms']:.0f} ms, pierdere={100*res['loss']:.0f}%  "
                 f"(CTE p95={res['cte_p95']:.2f} m, "
                 f"{res['time_s']:.0f} s, opriri={res['stops']})",
                 fontweight="bold", fontsize=11)
    cx = [p[0] for p in c.pts]
    cy = [p[1] for p in c.pts]
    ax[0].plot(cx, cy, "o--", color="#888", label="traseul (porti)")
    ax[0].plot([r[1] for r in rows], [r[2] for r in rows],
               color="#2E73CC", lw=1.8, label="drumul roverului")
    st = [(r[1], r[2]) for r in rows if r[6]]
    if st:
        ax[0].plot([p[0] for p in st], [p[1] for p in st], ".",
                   color="#c0392b", ms=3, label="oprit (watchdog)")
    ax[0].set_aspect("equal")
    ax[0].set_xlabel("x [m]", fontsize=11); ax[0].set_ylabel("y [m]", fontsize=11)
    ax[0].grid(linestyle=":", linewidth=0.5, alpha=0.6); ax[0].set_axisbelow(True)
    ax[0].legend(fontsize=9)
    ax[0].set_title("traiectoria")
    t = [r[0] for r in rows]
    ax[1].plot(t, [r[3] for r in rows], color="#d8702e", label="CTE [m]")
    ax[1].plot(t, [r[5] for r in rows], color="#2E8B57", ls="--",
               label="varsta feedback-ului [s]")
    ax[1].set_xlabel("timp [s]", fontsize=11)
    ax[1].set_ylabel("CTE [m] / varsta feedback [s]", fontsize=11)
    ax[1].legend(fontsize=9)
    ax[1].grid(linestyle=":", linewidth=0.5, alpha=0.6); ax[1].set_axisbelow(True)
    ax[1].set_title("eroarea si prospetimea")
    stem = os.path.splitext(out)[0]
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(stem + "." + ext, dpi=200)
    print(f"[ok] figura: {stem}.{{png,pdf}}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lat", type=float, default=0.0)
    ap.add_argument("--jit", type=float, default=0.0)
    ap.add_argument("--loss", type=float, default=0.0)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--trace", default=None)
    ap.add_argument("--amax", type=float, default=None,
                    help="limita de acceleratie liniara [m/s^2] (actuator realist)")
    ap.add_argument("--wacc", type=float, default=None)
    ap.add_argument("--plot", action="store_true")
    a = ap.parse_args()
    os.makedirs("results", exist_ok=True)
    res, rows = run(a.lat, a.jit, a.loss, a.seed, a.trace,
                    a_max=a.amax, w_acc=a.wacc)
    print(json.dumps(res, indent=1))
    if a.plot:
        plot(rows, res, f"results/run_lat{a.lat:.0f}_loss{int(100*a.loss)}"
                        f"_traj.png")


if __name__ == "__main__":
    main()
