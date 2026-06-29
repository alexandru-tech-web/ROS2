#!/usr/bin/env python3
"""ensembluri_core.py -- nucleul M13, numpy pur (scikit-learn INTERZIS).

Ensembluri: combina multe modele SLABE intr-unul puternic. Trei piese, toate
construite peste UN SINGUR invatator de baza implementat aici (ciot de decizie /
decision stump) ca modulul sa fie AUTO-SUFICIENT (nu importa din M12 sau alt modul):

  (a) DecisionStump -- ciotul de decizie: cel mai bun prag pe o singura axa.
      Varianta de clasificare (vot majoritar de fiecare parte) si de regresie
      (medie de fiecare parte, pentru reziduuri in boosting).
  (b) BaggingClassifier -- bootstrap (reesantionare cu inlocuire) + agregare prin
      vot majoritar. Reduce VARIANTA mediind modele de mare varianta.
  (c) GradientBoostingClassifier -- ansamblu ADITIV care potriveste cioturi de
      REGRESIE pe REZIDUURI in spatiul log-odds (gradient boosting cu pierdere
      logistica, varianta simpla si corecta). Reduce BIASUL adaugand corectii.

Determinism: orice aleator (bootstrap-ul din bagging) trece prin
numpy.random.default_rng(seed). Metricele (accuracy) vin din utils (SURSA UNICA).

_selftest() verifica:
  - bagging cu 1 estimator (fara bootstrap) == ciotul de baza (identitate);
  - bagging cu mai multe cioturi REDUCE eroarea fata de un singur ciot pe date
    zgomotoase (mediarea taie varianta);
  - gradient boosting SCADE eroarea de antrenare in primii pasi (monoton la inceput);
  - toate predictiile si log-odds-urile sunt FINITE.

Ruleaza: /home/ubuntu/ros2_ws/.venv_ml/bin/python ensembluri_core.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from utils import accuracy  # noqa: E402


# ============================================================ CIOT DE DECIZIE
class DecisionStump:
    """Ciot de decizie: un arbore de adancime 1. Alege o axa j si un prag t care
    minimizeaza impuritatea (clasificare) sau eroarea patratica (regresie), apoi
    prezice o valoare constanta de fiecare parte a pragului.

    task='clf' -> frunzele intorc vot majoritar (eticheta {0,1});
    task='reg' -> frunzele intorc media tintei (folosit pe reziduuri in boosting).
    """

    def __init__(self, task="clf", n_thresholds=32):
        if task not in ("clf", "reg"):
            raise ValueError("task trebuie 'clf' sau 'reg', primit %r" % (task,))
        self.task = task
        self.n_thresholds = int(n_thresholds)
        self.feature = None
        self.threshold = None
        self.left_value = None   # valoarea prezisa pentru x[feature] <= threshold
        self.right_value = None  # valoarea prezisa pentru x[feature]  > threshold

    # ------------------------------------------------- criterii
    @staticmethod
    def _gini(y):
        """Impuritate Gini a unui set de etichete {0,1}: 1 - sum p_c^2."""
        if y.size == 0:
            return 0.0
        p1 = float(np.mean(y))
        p0 = 1.0 - p1
        return 1.0 - (p0 * p0 + p1 * p1)

    def _candidate_thresholds(self, col):
        """Praguri candidate pe o coloana: cuantile (rapid si stabil la N mare)."""
        uniq = np.unique(col)
        if uniq.size <= self.n_thresholds:
            mids = uniq
        else:
            qs = np.linspace(0.0, 1.0, self.n_thresholds)
            mids = np.unique(np.quantile(uniq, qs))
        # mijloacele dintre valori consecutive -> praguri care chiar separa
        if mids.size >= 2:
            return (mids[:-1] + mids[1:]) / 2.0
        return mids

    # ------------------------------------------------- antrenare
    def fit(self, X, y, sample_weight=None):
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).reshape(-1)
        n, d = X.shape
        if sample_weight is None:
            w = np.ones(n)
        else:
            w = np.asarray(sample_weight, dtype=float).reshape(-1)

        best_cost = np.inf
        best = None
        for j in range(d):
            col = X[:, j]
            for t in self._candidate_thresholds(col):
                left = col <= t
                right = ~left
                if not left.any() or not right.any():
                    continue
                cost = self._split_cost(y, w, left, right)
                if cost < best_cost:
                    best_cost = cost
                    best = (j, float(t), self._leaf(y, w, left), self._leaf(y, w, right))

        if best is None:  # o singura valoare pe toate axele -> ciot constant
            self.feature = 0
            self.threshold = float(X[:, 0].max())
            const = self._leaf(y, w, np.ones(n, dtype=bool))
            self.left_value = const
            self.right_value = const
            return self

        self.feature, self.threshold, self.left_value, self.right_value = best
        return self

    def _split_cost(self, y, w, left, right):
        if self.task == "clf":
            wl, wr = w[left].sum(), w[right].sum()
            tot = wl + wr
            return (wl * self._gini(y[left].astype(int)) +
                    wr * self._gini(y[right].astype(int))) / tot
        # regresie: suma erorilor patratice fata de media fiecarei parti
        return self._sse(y[left], w[left]) + self._sse(y[right], w[right])

    @staticmethod
    def _sse(y, w):
        if y.size == 0:
            return 0.0
        mu = np.average(y, weights=w)
        return float(np.sum(w * (y - mu) ** 2))

    def _leaf(self, y, w, mask):
        ys, ws = y[mask], w[mask]
        if self.task == "clf":
            # vot majoritar ponderat -> eticheta {0,1}
            p1 = np.sum(ws * (ys == 1)) / max(ws.sum(), 1e-12)
            return 1.0 if p1 >= 0.5 else 0.0
        return float(np.average(ys, weights=ws))  # regresie: media ponderata

    # ------------------------------------------------- predictie
    def predict(self, X):
        X = np.asarray(X, dtype=float)
        go_left = X[:, self.feature] <= self.threshold
        out = np.where(go_left, self.left_value, self.right_value)
        return out.astype(float)


# ============================================================ BAGGING
class BaggingClassifier:
    """Bagging (bootstrap aggregating): antreneaza n_estimators cioturi, fiecare pe
    un esantion bootstrap (reesantionare cu inlocuire) al setului de antrenare, apoi
    agrega prin VOT MAJORITAR. Mediarea modelelor de varianta mare reduce varianta
    ansamblului fara sa creasca biasul (vezi derivarea din teorie.md).

    Cu n_estimators=1 si bootstrap=False, ansamblul == ciotul de baza (identitate).
    """

    def __init__(self, n_estimators=21, bootstrap=True, seed=0):
        self.n_estimators = int(n_estimators)
        self.bootstrap = bool(bootstrap)
        self.seed = int(seed)
        self.estimators_ = []

    def fit(self, X, y):
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).reshape(-1)
        n = X.shape[0]
        g = np.random.default_rng(self.seed)
        self.estimators_ = []
        for _ in range(self.n_estimators):
            if self.bootstrap:
                idx = g.integers(0, n, size=n)  # cu inlocuire
            else:
                idx = np.arange(n)
            stump = DecisionStump(task="clf").fit(X[idx], y[idx])
            self.estimators_.append(stump)
        return self

    def predict_proba1(self, X):
        """Fractia de cioturi care voteaza clasa 1 (o 'probabilitate' bruta)."""
        X = np.asarray(X, dtype=float)
        votes = np.zeros(X.shape[0])
        for est in self.estimators_:
            votes += est.predict(X)
        return votes / max(len(self.estimators_), 1)

    def predict(self, X):
        return (self.predict_proba1(X) >= 0.5).astype(int)


# ============================================================ GRADIENT BOOSTING
def _sigmoid(z):
    """Sigmoida numeric stabila: 1/(1+e^-z), fara overflow pe |z| mare."""
    z = np.asarray(z, dtype=float)
    out = np.empty_like(z, dtype=float)
    pos = z >= 0
    out[pos] = 1.0 / (1.0 + np.exp(-z[pos]))
    ez = np.exp(z[~pos])
    out[~pos] = ez / (1.0 + ez)
    return out


def _log_loss(y, p, eps=1e-12):
    """Pierdere logistica (cross-entropy) medie -- obiectivul minimizat de boosting."""
    y = np.asarray(y, dtype=float)
    p = np.clip(np.asarray(p, dtype=float), eps, 1.0 - eps)
    return float(-np.mean(y * np.log(p) + (1.0 - y) * np.log(1.0 - p)))


class GradientBoostingClassifier:
    """Gradient boosting pentru clasificare binara cu pierdere logistica.

    Model aditiv in spatiul LOG-ODDS: F(x) = F0 + lr * sum_m h_m(x). La fiecare pas,
    gradientul negativ al pierderii logistice fata de F este REZIDUUL r = y - p, unde
    p = sigmoid(F). Potrivim un ciot de REGRESIE pe reziduuri si il adaugam cu rata de
    invatare lr. Asa scade biasul pas cu pas (vezi exemplul numeric din teorie.md).

    Atentie: prea multi pasi -> supra-invatare (capcana clasica a boosting-ului).
    """

    def __init__(self, n_estimators=50, learning_rate=0.3):
        self.n_estimators = int(n_estimators)
        self.learning_rate = float(learning_rate)
        self.f0_ = 0.0          # log-odds initial (constanta optima)
        self.estimators_ = []   # cioturi de regresie pe reziduuri

    @staticmethod
    def _init_log_odds(y):
        """Log-odds-ul prior optim: log(p / (1-p)) cu p = media etichetelor."""
        p = float(np.clip(np.mean(y), 1e-6, 1 - 1e-6))
        return float(np.log(p / (1.0 - p)))

    def fit(self, X, y):
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).reshape(-1)
        self.f0_ = self._init_log_odds(y)
        F = np.full(y.shape, self.f0_, dtype=float)
        self.estimators_ = []
        for _ in range(self.n_estimators):
            p = _sigmoid(F)
            residual = y - p                 # gradient negativ al pierderii logistice
            h = DecisionStump(task="reg").fit(X, residual)
            F = F + self.learning_rate * h.predict(X)
            self.estimators_.append(h)
        return self

    def decision_function(self, X):
        """Log-odds-ul F(x) acumulat de ansamblu."""
        X = np.asarray(X, dtype=float)
        F = np.full(X.shape[0], self.f0_, dtype=float)
        for h in self.estimators_:
            F = F + self.learning_rate * h.predict(X)
        return F

    def staged_decision_function(self, X):
        """F(x) dupa fiecare pas (pentru curba de eroare vs numarul de pasi)."""
        X = np.asarray(X, dtype=float)
        F = np.full(X.shape[0], self.f0_, dtype=float)
        out = []
        for h in self.estimators_:
            F = F + self.learning_rate * h.predict(X)
            out.append(F.copy())
        return out

    def predict_proba1(self, X):
        return _sigmoid(self.decision_function(X))

    def predict(self, X):
        return (self.predict_proba1(X) >= 0.5).astype(int)


# ============================================================ SELFTEST
def _toy_noisy(n=240, seed=0):
    """Date de clasificare zgomotoase: 2 feature-uri, granita ~ x0 + x1 > 0, cu
    etichete intoarse aleator (zgomot) ca un singur ciot sa fie instabil."""
    g = np.random.default_rng(seed)
    X = g.uniform(-1.0, 1.0, size=(n, 2))
    logit = 3.0 * (X[:, 0] + X[:, 1])
    p = 1.0 / (1.0 + np.exp(-logit))
    y = (g.random(n) < p).astype(int)
    flip = g.random(n) < 0.12               # 12% etichete intoarse
    y = np.where(flip, 1 - y, y)
    return X, y


def _selftest():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    # ---- ciotul de baza: split corect pe un caz separabil pe o axa
    Xs = np.array([[0.0, 9.0], [1.0, 9.0], [2.0, 9.0], [3.0, 9.0]])
    ys = np.array([0, 0, 1, 1])
    st = DecisionStump(task="clf").fit(Xs, ys)
    ck("stump: alege axa informativa (feature 0)", st.feature == 0)
    ck("stump: prag separa clasele (in (1,2))", 1.0 < st.threshold < 2.0)
    ck("stump: prezice perfect cazul separabil",
       np.array_equal(st.predict(Xs).astype(int), ys))

    # ---- bagging cu 1 estimator FARA bootstrap == ciotul de baza (identitate)
    Xn, yn = _toy_noisy(n=200, seed=1)
    base = DecisionStump(task="clf").fit(Xn, yn)
    bag1 = BaggingClassifier(n_estimators=1, bootstrap=False, seed=0).fit(Xn, yn)
    ck("bagging(1, fara bootstrap) == ciotul de baza",
       np.array_equal(bag1.predict(Xn), base.predict(Xn).astype(int)))

    # ---- bagging REDUCE eroarea fata de un singur ciot pe date zgomotoase (pe test)
    Xtr, ytr = _toy_noisy(n=400, seed=2)
    Xte, yte = _toy_noisy(n=400, seed=99)
    err_stump = []
    err_bag = []
    for s in range(8):  # medie pe mai multe seminte: stabil, fara noroc
        stp = DecisionStump(task="clf").fit(*_toy_noisy(n=400, seed=100 + s))
        bag = BaggingClassifier(n_estimators=41, bootstrap=True, seed=s).fit(
            *_toy_noisy(n=400, seed=100 + s))
        err_stump.append(1.0 - accuracy(yte, stp.predict(Xte).astype(int)))
        err_bag.append(1.0 - accuracy(yte, bag.predict(Xte)))
    ck("bagging reduce eroarea medie de test fata de un singur ciot",
       np.mean(err_bag) <= np.mean(err_stump) + 1e-9)
    # bias-ul comparat onest: pe ACELASI set, bagging nu e mai rau decat ciotul
    bag_one = BaggingClassifier(n_estimators=41, seed=0).fit(Xtr, ytr)
    one = DecisionStump(task="clf").fit(Xtr, ytr)
    ck("bagging nu e mai rau decat ciotul pe acelasi set de train",
       accuracy(yte, bag_one.predict(Xte)) >=
       accuracy(yte, one.predict(Xte).astype(int)) - 0.05)

    # ---- gradient boosting: pierderea de antrenare scade in primii pasi (monoton)
    # Boosting minimizeaza pierderea LOGISTICA: aceasta scade strict pas cu pas la
    # inceput. Eroarea 0/1 (neteda doar pe portiuni) o urmeaza, dar mai zgomotos --
    # verificam pierderea pentru proprietatea monotona, eroarea 0/1 per total.
    gb = GradientBoostingClassifier(n_estimators=30, learning_rate=0.3).fit(Xtr, ytr)
    train_loss = []
    train_err = []
    for F in gb.staged_decision_function(Xtr):
        p = _sigmoid(F)
        train_loss.append(_log_loss(ytr, p))
        train_err.append(1.0 - accuracy(ytr, (p >= 0.5).astype(int)))
    first = np.array(train_loss[:6])
    ck("boosting: pierderea de antrenare scade monoton in primii 5 pasi",
       bool(np.all(np.diff(first) <= 1e-9)))
    ck("boosting: pierderea finala de train < pierderea la pasul 1",
       train_loss[-1] <= train_loss[0] + 1e-9)
    ck("boosting: eroarea 0/1 finala de train <= eroarea la pasul 1",
       train_err[-1] <= train_err[0] + 1e-9)
    ck("boosting: pe train e cel putin la fel de bun ca un ciot",
       accuracy(ytr, gb.predict(Xtr)) >= accuracy(ytr, one.predict(Xtr).astype(int)) - 1e-9)

    # ---- toate iesirile sunt FINITE
    ck("boosting: log-odds finit", np.all(np.isfinite(gb.decision_function(Xte))))
    ck("boosting: probabilitati finite in [0,1]",
       np.all(np.isfinite(gb.predict_proba1(Xte))) and
       np.all((gb.predict_proba1(Xte) >= 0) & (gb.predict_proba1(Xte) <= 1)))
    ck("bagging: probabilitati finite", np.all(np.isfinite(bag_one.predict_proba1(Xte))))

    print("\nTOATE VERIFICARILE ensembluri_core AU TRECUT: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _selftest()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
