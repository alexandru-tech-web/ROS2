#!/usr/bin/env python3
"""invatare_supervizata_core.py -- nucleul M03, numpy pur (scikit-learn INTERZIS).

Acopera doua piese ale cadrului invatarii supervizate:

1) FUNCTII DE PIERDERE. Pentru o tinta y si o predictie p (scor sau eticheta),
   o functie de pierdere L(y, p) >= 0 masoara cat de gresita e predictia. Riscul
   empiric este media pierderii pe setul de antrenare:
       R_emp(h) = (1/n) * sum_i L(y_i, h(x_i)).
   ERM (Empirical Risk Minimization) alege h care minimizeaza R_emp pe o clasa H.
   Implementam: patratica (regresie), 0-1 (clasificare, nediferentiabila),
   hinge (SVM, margine) si logistica (entropie incrucisata, probabilista).

2) DESCOMPUNEREA BIAS-VARIANTA prin simulatie Monte Carlo. Generam multe seturi
   de antrenare din acelasi proces y = f(x) + zgomot, antrenam pe fiecare un model
   polinomial de grad d (cu cele mai mici patrate, ecuatia normala), si masuram la
   un punct fix x0 (sau mediat pe un grid) descompunerea erorii patratice asteptate:

       E[(y - h_S(x))^2] = bias(x)^2 + Var(x) + sigma^2

   unde, notand h_bar(x) = E_S[h_S(x)] media predictiilor peste seturile S:
       bias(x)   = h_bar(x) - f(x)        (eroare sistematica)
       Var(x)    = E_S[(h_S(x) - h_bar(x))^2]   (sensibilitate la setul de antrenare)
       sigma^2   = Var al zgomotului ireductibil din y.

   DERIVAREA (pe scurt; completa in teorie.md). Fixam x. Fie y = f(x) + eps cu
   E[eps]=0, Var[eps]=sigma^2, eps independent de S. Scriem h = h_S(x), h_bar = E_S[h].
       E_{S,eps}[(y - h)^2]
         = E[(f + eps - h)^2]
         = E[(f - h)^2] + 2 E[eps (f - h)] + E[eps^2]
         = E[(f - h)^2] + 0 + sigma^2        (eps indep. de S, medie 0)
   Apoi adunam si scadem h_bar in (f - h):
       E[(f - h)^2] = E[((f - h_bar) - (h - h_bar))^2]
         = (f - h_bar)^2 - 2 (f - h_bar) E[h - h_bar] + E[(h - h_bar)^2]
         = (f - h_bar)^2 + 0 + Var_S[h]      (E[h - h_bar] = 0 prin definitie)
         = bias(x)^2 + Var(x).
   Deci E[(y - h)^2] = bias^2 + Var + sigma^2.   QED.

Determinism: tot aleatorul trece prin numpy.random.default_rng(seed).
Validare: _selftest() verifica valorile pierderilor pe cazuri mici cunoscute si
egalitatea Monte Carlo eroare_totala ~ bias^2 + Var + sigma^2 sub toleranta, plus
ca un model de grad mare are varianta mai mare ca unul de grad mic.

Ruleaza: /home/ubuntu/ros2_ws/.venv_ml/bin/python invatare_supervizata_core.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml


# ============================================================ FUNCTII DE PIERDERE
def squared_loss(y_true, y_pred):
    """Pierdere patratica L = (y - p)^2 (per esantion), pentru regresie."""
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    return (y_true - y_pred) ** 2


def zero_one_loss(y_true, y_pred):
    """Pierdere 0-1: 0 daca eticheta prezisa == reala, 1 altfel.

    Etichetele pot fi orice (de obicei {0,1} sau {-1,+1}); se compara direct.
    Nediferentiabila -- de aceea optimizarea foloseste surogate (hinge, logistica).
    """
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    return (y_true != y_pred).astype(float)


def hinge_loss(y_true, score):
    """Pierdere hinge L = max(0, 1 - y*score), cu y in {-1, +1} si score scor real.

    Penalizeaza scorurile cu margine < 1; zero pe partea corecta cu margine ampla.
    Surogatul SVM pentru 0-1.
    """
    y_true = np.asarray(y_true, dtype=float)
    score = np.asarray(score, dtype=float)
    return np.maximum(0.0, 1.0 - y_true * score)


def logistic_loss(y_true, score):
    """Pierdere logistica (entropie incrucisata) cu y in {0,1} si score = logit.

    L = log(1 + exp(score)) - y*score = -[ y*log(s) + (1-y)*log(1-s) ], s=sigmoid(score).
    Forma 'log(1+exp(score)) - y*score' e stabila numeric via logaddexp.
    Surogatul neted, probabilist, pentru 0-1.
    """
    y_true = np.asarray(y_true, dtype=float)
    score = np.asarray(score, dtype=float)
    # log(1 + exp(score)) = logaddexp(0, score), stabil pentru |score| mare
    return np.logaddexp(0.0, score) - y_true * score


def sigmoid(z):
    """Sigmoida logistica 1/(1+exp(-z)), stabila numeric."""
    z = np.asarray(z, dtype=float)
    out = np.empty_like(z)
    pos = z >= 0
    out[pos] = 1.0 / (1.0 + np.exp(-z[pos]))
    ez = np.exp(z[~pos])
    out[~pos] = ez / (1.0 + ez)
    return out


def empirical_risk(loss_fn, y_true, pred):
    """Risc empiric R_emp = media per-esantion a unei functii de pierdere."""
    return float(np.mean(loss_fn(y_true, pred)))


# ============================================================ MODEL POLINOMIAL
def poly_design(x, degree):
    """Matrice de design polinomiala [1, x, x^2, ..., x^degree] (Vandermonde)."""
    x = np.asarray(x, dtype=float).reshape(-1)
    return np.vander(x, N=degree + 1, increasing=True)


def fit_poly(x, y, degree, ridge=0.0):
    """Potrivire polinom de grad `degree` prin cele mai mici patrate (ecuatie normala).

    Rezolva (Phi^T Phi + ridge*I) w = Phi^T y. `ridge` mic stabilizeaza la grad mare
    (matrice prost conditionata); 0.0 = OLS curat. Returneaza vectorul de coeficienti w.
    """
    Phi = poly_design(x, degree)
    A = Phi.T @ Phi
    if ridge > 0.0:
        A = A + ridge * np.eye(A.shape[0])
    b = Phi.T @ np.asarray(y, dtype=float).reshape(-1)
    # lstsq pe sistemul normal: robust daca A e singular (grad > n_puncte)
    w, *_ = np.linalg.lstsq(A, b, rcond=None)
    return w


def predict_poly(w, x):
    """Predictie a unui polinom cu coeficienti w (increasing) pe punctele x."""
    Phi = poly_design(x, len(w) - 1)
    return Phi @ np.asarray(w, dtype=float)


# ============================================================ BIAS-VARIANTA (MONTE CARLO)
def bias_variance_decomposition(f_true, x_grid, degree, sigma, n_train,
                                n_datasets=400, x_train_low=-1.0, x_train_high=1.0,
                                ridge=1e-8, seed=0):
    """Descompunere bias-varianta a unui polinom de grad `degree` prin Monte Carlo.

    Pentru fiecare din `n_datasets` seturi de antrenare:
      - esantioneaza x_train ~ Uniform[x_train_low, x_train_high], n_train puncte;
      - y_train = f_true(x_train) + N(0, sigma^2);
      - potriveste polinom de grad `degree`; prezice pe `x_grid`.
    Apoi, mediat pe `x_grid`:
      bias2     = mean_x (h_bar(x) - f(x))^2
      variance  = mean_x mean_S (h_S(x) - h_bar(x))^2
      noise     = sigma^2   (zgomotul ireductibil, cunoscut prin constructie)
      total     = mean_x mean_S E[(y - h_S(x))^2]  estimat cu un y proaspat la fiecare x

    Returneaza un dict cu bias2, variance, noise, total si total_check
    (= bias2 + variance + noise), care trebuie sa coincida cu `total` sub toleranta.
    """
    g = np.random.default_rng(seed)
    x_grid = np.asarray(x_grid, dtype=float).reshape(-1)
    f_grid = np.asarray(f_true(x_grid), dtype=float)
    n_grid = x_grid.shape[0]

    preds = np.empty((n_datasets, n_grid))     # h_S(x) pentru fiecare set S si fiecare x
    fresh_y = np.empty((n_datasets, n_grid))    # un y proaspat la fiecare x (pt. eroarea totala)
    for s in range(n_datasets):
        x_tr = g.uniform(x_train_low, x_train_high, size=n_train)
        y_tr = f_true(x_tr) + g.normal(0.0, sigma, size=n_train)
        w = fit_poly(x_tr, y_tr, degree, ridge=ridge)
        preds[s] = predict_poly(w, x_grid)
        fresh_y[s] = f_grid + g.normal(0.0, sigma, size=n_grid)

    h_bar = preds.mean(axis=0)                   # media predictiilor peste seturi, per x
    bias2 = float(np.mean((h_bar - f_grid) ** 2))
    variance = float(np.mean(np.var(preds, axis=0)))   # var peste seturi, mediat pe grid
    noise = float(sigma ** 2)
    total = float(np.mean((fresh_y - preds) ** 2))     # eroare patratica totala empirica
    return dict(
        bias2=bias2,
        variance=variance,
        noise=noise,
        total=total,
        total_check=bias2 + variance + noise,
        degree=int(degree),
    )


# ============================================================ SELFTEST
def _selftest():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    # ---------------------------------------------- pierderi: valori cunoscute pe cazuri mici
    # patratica: (3-1)^2=4, (0-0)^2=0, (-2-1)^2=9 -> media 13/3
    sl = squared_loss([3.0, 0.0, -2.0], [1.0, 0.0, 1.0])
    ck("squared: per-esantion = [4, 0, 9]", np.allclose(sl, [4.0, 0.0, 9.0]))
    ck("squared: risc empiric = 13/3", abs(empirical_risk(squared_loss,
       [3.0, 0.0, -2.0], [1.0, 0.0, 1.0]) - 13.0 / 3.0) < 1e-12)

    # 0-1: 3 corecte din 4 -> 1 gresita -> risc 0.25
    z = zero_one_loss([0, 1, 1, 0], [0, 1, 0, 0])
    ck("0-1: per-esantion = [0,0,1,0]", np.allclose(z, [0, 0, 1, 0]))
    ck("0-1: risc empiric = 1/4", abs(empirical_risk(zero_one_loss,
       [0, 1, 1, 0], [0, 1, 0, 0]) - 0.25) < 1e-12)

    # hinge: y=+1, score=2 -> max(0,1-2)=0 ; y=+1, score=0.3 -> 0.7 ; y=-1, score=0.5 -> 1.5
    h = hinge_loss([1.0, 1.0, -1.0], [2.0, 0.3, 0.5])
    ck("hinge: [0, 0.7, 1.5]", np.allclose(h, [0.0, 0.7, 1.5]))
    # margine exact 1 pe partea corecta -> pierdere exact 0
    ck("hinge: margine =1 da pierdere 0", abs(hinge_loss([1.0], [1.0])[0]) < 1e-12)

    # logistica: score=0 -> log(2) indiferent de y (cand y=0: log(2)-0; cand y=1: log(2)-0? nu)
    # y=0, score=0 -> log(1+1) - 0 = log 2 ; y=1, score=0 -> log 2 - 0 = log 2
    ck("logistica: score 0 -> log 2 (y=0)", abs(logistic_loss([0.0], [0.0])[0] - np.log(2)) < 1e-12)
    ck("logistica: score 0 -> log 2 (y=1)", abs(logistic_loss([1.0], [0.0])[0] - np.log(2)) < 1e-12)
    # corespondenta cu entropia incrucisata via sigmoid: -[y log s + (1-y) log(1-s)]
    sc = np.array([-1.3, 0.0, 2.7, 4.1])
    yy = np.array([0.0, 1.0, 1.0, 0.0])
    s = sigmoid(sc)
    ce = -(yy * np.log(s) + (1 - yy) * np.log(1 - s))
    ck("logistica == entropie incrucisata via sigmoid",
       np.allclose(logistic_loss(yy, sc), ce, atol=1e-10))
    # sigmoid: valori cunoscute
    ck("sigmoid(0)=0.5", abs(sigmoid(0.0) - 0.5) < 1e-12)
    ck("sigmoid monotona crescatoare", sigmoid(-3.0) < sigmoid(0.0) < sigmoid(3.0))

    # ---------------------------------------------- model polinomial: potrivire exacta
    # 3 puncte pe o parabola y = 1 + 2x + 3x^2 -> grad 2 trebuie sa recupereze coeficientii
    xs = np.array([-1.0, 0.0, 1.0, 2.0])
    coef = np.array([1.0, 2.0, 3.0])           # increasing: 1 + 2x + 3x^2
    ys = predict_poly(coef, xs)
    w = fit_poly(xs, ys, degree=2, ridge=0.0)
    ck("poly: recupereaza coeficientii unei parabole", np.allclose(w, coef, atol=1e-8))
    ck("poly: predictie exacta dupa potrivire", np.allclose(predict_poly(w, xs), ys, atol=1e-8))

    # ---------------------------------------------- bias-varianta: egalitatea fundamentala
    def f_true(x):
        return np.sin(1.5 * np.pi * x)         # tinta neliniara, nepolinomiala exact

    x_grid = np.linspace(-0.9, 0.9, 25)
    sigma = 0.25

    # grad mic (sub-invatare): bias mare, varianta mica
    low = bias_variance_decomposition(f_true, x_grid, degree=1, sigma=sigma,
                                      n_train=20, n_datasets=600, seed=1)
    # grad mare (supra-invatare): bias mic, varianta mare
    high = bias_variance_decomposition(f_true, x_grid, degree=11, sigma=sigma,
                                       n_train=20, n_datasets=600, seed=1)

    # egalitatea total ~ bias^2 + varianta + zgomot (sub toleranta), pentru ambele grade
    rel_low = abs(low["total"] - low["total_check"]) / low["total"]
    rel_high = abs(high["total"] - high["total_check"]) / high["total"]
    ck("biasvar: total ~ bias2+var+zgomot (grad 1), eroare rel < 8pct", rel_low < 0.08)
    ck("biasvar: total ~ bias2+var+zgomot (grad 11), eroare rel < 8pct", rel_high < 0.08)

    # zgomotul estimat e exact sigma^2 prin constructie
    ck("biasvar: zgomot == sigma^2", abs(low["noise"] - sigma ** 2) < 1e-12)

    # gradul mare are varianta mai mare ca gradul mic
    ck("biasvar: var(grad 11) > var(grad 1)", high["variance"] > low["variance"])
    # gradul mic are bias mai mare ca gradul mare (sub-invatare vs flexibil)
    ck("biasvar: bias2(grad 1) > bias2(grad 11)", low["bias2"] > high["bias2"])

    print("\nTOATE VERIFICARILE invatare_supervizata_core AU TRECUT: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _selftest()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
