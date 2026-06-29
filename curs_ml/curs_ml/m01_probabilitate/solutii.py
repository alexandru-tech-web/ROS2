#!/usr/bin/env python3
"""solutii.py -- solutiile complete pentru exercitii.py (M01).

Rulat cu venv trebuie sa TREACA (exit 0):
  /home/ubuntu/ros2_ws/.venv_ml/bin/python solutii.py

Acelasi set de verificari ca exercitii.py, dar cu implementarile corecte.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml
from utils import rng  # noqa: E402
from date_sar import make_latency_dataset  # noqa: E402


# ---------------------------------------------------------------------------
# Ex. 1 -- pdf gaussiana.
def gauss_pdf(x, mu=0.0, sigma=1.0):
    x = np.asarray(x, dtype=float)
    sigma = float(sigma)
    z = (x - mu) / sigma
    return np.exp(-0.5 * z * z) / (sigma * np.sqrt(2.0 * np.pi))


# ---------------------------------------------------------------------------
# Ex. 2 -- MLE Gauss (numitor n).
def mle_gauss(samples):
    x = np.asarray(samples, dtype=float).ravel()
    mu_hat = float(np.mean(x))
    sigma2_hat = float(np.mean((x - mu_hat) ** 2))  # numitor n -> MLE
    return mu_hat, sigma2_hat


# ---------------------------------------------------------------------------
# Ex. 3 -- MLE Bernoulli.
def mle_bernoulli(samples):
    x = np.asarray(samples, dtype=float).ravel()
    return float(np.mean(x))


# ---------------------------------------------------------------------------
# Ex. 4 -- bootstrap percentila pentru media.
def bootstrap_mean_ci(samples, n_boot=2000, alpha=0.05, seed=0):
    x = np.asarray(samples, dtype=float).ravel()
    n = x.size
    g = rng(seed)
    idx = g.integers(0, n, size=(n_boot, n))
    means = x[idx].mean(axis=1)
    lo = float(np.quantile(means, alpha / 2.0))
    hi = float(np.quantile(means, 1.0 - alpha / 2.0))
    return lo, hi


# ---------------------------------------------------------------------------
# Ex. 5 -- aplica pe alta conditie.
def media_rtt_loss30_zenoh():
    df = make_latency_dataset(n_per_cond=300, seed=0)
    sub = df[(df.condition == "loss_30") & (df.middleware == "Zenoh")]
    return float(sub.rtt_ms.mean())


# ---------------------------------------------------------------------------
def _verifica():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
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

    print("\nTOATE SOLUTIILE M01 TREC: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _verifica()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
