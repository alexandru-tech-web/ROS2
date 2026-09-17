#!/usr/bin/env python3
"""rover_dyn.py -- nucleul PUR al gardei de siguranta C6. Fara ROS, fara retea.

MODEL: uniciclu cu doua limitari care conteaza pentru o garda de siguranta.

  1. LIMITA DE ACCELERATIE (a_max): comanda nu se aplica instantaneu.
  2. INTARZIERE DE ACTUATOR (tau_act): chiar si sub a_max, viteza reala urmareste
     comanda cu o intarziere de ordinul intai, dv/dt = (v_cmd - v) / tau_act.

Cele doua se compun: rata ceruta de intarziere se TAIE la a_max. Un model care ar
avea doar a_max ar prezice o oprire mai scurta decat cea reala, iar o garda
construita pe el ar lasa roverul sa intre in obstacol.

DISTANTA DE FRANARE, d_fr(v) = v * tau_act + v^2 / (2 * a_max)
  Primul termen: drumul facut cat timp actuatorul inca nu a raspuns.
  Al doilea: franarea propriu-zisa la a_max.
Este o margine SUPERIOARA, nu o predictie exacta: intarzierea de ordinul intai
incepe sa franeze imediat, nu dupa tau_act. Pentru o garda, eroarea trebuie sa
fie in partea asta.

Starea si comanda sunt tupluri simple, iar `step` NU muta starea primita: se
intoarce una noua. Asa un apelant poate explora mai multe comenzi din aceeasi
stare fara sa o strice.

Rulare: python3 rover_dyn.py --selftest
"""
import math
import sys

# --- parametri de model (C6, etapa 0) ------------------------------------
DT = 0.05            # s, pasul de integrare
A_MAX = 1.0          # m/s^2, acceleratie si deceleratie maxime
TAU_ACT = 0.2        # s, constanta de timp a actuatorului
V_MAX = 1.0          # m/s
OMEGA_MAX = 1.5      # rad/s

V_OPRIT = 1e-3       # m/s, sub asta consideram roverul oprit


class Stare(object):
    """Pozitie, orientare si vitezele REALE (nu cele comandate)."""

    __slots__ = ("x", "y", "theta", "v", "omega")

    def __init__(self, x=0.0, y=0.0, theta=0.0, v=0.0, omega=0.0):
        self.x = float(x)
        self.y = float(y)
        self.theta = float(theta)
        self.v = float(v)
        self.omega = float(omega)

    def __repr__(self):
        return ("Stare(x=%.4f, y=%.4f, theta=%.4f, v=%.4f, omega=%.4f)"
                % (self.x, self.y, self.theta, self.v, self.omega))


def satureaza(x, limita):
    return max(-limita, min(limita, x))


def d_fr(v, a_max=A_MAX, tau_act=TAU_ACT):
    """Distanta de franare de la viteza v: drumul din intarziere plus franarea.

    Margine SUPERIOARA. Negativ tratat ca modul: distanta nu are semn."""
    v = abs(float(v))
    return v * tau_act + (v * v) / (2.0 * a_max)


def step(state, cmd, dt=DT, tau_act=None):
    """Un pas. Intoarce o stare NOUA; nu o modifica pe cea primita.

    IMPLICIT (tau_act=None): EXACT modelul F din nota matematica M0, sec. 1:
        p_{k+1}     = p_k + dt * v_k * (cos th_k, sin th_k)     (Euler explicit, cu v_k)
        th_{k+1}    = th_k + dt * omega_k
        v_{k+1}     = v_k + clamp(v_cmd - v_k, -a_max dt, +a_max dt)
    Intarzierea de actuator NU e in dinamica: intra ca MARJA, prin d_fr(v).
    Asa filtrul CBF (liniarizat pe F) si certificatul M1 (x_{k+1} == F) vorbesc
    despre acelasi obiect.

    OPTIONAL (tau_act dat): intarziere de ordinul intai, taiata la a_max --
    plantul "mai real" din S0. Pastrat pentru teste de robustete; NU e modelul
    pe care se face teoria, si asta e o limita declarata (M0 sec. 7)."""
    v_cmd, omega_cmd = float(cmd[0]), float(cmd[1])
    v_cmd = satureaza(v_cmd, V_MAX)
    omega = satureaza(omega_cmd, OMEGA_MAX)

    if tau_act is None:
        dv = satureaza(v_cmd - state.v, A_MAX * dt)
    else:
        dv = satureaza((v_cmd - state.v) / tau_act, A_MAX) * dt
    v_nou = state.v + dv

    # pozitia cu v_k si th_k (Euler explicit), exact ca F
    return Stare(x=state.x + state.v * math.cos(state.theta) * dt,
                 y=state.y + state.v * math.sin(state.theta) * dt,
                 theta=state.theta + omega * dt,
                 v=v_nou, omega=omega)


