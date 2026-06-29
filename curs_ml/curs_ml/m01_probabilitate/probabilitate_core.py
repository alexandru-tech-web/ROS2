#!/usr/bin/env python3
"""probabilitate_core.py -- nucleu PUR numpy pentru M01 (probabilitate si statistica).

Implementeaza de la zero, fara scikit-learn:
  - densitati de probabilitate (pdf): gaussiana si lognormala;
  - estimari de maxima verosimilitate (MLE):
      * Gauss: mu_hat = media esantionului, sigma2_hat = varianta (impartita la n);
      * Bernoulli: p_hat = fractia de succese;
  - bootstrap nonparametric pentru intervalul de incredere al mediei.

NOTATIE si FORMULE (ASCII-LaTeX inline):
  Gauss:      f(x) = 1/sqrt(2*pi*sigma^2) * exp( -(x-mu)^2 / (2*sigma^2) )
  Lognormal:  daca log(X) ~ Normal(mu, sigma^2), atunci pentru x > 0
              f(x) = 1/(x*sigma*sqrt(2*pi)) * exp( -(log(x)-mu)^2 / (2*sigma^2) )
              media lui X este  exp(mu + sigma^2/2).
  MLE Gauss:  mu_hat    = (1/n) * sum_i x_i
              sigma2_hat = (1/n) * sum_i (x_i - mu_hat)^2     (estimator BIASAT, /n)
  MLE Bern.:  p_hat     = (1/n) * sum_i x_i,  x_i in {0,1}
  Bootstrap:  reesantioneaza CU inlocuire de B ori, recalculeaza media, ia
              cuantilele empirice (metoda percentila) ca margini ale intervalului.

De ce conteaza pentru teza: campaniile C1 au N=5. Cu atat de putine repetitii,
o estimare punctuala (ex: media RTT) este zgomotoasa; bootstrap-ul si intervalele
de incredere fac VIZIBILA aceasta incertitudine in loc sa o ascunda.

ONESTITATE: in demo_sil.py datele sunt SINTETICE (semanate din C1/M), nu masuratori.
DETERMINISM: orice aleator trece prin numpy.random.default_rng(seed).

Ruleaza selftest-ul:
  /home/ubuntu/ros2_ws/.venv_ml/bin/python probabilitate_core.py   (0 = PASS).
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml
from utils import rng  # noqa: E402  (sursa unica de aleator in curs)


# ---------------------------------------------------------------- densitati (pdf)
def gauss_pdf(x, mu=0.0, sigma=1.0):
    """Densitatea normalei N(mu, sigma^2) evaluata in x (scalar sau vector numpy).

    f(x) = 1/sqrt(2*pi*sigma^2) * exp( -(x-mu)^2 / (2*sigma^2) ).
    sigma > 0. Integreaza la 1 pe toata axa reala.
    """
    x = np.asarray(x, dtype=float)
    sigma = float(sigma)
    if sigma <= 0:
        raise ValueError("sigma trebuie > 0, primit %r" % (sigma,))
    z = (x - mu) / sigma
    return np.exp(-0.5 * z * z) / (sigma * np.sqrt(2.0 * np.pi))


def lognormal_pdf(x, mu=0.0, sigma=1.0):
    """Densitatea lognormalei (log(X) ~ N(mu, sigma^2)) evaluata in x > 0.

    f(x) = 1/(x*sigma*sqrt(2*pi)) * exp( -(log(x)-mu)^2 / (2*sigma^2) ) pentru x > 0,
    si 0 pentru x <= 0. mu, sigma sunt parametrii NORMALEI subiacente (pe scala log).
    """
    x = np.asarray(x, dtype=float)
    sigma = float(sigma)
    if sigma <= 0:
        raise ValueError("sigma trebuie > 0, primit %r" % (sigma,))
    out = np.zeros_like(x, dtype=float)
    pos = x > 0.0
    z = (np.log(x[pos]) - mu) / sigma
    out[pos] = np.exp(-0.5 * z * z) / (x[pos] * sigma * np.sqrt(2.0 * np.pi))
    return out


def lognormal_mean(mu, sigma):
    """Media (asteptarea) unei variabile lognormale: E[X] = exp(mu + sigma^2/2)."""
    return float(np.exp(mu + 0.5 * float(sigma) ** 2))


# ---------------------------------------------------------------- MLE
def mle_gauss(samples):
    """MLE pentru N(mu, sigma^2): intoarce (mu_hat, sigma2_hat).

    mu_hat     = media esantionului;
    sigma2_hat = varianta cu numitor n (estimatorul de maxima verosimilitate,
                 BIASAT in jos cu factorul (n-1)/n fata de varianta nedeplasata).
    """
    x = np.asarray(samples, dtype=float).ravel()
    n = x.size
    if n < 1:
        raise ValueError("esantion gol")
    mu_hat = float(np.mean(x))
    sigma2_hat = float(np.mean((x - mu_hat) ** 2))  # numitor n -> MLE
    return mu_hat, sigma2_hat


def mle_lognormal(samples):
    """MLE pentru lognormala: aplica MLE-ul gaussian pe log(x).

    Intoarce (mu_hat, sigma_hat) ai NORMALEI subiacente (sigma_hat = abaterea).
    Toate valorile trebuie strict pozitive.
    """
    x = np.asarray(samples, dtype=float).ravel()
    if np.any(x <= 0):
        raise ValueError("lognormala cere valori strict pozitive")
    logs = np.log(x)
    mu_hat, sigma2_hat = mle_gauss(logs)
    return mu_hat, float(np.sqrt(sigma2_hat))


def mle_bernoulli(samples):
    """MLE pentru Bernoulli(p): p_hat = fractia de 1 din esantion.

    Esantionul trebuie sa contina doar 0 si 1.
    """
    x = np.asarray(samples, dtype=float).ravel()
    n = x.size
    if n < 1:
        raise ValueError("esantion gol")
    if not np.all((x == 0) | (x == 1)):
        raise ValueError("Bernoulli cere valori in {0, 1}")
    return float(np.mean(x))


# ---------------------------------------------------------------- bootstrap
def bootstrap_mean_ci(samples, n_boot=2000, alpha=0.05, seed=0,
                      statistic=np.mean):
    """Interval de incredere bootstrap (metoda percentila) pentru o statistica.

    Reesantioneaza CU inlocuire de n_boot ori, aplica `statistic` pe fiecare
    reesantion, si intoarce cuantilele empirice (alpha/2, 1-alpha/2).

    Intoarce (lo, hi, boot_stats):
      lo, hi      -- marginile intervalului la nivelul 1-alpha;
      boot_stats  -- vectorul celor n_boot statistici (util pentru histograma).

    Implicit statistic=media; orice functie esantion -> scalar este acceptata.
    """
    x = np.asarray(samples, dtype=float).ravel()
    n = x.size
    if n < 1:
        raise ValueError("esantion gol")
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha trebuie in (0, 1), primit %r" % (alpha,))
    g = rng(seed)
    idx = g.integers(0, n, size=(n_boot, n))  # n_boot reesantioane de marime n
    boot = np.array([float(statistic(x[row])) for row in idx])
    lo = float(np.quantile(boot, alpha / 2.0))
    hi = float(np.quantile(boot, 1.0 - alpha / 2.0))
    return lo, hi, boot


# ---------------------------------------------------------------- integrare numerica
def integrate_pdf(pdf, a, b, n_grid=20001):
    """Integreaza numeric o pdf pe [a, b] cu regula trapezului (verificare ~1)."""
    xs = np.linspace(a, b, n_grid)
    ys = pdf(xs)
    return float(np.trapezoid(ys, xs))


# ---------------------------------------------------------------- selftest
def _selftest():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    # --- pdf-urile integreaza ~1 numeric ---
    area_g = integrate_pdf(lambda t: gauss_pdf(t, mu=2.0, sigma=1.5), -20, 24)
    ck("gauss_pdf integreaza ~1", abs(area_g - 1.0) < 1e-4)
    area_ln = integrate_pdf(lambda t: lognormal_pdf(t, mu=0.3, sigma=0.5), 1e-6, 60)
    ck("lognormal_pdf integreaza ~1", abs(area_ln - 1.0) < 1e-3)
    ck("lognormal_pdf = 0 pe x <= 0",
       float(lognormal_pdf(np.array([-1.0, 0.0]))[0]) == 0.0
       and float(lognormal_pdf(np.array([-1.0, 0.0]))[1]) == 0.0)

    # --- valoare cunoscuta: gauss standard in 0 = 1/sqrt(2*pi) ---
    ck("gauss_pdf(0;0,1) = 1/sqrt(2*pi)",
       abs(float(gauss_pdf(0.0)) - 1.0 / np.sqrt(2.0 * np.pi)) < 1e-12)

    # --- lognormal_mean = exp(mu + sigma^2/2) ---
    ck("lognormal_mean formula", abs(lognormal_mean(0.0, 1.0) - np.exp(0.5)) < 1e-12)

    # --- MLE Gauss recupereaza parametrii pe esantion mare ---
    g = rng(7)
    xg = g.normal(5.0, 2.0, size=200000)
    mu_hat, s2_hat = mle_gauss(xg)
    ck("MLE Gauss: mu_hat ~ 5 pe esantion mare", abs(mu_hat - 5.0) < 0.02)
    ck("MLE Gauss: sigma2_hat ~ 4 pe esantion mare", abs(s2_hat - 4.0) < 0.05)
    # estimatorul MLE foloseste numitor n (biasat fata de varianta /(n-1))
    small = np.array([1.0, 2.0, 3.0, 4.0])
    _, s2_small = mle_gauss(small)
    ck("MLE Gauss: numitor n (1.25, nu 1.6667)", abs(s2_small - 1.25) < 1e-12)

    # --- MLE lognormal recupereaza mu, sigma ai normalei subiacente ---
    mu_true, sig_true = 0.7, 0.4
    xln = g.lognormal(mean=mu_true, sigma=sig_true, size=200000)
    mu_ln, sig_ln = mle_lognormal(xln)
    ck("MLE lognormal: mu_hat ~ 0.7", abs(mu_ln - mu_true) < 0.01)
    ck("MLE lognormal: sigma_hat ~ 0.4", abs(sig_ln - sig_true) < 0.01)

    # --- MLE Bernoulli recupereaza p pe esantion mare ---
    xb = (g.random(200000) < 0.3).astype(int)
    p_hat = mle_bernoulli(xb)
    ck("MLE Bernoulli: p_hat ~ 0.3", abs(p_hat - 0.3) < 0.01)
    ck("MLE Bernoulli: caz cunoscut [1,1,0,0,1] = 0.6",
       abs(mle_bernoulli([1, 1, 0, 0, 1]) - 0.6) < 1e-12)

    # --- bootstrap: ordonarea marginilor si acoperirea mediei adevarate ---
    base = rng(11).normal(10.0, 3.0, size=80)
    lo, hi, boot = bootstrap_mean_ci(base, n_boot=3000, alpha=0.05, seed=1)
    ck("bootstrap: lo < media esantion < hi", lo < float(np.mean(base)) < hi)
    ck("bootstrap: vectorul boot are n_boot elemente", boot.size == 3000)
    ck("bootstrap: determinist la aceeasi samanta",
       bootstrap_mean_ci(base, n_boot=500, seed=1)[0]
       == bootstrap_mean_ci(base, n_boot=500, seed=1)[0])

    # --- acoperire: pe repetari, intervalul 95% prinde media adevarata ~95% ---
    mu_true2 = 50.0
    covered = 0
    reps = 200
    gg = rng(123)
    for r in range(reps):
        sample = gg.normal(mu_true2, 8.0, size=40)
        lo_r, hi_r, _ = bootstrap_mean_ci(sample, n_boot=400, alpha=0.05,
                                          seed=1000 + r)
        if lo_r <= mu_true2 <= hi_r:
            covered += 1
    cov = covered / reps
    ck("bootstrap: acoperire empirica ~0.95 (in [0.88, 1.0])", 0.88 <= cov <= 1.0)
    print("    (acoperire empirica masurata: %.3f pe %d repetari)" % (cov, reps))

    print("\nTOATE VERIFICARILE probabilitate_core AU TRECUT: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _selftest()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
