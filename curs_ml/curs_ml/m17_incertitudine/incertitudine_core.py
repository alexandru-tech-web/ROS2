#!/usr/bin/env python3
"""incertitudine_core.py -- nucleul M17, numpy pur (scikit-learn INTERZIS).

Cuantificarea incertitudinii unei predictii. Trei pietre de temelie:

1. BayesianLinearRegression -- regresie liniara bayesiana. In loc de UN singur
   vector de greutati w, intoarce o DISTRIBUTIE pe w (posterior gaussian). De aici
   o predictie cu VARIANTA, nu doar o medie. Posterior:
       S = (lam I + (1/sig2) X^T X)^-1            (covarianta pe w)
       m = (1/sig2) S X^T y                       (media pe w)
   Varianta predictiva intr-un punct x (cu bias):
       var(x) = sig2 + x^T S x
   (sig2 = zgomotul observatiilor; x^T S x = incertitudinea pe parametri).

2. bootstrap_predict_interval -- interval prin reesantionare: reantreneaza modelul
   pe B esantioane bootstrap, aduna predictiile, ia cuantilele empirice. Nu cere
   ipoteze gaussiene; surprinde incertitudinea pe parametri (nu si zgomotul nou).

3. conformal_split -- conformal prediction split: cuantila reziduurilor pe un set
   de CALIBRARE da un interval cu acoperire GARANTATA (sub schimb, fara ipoteze pe
   forma erorii). Garantia e marginala: P(y in interval) >= 1 - alpha.

DE CE M17 E SEMNATURA TEZEI: campaniile au N mic (C1: N=5). La N=5 o predictie
fara bara de eroare e inutila -- nu poti spune daca diferenta dintre Zenoh si DDS
e reala sau zgomot. Acest modul da barele de eroare.

Determinism: orice aleator trece prin numpy.random.default_rng(seed).
_selftest() verifica:
  - posteriorul se CONTRACTA cand cresc datele (urma covariantei scade);
  - media posterioara ~ OLS la prior slab (lam mic);
  - intervalul predictiv bayesian acopera ~ nivelul tinta pe date sintetice;
  - conformal: acoperirea empirica pe test >= 1 - alpha - toleranta.

Ruleaza: /home/ubuntu/ros2_ws/.venv_ml/bin/python incertitudine_core.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from utils import add_bias  # noqa: E402


# ============================================================ BAYESIAN LINEAR
class BayesianLinearRegression:
    """Regresie liniara bayesiana cu prior gaussian izotrop pe greutati.

    Model: y = phi(x)^T w + zgomot, zgomot ~ N(0, sig2).
    Prior:  w ~ N(0, (1/lam) I).
    Posterior (conjugat, gaussian):
        S = (lam I + (1/sig2) Phi^T Phi)^-1
        m = (1/sig2) S Phi^T y
    Predictie intr-un punct (cu bias) phi:
        medie    = phi^T m
        varianta = sig2 + phi^T S phi   (zgomot + incertitudine pe parametri)

    lam = precizia prior-ului (lam mic = prior slab -> media ~ OLS).
    sig2 = varianta zgomotului observatiilor (poate fi estimata din reziduuri).
    add_intercept = adauga coloana de 1 (interceptul nu e penalizat aici decat la
    fel ca restul; pentru curs e suficient).
    """

    def __init__(self, lam=1.0, sig2=1.0, add_intercept=True):
        self.lam = float(lam)
        self.sig2 = float(sig2)
        self.add_intercept = bool(add_intercept)
        self.m = None      # media posterioara pe w
        self.S = None      # covarianta posterioara pe w
        self.d = None      # dimensiunea lui w (cu bias)

    def _design(self, X):
        X = np.asarray(X, dtype=float)
        if X.ndim == 1:
            X = X.reshape(-1, 1)
        return add_bias(X) if self.add_intercept else X

    def fit(self, X, y):
        """Calculeaza posteriorul (m, S) din date. Returneaza self."""
        Phi = self._design(X)
        y = np.asarray(y, dtype=float).reshape(-1)
        d = Phi.shape[1]
        A = self.lam * np.eye(d) + (1.0 / self.sig2) * (Phi.T @ Phi)
        self.S = np.linalg.inv(A)
        self.m = (1.0 / self.sig2) * (self.S @ (Phi.T @ y))
        self.d = d
        return self

    def predict(self, X, return_std=False):
        """Media predictiva (si optional abaterea standard predictiva) in punctele X.

        Daca return_std=True, intoarce (medie, std) unde std = sqrt(sig2 + phi^T S phi)
        per punct: abaterea standard a unei OBSERVATII noi (interval de PREDICTIE).
        """
        if self.m is None:
            raise RuntimeError("cheama fit() inainte de predict()")
        Phi = self._design(X)
        mean = Phi @ self.m
        if not return_std:
            return mean
        # varianta predictiva per rand: sig2 + diag(Phi S Phi^T)
        var_param = np.einsum("ij,jk,ik->i", Phi, self.S, Phi)
        var_pred = self.sig2 + var_param
        return mean, np.sqrt(var_pred)

    def predict_interval(self, X, level=0.95):
        """Interval de PREDICTIE gaussian la nivelul cerut (acopera o observatie noua).

        Returneaza (medie, lo, hi). Foloseste cuantila normala z pentru `level`.
        """
        mean, std = self.predict(X, return_std=True)
        z = _normal_quantile(0.5 + level / 2.0)
        return mean, mean - z * std, mean + z * std

    def cov_trace(self):
        """Urma covariantei posterioare (masura scalara a incertitudinii pe w).
        Scade cand adaugi date informative -> posteriorul se contracta."""
        if self.S is None:
            raise RuntimeError("cheama fit() inainte de cov_trace()")
        return float(np.trace(self.S))


# ------------------------------------------------ cuantila normala (fara scipy)
def _normal_quantile(p):
    """Cuantila (inversa CDF) a normalei standard, aproximare Acklam. p in (0,1).

    Folosita ca sa nu importam scipy in nucleul pur. Eroare absoluta < 1.2e-9.
    """
    p = float(p)
    if not 0.0 < p < 1.0:
        raise ValueError("p trebuie in (0,1), primit %r" % (p,))
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    plow, phigh = 0.02425, 1.0 - 0.02425
    if p < plow:
        q = np.sqrt(-2.0 * np.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
               ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1.0)
    if p > phigh:
        q = np.sqrt(-2.0 * np.log(1.0 - p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
               ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1.0)
    q = p - 0.5
    r = q * q
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5]) * q / \
           (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1.0)


# ============================================================ BOOTSTRAP
def bootstrap_predict_interval(X_train, y_train, X_query, fit_predict,
                               B=200, level=0.95, seed=0):
    """Interval prin reesantionare bootstrap pe setul de antrenare.

    Reantreneaza modelul pe B esantioane bootstrap (cu inlocuire) si colecteaza
    predictiile in punctele X_query. Intoarce (medie, lo, hi) ca array-uri,
    unde lo/hi sunt cuantilele empirice (1-level)/2 si (1+level)/2 ale norului de
    predictii bootstrap.

    fit_predict(X_tr, y_tr, X_q) -> y_pred. Surprinde incertitudinea pe PARAMETRI
    (din varietatea seturilor de antrenare), NU zgomotul unei observatii noi -- deci
    e un interval de INCREDERE pe medie, mai ingust decat unul de predictie.
    """
    X_train = np.asarray(X_train, dtype=float)
    y_train = np.asarray(y_train, dtype=float).reshape(-1)
    X_query = np.asarray(X_query, dtype=float)
    n = X_train.shape[0]
    g = np.random.default_rng(seed)
    preds = np.empty((B, X_query.shape[0]), dtype=float)
    for b in range(B):
        idx = g.integers(0, n, size=n)  # reesantionare cu inlocuire
        preds[b] = fit_predict(X_train[idx], y_train[idx], X_query)
    alpha = 1.0 - level
    lo = np.percentile(preds, 100.0 * (alpha / 2.0), axis=0)
    hi = np.percentile(preds, 100.0 * (1.0 - alpha / 2.0), axis=0)
    mean = preds.mean(axis=0)
    return mean, lo, hi


# ============================================================ CONFORMAL SPLIT
def conformal_split(X_train, y_train, X_calib, y_calib, X_query, fit_predict,
                    alpha=0.1):
    """Conformal prediction split: interval cu acoperire marginala garantata.

    Procedura:
      1. antreneaza pe (X_train, y_train);
      2. calculeaza scorurile de neconformitate pe CALIBRARE: r_i = |y_i - pred_i|;
      3. q = cuantila ajustata de finitudine, nivel ceil((n_cal+1)(1-alpha))/n_cal,
         a reziduurilor de calibrare;
      4. interval in X_query: pred(x) +/- q.

    Garantie (sub ipoteza de schimb): P(y_nou in interval) >= 1 - alpha.
    Returneaza (medie, lo, hi, q).
    """
    X_calib = np.asarray(X_calib, dtype=float)
    y_calib = np.asarray(y_calib, dtype=float).reshape(-1)
    X_query = np.asarray(X_query, dtype=float)
    pred_cal = np.asarray(fit_predict(X_train, y_train, X_calib), dtype=float).reshape(-1)
    resid = np.abs(y_calib - pred_cal)
    n_cal = resid.shape[0]
    # nivel ajustat de finitudine (conformal split valid pentru esantion finit)
    k = int(np.ceil((n_cal + 1) * (1.0 - alpha)))
    k = min(k, n_cal)  # daca (n_cal+1)(1-alpha) > n_cal -> banda infinita; aici o legam
    q = float(np.sort(resid)[k - 1])
    mean = np.asarray(fit_predict(X_train, y_train, X_query), dtype=float).reshape(-1)
    return mean, mean - q, mean + q, q


def empirical_coverage(y_true, lo, hi):
    """Fractia de tinte care cad in [lo, hi] (acoperirea empirica)."""
    y_true = np.asarray(y_true, dtype=float).reshape(-1)
    lo = np.asarray(lo, dtype=float).reshape(-1)
    hi = np.asarray(hi, dtype=float).reshape(-1)
    return float(np.mean((y_true >= lo) & (y_true <= hi)))


# ============================================================ AUXILIAR PT TESTE
def _ols_fit_predict(X_tr, y_tr, X_te):
    """Model auxiliar pentru bootstrap/conformal: regresie liniara cu bias (lstsq)."""
    Phi = add_bias(np.asarray(X_tr, dtype=float))
    w, *_ = np.linalg.lstsq(Phi, np.asarray(y_tr, dtype=float).reshape(-1), rcond=None)
    return add_bias(np.asarray(X_te, dtype=float)) @ w


# ============================================================ SELFTEST
def _selftest():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    rng = np.random.default_rng(0)

    # cuantila normala: valori cunoscute
    ck("normal_quantile: z(0.975) ~ 1.95996",
       abs(_normal_quantile(0.975) - 1.959963985) < 1e-6)
    ck("normal_quantile: z(0.5) ~ 0", abs(_normal_quantile(0.5)) < 1e-9)

    # date liniare 1D pentru bayesian
    w_true, b_true, sig = 2.0, -1.0, 0.5
    X_small = rng.uniform(-3, 3, size=(8, 1))
    y_small = b_true + w_true * X_small[:, 0] + sig * rng.standard_normal(8)
    X_big = rng.uniform(-3, 3, size=(400, 1))
    y_big = b_true + w_true * X_big[:, 0] + sig * rng.standard_normal(400)

    # 1) posteriorul se CONTRACTA cand cresc datele (urma covariantei scade)
    blr_small = BayesianLinearRegression(lam=1e-3, sig2=sig**2).fit(X_small, y_small)
    blr_big = BayesianLinearRegression(lam=1e-3, sig2=sig**2).fit(X_big, y_big)
    ck("posterior se contracta cu mai multe date (trace S scade)",
       blr_big.cov_trace() < blr_small.cov_trace())

    # 2) media posterioara ~ OLS la prior slab (lam mic)
    Phi = add_bias(X_big)
    w_ols, *_ = np.linalg.lstsq(Phi, y_big, rcond=None)
    ck("media posterioara ~ OLS la prior slab (lam=1e-6)",
       np.allclose(BayesianLinearRegression(lam=1e-6, sig2=sig**2)
                   .fit(X_big, y_big).m, w_ols, atol=1e-3))

    # 3) interval predictiv bayesian acopera ~ nivelul tinta pe date sintetice
    X_tr = rng.uniform(-3, 3, size=(120, 1))
    y_tr = b_true + w_true * X_tr[:, 0] + sig * rng.standard_normal(120)
    X_te = rng.uniform(-3, 3, size=(2000, 1))
    y_te = b_true + w_true * X_te[:, 0] + sig * rng.standard_normal(2000)
    blr = BayesianLinearRegression(lam=1e-3, sig2=sig**2).fit(X_tr, y_tr)
    _, lo, hi = blr.predict_interval(X_te, level=0.90)
    cov90 = empirical_coverage(y_te, lo, hi)
    ck("interval predictiv bayesian 90%% acopera ~0.90 (>=0.86)", cov90 >= 0.86)

    # 4) bootstrap: interval de incredere pe medie, mai ingust decat predictia
    mean_b, lo_b, hi_b = bootstrap_predict_interval(
        X_tr, y_tr, X_te[:50], _ols_fit_predict, B=120, level=0.90, seed=1)
    width_boot = float(np.mean(hi_b - lo_b))
    _, lo_p, hi_p = blr.predict_interval(X_te[:50], level=0.90)
    width_pred = float(np.mean(hi_p - lo_p))
    ck("bootstrap (incredere) mai ingust decat predictia bayesiana",
       width_boot < width_pred)

    # 5) conformal split: acoperire empirica pe test >= 1 - alpha - toleranta
    perm = rng.permutation(X_tr.shape[0])
    cut = X_tr.shape[0] // 2
    tr_idx, cal_idx = perm[:cut], perm[cut:]
    alpha = 0.1
    mean_c, lo_c, hi_c, q = conformal_split(
        X_tr[tr_idx], y_tr[tr_idx], X_tr[cal_idx], y_tr[cal_idx],
        X_te, _ols_fit_predict, alpha=alpha)
    cov_conf = empirical_coverage(y_te, lo_c, hi_c)
    ck("conformal: acoperire empirica >= 1-alpha-toleranta (>=0.88 la alpha=0.1)",
       cov_conf >= 0.88)
    ck("conformal: latimea benzii q > 0", q > 0)

    print("\nTOATE VERIFICARILE incertitudine_core AU TRECUT: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _selftest()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
