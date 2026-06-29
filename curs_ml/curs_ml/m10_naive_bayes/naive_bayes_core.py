#!/usr/bin/env python3
"""naive_bayes_core.py -- nucleul M10, numpy pur (scikit-learn INTERZIS).

Gaussian Naive Bayes de la zero. Modelul GENERATIV: pentru fiecare clasa c
estimeaza un prior P(y=c) si, sub ipoteza de independenta conditionala, o
gaussiana 1D per feature j cu (medie mu_cj, varianta var_cj). La predictie
foloseste regula MAP in spatiul log:

    log P(y=c | x) = log P(y=c) + sum_j log N(x_j ; mu_cj, var_cj) + const

unde const (log-evidenta) e aceeasi pentru toate clasele, deci nu schimba
argmax-ul. predict = argmax_c log-posterior.

Estimari de antrenare (maxima verosimilitate):
  P(y=c)  = n_c / n
  mu_cj   = media feature-ului j pe exemplele clasei c
  var_cj  = varianta (MLE, ddof=0) a feature-ului j pe clasa c, + var_smoothing

var_smoothing > 0 e o podea de varianta (ca in sklearn): evita impartirea la
zero cand un feature e constant intr-o clasa -> log-densitate finita (fara -inf).

Determinism: nu exista aleator in fit/predict; testele isi seamana datele prin
numpy.random.default_rng(seed).

_selftest() verifica:
  - pe doua gaussiene bine separate clasifica ~ perfect;
  - log-posteriorul corespunde formulei pe un caz mic calculat MANUAL (vezi
    teorie.md sec.5);
  - cand feature-urile NU disting clasele, recupereaza clasa cu prior dominant;
  - predict_log_proba e finit (fara -inf) chiar cu un feature constant.

Ruleaza: /home/ubuntu/ros2_ws/.venv_ml/bin/python naive_bayes_core.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from utils import accuracy  # noqa: E402


class GaussianNaiveBayes:
    """Gaussian Naive Bayes from-scratch (numpy pur).

    Atribute dupa fit:
      classes_  -- etichetele de clasa, sortate
      priors_   -- P(y=c), aliniat cu classes_
      theta_    -- mediile (n_classes, n_features)
      var_      -- variantele (n_classes, n_features), cu podea var_smoothing
    """

    def __init__(self, var_smoothing=1e-9):
        self.var_smoothing = float(var_smoothing)
        self.classes_ = None
        self.priors_ = None
        self.theta_ = None
        self.var_ = None

    # ------------------------------------------------------------ fit
    def fit(self, X, y):
        """Estimeaza prior-uri si (medie, varianta) per clasa per feature."""
        X = np.asarray(X, dtype=float)
        if X.ndim == 1:
            X = X.reshape(-1, 1)
        y = np.asarray(y).reshape(-1)
        self.classes_ = np.unique(y)
        n, n_features = X.shape
        n_classes = self.classes_.size
        # podea de varianta proportionala cu cea mai mare varianta a unui feature
        # (conventia sklearn): stabila numeric, scaleaza cu datele.
        eps = self.var_smoothing * X.var(axis=0).max()
        self.priors_ = np.zeros(n_classes)
        self.theta_ = np.zeros((n_classes, n_features))
        self.var_ = np.zeros((n_classes, n_features))
        for i, c in enumerate(self.classes_):
            Xc = X[y == c]
            self.priors_[i] = Xc.shape[0] / n
            self.theta_[i] = Xc.mean(axis=0)
            self.var_[i] = Xc.var(axis=0) + eps  # MLE (ddof=0) + podea
        return self

    # ------------------------------------------------------------ scor MAP
    def predict_log_proba(self, X):
        """log-posterior NENORMALIZAT per clasa: log P(y=c) + sum_j log N(x_j).

        Returneaza un array (n_samples, n_classes). NU scade log-evidenta (ar fi
        aceeasi pe rand), deci nu sunt log-probabilitati normalizate -- dar
        argmax-ul si joint_log_likelihood sunt corecte. Vezi predict_proba pentru
        normalizare."""
        X = np.asarray(X, dtype=float)
        if X.ndim == 1:
            X = X.reshape(-1, 1)
        n = X.shape[0]
        out = np.zeros((n, self.classes_.size))
        for i in range(self.classes_.size):
            mu = self.theta_[i]
            var = self.var_[i]
            # log N(x_j; mu, var) = -0.5*log(2*pi*var) - (x-mu)^2/(2*var), sumat pe j
            log_dens = -0.5 * np.log(2.0 * np.pi * var) - (X - mu) ** 2 / (2.0 * var)
            out[:, i] = np.log(self.priors_[i]) + log_dens.sum(axis=1)
        return out

    def predict_proba(self, X):
        """Posterior NORMALIZAT P(y=c | x) prin softmax stabil pe log-posterior."""
        jll = self.predict_log_proba(X)
        m = jll.max(axis=1, keepdims=True)
        e = np.exp(jll - m)
        return e / e.sum(axis=1, keepdims=True)

    def predict(self, X):
        """Eticheta MAP = argmax_c log-posterior."""
        idx = np.argmax(self.predict_log_proba(X), axis=1)
        return self.classes_[idx]


# ============================================================ SELFTEST
def _selftest():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    # 1) doua gaussiene bine separate -> clasificare ~ perfecta
    rng = np.random.default_rng(0)
    X0 = rng.normal([0.0, 0.0], 1.0, size=(200, 2))
    X1 = rng.normal([6.0, 6.0], 1.0, size=(200, 2))
    X = np.vstack([X0, X1])
    y = np.r_[np.zeros(200), np.ones(200)].astype(int)
    clf = GaussianNaiveBayes().fit(X, y)
    acc = accuracy(y, clf.predict(X))
    ck("doua gaussiene bine separate: acuratete >= 0.99", acc >= 0.99)

    # 2) log-posterior == formula, pe cazul mic CALCULAT MANUAL (vezi teorie.md sec.5)
    # clasa 0: x=[1,2,3] -> mu=2, var(MLE)=2/3 ; clasa 1: x=[5,6,7] -> mu=6, var=2/3
    Xs = np.array([[1.0], [2.0], [3.0], [5.0], [6.0], [7.0]])
    ys = np.array([0, 0, 0, 1, 1, 1])
    m = GaussianNaiveBayes(var_smoothing=0.0).fit(Xs, ys)
    ck("estimari: mu0=2, mu1=6", np.allclose(m.theta_.ravel(), [2.0, 6.0]))
    ck("estimari: var0=var1=2/3", np.allclose(m.var_.ravel(), [2.0 / 3.0, 2.0 / 3.0]))
    ck("estimari: prior-uri 0.5/0.5", np.allclose(m.priors_, [0.5, 0.5]))
    # log-posterior pentru x=3, calculat de mana
    v = 2.0 / 3.0
    lp0_man = np.log(0.5) - 0.5 * np.log(2 * np.pi * v) - (3 - 2.0) ** 2 / (2 * v)
    lp1_man = np.log(0.5) - 0.5 * np.log(2 * np.pi * v) - (3 - 6.0) ** 2 / (2 * v)
    jll = m.predict_log_proba(np.array([[3.0]]))[0]
    ck("log-posterior x=3 == formula manuala",
       np.isclose(jll[0], lp0_man) and np.isclose(jll[1], lp1_man))
    ck("x=3 clasificat ca 0 (mai aproape de mu0)", m.predict(np.array([[3.0]]))[0] == 0)
    # la mijloc (x=4) log-posteriorii sunt egali (clase simetrice, prior egal)
    jmid = m.predict_log_proba(np.array([[4.0]]))[0]
    ck("x=4 (mijloc): log-posteriori egali", np.isclose(jmid[0], jmid[1]))

    # 3) feature-uri care NU disting -> recupereaza clasa cu prior dominant
    # ambele clase trag din aceeasi distributie; clasa 0 are 90%, clasa 1 are 10%
    Xa = rng.normal(0.0, 1.0, size=(90, 1))
    Xb = rng.normal(0.0, 1.0, size=(10, 1))
    Xp = np.vstack([Xa, Xb])
    yp = np.r_[np.zeros(90), np.ones(10)].astype(int)
    mp = GaussianNaiveBayes().fit(Xp, yp)
    pred = mp.predict(np.array([[0.0], [0.5], [-0.5]]))
    ck("prior dominant: prezice clasa majoritara (0) cand feature nu distinge",
       np.all(pred == 0))

    # 4) predict_log_proba e FINIT chiar cu un feature constant intr-o clasa
    Xc = np.array([[1.0, 5.0], [1.0, 5.0], [1.0, 5.0], [2.0, 9.0], [3.0, 9.0]])
    yc = np.array([0, 0, 0, 1, 1])  # feature 0 constant in clasa 0
    mc = GaussianNaiveBayes().fit(Xc, yc)
    jc = mc.predict_log_proba(Xc)
    ck("log-posterior finit cu feature constant (fara -inf/nan)", np.all(np.isfinite(jc)))
    # predict_proba normalizat: randuri care insumeaza 1
    pp = mc.predict_proba(Xc)
    ck("predict_proba normalizat (randuri insumeaza 1)",
       np.allclose(pp.sum(axis=1), 1.0))

    print("\nTOATE VERIFICARILE naive_bayes_core AU TRECUT: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _selftest()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
