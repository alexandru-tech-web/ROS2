#!/usr/bin/env python3
"""exercitii.py -- stub-uri TODO pentru M01 (probabilitate si statistica).

Completeaza fiecare functie marcata cu TODO. RULAT ACUM trebuie sa PICE clar
(un assert da AssertionError cu mesaj), pentru ca stub-urile intorc valori
gresite intentionat. Cand le rezolvi corect, `_verifica()` trebuie sa treaca.

Solutiile complete sunt in solutii.py (NU te uita inainte sa incerci).

Ruleaza: /home/ubuntu/ros2_ws/.venv_ml/bin/python exercitii.py
  -> ACUM: iese cu cod != 0 (e corect, exercitiile nu sunt rezolvate).
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml
from utils import rng  # noqa: E402
from date_sar import make_latency_dataset  # noqa: E402


# ---------------------------------------------------------------------------
# Ex. 1 -- pdf gaussiana de la zero.
#   Implementeaza f(x) = 1/sqrt(2*pi*sigma^2) * exp(-(x-mu)^2/(2*sigma^2)).
def gauss_pdf(x, mu=0.0, sigma=1.0):
    x = np.asarray(x, dtype=float)
    # TODO: inlocuieste cu formula corecta a densitatii normale
    return np.zeros_like(x)  # STUB gresit


# ---------------------------------------------------------------------------
# Ex. 2 -- MLE pentru Gauss.
#   Intoarce (mu_hat, sigma2_hat) cu sigma2_hat avand NUMITOR n (estimator MLE).
def mle_gauss(samples):
    x = np.asarray(samples, dtype=float).ravel()
    # TODO: calculeaza media si varianta cu numitor n
    return 0.0, 0.0  # STUB gresit


# ---------------------------------------------------------------------------
# Ex. 3 -- MLE pentru Bernoulli.
#   p_hat = fractia de 1 din esantion (valori in {0,1}).
def mle_bernoulli(samples):
    x = np.asarray(samples, dtype=float).ravel()
    # TODO: intoarce fractia de succese
    return 0.0  # STUB gresit


# ---------------------------------------------------------------------------
# Ex. 4 -- bootstrap percentila pentru media.
#   Reesantioneaza CU inlocuire de n_boot ori, ia cuantilele (alpha/2, 1-alpha/2)
#   ale mediilor. Foloseste rng(seed) pentru determinism.
def bootstrap_mean_ci(samples, n_boot=2000, alpha=0.05, seed=0):
    x = np.asarray(samples, dtype=float).ravel()
    # TODO: implementeaza bootstrap-ul percentila; intoarce (lo, hi)
    return 0.0, 0.0  # STUB gresit


# ---------------------------------------------------------------------------
# Ex. 5 -- aplica pe alta conditie din make_latency_dataset.
#   Intoarce media RTT a conditiei 'loss_30' / 'Zenoh' (n_per_cond=300, seed=0).
def media_rtt_loss30_zenoh():
    df = make_latency_dataset(n_per_cond=300, seed=0)
    # TODO: filtreaza condition=='loss_30' si middleware=='Zenoh', intoarce media rtt_ms
    return -1.0  # STUB gresit


# ---------------------------------------------------------------------------
def _verifica():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "PICA (de rezolvat): " + name
        ok += 1
        print("  [ok] " + name)

    # Ex.1
    ck("gauss_pdf(0;0,1) = 1/sqrt(2*pi)",
       abs(float(gauss_pdf(0.0)) - 1.0 / np.sqrt(2.0 * np.pi)) < 1e-12)
    ck("gauss_pdf simetrica in jurul lui mu",
       abs(float(gauss_pdf(1.0, mu=3.0, sigma=2.0))
           - float(gauss_pdf(5.0, mu=3.0, sigma=2.0))) < 1e-12)

    # Ex.2
    mu_h, s2_h = mle_gauss([1.0, 2.0, 3.0, 4.0])
    ck("mle_gauss mu = 2.5", abs(mu_h - 2.5) < 1e-12)
    ck("mle_gauss sigma2 = 1.25 (numitor n)", abs(s2_h - 1.25) < 1e-12)

    # Ex.3
    ck("mle_bernoulli [1,1,0,0,1] = 0.6", abs(mle_bernoulli([1, 1, 0, 0, 1]) - 0.6) < 1e-12)

    # Ex.4
    base = rng(11).normal(10.0, 3.0, size=80)
    lo, hi = bootstrap_mean_ci(base, n_boot=2000, alpha=0.05, seed=1)
    ck("bootstrap: lo < media < hi", lo < float(np.mean(base)) < hi)
    ck("bootstrap: interval rezonabil de ingust (hi-lo < 3)", 0 < (hi - lo) < 3.0)

    # Ex.5
    m = media_rtt_loss30_zenoh()
    ck("media RTT loss_30/Zenoh in interval plauzibil (1500..6000 ms)",
       1500.0 < m < 6000.0)

    print("\nTOATE EXERCITIILE M01 REZOLVATE: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _verifica()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        print("\n[exercitii] inca nerezolvate -- e normal sa pice acum.")
        sys.exit(1)
