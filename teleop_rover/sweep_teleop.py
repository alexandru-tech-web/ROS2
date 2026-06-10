#!/usr/bin/env python3
"""sweep_teleop.py — EXPERIMENTUL de teza: aceeasi teleoperare, maturata pe
grila latenta x pierdere (jitter = 20% din latenta), N seminte per conditie.
Iesiri: results/sweep.csv + results/teleop_sweep.png (eroarea de urmarire,
timpul de parcurs si opririle de siguranta vs degradarea legaturii).

Rulare:  python3 sweep_teleop.py            (~75 de rulari, sub un minut)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sil_teleop import run

LATS = [0, 100, 200, 500, 1000]          # ms (dus; bucla vede 2x)
LOSSES = [0.0, 0.10, 0.30]
SEEDS = [1, 2, 3, 4, 5]


def main():
    os.makedirs("results", exist_ok=True)
    rows = []
    for loss in LOSSES:
        for lat in LATS:
            rs = [run(lat, 0.2 * lat, loss, seed=s)[0] for s in SEEDS]
            m = lambda k: sum(r[k] for r in rs) / len(rs)
            rows.append(dict(lat=lat, loss=loss,
                             cte_p95=m("cte_p95"), cte_mean=m("cte_mean"),
                             time_s=m("time_s"), stops=m("stops"),
                             completed=sum(r["completed"] for r in rs)))
            print(f"lat={lat:4.0f}ms loss={loss:.0%}: "
                  f"CTE p95={rows[-1]['cte_p95']:.2f} m  "
                  f"timp={rows[-1]['time_s']:5.1f} s  "
                  f"opriri={rows[-1]['stops']:.1f}  "
                  f"finalizate {rows[-1]['completed']}/{len(SEEDS)}")
    with open("results/sweep.csv", "w") as f:
        f.write("lat_ms,loss,cte_p95,cte_mean,time_s,stops,completed\n")
        for r in rows:
            f.write(f"{r['lat']},{r['loss']},{r['cte_p95']:.3f},"
                    f"{r['cte_mean']:.3f},{r['time_s']:.1f},"
                    f"{r['stops']:.2f},{r['completed']}\n")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 3, figsize=(14, 4.2))
    fig.suptitle("Teleoperare in bucla inchisa sub degradare de retea — "
                 "metrici de APLICATIE (5 rulari/conditie, pilot identic)",
                 fontweight="bold")
    col = {0.0: "#2E8B57", 0.10: "#2E73CC", 0.30: "#c0392b"}
    for loss in LOSSES:
        sel = [r for r in rows if r["loss"] == loss]
        x = [r["lat"] for r in sel]
        lab = f"pierdere {loss:.0%}"
        ax[0].plot(x, [r["cte_p95"] for r in sel], "o-", color=col[loss],
                   label=lab)
        ax[1].plot(x, [r["time_s"] for r in sel], "o-", color=col[loss],
                   label=lab)
        ax[2].plot(x, [r["stops"] for r in sel], "o-", color=col[loss],
                   label=lab)
    for a, t, yl in ((ax[0], "eroarea de urmarire", "CTE p95 [m]"),
                     (ax[1], "timpul de parcurs", "timp [s]"),
                     (ax[2], "opriri de siguranta (watchdog)",
                      "opriri / rulare")):
        a.set_title(t)
        a.set_xlabel("latenta legaturii (un sens) [ms]")
        a.set_ylabel(yl)
        a.grid(alpha=0.3)
        a.legend()
    fig.tight_layout()
    fig.savefig("results/teleop_sweep.png", dpi=130)
    print("[ok] results/sweep.csv + results/teleop_sweep.png")


if __name__ == "__main__":
    main()
