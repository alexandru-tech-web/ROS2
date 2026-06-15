#!/usr/bin/env python3
"""
swarm_core.py — Logica pura a roiului de drone, FARA dependinte ROS2.

Separarea logicii de transport este intentionata si are doua motive:
1. Testabilitate: toata matematica (cinematica, formatii, cautare, failsafe)
   se poate verifica cu teste unitare pe orice masina, fara ROS2.
2. Portabilitate: aceleasi functii sunt folosite de nodul de simulare si pot
   fi refolosite de adaptorul pentru drone reale (PX4).

Modulele ROS2 (drone_sim.py, swarm_coordinator.py, gcs_node.py) sunt doar
invelisuri subtiri peste acest fisier.

Conventii:
- Pozitii si viteze in metri / metri pe secunda, sistem ENU (x est, y nord,
  z sus). Altitudinea pozitiva inseamna deasupra solului.
- Timpul pentru watchdog este ceas monotonic (time.monotonic()), imun la
  ajustari de ceas — consecvent cu metodologia de masurare a latentei.
"""

import math
import time
from dataclasses import dataclass, field


# ============================================================
# 1. Cinematica simplificata a unei drone (model de ordinul I)
# ============================================================
# Pentru experimente de middleware si control la distanta, fidelitatea
# aerodinamica e secundara: ce conteaza este traficul de mesaje si
# raspunsul in bucla inchisa. Un model de ordinul I (viteza comandata
# urmarita cu constanta de timp tau) este standardul pragmatic.

@dataclass
class DroneKinematics:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0          # altitudine (0 = sol)
    vx: float = 0.0
    vy: float = 0.0
    vz: float = 0.0
    tau: float = 0.5        # constanta de timp a raspunsului [s]
    vmax_xy: float = 3.0    # viteza orizontala maxima [m/s]
    vmax_z: float = 1.5     # viteza verticala maxima [m/s]

    def step(self, cmd_vx: float, cmd_vy: float, cmd_vz: float, dt: float):
        """Avanseaza starea cu dt secunde, urmarind viteza comandata."""
        cvx, cvy = clamp_xy(cmd_vx, cmd_vy, self.vmax_xy)
        cvz = max(-self.vmax_z, min(self.vmax_z, cmd_vz))
        # urmarire de ordinul I: v += (v_cmd - v) * alpha
        alpha = min(1.0, dt / max(1e-6, self.tau))
        self.vx += (cvx - self.vx) * alpha
        self.vy += (cvy - self.vy) * alpha
        self.vz += (cvz - self.vz) * alpha
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.z += self.vz * dt
        if self.z < 0.0:          # solul e bariera fizica
            self.z = 0.0
            self.vz = 0.0


def clamp_xy(vx: float, vy: float, vmax: float):
    """Limiteaza vectorul orizontal la modul vmax, pastrand directia."""
    mag = math.hypot(vx, vy)
    if mag <= vmax or mag < 1e-9:
        return vx, vy
    s = vmax / mag
    return vx * s, vy * s


# ============================================================
# 2. Masina de stari de zbor + tranzitii legale
# ============================================================

VALID_TRANSITIONS = {
    "IDLE":            {"ARMED"},
    "ARMED":           {"TAKEOFF", "IDLE"},
    "TAKEOFF":         {"ACTIVE", "LANDING"},
    "ACTIVE":          {"LANDING", "FAILSAFE_HOVER"},
    "FAILSAFE_HOVER":  {"ACTIVE", "FAILSAFE_LAND"},
    "FAILSAFE_LAND":   {"LANDING"},
    "LANDING":         {"IDLE"},
}


class FlightStateMachine:
    """Masina de stari per drona. Tranzitiile ilegale sunt refuzate —
    protectie esentiala cand comenzile vin printr-o retea degradata si
    pot sosi tarziu sau in ordine gresita."""

    def __init__(self):
        self.state = "IDLE"

    def request(self, new_state: str) -> bool:
        if new_state == self.state:
            return True
        if new_state in VALID_TRANSITIONS.get(self.state, set()):
            self.state = new_state
            return True
        return False


# ============================================================
# 3. Watchdog de legatura (heartbeat) — failsafe sub pierderi
# ============================================================
# Statia de sol emite heartbeat. Fiecare drona il monitorizeaza DIRECT
# (nu prin coordonator) — astfel pierderea legaturii sau caderea
# coordonatorului declanseaza failsafe local, autonom.

class HeartbeatWatchdog:
    def __init__(self, timeout_s: float = 3.0, grace_s: float = 5.0):
        self.timeout_s = timeout_s   # dupa atat fara beat -> HOVER
        self.grace_s = grace_s       # dupa inca atat -> LAND
        self.last_beat = time.monotonic()

    def beat(self, t: float | None = None):
        self.last_beat = time.monotonic() if t is None else t

    def status(self, t: float | None = None) -> str:
        now = time.monotonic() if t is None else t
        dt = now - self.last_beat
        if dt <= self.timeout_s:
            return "OK"
        if dt <= self.timeout_s + self.grace_s:
            return "HOVER"
        return "LAND"


# ============================================================
# 4. Formatii — offseturi fata de un punct de ancora
# ============================================================

