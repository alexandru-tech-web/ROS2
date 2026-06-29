#!/usr/bin/env python3
"""demo_sil.py -- M07: curba de invatare pe datele mele de latenta.

Headless, fara argumente. Prezice log10(rtt_ms) din feature-uri standardizate cu
un model liniar si traseaza eroarea de TRAIN vs VALIDARE pe masura ce creste setul
de antrenare -- arata unde supra-invata (gol mare train-validare) si unde se aseaza.

Daca matplotlib exista, emite fig_curba_invatare.png; altfel tipareste numeric.
Datele sunt SINTETICE (semanate din C1/M).
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from evaluare_validare_core import learning_curve, cross_val_score, cv_summary, _ols_fit_predict  # noqa: E402
from date_sar import make_latency_dataset  # noqa: E402
from utils import standardize, maybe_savefig  # noqa: E402

FEATURES = ["loss_pct", "base_lat_ms", "jitter_ms", "distance_m"]


def main():
    df = make_latency_dataset(n_per_cond=150, seed=0)
    X = df[FEATURES].to_numpy(dtype=float)
    y = np.log10(df["rtt_ms"].to_numpy(dtype=float))
    Xs, _, _, _ = standardize(X)

    summ = cv_summary(cross_val_score(Xs, y, _ols_fit_predict, k=5, seed=0))
    print("RMSE (log10 rtt) 5-fold: %.4f +/- %.4f" % (summ["mean"], summ["std"]))

    sizes = [10, 25, 50, 100, 200, 400, 800]
    tr, va = learning_curve(Xs, y, _ols_fit_predict, train_sizes=sizes, seed=0)
    print("marime  train_rmse  val_rmse")
    for m, a, b in zip(sizes, tr, va):
        print("  %4d    %.4f     %.4f" % (m, a, b))

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.plot(sizes, tr, marker="o", label="train RMSE")
        ax.plot(sizes, va, marker="s", label="validare RMSE")
        ax.set_xlabel("marimea setului de antrenare"); ax.set_ylabel("RMSE (log10 rtt)")
        ax.set_title("Curba de invatare (date SINTETICE)"); ax.legend()
        here = os.path.dirname(os.path.abspath(__file__))
        maybe_savefig(fig, os.path.join(here, "fig_curba_invatare.png"))
    except Exception as e:
        print("[fig] matplotlib indisponibil (%s) -- doar numeric." % e)


if __name__ == "__main__":
    main()
