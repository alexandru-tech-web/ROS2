#!/usr/bin/env python3
"""
phsc_teleop_mpc/mpc_controller.py
MPC Neliniar pentru teleoperare cu latenta variabila.

Formulare:
    min   sum_{k=0}^{N-1} ||x_k - x_ref||_Q^2 + ||u_k||_R^2 + ||Delta u_k||_Rdu^2
          + ||x_N - x_ref||_P^2
    s.t.  x_{k+1} = f_RK4(x_k, u_k, dt)           [dinamica neliniara]
          u_min <= u_k <= u_max                      [constrangere control]
          |theta_k| <= theta_max                     [constrangere stare]
          x_0 = x_current (sau x_predicted cu delay)

Delay compensation:
    - x_0 = predict_state(x_measured, u_prev, tau_est, dt)
    - Predictie RK4 pe modelul neliniar pe durata tau_est

Autor: PhD Research - Predictive Haptic Shared Control
"""

import time

import numpy as np
from scipy.optimize import minimize
from typing import Callable, Optional, Tuple
from dataclasses import dataclass


@dataclass
class MPCParams:
    """Parametri de tuning MPC."""
    N: int = 20              # orizont de predictie
    dt: float = 0.05         # pas de discretizare [s]
    u_max: float = 50.0      # limita control [N]
    theta_max: float = 0.5   # limita unghi [rad] (~28 grade)

    # Matrici de cost
    Q: np.ndarray = None     # cost stare
    R: np.ndarray = None     # cost control
    R_du: np.ndarray = None  # cost variatie control (smoothness)
    P: np.ndarray = None     # cost terminal

    # Delay
    tau_est: float = 0.1     # latenta estimata [s]
    tau_var: float = 0.02    # variatie latenta [s]

    # Solver (erau hardcodate in solve(); acum configurabile)
    max_iter: int = 200
    ftol: float = 1e-6
    n_pred: int = 20         # sub-pasi de integrare pe fereastra de latenta
    # Cum se impune |theta_k| <= theta_max:
    #   'hard' -- NonlinearConstraint SLSQP: exact, dar ~2x timp de solve
    #             (cere un rollout separat la fiecare evaluare de constrangere)
    #   'soft' -- penalizare patratica in cost: aproape gratis (refoloseste
    #             rollout-ul existent), dar nu garanteaza respectarea limitei
    #   'none' -- neimpus (comportamentul initial)
    theta_mode: str = 'hard'
    theta_penalty_w: float = 1.0e6

    def __post_init__(self):
        if self.Q is None:
            self.Q = np.diag([10.0, 1.0, 100.0, 1.0])
        if self.R is None:
            self.R = np.array([[1.0]])
        if self.R_du is None:
            self.R_du = np.array([[0.5]])
        if self.P is None:
            self.P = np.diag([20.0, 2.0, 200.0, 2.0])


