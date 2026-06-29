#!/usr/bin/env python3
"""demo_sil.py -- M08: regresie logistica pe utilizabilitatea legaturii (clase dezechilibrate).

Headless, fara argumente. Pe make_link_usability_dataset (clasa 'usable' minoritara,
~30%), standardizeaza feature-urile, antreneaza nucleul (coborare pe gradient) si
raporteaza acuratete / precizie / recall / F1 si matricea de confuzie. La date
dezechilibrate acuratetea minte (vezi M09) -- de aceea raportam si precizie/recall.

Daca matplotlib exista, emite fig_granita_decizie.png (granita de decizie pe doua
feature-uri); altfel doar numeric. Datele sunt SINTETICE (semanate din C1/M).
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from regresie_logistica_core import LogisticRegressionGD  # noqa: E402
from date_sar import make_link_usability_dataset  # noqa: E402
from utils import (  # noqa: E402
    standardize, train_test_split, accuracy, confusion_matrix, precision_recall_f1,
    maybe_savefig,
)

FEATURES = ["p95_ms", "loss_frac", "jitter_ms", "distance_m", "mw_zenoh"]


def main():
    df = make_link_usability_dataset(n_per_cond=120, seed=1)
    X = df[FEATURES].to_numpy(dtype=float)
    y = df["usable"].to_numpy(dtype=int)
    print("clase: %d usable / %d total (%.1f%% pozitive -- DEZECHILIBRAT)"
          % (int(y.sum()), len(y), 100.0 * y.mean()))

    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_frac=0.30, seed=0)
    Xtr_s, Xte_s, _, _ = standardize(X_tr, X_te)

    model = LogisticRegressionGD(lr=0.3, n_iter=4000, seed=0).fit(Xtr_s, y_tr)
    y_pred = model.predict(Xte_s)

    acc = accuracy(y_te, y_pred)
    prec, rec, f1 = precision_recall_f1(y_te, y_pred)
    cm = confusion_matrix(y_te, y_pred)
    print("acuratete : %.3f" % acc)
    print("precizie  : %.3f   recall: %.3f   F1: %.3f" % (prec, rec, f1))
    print("confuzie [[TN, FP], [FN, TP]] = %s" % cm.tolist())
    print("(acuratetea inseala la clase dezechilibrate -- vezi M09)")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        # granita de decizie pe doua feature-uri (p95_ms, loss_frac), restul la medie
        i0, i1 = FEATURES.index("p95_ms"), FEATURES.index("loss_frac")
        Xtr2 = X_tr[:, [i0, i1]]
        Xtr2_s, _, mean2, std2 = standardize(Xtr2)
        m2 = LogisticRegressionGD(lr=0.3, n_iter=4000, seed=0).fit(Xtr2_s, y_tr)

        x_min, x_max = Xtr2_s[:, 0].min() - 1, Xtr2_s[:, 0].max() + 1
        y_min, y_max = Xtr2_s[:, 1].min() - 1, Xtr2_s[:, 1].max() + 1
        gx, gy = np.meshgrid(np.linspace(x_min, x_max, 200),
                             np.linspace(y_min, y_max, 200))
        grid = np.column_stack([gx.ravel(), gy.ravel()])
        zz = m2.predict_proba(grid).reshape(gx.shape)

        fig, ax = plt.subplots(figsize=(7, 5))
        cs = ax.contourf(gx, gy, zz, levels=20, cmap="RdBu", alpha=0.7)
        ax.contour(gx, gy, zz, levels=[0.5], colors="k", linewidths=1.5)
        ax.scatter(Xtr2_s[y_tr == 0, 0], Xtr2_s[y_tr == 0, 1], s=12,
                   c="darkred", label="inutilizabil (0)", edgecolors="none")
        ax.scatter(Xtr2_s[y_tr == 1, 0], Xtr2_s[y_tr == 1, 1], s=12,
                   c="navy", label="usable (1)", edgecolors="none")
        ax.set_xlabel("p95_ms (standardizat)")
        ax.set_ylabel("loss_frac (standardizat)")
        ax.set_title("Granita de decizie -- regresie logistica (date SINTETICE)")
        ax.legend(loc="upper right")
        fig.colorbar(cs, ax=ax, label="P(usable)")
        here = os.path.dirname(os.path.abspath(__file__))
        maybe_savefig(fig, os.path.join(here, "fig_granita_decizie.png"))
    except Exception as e:
        print("[fig] matplotlib indisponibil (%s) -- doar numeric." % e)


if __name__ == "__main__":
    main()
