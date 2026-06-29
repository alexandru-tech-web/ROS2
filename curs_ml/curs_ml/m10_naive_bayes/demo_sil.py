#!/usr/bin/env python3
"""demo_sil.py -- M10: Gaussian Naive Bayes ca linie de baza pe datele mele.

Headless, fara argumente. Clasifica eticheta `usable` (link utilizabil pentru
teleoperatie) din make_link_usability_dataset cu Gaussian NB de la zero si
raporteaza acuratetea fata de o BAZA TRIVIALA (mereu clasa majoritara).

NB e o linie de baza GENERATIVA ieftina: nici un pas de optimizare, doar medii si
variante per clasa. Util tocmai cand vrei un reper rapid si reproductibil.

Daca matplotlib exista, emite fig_nb_frontiera.png (frontiera de decizie pe doua
feature-uri); altfel tipareste numeric. Datele sunt SINTETICE (semanate din C1/M).
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from naive_bayes_core import GaussianNaiveBayes  # noqa: E402
from date_sar import make_link_usability_dataset  # noqa: E402
from utils import train_test_split, standardize, accuracy, precision_recall_f1, maybe_savefig  # noqa: E402

FEATURES = ["p95_ms", "loss_frac", "jitter_ms", "distance_m", "mw_zenoh"]


def main():
    df = make_link_usability_dataset(n_per_cond=120, seed=1)
    X = df[FEATURES].to_numpy(dtype=float)
    y = df["usable"].to_numpy(dtype=int)

    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_frac=0.25, seed=0)
    X_tr_s, X_te_s, _, _ = standardize(X_tr, X_te)

    clf = GaussianNaiveBayes().fit(X_tr_s, y_tr)
    pred = clf.predict(X_te_s)
    acc_nb = accuracy(y_te, pred)
    prec, rec, f1 = precision_recall_f1(y_te, pred)

    # baza triviala: mereu clasa majoritara de pe TRAIN
    maj = int(np.bincount(y_tr).argmax())
    acc_maj = accuracy(y_te, np.full_like(y_te, maj))

    frac_usable = float(y.mean())
    print("date SINTETICE (C1/M) -- clasificare 'usable' (link utilizabil)")
    print("fractie usable global: %.3f (clase dezechilibrate)" % frac_usable)
    print("clasa majoritara pe train: %d" % maj)
    print("-" * 52)
    print("Gaussian NB (de la zero):")
    print("  acuratete = %.4f  precizie = %.4f  recall = %.4f  F1 = %.4f"
          % (acc_nb, prec, rec, f1))
    print("Baza triviala (mereu clasa majoritara):")
    print("  acuratete = %.4f" % acc_maj)
    print("-" * 52)
    delta = acc_nb - acc_maj
    if delta > 0:
        print("NB bate baza triviala cu %.4f la acuratete." % delta)
    else:
        print("NB NU bate baza triviala (%.4f) -- la dezechilibru mare," % delta)
        print("acuratetea singura inseala; vezi precizie/recall/F1 (M09).")

    # vizualizare: frontiera de decizie pe primele doua feature-uri standardizate
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        clf2 = GaussianNaiveBayes().fit(X_tr_s[:, :2], y_tr)
        x0 = np.linspace(X_tr_s[:, 0].min() - 0.5, X_tr_s[:, 0].max() + 0.5, 200)
        x1 = np.linspace(X_tr_s[:, 1].min() - 0.5, X_tr_s[:, 1].max() + 0.5, 200)
        g0, g1 = np.meshgrid(x0, x1)
        grid = np.column_stack([g0.ravel(), g1.ravel()])
        zz = clf2.predict(grid).reshape(g0.shape)

        fig, ax = plt.subplots(figsize=(7, 5))
        ax.contourf(g0, g1, zz, levels=[-0.5, 0.5, 1.5], alpha=0.2,
                    colors=["#d62728", "#2ca02c"])
        for cls, mark, col, lab in [(0, "x", "#d62728", "inutilizabil"),
                                    (1, "o", "#2ca02c", "usable")]:
            m = y_tr == cls
            ax.scatter(X_tr_s[m, 0], X_tr_s[m, 1], marker=mark, c=col, s=14,
                       alpha=0.6, label=lab)
        ax.set_xlabel("p95_ms (standardizat)")
        ax.set_ylabel("loss_frac (standardizat)")
        ax.set_title("Gaussian NB: frontiera de decizie (date SINTETICE)")
        ax.legend()
        here = os.path.dirname(os.path.abspath(__file__))
        maybe_savefig(fig, os.path.join(here, "fig_nb_frontiera.png"))
    except Exception as e:
        print("[fig] matplotlib indisponibil (%s) -- doar numeric." % e)


if __name__ == "__main__":
    main()
