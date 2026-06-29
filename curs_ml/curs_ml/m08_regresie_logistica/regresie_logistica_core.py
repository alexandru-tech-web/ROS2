#!/usr/bin/env python3
"""regresie_logistica_core.py -- nucleul M08, numpy pur (scikit-learn INTERZIS).

Regresie logistica binara antrenata prin COBORARE PE GRADIENT de la zero:
  - sigmoid stabil numeric (fara overflow la argumente mari negative/pozitive);
  - pierdere de entropie incrucisata (log-loss) mediata pe esantion;
  - gradient analitic g = (1/n) X^T (p - y), unde p = sigmoid(X w);
  - fit(X, y) adauga interceptul (bias) intern, deci X NU trebuie sa contina o
    coloana de 1; predict_proba(X) si predict(X, prag).

Notatii (consecvente cu M02/M03/M05): w include interceptul pe pozitia 0 dupa ce
add_bias adauga coloana de 1; p = probabilitatea prezisa pentru clasa 1.

Determinism: initializarea si orice amestecare trec prin numpy.random.default_rng(seed).

_selftest() verifica CORECTITUDINEA, nu doar ca ruleaza:
  - gradientul analitic == diferente finite (eroare maxima < 1e-5);
  - pe date liniar separabile converge la acuratete > 0.95;
  - predict_proba ramane in [0, 1];
  - pierderea (log-loss) scade monoton de-a lungul iteratiilor.

Ruleaza: /home/ubuntu/ros2_ws/.venv_ml/bin/python regresie_logistica_core.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from utils import add_bias, accuracy  # noqa: E402


# ============================================================ PRIMITIVE
def sigmoid(z):
    """Sigmoida logistica 1/(1+exp(-z)), stabila numeric.

    Evita overflow-ul lui exp pentru z foarte negativ (sau pozitiv) calculand pe
    cele doua ramuri: pentru z>=0 forma directa, pentru z<0 forma echivalenta
    exp(z)/(1+exp(z)). Rezultat in (0, 1)."""
    z = np.asarray(z, dtype=float)
    out = np.empty_like(z)
    pos = z >= 0
    out[pos] = 1.0 / (1.0 + np.exp(-z[pos]))
    ez = np.exp(z[~pos])
    out[~pos] = ez / (1.0 + ez)
    return out


def cross_entropy_loss(y, p, eps=1e-12):
    """Entropie incrucisata binara (log-loss) mediata pe esantion.

    L = -(1/n) sum [ y*log(p) + (1-y)*log(1-p) ]. p e tuns in [eps, 1-eps] ca
    log-ul sa nu explodeze cand probabilitatea atinge 0 sau 1."""
    y = np.asarray(y, dtype=float).reshape(-1)
    p = np.clip(np.asarray(p, dtype=float).reshape(-1), eps, 1.0 - eps)
    return float(-np.mean(y * np.log(p) + (1.0 - y) * np.log(1.0 - p)))


def _grad(Phi, y, w):
    """Gradientul analitic al log-loss-ului fata de w: (1/n) Phi^T (sigmoid(Phi w) - y).

    Phi e deja cu coloana de bias; y in {0, 1}. Returneaza un vector de marimea lui w."""
    p = sigmoid(Phi @ w)
    return (Phi.T @ (p - y)) / Phi.shape[0]


# ============================================================ MODEL
class LogisticRegressionGD:
    """Regresie logistica binara prin coborare pe gradient (de la zero, numpy pur).

    Parametri:
      lr        -- pasul de invatare (rata de coborare);
      n_iter    -- numarul de iteratii de gradient (epoci full-batch);
      seed      -- samanta pentru initializarea greutatilor (mici, aproape 0).

    Atribute dupa fit:
      w_        -- vectorul de greutati cu interceptul pe pozitia 0;
      loss_     -- istoricul log-loss-ului per iteratie (pentru diagnoza convergentei).
    """

    def __init__(self, lr=0.1, n_iter=2000, seed=0):
        self.lr = float(lr)
        self.n_iter = int(n_iter)
        self.seed = int(seed)
        self.w_ = None
        self.loss_ = None

    def fit(self, X, y):
        """Antreneaza pe (X, y). Adauga interceptul intern; X fara coloana de 1.
        y in {0, 1}. Returneaza self (interfata stil fluent)."""
        Phi = add_bias(X)
        y = np.asarray(y, dtype=float).reshape(-1)
        rng = np.random.default_rng(self.seed)
        w = 0.01 * rng.standard_normal(Phi.shape[1])
        loss = np.empty(self.n_iter)
        for t in range(self.n_iter):
            p = sigmoid(Phi @ w)
            loss[t] = cross_entropy_loss(y, p)
            w = w - self.lr * (Phi.T @ (p - y)) / Phi.shape[0]
        self.w_ = w
        self.loss_ = loss
        return self

    def decision_function(self, X):
        """Scorul liniar X w (logit-ul), inainte de sigmoid."""
        return add_bias(X) @ self.w_

    def predict_proba(self, X):
        """Probabilitatea prezisa pentru clasa 1, in [0, 1]."""
        return sigmoid(self.decision_function(X))

    def predict(self, X, threshold=0.5):
        """Eticheta {0, 1} prin pragul aplicat pe probabilitate (implicit 0.5)."""
        return (self.predict_proba(X) >= threshold).astype(int)


# ============================================================ SELFTEST
def _make_separable(n=200, seed=0):
    """Doua nori gaussieni bine separati in 2D -> liniar separabili."""
    rng = np.random.default_rng(seed)
    n0 = n // 2
    X0 = rng.normal([-2.0, -2.0], 0.6, size=(n0, 2))
    X1 = rng.normal([2.0, 2.0], 0.6, size=(n - n0, 2))
    X = np.vstack([X0, X1])
    y = np.concatenate([np.zeros(n0), np.ones(n - n0)])
    return X, y


def _selftest():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    # --- sigmoid: valori cunoscute si stabilitate la argumente extreme
    ck("sigmoid(0) = 0.5", abs(float(sigmoid(0.0)) - 0.5) < 1e-12)
    ck("sigmoid stabil la argumente mari (fara nan/inf)",
       np.all(np.isfinite(sigmoid(np.array([-1000.0, 1000.0])))))
    ck("sigmoid monoton si in (0,1)",
       0.0 < float(sigmoid(-5.0)) < float(sigmoid(5.0)) < 1.0)

    # --- gradient analitic == diferente finite (eroare < 1e-5)
    rng = np.random.default_rng(3)
    Phi = add_bias(rng.standard_normal((40, 3)))
    y = (rng.random(40) < 0.5).astype(float)
    w = rng.standard_normal(Phi.shape[1])
    g_analytic = _grad(Phi, y, w)
    g_numeric = np.zeros_like(w)
    h = 1e-6
    for j in range(w.size):
        wp = w.copy(); wp[j] += h
        wm = w.copy(); wm[j] -= h
        lp = cross_entropy_loss(y, sigmoid(Phi @ wp))
        lm = cross_entropy_loss(y, sigmoid(Phi @ wm))
        g_numeric[j] = (lp - lm) / (2 * h)
    err = float(np.max(np.abs(g_analytic - g_numeric)))
    ck("gradient analitic == diferente finite (err %.2e < 1e-5)" % err, err < 1e-5)

    # --- converge pe date liniar separabile: acuratete > 0.95
    X, ys = _make_separable(n=200, seed=1)
    model = LogisticRegressionGD(lr=0.3, n_iter=3000, seed=0).fit(X, ys)
    acc = accuracy(ys, model.predict(X))
    ck("converge pe date separabile (acc %.3f > 0.95)" % acc, acc > 0.95)

    # --- predict_proba in [0, 1]
    proba = model.predict_proba(X)
    ck("predict_proba in [0, 1]", float(proba.min()) >= 0.0 and float(proba.max()) <= 1.0)

    # --- pierderea scade monoton de-a lungul iteratiilor
    diffs = np.diff(model.loss_)
    ck("log-loss scade monoton pe iteratii", np.all(diffs <= 1e-12))
    ck("log-loss finala < log-loss initiala", model.loss_[-1] < model.loss_[0])

    print("\nTOATE VERIFICARILE regresie_logistica_core AU TRECUT: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _selftest()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
