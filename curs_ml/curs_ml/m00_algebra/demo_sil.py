#!/usr/bin/env python3
"""demo_sil.py -- structura de covarianta a feature-urilor de telemetrie (M00).

Demonstratie HEADLESS, fara argumente. Aplica primitivele din nucleu pe date
SINTETICE (semanate din campania reala C1; vezi date_sar.py si ONESTITATE in
teorie.md) ca sa arate ideea centrala a modulului:

  - construieste matricea de covarianta a coloanelor NUMERICE din
    date_sar.make_latency_dataset();
  - gaseste vectorul propriu dominant prin iteratia puterii din nucleu -> directia
    principala de variatie a feature-urilor de telemetrie;
  - confirma cu numpy.linalg.eigh (acelasi vector propriu, aceeasi valoare proprie);
  - daca matplotlib exista, emite figuri (fig_*.png) prin utils.maybe_savefig;
    altfel tipareste totul numeric.

Ruleaza: /home/ubuntu/ros2_ws/.venv_ml/bin/python demo_sil.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from utils import maybe_savefig                       # noqa: E402
from date_sar import make_latency_dataset             # noqa: E402
from algebra_liniara_core import (                    # noqa: E402
    covariance, norm, power_iteration,
)

HERE = os.path.dirname(os.path.abspath(__file__))
# coloane numerice de telemetrie pe care le analizam (din make_latency_dataset)
FEATURES = ["loss_pct", "base_lat_ms", "jitter_ms", "distance_m", "rtt_ms"]


def main():
    print("== M00 demo: structura de covarianta a feature-urilor de telemetrie ==")
    print("DATE SINTETICE (semanate din campania reala C1) -- NU masuratori brute.\n")

    df = make_latency_dataset(n_per_cond=200, seed=0)
    X = df[FEATURES].to_numpy(dtype=float)
    n, d = X.shape
    print("matrice de date X: %d esantioane x %d feature-uri %s" % (n, d, FEATURES))

    # jitter_ms si base_lat_ms pot fi constante pe un subset; standardizam pe coloana
    # ca o covarianta sa fie comparabila intre feature-uri cu scale foarte diferite.
    mean = X.mean(axis=0)
    std = X.std(axis=0)
    std_safe = np.where(std < 1e-12, 1.0, std)
    Xs = (X - mean) / std_safe                         # z-score pe coloane (corelatie)

    C = covariance(Xs)                                 # ~ matrice de corelatie (date standardizate)
    print("\nmatrice de covarianta C (feature-uri standardizate, deci ~ corelatie):")
    with np.printoptions(precision=3, suppress=True):
        print(C)

    # vectorul propriu dominant (directia principala de variatie) prin iteratia puterii
    lam_pi, v_pi = power_iteration(C, num_iter=5000, seed=1)
    # referinta: numpy.linalg.eigh (matrice simetrica)
    w, V = np.linalg.eigh(C)
    lam_ref, v_ref = w[-1], V[:, -1]
    # fixam un semn comun (cea mai mare componenta in modul pozitiva) pentru lizibilitate
    if v_pi[np.argmax(np.abs(v_pi))] < 0:
        v_pi = -v_pi

    cosang = abs(float(v_pi @ v_ref)) / (norm(v_pi, 2) * norm(v_ref, 2))
    total_var = float(np.sum(w))
    frac = lam_pi / total_var if total_var > 0 else 0.0

    print("\n-- vector propriu DOMINANT (directia principala de variatie) --")
    print("valoare proprie (iteratia puterii) : %.4f" % lam_pi)
    print("valoare proprie (numpy.linalg.eigh): %.4f" % lam_ref)
    print("acord directie |cos(pi, eigh)|     : %.6f (1 = identice)" % cosang)
    print("varianta explicata de aceasta axa  : %.1f%% din total" % (100.0 * frac))
    print("\nincarcari (loadings) pe feature-uri pentru axa dominanta:")
    order = np.argsort(-np.abs(v_pi))
    for i in order:
        print("  %-12s : %+.3f" % (FEATURES[i], v_pi[i]))
    dom = FEATURES[order[0]]
    print("\nINTERPRETARE: axa principala e dominata de '%s'; feature-urile cu" % dom)
    print("incarcari de acelasi semn variaza impreuna (covariaza pozitiv), cele cu")
    print("semn opus variaza in contrasens. Asta e structura pe care PCA (M16) o")
    print("foloseste ca sa comprime telemetria pastrand directiile de variatie maxima.")

    # ---- figuri (optionale) ----
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        # fig 1: heatmap al matricei de covarianta/corelatie
        fig1, ax1 = plt.subplots(figsize=(5.2, 4.4))
        im = ax1.imshow(C, cmap="coolwarm", vmin=-1, vmax=1)
        ax1.set_xticks(range(d)); ax1.set_xticklabels(FEATURES, rotation=45, ha="right")
        ax1.set_yticks(range(d)); ax1.set_yticklabels(FEATURES)
        for i in range(d):
            for j in range(d):
                ax1.text(j, i, "%.2f" % C[i, j], ha="center", va="center", fontsize=7)
        ax1.set_title("M00: covarianta feature-uri telemetrie (standardizate)")
        fig1.colorbar(im, ax=ax1, fraction=0.046, pad=0.04)
        maybe_savefig(fig1, os.path.join(HERE, "fig_covarianta.png"))

        # fig 2: incarcarile axei dominante (bar chart)
        fig2, ax2 = plt.subplots(figsize=(5.6, 3.6))
        idx = np.arange(d)
        ax2.bar(idx, v_pi[order], color="steelblue")
        ax2.axhline(0, color="black", lw=0.8)
        ax2.set_xticks(idx)
        ax2.set_xticklabels([FEATURES[i] for i in order], rotation=45, ha="right")
        ax2.set_ylabel("incarcare pe axa dominanta")
        ax2.set_title("M00: directia principala de variatie (%.0f%% varianta)"
                      % (100.0 * frac))
        maybe_savefig(fig2, os.path.join(HERE, "fig_axa_dominanta.png"))
    except Exception as e:  # pragma: no cover - depinde de mediu
        print("\n[fig] matplotlib indisponibil sau eroare la plot (%s) -- doar numeric." % e)

    # acordul nucleu <-> referinta e conditia de succes a demonstratiei
    if abs(cosang - 1.0) > 1e-5 or abs(lam_pi - lam_ref) / abs(lam_ref) > 1e-5:
        print("\nATENTIE: nucleul nu coincide cu numpy.linalg.eigh -- verifica.")
        return 1
    print("\nDemo OK: iteratia puterii din nucleu recupereaza axa dominanta (acord cu eigh).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
