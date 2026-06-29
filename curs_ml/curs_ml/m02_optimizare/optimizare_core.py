#!/usr/bin/env python3
"""optimizare_core.py -- optimizare de la zero pentru ML (numpy pur).

Modulul M02 al cursului curs_ml. Implementeaza, FARA scikit-learn, motorul din
spatele tuturor modelelor antrenate: coborarea pe gradient (GD), versiunea
stochastica (SGD), momentum si Adam. Plus o unealta esentiala de depanare:
verificarea gradientului analitic cu diferente finite.

MATEMATICA (banc de proba: o patratica convexa)
------------------------------------------------
Folosim functia obiectiv

    f(w) = 0.5 * w^T A w - b^T w

cu A simetrica si pozitiv definita (SPD). Gradientul este

    grad f(w) = A w - b

iar minimul (unde gradientul se anuleaza) are forma inchisa

    w* = A^{-1} b .

Asta e bancul de proba perfect: stim raspunsul exact, deci putem verifica daca
optimizarea iterativa chiar ajunge acolo. f este CONVEXA (Hessiana A este SPD),
deci coborarea pe gradient cu pas suficient de mic converge global.

CONDITIONAREA. Viteza de convergenta a GD pe patratica depinde de numarul de
conditionare kappa = lambda_max(A) / lambda_min(A). Pasul (rata de invatare) eta
trebuie ales sub 2 / lambda_max(A); pentru un raport convergenta/pas optim,
eta = 2 / (lambda_max + lambda_min). Cu kappa mare (problema 'prost conditionata')
GD zigzagheaza si converge lent -- de aici momentum si Adam.

ALGORITMI
---------
GD:        w <- w - eta * grad
Momentum:  v <- mu * v - eta * grad ;  w <- w + v       (Polyak heavy-ball)
Adam:      momente 1 (m) si 2 (v) exponentiale, corectate de bias:
           m <- b1*m + (1-b1)*g ; v <- b2*v + (1-b2)*g^2
           m_hat = m/(1-b1^t) ; v_hat = v/(1-b2^t)
           w <- w - alpha * m_hat / (sqrt(v_hat) + eps)

VERIFICAREA GRADIENTULUI (diferente finite centrate)
----------------------------------------------------
    d f / d w_i ~ (f(w + h e_i) - f(w - h e_i)) / (2h)
Eroarea formulei centrate scade ca O(h^2), deci la h ~ 1e-5 ajungem usor sub 1e-5
fata de gradientul analitic. Este testul standard pentru a prinde o derivata
gresit derivata de mana.

CONVENTII: ASCII pur, romana fara diacritice. Determinism prin numpy default_rng.
scikit-learn este INTERZIS aici (validarea cu sklearn sta in optimizare_sklearn.py).

Ruleaza selftestul:
  /home/ubuntu/ros2_ws/.venv_ml/bin/python optimizare_core.py   (iesire 0 = PASS)
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml


# ============================================================ functia obiectiv
def quadratic_value(w, A, b):
    """f(w) = 0.5 w^T A w - b^T w (un scalar)."""
    w = np.asarray(w, dtype=float)
    return float(0.5 * w @ A @ w - b @ w)


def quadratic_grad(w, A, b):
    """Gradient analitic: grad f(w) = A w - b."""
    w = np.asarray(w, dtype=float)
    return A @ w - b


def quadratic_solution(A, b):
    """Minimul analitic w* = A^{-1} b (A trebuie inversabila / SPD)."""
    return np.linalg.solve(A, b)


# ============================================================ diferente finite
def numerical_grad(f, w, h=1e-5):
    """Gradient prin diferente finite CENTRATE.

    f: functie scalara de un vector w. Returneaza un vector de aceeasi forma cu w.
    Eroarea formulei centrate este O(h^2)."""
    w = np.asarray(w, dtype=float)
    g = np.zeros_like(w)
    for i in range(w.size):
        e = np.zeros_like(w)
        e[i] = h
        g[i] = (f(w + e) - f(w - e)) / (2.0 * h)
    return g


def check_grad(f, grad_f, w, h=1e-5):
    """Norma diferentei (analitic - numeric) la w. Sub ~1e-5 = derivata corecta."""
    ga = np.asarray(grad_f(w), dtype=float)
    gn = numerical_grad(f, w, h=h)
    return float(np.linalg.norm(ga - gn))


# ============================================================ optimizatori
def gradient_descent(grad, w0, eta=0.1, n_iter=200, value=None, tol=0.0):
    """Coborare pe gradient pe loturi complete (batch GD).

    grad(w) -> gradient; w0 vector initial; eta rata de invatare. Daca `value`
    e dat, inregistreaza pierderea la fiecare iteratie in `history`. Opreste
    devreme daca ||grad|| < tol (tol=0 dezactiveaza). Returneaza (w, history)."""
    w = np.array(w0, dtype=float)
    history = []
    for _ in range(n_iter):
        g = grad(w)
        if value is not None:
            history.append(value(w))
        if tol > 0.0 and np.linalg.norm(g) < tol:
            break
        w = w - eta * g
    return w, history


def momentum_gd(grad, w0, eta=0.05, mu=0.9, n_iter=200, value=None):
    """Coborare cu moment (Polyak heavy-ball).

    v <- mu*v - eta*grad ; w <- w + v. mu in [0,1) este factorul de inertie.
    Amortizeaza zigzagul pe problemele prost conditionate. Returneaza (w, history)."""
    w = np.array(w0, dtype=float)
    v = np.zeros_like(w)
    history = []
    for _ in range(n_iter):
        g = grad(w)
        if value is not None:
            history.append(value(w))
        v = mu * v - eta * g
        w = w + v
    return w, history


def adam(grad, w0, alpha=0.05, b1=0.9, b2=0.999, eps=1e-8, n_iter=200, value=None):
    """Adam (Kingma & Ba, 2015): pas adaptiv pe coordonata.

    Combina momentul de ordin 1 (medie a gradientului) cu cel de ordin 2 (medie a
    patratului), ambele cu corectie de bias. Robust la scalari diferiti pe axe.
    Returneaza (w, history)."""
    w = np.array(w0, dtype=float)
    m = np.zeros_like(w)
    v = np.zeros_like(w)
    history = []
    for t in range(1, n_iter + 1):
        g = grad(w)
        if value is not None:
            history.append(value(w))
        m = b1 * m + (1.0 - b1) * g
        v = b2 * v + (1.0 - b2) * (g * g)
        m_hat = m / (1.0 - b1 ** t)
        v_hat = v / (1.0 - b2 ** t)
        w = w - alpha * m_hat / (np.sqrt(v_hat) + eps)
    return w, history


def sgd(grad_i, w0, n_samples, eta=0.05, n_epochs=50, seed=0, value=None):
    """Coborare stochastica pe gradient (un esantion pe pas).

    grad_i(w, i) -> gradientul contributiei esantionului i. Permuta indicii la
    fiecare epoca (fara inlocuire). Pasul scade ca eta / (1 + 0.01*epoca) ca sa
    micsoreze zgomotul stochastic spre final. `value` (daca e dat) e evaluata o
    data per epoca. Returneaza (w, history)."""
    w = np.array(w0, dtype=float)
    g = np.random.default_rng(seed)
    history = []
    for ep in range(n_epochs):
        if value is not None:
            history.append(value(w))
        eta_t = eta / (1.0 + 0.01 * ep)
        for i in g.permutation(n_samples):
            w = w - eta_t * grad_i(w, int(i))
    return w, history


# ============================================================ rata buna pe patratica
def optimal_step_quadratic(A):
    """Pasul GD care maximizeaza viteza pe patratica: 2 / (lmax + lmin)."""
    ev = np.linalg.eigvalsh(A)
    return 2.0 / (ev[0] + ev[-1])


def condition_number(A):
    """Numarul de conditionare kappa = lambda_max / lambda_min (A SPD)."""
    ev = np.linalg.eigvalsh(A)
    return float(ev[-1] / ev[0])


# ============================================================ selftest
def _selftest():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    # --- banc de proba: patratica SPD bidimensionala, prost conditionata ---
    A = np.array([[3.0, 1.0],
                  [1.0, 2.0]])
    b = np.array([1.0, -2.0])
    w_star = quadratic_solution(A, b)

    f = lambda w: quadratic_value(w, A, b)
    grad = lambda w: quadratic_grad(w, A, b)

    # (1) gradientul analitic == diferente finite, eroare < 1e-5
    rng = np.random.default_rng(0)
    max_err = 0.0
    for _ in range(20):
        w = rng.normal(size=2)
        max_err = max(max_err, check_grad(f, grad, w, h=1e-5))
    ck("gradient analitic == diferente finite (eroare %.2e < 1e-5)" % max_err, max_err < 1e-5)

    # (2) la minim gradientul se anuleaza
    ck("grad f(w*) ~ 0", np.linalg.norm(grad(w_star)) < 1e-10)

    # (3) GD converge la minimul analitic w* = A^-1 b
    w0 = np.array([5.0, 5.0])
    eta = optimal_step_quadratic(A)
    w_gd, hist_gd = gradient_descent(grad, w0, eta=eta, n_iter=300, value=f)
    ck("GD converge la w* = A^-1 b (||w_gd - w*|| %.2e)" % np.linalg.norm(w_gd - w_star),
       np.allclose(w_gd, w_star, atol=1e-6))
    ck("GD: pierderea scade monoton", all(hist_gd[i + 1] <= hist_gd[i] + 1e-12
                                          for i in range(len(hist_gd) - 1)))

    # (4) momentum converge si el la w*
    w_mom, _ = momentum_gd(grad, w0, eta=0.05, mu=0.9, n_iter=400, value=f)
    ck("momentum converge la w* (||.|| %.2e)" % np.linalg.norm(w_mom - w_star),
       np.allclose(w_mom, w_star, atol=1e-5))

    # (5) Adam converge si el la w*
    w_adam, hist_adam = adam(grad, w0, alpha=0.05, n_iter=4000, value=f)
    ck("Adam converge la w* (||.|| %.2e)" % np.linalg.norm(w_adam - w_star),
       np.allclose(w_adam, w_star, atol=1e-4))

    # (6) toate trei ating aceeasi valoare minima a functiei
    f_star = f(w_star)
    ck("f(w_gd) ~ f(w_mom) ~ f(w_adam) ~ f(w*)",
       abs(f(w_gd) - f_star) < 1e-6 and abs(f(w_mom) - f_star) < 1e-6
       and abs(f(w_adam) - f_star) < 1e-3)

    # (7) conditionarea: pas prea mare -> divergenta
    eta_big = 2.0 / np.linalg.eigvalsh(A)[-1] + 0.5  # peste pragul 2/lmax
    w_div, _ = gradient_descent(grad, w0, eta=eta_big, n_iter=50)
    ck("pas peste 2/lmax -> diverge (||w|| mare)", np.linalg.norm(w_div) > 1e3)

    # (8) numarul de conditionare e calculat corect (vs eigvals)
    ev = np.linalg.eigvalsh(A)
    ck("kappa = lmax/lmin corect", abs(condition_number(A) - ev[-1] / ev[0]) < 1e-12)

    # (9) SGD pe o regresie liniara mica converge aproape de solutia normala
    rng2 = np.random.default_rng(1)
    n, d = 200, 3
    X = rng2.normal(size=(n, d))
    w_true = np.array([1.5, -2.0, 0.5])
    y = X @ w_true + 0.01 * rng2.normal(size=n)

    def grad_i(w, i):  # gradientul pierderii patratice pentru esantionul i
        xi = X[i]
        return 2.0 * (xi @ w - y[i]) * xi

    w_sgd, _ = sgd(grad_i, np.zeros(d), n_samples=n, eta=0.02, n_epochs=200, seed=0)
    w_normal = np.linalg.lstsq(X, y, rcond=None)[0]
    ck("SGD ~ solutia normala pe regresie (||.|| %.3f)" % np.linalg.norm(w_sgd - w_normal),
       np.allclose(w_sgd, w_normal, atol=0.05))

    print("\nTOATE VERIFICARILE optimizare_core AU TRECUT: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _selftest()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
