#!/usr/bin/env python3
"""probabilitate_sklearn.py -- VALIDARE incrucisata a nucleului M01.

Ruleaza nucleul pur (probabilitate_core) si echivalentele din ecosistemul
scientific (scipy.stats / numpy) pe ACELEASI date si aserteaza ca rezultatele
coincid sub o toleranta. scikit-learn nu are estimatori MLE univariati dedicati
pentru aceste distributii, asa ca folosim scipy.stats (acceptat pentru validare).

Verifica patru lucruri:
  1. pdf gaussiana   vs scipy.stats.norm.pdf;
  2. pdf lognormala  vs scipy.stats.lognorm.pdf (cu maparea de parametri);
  3. MLE Gauss/lognormal/Bernoulli vs scipy.stats.*.fit / media empirica;
  4. interval bootstrap al mediei vs scipy.stats.bootstrap (metoda percentila).

Ruleaza: /home/ubuntu/ros2_ws/.venv_ml/bin/python probabilitate_sklearn.py  (0 = PASS).
"""
import os
import sys

import numpy as np
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml
from utils import rng  # noqa: E402

from probabilitate_core import (  # noqa: E402
    gauss_pdf, lognormal_pdf, mle_gauss, mle_lognormal, mle_bernoulli,
    bootstrap_mean_ci,
)


def main():
    ok = 0

    def ck(name, cond, detail=""):
        nonlocal ok
        assert cond, "DEZACORD nucleu vs scipy: " + name + " " + detail
        ok += 1
        print("  [ok] %s %s" % (name, detail))

    g = rng(0)

    # ---- 1. pdf gaussiana vs scipy.stats.norm ----
    xs = np.linspace(-6, 10, 50)
    mine = gauss_pdf(xs, mu=2.0, sigma=1.5)
    ref = stats.norm.pdf(xs, loc=2.0, scale=1.5)
    md = float(np.max(np.abs(mine - ref)))
    ck("gauss_pdf == scipy.norm.pdf", md < 1e-12, "(max diff %.2e)" % md)

    # ---- 2. pdf lognormala vs scipy.stats.lognorm ----
    # scipy: lognorm(s=sigma, scale=exp(mu)) <=> normala subiacenta N(mu, sigma^2)
    mu_ln, sig_ln = 0.3, 0.5
    xl = np.linspace(0.01, 30, 50)
    mine_ln = lognormal_pdf(xl, mu=mu_ln, sigma=sig_ln)
    ref_ln = stats.lognorm.pdf(xl, s=sig_ln, scale=np.exp(mu_ln))
    md_ln = float(np.max(np.abs(mine_ln - ref_ln)))
    ck("lognormal_pdf == scipy.lognorm.pdf", md_ln < 1e-12, "(max diff %.2e)" % md_ln)

    # ---- 3a. MLE Gauss vs scipy.stats.norm.fit ----
    xg = g.normal(5.0, 2.0, size=5000)
    mu_hat, s2_hat = mle_gauss(xg)
    loc_ref, scale_ref = stats.norm.fit(xg)  # scipy fit = MLE (numitor n)
    ck("MLE Gauss mu == scipy norm.fit loc", abs(mu_hat - loc_ref) < 1e-9,
       "(%.6f vs %.6f)" % (mu_hat, loc_ref))
    ck("MLE Gauss sigma == scipy norm.fit scale",
       abs(np.sqrt(s2_hat) - scale_ref) < 1e-9,
       "(%.6f vs %.6f)" % (np.sqrt(s2_hat), scale_ref))

    # ---- 3b. MLE lognormal vs scipy.stats.lognorm.fit (cu floc=0) ----
    xln = g.lognormal(mean=0.7, sigma=0.4, size=5000)
    mu_l, sig_l = mle_lognormal(xln)
    s_ref, _, scale_l = stats.lognorm.fit(xln, floc=0.0)  # MLE cu locatie fixata la 0
    ck("MLE lognormal sigma == scipy lognorm.fit s", abs(sig_l - s_ref) < 1e-6,
       "(%.6f vs %.6f)" % (sig_l, s_ref))
    ck("MLE lognormal mu == log(scale) scipy", abs(mu_l - np.log(scale_l)) < 1e-6,
       "(%.6f vs %.6f)" % (mu_l, np.log(scale_l)))

    # ---- 3c. MLE Bernoulli vs media empirica ----
    xb = (g.random(5000) < 0.3).astype(int)
    p_hat = mle_bernoulli(xb)
    ck("MLE Bernoulli p == media empirica", abs(p_hat - float(np.mean(xb))) < 1e-12,
       "(%.6f)" % p_hat)

    # ---- 4. bootstrap mediei vs scipy.stats.bootstrap (percentila) ----
    data = g.normal(10.0, 3.0, size=120)
    lo_mine, hi_mine, _ = bootstrap_mean_ci(data, n_boot=4000, alpha=0.05, seed=5)
    res = stats.bootstrap(
        (data,), np.mean, n_resamples=4000, method="percentile",
        confidence_level=0.95, random_state=np.random.default_rng(5),
    )
    lo_ref = float(res.confidence_interval.low)
    hi_ref = float(res.confidence_interval.high)
    # implementari diferite ale reesantionarii -> toleranta relativa la largimea CI
    width = hi_ref - lo_ref
    ck("bootstrap lo ~ scipy (percentila)", abs(lo_mine - lo_ref) < 0.10 * width,
       "(%.4f vs %.4f)" % (lo_mine, lo_ref))
    ck("bootstrap hi ~ scipy (percentila)", abs(hi_mine - hi_ref) < 0.10 * width,
       "(%.4f vs %.4f)" % (hi_mine, hi_ref))

    print("\nVALIDARE INCRUCISATA OK: %d comparatii nucleu-vs-scipy au coincis." % ok)
    return ok


if __name__ == "__main__":
    try:
        main()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
