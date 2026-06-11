#!/usr/bin/env python3
"""nav_core.py — nucleul PUR (fara ROS) pentru roverul cu 4 ROTI skid-steer
si pentru navigarea go-to-goal (mergi la o coordonata).

De ce separat de rover_core: rover_core ramane roverul diferential cu 2 roti
si pilotul-slalom al experimentului de teza, neatins (cele 17 teste trec).
Aici adaugam, ADITIV:
  - SkidSteer4W: cinematica unui rover cu 4 roti motoare (skid-steer). Are
    EXACT aceeasi interfata step(v, w, dt) ca DiffDrive, plus coeficienti de
    PATINARE (slip): un skid-steer scrubeaza pe loc, deci avanseaza si se
    roteste ceva mai putin decat comanda ideala. slip=w_slip=0 -> identic cu
    DiffDrive (onest si testabil prin comparatie directa).
  - goto_command: controler PUR "mergi la (gx, gy)" — pivoteaza pe loc cand
    tinta e mult in lateral (skid-steer-ul intoarce curat pe loc), altfel
    inainteaza cu decelerare la sosire. Acelasi tipar de pure-pursuit ca
    PilotModel din rover_core, dar spre o singura tinta (waypoint sau obiect).

Navigatorul (goto_node) foloseste DOAR goto_command pe ultima poza primita,
deci se comporta ca un OPERATOR drop-in: comenzile lui curg prin aceeasi
legatura degradata + SafetyGate + jurnal ca pilotul uman.
"""
import math

from rover_core import V_MAX, W_MAX


def _wrap(a):
    """Aduce un unghi in [-pi, pi] (acelasi idiom ca in rover_core)."""
    return (a + math.pi) % (2 * math.pi) - math.pi


class SkidSteer4W:
    """Cinematica unui rover cu 4 roti SKID-STEER (integrare Euler).

    Comanda e tot (v, w) — exact ca la diferential — fiindca un skid-steer cu
    4 roti se comanda la fel (roti stanga vs roti dreapta). Diferenta fizica e
    PATINAREA: la viraj track-urile freaca lateral, deci miscarea efectiva e
    putin sub comanda. O modelam cu doi coeficienti in [0, 1):
      slip    -> reduce viteza liniara efectiva (scrub la inaintare/viraj);
      w_slip  -> reduce viteza unghiulara efectiva (sub-rotire la viraj).
    Implicit 0 -> raspuns ideal, identic cu DiffDrive.

    a_max / w_acc (optionale): limite de ACCELERATIE liniara/unghiulara
    (actuator realist), aplicate pe COMANDA, exact ca in DiffDrive.
    """

    def __init__(self, x=0.0, y=0.0, th=0.0, a_max=None, w_acc=None,
                 slip=0.0, w_slip=0.0):
        self.x, self.y, self.th = x, y, th
        self.a_max, self.w_acc = a_max, w_acc
        self.slip, self.w_slip = slip, w_slip
        self._v = self._w = 0.0            # comanda curenta (pt. rampa de accel)
        self._v_eff = self._w_eff = 0.0    # miscarea efectiva (dupa patinare)

    def step(self, v, w, dt):
        # 1) saturatia comenzii la limitele roverului
        v = max(-V_MAX, min(V_MAX, v))
        w = max(-W_MAX, min(W_MAX, w))
        # 2) limite de acceleratie pe COMANDA (rampa), ca in DiffDrive
        if self.a_max is not None:
            dv = max(-self.a_max * dt, min(self.a_max * dt, v - self._v))
            v = self._v + dv
        if self.w_acc is not None:
            dw = max(-self.w_acc * dt, min(self.w_acc * dt, w - self._w))
            w = self._w + dw
        self._v, self._w = v, w
        # 3) PATINAREA: miscarea efectiva e sub comanda (skid-steer scrub)
        v_eff = v * (1.0 - self.slip)
        w_eff = w * (1.0 - self.w_slip)
        self._v_eff, self._w_eff = v_eff, w_eff
        # 4) integrarea pozei cu miscarea EFECTIVA
        self.x += v_eff * math.cos(self.th) * dt
        self.y += v_eff * math.sin(self.th) * dt
        self.th = _wrap(self.th + w_eff * dt)
        return v, w                        # intoarce COMANDA (ca DiffDrive)


def goto_command(x, y, th, gx, gy, *, k_w=2.2, v_max=V_MAX, w_max=W_MAX,
                 arrive_r=0.5, slow_r=1.5, turn_gate=0.8):
    """Controler PUR go-to-goal: din poza (x, y, th) si tinta (gx, gy) -> (v, w, arrived).

    - daca esti sub arrive_r de tinta -> oprire, arrived=True;
    - daca tinta e mult in lateral (|alpha| > turn_gate) -> PIVOTEAZA pe loc
      (v~0), ca skid-steer-ul sa se alinieze inainte de a porni;
    - altfel inainteaza, cu viteza scazuta proportional cu eroarea de unghi
      SI cu decelerare in apropierea tintei (sub slow_r).
    """
    dist = math.hypot(gx - x, gy - y)
    if dist < arrive_r:
        return 0.0, 0.0, True
    alpha = _wrap(math.atan2(gy - y, gx - x) - th)
    w = max(-w_max, min(w_max, k_w * alpha))
    if abs(alpha) > turn_gate:
        return 0.0, w, False               # intai aliniaza-te (pivot pe loc)
    v = v_max * max(0.2, 1.0 - abs(alpha) / 1.2) * min(1.0, dist / slow_r)
    return v, w, False


def goal_reached(x, y, gx, gy, arrive_r=0.5):
    """True daca (x, y) e in raza de sosire fata de tinta (gx, gy)."""
    return math.hypot(gx - x, gy - y) < arrive_r
