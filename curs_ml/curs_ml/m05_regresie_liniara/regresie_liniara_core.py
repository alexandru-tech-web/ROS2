#!/usr/bin/env python3
"""regresie_liniara_core.py -- regresie liniara PURA in numpy (M05).

Model: y_hat = X w, unde X are deja coloana de bias (interceptul) la stanga.
Antrenam parametrii w in DOUA feluri echivalente:

1) Ecuatii normale (solutie inchisa). Minimizam riscul empiric patratic
       J(w) = || X w - y ||^2
   Anuland gradientul, nabla_w J = 2 X^T (X w - y) = 0, obtinem sistemul normal
       (X^T X) w = X^T y   =>   w = (X^T X)^{-1} X^T y.
   In cod folosim numpy.linalg.solve (sau lstsq cand X^T X e prost conditionata),
   NU inversa explicita -- mai stabil numeric.

2) Coborare pe gradient (gradient descent). Iteram
       w <- w - alpha * grad,   grad = (2/n) X^T (X w - y)
   pana la convergenta. Cu o rata de invatare alpha potrivita pe date
   standardizate, GD converge spre ACEEASI solutie ca ecuatiile normale.

Ipotezele modelului liniar (pentru interpretare, nu pentru a rula codul):
  - liniaritate: E[y|X] = X w (relatie liniara in parametri);
  - erori cu media zero si varianta constanta (homoscedasticitate);
  - erori necorelate; pentru inferenta (intervale) se adauga normalitatea;
  - coloane ale lui X liniar independente (altfel X^T X e singulara).

Conditionare: daca feature-urile au scari foarte diferite sau sunt aproape
coliniare, X^T X are numar de conditie mare -> solutia inchisa devine instabila
si GD converge incet. Remediul didactic aici: standardizarea feature-urilor
(z-score) inainte de antrenare. Vezi numar_conditie() si demo.

ONESTITATE: datele de demonstratie din curs sunt SINTETICE (semanate din campania
C1/M). Acest fisier nu depinde de date reale -- selftest-ul ruleaza pe date
sintetice cu w_adevarat cunoscut.

scikit-learn este INTERZIS aici. Doar numpy (+ utils pentru auxiliare: split,
standardizare, metrici). Ruleaza: python3 regresie_liniara_core.py  (0 = PASS).
"""
import os
import sys

import numpy as np

# permite rularea ca 'python3 fisier.py' din orice cwd: adauga .../curs_ml/curs_ml
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import add_bias, r2_score, rmse, rng  # noqa: E402


# ----------------------------------------------------------------------------
def fit_normal_equations(X, y, ridge=0.0):
    """Rezolva ecuatiile normale (X^T X + ridge*I) w = X^T y.

    X: (n, d) matricea de design (include deja coloana de bias daca o vrei).
    y: (n,) tinta. ridge >= 0: mic termen de stabilizare (0 = pur OLS).
    Returneaza w: (d,). Folosim solve pe sistemul normal, NU inversa explicita;
    daca matricea e singulara cadem pe lstsq (solutie de norma minima)."""
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float).ravel()
    d = X.shape[1]
    A = X.T @ X + ridge * np.eye(d)
    b = X.T @ y
    try:
        w = np.linalg.solve(A, b)
    except np.linalg.LinAlgError:
        w, *_ = np.linalg.lstsq(X, y, rcond=None)
    return w


# ----------------------------------------------------------------------------
def fit_gradient_descent(X, y, alpha=0.1, n_iter=5000, tol=1e-10, w0=None,
                         return_history=False):
    """Coborare pe gradient pentru J(w) = ||Xw - y||^2 (pierdere medie patratica).

    Gradientul mediei patratice: grad = (2/n) X^T (X w - y).
    alpha: rata de invatare. Pe feature-uri standardizate, alpha ~ 0.1 merge.
    Opreste cand ||grad|| < tol sau dupa n_iter pasi. Daca return_history,
    intoarce si lista pierderilor (MSE) per iteratie. Returneaza w (sau (w, hist))."""
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float).ravel()
    n, d = X.shape
    w = np.zeros(d) if w0 is None else np.asarray(w0, dtype=float).copy()
    hist = []
    for _ in range(int(n_iter)):
        resid = X @ w - y
        if return_history:
            hist.append(float(np.mean(resid ** 2)))
        grad = (2.0 / n) * (X.T @ resid)
        if np.linalg.norm(grad) < tol:
            break
        w = w - alpha * grad
    if return_history:
        return w, hist
    return w


# ----------------------------------------------------------------------------
def predict(X, w):
    """Predictie liniara y_hat = X w. X trebuie sa aiba aceleasi coloane ca la fit."""
    return np.asarray(X, dtype=float) @ np.asarray(w, dtype=float).ravel()


# ----------------------------------------------------------------------------
def numar_conditie(X):
    """Numar de conditie al lui X^T X (raport valoarea proprie max / min).

    Valori mari (>> 1) semnaleaza coliniaritate / scari diferite -> solutie
    instabila si GD lent. Standardizarea il reduce. Folosim valori singulare:
    cond(X^T X) = (sigma_max / sigma_min)^2."""
    X = np.asarray(X, dtype=float)
    s = np.linalg.svd(X, compute_uv=False)
    s_min = s[-1]
    if s_min < 1e-300:
        return float("inf")
    return float((s[0] / s_min) ** 2)


