#!/usr/bin/env python3
"""demo_sil.py -- M14: ce feature de link conteaza cel mai mult pentru utilizabilitate.

Headless, fara argumente. Pe ferestrele de link (make_link_usability_dataset)
antreneaza un model liniar simplu care prezice eticheta `usable` din feature-urile
de link standardizate, apoi calculeaza importanta prin PERMUTARE a fiecarui feature
si tipareste clasamentul. In plus, un profil de dependenta partiala (PDP) pe
feature-ul de pierdere, ca sa vedem in ce sens impinge predictia.

Modelul de explicat e un model liniar minimal definit in nucleu (_linfit) -- NU
importam alt modul mXX. Predictia liniara aici e un scor continuu de utilizabilitate
(probe liniar), suficient ca tinta a explicabilitatii.

Daca matplotlib exista, emite fig_importanta_link.png; altfel tipareste numeric.
Datele sunt SINTETICE (semanate din C1/M).
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from interpretabilitate_core import (  # noqa: E402
    permutation_importance, partial_dependence, _linfit, _make_predict,
)
from date_sar import make_link_usability_dataset  # noqa: E402
from utils import standardize, maybe_savefig, r2_score  # noqa: E402

FEATURES = ["p95_ms", "loss_frac", "jitter_ms", "base_lat_ms", "mw_zenoh", "distance_m"]


def main():
    df = make_link_usability_dataset(n_per_cond=200, seed=1)
    X = df[FEATURES].to_numpy(dtype=float)
    y = df["usable"].to_numpy(dtype=float)
    Xs, _, _, _ = standardize(X)

    # model liniar minimal (probe) ca model de explicat
    w0, w = _linfit(Xs, y)
    pred = _make_predict(w0, w)
    print("R2 al probei liniare pe `usable`: %.4f" % r2_score(y, pred(Xs)))

    imp = permutation_importance(pred, Xs, y, metric=r2_score, n_repeats=30, seed=2)
    order = np.argsort(imp)[::-1]
    print("\nClasamentul importantei prin permutare (scadere medie a R2):")
    for rank, j in enumerate(order, 1):
        print("  %d. %-12s  %.4f" % (rank, FEATURES[j], imp[j]))

    # PDP pe feature-ul de pierdere (standardizat): in ce sens impinge predictia
    j_loss = FEATURES.index("loss_frac")
    grid = np.linspace(Xs[:, j_loss].min(), Xs[:, j_loss].max(), 9)
    pdp = partial_dependence(pred, Xs, feature_idx=j_loss, grid=grid)
    print("\nPDP pe loss_frac (standardizat) -- scor mediu de utilizabilitate:")
    for v, p in zip(grid, pdp):
        print("  loss_std=%+.2f  ->  %.4f" % (v, p))

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.barh([FEATURES[j] for j in order[::-1]], imp[order[::-1]])
        ax.set_xlabel("importanta prin permutare (scadere medie a R2)")
        ax.set_title("Ce feature de link conteaza pentru `usable` (date SINTETICE)")
        here = os.path.dirname(os.path.abspath(__file__))
        maybe_savefig(fig, os.path.join(here, "fig_importanta_link.png"))
    except Exception as e:
        print("[fig] matplotlib indisponibil (%s) -- doar numeric." % e)


if __name__ == "__main__":
    main()
