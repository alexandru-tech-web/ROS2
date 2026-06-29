#!/usr/bin/env python3
"""mlp_core.py -- nucleul M20, numpy PUR (scikit-learn si torch INTERZISE).

Un perceptron multistrat (MLP) cu UN strat ascuns, scris de la zero ca sa se vada
fiecare piesa: propagarea inainte (forward), propagarea inapoi a gradientului
(backpropagation, regula lantului) si coborarea pe gradient (fit). Implementarea e
pentru REGRESIE (pierdere patratica medie), cu o ramura optionala de clasificare
binara (sigmoid + entropie incrucisata).

Reteaua (un strat ascuns, H neuroni):
    z1 = X W1 + b1        (X: n x d, W1: d x H, b1: H)
    a1 = activare(z1)     (relu / tanh / sigmoid)
    z2 = a1 W2 + b2       (W2: H x 1, b2: 1)
    y_hat = z2            (regresie)  sau  sigmoid(z2)  (clasificare)

Gradientii (derivati in teorie.md, sectiunile 3 si 5). Pentru pierderea medie
L = (1/n) sum (y_hat - y)^2, cu dz2 = (2/n)(y_hat - y):
    dW2 = a1^T dz2 ;  db2 = sum(dz2)
    dz1 = (dz2 W2^T) * activare'(z1)
    dW1 = X^T dz1  ;  db1 = sum(dz1)
(weight decay lambda adauga 2*lambda*W la dW pentru fiecare matrice de greutati.)

Determinism: initializarea greutatilor trece prin numpy.random.default_rng(seed).
ONESTITATE: testele folosesc functii-tinta SINTETICE (XOR, sin), marcate ca atare.

_selftest() verifica:
  - GRADIENT CHECK: gradientul analitic prin backprop == diferente finite centrate
    pe TOATE matricile (W1, b1, W2, b2), eroare relativa < 1e-4;
  - reteaua invata o functie NELINIARA (XOR ca regresie) cu eroare mica;
  - pierderea SCADE monoton in primii pasi de antrenare;
  - weight decay (lambda > 0) micsoreaza norma greutatilor invatate.

Ruleaza: /home/ubuntu/ros2_ws/.venv_ml/bin/python mlp_core.py   (0 = PASS).
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from utils import rmse  # noqa: E402


# ============================================================ ACTIVARI
def _act(name):
    """Returneaza (f, f') pentru o activare; f' este derivata in functie de z."""
    if name == "relu":
        return (lambda z: np.maximum(0.0, z),
                lambda z: (z > 0.0).astype(float))
    if name == "tanh":
        return (np.tanh,
                lambda z: 1.0 - np.tanh(z) ** 2)
    if name == "sigmoid":
        s = lambda z: 1.0 / (1.0 + np.exp(-z))
        return (s, lambda z: s(z) * (1.0 - s(z)))
    raise ValueError("activare necunoscuta: %r (relu|tanh|sigmoid)" % (name,))


def _sigmoid(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -500.0, 500.0)))


# ============================================================ MLP
class MLP:
    """Perceptron multistrat cu un singur strat ascuns, numpy pur.

    Parametri:
      n_hidden  -- numarul de neuroni ascunsi H;
      activation-- 'relu' | 'tanh' | 'sigmoid' (pe stratul ascuns);
      task      -- 'regression' (MSE, iesire liniara) | 'classification'
                   (sigmoid + entropie incrucisata binara);
      lr        -- rata de invatare (pas de gradient descent);
      l2        -- coeficientul de weight decay (lambda); 0 = fara;
      n_iter    -- numarul de pasi de gradient (batch complet);
      seed      -- samanta initializarii greutatilor.

    Initializare: scalare tip He/Xavier (sqrt(2/fan_in)) ca z1 sa nu satureze.
    """

    def __init__(self, n_hidden=8, activation="tanh", task="regression",
                 lr=0.05, l2=0.0, n_iter=2000, seed=0):
        self.n_hidden = int(n_hidden)
        self.activation = activation
        self.task = task
        self.lr = float(lr)
        self.l2 = float(l2)
        self.n_iter = int(n_iter)
        self.seed = int(seed)
        self.f, self.df = _act(activation)
        self.W1 = self.b1 = self.W2 = self.b2 = None
        self.loss_history_ = []

    # ---------------------------------------------------------- init
    def _init_params(self, d):
        g = np.random.default_rng(self.seed)
        H = self.n_hidden
        self.W1 = g.standard_normal((d, H)) * np.sqrt(2.0 / d)
        self.b1 = np.zeros(H)
        self.W2 = g.standard_normal((H, 1)) * np.sqrt(2.0 / H)
        self.b2 = np.zeros(1)

    # ---------------------------------------------------------- forward
    def _forward(self, X):
        """Propagare inainte. Returneaza (y_hat, cache) cu valorile intermediare."""
        z1 = X @ self.W1 + self.b1          # n x H
        a1 = self.f(z1)                      # n x H
        z2 = a1 @ self.W2 + self.b2          # n x 1
        if self.task == "classification":
            y_hat = _sigmoid(z2)
        else:
            y_hat = z2
        cache = dict(X=X, z1=z1, a1=a1, z2=z2, y_hat=y_hat)
        return y_hat, cache

    # ---------------------------------------------------------- loss
    def _loss(self, y_hat, y):
        """Pierderea medie pe esantion (MSE pentru regresie, BCE pentru clasificare),
        plus termenul de weight decay (1/2 din conventia uzuala -> grad = 2*l2*W)."""
        n = y.shape[0]
        if self.task == "classification":
            p = np.clip(y_hat.reshape(-1), 1e-12, 1.0 - 1e-12)
            data = -np.mean(y * np.log(p) + (1.0 - y) * np.log(1.0 - p))
        else:
            data = np.mean((y_hat.reshape(-1) - y) ** 2)
        reg = self.l2 * (np.sum(self.W1 ** 2) + np.sum(self.W2 ** 2))
        return float(data + reg)

    # ---------------------------------------------------------- backward
    def _backward(self, cache, y):
        """Backpropagation prin regula lantului. Returneaza gradientii
        (dW1, db1, dW2, db2). Vezi derivarea din teorie.md sectiunea 3.

        Pentru REGRESIE cu MSE: dz2 = (2/n)(y_hat - y).
        Pentru CLASIFICARE cu sigmoid+BCE: dz2 = (1/n)(y_hat - y) (forma curata,
        gradientul sigmoidului se anuleaza cu cel al entropiei incrucisate)."""
        X, z1, a1, y_hat = cache["X"], cache["z1"], cache["a1"], cache["y_hat"]
        n = y.shape[0]
        yv = y.reshape(-1, 1)
        if self.task == "classification":
            dz2 = (y_hat - yv) / n                      # n x 1
        else:
            dz2 = 2.0 * (y_hat - yv) / n                # n x 1
        dW2 = a1.T @ dz2 + 2.0 * self.l2 * self.W2      # H x 1
        db2 = np.sum(dz2, axis=0)                        # (1,)
        da1 = dz2 @ self.W2.T                            # n x H
        dz1 = da1 * self.df(z1)                          # n x H
        dW1 = X.T @ dz1 + 2.0 * self.l2 * self.W1       # d x H
        db1 = np.sum(dz1, axis=0)                        # (H,)
        return dW1, db1, dW2, db2

    # ---------------------------------------------------------- fit
    def fit(self, X, y):
        """Antreneaza prin gradient descent pe batch complet. Salveaza
        loss_history_ (pierderea la fiecare pas). Returneaza self."""
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).reshape(-1)
        self._init_params(X.shape[1])
        self.loss_history_ = []
        for _ in range(self.n_iter):
            y_hat, cache = self._forward(X)
            self.loss_history_.append(self._loss(y_hat, y))
            dW1, db1, dW2, db2 = self._backward(cache, y)
            self.W1 -= self.lr * dW1
            self.b1 -= self.lr * db1
            self.W2 -= self.lr * dW2
            self.b2 -= self.lr * db2
        return self

    # ---------------------------------------------------------- predict
    def predict(self, X):
        """Iesirea retelei. Regresie: valoarea reala. Clasificare: eticheta {0,1}
        (prag 0.5). Foloseste predict_proba pentru probabilitati."""
        X = np.asarray(X, dtype=float)
        y_hat, _ = self._forward(X)
        y_hat = y_hat.reshape(-1)
        if self.task == "classification":
            return (y_hat >= 0.5).astype(int)
        return y_hat

    def predict_proba(self, X):
        """Probabilitatea clasei pozitive (doar pentru task='classification')."""
        X = np.asarray(X, dtype=float)
        y_hat, _ = self._forward(X)
        return y_hat.reshape(-1)

    # ---------------------------------------------------------- utilitar
    def weight_norm(self):
        """Norma L2 totala a greutatilor (fara bias) -- pentru a vedea efectul
        weight decay-ului."""
        return float(np.sqrt(np.sum(self.W1 ** 2) + np.sum(self.W2 ** 2)))


# ============================================================ GRADIENT CHECK
def _numerical_grad(model, X, y, param_name, eps=1e-6):
    """Gradientul pierderii fata de un parametru, prin diferente finite CENTRATE:
    g[i] = (L(theta + eps*e_i) - L(theta - eps*e_i)) / (2*eps). Sursa unica de
    adevar pentru a verifica backprop-ul. Restaureaza parametrul la final."""
    P = getattr(model, param_name)
    grad = np.zeros_like(P)
    it = np.nditer(P, flags=["multi_index"])
    while not it.finished:
        ix = it.multi_index
        orig = P[ix]
        P[ix] = orig + eps
        y_hat, _ = model._forward(X)
        loss_plus = model._loss(y_hat, y)
        P[ix] = orig - eps
        y_hat, _ = model._forward(X)
        loss_minus = model._loss(y_hat, y)
        P[ix] = orig
        grad[ix] = (loss_plus - loss_minus) / (2.0 * eps)
        it.iternext()
    return grad


def _rel_error(a, b):
    """Eroare relativa intre doua array-uri de gradient (numitor protejat)."""
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    num = np.linalg.norm(a - b)
    den = np.linalg.norm(a) + np.linalg.norm(b) + 1e-12
    return float(num / den)


# ============================================================ SELFTEST
def _selftest():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    # ---- GRADIENT CHECK: backprop == diferente finite pe TOATE matricile.
    # Pe fiecare activare si pe ambele sarcini, ca sa prindem orice eroare de semn.
    g = np.random.default_rng(0)
    X = g.standard_normal((7, 3))
    for task, ygen in [
        ("regression", lambda: g.standard_normal(7)),
        ("classification", lambda: (g.random(7) < 0.5).astype(float)),
    ]:
        for act in ("tanh", "relu", "sigmoid"):
            y = ygen()
            m = MLP(n_hidden=5, activation=act, task=task, l2=0.01, seed=1)
            m._init_params(X.shape[1])
            y_hat, cache = m._forward(X)
            dW1, db1, dW2, db2 = m._backward(cache, y)
            for name, ana in [("W1", dW1), ("b1", db1), ("W2", dW2), ("b2", db2)]:
                num = _numerical_grad(m, X, y, name).reshape(ana.shape)
                err = _rel_error(ana, num)
                ck("gradcheck %s/%s d%s eroare rel < 1e-4 (=%.2e)"
                   % (task, act, name, err), err < 1e-4)

    # ---- INVATA o functie NELINIARA: XOR ca regresie. Date SINTETICE.
    Xxor = np.array([[0.0, 0.0], [0.0, 1.0], [1.0, 0.0], [1.0, 1.0]])
    yxor = np.array([0.0, 1.0, 1.0, 0.0])
    mxor = MLP(n_hidden=8, activation="tanh", task="regression",
               lr=0.2, n_iter=5000, seed=2).fit(Xxor, yxor)
    err_xor = rmse(yxor, mxor.predict(Xxor))
    ck("MLP invata XOR (regresie) cu RMSE < 0.05 (=%.4f)" % err_xor, err_xor < 0.05)

    # un model liniar NU poate separa XOR -> contrast (justifica neliniaritatea)
    Phi = np.column_stack([np.ones(4), Xxor])
    w_lin, *_ = np.linalg.lstsq(Phi, yxor, rcond=None)
    err_lin = rmse(yxor, Phi @ w_lin)
    ck("contrast: liniarul NU rezolva XOR (RMSE > 0.4, =%.4f)" % err_lin, err_lin > 0.4)

    # ---- INVATA y = sin(x) (regresie neliniara). Date SINTETICE.
    g2 = np.random.default_rng(3)
    Xs = g2.uniform(-3.0, 3.0, size=(120, 1))
    ys = np.sin(Xs[:, 0])
    msin = MLP(n_hidden=16, activation="tanh", lr=0.05, n_iter=4000, seed=4).fit(Xs, ys)
    err_sin = rmse(ys, msin.predict(Xs))
    ck("MLP invata sin(x) cu RMSE < 0.1 (=%.4f)" % err_sin, err_sin < 0.1)

    # ---- PIERDEREA SCADE monoton in primii pasi (semn de optimizare sanatoasa)
    hist = np.array(msin.loss_history_[:50])
    ck("pierderea scade in primii 50 pasi (monoton)",
       np.all(np.diff(hist) <= 1e-9))

    # ---- WEIGHT DECAY micsoreaza norma greutatilor
    base = MLP(n_hidden=16, activation="tanh", lr=0.05, l2=0.0,
               n_iter=2000, seed=5).fit(Xs, ys)
    reg = MLP(n_hidden=16, activation="tanh", lr=0.05, l2=0.05,
              n_iter=2000, seed=5).fit(Xs, ys)
    ck("weight decay micsoreaza norma greutatilor (%.3f < %.3f)"
       % (reg.weight_norm(), base.weight_norm()),
       reg.weight_norm() < base.weight_norm())

    # ---- CLASIFICARE binara: separa doua nori (XOR ca clasificare)
    mcls = MLP(n_hidden=8, activation="tanh", task="classification",
               lr=0.3, n_iter=4000, seed=6).fit(Xxor, yxor)
    ck("MLP clasifica XOR perfect (acuratete 1.0)",
       np.array_equal(mcls.predict(Xxor), yxor.astype(int)))

    print("\nTOATE VERIFICARILE mlp_core AU TRECUT: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _selftest()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