# ----------------------------------------------------------------------------
class RegresieLiniara:
    """Invelis subtire peste cele doua metode, cu API fit/predict.

    method in {'normal', 'gd'}. fit_intercept adauga coloana de bias intern
    (daca True, X-ul dat NU trebuie sa aiba deja bias)."""

    def __init__(self, method="normal", fit_intercept=True, alpha=0.1,
                 n_iter=5000, ridge=0.0):
        self.method = method
        self.fit_intercept = fit_intercept
        self.alpha = alpha
        self.n_iter = n_iter
        self.ridge = ridge
        self.w_ = None

    def _design(self, X):
        X = np.asarray(X, dtype=float)
        if X.ndim == 1:
            X = X.reshape(-1, 1)
        return add_bias(X) if self.fit_intercept else X

    def fit(self, X, y):
        Xd = self._design(X)
        if self.method == "normal":
            self.w_ = fit_normal_equations(Xd, y, ridge=self.ridge)
        elif self.method == "gd":
            self.w_ = fit_gradient_descent(Xd, y, alpha=self.alpha,
                                           n_iter=self.n_iter)
        else:
            raise ValueError("method necunoscut: %r ('normal'|'gd')" % (self.method,))
        return self

    def predict(self, X):
        if self.w_ is None:
            raise RuntimeError("cheama fit() inainte de predict()")
        return predict(self._design(X), self.w_)


# ----------------------------------------------------------------------------
def _make_linear_data(n=300, d=3, noise=0.5, seed=0):
    """Date sintetice cu w_adevarat cunoscut: y = bias + X w_true + zgomot."""
    g = rng(seed)
    X = g.normal(0.0, 1.0, size=(n, d))
    w_true = g.normal(0.0, 2.0, size=d)
    bias_true = 1.5
    y = bias_true + X @ w_true + g.normal(0.0, noise, size=n)
    return X, y, bias_true, w_true


# ----------------------------------------------------------------------------
def _selftest():
    """Verifica CORECTITUDINEA pe cazuri cunoscute. Tipareste [ok]/PASS, exit 0/1."""
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    # (1) Caz mic, calculabil de mana: y = 1 + 2x pe trei puncte fara zgomot.
    #     Ecuatiile normale trebuie sa recupereze EXACT [bias=1, panta=2].
    Xs = np.array([[1.0], [2.0], [3.0]])
    ys = np.array([3.0, 5.0, 7.0])
    w_small = fit_normal_equations(add_bias(Xs), ys)
    ck("ecuatii normale: y=1+2x -> w=[1,2] exact",
       np.allclose(w_small, [1.0, 2.0], atol=1e-9))

    # (2) Pe date generate cu w_adevarat cunoscut, recupereaza w_adevarat.
    X, y, bias_true, w_true = _make_linear_data(n=400, d=3, noise=0.4, seed=1)
    Xb = add_bias(X)
    w_ne = fit_normal_equations(Xb, y)
    ck("recupereaza interceptul adevarat (~1.5)", abs(w_ne[0] - bias_true) < 0.15)
    ck("recupereaza pantele adevarate w_true",
       np.allclose(w_ne[1:], w_true, atol=0.12))

    # (3) Solutia inchisa == solutia GD sub toleranta (pe ACELEASI date).
    #     Standardizam intai feature-urile ca GD sa convearga repede.
    mean, std = X.mean(axis=0), X.std(axis=0)
    Xs_std = (X - mean) / std
    Xb_std = add_bias(Xs_std)
    w_ne_std = fit_normal_equations(Xb_std, y)
    w_gd_std = fit_gradient_descent(Xb_std, y, alpha=0.2, n_iter=20000, tol=1e-12)
    ck("solutie inchisa == gradient descent (||.|| < 1e-4)",
       np.allclose(w_ne_std, w_gd_std, atol=1e-4))
    # si predictiile coincid
    ck("predictii NE ~ predictii GD (RMSE intre ele < 1e-4)",
       rmse(predict(Xb_std, w_ne_std), predict(Xb_std, w_gd_std)) < 1e-4)

    # (4) R^2 ridicat pe date liniare (zgomot mic).
    Xq, yq, _, _ = _make_linear_data(n=500, d=2, noise=0.2, seed=2)
    model = RegresieLiniara(method="normal").fit(Xq, yq)
    r2 = r2_score(yq, model.predict(Xq))
    ck("R^2 > 0.97 pe date liniare cu zgomot mic", r2 > 0.97)

    # (5) GD reduce monoton (in mare) pierderea: ultima < prima.
    _, hist = fit_gradient_descent(Xb_std, y, alpha=0.2, n_iter=200,
                                   tol=0.0, return_history=True)
    ck("GD: pierderea finala < pierderea initiala", hist[-1] < hist[0])

    # (6) API-ul de clasa cu cele doua metode da acelasi rezultat (standardizat).
    #     Folosim date standardizate ca GD sa ajunga la solutia inchisa.
    mA = RegresieLiniara(method="normal").fit(Xs_std, y)
    mB = RegresieLiniara(method="gd", alpha=0.2, n_iter=20000).fit(Xs_std, y)
    ck("clasa: 'normal' ~ 'gd' pe predictii (RMSE < 1e-3)",
       rmse(mA.predict(Xs_std), mB.predict(Xs_std)) < 1e-3)

    # (7) Conditionarea scade prin standardizare (scari foarte diferite).
    Xbad = X.copy()
    Xbad[:, 0] *= 1000.0  # un feature pe scara mult mai mare
    cond_brut = numar_conditie(add_bias(Xbad))
    cond_std = numar_conditie(add_bias((Xbad - Xbad.mean(0)) / Xbad.std(0)))
    ck("conditionare: standardizarea reduce numarul de conditie",
       cond_std < cond_brut)

    print("\nTOATE VERIFICARILE core AU TRECUT: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _selftest()
        print("PASS")
        sys.exit(0)
    except AssertionError as e:
        print(e)
        print("FAIL")
        sys.exit(1)
