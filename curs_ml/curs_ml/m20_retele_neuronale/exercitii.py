#!/usr/bin/env python3
"""exercitii.py -- M20 Retele neuronale (STUB-URI cu TODO).

Completeaza fiecare functie marcata cu TODO. Rulat ACUM trebuie sa PICE (exit != 0).
Solutiile complete in solutii.py. Refoloseste nucleul mlp_core.

Ruleaza: /home/ubuntu/ros2_ws/.venv_ml/bin/python exercitii.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from mlp_core import MLP, _act, _numerical_grad, _rel_error  # noqa: E402
from date_sar import make_latency_dataset  # noqa: E402
from utils import standardize, rmse  # noqa: E402


# ---------------------------------------------------------------- Ex.1
def ex1_relu_si_derivata(z):
    """E1. Implementeaza ReLU si derivata ei de la zero (fara mlp_core._act).
    relu(z) = max(0, z) ; relu'(z) = 1 daca z > 0 altfel 0.
    Returneaza (relu_vals, relu_grad) ca array-uri numpy de aceeasi forma cu z.
    """
    # TODO: foloseste numpy.maximum si o comparatie booleana convertita la float
    raise NotImplementedError("E1: relu si derivata ei")


# ---------------------------------------------------------------- Ex.2
def ex2_forward_un_neuron(x, w1, b1, w2, b2):
    """E2. Un pas FORWARD de mana pe o retea minuscula: 1 intrare, 1 neuron ascuns
    cu activare tanh, 1 iesire liniara.
        z1 = x*w1 + b1 ; a1 = tanh(z1) ; z2 = a1*w2 + b2 ; y_hat = z2
    Toate argumentele sunt scalari. Returneaza y_hat (float).
    (Vezi exemplul numeric din teorie.md sectiunea 5.)
    """
    # TODO
    raise NotImplementedError("E2: forward pe un neuron")


# ---------------------------------------------------------------- Ex.3
def ex3_pierdere_scade(X, y, seed=0):
    """E3. Antreneaza un MLP de regresie (n_hidden=8, tanh, lr=0.05, n_iter=500) pe
    (X, y) si verifica daca pierderea a SCAZUT de la primul la ultimul pas.
    Returneaza (loss_primul, loss_ultimul) ca tuplu de float-uri.
    """
    # TODO: foloseste MLP(...).fit(X, y) si atributul loss_history_
    raise NotImplementedError("E3: pierderea scade")


# ---------------------------------------------------------------- Ex.4
def ex4_gradcheck_W2(seed=0):
    """E4. Verifica backprop-ul pentru W2 cu diferente finite. Construieste o retea
    mica de regresie pe date sintetice, ruleaza _forward + _backward pentru
    gradientul analitic dW2, apoi _numerical_grad(model, X, y, 'W2'), si intoarce
    eroarea relativa (_rel_error) dintre cele doua (float). Trebuie sa fie < 1e-4.
    """
    # TODO: vezi _selftest din mlp_core pentru pattern
    raise NotImplementedError("E4: gradient check pe W2")


# ---------------------------------------------------------------- Ex.5
def ex5_weight_decay_norma():
    """E5. Pe y = sin(x) sintetic, antreneaza doua MLP-uri IDENTICE (aceeasi samanta)
    care difera doar prin l2 (unul 0.0, unul 0.1). Returneaza (norma_fara_decay,
    norma_cu_decay) folosind metoda weight_norm(). Asteptare: cu decay < fara decay.
    """
    # TODO
    raise NotImplementedError("E5: weight decay micsoreaza norma")


# ---------------------------------------------------------------- Ex.6
def ex6_mlp_vs_liniar_latenta():
    """E6. Pe make_latency_dataset(n_per_cond=120, seed=1), feature-uri standardizate
    -> log10(rtt_ms), antreneaza un MLP (n_hidden=12, tanh, lr=0.05, n_iter=2000,
    seed=0) si compara RMSE-ul de antrenare cu o regresie liniara cu bias.
    Returneaza (rmse_mlp, rmse_liniar). Reflectie: pe semnal aproape liniar, MLP-ul
    isi merita complexitatea?
    """
    # TODO
    raise NotImplementedError("E6: MLP vs liniar pe latenta")


# ---------------------------------------------------------------- verificare
FEATURES = ["loss_pct", "base_lat_ms", "jitter_ms", "distance_m"]


def _check():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    z = np.array([-2.0, -0.5, 0.0, 1.5, 3.0])
    vals, grad = ex1_relu_si_derivata(z)
    ck("E1: relu(z) corect", np.allclose(vals, [0, 0, 0, 1.5, 3.0]))
    ck("E1: relu'(z) corect", np.allclose(grad, [0, 0, 0, 1, 1]))

    # forward de mana: x=0.5, w1=0.8, b1=-0.1, w2=1.2, b2=0.3
    # z1 = 0.3 ; a1 = tanh(0.3) ; y_hat = a1*1.2 + 0.3
    yh = ex2_forward_un_neuron(0.5, 0.8, -0.1, 1.2, 0.3)
    expected = np.tanh(0.5 * 0.8 - 0.1) * 1.2 + 0.3
    ck("E2: forward pe un neuron = %.6f" % expected, abs(yh - expected) < 1e-9)

    g = np.random.default_rng(0)
    Xs = g.uniform(-3, 3, (100, 1))
    ys = np.sin(Xs[:, 0])
    l0, l1 = ex3_pierdere_scade(Xs, ys, seed=0)
    ck("E3: pierderea a scazut (ultim < primul)", l1 < l0)

    err = ex4_gradcheck_W2(seed=0)
    ck("E4: gradient check W2 < 1e-4 (=%.2e)" % err, err < 1e-4)

    nf, nc = ex5_weight_decay_norma()
    ck("E5: weight decay micsoreaza norma (%.3f < %.3f)" % (nc, nf), nc < nf)

    rm, rl = ex6_mlp_vs_liniar_latenta()
    ck("E6: ambele RMSE finite si pozitive", np.isfinite(rm) and np.isfinite(rl)
       and rm > 0 and rl > 0)

    print("\nTOATE EXERCITIILE M20 REZOLVATE: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _check()
        sys.exit(0)
    except (AssertionError, NotImplementedError) as e:
        print("PICA (asteptat pana rezolvi): %s" % e)
        sys.exit(1)
