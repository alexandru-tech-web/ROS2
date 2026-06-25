#!/usr/bin/env python3
"""plot_joint.py -- figurile bancului din mediul de simulare:
  figs/joint_sweep.png  E_max vs latenta: fix-total-remote vs adaptiv+
                        amortizare locala (FIGURA-CHEIE pentru C4)
  figs/joint_duel.png   pozitia in timp la 60 ms: fix vs adaptiv
Ruleaza: python3 plot_joint.py
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from joint_core import ImpedanceLaw
from teleimpedance import DegradedMeasure, AdaptiveImpedance, run_teleimpedance

TAU = lambda t: 0.5 if t > 0.2 else 0.0
os.makedirs("figs", exist_ok=True)

# ---- fig 1: matura de latenta ----
mss = [0, 10, 20, 30, 40, 50, 60, 80, 100, 120]
e_fix, e_ad = [], []
for ms in mss:
    _, m1, _ = run_teleimpedance(ImpedanceLaw(k_nm_rad=40, b_nms_rad=1.2,
                                              tau_max=8.0),
                                 DegradedMeasure(ms=ms, seed=42), TAU,
                                 t_end=4.0)
    _, m2, _ = run_teleimpedance(AdaptiveImpedance(k0=40, b0=1.2, tau_max=8.0),
                                 DegradedMeasure(ms=ms, seed=42), TAU,
                                 t_end=4.0, adaptive=True)
    e_fix.append(max(m1.e_max, 1e-4))
    e_ad.append(max(m2.e_max, 1e-4))

fig, ax = plt.subplots(figsize=(7.2, 4.2))
ax.semilogy(mss, e_fix, "o--", color="crimson",
            label="impedanta fixa, totul prin link")
ax.semilogy(mss, e_ad, "s-", color="tab:green",
            label="K adaptiv prin link + amortizare LOCALA")
ax.set_xlabel("latenta legaturii [ms]")
ax.set_ylabel("energia injectata de motorul B [J] (log)")
ax.set_title("Tele-impedanta sub legatura degradata: de ce bucla rapida\n"
             "traieste langa drive (Pi), iar prin retea trece doar referinta")
ax.grid(alpha=0.3, which="both")
ax.legend()
fig.tight_layout(); fig.savefig("figs/joint_sweep.png", dpi=150)

# ---- fig 2: duelul in timp la 60 ms ----
_, _, t_fx = run_teleimpedance(ImpedanceLaw(k_nm_rad=40, b_nms_rad=1.2,
                                            tau_max=8.0),
                               DegradedMeasure(ms=60, seed=42), TAU,
                               t_end=3.0)
law_a = AdaptiveImpedance(k0=40, b0=1.2, tau_max=8.0)
_, _, t_ad = run_teleimpedance(law_a, DegradedMeasure(ms=60, seed=42), TAU,
                               t_end=3.0, adaptive=True)
fig, ax = plt.subplots(figsize=(7.2, 4.0))
ax.plot([r[0] for r in t_fx], [r[1] for r in t_fx], color="crimson",
        lw=1.2, label="fix (instabil)")
ax.plot([r[0] for r in t_ad], [r[1] for r in t_ad], color="tab:green",
        lw=1.8, label=f"adaptiv (stabil, K_ef={law_a.k_ef:.1f})")
ax.axhline(0.5 / law_a.k_ef, color="gray", ls=":", lw=1,
           label="echilibrul teoretic tau/K_ef")
ax.set_ylim(-1.5, 1.5)
ax.set_xlabel("t [s]"); ax.set_ylabel("pozitia articulatiei [rad]")
ax.set_title("Aceeasi articulatie, 60 ms latenta: fix vs adaptiv")
ax.grid(alpha=0.3); ax.legend()
fig.tight_layout(); fig.savefig("figs/joint_duel.png", dpi=150)
print("[ok] figs/joint_sweep.png + figs/joint_duel.png")