# --- selftest ------------------------------------------------------------
def _distanta(a, b):
    return math.hypot(b.x - a.x, b.y - a.y)


def _selftest():
    n = 0

    # (a) v constant -> distanta = v * t, in 1%
    #     Pornim DEJA la viteza ceruta: altfel masuram intarzierea, nu regimul.
    v = 0.8
    t_total = 3.0
    s = Stare(v=v)
    plecare = Stare(x=s.x, y=s.y)
    for _ in range(int(round(t_total / DT))):
        s = step(s, (v, 0.0))
    d = _distanta(plecare, s)
    astept = v * t_total
    err = abs(d - astept) / astept
    assert err <= 0.01, "(a) distanta %.4f vs %.4f, eroare %.2f%%" % (d, astept, 100 * err)
    print("  (a) v constant %.1f m/s, %.1f s: %.4f m, asteptat %.4f m, eroare %.3f%%"
          % (v, t_total, d, astept, 100 * err))
    n += 1

    # (b) franare de la V_MAX -> oprire in cel mult d_fr(V_MAX) + 0.1 m
    s = Stare(v=V_MAX)
    plecare = Stare(x=s.x, y=s.y)
    limita = d_fr(V_MAX) + 0.1
    t = 0.0
    while s.v > V_OPRIT and t < 20.0:
        s = step(s, (0.0, 0.0))
        t += DT
    assert s.v <= V_OPRIT, "(b) nu s-a oprit in 20 s: v=%.6f" % s.v
    d = _distanta(plecare, s)
    assert d <= limita, "(b) oprire in %.4f m, limita %.4f m" % (d, limita)
    print("  (b) franare de la %.1f m/s: oprit in %.4f m dupa %.2f s; d_fr=%.4f, limita %.4f"
          % (V_MAX, d, t, d_fr(V_MAX), limita))
    n += 1

    # (c) OMEGA_MAX respectat, chiar cerut mult peste
    s = Stare()
    om_max_vazut = 0.0
    for _ in range(200):
        s = step(s, (0.0, 10.0 * OMEGA_MAX))
        om_max_vazut = max(om_max_vazut, abs(s.omega))
    assert om_max_vazut <= OMEGA_MAX + 1e-12, "(c) omega %.6f > %.6f" % (om_max_vazut, OMEGA_MAX)
    # si in sens negativ, ca sa nu treaca un model care satureaza doar pe o parte
    s = Stare()
    om_min_vazut = 0.0
    for _ in range(200):
        s = step(s, (0.0, -10.0 * OMEGA_MAX))
        om_min_vazut = min(om_min_vazut, s.omega)
    assert om_min_vazut >= -OMEGA_MAX - 1e-12, "(c) omega %.6f < -%.6f" % (om_min_vazut, OMEGA_MAX)
    print("  (c) omega cerut %.1f rad/s: atins %.4f / %.4f, limita %.1f"
          % (10.0 * OMEGA_MAX, om_max_vazut, om_min_vazut, OMEGA_MAX))
    n += 1

    # (d) `step` nu muta starea primita -- proprietatea pe care se bazeaza apelantii
    s0 = Stare(x=1.0, v=0.5)
    _ = step(s0, (1.0, 1.0))
    assert (s0.x, s0.v) == (1.0, 0.5), "(d) step a modificat starea primita"
    print("  (d) step nu modifica starea primita")
    n += 1

    print("SELFTEST rover_dyn OK (%d verificari)." % n)
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    print(__doc__.splitlines()[0])
    print("Foloseste --selftest.")
