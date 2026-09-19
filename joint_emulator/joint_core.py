#!/usr/bin/env python3
"""joint_core.py -- nucleul PUR al emulatorului de articulatie (fara ROS,
fara hardware): doua servomotoare cuplate rigid pe acelasi ax = o
articulatie. Motorul A actioneaza; motorul B citeste encoderul si aplica
un cuplu de opozitie dupa o lege de IMPEDANTA, ca sa tina echilibrul.

Concepte:
  ImpedanceLaw   tau_B = -K*(th - th0) - B*om  (+ clamp, deadband, rampa)
  VirtualLimb    "pacientul" emulat de motorul B: inertie+amortizare+
                 rigiditate + optional "catch" spastic (rezistenta care
                 creste brusc cu viteza -- relevant pentru reabilitare)
  PairSim        fizica perechii pe ax comun: J*th'' = tau_A + tau_B - frec
  DelayLine      intarziere de masura/comanda -- CARLIGUL TEZEI: aceeasi
                 lege de impedanta devine instabila cand bucla trece
                 printr-o legatura cu latenta (teleoperare degradata)
  EnergyMonitor  energia injectata de controler -- semnal de pasivitate
  SafetyGate     watchdog + limita de cuplu: orice dubiu => cuplu zero

Conventii: SI (rad, rad/s, Nm, s). Integrare semi-implicita (Euler).
"""
import math
from collections import deque


class ImpedanceLaw:
    def __init__(self, k_nm_rad=10.0, b_nms_rad=0.3, th0=0.0,
                 tau_max=2.0, deadband_rad=0.0, ramp_nm_s=None):
        self.k = float(k_nm_rad)
        self.b = float(b_nms_rad)
        self.th0 = float(th0)
        self.tau_max = abs(float(tau_max))
        self.deadband = abs(float(deadband_rad))
        self.ramp = ramp_nm_s          # limita de variatie a cuplului
        self._last = 0.0

    def torque(self, th, om, dt=None):
        e = th - self.th0
        if abs(e) < self.deadband:
            e = 0.0
        tau = -self.k * e - self.b * om
        tau = max(-self.tau_max, min(self.tau_max, tau))
        if self.ramp is not None and dt:
            step = self.ramp * dt
            tau = max(self._last - step, min(self._last + step, tau))
        self._last = tau
        return tau


class VirtualLimb:
    """Pacientul emulat: raspunsul B nu e doar arc-amortizor, ci membrul
    uman parametrizat. catch_om/catch_gain modeleaza rezistenta spastica:
    peste viteza-prag, amortizarea creste brusc (scala Tardieu)."""

    def __init__(self, k=4.0, b=0.2, th_rest=0.0,
                 catch_om=None, catch_gain=4.0, tau_max=2.0):
        self.k, self.b = float(k), float(b)
        self.th_rest = float(th_rest)
        self.catch_om = catch_om
        self.catch_gain = float(catch_gain)
        self.tau_max = abs(float(tau_max))

    def torque(self, th, om):
        b = self.b
        if self.catch_om is not None and abs(om) > self.catch_om:
            b = self.b * self.catch_gain
        tau = -self.k * (th - self.th_rest) - b * om
        return max(-self.tau_max, min(self.tau_max, tau))


class VirtualStopLaw:
    """Opritor virtual bilateral pe axul comun, fara senzatie de contact
    in interiorul intervalului liber. Amortizarea actioneaza numai cand
    axul patrunde mai adanc in opritor, nu cand se retrage.
    """

    def __init__(self, k=20.0, b=0.8, contact_angle_rad=0.0872665,
                 th0=0.0, tau_max=2.0):
        self.k = float(k)
        self.b = float(b)
        self.contact_angle = float(contact_angle_rad)
        self.th0 = float(th0)
        self.tau_max = float(tau_max)
        if (not all(math.isfinite(x) for x in
                    (self.k, self.b, self.contact_angle, self.th0,
                     self.tau_max)) or
                self.k < 0.0 or self.b < 0.0 or self.contact_angle < 0.0 or
                self.tau_max <= 0.0):
            raise ValueError("parametrii contactului trebuie sa fie pasivi")

    def torque(self, th, om, dt=None):
        e = float(th) - self.th0
        penetration = abs(e) - self.contact_angle
        if penetration <= 0.0:
            return 0.0
        direction = 1.0 if e > 0.0 else -1.0
        tau = -direction * self.k * penetration
        if direction * om > 0.0:
            tau -= self.b * om
        return max(-self.tau_max, min(self.tau_max, tau))


