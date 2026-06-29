#!/usr/bin/env python3
"""demo_sil.py -- M11: k-NN vs SVM liniar pe o granita NELINIARA.

Headless, fara argumente. Construieste un set 2D sintetic cu granita neliniara
(doua inele concentrice: clasa interioara vs clasa exterioara) si compara:
  - k-NN (k=5), care urmareste local granita curba;
  - SVM liniar (Pegasos), care poate trasa DOAR o dreapta -> esueaza pe inele.

Concluzia didactica: pe granite neliniare, k-NN bate SVM-ul liniar; ca SVM-ul sa
prinda granita ar trebui un kernel (RBF) -- vezi rbf_kernel din nucleu.

Daca matplotlib exista, emite fig_granite.png cu cele doua granite de decizie;
altfel tipareste acuratetile numeric. Datele sunt SINTETICE (semanate aici).
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from knn_svm_core import KNN, pegasos_svm, svm_predict  # noqa: E402
from utils import standardize, accuracy, maybe_savefig  # noqa: E402


def make_rings(n=300, seed=0):
    """Doua inele concentrice in 2D: clasa 0 = disc interior, clasa 1 = inel exterior.

    Granita (un cerc) e fundamental neliniara -- nicio dreapta nu o separa bine."""
    g = np.random.default_rng(seed)
    n_in = n // 2
    n_out = n - n_in
    # disc interior
    r_in = g.uniform(0.0, 1.0, size=n_in)
    th_in = g.uniform(0.0, 2 * np.pi, size=n_in)
    inner = np.column_stack([r_in * np.cos(th_in), r_in * np.sin(th_in)])
    # inel exterior
    r_out = g.uniform(2.0, 3.0, size=n_out)
    th_out = g.uniform(0.0, 2 * np.pi, size=n_out)
    outer = np.column_stack([r_out * np.cos(th_out), r_out * np.sin(th_out)])
    X = np.vstack([inner, outer])
    y01 = np.concatenate([np.zeros(n_in, dtype=int), np.ones(n_out, dtype=int)])
    return X, y01


def main():
    X, y01 = make_rings(n=300, seed=0)
    Xs, _, _, _ = standardize(X)
    y_pm = np.where(y01 == 1, 1, -1)            # {-1,+1} pentru SVM

    # k-NN
    knn = KNN(k=5).fit(Xs, y01)
    acc_knn = accuracy(y01, knn.predict(Xs))

    # SVM liniar (Pegasos) -- pe granita circulara nu poate decat o dreapta
    w = pegasos_svm(Xs, y_pm, lam=0.01, n_epoci=60, seed=0)
    acc_svm = accuracy(y_pm, svm_predict(Xs, w))

    print("Granita NELINIARA (inele concentrice), date SINTETICE.")
    print("  k-NN (k=5)     acuratete = %.3f" % acc_knn)
    print("  SVM liniar     acuratete = %.3f" % acc_svm)
    print("  -> k-NN urmareste granita curba; SVM-ul liniar nu o poate trasa.")
    print("     Pentru SVM ar trebui kernel RBF (vezi knn_svm_core.rbf_kernel).")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        # grila pentru granitele de decizie
        x_min, x_max = Xs[:, 0].min() - 0.5, Xs[:, 0].max() + 0.5
        y_min, y_max = Xs[:, 1].min() - 0.5, Xs[:, 1].max() + 0.5
        gx, gy = np.meshgrid(np.linspace(x_min, x_max, 200),
                             np.linspace(y_min, y_max, 200))
        grid = np.column_stack([gx.ravel(), gy.ravel()])

        z_knn = knn.predict(grid).reshape(gx.shape)
        z_svm = (svm_predict(grid, w) == 1).astype(int).reshape(gx.shape)

        fig, axes = plt.subplots(1, 2, figsize=(11, 5))
        for ax, z, titlu, acc in (
                (axes[0], z_knn, "k-NN (k=5)", acc_knn),
                (axes[1], z_svm, "SVM liniar (Pegasos)", acc_svm)):
            ax.contourf(gx, gy, z, alpha=0.25, levels=[-0.5, 0.5, 1.5], cmap="coolwarm")
            ax.scatter(Xs[y01 == 0, 0], Xs[y01 == 0, 1], s=12, c="navy", label="clasa 0 (interior)")
            ax.scatter(Xs[y01 == 1, 0], Xs[y01 == 1, 1], s=12, c="darkred", label="clasa 1 (exterior)")
            ax.set_title("%s  acc=%.2f" % (titlu, acc))
            ax.set_xlabel("x1 (std)"); ax.set_ylabel("x2 (std)")
        axes[0].legend(loc="upper right", fontsize=8)
        fig.suptitle("Granita neliniara: k-NN vs SVM liniar (date SINTETICE)")
        here = os.path.dirname(os.path.abspath(__file__))
        maybe_savefig(fig, os.path.join(here, "fig_granite.png"))
    except Exception as e:
        print("[fig] matplotlib indisponibil (%s) -- doar numeric." % e)


if __name__ == "__main__":
    main()
