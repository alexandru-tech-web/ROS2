#!/usr/bin/env python3
"""demo_sil.py -- M02 pe date_sar: GD vs Adam pe o regresie de latenta.

Demonstratie headless, fara argumente. Antrenam o regresie liniara care prezice
RTT (log-ms) din cateva trasaturi de retea, minimizand eroarea patratica cu doi
optimizatori implementati in nucleu (optimizare_core): coborare pe gradient (GD)
si Adam. Comparam:
  - viteza de convergenta (pierdere vs iteratie) -> fig_convergenta.png;
  - efectul standardizarii (conditionarea problemei).

ONESTITATE: datele (make_latency_dataset) sunt SINTETICE, semanate din campania
reala C1 (p95 RTT si pierdere DDS vs Zenoh sub tc netem). Nu sunt masuratori brute.

Ruleaza:
  /home/ubuntu/ros2_ws/.venv_ml/bin/python demo_sil.py
Emite fig_*.png daca matplotlib exista; altfel tipareste numeric.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from optimizare_core import adam, condition_number, gradient_descent
from utils import add_bias, maybe_savefig, r2_score, rng, standardize, train_test_split

from date_sar import make_latency_dataset

HERE = os.path.dirname(os.path.abspath(__file__))


def _build_xy(seed=0):
    """Construieste (X, y) din make_latency_dataset.

    Tinta y = log(rtt_ms) (lognormal -> aproape liniar in features dupa log).
    Trasaturi: loss_pct, base_lat_ms, jitter_ms, distance_m, mw_zenoh.
    """
    df = make_latency_dataset(n_per_cond=200, seed=seed)
    feats = ["loss_pct", "base_lat_ms", "jitter_ms", "distance_m"]
    X = df[feats].to_numpy(dtype=float)
    mw = (df["middleware"].to_numpy() == "Zenoh").astype(float).reshape(-1, 1)
    X = np.hstack([X, mw])
    feats = feats + ["mw_zenoh"]
    y = np.log(df["rtt_ms"].to_numpy(dtype=float))
    return X, y, feats


def _fit_loss(Xtr, ytr):
    """Returneaza (grad, value) pentru pierderea patratica medie cu bias inclus."""
    n = Xtr.shape[0]

    def grad(w):
        return (2.0 / n) * Xtr.T @ (Xtr @ w - ytr)

    def value(w):
        return float(np.mean((Xtr @ w - ytr) ** 2))

    return grad, value


def main():
    print("=== M02 demo_sil: GD vs Adam pe regresia de latenta (date sintetice C1) ===\n")
    X, y, feats = _build_xy(seed=0)
    Xtr_raw, Xte_raw, ytr, yte = train_test_split(X, y, test_frac=0.25, seed=0)

    # standardizare (statistici de pe TRAIN) -> imbunatateste conditionarea
    Xtr_s, Xte_s, _, _ = standardize(Xtr_raw, Xte_raw)
    Xtr = add_bias(Xtr_s)
    Xte = add_bias(Xte_s)

    # conditionarea matricei normale, brut vs standardizat (de ce conteaza scalarea)
    G_raw = add_bias(Xtr_raw)  # X brut (nestandardizat) + coloana de bias
    kappa_raw = condition_number(G_raw.T @ G_raw / G_raw.shape[0] + 1e-9 * np.eye(G_raw.shape[1]))
    kappa_std = condition_number(Xtr.T @ Xtr / Xtr.shape[0])
    print("conditionarea X^T X / n: brut kappa=%.1f  vs  standardizat kappa=%.1f" %
          (kappa_raw, kappa_std))
    print("(o kappa mai mica = GD converge mai repede; de aici standardizarea)\n")

    grad, value = _fit_loss(Xtr, ytr)
    w0 = np.zeros(Xtr.shape[1])

    n_iter = 200
    w_gd, hist_gd = gradient_descent(grad, w0, eta=0.3, n_iter=n_iter, value=value)
    w_adam, hist_adam = adam(grad, w0, alpha=0.1, n_iter=n_iter, value=value)

    r2_gd = r2_score(yte, Xte @ w_gd)
    r2_adam = r2_score(yte, Xte @ w_adam)
    print("dupa %d iteratii:" % n_iter)
    print("  GD  : pierdere train start=%.4f -> final=%.5f   R2 test=%.4f" %
          (hist_gd[0], hist_gd[-1], r2_gd))
    print("  Adam: pierdere train start=%.4f -> final=%.5f   R2 test=%.4f" %
          (hist_adam[0], hist_adam[-1], r2_adam))

    # iteratia la care fiecare atinge 1% peste pierderea finala a lui GD (proxy convergenta)
    target = hist_gd[-1] * 1.01

    def first_below(hist, t):
        for i, v in enumerate(hist):
            if v <= t:
                return i
        return len(hist)

    it_gd = first_below(hist_gd, target)
    it_adam = first_below(hist_adam, target)
    print("\niteratii pana la pragul de convergenta (1%% peste pierderea finala GD):")
    print("  GD=%d   Adam=%d" % (it_gd, it_adam))

    # ---- figura: curba de convergenta (pierdere vs iteratie) ----
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(7, 4.5))
        ax.plot(range(len(hist_gd)), hist_gd, label="GD (eta=0.3)", lw=2)
        ax.plot(range(len(hist_adam)), hist_adam, label="Adam (alpha=0.1)", lw=2)
        ax.set_yscale("log")
        ax.set_xlabel("iteratie")
        ax.set_ylabel("pierdere patratica medie (train, scala log)")
        ax.set_title("M02: convergenta GD vs Adam pe regresia de latenta (date sintetice C1)")
        ax.legend()
        ax.grid(True, which="both", alpha=0.3)
        maybe_savefig(fig, os.path.join(HERE, "fig_convergenta.png"))

        # a doua figura: predictie vs adevar pe test (Adam)
        fig2, ax2 = plt.subplots(figsize=(5, 5))
        yhat = Xte @ w_adam
        ax2.scatter(yte, yhat, s=8, alpha=0.4)
        lim = [min(yte.min(), yhat.min()), max(yte.max(), yhat.max())]
        ax2.plot(lim, lim, "k--", lw=1, label="ideal")
        ax2.set_xlabel("log(rtt) adevarat (test)")
        ax2.set_ylabel("log(rtt) prezis (Adam)")
        ax2.set_title("M02: predictie vs adevar (R2=%.3f)" % r2_adam)
        ax2.legend()
        maybe_savefig(fig2, os.path.join(HERE, "fig_predictie.png"))
    except Exception as e:  # pragma: no cover - depinde de mediu
        print("[fig] matplotlib indisponibil, sar figurile: %s" % e)
        print("histograma pierderii GD (esantion la 0,50,100,150,199):",
              [round(hist_gd[i], 5) for i in [0, 50, 100, 150, 199]])

    print("\nDEMO OK.")
    return 0


if __name__ == "__main__":
    main()
    sys.exit(0)
