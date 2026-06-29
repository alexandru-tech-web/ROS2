#!/usr/bin/env python3
"""solutii.py -- M02 Optimizare pentru ML. Solutii complete.

Aceleasi asserturi ca in exercitii.py, dar cu functiile rezolvate. Rulat cu venv
TREBUIE sa TREACA (iesire 0).

Ruleaza:
  /home/ubuntu/ros2_ws/.venv_ml/bin/python solutii.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from optimizare_core import quadratic_grad, quadratic_solution, quadratic_value


# ---------------------------------------------------------------- Exercitiul 1
def ex1_grad_numeric(f, w, h=1e-5):
    """Gradient prin diferente finite centrate."""
    w = np.asarray(w, dtype=float)
    g = np.zeros_like(w)
    for i in range(w.size):
        e = np.zeros_like(w)
        e[i] = h
        g[i] = (f(w + e) - f(w - e)) / (2.0 * h)
    return g


# ---------------------------------------------------------------- Exercitiul 2
def ex2_gd(grad, w0, eta, n_iter):
    """Coborare pe gradient (batch)."""
    w = np.array(w0, dtype=float)
    for _ in range(n_iter):
        w = w - eta * grad(w)
    return w


# ---------------------------------------------------------------- Exercitiul 3
def ex3_momentum(grad, w0, eta, mu, n_iter):
    """Coborare cu moment (heavy-ball)."""
    w = np.array(w0, dtype=float)
    v = np.zeros_like(w)
    for _ in range(n_iter):
        v = mu * v - eta * grad(w)
        w = w + v
    return w


# ---------------------------------------------------------------- Exercitiul 4
def ex4_best_step(A):
    """Pas optim 2/(lmax+lmin)."""
    ev = np.linalg.eigvalsh(A)
    return 2.0 / (ev[0] + ev[-1])


# ---------------------------------------------------------------- Exercitiul 5
def ex5_early_stopping(grad, value_val, w0, eta, n_iter, patience):
    """GD cu oprire timpurie pe pierderea de validare."""
    w = np.array(w0, dtype=float)
    best_w = w.copy()
    best_val = value_val(w)
    since_improve = 0
    done = 0
    for it in range(n_iter):
        done = it + 1
        w = w - eta * grad(w)
        v = value_val(w)
        if v < best_val - 1e-12:
            best_val = v
            best_w = w.copy()
            since_improve = 0
        else:
            since_improve += 1
            if since_improve >= patience:
                break
    return best_w, best_val, done


# ---------------------------------------------------------------- verificare
def _check():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    A = np.array([[3.0, 1.0], [1.0, 2.0]])
    b = np.array([1.0, -2.0])
    w_star = quadratic_solution(A, b)
    f = lambda w: quadratic_value(w, A, b)
    grad = lambda w: quadratic_grad(w, A, b)

    g_num = ex1_grad_numeric(f, np.array([0.5, -0.3]))
    ck("ex1: diferente finite == gradient analitic",
       np.linalg.norm(g_num - grad(np.array([0.5, -0.3]))) < 1e-5)

    eta = ex4_best_step(A)
    w_gd = ex2_gd(grad, np.array([5.0, 5.0]), eta, 300)
    ck("ex2: GD converge la w* = A^-1 b", np.allclose(w_gd, w_star, atol=1e-6))

    w_mom = ex3_momentum(grad, np.array([5.0, 5.0]), 0.05, 0.9, 400)
    ck("ex3: momentum converge la w*", np.allclose(w_mom, w_star, atol=1e-5))

    ev = np.linalg.eigvalsh(A)
    ck("ex4: pas optim = 2/(lmax+lmin)", abs(ex4_best_step(A) - 2.0 / (ev[0] + ev[-1])) < 1e-12)

    c = np.array([1.0, 1.0])
    d = np.array([4.0, -2.0])
    grad_tr = lambda w: 2.0 * (w - d)
    val = lambda w: float(np.sum((w - c) ** 2))
    w_best, best_val, n_done = ex5_early_stopping(grad_tr, val, np.zeros(2),
                                                  eta=0.05, n_iter=500, patience=10)
    ck("ex5: oprirea timpurie returneaza w mai aproape de optimul de validare",
       np.linalg.norm(w_best - c) < np.linalg.norm(d - c))
    ck("ex5: s-a oprit inainte de n_iter (a declansat patience)", n_done < 500)
    ck("ex5: best_val e pierderea la w_best", abs(best_val - val(w_best)) < 1e-9)

    print("\nTOATE SOLUTIILE M02 TREC: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _check()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
