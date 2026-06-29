#!/usr/bin/env python3
"""invatare_supervizata_sklearn.py -- validare incrucisata a nucleului M03.

Ruleaza ACELASI calcul cu scikit-learn / referinta analitica si ASERTEAZA ca
nucleul pur (invatare_supervizata_core) coincide sub o toleranta. Verifica:

  (a) Functiile de pierdere ale nucleului fata de echivalentele bibliotecii:
        - patratica   vs sklearn.metrics.mean_squared_error (per esantion / medie);
        - 0-1         vs 1 - accuracy_score;
        - hinge       vs sklearn.metrics.hinge_loss (forma cu y in {-1,+1});
        - logistica   vs sklearn.metrics.log_loss (entropie incrucisata).
  (b) Modelul polinomial al nucleului (ecuatie normala) fata de
        sklearn Pipeline(PolynomialFeatures + LinearRegression).
  (c) Descompunerea bias-varianta Monte Carlo: gradul mare are varianta mai mare
        decat gradul mic si la nucleu, si la sklearn (acelasi protocol).

Ruleaza: /home/ubuntu/ros2_ws/.venv_ml/bin/python invatare_supervizata_sklearn.py
Iesire 0 = nucleul si scikit-learn coincid; non-0 = divergenta.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from invatare_supervizata_core import (  # noqa: E402
    squared_loss, zero_one_loss, hinge_loss, logistic_loss, sigmoid,
    empirical_risk, fit_poly, predict_poly, bias_variance_decomposition,
)

from sklearn.metrics import (  # noqa: E402
    mean_squared_error, accuracy_score, hinge_loss as sk_hinge_loss, log_loss,
)
from sklearn.linear_model import LinearRegression  # noqa: E402
from sklearn.preprocessing import PolynomialFeatures  # noqa: E402
from sklearn.pipeline import Pipeline  # noqa: E402


def main():
    ok = 0

    def ck(name, cond, a=None, b=None):
        nonlocal ok
        extra = "" if a is None else "  (nucleu=%.6g  sklearn=%.6g)" % (a, b)
        assert cond, "FAIL: " + name + extra
        ok += 1
        print("  [ok] " + name + extra)

    rng = np.random.default_rng(7)

    # -------------------------------------------------- (a1) pierdere patratica
    y = rng.normal(size=50)
    p = y + rng.normal(0, 0.4, size=50)
    core_mse = empirical_risk(squared_loss, y, p)
    sk_mse = mean_squared_error(y, p)
    ck("patratica: R_emp nucleu == mean_squared_error", abs(core_mse - sk_mse) < 1e-12,
       core_mse, sk_mse)

    # -------------------------------------------------- (a2) pierdere 0-1
    yc = rng.integers(0, 2, size=60)
    pc = yc.copy()
    flip = rng.choice(60, size=14, replace=False)
    pc[flip] = 1 - pc[flip]
    core_01 = empirical_risk(zero_one_loss, yc, pc)
    sk_01 = 1.0 - accuracy_score(yc, pc)
    ck("0-1: R_emp nucleu == 1 - accuracy_score", abs(core_01 - sk_01) < 1e-12,
       core_01, sk_01)

    # -------------------------------------------------- (a3) pierdere hinge
    ypm = rng.choice([-1.0, 1.0], size=40)         # etichete in {-1,+1}
    score = rng.normal(0, 1.2, size=40)
    core_hinge = empirical_risk(hinge_loss, ypm, score)
    sk_h = sk_hinge_loss(ypm, score)               # sklearn: media max(0,1-y*score)
    ck("hinge: R_emp nucleu == sklearn.hinge_loss", abs(core_hinge - sk_h) < 1e-10,
       core_hinge, sk_h)

    # -------------------------------------------------- (a4) pierdere logistica
    y01 = rng.integers(0, 2, size=80).astype(float)
    logit = rng.normal(0, 1.5, size=80)
    core_log = empirical_risk(logistic_loss, y01, logit)
    proba = sigmoid(logit)
    # log_loss asteapta probabilitati; cu eps=0 si labels explicite e exact entropia
    sk_log = log_loss(y01, proba, labels=[0, 1])
    ck("logistica: R_emp nucleu == sklearn.log_loss", abs(core_log - sk_log) < 1e-9,
       core_log, sk_log)

    # -------------------------------------------------- (b) model polinomial
    xtr = rng.uniform(-1.0, 1.0, size=40)
    ytr = 0.5 - 1.2 * xtr + 2.0 * xtr ** 2 - 0.7 * xtr ** 3 + rng.normal(0, 0.05, size=40)
    degree = 3
    w = fit_poly(xtr, ytr, degree=degree, ridge=0.0)
    xte = np.linspace(-0.95, 0.95, 17)
    core_pred = predict_poly(w, xte)

    pipe = Pipeline([
        ("poly", PolynomialFeatures(degree=degree, include_bias=True)),
        ("lin", LinearRegression(fit_intercept=False)),
    ])
    pipe.fit(xtr.reshape(-1, 1), ytr)
    sk_pred = pipe.predict(xte.reshape(-1, 1))
    max_dev = float(np.max(np.abs(core_pred - sk_pred)))
    ck("poly: predictia nucleului == Pipeline(PolynomialFeatures+LinearRegression)",
       max_dev < 1e-6, max_dev, 0.0)

    # -------------------------------------------------- (c) bias-varianta: ordine grade
    def f_true(x):
        return np.sin(1.5 * np.pi * x)

    x_grid = np.linspace(-0.9, 0.9, 25)
    sigma = 0.25
    core_low = bias_variance_decomposition(f_true, x_grid, degree=1, sigma=sigma,
                                           n_train=20, n_datasets=400, seed=3)
    core_high = bias_variance_decomposition(f_true, x_grid, degree=11, sigma=sigma,
                                            n_train=20, n_datasets=400, seed=3)

    # acelasi protocol Monte Carlo, dar cu sklearn ca estimator polinomial
    def sk_variance(degree, n_datasets=400, n_train=20, seed=3):
        g = np.random.default_rng(seed)
        preds = np.empty((n_datasets, x_grid.shape[0]))
        for s in range(n_datasets):
            xt = g.uniform(-1.0, 1.0, size=n_train)
            yt = f_true(xt) + g.normal(0, sigma, size=n_train)
            pl = Pipeline([
                ("poly", PolynomialFeatures(degree=degree, include_bias=True)),
                ("lin", LinearRegression(fit_intercept=False)),
            ])
            pl.fit(xt.reshape(-1, 1), yt)
            preds[s] = pl.predict(x_grid.reshape(-1, 1))
        return float(np.mean(np.var(preds, axis=0)))

    sk_var_low = sk_variance(1)
    sk_var_high = sk_variance(11)

    ck("biasvar: nucleu confirma var(grad 11) > var(grad 1)",
       core_high["variance"] > core_low["variance"], core_high["variance"], core_low["variance"])
    ck("biasvar: sklearn confirma var(grad 11) > var(grad 1)",
       sk_var_high > sk_var_low, sk_var_high, sk_var_low)
    # variantele nucleu vs sklearn la grad mic sunt apropiate (protocol identic, seed identic)
    ck("biasvar: var(grad 1) nucleu ~ sklearn (rel < 5pct)",
       abs(core_low["variance"] - sk_var_low) / max(sk_var_low, 1e-12) < 0.05,
       core_low["variance"], sk_var_low)

    print("\nVALIDARE INCRUCISATA OK: %d comparatii nucleu-vs-sklearn coincid." % ok)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AssertionError as e:
        print(e)
        sys.exit(1)
