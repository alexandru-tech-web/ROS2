#!/usr/bin/env python3
"""demo_sil.py -- M16: comprima feature-uri de latenta in 2D si vizualizeaza
separarea conditiilor de retea.

Headless, fara argumente. Pe feature-urile numerice pe conditii din
make_latency_dataset (loss, latenta de baza, jitter, distanta, plus rtt-ul
logaritmat), standardizeaza, ruleaza PCA si proiecteaza pe primele 2 componente.
Raporteaza varianta explicata de fiecare componenta si cumulat. Cele 6 conditii
de retea (ideal, loss_*, lat200_*) ar trebui sa se separe vizibil in planul PCA --
asa comprimi un spatiu de feature-uri si verifici daca regimurile sunt separabile.

Daca matplotlib exista, emite fig_pca_conditii.png (scatter 2D colorat pe conditie
+ varianta explicata cumulata); altfel tipareste numeric.
Datele sunt SINTETICE (semanate din C1/M).
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from pca_core import PCA  # noqa: E402
from date_sar import make_latency_dataset  # noqa: E402
from utils import standardize, maybe_savefig  # noqa: E402

FEATURES = ["loss_pct", "base_lat_ms", "jitter_ms", "distance_m"]


def main():
    df = make_latency_dataset(n_per_cond=150, seed=0)
    # feature-uri numerice pe conditii + rtt logaritmat (intinde scara intre conditii)
    X = np.column_stack([
        df[FEATURES].to_numpy(dtype=float),
        np.log10(df["rtt_ms"].to_numpy(dtype=float)),
    ])
    Xs, _, _, _ = standardize(X)                # scara feature-urilor conteaza la PCA

    p = PCA().fit(Xs)
    T = p.transform(Xs, k=2)
    evr = p.explained_variance_ratio_
    print("PCA pe feature-uri de latenta (date SINTETICE):")
    print("  varianta explicata per componenta:")
    for i, v in enumerate(evr):
        print("    PC%d: %.4f" % (i + 1, v))
    print("  varianta explicata de primele 2 componente (cumulat): %.4f"
          % float(evr[:2].sum()))

    # separare numerica: cat de departe sunt centroizii conditiilor in planul PCA
    conds = df["condition"].to_numpy()
    print("  centroizi PC1/PC2 per conditie:")
    for c in sorted(set(conds)):
        m = conds == c
        print("    %-13s  PC1=%+.3f  PC2=%+.3f" % (c, T[m, 0].mean(), T[m, 1].mean()))

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))
        # scatter 2D colorat pe conditie
        uniq = sorted(set(conds))
        cmap = plt.get_cmap("tab10")
        for i, c in enumerate(uniq):
            m = conds == c
            ax1.scatter(T[m, 0], T[m, 1], s=12, color=cmap(i % 10), label=c, alpha=0.7)
        ax1.set_xlabel("PC1"); ax1.set_ylabel("PC2")
        ax1.set_title("Conditii in planul PCA (date SINTETICE)")
        ax1.legend(fontsize=7, markerscale=1.4)
        # varianta explicata cumulata
        cum = np.cumsum(evr)
        ax2.plot(np.arange(1, len(cum) + 1), cum, marker="o")
        ax2.axhline(1.0, color="gray", linestyle=":")
        ax2.set_xlabel("numar de componente"); ax2.set_ylabel("varianta explicata cumulata")
        ax2.set_title("Cat retii cu k componente"); ax2.set_ylim(0, 1.05)
        here = os.path.dirname(os.path.abspath(__file__))
        maybe_savefig(fig, os.path.join(here, "fig_pca_conditii.png"))
    except Exception as e:
        print("[fig] matplotlib indisponibil (%s) -- doar numeric." % e)


if __name__ == "__main__":
    main()
