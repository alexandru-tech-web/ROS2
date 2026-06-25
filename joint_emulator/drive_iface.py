#!/usr/bin/env python3
"""drive_iface.py -- TAIETURA dintre logica si fier: interfata unica pe
care o vor implementa backend-urile. Azi exista doar SimBackend (pentru
dezvoltare oriunde); backend-ul real (EtherCAT/analog/vendor) se scrie
DUPA ce stim modelul drive-urilor ABB de pe stand -- fara sa schimbam
nimic deasupra acestei interfete.

Contract (toate marimile SI):
  enable(id) / disable(id)            armare/dezarmare (B: mod TORQUE!)
  read(id) -> (t, th, om)             timpul masurii + pozitie + viteza
  set_torque(id, tau)                 comanda de cuplu (clamp in backend)
  estop()                             cuplu zero pe TOT, imediat
Regula de fier: motorul B NU ruleaza niciodata in mod pozitie --
pozitie-contra-pozitie pe ax rigid = oscilatie si supracurent.
"""
import time

from joint_core import PairSim


class SimBackend:
    """Perechea simulata in spatele aceleiasi interfete ca fierul."""

    def __init__(self, n_pairs=3, dt=0.001):
        self.pairs = [PairSim() for _ in range(n_pairs)]
        self.tau = [[0.0, 0.0] for _ in range(n_pairs)]
        self.enabled = [[False, False] for _ in range(n_pairs)]
        self.dt = dt
        self.t0 = time.time()

    def _tick(self):
        for k, p in enumerate(self.pairs):
            a = self.tau[k][0] if self.enabled[k][0] else 0.0
            b = self.tau[k][1] if self.enabled[k][1] else 0.0
            p.step(a, b, self.dt)

    def enable(self, mid):
        pair, side = divmod(mid, 2)
        self.enabled[pair][side] = True

    def disable(self, mid):
        pair, side = divmod(mid, 2)
        self.enabled[pair][side] = False
        self.tau[pair][side] = 0.0

    def read(self, mid):
        pair, _ = divmod(mid, 2)
        self._tick()
        p = self.pairs[pair]
        return p.t, p.th, p.om

    def set_torque(self, mid, tau):
        pair, side = divmod(mid, 2)
        self.tau[pair][side] = float(tau)

    def estop(self):
        for k in range(len(self.pairs)):
            self.tau[k] = [0.0, 0.0]
            self.enabled[k] = [False, False]