class MPCController:
    """
    MPC Neliniar pentru pendul invers cu compensare de delay.

    Analogie mecanica: "arcul virtual" de control se intinde
    in viitor pentru a compensa "amortizorul" de delay.
    """

    def __init__(self, model, params: MPCParams = None):
        """
        Args:
            model: instanta CartPoleModel (sau similar)
            params: MPCParams cu tuning
        """
        self.model = model
        self.params = params if params else MPCParams()
        self.nx = model.n_states
        self.nu = model.n_controls

        # Buffer pentru control anterior (pentru cost Delta-u)
        self.u_prev = 0.0

        # Statistici solver.
        # solve_times = SECUNDE reale de wall-clock (inainte contineau
        # result.nit, adica numar de iteratii -- orice cifra de latenta
        # derivata din ele era falsa).
        self.solve_times = []
        self.solve_iters = []
        self.solve_success = []
        self.solve_taus = []

    def predict_state_delay(self, x_measured: np.ndarray, 
                            u_prev_seq: np.ndarray,
                            tau: float) -> np.ndarray:
        """
        Predictie de stare pe durata latentei tau.
        Propaga x_measured prin dinamica neliniara cu controlul anterior.

        Args:
            x_measured: stare masurata la timpul t
            u_prev_seq: secventa de control anterioara (sau scalar)
            tau: latenta estimata [s]

        Returns:
            x_pred: starea prezisa la t + tau (ceea ce "va vedea" robotul)
        """
        tau = max(0.0, float(tau))
        if tau <= 0.0:
            return np.asarray(x_measured, dtype=float).copy()

        # Orizontul trebuie sa acopere EXACT tau. Varianta initiala folosea
        # n = int(tau/dt): cu tau=0.08 si dt=0.05 propaga doar 0.05 s, adica
        # sub-compensare de 37.5% fix pe variabila centrala a lucrarii.
        # Acum sub-esantionam fereastra in n_pred pasi de tau/n_pred.
        n_pred = self.params.n_pred

        if callable(u_prev_seq):
            u_arg = u_prev_seq
        elif np.isscalar(u_prev_seq):
            u_arg = float(u_prev_seq)
        else:
            seq = np.atleast_1d(u_prev_seq)
            dt_pred = tau / n_pred
            # esantionam secventa data de-a lungul ferestrei
            u_arg = lambda dtr, s=seq, d=dt_pred: float(
                s[min(int(dtr / d), len(s) - 1)])

        return self.model.predict_state_delay(x_measured, u_arg, tau, n_pred)

    def _cost_function(self, U_flat: np.ndarray, x0: np.ndarray, 
                       x_ref: np.ndarray) -> float:
        """
        Functie cost pentru optimizare.
        U_flat = [u_0, u_1, ..., u_{N-1}] (vector 1D)
        """
        N = self.params.N
        Q = self.params.Q
        R = self.params.R
        R_du = self.params.R_du
        P = self.params.P
        dt = self.params.dt
        soft_theta = (self.params.theta_mode == 'soft')
        theta_max = self.params.theta_max

        U = U_flat.reshape(N, self.nu)
        cost = 0.0
        x = x0.copy()

        for k in range(N):
            u = U[k]

            # Cost stare
            e = x - x_ref
            cost += e.T @ Q @ e

            # Cost control
            cost += u.T @ R @ u

            # Cost variatie control (smoothness)
            if k == 0:
                du = u - self.u_prev
            else:
                du = u - U[k-1]
            cost += du.T @ R_du @ du

            # Propagare dinamica
            x = self.model.dynamics_rk4(x, u[0], dt)

            # Constrangere de stare in varianta 'soft': se evalueaza pe starea
            # DUPA propagare (x_{k+1}), refolosind rollout-ul deja facut aici,
            # deci nu costa aproape nimic in plus.
            if soft_theta:
                viol = abs(x[2]) - theta_max
                if viol > 0.0:
                    cost += self.params.theta_penalty_w * viol * viol

        # Cost terminal
        e_N = x - x_ref
        cost += e_N.T @ P @ e_N

        return float(cost)

    def _theta_margin(self, U_flat: np.ndarray, x0: np.ndarray) -> np.ndarray:
        """
        Constrangerea de stare din formulare: |theta_k| <= theta_max.

        Intoarce vectorul theta_max - |theta_k| pentru k=1..N; SLSQP cere
        ca fiecare componenta sa fie >= 0 (tip 'ineq').

        Inainte exista `_constraints()`, care doar reconstruia bounds-urile de
        control si NU era apelata NICIODATA -- deci constrangerea de stare
        promisa in docstring-ul modulului nu era impusa nicaieri.
        """
        N = self.params.N
        dt = self.params.dt
        U = U_flat.reshape(N, self.nu)

        x = x0.copy()
        margins = np.empty(N)
        for k in range(N):
            x = self.model.dynamics_rk4(x, U[k][0], dt)
            margins[k] = self.params.theta_max - abs(x[2])
        return margins

    def solve(self, x0: np.ndarray, x_ref: np.ndarray, 
              u_init: Optional[np.ndarray] = None,
              tau_current: float = None) -> Tuple[float, np.ndarray, bool]:
        """
        Rezolva problema MPC.

        Args:
            x0: stare curenta (deja compensata pentru delay, sau bruta)
            x_ref: referinta de stare
            u_init: initializare control (warm start)
            tau_current: latenta curenta (pentru logging)

        Returns:
            u_opt: primul control optim
            U_seq: secventa completa de control
            success: flag de convergenta
        """
        N = self.params.N

        # Initializare
        if u_init is None:
            U0 = np.zeros(N * self.nu)
        else:
            U0 = u_init.flatten()

        # Bounds
        bounds = [(-self.params.u_max, self.params.u_max)] * (N * self.nu)

        # Constrangerea de stare, acum impusa efectiv (era cod mort)
        constraints = ()
        if self.params.theta_mode == 'hard':
            constraints = ({'type': 'ineq',
                            'fun': self._theta_margin,
                            'args': (x0,)},)

        # Optimizare
        t_solve0 = time.perf_counter()
        result = minimize(
            fun=self._cost_function,
            x0=U0,
            args=(x0, x_ref),
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={
                'maxiter': self.params.max_iter,
                'ftol': self.params.ftol,
                'disp': False
            }
        )
        dt_solve = time.perf_counter() - t_solve0

        success = result.success
        U_seq = result.x.reshape(N, self.nu)
        u_opt = float(U_seq[0, 0])

        # Salvare statistici (timp REAL, plus iteratiile separat).
        # tau_current era primit si aruncat; il pastram, ca sa se poata corela
        # timpul de solve cu latenta la care a fost cerut -- utile in teza.
        self.solve_times.append(dt_solve)
        self.solve_iters.append(result.nit)
        self.solve_success.append(success)
        self.solve_taus.append(tau_current)

        # Update u_prev pentru cost Delta-u la urmatorul pas
        self.u_prev = u_opt

        return u_opt, U_seq, success

    def compute_haptic_feedback(self, x_pred: np.ndarray, 
                                 x_ref: np.ndarray,
                                 x_actual: np.ndarray) -> np.ndarray:
        """
        Generare feedback haptic bazat pe "tensiunea mecanica"
        a erorii de predictie.

        Analogie: un arc virtual conecteaza starea prezisa de cea reala.
        Forta haptica = -K_h * (x_pred - x_actual) - D_h * d/dt(error)

        Returns:
            force: vector forta haptica [Fx, Fy, Fz, Tx, Ty, Tz]
                   (simplificat la 2 DOF pentru cart-pole)
        """
        # Rigiditate si amortizare virtuala (analogie masa-arc-amortizor)
        K_h = np.diag([10.0, 0.0, 50.0, 0.0])   # rigiditate pe p si theta
        D_h = np.diag([2.0, 0.0, 5.0, 0.0])      # amortizare

        error = x_pred - x_actual
        # Derivata erorii aproximata (simplificat)
        force_4d = -K_h @ error

        # Mapare la Twist 6D pentru ROS
        force_6d = np.zeros(6)
        force_6d[0] = force_4d[0]   # Fx ~ pozitie carucior
        force_6d[5] = force_4d[2]   # Tz ~ unghi pendul

        return force_6d

    def reset(self):
        """Resetare stare interna."""
        self.u_prev = 0.0
        self.solve_times = []
        self.solve_iters = []
        self.solve_success = []
        self.solve_taus = []


