#!/usr/bin/env python3
"""demo_sil.py -- M18: selectie de model pe datele mele de latenta cu nested CV.

Headless, fara argumente. Problema: prezice log10(rtt_ms) din distanta. Alegem
gradul polinomului cu validare incrucisata IMBRICATA -- nested CV raporteaza o
eroare ONESTA a intregii proceduri de selectie (nu doar minimul optimist al unui
singur CV).

Raporteaza:
  - eroarea de SELECTIE (minimul CV peste grid; optimista, supra-ajustata);
  - eroarea ONESTA (nested CV); golul dintre ele = cat de mult ne-am pacalit;
  - gradul ales de un grid_search pe tot setul.

Daca matplotlib exista, emite fig_selectie_model.png (eroare CV vs grad polinom);
altfel tipareste numeric. Datele sunt SINTETICE (semanate din C1/M).
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from selectie_model_core import (  # noqa: E402
    grid_search_cv, nested_cv, _poly_design,
)
from date_sar import make_latency_dataset  # noqa: E402
from utils import standardize, maybe_savefig  # noqa: E402

GRID_GRADE = [1, 2, 3, 4, 5, 6, 7]


def fit_predict_poly_1d(X_tr, y_tr, X_te, deg):
    """fit_predict pentru nucleu: polinom de grad `deg` pe prima coloana (distanta std)."""
    x_tr = np.asarray(X_tr, dtype=float)[:, 0]
    x_te = np.asarray(X_te, dtype=float)[:, 0]
    Phi = _poly_design(x_tr, deg)
    w, *_ = np.linalg.lstsq(Phi, y_tr, rcond=None)
    return _poly_design(x_te, deg) @ w


def main():
    df = make_latency_dataset(n_per_cond=120, seed=0)
    # o singura axa de feature (distanta), standardizata, ca selectia de grad sa fie clara
    x = df["distance_m"].to_numpy(dtype=float).reshape(-1, 1)
    y = np.log10(df["rtt_ms"].to_numpy(dtype=float))
    Xs, _, _, _ = standardize(x)

    # selectie pe un singur CV (optimista) + curba grad -> eroare CV
    best, sel_err, scores = grid_search_cv(Xs, y, fit_predict_poly_1d, GRID_GRADE, k=5, seed=0)
    print("DATE SINTETICE (semanate din C1/M). Tinta: log10(rtt_ms) din distanta.")
    print("Grid grade polinom:", GRID_GRADE)
    print("grad  cv_rmse")
    for d in GRID_GRADE:
        marca = "  <- ales" if d == best else ""
        print("  %d   %.4f%s" % (d, scores[d], marca))
    print("Selectie (un singur CV): grad %d, RMSE selectie = %.4f (OPTIMIST)" % (best, sel_err))

    # eroare ONESTA prin nested CV
    honest, fold_sc, chosen = nested_cv(Xs, y, fit_predict_poly_1d, GRID_GRADE,
                                        k_outer=5, k_inner=4, seed=0)
    print("Nested CV: RMSE onest = %.4f  (grade alese pe falduri externe: %s)"
          % (honest, chosen))
    print("Gol selectie -> onest = %.4f  (cat de optimista era selectia)"
          % (honest - sel_err))

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(7, 4))
        ys = [scores[d] for d in GRID_GRADE]
        ax.plot(GRID_GRADE, ys, marker="o", label="RMSE CV (selectie)")
        ax.axhline(honest, ls="--", color="C3", label="RMSE onest (nested CV)")
        ax.scatter([best], [scores[best]], color="C1", zorder=5, s=80, label="grad ales")
        ax.set_xlabel("grad polinom"); ax.set_ylabel("RMSE (log10 rtt)")
        ax.set_title("Selectie de model: CV de selectie vs eroare onesta (date SINTETICE)")
        ax.legend()
        here = os.path.dirname(os.path.abspath(__file__))
        maybe_savefig(fig, os.path.join(here, "fig_selectie_model.png"))
    except Exception as e:
        print("[fig] matplotlib indisponibil (%s) -- doar numeric." % e)


if __name__ == "__main__":
    main()
