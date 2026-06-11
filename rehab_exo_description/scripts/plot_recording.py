#!/usr/bin/env python3
"""
plot_recording.py — Transforma o inregistrare CSV (din sensor_recorder)
intr-o figura cu trei panouri: POZITIE, VITEZA, TORQUE pentru cele 6
servomotoare, plus statistici in consola (maxime per articulatie).
Ideal pentru figurile din teza/articol, direct din datele de senzori.

Utilizare:
    $ python3 plot_recording.py ~/rehab_data/sesiune_X.csv [iesire.png]
(implicit, figura se salveaza langa CSV, cu acelasi nume si extensia .png)

Nu necesita ROS — doar Python + matplotlib.
"""

import csv
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

COLOR = {"hip": "#2E73CC", "knee": "#2E8B57", "ankle": "#C77F2E"}
SHORT = {"hip": "sold", "knee": "genunchi", "ankle": "glezna"}


def style(j):
    base = j.split("_")[1]
    return COLOR.get(base, "#888"), "-" if j.startswith("left") else "--"


def is_exercise_joint(name):
    return ("_ext_" not in name) and ("seat_lift" not in name)


def load(path):
    with open(path, newline="") as f:
        rows = [r for r in csv.reader(f) if r and not r[0].startswith("#")]
    header, data = rows[0], rows[1:]
    cols = {h: i for i, h in enumerate(header)}
    joints = sorted({h[:-4] for h in header if h.endswith("_pos")})
    t, series = [], {j: {"pos": [], "vel": [], "eff": []} for j in joints}
    for r in data:
        try:
            t.append(float(r[cols["t_sec"]]))
        except (ValueError, IndexError):
            continue
        for j in joints:
            for q in ("pos", "vel", "eff"):
                i = cols.get(f"{j}_{q}")
                v = r[i] if i is not None and i < len(r) else ""
                series[j][q].append(float(v) if v not in ("", None) else float("nan"))
    return t, joints, series


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    path = os.path.expanduser(sys.argv[1])
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(path)[0] + ".png"

    t, joints, S = load(path)
    exj = [j for j in joints if is_exercise_joint(j)]
    adjj = [j for j in joints if not is_exercise_joint(j)]
    if not t:
        print("CSV gol sau ilizibil."); sys.exit(1)

    fig, axes = plt.subplots(3, 1, figsize=(11, 8), sharex=True)
    for ax, q, ttl in zip(axes, ("pos", "vel", "eff"),
                          ("Pozitie [rad]", "Viteza [rad/s]",
                           "Torque (effort) [N*m]")):
        for j in exj:
            c, ls = style(j)
            lbl = ("stg " if j.startswith("left") else "dr ") + SHORT.get(j.split("_")[1], j)
            ax.plot(t, S[j][q], color=c, ls=ls, lw=1.5, label=lbl)
        ax.set_ylabel(ttl, fontsize=10)
        ax.grid(alpha=0.3)
    axes[0].legend(ncol=6, fontsize=8, loc="upper right")
    axes[2].set_xlabel("timp [s]")
    fig.suptitle(f"Inregistrare senzori: {os.path.basename(path)}",
                 fontsize=12, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(out, dpi=150, bbox_inches="tight")

    # statistici in consola
    print(f"\nFigura salvata: {out}")
    print(f"Durata inregistrarii: {t[-1]:.1f} s, {len(t)} esantioane "
          f"(~{len(t)/max(t[-1],1e-9):.0f} Hz)\n")
    print(f"{'articulatie':24s} {'|pos|max [rad]':>14s} {'|v|max [rad/s]':>14s} {'|tau|max [N*m]':>14s}")
    for j in exj + adjj:
        m = {q: max((abs(x) for x in S[j][q] if x == x), default=0.0)
             for q in ("pos", "vel", "eff")}
        print(f"{j:24s} {m['pos']:14.3f} {m['vel']:14.3f} {m['eff']:14.2f}")


if __name__ == "__main__":
    main()
