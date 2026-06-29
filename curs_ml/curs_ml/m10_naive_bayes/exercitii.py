#!/usr/bin/env python3
"""exercitii.py -- M10 Naive Bayes (STUB-URI cu TODO).

Completeaza fiecare functie marcata cu TODO. Rulat ACUM trebuie sa PICE (exit != 0).
Solutiile complete in solutii.py. Refoloseste nucleul naive_bayes_core.

Ruleaza: /home/ubuntu/ros2_ws/.venv_ml/bin/python exercitii.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from naive_bayes_core import GaussianNaiveBayes  # noqa: E402
from date_sar import make_link_usability_dataset  # noqa: E402
from utils import train_test_split, standardize, accuracy  # noqa: E402

FEATURES = ["p95_ms", "loss_frac", "jitter_ms", "distance_m", "mw_zenoh"]


# ---------------------------------------------------------------- Ex.1
def ex1_log_gaussian(x, mu, var):
    """E1. Log-densitatea gaussiana 1D:
        log N(x; mu, var) = -0.5*log(2*pi*var) - (x-mu)^2 / (2*var).
    Returneaza un float. (Vezi exemplul numeric din teorie.md.)
    """
    # TODO
    raise NotImplementedError("E1: log-densitate gaussiana 1D")


# ---------------------------------------------------------------- Ex.2
def ex2_estimari(X, y):
    """E2. Estimari MLE pentru o singura clasa c=1 pe feature unic: intoarce
    (prior, mu, var) ca tuple de float, unde prior = n_1 / n, mu = media
    feature-ului pe clasa 1, var = varianta (MLE, ddof=0) pe clasa 1.
    X are forma (n, 1); y in {0, 1}.
    """
    # TODO
    raise NotImplementedError("E2: estimari MLE per clasa")


# ---------------------------------------------------------------- Ex.3
def ex3_log_posterior(x):
    """E3. Pe cazul mic din teorie.md (clasa 0: x=[1,2,3]; clasa 1: x=[5,6,7],
    prior 0.5/0.5), antreneaza GaussianNaiveBayes(var_smoothing=0.0) si intoarce
    log-posteriorul nenormalizat [lp0, lp1] pentru scalarul x.
    Returneaza un array numpy de lungime 2.
    """
    # TODO: construieste Xs, ys; fit; predict_log_proba pe [[x]]
    raise NotImplementedError("E3: log-posterior pe cazul mic")


# ---------------------------------------------------------------- Ex.4
def ex4_prior_dominant():
    """E4. Construieste un caz in care feature-urile NU disting clasele (ambele
    trase din N(0,1)) dar clasa 0 e majoritara (90 vs 10). Antreneaza NB si
    intoarce predictia pentru x=0.0 (un singur feature). Returneaza un int.
    Asteptare: prezice clasa cu prior dominant (0).
    """
    # TODO
    raise NotImplementedError("E4: prior dominant")


# ---------------------------------------------------------------- Ex.5
def ex5_nb_vs_baza():
    """E5. Pe make_link_usability_dataset(n_per_cond=120, seed=1), feature-urile
    FEATURES standardizate (split test_frac=0.25, seed=0), antreneaza Gaussian NB
    si calculeaza (acc_nb, acc_majoritate) pe TEST, unde acc_majoritate e baza
    triviala 'mereu clasa majoritara de pe train'. Returneaza (acc_nb, acc_maj).
    Asteptare: acc_nb > acc_maj.
    """
    # TODO
    raise NotImplementedError("E5: NB vs baza triviala pe datele mele")


# ---------------------------------------------------------------- verificare
def _check():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    # E1: log N(0; 0, 1) = -0.5*log(2*pi)
    val = ex1_log_gaussian(0.0, 0.0, 1.0)
    ck("E1: log N(0;0,1) = -0.5*log(2*pi)", abs(val + 0.5 * np.log(2 * np.pi)) < 1e-12)

    # E2: clasa 1 = [5,6,7] -> prior=0.5, mu=6, var=2/3
    X = np.array([[1.0], [2.0], [3.0], [5.0], [6.0], [7.0]])
    y = np.array([0, 0, 0, 1, 1, 1])
    pr, mu, var = ex2_estimari(X, y)
    ck("E2: prior clasa 1 = 0.5", abs(pr - 0.5) < 1e-12)
    ck("E2: mu clasa 1 = 6", abs(mu - 6.0) < 1e-12)
    ck("E2: var clasa 1 = 2/3", abs(var - 2.0 / 3.0) < 1e-12)

    # E3: log-posterior pe x=3 == formula manuala
    v = 2.0 / 3.0
    lp0 = np.log(0.5) - 0.5 * np.log(2 * np.pi * v) - (3 - 2.0) ** 2 / (2 * v)
    lp1 = np.log(0.5) - 0.5 * np.log(2 * np.pi * v) - (3 - 6.0) ** 2 / (2 * v)
    got = ex3_log_posterior(3.0)
    ck("E3: log-posterior x=3 == manual", np.allclose(got, [lp0, lp1]))

    # E4: prior dominant -> clasa 0
    ck("E4: prezice clasa cu prior dominant (0)", ex4_prior_dominant() == 0)

    # E5: NB bate baza triviala
    acc_nb, acc_maj = ex5_nb_vs_baza()
    ck("E5: NB bate baza triviala", acc_nb > acc_maj)

    print("\nTOATE EXERCITIILE M10 REZOLVATE: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _check()
        sys.exit(0)
    except (AssertionError, NotImplementedError) as e:
        print("PICA (asteptat pana rezolvi): %s" % e)
        sys.exit(1)
