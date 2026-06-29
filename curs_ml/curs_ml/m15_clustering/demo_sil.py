#!/usr/bin/env python3
"""demo_sil.py -- M15: descopera regimuri de canal prin clustering, fara etichete.

Headless, fara argumente. Pe feature-uri de canal (profilul urban_rubble din
campania M -- distanta, path loss, marja, fractie livrata), ruleaza k-means pentru
mai multe valori k si raporteaza silhouette vs k. Varful curbei silhouette sugereaza
cate regimuri distincte de canal exista (de exemplu: aproape -> livrare buna,
departe -> link slab). Asa gasesti regimuri din date NEETICHETATE.

Daca matplotlib exista, emite fig_silhouette_k.png (scatter colorat pe cluster-e
la k-ul ales + curba silhouette vs k); altfel tipareste numeric.
Datele sunt SINTETICE (semanate din C1/M).
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from clustering_core import kmeans, silhouette_score  # noqa: E402
from date_sar import make_channel_dataset  # noqa: E402
from utils import standardize, maybe_savefig  # noqa: E402

FEATURES = ["distance_m", "path_loss_db", "margin_db", "delivered_frac"]


def main():
    df = make_channel_dataset("urban_rubble", seed=2, n=400)
    X = df[FEATURES].to_numpy(dtype=float)
    Xs, _, _, _ = standardize(X)                      # scara conteaza pentru distante

    ks = [2, 3, 4, 5, 6]
    print("alegerea lui k pe regimuri de canal (date SINTETICE):")
    print("  k   silhouette   inertie")
    sils = []
    results = {}
    for k in ks:
        res = kmeans(Xs, k=k, n_init=10, seed=0)
        s = silhouette_score(Xs, res["labels"])
        sils.append(s)
        results[k] = res
        print("  %d    %.4f      %.2f" % (k, s, res["inertia"]))

    k_best = ks[int(np.argmax(sils))]
    print("k ales (silhouette maxim): %d" % k_best)

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))
        # scatter pe doua feature-uri interpretabile, colorat pe cluster
        lab = results[k_best]["labels"]
        ax1.scatter(df["distance_m"], df["delivered_frac"], c=lab, cmap="viridis", s=14)
        ax1.set_xlabel("distanta [m]"); ax1.set_ylabel("fractie livrata")
        ax1.set_title("Regimuri de canal, k=%d (date SINTETICE)" % k_best)
        # curba silhouette vs k
        ax2.plot(ks, sils, marker="o")
        ax2.axvline(k_best, color="r", linestyle="--", label="k ales = %d" % k_best)
        ax2.set_xlabel("k (numar de cluster-e)"); ax2.set_ylabel("silhouette mediu")
        ax2.set_title("Alegerea lui k"); ax2.legend()
        here = os.path.dirname(os.path.abspath(__file__))
        maybe_savefig(fig, os.path.join(here, "fig_silhouette_k.png"))
    except Exception as e:
        print("[fig] matplotlib indisponibil (%s) -- doar numeric." % e)


if __name__ == "__main__":
    main()
