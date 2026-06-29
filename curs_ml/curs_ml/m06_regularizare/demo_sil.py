#!/usr/bin/env python3
"""demo_sil.py -- M06: traseul coeficientilor Ridge si Lasso vs lambda, pe datele mele.

Headless, fara argumente. Pe make_latency_dataset construieste feature-uri
standardizate (loss_pct, base_lat_ms, jitter_ms, distance_m) ca sa prezica
log10(rtt_ms) centrat, apoi traseaza norma/valorile coeficientilor cand lambda
creste. Arata cum Ridge micsoreaza neted si Lasso aduce coeficienti la 0.

Daca matplotlib exista, emite fig_trasee_coef.png; altfel tipareste numeric.
Datele sunt SINTETICE (semanate din C1/M).
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from regularizare_core import ridge_fit, lasso_fit  # noqa: E402
from date_sar import make_latency_dataset  # noqa: E402
from utils import standardize, maybe_savefig  # noqa: E402

FEATURES = ["loss_pct", "base_lat_ms", "jitter_ms", "distance_m"]


def build_xy(seed=0):
    df = make_latency_dataset(n_per_cond=150, seed=seed)
    X = df[FEATURES].to_numpy(dtype=float)
    y = np.log10(df["rtt_ms"].to_numpy(dtype=float))
    Xs, _, _, _ = standardize(X)
    y = y - y.mean()
    return Xs, y


def main():
    Xs, y = build_xy()
    lams = np.logspace(-2, 3, 20)
    ridge_paths = np.array([ridge_fit(Xs, y, lam) for lam in lams])      # (n_lam, p)
    lasso_paths = np.array([lasso_fit(Xs, y, lam, n_iter=1000) for lam in lams])

    print("Trasee de coeficienti (feature-uri:", FEATURES, ")")
    print("Ridge: norma coef la lam mic (%.2g) = %.3f; la lam mare (%.0f) = %.3f"
          % (lams[0], np.linalg.norm(ridge_paths[0]), lams[-1], np.linalg.norm(ridge_paths[-1])))
    nz_small = int(np.sum(np.abs(lasso_paths[0]) > 1e-6))
    nz_big = int(np.sum(np.abs(lasso_paths[-1]) > 1e-6))
    print("Lasso: feature-uri nenule la lam mic = %d; la lam mare = %d (sparsitate)"
          % (nz_small, nz_big))

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4))
        for j, name in enumerate(FEATURES):
            a1.plot(lams, ridge_paths[:, j], marker="o", ms=3, label=name)
            a2.plot(lams, lasso_paths[:, j], marker="o", ms=3, label=name)
        for ax, t in ((a1, "Ridge (L2)"), (a2, "Lasso (L1)")):
            ax.set_xscale("log"); ax.set_xlabel("lambda"); ax.set_ylabel("coeficient")
            ax.set_title(t); ax.axhline(0, color="k", lw=0.6); ax.legend(fontsize=7)
        fig.suptitle("Trasee de coeficienti vs regularizare (date SINTETICE)")
        here = os.path.dirname(os.path.abspath(__file__))
        maybe_savefig(fig, os.path.join(here, "fig_trasee_coef.png"))
    except Exception as e:
        print("[fig] matplotlib indisponibil (%s) -- doar numeric." % e)


if __name__ == "__main__":
    main()
