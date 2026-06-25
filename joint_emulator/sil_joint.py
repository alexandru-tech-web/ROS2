#!/usr/bin/env python3
"""sil_joint.py -- mediul de simulare COMPLET al bancului, fara ROS:
scenarii numite, urme CSV, bilant in consola. Acelasi tipar ca sil_run /
sil_teleop din restul repo-ului.

  python3 sil_joint.py echilibru                # treapta + impedanta fixa
  python3 sil_joint.py pacient_spastic          # B = membrul cu catch
  python3 sil_joint.py delay_sweep              # E_max vs latenta (fix vs adaptiv)
  python3 sil_joint.py adaptiv_vs_fix --ms 60   # duelul la o latenta data
Optiuni: --ms --jit --loss --t_end --trace cale.csv --seed
"""
import argparse
import csv
import math
import os

from joint_core import (ImpedanceLaw, VirtualLimb, PairSim, EnergyMonitor,
                        run_equilibrium)
from teleimpedance import DegradedMeasure, AdaptiveImpedance, run_teleimpedance

TAU_STEP = lambda t: 0.5 if t > 0.2 else 0.0
TAU_SINE = lambda t: 0.8 * math.sin(2 * math.pi * 0.5 * t)


def scrie_trace(path, trace, header):
    if not path:
        return
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        for row in trace:
            w.writerow([round(x, 6) for x in row])
    print(f"[ok] urma scrisa: {path} ({len(trace)} esantioane)")


def sc_echilibru(a):
    law = ImpedanceLaw(k_nm_rad=10, b_nms_rad=0.6, tau_max=2.0)
    sim, mon, tr = run_equilibrium(TAU_STEP, law, t_end=a.t_end)
    print(f"echilibru: th_final={sim.th:.4f} rad (teoretic 0.0500), "
          f"E_B={mon.e_max:.4f} J")
    scrie_trace(a.trace, tr, ["t", "th", "om", "tau_a", "tau_b"])


def sc_pacient(a):
    limb = VirtualLimb(k=4, b=0.3, catch_om=0.8, catch_gain=5, tau_max=3)
    sim, mon, tr = run_equilibrium(TAU_SINE, limb_as_law(limb), t_end=a.t_end)
    om_max = max(abs(r[2]) for r in tr)
    print(f"pacient_spastic: om_max={om_max:.2f} rad/s "
          f"(catch la 0.8), E_B={mon.e_max:.3f} J")
    scrie_trace(a.trace, tr, ["t", "th", "om", "tau_a", "tau_b"])


def limb_as_law(limb):
    class L:
        def torque(self, th, om, dt=None):
            return limb.torque(th, om)
    return L()


def sc_delay_sweep(a):
    print("latenta_ms,E_fix_J,E_adaptiv_J")
    rows = []
    for ms in [0, 10, 20, 30, 40, 50, 60, 80]:
        link1 = DegradedMeasure(ms=ms, jit=a.jit, loss=a.loss, seed=a.seed)
        law_f = ImpedanceLaw(k_nm_rad=40, b_nms_rad=1.2, tau_max=8.0)
        _, m1, _ = run_teleimpedance(law_f, link1, TAU_STEP, t_end=a.t_end)
        link2 = DegradedMeasure(ms=ms, jit=a.jit, loss=a.loss, seed=a.seed)
        law_a = AdaptiveImpedance(k0=40, b0=1.2, tau_max=8.0)
        _, m2, _ = run_teleimpedance(law_a, link2, TAU_STEP,
                                     t_end=a.t_end, adaptive=True)
        print(f"{ms},{m1.e_max:.3f},{m2.e_max:.3f}")
        rows.append((ms, m1.e_max, m2.e_max))
    scrie_trace(a.trace, rows, ["latenta_ms", "e_fix", "e_adaptiv"])


def sc_duel(a):
    link1 = DegradedMeasure(ms=a.ms, jit=a.jit, loss=a.loss, seed=a.seed)
    law_f = ImpedanceLaw(k_nm_rad=40, b_nms_rad=1.2, tau_max=8.0)
    s1, m1, t1 = run_teleimpedance(law_f, link1, TAU_STEP, t_end=a.t_end)
    link2 = DegradedMeasure(ms=a.ms, jit=a.jit, loss=a.loss, seed=a.seed)
    law_a = AdaptiveImpedance(k0=40, b0=1.2, tau_max=8.0)
    s2, m2, t2 = run_teleimpedance(law_a, link2, TAU_STEP,
                                   t_end=a.t_end, adaptive=True)
    print(f"adaptiv_vs_fix la {a.ms} ms (jit={a.jit}, loss={a.loss}):")
    print(f"  FIX:     E_max={m1.e_max:9.3f} J  th_final={s1.th:8.3f} rad")
    print(f"  ADAPTIV: E_max={m2.e_max:9.3f} J  th_final={s2.th:8.3f} rad"
          f"  (K_ef={law_a.k_ef:.1f}, B_ef={law_a.b_ef:.2f})")
    if a.trace:
        scrie_trace(a.trace, [(r1[0], r1[1], r2[1]) for r1, r2 in zip(t1, t2)],
                    ["t", "th_fix", "th_adaptiv"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scenariu", choices=["echilibru", "pacient_spastic",
                                         "delay_sweep", "adaptiv_vs_fix"])
    ap.add_argument("--ms", type=float, default=60.0)
    ap.add_argument("--jit", type=float, default=0.0)
    ap.add_argument("--loss", type=float, default=0.0)
    ap.add_argument("--t_end", type=float, default=3.0)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--trace", default=None)
    a = ap.parse_args()
    {"echilibru": sc_echilibru, "pacient_spastic": sc_pacient,
     "delay_sweep": sc_delay_sweep, "adaptiv_vs_fix": sc_duel}[a.scenariu](a)


if __name__ == "__main__":
    main()
