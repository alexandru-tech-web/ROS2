#!/usr/bin/env python3
"""demo_sil.py -- M20: MLP vs regresie liniara pe datele mele de latenta.

Headless, fara argumente. Prezice log10(rtt_ms) din feature-uri standardizate cu
DOUA modele: o regresie liniara (baza) si MLP-ul nostru cu un strat ascuns. Pe
acelasi split train/test raporteaza RMSE-urile celor doua.

NOTA ONESTA (vezi si teorie.md sec.8): pe acest semnal feature-urile explica
log10(rtt) aproape liniar (latenta de baza si pierderea sunt aditive in log), deci
MLP-ul NU bate clar regresia liniara -- uneori e mai prost cu N mic, fiindca are
mai multi parametri de potrivit pe acelasi semnal simplu. Asta e exact lectia:
o retea neuronala isi merita complexitatea doar cand exista neliniaritate de
exploatat SI date suficiente; la N mic / semnal liniar, modelul simplu castiga.

Daca matplotlib exista, emite fig_mlp_vs_liniar.png; altfel tipareste numeric.
Datele sunt SINTETICE (semanate din C1/M).
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from mlp_core import MLP  # noqa: E402
from date_sar import make_latency_dataset  # noqa: E402
from utils import standardize, train_test_split, add_bias, rmse, maybe_savefig  # noqa: E402

FEATURES = ["loss_pct", "base_lat_ms", "jitter_ms", "distance_m"]


def _ols_fit_predict(X_tr, y_tr, X_te):
    """Regresie liniara cu bias (ecuatii normale), de baza."""
    Phi = add_bias(X_tr)
    w, *_ = np.linalg.lstsq(Phi, y_tr, rcond=None)
    return add_bias(X_te) @ w


def main():
    df = make_latency_dataset(n_per_cond=150, seed=0)
    X = df[FEATURES].to_numpy(dtype=float)
    y = np.log10(df["rtt_ms"].to_numpy(dtype=float))

    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_frac=0.25, seed=0)
    Xtr_s, Xte_s, _, _ = standardize(X_tr, X_te)

    # baza: regresie liniara
    y_lin = _ols_fit_predict(Xtr_s, y_tr, Xte_s)
    rmse_lin = rmse(y_te, y_lin)

    # MLP cu un strat ascuns
    mlp = MLP(n_hidden=16, activation="tanh", lr=0.05, l2=1e-4,
              n_iter=4000, seed=0).fit(Xtr_s, y_tr)
    y_mlp = mlp.predict(Xte_s)
    rmse_mlp = rmse(y_te, y_mlp)

    print("Tinta: log10(rtt_ms). Split 75/25, feature-uri standardizate pe TRAIN.")
    print("  RMSE regresie liniara (baza) : %.4f" % rmse_lin)
    print("  RMSE MLP (1 strat ascuns)    : %.4f" % rmse_mlp)
    if rmse_mlp <= rmse_lin:
        verdict = "MLP usor mai bun, dar marja e mica -- semnal aproape liniar."
    else:
        verdict = ("MLP NU bate liniarul -- mai multi parametri pe un semnal "
                   "aproape liniar la N mic. Modelul simplu castiga.")
    print("  NOTA ONESTA: %s" % verdict)

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(1, 2, figsize=(11, 4))
        for a, yp, titlu, r in [(ax[0], y_lin, "regresie liniara", rmse_lin),
                                (ax[1], y_mlp, "MLP (1 strat)", rmse_mlp)]:
            a.scatter(y_te, yp, s=14, alpha=0.5)
            lo = min(y_te.min(), yp.min())
            hi = max(y_te.max(), yp.max())
            a.plot([lo, hi], [lo, hi], "k--", lw=1)
            a.set_xlabel("log10(rtt) real")
            a.set_ylabel("log10(rtt) prezis")
            a.set_title("%s  RMSE=%.3f" % (titlu, r))
        fig.suptitle("MLP vs liniar pe latenta (date SINTETICE)")
        here = os.path.dirname(os.path.abspath(__file__))
        maybe_savefig(fig, os.path.join(here, "fig_mlp_vs_liniar.png"))
    except Exception as e:
        print("[fig] matplotlib indisponibil (%s) -- doar numeric." % e)


if __name__ == "__main__":
    main()
