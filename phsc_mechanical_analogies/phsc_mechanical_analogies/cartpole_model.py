#!/usr/bin/env python3
"""
phsc_mechanical_analogies/cartpole_model.py
Model matematic pentru pendul invers pe carucior (cart-pole).
Analogie mecanica: sistem cu masa-arc-amortizor cu timp mort.

Autor: PhD Research - Predictive Haptic Shared Control
"""

import numpy as np
from typing import Callable, Tuple


class CartPoleModel:
    """
    Pendul invers pe carucior cu dinamica neliniara si linearizata.

    Stare: x = [p, p_dot, theta, theta_dot]
        p       - pozitie carucior [m]
        theta   - unghi pendul (0 = vertical sus) [rad]

    Parametri fizici (default pentru simulare Gazebo):
        M = 1.0 kg   (masa carucior)
        m = 0.1 kg   (masa pendul)
        L = 0.5 m    (lungime pendul)
        g = 9.81     (gravitatie)
        b = 0.1      (amortizare carucior)
    """

    def __init__(self, M: float = 1.0, m: float = 0.1, 
                 L: float = 0.5, g: float = 9.81, b: float = 0.1):
        self.M = M
        self.m = m
        self.L = L
        self.g = g
        self.b = b
        self.n_states = 4
        self.n_controls = 1

    def dynamics(self, x: np.ndarray, u: float) -> np.ndarray:
        """
        Dinamica neliniara: dx/dt = f(x, u)

        Args:
            x: stare [p, p_dot, theta, theta_dot]
            u: forta de control aplicata caruciorului [N]

        Returns:
            dx: derivata starii
        """
        p, p_dot, theta, theta_dot = x

        sin_theta = np.sin(theta)
        cos_theta = np.cos(theta)

        # Denominator din ecuatiile Lagrange
        denom = self.M + self.m - self.m * cos_theta**2

        # Accelerare carucior
        p_ddot = (u - self.b * p_dot + 
                  self.m * self.L * theta_dot**2 * sin_theta - 
                  self.m * self.g * sin_theta * cos_theta) / denom

        # Accelerare unghiulara pendul
        theta_ddot = (self.g * sin_theta - cos_theta * p_ddot) / self.L

        return np.array([p_dot, p_ddot, theta_dot, theta_ddot])

    def dynamics_rk4(self, x: np.ndarray, u: float, dt: float) -> np.ndarray:
        """Integrare Runge-Kutta 4 pentru un pas dt."""
        k1 = self.dynamics(x, u)
        k2 = self.dynamics(x + 0.5 * dt * k1, u)
        k3 = self.dynamics(x + 0.5 * dt * k2, u)
        k4 = self.dynamics(x + dt * k3, u)
        return x + (dt / 6.0) * (k1 + 2*k2 + 2*k3 + k4)

    def linearized_matrices(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Linearizare in jurul punctului de echilibru instabil (theta=0).
        Returneaza matricile A, B pentru: dx/dt = A*x + B*u
        """
        M, m, L, g, b = self.M, self.m, self.L, self.g, self.b

        A = np.array([
            [0, 1, 0, 0],
            [0, -b/M, -m*g/M, 0],
            [0, 0, 0, 1],
            # A[3][3] = 0: theta_ddot linearizat NU depinde de theta_dot.
            # (b este amortizarea CARUCIORULUI; intra doar prin p_ddot, deci
            # doar in A[3][1] = +b/(M*L). Un termen -b/(M*L) pe theta_dot ar fi
            # amortizare fictiva pe pendul -- verificat cu Jacobian numeric.)
            [0, b/(M*L), g*(M+m)/(M*L), 0]
        ])

        B = np.array([[0], [1/M], [0], [-1/(M*L)]])

        return A, B

    def lqr_gain(self, Q: np.ndarray = None, R: np.ndarray = None) -> np.ndarray:
        """
        Proiectare controller LQR pentru sistemul linearizat.

        Args:
            Q: matrice de penalizare stare (default: diag([10, 1, 100, 1]))
            R: matrice de penalizare control (default: [[0.1]])

        Returns:
            K: matrice de feedback LQR [1 x 4]
        """
        from scipy.linalg import solve_continuous_are

        A, B = self.linearized_matrices()

        if Q is None:
            Q = np.diag([10.0, 1.0, 100.0, 1.0])
        if R is None:
            R = np.array([[0.1]])

        P = solve_continuous_are(A, B, Q, R)
        K = np.linalg.inv(R) @ B.T @ P
        return K.reshape(1, -1)

    def predict_state_openloop(self, x0: np.ndarray, u_seq: np.ndarray, 
                                dt: float, n_steps: int = None) -> np.ndarray:
        """
        Predictie de stare in bucla deschisa folosind RK4.

        Args:
            x0: stare initiala
            u_seq: secventa de control (sau scalar pentru control constant)
            dt: pas de discretizare
            n_steps: numar de pasi (daca u_seq e scalar, se repeta)

        Returns:
            x_final: starea prezisa
        """
        if np.isscalar(u_seq):
            u_seq = np.full(n_steps if n_steps else int(1.0/dt), u_seq)

        x = x0.copy()
        for u in u_seq:
            x = self.dynamics_rk4(x, u, dt)
        return x


    def predict_state_delay(self, x0: np.ndarray, u, tau: float,
                            n_steps: int = 20) -> np.ndarray:
        """
        Predictie de stare pe durata latentei tau (API cerut in runda 2).

        Propagare RK4 cu pas dt_pred = tau / n_steps, deci acopera EXACT tau,
        indiferent de raportul dintre tau si dt-ul controllerului.

        Args:
            x0: stare masurata
            u: fie un scalar (comanda tinuta pe toata fereastra), fie un
               callable u(t_relativ) care intoarce comanda IN ZBOR la acel
               moment din fereastra. Varianta callable e cea corecta fizic --
               vezi nota de mai jos.
            tau: latenta [s]
            n_steps: sub-pasi de integrare

        NOTA IMPORTANTA (masurat in runda 2): daca predictia presupune u=0 pe
        fereastra, compensarea e MAI REA decat lipsa ei (cadere la 0.70 s vs
        0.81 s). Cu comenzile reale in zbor, aceeasi bucla ramane stabila
        pana la ~150 ms latenta. Deci nu conteaza doar CA prezici, ci CU CE.
        """
        if tau <= 0:
            return np.asarray(x0, dtype=float).copy()

        n_steps = max(1, int(n_steps))
        dt_pred = tau / n_steps
        x = np.asarray(x0, dtype=float).copy()

        for i in range(n_steps):
            u_i = u(i * dt_pred) if callable(u) else float(u)
            x = self.dynamics_rk4(x, u_i, dt_pred)
        return x


    @staticmethod
    def interp_control(control_buffer, t: float) -> float:
        """
        Comanda emisa la momentul t, citita din bufferul (t_i, u_i).

        Interpolare liniara, cu clamp la capete: inainte de prima comanda
        canalul e gol (0.0), dupa ultima se tine ultima valoare.
        """
        if not control_buffer:
            return 0.0
        if t <= control_buffer[0][0]:
            return 0.0
        if t >= control_buffer[-1][0]:
            return float(control_buffer[-1][1])
        times = [c[0] for c in control_buffer]
        controls = [c[1] for c in control_buffer]
        return float(np.interp(t, times, controls))

    def predict_state_smith(self, x0: np.ndarray, tau: float,
                            control_buffer, t_current: float,
                            n_steps: int = 20) -> np.ndarray:
        """
        Predictie Smith reala: propaga starea masurata cu tau inainte,
        folosind comenzile DIN BUFFER (cele deja emise si inca in zbor pe
        canal), nu o comanda fictiva tinuta constant.

        La pasul k, planta este actionata de comanda emisa la
        (t_current + k*dt_pred) - tau, pentru ca aceea ajunge atunci.

        MASURAT (runda 2, bucla inchisa, tau=80+/-20 ms): cu u=0 presupus pe
        fereastra, bucla CADE la 0.70 s -- mai rau decat fara compensare
        (0.81 s). Cu comenzile reale din buffer, ramane STABILA pana la
        ~150 ms latenta. Deci ce anume prezici conteaza mai mult decat faptul
        ca prezici.
        """
        if tau <= 0:
            return np.asarray(x0, dtype=float).copy()

        n_steps = max(1, int(n_steps))
        dt_pred = tau / n_steps
        x = np.asarray(x0, dtype=float).copy()

        for k in range(n_steps):
            t_k = t_current + k * dt_pred
            u_k = self.interp_control(control_buffer, t_k - tau)
            x = self.dynamics_rk4(x, u_k, dt_pred)
        return x


class DelayedCartPole(CartPoleModel):
    """
    Extensie cu latenta variabila in canalul de control.

    Analogie mecanica: sistem cu amortizor cu timp mort.
    Comanda u(t) ajunge la sistem ca u(t - tau(t)).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.control_history = []  # [(t, u), ...] comenzi emise pe canal

    def get_delayed_control(self, t: float, tau: float) -> float:
        """Obtine controlul aplicat la timpul t - tau din istoric."""
        if not self.control_history or t - tau <= self.control_history[0][0]:
            return 0.0

        target_t = t - tau
        # Interpolare liniara
        times = np.array([entry[0] for entry in self.control_history])
        controls = np.array([entry[1] for entry in self.control_history])

        return np.interp(target_t, times, controls)

    def simulate_step(self, x: np.ndarray, t: float, u: float, 
                      tau_func: Callable[[float], float], dt: float) -> np.ndarray:
        """
        Simuleaza un pas cu latenta variabila.

        Args:
            x: stare curenta
            t: timp curent
            u: control comandat acum (va fi aplicat cu delay)
            tau_func: functie tau(t) care returneaza latenta
            dt: pas de simulare
        """
        tau = tau_func(t)
        u_delayed = self.get_delayed_control(t, tau)

        # Salvam controlul comandat in istoric
        self.control_history.append((t, u))

        # Integrare dinamica reala cu control intarziat
        return self.dynamics_rk4(x, u_delayed, dt)

    def reset_history(self) -> None:
        """Resetare buffer istoric."""
        self.control_history = []


if __name__ == "__main__":
    # Test rapid
    model = CartPoleModel()
    A, B = model.linearized_matrices()
    K = model.lqr_gain()
    print("[Test cartpole_model.py]")
    print(f"A[3][3] = {A[3][3]} (asteptat: 0.0)")
    print(f"A shape: {A.shape}, B shape: {B.shape}")
    print(f"LQR K: {K.flatten()}")
    eig = np.linalg.eigvals(A - B @ K)
    print(f"Valori proprii LQR: {eig}")
    print(f"Toate stabile (Re < 0): {bool(np.all(eig.real < 0))}")

    x0 = np.array([0.0, 0.0, 0.1, 0.0])
    x_pred = model.predict_state_openloop(x0, 0.0, 0.01, 100)
    print(f"Predictie 1s fara control: theta = {np.degrees(x_pred[2]):.2f} grade")
