#!/usr/bin/env python3
"""demo_sil.py -- M03: curba bias-varianta vs complexitatea modelului (grad polinomial).

Demonstratie headless, FARA argumente. Foloseste datele SINTETICE din date_sar
(semanate din campania reala C1 / M -- NU masuratori reale). Construieste o
relatie unidimensionala intre o trasatura (distanta legaturii) si o tinta (RTT,
pe scara logaritmica pentru a o aduce intr-un domeniu polinomial rezonabil),
apoi:

  1) ruleaza descompunerea bias-varianta Monte Carlo a nucleului pentru o serie
     de grade polinomiale d = 0..D pe acest proces;
  2) raporteaza bias^2, varianta, zgomot si eroarea totala per grad;
  3) identifica PUNCTUL DE ECHILIBRU (gradul care minimizeaza eroarea totala
     estimata) -- compromisul bias-varianta;
  4) daca matplotlib exista, emite fig_biasvar_complexitate.png (prin
     utils.maybe_savefig); altfel tipareste tabelul numeric.

Ruleaza: /home/ubuntu/ros2_ws/.venv_ml/bin/python demo_sil.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from utils import rng  # noqa: E402
from date_sar import make_latency_dataset  # noqa: E402
from invatare_supervizata_core import bias_variance_decomposition  # noqa: E402


def _build_truth_from_data(seed=0):
    """Distileaza din date_sar un 'proces adevarat' 1D f(x) + zgomot.

    Luam conditia 'lat200_jit50' (degradare moderata, raspuns curbat al RTT cu
    distanta), aducem distanta in [-1, 1] (x). Tinta y combina forma logaritmica
    a RTT cu distanta (curbura din date) si o oscilatie motivata de jitter, ca
    f_true sa fie GENUIN neliniara -- altfel relatia e cvasi-liniara si compromisul
    bias-varianta nu se vede (optimul ar cadea la grad 0-1). f si sigma raman
    cunoscute, exact ce cere descompunerea bias-varianta.
    """
    df = make_latency_dataset(n_per_cond=200, seed=seed)
    sub = df[(df.condition == "lat200_jit50") & (df.middleware == "DDS")].copy()
    d = sub["distance_m"].to_numpy()
    rtt = sub["rtt_ms"].to_numpy()

    # normalizare distanta in [-1, 1]
    d_min, d_max = d.min(), d.max()
    x = 2.0 * (d - d_min) / (d_max - d_min) - 1.0
    y_obs = np.log10(np.maximum(rtt, 1e-3))

    # forma de referinta: nivelul mediu (log RTT) + curbura realista in distanta.
    # Tendinta liniara distilata din date (panta efectului de distanta) plus o
    # componenta sinusoidala (regim de jitter periodic pe legatura) -> f_true curbat.
    base = float(np.mean(y_obs))
    slope = float(np.polynomial.polynomial.polyfit(x, y_obs, deg=1)[1])  # panta liniara reala
    spread = float(np.std(y_obs))                                        # scara verticala reala
    amp = 1.2 * spread                                                   # curbura ampla, vizibila
    f_true = lambda xx: (base + slope * np.asarray(xx, dtype=float)
                         + amp * np.sin(1.7 * np.pi * np.asarray(xx, dtype=float)))

    # sigma: zgomot ireductibil pentru demonstratie, fixat la o fractie din scara
    # verticala reala a datelor (ramane realist, dar mic fata de curbura, ca sa se
    # vada compromisul bias-varianta cu optim INTERIOR -- altfel zgomotul ar domina).
    sigma = 0.10 * spread
    return f_true, sigma, x, y_obs


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    f_true, sigma, x_data, y_data = _build_truth_from_data(seed=0)

    print("=" * 70)
    print("M03 DEMO -- bias-varianta vs complexitate (date SINTETICE, sem. C1/M)")
    print("=" * 70)
    print("proces 1D distilat din date_sar: x = distanta normalizata, y = log10(RTT_ms)")
    print("conditie 'lat200_jit50' / DDS; sigma (zgomot ireductibil, demonstrativ) = %.4f" % sigma)
    print("n puncte folosite la distilarea f_true: %d" % len(x_data))
    print()

    # grila de evaluare (acoperind domeniul observat al lui x)
    x_grid = np.linspace(-0.9, 0.9, 30)
    degrees = list(range(0, 10))
    n_train = 25                 # set mic -> varianta vizibila la grad mare (N mic, ca in teza)

    rows = []
    for d in degrees:
        res = bias_variance_decomposition(
            f_true, x_grid, degree=d, sigma=sigma,
            n_train=n_train, n_datasets=500,
            x_train_low=-1.0, x_train_high=1.0, ridge=1e-8, seed=100 + d,
        )
        rows.append(res)

    bias2 = np.array([r["bias2"] for r in rows])
    var = np.array([r["variance"] for r in rows])
    noise = np.array([r["noise"] for r in rows])
    total = np.array([r["total"] for r in rows])

    best = int(degrees[int(np.argmin(total))])

    print("  grad |   bias^2   | varianta  |  zgomot   |  total (emp) | b^2+var+zg")
    print("  -----+------------+-----------+-----------+--------------+-----------")
    for i, d in enumerate(degrees):
        mark = "  <== echilibru" if d == best else ""
        print("   %3d | %10.5f | %9.5f | %9.5f | %12.5f | %9.5f%s" % (
            d, bias2[i], var[i], noise[i], total[i], bias2[i] + var[i] + noise[i], mark))
    print()
    print("PUNCT DE ECHILIBRU (eroare totala minima): grad d* = %d" % best)
    print("  - sub d*: bias domina (sub-invatare, model prea rigid);")
    print("  - peste d*: varianta domina (supra-invatare, model prea flexibil la N mic).")
    print()

    # ---- figura (daca matplotlib exista) ----
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(7.5, 5.0))
        ax.plot(degrees, bias2, "o-", label="bias^2 (eroare sistematica)")
        ax.plot(degrees, var, "s-", label="varianta")
        ax.plot(degrees, bias2 + var + noise, "^-", label="bias^2 + var + zgomot")
        ax.axhline(noise[0], color="0.5", ls=":", label="zgomot ireductibil sigma^2")
        ax.axvline(best, color="0.3", ls="--", lw=1.0)
        ax.annotate("echilibru d*=%d" % best, xy=(best, (bias2 + var + noise)[best]),
                    xytext=(best + 0.4, (bias2 + var + noise).max() * 0.8),
                    arrowprops=dict(arrowstyle="->", color="0.3"))
        ax.set_xlabel("complexitate model (grad polinomial d)")
        ax.set_ylabel("eroare patratica asteptata")
        ax.set_title("M03: compromisul bias-varianta vs complexitate\n"
                     "(date sintetice, semanate din C1/M)")
        ax.set_yscale("log")
        ax.legend(loc="upper center", fontsize=8)
        ax.grid(True, alpha=0.3)
        from utils import maybe_savefig
        maybe_savefig(fig, os.path.join(here, "fig_biasvar_complexitate.png"))
        plt.close(fig)
    except Exception as e:  # pragma: no cover - depinde de mediu
        print("[fig] matplotlib indisponibil sau eroare (%s); raportare doar numerica." % e)

    # un al doilea fisier: o ilustrare a pierderilor surogat vs 0-1 (pedagogic, numeric/fig)
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from invatare_supervizata_core import hinge_loss, logistic_loss, zero_one_loss

        m = np.linspace(-3, 3, 400)             # margine y*score pentru y=+1
        # pentru o margine m si y=+1: score=m
        h = hinge_loss(np.ones_like(m), m)
        # logistica in functie de margine: y in {0,1}; pentru clasa pozitiva si logit=m
        lg = logistic_loss(np.ones_like(m), m) / np.log(2.0)   # normata: =1 la margine 0
        z01 = zero_one_loss(np.ones_like(m), (m > 0).astype(float))

        fig2, ax2 = plt.subplots(figsize=(7.5, 4.5))
        ax2.plot(m, z01, label="0-1 (ce vrem)")
        ax2.plot(m, h, label="hinge (SVM)")
        ax2.plot(m, lg, label="logistica (normata)")
        ax2.set_xlabel("margine  y * score")
        ax2.set_ylabel("pierdere")
        ax2.set_title("M03: surogate convexe peste pierderea 0-1")
        ax2.legend(fontsize=8)
        ax2.grid(True, alpha=0.3)
        from utils import maybe_savefig
        maybe_savefig(fig2, os.path.join(here, "fig_pierderi_surogat.png"))
        plt.close(fig2)
    except Exception as e:  # pragma: no cover
        print("[fig] surogate sarite (%s)." % e)

    print("Gata. (datele sunt SINTETICE -- semanate din campaniile reale C1/M, nu masuratori.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