def formation_offsets(kind: str, n: int, spacing: float = 4.0):
    """Returneaza n offseturi (dx, dy) fata de ancora formatiei.
    kind: 'line' | 'circle' | 'grid'."""
    if n <= 0:
        return []
    if kind == "line":
        return [((i - (n - 1) / 2.0) * spacing, 0.0) for i in range(n)]
    if kind == "circle":
        if n == 1:
            return [(0.0, 0.0)]
        r = spacing * n / (2.0 * math.pi)      # circumferinta ~ n*spacing
        r = max(r, spacing / 2.0)
        return [(r * math.cos(2 * math.pi * i / n),
                 r * math.sin(2 * math.pi * i / n)) for i in range(n)]
    if kind == "grid":
        cols = math.ceil(math.sqrt(n))
        rows = math.ceil(n / cols)
        offs = []
        for i in range(n):
            r_i, c_i = divmod(i, cols)
            offs.append(((c_i - (cols - 1) / 2.0) * spacing,
                         (r_i - (rows - 1) / 2.0) * spacing))
        return offs
    raise ValueError(f"formatie necunoscuta: {kind}")


# ============================================================
# 5. Controlere simple de ghidare
# ============================================================

def goto_velocity(px, py, pz, tx, ty, tz, kp=0.8, vmax_xy=3.0, vmax_z=1.5):
    """Controler P spre tinta. Returneaza (vx, vy, vz)."""
    vx, vy = clamp_xy(kp * (tx - px), kp * (ty - py), vmax_xy)
    vz = max(-vmax_z, min(vmax_z, kp * (tz - pz)))
    return vx, vy, vz


def separation_velocity(px, py, others, d_min=1.5, gain=1.2):
    """Evitare de coliziune prin repulsie: pentru fiecare vecin mai aproape
    de d_min, adauga o componenta de viteza care impinge in afara.
    others: lista de (x, y)."""
    rx, ry = 0.0, 0.0
    for ox, oy in others:
        dx, dy = px - ox, py - oy
        d = math.hypot(dx, dy)
        if d < 1e-6:
            # suprapunere perfecta — impinge intr-o directie determinista
            rx += d_min * gain
            continue
        if d < d_min:
            # crestere patratica pe masura ce distanta scade: repulsia
            # devine dominanta inainte de contact, compensand inertia
            # modelului de ordinul I
            ratio = (d_min - d) / d_min          # 0 la d_min, 1 la contact
            push = gain * (1.0 + 3.0 * ratio) * ratio * d_min / d
            rx += dx * push
            ry += dy * push
    return rx, ry


def at_target(px, py, pz, tx, ty, tz, tol=0.4) -> bool:
    return (math.hypot(tx - px, ty - py) <= tol and abs(tz - pz) <= tol)


# ============================================================
# 6. Pattern de cautare SAR — boustrophedon (lawnmower) pe fasii
# ============================================================

def lawnmower_waypoints(x0, y0, x1, y1, n_drones, track, alt):
    """Imparte dreptunghiul [x0,x1]x[y0,y1] in n_drones fasii verticale
    si genereaza pentru fiecare drona un traseu serpentina (boustrophedon)
    cu distanta intre linii <= track. Returneaza lista de liste de
    waypoint-uri (x, y, alt).

    Acesta e nucleul aplicativ SAR: acoperire sistematica a unei zone
    de cautare, impartita intre membrii roiului."""
    if n_drones <= 0:
        return []
    x0, x1 = min(x0, x1), max(x0, x1)
    y0, y1 = min(y0, y1), max(y0, y1)
    width = x1 - x0
    strip_w = width / n_drones
    all_routes = []
    for i in range(n_drones):
        sx0 = x0 + i * strip_w
        sx1 = sx0 + strip_w
        # linii de survol in interiorul fasiei, la pas <= track
        n_lines = max(1, math.ceil(strip_w / track))
        step = strip_w / n_lines
        route = []
        for k in range(n_lines):
            lx = sx0 + step * (k + 0.5)       # centrul benzii k
            if k % 2 == 0:
                route.append((lx, y0, alt))
                route.append((lx, y1, alt))
            else:
                route.append((lx, y1, alt))
                route.append((lx, y0, alt))
        all_routes.append(route)
    return all_routes


# ============================================================
# 7. Protocolul de comenzi (folosit de GCS si coordonator)
# ============================================================
# Comenzile sunt JSON serializat in std_msgs/String. Campuri comune:
#   id       — identificator unic al comenzii (pentru ACK / masurare RTT)
#   t_ns     — time.monotonic_ns() la emitere (ecou in ACK -> RTT pe un
#              singur ceas, fara sincronizare intre masini)
#   cmd      — takeoff | land | rtl | formation | goto | search
# Campuri specifice:
#   formation: kind (line|circle|grid), anchor [x,y], alt, spacing
#   goto:      anchor [x,y], alt   (roiul pastreaza formatia curenta)
#   search:    area [x0,y0,x1,y1], track, alt

KNOWN_COMMANDS = {"takeoff", "land", "rtl", "formation", "goto", "search"}


def validate_command(d: dict) -> str | None:
    """Returneaza None daca e valida, altfel mesajul de eroare."""
    if not isinstance(d, dict):
        return "comanda trebuie sa fie obiect JSON"
    if d.get("cmd") not in KNOWN_COMMANDS:
        return f"cmd necunoscut: {d.get('cmd')}"
    if "id" not in d or "t_ns" not in d:
        return "lipsesc campurile id / t_ns"
    if d["cmd"] == "formation":
        if d.get("kind") not in {"line", "circle", "grid"}:
            return "formation.kind invalid"
    if d["cmd"] == "search":
        a = d.get("area")
        if not (isinstance(a, (list, tuple)) and len(a) == 4):
            return "search.area trebuie sa fie [x0,y0,x1,y1]"
    return None