class DelayCompensatedMPC(MPCController):
    """
    MPC cu compensare explicita de delay prin predictie de stare.

    Arhitectura:
        1. Masoara x(t)
        2. Predictie: x_pred = predict_state(x(t), u_hist, tau_est)
        3. MPC: optimizeaza U pe orizont N pornind de la x_pred
        4. Aplica u_0 (va ajunge la robot la t + tau)
    """

    def __init__(self, model, params: MPCParams = None):
        super().__init__(model, params)
        self.control_buffer = []  # istoric (t, u) al comenzilor emise
        self._U_prev = None       # initializat explicit (nu prin hasattr)
        # cate comenzi pastram: acopera latente pana la ~2 s la 20 Hz
        self.buffer_max = 200

    def reset(self):
        """Resetare completa, inclusiv warm start si istoricul de comenzi."""
        super().reset()
        self.control_buffer = []
        self._U_prev = None

    def step(self, x_measured: np.ndarray, x_ref: np.ndarray,
             tau_func: Callable[[float], float], t: float) -> Tuple[float, np.ndarray, bool]:
        """
        Pas complet MPC cu compensare de delay.

        Args:
            x_measured: stare masurata la timpul t
            x_ref: referinta
            tau_func: functie tau(t) pentru latenta variabila
            t: timp curent

        Returns:
            u_opt, U_seq, success
        """
        tau = tau_func(t)

        # Compensare delay: predictie stare la t + tau folosind comenzile
        # IN ZBOR (emise, dar inca neajunse la planta).
        #
        # Varianta veche folosea un singur scalar (self.u_prev) tinut pe toata
        # fereastra, iar control_buffer era scris si niciodata citit. Masurat
        # in runda 2 pe bucla inchisa: o predictie care presupune comanda
        # gresita pe fereastra e MAI REA decat lipsa compensarii (cadere la
        # 0.70 s vs 0.81 s); cu comenzile reale in zbor, bucla ramane stabila
        # pana la ~150 ms latenta. Aici e miezul contributiei stiintifice.
        x_pred = self.model.predict_state_smith(
            x_measured, tau, self.control_buffer, t, self.params.n_pred)

        # Warm start: shift secventa anterioara
        u_init = None
        if hasattr(self, '_U_prev') and self._U_prev is not None:
            u_init = np.roll(self._U_prev, -1, axis=0)
            u_init[-1] = u_init[-2]  # hold last

        # Rezolvare MPC
        u_opt, U_seq, success = self.solve(x_pred, x_ref, u_init, tau)

        # Salvare pentru warm start
        self._U_prev = U_seq.copy()
        self.control_buffer.append((t, u_opt))
        # buffer marginit: altfel creste nelimitat pe durata procesului
        if len(self.control_buffer) > self.buffer_max:
            del self.control_buffer[:-self.buffer_max]

        return u_opt, U_seq, success


if __name__ == "__main__":
    from cartpole_model import CartPoleModel

    print("[Test mpc_controller.py]")
    model = CartPoleModel()

    # Parametri MPC
    params = MPCParams(N=15, dt=0.05, u_max=30.0, tau_est=0.08)
    mpc = DelayCompensatedMPC(model, params)

    # Test pas MPC
    x0 = np.array([0.0, 0.0, 0.1, 0.0])
    x_ref = np.array([0.0, 0.0, 0.0, 0.0])
    tau_func = lambda t: 0.05 + 0.02 * np.sin(2*t)

    u_opt, U_seq, success = mpc.step(x0, x_ref, tau_func, 0.0)
    print(f"Control optim: {u_opt:.4f} N")
    print(f"Convergenta: {success}")
    print(f"Secventa control: {U_seq.flatten()[:5]}")
