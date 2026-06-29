#!/usr/bin/env python3
"""utils.py -- infrastructura partajata a cursului curs_ml (DRY).

Aici stau functiile comune folosite de toate modulele: seeding determinist,
impartirea train/test, standardizarea (z-score cu statistici de pe TRAIN ca sa
nu existe scurgere de date), metrici de regresie si clasificare, si un ajutor de
salvare a figurilor care nu da crash daca matplotlib lipseste.

Reguli respectate (vezi PRINCIPII_TRANSVERSALE.md):
- determinism: orice aleator trece printr-un numpy.random.Generator semanat;
- fara scurgere: standardize() invata media/abaterea pe TRAIN si le aplica pe TEST;
- pur: doar numpy aici (scikit-learn este interzis in nucleele de curs).

Ruleaza verificarile: python3 utils.py   (iesire 0 = PASS, non-0 = FAIL).
"""
import sys

import numpy as np


# ---------------------------------------------------------------- seeding
def rng(seed=0):
    """Generator aleator determinist. O singura sursa de aleator in tot cursul."""
    return np.random.default_rng(seed)


# ---------------------------------------------------------------- split
def train_test_split(X, y, test_frac=0.25, seed=0):
    """Imparte (X, y) determinist in train/test prin permutare semanata.

    Returneaza X_tr, X_te, y_tr, y_te. test_frac in (0, 1). Pastreaza randurile
    aliniate intre X si y. NU stratifica (vezi nota din M07/M09 pentru clase rare)."""
    X = np.asarray(X, dtype=float)
    y = np.asarray(y)
    n = X.shape[0]
    if not 0.0 < test_frac < 1.0:
        raise ValueError("test_frac trebuie in (0, 1), primit %r" % (test_frac,))
    idx = rng(seed).permutation(n)
    n_te = max(1, int(round(n * test_frac)))
    te, tr = idx[:n_te], idx[n_te:]
    return X[tr], X[te], y[tr], y[te]


# ---------------------------------------------------------------- standardizare
def standardize(X_train, X_test=None, eps=1e-12):
    """Z-score pe coloane folosind media/abaterea de pe TRAIN (fara scurgere).

    Returneaza (X_train_std, X_test_std, mean, std). Daca X_test e None, al doilea
    element e None. Coloanele cu abatere ~0 sunt impartite la eps -> raman ~0."""
    X_train = np.asarray(X_train, dtype=float)
    mean = X_train.mean(axis=0)
    std = X_train.std(axis=0)
    std_safe = np.where(std < eps, eps, std)
    Xtr = (X_train - mean) / std_safe
    Xte = None if X_test is None else (np.asarray(X_test, dtype=float) - mean) / std_safe
    return Xtr, Xte, mean, std


def add_bias(X):
    """Adauga o coloana de 1 (interceptul) la stanga lui X."""
    X = np.asarray(X, dtype=float)
    return np.column_stack([np.ones(X.shape[0]), X])


# ---------------------------------------------------------------- metrici regresie
def mse(y_true, y_pred):
    y_true, y_pred = np.asarray(y_true, dtype=float), np.asarray(y_pred, dtype=float)
    return float(np.mean((y_true - y_pred) ** 2))


def rmse(y_true, y_pred):
    return float(np.sqrt(mse(y_true, y_pred)))


def mae(y_true, y_pred):
    y_true, y_pred = np.asarray(y_true, dtype=float), np.asarray(y_pred, dtype=float)
    return float(np.mean(np.abs(y_true - y_pred)))


def r2_score(y_true, y_pred):
    """Coeficient de determinare R^2 = 1 - SS_res / SS_tot. 1 = potrivire perfecta."""
    y_true, y_pred = np.asarray(y_true, dtype=float), np.asarray(y_pred, dtype=float)
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    if ss_tot < 1e-15:
        return 0.0
    return float(1.0 - ss_res / ss_tot)


# ---------------------------------------------------------------- metrici clasificare
def accuracy(y_true, y_pred):
    y_true, y_pred = np.asarray(y_true), np.asarray(y_pred)
    return float(np.mean(y_true == y_pred))