class DelayLine:
    """Intarziere fixa pe un semnal esantionat (masura sau comanda)."""

    def __init__(self, delay_s, dt, initial=0.0):
        n = max(0, int(round(delay_s / dt)))
        self.buf = deque([initial] * (n + 1), maxlen=n + 1)

    def push(self, x):
        self.buf.append(x)
        return self.buf[0]


class EnergyMonitor:
    """Energia injectata de motorul B in ax: integ(tau_B * om) dt.
    Un controler pasiv (impedanta pura, fara intarziere) doar DISIPA:
    energia ramane marginita. Cresterea nemarginita = semn de
    instabilitate (exact ce cauta experimentul cu legatura degradata).

    win_energy = energia pe ultima fereastra de window_s (margine de stabilitate
    glisanta); daca depaseste estop_energy -> estopped=True (declanseaza ESTOP).
    Parametrii au valori implicite -> backward-compatibil (EnergyMonitor() merge ca inainte)."""

    def __init__(self, window_s=1.0, estop_energy=0.5):
        self.e = 0.0
        self.e_max = 0.0
        self.window_s = float(window_s)
        self.estop_energy = float(estop_energy)
        self._win = deque()       # (t, putere_increment) pe ultima fereastra
        self._t = 0.0
        self.win_energy = 0.0
        self.estopped = False

    def step(self, tau, om, dt):
        p = tau * om * dt
        self.e += p
        self.e_max = max(self.e_max, self.e)
        self._t += dt
        self._win.append((self._t, p))
        self.win_energy += p
        while self._win and self._t - self._win[0][0] > self.window_s:
            self.win_energy -= self._win.popleft()[1]
        if self.win_energy > self.estop_energy + 1e-12:
            self.estopped = True
        return self.e

    def reset_estop(self):
        self.estopped = False


class SafetyGate:
    """Watchdog de masura + limita dura: daca encoderul tace mai mult de
    timeout, cuplul comandat devine 0 (torque-off logic)."""

    def __init__(self, timeout_s=0.1, tau_max=2.0):
        self.timeout = float(timeout_s)
        self.tau_max = abs(float(tau_max))
        self.t_last = None
        self.tripped = False

    def feed(self, t):
        self.t_last = t

    def gate(self, t, tau):
        if self.t_last is None or (t - self.t_last) > self.timeout:
            self.tripped = True
            return 0.0
        return max(-self.tau_max, min(self.tau_max, tau))


class PairSim:
    """Doua motoare pe ax comun, cuplaj rigid: o singura coordonata th.
    J*th'' = tau_A + tau_B - b_fric*om - tau_coulomb*sign(om)"""

    def __init__(self, j_kgm2=0.004, b_fric=0.01, tau_coulomb=0.0,
                 th0=0.0, om0=0.0):
        self.j = float(j_kgm2)
        self.b = float(b_fric)
        self.tc = abs(float(tau_coulomb))
        self.th, self.om = float(th0), float(om0)
        self.t = 0.0

    def step(self, tau_a, tau_b, dt):
        tau = tau_a + tau_b - self.b * self.om
        if self.om > 0:
            tau -= self.tc
        elif self.om < 0:
            tau += self.tc
        self.om += (tau / self.j) * dt
        self.th += self.om * dt
        self.t += dt
        return self.th, self.om


def simulation_substeps(rate_hz, max_step_s=0.0005):
    """Pastraza rata ROS, dar limiteaza pasul intern de fizica/control SIM."""
    rate_hz = float(rate_hz)
    max_step_s = float(max_step_s)
    if (not math.isfinite(rate_hz) or rate_hz <= 0.0 or
            not math.isfinite(max_step_s) or max_step_s <= 0.0):
        raise ValueError("rate_hz si max_step_s trebuie sa fie pozitive")
    dt = 1.0 / rate_hz
    count = max(1, math.ceil(dt / max_step_s))
    return count, dt / count


def run_equilibrium(tau_a_fn, law, dt=0.001, t_end=3.0, delay_s=0.0,
                    sim=None, monitor=None):
    """Bucla standard: A aplica tau_a_fn(t); B raspunde prin `law` pe
    masura (eventual intarziata). Intoarce (sim, monitor, urma)."""
    sim = sim or PairSim()
    monitor = monitor or EnergyMonitor()
    dl_th = DelayLine(delay_s, dt, sim.th)
    dl_om = DelayLine(delay_s, dt, sim.om)
    trace = []
    while sim.t < t_end:
        th_m = dl_th.push(sim.th)
        om_m = dl_om.push(sim.om)
        tau_b = law.torque(th_m, om_m, dt)
        tau_a = tau_a_fn(sim.t)
        sim.step(tau_a, tau_b, dt)
        monitor.step(tau_b, sim.om, dt)
        trace.append((sim.t, sim.th, sim.om, tau_a, tau_b))
    return sim, monitor, trace
