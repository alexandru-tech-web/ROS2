#!/usr/bin/env python3
"""
test_mpc.py -- validare numerica rapida a nucleului PHSC (fara ROS).

NOTA: scriptul original cerut folosea model.linearized_dynamics().
Metoda NU exista in cartpole_model.py; numele real este
linearized_matrices(). Am pastrat restul scriptului identic.
"""
import numpy as np
import _context  # noqa: F401  -- pachetul importabil si din sursa
from phsc_mechanical_analogies.cartpole_model import CartPoleModel
from phsc_mechanical_analogies.mpc_controller import MPCParams, DelayCompensatedMPC

model = CartPoleModel()
params = MPCParams(N=20, dt=0.05, u_max=100.0, tau_est=0.08,
                   Q=np.diag([10, 1, 100, 1]),
                   R=np.array([[0.01]]),
                   P=np.diag([50, 5, 500, 5]))
mpc = DelayCompensatedMPC(model, params)

x0 = np.array([0.0, 0.0, 0.1, 0.0])
x_ref = np.zeros(4)
tau_func = lambda t: 0.08

u_opt, U_seq, success = mpc.step(x0, x_ref, tau_func, 0.0)

A, B = model.linearized_matrices()
K = model.lqr_gain()
eig = np.linalg.eigvals(A - B @ K)

print(f"Control optim: {u_opt:.4f} N")
print(f"Convergenta: {success}")
print(f"Valori proprii LQR: {eig}")
print(f"Toate stabile (Re < 0): {bool(np.all(eig.real < 0))}")
print(f"Castig LQR K: {K.flatten()}")
print(f"Primele 5 comenzi din secventa: {U_seq.flatten()[:5]}")
