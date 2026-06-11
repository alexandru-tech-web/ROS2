#!/usr/bin/env python3
"""sweep_teleop.py — EXPERIMENTUL de teza: aceeasi teleoperare, maturata pe
grila latenta x pierdere (jitter = 20% din latenta), N seminte per conditie.

Acum si pe doua regimuri de ACTUATOR (dimensiunea ceruta in README):
  - "ideal"     : raspuns instantaneu (a_max=w_acc=None) — comportamentul de baza;
  - "realistic" : limite de acceleratie (actuator real) — vedem daca pragul de
                  rupere latenta se MUTA cand roverul nu mai poate corecta instant.

Iesiri:
  results/sweep.csv            (coloana 'accel' = ideal/realistic)
  results/teleop_sweep.png     (ca inainte: regimul IDEAL, 3 panouri vs latenta)
  results/teleop_sweep_accel.png  (ideal vs realistic la pierdere 0% — efectul actuatorului)

Rulare:  python3 sweep_teleop.py            (~150 de rulari, ~un minut)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sil_teleop import run

LATS = [0, 100, 200, 500, 1000]          # ms (dus; bucla vede 2x)
LOSSES = [0.0, 0.10, 0.30]
SEEDS = [1, 2, 3, 4, 5]
# regimuri de actuator: (eticheta, a_max [m/s^2], w_acc [rad/s^2])
ACCELS = [("ideal", None, None), ("realistic", 1.5, 3.0)]


def main():
    os.makedirs("results", exist_ok=True)
    rows = []
    for accel, am, wa in ACCELS:
        for loss in LOSSES:
            for lat in LATS:
                rs = [run(lat, 0.2 * lat, loss, seed=s,
                          a_max=am, w_acc=wa)[0] for s in SEEDS]
                m = lambda k: sum(r[k] for r in rs) / len(rs)
                rows.append(dict(accel=accel, lat=lat, loss=loss,
                                 cte_p95=m("cte_p95"), cte_mean=m("cte_mean"),
                                 time_s=m("time_s"), stops=m("stops"),
                                 completed=sum(r["completed"] for r in rs)))
                print(f"[{accel:9}] lat={lat:4.0f}ms loss={loss:.0%}: "
                      f"CTE p95={rows[-1]['cte_p95']:.2f} m  "
                      f"timp={rows[-1]['time_s']:5.1f} s  "
                      f"opriri={rows[-1]['stops']:.1f}  "
                      f"finalizate {rows[-1]['completed']}/{len(SEEDS)}")
    with open("results/sweep.csv", "w") as f:
        f.write("accel,lat_ms,loss,cte_p95,cte_mean,time_s,stops,completed\n")
        for r in rows:
            f.write(f"{r['accel']},{r['lat']},{r['loss']},{r['cte_p95']:.3f},"
                    f"{r['cte_mean']:.3f},{r['time_s']:.1f},"
                    f"{r['stops']:.2f},{r['completed']}\n")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # --- figura 1 (neschimbata): regimul IDEAL, metrici vs latenta ---
    ideal = [r for r in rows if r["accel"] == "ideal"]
    fig, ax = plt.subplots(1, 3, figsize=(14, 4.2))
    fig.suptitle("Teleoperare in bucla inchisa sub degradare de retea — "
                 "metrici de APLICATIE (5 rulari/conditie, pilot identic)",
                 fontweight="bold")
    col = {0.0: "#2E8B57", 0.10: "#2E73CC", 0.30: "#c0392b"}
    for loss in LOSSES:
        sel = [r for r in ideal if r["loss"] == loss]
        x = [r["lat"] for r in sel]
        lab = f"pierdere {loss:.0%}"
        ax[0].plot(x, [r["cte_p95"] for r in sel], "o-", color=col[loss], label=lab)
        ax[1].plot(x, [r["time_s"] for r in sel], "o-", color=col[loss], label=lab)
        ax[2].plot(x, [r["stops"] for r in sel], "o-", color=col[loss], label=lab)
    for a, t, yl in ((ax[0], "eroarea de urmarire", "CTE p95 [m]"),
                     (ax[1], "timpul de parcurs", "timp [s]"),
                     (ax[2], "opriri de siguranta (watchdog)", "opriri / rulare")):
        a.set_title(t)
        a.set_xlabel("latenta legaturii (un sens) [ms]")
        a.set_ylabel(yl)
        a.grid(alpha=0.3)
        a.legend()
    fig.tight_layout()
    fig.savefig("results/teleop_sweep.png", dpi=130)

    # --- figura 2 (noua): ideal vs realistic la pierdere 0% ---
    fig2, bx = plt.subplots(1, 3, figsize=(14, 4.2))
    fig2.suptitle("Efectul DINAMICII DE ACTUATOR asupra pragului de rupere "
                  "(pierdere 0%): ideal vs. actuator realist",
                  fontweight="bold")
    style = {"ideal": ("-", "#2E73CC"), "realistic": ("--", "#c0392b")}
    for accel in ("ideal", "realistic"):
        sel = [r for r in rows if r["accel"] == accel and r["loss"] == 0.0]
        x = [r["lat"] for r in sel]
        ls, c = style[accel]
        bx[0].plot(x, [r["cte_p95"] for r in sel], "o" + ls, color=c, label=accel)
        bx[1].plot(x, [r["time_s"] for r in sel], "o" + ls, color=c, label=accel)
        bx[2].plot(x, [r["stops"] for r in sel], "o" + ls, color=c, label=accel)
    for a, t, yl in ((bx[0], "eroarea de urmarire", "CTE p95 [m]"),
                     (bx[1], "timpul de parcurs", "timp [s]"),
                     (bx[2], "opriri de siguranta (watchdog)", "opriri / rulare")):
        a.set_title(t)
        a.set_xlabel("latenta legaturii (un sens) [ms]")
        a.set_ylabel(yl)
        a.grid(alpha=0.3)
        a.legend()
    fig2.tight_layout()
    fig2.savefig("results/teleop_sweep_accel.png", dpi=130)
    print("[ok] results/sweep.csv + teleop_sweep.png + teleop_sweep_accel.png")


if __name__ == "__main__":
    main()