def confusion_matrix(y_true, y_pred):
    """Matrice de confuzie binara [[TN, FP], [FN, TP]] pentru etichete in {0, 1}."""
    y_true, y_pred = np.asarray(y_true).astype(int), np.asarray(y_pred).astype(int)
    tn = int(np.sum((y_true == 0) & (y_pred == 0)))
    fp = int(np.sum((y_true == 0) & (y_pred == 1)))
    fn = int(np.sum((y_true == 1) & (y_pred == 0)))
    tp = int(np.sum((y_true == 1) & (y_pred == 1)))
    return np.array([[tn, fp], [fn, tp]])


def precision_recall_f1(y_true, y_pred):
    """Precizie, recall si F1 pentru clasa pozitiva (1). Numitor 0 -> 0.0."""
    cm = confusion_matrix(y_true, y_pred)
    tp, fp, fn = cm[1, 1], cm[0, 1], cm[1, 0]
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
    return float(prec), float(rec), float(f1)


# ---------------------------------------------------------------- plot
def maybe_savefig(fig, path):
    """Salveaza figura daca matplotlib e disponibil; altfel tipareste o nota si trece.

    Toate demo_sil.py folosesc asta ca sa ruleze headless si fara matplotlib."""
    try:
        fig.savefig(path, dpi=110, bbox_inches="tight")
        print("[fig] scris %s" % path)
        return True
    except Exception as e:  # pragma: no cover - depinde de mediu
        print("[fig] sarit (%s): %s" % (path, e))
        return False


# ---------------------------------------------------------------- selftest
def _selftest():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    # split: dimensiuni corecte, fara suprapunere, determinist
    X = np.arange(40).reshape(20, 2)
    y = np.arange(20)
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_frac=0.25, seed=0)
    ck("split: 15 train + 5 test din 20", Xtr.shape[0] == 15 and Xte.shape[0] == 5)
    ck("split: train+test acopera tot, fara suprapunere",
       sorted(np.concatenate([ytr, yte]).tolist()) == list(range(20)))
    Xtr2, _, ytr2, _ = train_test_split(X, y, test_frac=0.25, seed=0)
    ck("split: determinist la aceeasi samanta", np.array_equal(ytr, ytr2))

    # standardize: train are media ~0 si abaterea ~1; fara scurgere (foloseste stat train)
    Xr = rng(1).normal(5, 3, size=(100, 3))
    Xs, _, m, s = standardize(Xr)
    ck("standardize: media train ~0", np.allclose(Xs.mean(axis=0), 0, atol=1e-9))
    ck("standardize: abaterea train ~1", np.allclose(Xs.std(axis=0), 1, atol=1e-9))
    _, Xte_s, _, _ = standardize(Xr[:80], Xr[80:])
    expected = (Xr[80:] - Xr[:80].mean(axis=0)) / Xr[:80].std(axis=0)
    ck("standardize: test foloseste stat de pe train", np.allclose(Xte_s, expected))

    # add_bias
    ck("add_bias: coloana de 1 la stanga", np.array_equal(add_bias([[2.0], [3.0]])[:, 0], [1, 1]))

    # metrici regresie
    ck("rmse: potrivire perfecta = 0", rmse([1, 2, 3], [1, 2, 3]) == 0.0)
    ck("mae: |.| mediu", abs(mae([0, 0], [1, 3]) - 2.0) < 1e-12)
    ck("r2: potrivire perfecta = 1", abs(r2_score([1, 2, 3, 4], [1, 2, 3, 4]) - 1.0) < 1e-12)
    ck("r2: media constanta = 0", abs(r2_score([1, 2, 3], [2, 2, 2]) - 0.0) < 1e-12)

    # metrici clasificare: caz cunoscut
    yt = [0, 0, 1, 1, 1]
    yp = [0, 1, 1, 1, 0]
    cm = confusion_matrix(yt, yp)
    ck("confusion: [[TN,FP],[FN,TP]] = [[1,1],[1,2]]", np.array_equal(cm, [[1, 1], [1, 2]]))
    prec, rec, f1 = precision_recall_f1(yt, yp)
    ck("precision = TP/(TP+FP) = 2/3", abs(prec - 2 / 3) < 1e-12)
    ck("recall = TP/(TP+FN) = 2/3", abs(rec - 2 / 3) < 1e-12)
    ck("accuracy = 3/5", abs(accuracy(yt, yp) - 0.6) < 1e-12)

    print("\nTOATE VERIFICARILE utils AU TRECUT: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _selftest()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
