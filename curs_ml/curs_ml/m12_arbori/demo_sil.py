#!/usr/bin/env python3
"""demo_sil.py -- M12: arbore de decizie pentru mission_complete pe datele mele.

Headless, fara argumente. Antreneaza un arbore CART mic (max_depth=3) sa prezica
mission_complete din (delivered_frac, p95_ms, n_drones), raporteaza acuratetea pe
un set de test tinut deoparte, tipareste REGULILE interpretabile (forta arborilor:
explicabili) si importanta feature-urilor.

Daca matplotlib exista, emite fig_arbore_importanta.png (bare cu importanta
feature-urilor); altfel doar numeric. Datele sunt SINTETICE (semanate din C1/M).
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from arbori_decizie_core import DecisionTreeCart  # noqa: E402
from date_sar import make_mission_outcome_dataset  # noqa: E402
from utils import train_test_split, accuracy, maybe_savefig  # noqa: E402

FEATURES = ["delivered_frac", "p95_ms", "n_drones"]


def main():
    df = make_mission_outcome_dataset(n=500, seed=3)
    X = df[FEATURES].to_numpy(dtype=float)
    y = df["mission_complete"].to_numpy(dtype=int)
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_frac=0.25, seed=0)

    tree = DecisionTreeCart(max_depth=3, min_samples_split=10, criterion="gini")
    tree.fit(Xtr, ytr)

    acc_tr = accuracy(ytr, tree.predict(Xtr))
    acc_te = accuracy(yte, tree.predict(Xte))
    print("Arbore CART (max_depth=3) pentru mission_complete -- date SINTETICE")
    print("  acuratete train = %.3f   test = %.3f   (adancime efectiva %d)"
          % (acc_tr, acc_te, tree.depth()))

    print("\nImportanta feature-urilor (reducere de impuritate, suma 1):")
    for name, imp in zip(FEATURES, tree.feature_importances_):
        print("  %-16s %.3f" % (name, imp))

    print("\nReguli interpretabile (cate o frunza):")
    for line in tree.rules(feature_names=FEATURES):
        print("  " + line)

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(6, 4))
        idx = np.arange(len(FEATURES))
        ax.bar(idx, tree.feature_importances_, color="steelblue")
        ax.set_xticks(idx)
        ax.set_xticklabels(FEATURES, rotation=20, ha="right")
        ax.set_ylabel("importanta (reducere de impuritate)")
        ax.set_title("Arbore mission_complete (date SINTETICE)")
        here = os.path.dirname(os.path.abspath(__file__))
        maybe_savefig(fig, os.path.join(here, "fig_arbore_importanta.png"))
    except Exception as e:
        print("[fig] matplotlib indisponibil (%s) -- doar numeric." % e)


if __name__ == "__main__":
    main()
