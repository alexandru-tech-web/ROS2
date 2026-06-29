#!/usr/bin/env python3
"""naive_bayes_sklearn.py -- validare incrucisata a nucleului M10 cu scikit-learn.

Verifica fata de sklearn.naive_bayes.GaussianNB:
  - estimarile de antrenare (theta_ = medii, var_ = variante, priors_) coincid sub
    toleranta (folosesc aceeasi conventie de podea var_smoothing);
  - PREDICTIILE coincid pe un set de test (acelasi argmax MAP);
  - ACURATETEA coincide sub toleranta.

Iesire 0 daca potrivirile trec sau daca sklearn lipseste (try/except ImportError).
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from naive_bayes_core import GaussianNaiveBayes  # noqa: E402
from utils import accuracy  # noqa: E402

try:
    from sklearn.naive_bayes import GaussianNB
except ImportError:
    print("[sklearn] indisponibil -- sar validarea incrucisata (nu e o eroare).")
    sys.exit(0)


def _check():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    # date de test: trei gaussiene 2D partial suprapuse, clase dezechilibrate
    rng = np.random.default_rng(7)
    Xtr = np.vstack([
        rng.normal([0.0, 0.0], 1.0, size=(150, 2)),
        rng.normal([3.0, 1.0], 1.2, size=(90, 2)),
        rng.normal([1.0, 4.0], 0.8, size=(40, 2)),
    ])
    ytr = np.r_[np.zeros(150), np.ones(90), 2 * np.ones(40)].astype(int)
    Xte = np.vstack([
        rng.normal([0.0, 0.0], 1.0, size=(60, 2)),
        rng.normal([3.0, 1.0], 1.2, size=(60, 2)),
        rng.normal([1.0, 4.0], 0.8, size=(60, 2)),
    ])
    yte = np.r_[np.zeros(60), np.ones(60), 2 * np.ones(60)].astype(int)

    # acelasi var_smoothing (1e-9) ca implicitul sklearn -> podele identice
    mine = GaussianNaiveBayes(var_smoothing=1e-9).fit(Xtr, ytr)
    sk = GaussianNB(var_smoothing=1e-9).fit(Xtr, ytr)

    ck("medii (theta_) ~ sklearn", np.allclose(mine.theta_, sk.theta_, atol=1e-9))
    ck("variante (var_) ~ sklearn", np.allclose(mine.var_, sk.var_, atol=1e-9))
    ck("prior-uri ~ sklearn", np.allclose(mine.priors_, sk.class_prior_, atol=1e-12))

    p_mine = mine.predict(Xte)
    p_sk = sk.predict(Xte)
    ck("predictii identice cu sklearn pe test", np.array_equal(p_mine, p_sk))

    a_mine = accuracy(yte, p_mine)
    a_sk = accuracy(yte, p_sk)
    ck("acuratete identica cu sklearn (|d| < 1e-12)", abs(a_mine - a_sk) < 1e-12)
    print("  acuratete nucleu = %.4f ; sklearn = %.4f" % (a_mine, a_sk))

    # log-posteriorul nucleului == joint log likelihood al sklearn (sub constanta)
    jll_mine = mine.predict_log_proba(Xte[:5])
    jll_sk = sk._joint_log_likelihood(Xte[:5])
    ck("log-posterior nenormalizat ~ sklearn _joint_log_likelihood",
       np.allclose(jll_mine, jll_sk, atol=1e-9))

    print("\nVALIDARE INCRUCISATA M10 OK: %d potriviri." % ok)
    return ok


if __name__ == "__main__":
    try:
        _check()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
