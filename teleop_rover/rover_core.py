#!/usr/bin/env python3
"""rover_core.py — nucleul PUR al teleoperarii unui rover diferential
(fara ROS, testabil integral): cinematica, traseul-slalom, eroarea de
urmarire, pilotul-model (operator reproductibil) si stratul de siguranta.

De ce pilot-MODEL si nu doar tastatura: experimentele de teza cer
repetabilitate — acelasi "operator" (pure pursuit cu feedback INTARZIAT),
rulat de N ori pe fiecare conditie de retea, da curbe eroare-vs-latenta
comparabile. Tastatura ramane disponibila in operator_node (mode:=manual).
"""
import math

V_MAX, W_MAX = 1.2, 2.2          # limitele roverului [m/s, rad/s]
WATCHDOG_S = 0.4                  # fara comanda proaspata -> STOP
STALE_S = 1.0                     # comenzile mai vechi de atat se ignora

# traseul-slalom (sursa unica si pentru lumea Gazebo): start (0,0), cap 0
COURSE = [(4.0, 0.0), (8.0, 2.5), (12.0, -2.5), (16.0, 2.5),
          (20.0, -2.5), (24.0, 0.0), (28.0, 0.0)]
WP_RADIUS = 1.0                   # punct atins sub aceasta distanta


class DiffDrive:
    """Cinematica unui robot diferential (integrare Euler).
    a_max / w_acc (optionale): limite de ACCELERATIE liniara/unghiulara —
    actuator realist (M1); implicit None = raspuns instantaneu (ideal)."""

    def __init__(self, x=0.0, y=0.0, th=0.0, a_max=None, w_acc=None):
        self.x, self.y, self.th = x, y, th
        self.a_max, self.w_acc = a_max, w_acc
        self._v = self._w = 0.0

    def step(self, v, w, dt):
        v = max(-V_MAX, min(V_MAX, v))
        w = max(-W_MAX, min(W_MAX, w))
        if self.a_max is not None:
            dv = max(-self.a_max * dt, min(self.a_max * dt, v - self._v))
            v = self._v + dv
        if self.w_acc is not None:
            dw = max(-self.w_acc * dt, min(self.w_acc * dt, w - self._w))
            w = self._w + dw
        self._v, self._w = v, w
        self.x += v * math.cos(self.th) * dt
        self.y += v * math.sin(self.th) * dt
        self.th = (self.th + w * dt + math.pi) % (2 * math.pi) - math.pi
        return v, w


class Course:
    """Traseul + eroarea de urmarire (cross-track fata de segmentul curent)."""

    def __init__(self, pts=None):
        self.pts = [(0.0, 0.0)] + list(pts or COURSE)
        self.i = 1                       # tinta curenta (index in pts)

    @property
    def target(self):
        return self.pts[self.i]

    @property
    def done(self):
        return self.i >= len(self.pts)

    def advance(self, x, y):
        """Avanseaza tinta cand e atinsa; intoarce True daca s-a terminat."""
        while not self.done and math.hypot(self.target[0] - x,
                                           self.target[1] - y) < WP_RADIUS:
            self.i += 1
        return self.done

    def cross_track(self, x, y):
        """Distanta pana la segmentul curent al traseului [m]."""
        j = min(self.i, len(self.pts) - 1)
        (ax, ay), (bx, by) = self.pts[j - 1], self.pts[j]
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((x - ax) * dx
                                                   + (y - ay) * dy) / L2))
        px, py = ax + t * dx, ay + t * dy
        return math.hypot(x - px, y - py)

    def length(self):
        return sum(math.hypot(self.pts[k + 1][0] - self.pts[k][0],
                              self.pts[k + 1][1] - self.pts[k][1])
                   for k in range(len(self.pts) - 1))


class PilotModel:
    """„Operatorul" reproductibil: pure pursuit pe ULTIMA poza primita
    (adica pe feedback intarziat/pierdut — exact bucla reala de teleop)."""

    def __init__(self, course: Course, k_w=2.2):
        self.course = course
        self.k_w = k_w

    def command(self, x, y, th):
        """(v, w) pe baza pozei cunoscute (posibil veche)."""
        self.course.advance(x, y)
        if self.course.done:
            return 0.0, 0.0
        tx, ty = self.course.target
        alpha = math.atan2(ty - y, tx - x) - th
        alpha = (alpha + math.pi) % (2 * math.pi) - math.pi
        v = V_MAX * max(0.25, 1.0 - abs(alpha) / 1.2)
        w = max(-W_MAX, min(W_MAX, self.k_w * alpha))
        return v, w


class SafetyGate:
    """Stratul de siguranta de pe ROBOT: watchdog + comenzi invechite.

    - daca nu a sosit nicio comanda de WATCHDOG_S -> STOP (numarat);
    - comenzile cu varsta peste STALE_S la sosire sunt ignorate.
    Robotul nu se misca niciodata pe o comanda veche sau absenta.
    """

    def __init__(self, watchdog_s=WATCHDOG_S, stale_s=STALE_S):
        self.watchdog_s, self.stale_s = watchdog_s, stale_s
        self.t_rx = None        # cand a SOSIT ultima comanda valida
        self.cmd = (0.0, 0.0)
        self.stopped = True
        self.stop_events = 0

    def on_command(self, t_now, t_emitted, v, w):
        if t_now - t_emitted > self.stale_s:
            return False                      # prea veche: ignorata
        self.t_rx = t_now
        self.cmd = (v, w)
        return True

    def output(self, t_now):
        """(v, w, stopped) de aplicat pe motoare acum."""
        alive = self.t_rx is not None and (t_now - self.t_rx) <= self.watchdog_s
        if alive and self.stopped:
            self.stopped = False
        if not alive and not self.stopped:
            self.stopped = True
            self.stop_events += 1
        return (self.cmd[0], self.cmd[1], False) if alive else (0.0, 0.0, True)


def summarize(samples):
    """Din lista de (cte, cmd_age) -> metricile rularii."""
    if not samples:
        return {}
    ctes = sorted(s[0] for s in samples)
    ages = [s[1] for s in samples if s[1] is not None]
    p = lambda a, q: a[min(len(a) - 1, round(q * (len(a) - 1)))]
    return {"cte_mean": sum(ctes) / len(ctes), "cte_p95": p(ctes, 0.95),
            "cte_max": ctes[-1],
            "cmd_age_mean": (sum(ages) / len(ages)) if ages else None}
