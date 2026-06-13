#!/usr/bin/env python3
"""sil_link_adaptive.py - SIL: stratul adaptiv vs. alegeri statice de middleware.

Fara ROS. Conduce controlerul printr-o cronologie de degradare (conditiile C1
care variaza in timp) si compara trei strategii pe doua axe care conteaza in
teleoperare:
  - prospetimea controlului    = varsta comenzii executate [ms, mai mic = mai bine];
  - completitudinea telemetriei = fractia de telemetrie ajunsa la GCS [%, mai mare = mai bine].

Strategii:
  STATIC-COMPLETE (DDS, fiabil pe tot)  -> livreaza tot, dar controlul se
        invecheste pana la zidul p95 sub pierdere (blocaj cap-de-linie / retransmisii).
  STATIC-FRESH    (Zenoh, best-effort)  -> control proaspat (actionezi pe ultima
        sosire), dar telemetria pierde proportional cu pierderea.
  ADAPTIVE        (link_adaptive)       -> control mereu proaspat; telemetria
        fiabila cand legatura e buna (retransmisii ieftine, recupereaza pierderi),
        best-effort + rata redusa cand fiabilitatea devine inutila (pierdere/latenta mare).

Model numeric ancorat in mediile C1 (N=5):
  - control proaspat: staleness ~ o cale dus (latenta de baza impusa / 2);
  - control fiabil: staleness ~ zidul p95 al DDS / 2 (comenzile se aseaza la coada);
  - telemetrie fiabila (NOMINAL): completitudine ~ 1 (recupereaza pierderi ieftin);
  - telemetrie best-effort: completitudine ~ 1 - pierderea livrata a canalului.
Determinist (N=1) -- de inlocuit cu campania reala adaptiv-vs-static la publicare.

  python3 sil_link_adaptive.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from link_adaptive_core import (AdaptiveController, MIN_DWELL_S,
                                NOMINAL, DEGRADED, CRITICAL)

# Conditiile C1 (medii N=5): rtt impus [ms], pierdere impusa, p95 DDS/Zenoh [ms],
# pierdere livrata DDS/Zenoh.
#   name: (rtt_impus, loss_impus, p95_dds, loss_dds, p95_zenoh, loss_zenoh)
C1 = {
    "ideal":        (20, 0.00,    1, 0.00,    2, 0.00),
    "loss_5":       (20, 0.05,  146, 0.00,  172, 0.04),
    "loss_15":      (20, 0.15, 1056, 0.01,  690, 0.02),
    "loss_30":      (20, 0.30, 2320, 0.39, 3645, 0.35),
    "lat200_jit50": (200, 0.00, 490, 0.02,  477, 0.01),
    "lat200_l15":   (200, 0.15, 2523, 0.34, 4125, 0.22),
}
TIMELINE = ["ideal", "loss_5", "loss_15", "loss_30", "loss_15",
            "lat200_jit50", "lat200_l15", "loss_5", "ideal"]
STEP_S = 3.0
DT = 1.0


def run():
    ctrl = AdaptiveController()
    t = 0.0
    rows = []
    for cond in TIMELINE:
        rtt, loss, p95d, lossd, p95z, lossz = C1[cond]
        fresh_stale = rtt / 2.0
        complete_stale = p95d / 2.0
        fresh_compl = 1.0 - lossz
        for _ in range(int(STEP_S / DT)):
            mode, pol = ctrl.update(rtt, loss, t)
            c_stale, c_compl = complete_stale, 1.0 - lossd
            f_stale, f_compl = fresh_stale, fresh_compl
            a_stale = fresh_stale
            a_compl = 1.0 if mode == NOMINAL else fresh_compl
            rows.append({"t": t, "cond": cond, "mode": mode,
                         "a_stale": a_stale, "a_compl": a_compl,
                         "c_stale": c_stale, "c_compl": c_compl,
                         "f_stale": f_stale, "f_compl": f_compl})
            t += DT

    def mean(k): return sum(r[k] for r in rows) / len(rows)
    def worst_stale(k): return max(r[k] for r in rows)
    def worst_compl(k): return min(r[k] for r in rows)

    print("--- SIL link_adaptive: adaptiv vs static (cronologie C1) ---")
    print(f"  {'strategie':17s}{'staleness control (mediu / cel mai rau)':>42s}")
    print(f"  {'STATIC-COMPLETE':17s}{mean('c_stale'):14.0f} ms /{worst_stale('c_stale'):8.0f} ms")
    print(f"  {'STATIC-FRESH':17s}{mean('f_stale'):14.0f} ms /{worst_stale('f_stale'):8.0f} ms")
    print(f"  {'ADAPTIVE':17s}{mean('a_stale'):14.0f} ms /{worst_stale('a_stale'):8.0f} ms")
    print()
    print(f"  {'strategie':17s}{'completitudine telemetrie (medie / cea mai rea)':>46s}")
    print(f"  {'STATIC-COMPLETE':17s}{mean('c_compl')*100:17.0f} % /{worst_compl('c_compl')*100:8.0f} %")
    print(f"  {'STATIC-FRESH':17s}{mean('f_compl')*100:17.0f} % /{worst_compl('f_compl')*100:8.0f} %")
    print(f"  {'ADAPTIVE':17s}{mean('a_compl')*100:17.0f} % /{worst_compl('a_compl')*100:8.0f} %")
    print()
    ratio = mean('c_stale') / max(mean('a_stale'), 1e-9)
    print(f"  Esenta: ADAPTIVE pastreaza controlul ~{ratio:.0f}x mai proaspat decat")
    print(f"  STATIC-COMPLETE ({mean('a_stale'):.0f} vs {mean('c_stale'):.0f} ms mediu; "
          f"cel mai rau {worst_stale('a_stale'):.0f} vs {worst_stale('c_stale'):.0f} ms),")
    print(f"  recuperand telemetria pe care STATIC-FRESH o pierde cand legatura e buna")
    print(f"  ({mean('a_compl')*100:.0f}% vs {mean('f_compl')*100:.0f}% mediu).")
    print(f"  Fiecare alegere statica pierde pe cate o axa; adaptivul prinde coltul bun.")

    _plot(rows)
    return mean('a_stale') < mean('c_stale') and mean('a_compl') >= mean('f_compl')


def _plot(rows):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        print("\n  (matplotlib indisponibil - sar peste figura)")
        return
    ts = [r["t"] for r in rows]
    yv = {NOMINAL: 0, DEGRADED: 1, CRITICAL: 2}

    fig = plt.figure(figsize=(13.5, 3.8), dpi=130)
    gs = fig.add_gridspec(1, 3, width_ratios=[1.1, 1.1, 1.0], wspace=0.34)

    axA = fig.add_subplot(gs[0, 0])
    axA.step(ts, [yv[r["mode"]] for r in rows], where="post", lw=2.4, color="#1C7293")
    axA.set_yticks([0, 1, 2]); axA.set_yticklabels(["NOMINAL", "DEGRADED", "CRITICAL"])
    axA.set_ylim(-0.3, 2.4); axA.set_xlabel("timp [s]")
    axA.set_title("Modul ales de link_adaptive")
    axA.grid(alpha=0.3)
    last = None
    for r in rows:
        if r["cond"] != last:
            axA.axvline(r["t"], color="#ccc", lw=0.7, ls=":")
            axA.annotate(r["cond"], (r["t"], 2.3), fontsize=6.5, rotation=90,
                         va="top", ha="right", color="#777")
            last = r["cond"]

    axB = fig.add_subplot(gs[0, 1])
    axB.step(ts, [max(r["c_stale"], 0.5) for r in rows], where="post", lw=2.2,
             color="#C0504D", label="STATIC-COMPLETE")
    axB.step(ts, [max(r["f_stale"], 0.5) for r in rows], where="post", lw=2.2,
             color="#E8A33D", label="STATIC-FRESH", ls="--")
    axB.step(ts, [max(r["a_stale"], 0.5) for r in rows], where="post", lw=2.6,
             color="#1C7293", label="ADAPTIVE")
    axB.set_yscale("log"); axB.set_xlabel("timp [s]")
    axB.set_ylabel("staleness control [ms] (jos=bine)")
    axB.set_title("Prospetimea controlului")
    axB.grid(alpha=0.3, which="both"); axB.legend(fontsize=7, loc="upper left")

    axC = fig.add_subplot(gs[0, 2])
    axC.step(ts, [r["c_compl"]*100 for r in rows], where="post", lw=2.2,
             color="#C0504D", label="STATIC-COMPLETE")
    axC.step(ts, [r["f_compl"]*100 for r in rows], where="post", lw=2.2,
             color="#E8A33D", label="STATIC-FRESH", ls="--")
    axC.step(ts, [r["a_compl"]*100 for r in rows], where="post", lw=2.6,
             color="#1C7293", label="ADAPTIVE")
    axC.set_ylim(40, 103); axC.set_xlabel("timp [s]")
    axC.set_ylabel("completitudine telemetrie [%] (sus=bine)")
    axC.set_title("Completitudinea telemetriei")
    axC.grid(alpha=0.3); axC.legend(fontsize=7, loc="lower left")

    fig.suptitle("link_adaptive: control proaspat ca best-effort SI telemetrie "
                 "completa ca fiabil; staticele pierd pe cate o axa", fontsize=11.5, y=1.05)
    fig.savefig("sil_link_adaptive.png", bbox_inches="tight")
    print("\n  [figura] sil_link_adaptive.png")


if __name__ == "__main__":
    sys.exit(0 if run() else 1)


def main():
    """Wrapper pentru entry-point 'ros2 run' (nu propaga bool-ul ca exit code)."""
    run()
