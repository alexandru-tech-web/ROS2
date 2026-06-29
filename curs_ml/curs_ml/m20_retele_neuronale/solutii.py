#!/usr/bin/env python3
"""solutii.py -- M20 Retele neuronale (SOLUTIILE complete). Ruleaza -> exit 0."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from mlp_core import MLP, _numerical_grad, _rel_error  # noqa: E402
from date_sar import make_latency_dataset  # noqa: E402
from utils import standardize, add_bias, rmse  # noqa: E402

FEATURES = ["loss_pct", "base_lat_ms", "jitter_ms", "distance_m"]


def ex1_relu_si_derivata(z):
    z = np.asarray(z, dtype=float)
    vals = np.maximum(0.0, z)
    grad = (z > 0.0).astype(float)
    return vals, grad


def ex2_forward_un_neuron(x, w1, b1, w2, b2):
    z1 = x * w1 + b1
    a1 = np.tanh(z1)
    z2 = a1 * w2 + b2
    return float(z2)


def ex3_pierdere_scade(X, y, seed=0):
    m = MLP(n_hidden=8, activation="tanh", lr=0.05, n_iter=500, seed=seed).fit(X, y)
    return float(m.loss_history_[0]), float(m.loss_history_[-1])


def ex4_gradcheck_W2(seed=0):
    g = np.random.default_rng(seed)
    X = g.standard_normal((8, 3))
    y = g.standard_normal(8)
    m = MLP(n_hidden=5, activation="tanh", l2=0.01, seed=seed)
    m._init_params(X.shape[1])
    _, cache = m._forward(X)
    _, _, dW2, _ = m._backward(cache, y)
    num = _numerical_grad(m, X, y, "W2").reshape(dW2.shape)
    return _rel_error(dW2, num)


def ex5_weight_decay_norma():
    g = np.random.default_rng(0)
    X = g.uniform(-3, 3, (120, 1))
    y = np.sin(X[:, 0])
    base = MLP(n_hidden=16, activation="tanh", lr=0.05, l2=0.0,
               n_iter=2000, seed=7).fit(X, y)
    reg = MLP(n_hidden=16, activation="tanh", lr=0.05, l2=0.1,
              n_iter=2000, seed=7).fit(X, y)
    return base.weight_norm(), reg.weight_norm()


def ex6_mlp_vs_liniar_latenta():
    df = make_latency_dataset(n_per_cond=120, seed=1)
    X = df[FEATURES].to_numpy(dtype=float)
    y = np.log10(df["rtt_ms"].to_numpy(dtype=float))
    Xs, _, _, _ = standardize(X)
    mlp = MLP(n_hidden=12, activation="tanh", lr=0.05, n_iter=2000, seed=0).fit(Xs, y)
    rmse_mlp = rmse(y, mlp.predict(Xs))
    Phi = add_bias(Xs)
    w, *_ = np.linalg.lstsq(Phi, y, rcond=None)
    rmse_lin = rmse(y, Phi @ w)
    return float(rmse_mlp), float(rmse_lin)


def _check():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    z = np.array([-2.0, -0.5, 0.0, 1.5, 3.0])
    vals, grad = ex1_relu_si_derivata(z)
    ck("E1: relu corect", np.allclose(vals, [0, 0, 0, 1.5, 3.0]))
    ck("E1: relu' corect", np.allclose(grad, [0, 0, 0, 1, 1]))

    yh = ex2_forward_un_neuron(0.5, 0.8, -0.1, 1.2, 0.3)
    expected = np.tanh(0.5 * 0.8 - 0.1) * 1.2 + 0.3
    ck("E2: forward un neuron", abs(yh - expected) < 1e-9)

    g = np.random.default_rng(0)
    Xs = g.uniform(-3, 3, (100, 1))
    ys = np.sin(Xs[:, 0])
    l0, l1 = ex3_pierdere_scade(Xs, ys, seed=0)
    ck("E3: pierderea scade", l1 < l0)

    err = ex4_gradcheck_W2(seed=0)
    ck("E4: gradient check W2 < 1e-4", err < 1e-4)

    nf, nc = ex5_weight_decay_norma()
    ck("E5: weight decay micsoreaza norma", nc < nf)

    rm, rl = ex6_mlp_vs_liniar_latenta()
    ck("E6: RMSE-uri finite pozitive", np.isfinite(rm) and np.isfinite(rl)
       and rm > 0 and rl > 0)

    print("\nTOATE SOLUTIILE M20 TREC: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _check()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
