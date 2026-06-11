#!/usr/bin/env python3
"""analyze_perception.py — metricile de teza pentru navigarea go-to-goal sub
percepție, comparand RMW-uri (ex. Zenoh vs Cyclone).

Pentru fiecare rulare (un director cu robot_log.csv [+ detections.csv]) calculeaza:
  - timp-pana-la-tinta   : prima clipa cand roverul intra in raza de sosire;
  - distanta finala      : cat de aproape de tinta a ramas la final;
  - eroare de localizare : |tinta_estimata_de_detector - adevarul OBJECTS| (daca
                           exista detections.csv).
Produce un tabel in consola + o figura de comparatie.

Rulare (dupa doua rulari, una pe fiecare RMW):
    python3 analyze_perception.py --goal 8 3 --arrive_r 0.5 \\
        --run cyclone ~/teleop_data_cyclone --run zenoh ~/teleop_data_zenoh
sau, tinta = un obiect din lume (adevarul din gen_rough_world.OBJECTS):
    python3 analyze_perception.py --goal-class red --run cyclone ~/teleop_data
"""
import argparse
import csv
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_rough_world import OBJECTS


def truth_for(color):
    for o in OBJECTS:
        if o["color"] == color:
            return o["xy"]
    return None


def load_traj(run_dir):
    p = os.path.join(os.path.expanduser(run_dir), "robot_log.csv")
    if not os.path.exists(p):
        return []
    return [(float(r["t_s"]), float(r["x"]), float(r["y"]))
            for r in csv.DictReader(open(p))]


def load_dets(run_dir):
    p = os.path.join(os.path.expanduser(run_dir), "detections.csv")
    if not os.path.exists(p):
        return []
    return list(csv.DictReader(open(p)))


def metrics(traj, dets, goal, arrive_r):
    gx, gy = goal
    t_goal, final = None, None
    for t, x, y in traj:
        if t_goal is None and math.hypot(gx - x, gy - y) < arrive_r:
            t_goal = t
    if traj:
        _, x, y = traj[-1]
        final = math.hypot(gx - x, gy - y)
    # eroare de localizare per culoare, fata de adevarul OBJECTS
    errs = []
    for d in dets:
        tr = truth_for(d.get("color", ""))
        if tr is not None:
            errs.append(math.hypot(float(d["wx"]) - tr[0],
                                   float(d["wy"]) - tr[1]))
    loc = (sum(errs) / len(errs)) if errs else None
    return {"t_goal": t_goal, "final": final, "loc_err": loc,
            "n_det": len(dets)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", nargs=2, action="append", metavar=("LABEL", "DIR"),
                    required=True, help="eticheta si directorul rularii")
    ap.add_argument("--goal", nargs=2, type=float, metavar=("GX", "GY"))
    ap.add_argument("--goal-class", default=None,
                    help="tinta = obiectul de aceasta culoare din OBJECTS")
    ap.add_argument("--arrive_r", type=float, default=0.5)
    ap.add_argument("--out", default="results/perception_compare.png")
    a = ap.parse_args()

    if a.goal:
        goal = tuple(a.goal)
    elif a.goal_class:
        goal = truth_for(a.goal_class)
        if goal is None:
            sys.exit(f"[eroare] nu exista obiect de culoare '{a.goal_class}' in OBJECTS")
    else:
        sys.exit("[eroare] da --goal GX GY sau --goal-class CULOARE")

    runs = []
    print(f"\ntinta = ({goal[0]:.1f}, {goal[1]:.1f}), raza de sosire = {a.arrive_r} m\n")
    print(f"{'rulare':12} {'timp->tinta':>12} {'dist finala':>12} "
          f"{'eroare loc.':>12} {'#detectii':>10}")
    print("-" * 62)
    for label, d in a.run:
        m = metrics(load_traj(d), load_dets(d), goal, a.arrive_r)
        runs.append((label, load_traj(d), m))
        tg = f"{m['t_goal']:.1f} s" if m["t_goal"] is not None else "ATINS NU"
        fn = f"{m['final']:.2f} m" if m["final"] is not None else "—"
        lc = f"{m['loc_err']:.2f} m" if m["loc_err"] is not None else "—"
        print(f"{label:12} {tg:>12} {fn:>12} {lc:>12} {m['n_det']:>10}")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.6))
    fig.suptitle("Navigare go-to-goal sub percepție — comparatie RMW",
                 fontweight="bold")
    # stanga: traiectoriile + tinta + obiectele
    for label, traj, _ in runs:
        if traj:
            ax[0].plot([r[1] for r in traj], [r[2] for r in traj], lw=1.8,
                       label=label)
    ax[0].plot([goal[0]], [goal[1]], "*", ms=16, color="#c0392b", label="tinta")
    for o in OBJECTS:
        ax[0].plot(*o["xy"], "s", ms=7, color="#888")
    ax[0].set_aspect("equal"); ax[0].grid(alpha=0.3); ax[0].legend()
    ax[0].set_title("traiectorii catre tinta")
    # dreapta: bare cu timp-pana-la-tinta si distanta finala
    labels = [r[0] for r in runs]
    tg = [r[2]["t_goal"] if r[2]["t_goal"] is not None else 0 for r in runs]
    fn = [r[2]["final"] if r[2]["final"] is not None else 0 for r in runs]
    xpos = range(len(labels))
    ax[1].bar([i - 0.2 for i in xpos], tg, 0.4, label="timp->tinta [s]",
              color="#2E73CC")
    ax[1].bar([i + 0.2 for i in xpos], fn, 0.4, label="dist finala [m]",
              color="#d8702e")
    ax[1].set_xticks(list(xpos)); ax[1].set_xticklabels(labels)
    ax[1].grid(alpha=0.3, axis="y"); ax[1].legend()
    ax[1].set_title("metrici per RMW")
    fig.tight_layout(); fig.savefig(a.out, dpi=130)
    print(f"\n[ok] figura: {a.out}")


if __name__ == "__main__":
    main()
