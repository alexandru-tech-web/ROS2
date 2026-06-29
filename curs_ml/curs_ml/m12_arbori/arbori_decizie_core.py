#!/usr/bin/env python3
"""arbori_decizie_core.py -- nucleul M12, numpy pur (scikit-learn INTERZIS).

Arbore de decizie CART de la zero pentru CLASIFICARE binara (etichete in {0, 1}).
Crestere recursiva greedy: la fiecare nod se cauta perechea (feature, prag) care
maximizeaza REDUCEREA de impuritate (Gini sau entropie); creste pana la max_depth
sau pana sub min_samples_split, apoi devine frunza cu eticheta majoritara.

Impuritate (vezi teorie.md):
  - Gini(y)    = 1 - sum_c p_c^2          (0 = nod pur, 0.5 = 50/50 binar)
  - Entropy(y) = -sum_c p_c log2 p_c       (0 = pur, 1 bit = 50/50 binar)
Reducere de impuritate a unui split:
  Delta = I(parinte) - (n_st/n) I(stanga) - (n_dr/n) I(dreapta)

Determinism: pragurile candidate vin din valorile observate (fara aleator).
Importanta feature-urilor = reducerea de impuritate ponderata, acumulata pe noduri.

_selftest() verifica:
  - gini/entropie pe distributii cunoscute (nod pur -> 0; 50/50 -> Gini 0.5,
    entropie 1 bit);
  - best_split alege feature-ul corect pe date separabile pe o axa;
  - arborele clasifica PERFECT date simplu separabile;
  - max_depth e respectat;
  - pe zgomot pur, adancimea 1 (cioturi) NU supra-invata (acuratete de train modesta).

Ruleaza: /home/ubuntu/ros2_ws/.venv_ml/bin/python arbori_decizie_core.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from utils import accuracy  # noqa: E402


# ============================================================ IMPURITATE
def _class_probs(y):
    """Fractiile claselor din y (etichete intregi >= 0). Returneaza un array de p_c."""
    y = np.asarray(y).astype(int)
    if y.size == 0:
        return np.array([])
    counts = np.bincount(y)
    return counts[counts > 0] / y.size


def gini(y):
    """Impuritate Gini = 1 - sum_c p_c^2. Nod pur -> 0; binar 50/50 -> 0.5."""
    p = _class_probs(y)
    if p.size == 0:
        return 0.0
    return float(1.0 - np.sum(p ** 2))


def entropy(y):
    """Entropie Shannon in BITI = -sum_c p_c log2 p_c. Pur -> 0; 50/50 -> 1 bit."""
    p = _class_probs(y)
    if p.size == 0:
        return 0.0
    return float(-np.sum(p * np.log2(p)))


_IMPURITY = {"gini": gini, "entropy": entropy}


# ============================================================ SPLIT
def _impurity_reduction(y, mask, impurity):
    """Reducerea de impuritate a unui split dat de masca booleana (stanga = True)."""
    n = y.size
    n_st = int(np.sum(mask))
    n_dr = n - n_st
    if n_st == 0 or n_dr == 0:
        return 0.0
    parent = impurity(y)
    child = (n_st / n) * impurity(y[mask]) + (n_dr / n) * impurity(y[~mask])
    return parent - child


def best_split(X, y, criterion="gini"):
    """Cauta (feature, prag) care MAXIMIZEAZA reducerea de impuritate.

    Pragurile candidate sunt mijloacele dintre valori consecutive distincte ale
    fiecarui feature (split-uri x <= prag -> stanga). Returneaza un dict cu
    feature, threshold, gain (>= 0). Daca niciun split nu reduce impuritatea,
    feature = None.
    """
    X = np.asarray(X, dtype=float)
    y = np.asarray(y).astype(int)
    impurity = _IMPURITY[criterion]
    best = dict(feature=None, threshold=None, gain=0.0)
    n_features = X.shape[1]
    for j in range(n_features):
        vals = np.unique(X[:, j])
        if vals.size < 2:
            continue
        thresholds = (vals[:-1] + vals[1:]) / 2.0
        for t in thresholds:
            mask = X[:, j] <= t
            gain = _impurity_reduction(y, mask, impurity)
            if gain > best["gain"] + 1e-12:
                best = dict(feature=int(j), threshold=float(t), gain=float(gain))
    return best


# ============================================================ NOD / ARBORE
class _Node:
    """Nod de arbore: fie frunza (label setat), fie intern (feature/threshold + copii)."""
    __slots__ = ("feature", "threshold", "left", "right", "label", "n", "impurity")

    def __init__(self):
        self.feature = None
        self.threshold = None
        self.left = None
        self.right = None
        self.label = None
        self.n = 0
        self.impurity = 0.0

    def is_leaf(self):
        return self.label is not None and self.feature is None


class DecisionTreeCart:
    """Arbore de decizie CART pentru clasificare binara, de la zero in numpy.

    Parametri:
      max_depth         -- adancimea maxima (radacina = adancime 0). None = nelimitat.
      min_samples_split -- nu mai imparte un nod cu mai putine exemple decat atat.
      criterion         -- 'gini' sau 'entropy'.
    """

    def __init__(self, max_depth=None, min_samples_split=2, criterion="gini"):
        if criterion not in _IMPURITY:
            raise ValueError("criterion necunoscut: %r (gini|entropy)" % (criterion,))
        self.max_depth = max_depth
        self.min_samples_split = int(min_samples_split)
        self.criterion = criterion
        self.root = None
        self.n_features_ = None
        self._importances = None

    # ----------------------------------------------------- antrenare
    def fit(self, X, y):
        X = np.asarray(X, dtype=float)
        y = np.asarray(y).astype(int)
        if X.ndim != 2:
            raise ValueError("X trebuie 2D (n, d), primit forma %r" % (X.shape,))
        self.n_features_ = X.shape[1]
        self._importances = np.zeros(self.n_features_)
        self.root = self._grow(X, y, depth=0)
        # normalizeaza importantele (suma 1 daca exista vreun split)
        total = self._importances.sum()
        if total > 0:
            self._importances = self._importances / total
        return self

    def _majority(self, y):
        """Eticheta majoritara; la egalitate, clasa cu indice minim (determinist)."""
        return int(np.argmax(np.bincount(y, minlength=2)))

    def _grow(self, X, y, depth):
        node = _Node()
        node.n = int(y.size)
        node.impurity = _IMPURITY[self.criterion](y)

        pure = node.impurity == 0.0
        too_small = y.size < self.min_samples_split
        too_deep = self.max_depth is not None and depth >= self.max_depth
        if pure or too_small or too_deep:
            node.label = self._majority(y)
            return node

        split = best_split(X, y, self.criterion)
        if split["feature"] is None:
            node.label = self._majority(y)
            return node

        j, t = split["feature"], split["threshold"]
        mask = X[:, j] <= t
        # acumuleaza importanta = reducerea de impuritate * numarul de exemple
        self._importances[j] += split["gain"] * y.size

        node.feature = j
        node.threshold = t
        node.left = self._grow(X[mask], y[mask], depth + 1)
        node.right = self._grow(X[~mask], y[~mask], depth + 1)
        return node

    # ----------------------------------------------------- predictie
    def _predict_one(self, x):
        node = self.root
        while not node.is_leaf():
            if x[node.feature] <= node.threshold:
                node = node.left
            else:
                node = node.right
        return node.label

    def predict(self, X):
        X = np.asarray(X, dtype=float)
        if X.ndim == 1:
            X = X.reshape(1, -1)
        return np.array([self._predict_one(x) for x in X], dtype=int)

    # ----------------------------------------------------- introspectie
    def depth(self):
        """Adancimea efectiva a arborelui (frunza singura -> 0)."""
        def _d(node):
            if node is None or node.is_leaf():
                return 0
            return 1 + max(_d(node.left), _d(node.right))
        return _d(self.root)

    @property
    def feature_importances_(self):
        """Importanta feature-urilor (reducere de impuritate ponderata, suma 1)."""
        return self._importances

    def rules(self, feature_names=None):
        """Lista de reguli interpretabile (cate o linie text per frunza)."""
        names = feature_names
        lines = []

        def _walk(node, conds):
            if node.is_leaf():
                cond = " SI ".join(conds) if conds else "(radacina)"
                lines.append("DACA %s -> clasa %d (n=%d)" % (cond, node.label, node.n))
                return
            fn = names[node.feature] if names is not None else "x[%d]" % node.feature
            _walk(node.left, conds + ["%s <= %.4g" % (fn, node.threshold)])
            _walk(node.right, conds + ["%s > %.4g" % (fn, node.threshold)])

        _walk(self.root, [])
        return lines


# ============================================================ SELFTEST
def _selftest():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    # ----- impuritate pe distributii cunoscute
    pur = np.array([1, 1, 1, 1])
    half = np.array([0, 0, 1, 1])
    ck("gini: nod pur = 0", abs(gini(pur) - 0.0) < 1e-12)
    ck("gini: 50/50 = 0.5", abs(gini(half) - 0.5) < 1e-12)
    ck("entropy: nod pur = 0", abs(entropy(pur) - 0.0) < 1e-12)
    ck("entropy: 50/50 = 1 bit", abs(entropy(half) - 1.0) < 1e-12)
    # exemplul lucrat din teorie.md: y=[0,0,0,1,1,1], split la x<=2.5
    # parinte gini = 0.5; copii puri -> reducere = 0.5
    yex = np.array([0, 0, 0, 1, 1, 1])
    Xex = np.array([[1.0], [2.0], [2.0], [3.0], [4.0], [5.0]])
    sp = best_split(Xex, yex, "gini")
    ck("best_split: exemplu numeric ales pe feature 0", sp["feature"] == 0)
    ck("best_split: prag intre 2 si 3 (= 2.5)", abs(sp["threshold"] - 2.5) < 1e-9)
    ck("best_split: reducere Gini = 0.5 (copii puri)", abs(sp["gain"] - 0.5) < 1e-9)

    # ----- best_split alege feature-ul corect: f0 separabil, f1 zgomot
    rng = np.random.default_rng(0)
    n = 200
    f0 = rng.uniform(-1, 1, n)
    f1 = rng.uniform(-1, 1, n)        # irelevant
    y = (f0 > 0).astype(int)
    X = np.column_stack([f1, f0])     # punem feature-ul bun pe coloana 1
    sp = best_split(X, y, "gini")
    ck("best_split: alege feature-ul separabil (col 1)", sp["feature"] == 1)
    ck("best_split: prag aproape de 0", abs(sp["threshold"]) < 0.05)

    # ----- arborele clasifica PERFECT date simplu separabile prin regiuni
    # axis-aligned (cuadrante L-de-1: clasa 1 doar daca x0 > 0 SI x1 > 0).
    # Greedy CART rezolva asta in 2 split-uri; ambele feature-uri conteaza.
    g = np.random.default_rng(1)
    Xx = g.uniform(-1, 1, size=(300, 2))
    yx = ((Xx[:, 0] > 0) & (Xx[:, 1] > 0)).astype(int)
    tree = DecisionTreeCart(max_depth=3, criterion="gini").fit(Xx, yx)
    acc = accuracy(yx, tree.predict(Xx))
    ck("arbore: clasifica regiuni separabile perfect (acc=1.0)", acc > 0.99)
    ck("arbore: importanta feature-urilor are suma 1",
       abs(tree.feature_importances_.sum() - 1.0) < 1e-9)
    ck("arbore: ambele feature-uri folosite",
       np.all(tree.feature_importances_ > 0))

    # ----- max_depth respectat
    deep = DecisionTreeCart(max_depth=2, criterion="entropy").fit(Xx, yx)
    ck("arbore: max_depth=2 respectat", deep.depth() <= 2)
    shallow = DecisionTreeCart(max_depth=1).fit(Xx, yx)
    ck("arbore: max_depth=1 -> ciot (depth <= 1)", shallow.depth() <= 1)

    # ----- pe zgomot PUR, un ciot (depth 1) NU supra-invata
    gn = np.random.default_rng(2)
    Xn = gn.uniform(-1, 1, size=(200, 3))
    yn = gn.integers(0, 2, size=200)   # eticheta independenta de X = zgomot
    stump = DecisionTreeCart(max_depth=1).fit(Xn, yn)
    acc_stump = accuracy(yn, stump.predict(Xn))
    ck("arbore: ciot pe zgomot nu supra-invata (acc < 0.65)", acc_stump < 0.65)
    # iar un arbore adanc memoreaza zgomotul (acc mare) -> ilustreaza supra-invatarea
    big = DecisionTreeCart(max_depth=None, min_samples_split=2).fit(Xn, yn)
    acc_big = accuracy(yn, big.predict(Xn))
    ck("arbore: adanc memoreaza zgomotul (acc > ciot)", acc_big > acc_stump)

    print("\nTOATE VERIFICARILE arbori_decizie_core AU TRECUT: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _selftest()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
