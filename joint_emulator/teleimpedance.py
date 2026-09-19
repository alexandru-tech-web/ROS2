#!/usr/bin/env python3
"""teleimpedance.py -- stratul de TELE-impedanta al emulatorului:
masura encoderului trece printr-o legatura degradata (aceeasi schema
{ms, jit, loss, down} ca in tot repo-ul), iar legea de impedanta se
poate ADAPTA la calitatea legaturii -- intrebarea de cercetare a
bancului: K scade si B creste cand masura imbatraneste, ca bucla sa
ramana stabila acolo unde impedanta fixa explodeaza.
"""
import math
import random

from joint_core import ImpedanceLaw


class DegradedMeasure:
    """Canal de masura cu latenta/jitter/pierdere/cadere. push() la
    fiecare esantion (t, th, om); latest(t_now) intoarce ultimul esantion
    LIVRAT pana la t_now si varsta lui. Livrare monotona (fara reordonare).
    """

    def __init__(self, ms=0.0, jit=0.0, loss=0.0, down=False, seed=None):
        self.ms, self.jit, self.loss, self.down = ms, jit, loss, down
        self.rng = random.Random(seed)
        self._pend = []                 # (t_livrare, t_masura, th, om)
        self._last_sched = -1e18
        self._cur = None                # (t_masura, th, om)

    def set_from_dict(self, d):
        """Actualizeaza canalul din schema plata sau multi-link.

        Schema proprie este ``{ms, jit, loss, down}``. Pentru replay si
        compatibilitate acceptam si schema roverului ``{lat_ms: {id: ...},
        jit_ms: {id: ...}, loss: {id: ...}, down: [id, ...]}``.
        Valorile sunt validate inainte de a modifica starea canalului.
        """
        if not isinstance(d, dict):
            raise ValueError("linkstate trebuie sa fie un obiect JSON")

        def scalar(value):
            if isinstance(value, dict):
                return next(iter(value.values()), None)
            return value

        def number(value, current, name):
            value = scalar(value)
            if value is None:
                return current
            if isinstance(value, bool):
                raise ValueError(f"{name} nu poate fi boolean")
            result = float(value)
            if not math.isfinite(result):
                raise ValueError(f"{name} trebuie sa fie finit")
            return result

        ms_value = d["ms"] if "ms" in d else d.get("lat_ms")
        jit_value = d["jit"] if "jit" in d else d.get("jit_ms")
        ms = max(0.0, number(ms_value, self.ms, "ms"))
        jit = max(0.0, number(jit_value, self.jit, "jit"))
        loss = number(d.get("loss"), self.loss, "loss")
        loss = min(max(loss, 0.0), 1.0)

        down_value = d.get("down", self.down)
        if isinstance(down_value, dict):
            down = any(bool(v) for v in down_value.values())
        elif isinstance(down_value, (list, tuple, set)):
            down = bool(down_value)
        elif isinstance(down_value, str):
            normalized = down_value.strip().lower()
            if normalized not in ("true", "false", "1", "0"):
                raise ValueError("down trebuie sa fie boolean")
            down = normalized in ("true", "1")
        else:
            down = bool(down_value)

        self.ms, self.jit, self.loss, self.down = ms, jit, loss, down

    def push(self, t, th, om):
        if self.down or self.rng.random() < self.loss:
            return False
        delay = self.ms / 1000.0
        if self.jit > 0:
            delay += abs(self.rng.gauss(0.0, self.jit / 1000.0))
        t_del = max(t + delay, self._last_sched)
        self._last_sched = t_del
        self._pend.append((t_del, t, th, om))
        return True

    def latest(self, t_now):
        while self._pend and self._pend[0][0] <= t_now:
            _, tm, th, om = self._pend.pop(0)
            self._cur = (tm, th, om)
        if self._cur is None:
            return None
        tm, th, om = self._cur
        return th, om, (t_now - tm)     # + varsta masurii


class AdaptiveImpedance:
    """Impedanta adaptata la varsta masurii: K_ef = K0/(1+ck*age_ms),
    B_ef = B0*(1+cb*age_ms). Masura veche => articulatie mai moale si
    mai amortizata -- schimbam transparenta pe stabilitate, controlat."""

    def __init__(self, k0=40.0, b0=1.2, th0=0.0, tau_max=8.0,
                 ck=0.10, cb=0.03, age_floor_ms=0.0):
        self.k0, self.b0 = float(k0), float(b0)
        self.th0 = float(th0)
        self.tau_max = abs(float(tau_max))
        self.ck, self.cb = float(ck), float(cb)
        self.age_floor = float(age_floor_ms)
        self.k_ef, self.b_ef = self.k0, self.b0

    def torque(self, th, om, age_s=0.0, dt=None, om_local=None):
        """LECTIA DE ARHITECTURA (verificata in teste): amortizarea pe o
        viteza INTARZIATA pompeaza energie -- de aceea pe banc bucla de
        amortizare traieste LOCAL (pe Pi, langa drive), iar prin legatura
        degradata calatoreste doar rigiditatea/referinta. om_local, daca
        e dat, e viteza masurata local; om ramane cea sosita prin link."""
        age_ms = max(0.0, age_s * 1000.0 - self.age_floor)
        self.k_ef = self.k0 / (1.0 + self.ck * age_ms)
        self.b_ef = self.b0 * (1.0 + self.cb * age_ms)
        om_d = om_local if om_local is not None else om
        tau = -self.k_ef * (th - self.th0) - self.b_ef * om_d
        return max(-self.tau_max, min(self.tau_max, tau))


def run_teleimpedance(law, link, tau_a_fn, dt=0.001, t_end=3.0,
                      adaptive=False, local_damping=True,
                      sim=None, monitor=None):
    """Bucla de tele-impedanta: encoderul -> link degradat -> legea B."""
    from joint_core import PairSim, EnergyMonitor
    sim = sim or PairSim()
    monitor = monitor or EnergyMonitor()
    trace = []
    tau_b = 0.0
    while sim.t < t_end:
        link.push(sim.t, sim.th, sim.om)
        m = link.latest(sim.t)
        if m is not None:
            th_m, om_m, age = m
            if adaptive:
                tau_b = law.torque(th_m, om_m, age_s=age, dt=dt,
                                   om_local=(sim.om if local_damping else None))
            else:
                tau_b = law.torque(th_m, om_m, dt)
        sim.step(tau_a_fn(sim.t), tau_b, dt)
        monitor.step(tau_b, sim.om, dt)
        trace.append((sim.t, sim.th, sim.om, tau_b))
    return sim, monitor, trace
