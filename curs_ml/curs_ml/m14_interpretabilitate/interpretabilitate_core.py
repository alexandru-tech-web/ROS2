#!/usr/bin/env python3
"""interpretabilitate_core.py -- nucleul M14, numpy pur (scikit-learn INTERZIS).

Explicabilitate MODEL-AGNOSTICA: functiile primesc un callback `model_predict(X)`
si nu stiu nimic despre cum e antrenat modelul. Trei unelte:
  - permutation_importance: cat scade scorul cand stricam (permutam) un feature;
  - partial_dependence (PDP): media predictiei variind un feature peste distributia
    celorlalte (le tinem la valorile reale, variem doar coloana de interes);
  - shapley_linear: valori Shapley EXACTE pentru un model liniar -- contributia
    feature-ului j este w_j * (x_j - E[x_j]); proprietatea de eficienta (suma
    contributiilor = predictie - baza) tine exact.

Pentru selftest definim intern un model liniar minimal (ecuatii normale) ca sa nu
importam alt modul mXX -- nucleul ramane auto-suficient.

Determinism: permutarile trec prin numpy.random.default_rng(seed).
_selftest() verifica:
  - pe date unde DOAR feature 0 conteaza, importanta de permutare a lui 0 >>
    importanta feature-ului de zgomot (~0);
  - PDP pe un model monoton crescator iese crescator;
  - valorile Shapley liniare insumeaza la predictie - baza (eficienta) sub toleranta.

Ruleaza: /home/ubuntu/ros2_ws/.venv_ml/bin/python interpretabilitate_core.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from utils import r2_score  # noqa: E402


# ============================================================ IMPORTANTA PRIN PERMUTARE
def permutation_importance(model_predict, X, y, metric=r2_score, n_repeats=10, seed=0):
    """Cat scade scorul cand stricam fiecare feature.

    Scorul de baza este metric(y, model_predict(X)). Pentru fiecare coloana j,
    permutam aleator valorile coloanei (rupem legatura feature-tinta), recalculam
    scorul si raportam SCADEREA medie pe n_repeats permutari: baza - scor_permutat.
    O importanta mare = feature-ul conta (scorul s-a prabusit cand l-am stricat);
    ~0 = feature-ul nu ajuta modelul.

    Returneaza un array (n_features,) cu importanta medie per feature.
    """
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float).reshape(-1)
    n, d = X.shape
    g = np.random.default_rng(seed)
    base = metric(y, model_predict(X))
    importances = np.zeros(d)
    for j in range(d):
        drops = np.empty(n_repeats)
        for r in range(n_repeats):
            Xp = X.copy()
            Xp[:, j] = X[g.permutation(n), j]
            drops[r] = base - metric(y, model_predict(Xp))
        importances[j] = drops.mean()
    return importances


# ============================================================ PARTIAL DEPENDENCE (PDP)
def partial_dependence(model_predict, X, feature_idx, grid):
    """Profilul de dependenta partiala al unui feature.

    Pentru fiecare valoare v din grid, FORTAM coloana feature_idx la v pe TOATE
    randurile (pastrand celelalte coloane la valorile lor reale) si mediem
    predictia. Asta marginalizeaza empiric peste distributia celorlalte feature-uri:
    pdp(v) = (1/n) sum_i model_predict(x_i cu x_{i,feature_idx} := v).

    Returneaza un array aliniat cu grid: media predictiei la fiecare valoare.
    """
    X = np.asarray(X, dtype=float)
    grid = np.asarray(grid, dtype=float).reshape(-1)
    out = np.empty(grid.size)
    for t, v in enumerate(grid):
        Xv = X.copy()
        Xv[:, feature_idx] = v
        out[t] = float(np.mean(model_predict(Xv)))
    return out


# ============================================================ VALORI SHAPLEY (LINIAR)
def shapley_linear(w, x, x_mean):
    """Valori Shapley EXACTE pentru un model liniar f(x) = w0 + sum_j w_j x_j.

    Pentru o functie liniara, contributia (valoarea Shapley) a feature-ului j fata
    de baza E[f] = w0 + sum_j w_j E[x_j] este, exact:
        phi_j = w_j * (x_j - E[x_j]).
    Nu e nevoie de suma peste coalitii: liniaritatea o colapseaza la acest termen.

    Proprietatea de EFICIENTA: sum_j phi_j = f(x) - E[f] (interceptul w0 se anuleaza
    intre f(x) si baza). Returneaza un array (n_features,) cu phi_j.

    `w` sunt PANTELE (fara intercept), `x` instanta, `x_mean` mediile pe feature.
    """
    w = np.asarray(w, dtype=float).reshape(-1)
    x = np.asarray(x, dtype=float).reshape(-1)
    x_mean = np.asarray(x_mean, dtype=float).reshape(-1)
    return w * (x - x_mean)


# ============================================================ MODEL AUXILIAR (intern)
def _linfit(X, y):
    """Regresie liniara minimala cu intercept (ecuatii normale via lstsq).

    Definita INTERN ca sa nu importam alt modul mXX. Returneaza (w0, w) cu w0
    interceptul si w pantele. Folosita doar in selftest si demo ca model de explicat.
    """
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float).reshape(-1)
    Phi = np.column_stack([np.ones(X.shape[0]), X])
    beta, *_ = np.linalg.lstsq(Phi, y, rcond=None)
    return float(beta[0]), beta[1:]


def _make_predict(w0, w):
    """Inchide un model liniar intr-un callback model_predict(X) -> y_pred."""
    w = np.asarray(w, dtype=float).reshape(-1)
    return lambda X: np.asarray(X, dtype=float) @ w + w0


# ============================================================ SELFTEST
def _selftest():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    # ---- permutation_importance: doar feature 0 conteaza, feature 1 e zgomot
    g = np.random.default_rng(0)
    n = 400
    x0 = g.uniform(-2, 2, size=n)
    x1 = g.uniform(-2, 2, size=n)  # zgomot pur: nu intra in tinta
    X = np.column_stack([x0, x1])
    y = 3.0 * x0 + 0.5 + 0.01 * g.standard_normal(n)
    w0, w = _linfit(X, y)
    pred = _make_predict(w0, w)
    imp = permutation_importance(pred, X, y, metric=r2_score, n_repeats=20, seed=1)
    ck("perm: importanta feature 0 mare (> 0.5)", imp[0] > 0.5)
    ck("perm: importanta feature de zgomot ~0 (< 0.02)", abs(imp[1]) < 0.02)
    ck("perm: feature 0 >> feature de zgomot", imp[0] > 10 * abs(imp[1]) + 0.1)

    # ---- partial_dependence: model monoton crescator -> PDP crescator
    # f(x) = 2*x0 - x1 ; PDP pe feature 0 trebuie sa creasca cu grid-ul
    predm = _make_predict(0.0, np.array([2.0, -1.0]))
    Xm = g.uniform(-1, 1, size=(200, 2))
    grid = np.linspace(-3, 3, 7)
    pdp0 = partial_dependence(predm, Xm, feature_idx=0, grid=grid)
    ck("pdp: profil crescator pe feature monoton crescator",
       np.all(np.diff(pdp0) > 0))
    ck("pdp: panta PDP ~ coeficientul (2.0)",
       abs((pdp0[-1] - pdp0[0]) / (grid[-1] - grid[0]) - 2.0) < 1e-9)
    # feature cu coeficient negativ -> PDP descrescator
    pdp1 = partial_dependence(predm, Xm, feature_idx=1, grid=grid)
    ck("pdp: profil descrescator pe feature cu coeficient negativ",
       np.all(np.diff(pdp1) < 0))

    # ---- shapley_linear: eficienta (suma = predictie - baza), caz exact
    rng = np.random.default_rng(5)
    Xs = rng.normal(0, 1, size=(300, 4))
    w_true = np.array([1.5, -2.0, 0.7, 0.0])
    w0s = 0.4
    ys = Xs @ w_true + w0s + 0.02 * rng.standard_normal(300)
    w0_hat, w_hat = _linfit(Xs, ys)
    x_mean = Xs.mean(axis=0)
    predf = _make_predict(w0_hat, w_hat)
    base = float(np.mean(predf(Xs)))            # E[f] empiric
    for i in (0, 1, 2):
        phi = shapley_linear(w_hat, Xs[i], x_mean)
        fx = float(predf(Xs[i]))
        ck("shapley: eficienta suma(phi) = f(x) - baza (rand %d)" % i,
           abs(phi.sum() - (fx - base)) < 1e-8)
    # caz lucrat de mana din teorie.md: w=[2,-3], x=[1,4], E[x]=[0,5]
    phi_man = shapley_linear([2.0, -3.0], [1.0, 4.0], [0.0, 5.0])
    ck("shapley: caz manual phi = [2, 3] (vezi teorie.md)",
       np.allclose(phi_man, [2.0, 3.0]))

    print("\nTOATE VERIFICARILE interpretabilitate_core AU TRECUT: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _selftest()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
