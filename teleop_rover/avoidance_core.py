#!/usr/bin/env python3
"""avoidance_core.py - evitare de obstacole, nucleu PUR (fara ROS, testabil).

Combina ATRACTIA spre tinta cu REPULSIA fata de obstacolele vazute de lidar,
in stil potential-fields (Khatib 1986) cu o componenta de tip VFH (Borenstein &
Koren 1991): scanul 360 grade e impartit in sectoare, fiecare sector ocupat sub
un prag genereaza un vector de respingere; suma vectoriala cu atractia spre tinta
da directia libera, din care rezulta (v, w).

De ce nucleu pur: la fel ca rover_core / nav_core, logica de evitare se scrie si
se testeaza FARA Gazebo (cu scanuri sintetice), apoi se cableaza intr-un nod subtire.

Conventii:
- ranges: lista de distante [m] de la lidar, ordonate de la angle_min la angle_max;
  o valoare inf / nan / >= range_max inseamna "liber pe directia aceea".
- bearing-ul unei raze i:  angle_min + i * angle_increment  (in cadrul ROBOTULUI,
  0 = inainte, pozitiv = la stanga / CCW).
- goal_bearing: unghiul catre tinta in cadrul robotului (0 = drept inainte).
- iesire: (v, w, blocked). blocked=True cand frontul e infundat (toate directiile
  utile sunt sub pragul critic) -> apelantul decide (opreste / da inapoi).
"""
import math

# limitele roverului (aceleasi ca rover_core, ca sa fie coerent)
V_MAX, W_MAX = 1.2, 2.2

# parametri evitare (reglabili din nod prin AvoidParams)
D_SAFE = 2.5        # sub atata [m] un obstacol incepe sa respinga (reactie din timp)
D_CRIT = 0.6        # sub atata [m] coliziune iminenta -> blocked
K_REP = 3.0         # repulsie mai puternica -> ocolire mai larga, vizibila
K_ATT = 1.0         # greutatea atractiei spre tinta
FRONT_CONE = math.radians(45)   # conul frontal verificat pentru "blocked"
K_W = 2.2           # castig pe eroarea de unghi -> w
GOAL_CLEAR_R = 4.0  # sub atata [m] de tinta, ignora obstacolele (tinta != obstacol)


class AvoidParams:
    """Container de parametri, ca sa fie usor de reglat / pasat din nod."""

    def __init__(self, d_safe=D_SAFE, d_crit=D_CRIT, k_rep=K_REP,
                 k_att=K_ATT, front_cone=FRONT_CONE, k_w=K_W,
                 v_max=V_MAX, w_max=W_MAX, goal_clear_r=GOAL_CLEAR_R):
        self.d_safe = d_safe
        self.d_crit = d_crit
        self.k_rep = k_rep
        self.k_att = k_att
        self.front_cone = front_cone
        self.k_w = k_w
        self.v_max = v_max
        self.w_max = w_max
        # sub atata [m] de tinta, IGNORA repulsia: tinta e destinatia (victima/
        # obiectiv), nu un obstacol de evitat -> altfel roverul orbiteaza in jurul ei
        self.goal_clear_r = goal_clear_r


def _wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


def repulsion_vector(ranges, angle_min, angle_increment, p: AvoidParams):
    """Suma vectoriala a respingerilor din scan, in cadrul robotului.
    Fiecare raza sub d_safe impinge in sens OPUS directiei ei, cu o forta care
    creste pe masura ce obstacolul e mai aproape. Intoarce (rx, ry, d_min)."""
    rx = ry = 0.0
    d_min = float("inf")
    n = len(ranges)
    for i in range(n):
        d = ranges[i]
        if d is None:
            continue
        # ignora citirile invalide / "liber"
        if math.isinf(d) or math.isnan(d) or d <= 0.0:
            continue
        if d < d_min:
            d_min = d
        if d >= p.d_safe:
            continue
        ang = angle_min + i * angle_increment
        # forta ~ (1/d - 1/d_safe): 0 la d_safe, mare aproape de obstacol
        f = p.k_rep * (1.0 / max(d, 1e-3) - 1.0 / p.d_safe)
        if f <= 0:
            continue
        # respinge in sens opus directiei obstacolului
        rx -= f * math.cos(ang)
        ry -= f * math.sin(ang)
    return rx, ry, d_min


def attraction_vector(goal_bearing, p: AvoidParams):
    """Vector unitar*k_att spre tinta, in cadrul robotului."""
    return p.k_att * math.cos(goal_bearing), p.k_att * math.sin(goal_bearing)


def front_blocked(ranges, angle_min, angle_increment, p: AvoidParams):
    """True daca in conul frontal (+/- front_cone) exista o raza sub d_crit."""
    n = len(ranges)
    for i in range(n):
        d = ranges[i]
        if d is None or math.isinf(d) or math.isnan(d) or d <= 0.0:
            continue
        ang = _wrap(angle_min + i * angle_increment)
        if abs(ang) <= p.front_cone and d <= p.d_crit:
            return True
    return False


def avoid_command(ranges, angle_min, angle_increment, goal_bearing, goal_dist,
                  p: AvoidParams = None, arrive_r=1.0):
    """Comanda finala (v, w, blocked) care merge spre tinta SI ocoleste.

    - daca esti sub arrive_r de tinta -> (0,0,False) (apelantul declara sosit);
    - daca frontul e infundat sub d_crit -> blocked=True, v=0, w spre partea mai
      libera (cauta o iesire pivotand);
    - altfel: directia rezultanta = atractie + repulsie; v scade cu cat directia
      ceruta e mai laterala (intai aliniaza-te) si cu cat un obstacol e mai aproape.
    """
    if p is None:
        p = AvoidParams()

    if goal_dist <= arrive_r:
        return 0.0, 0.0, False

    ax, ay = attraction_vector(goal_bearing, p)
    # aproape de tinta: ignora repulsia (tinta e destinatia, nu obstacol)
    if goal_dist <= p.goal_clear_r:
        alpha = _wrap(goal_bearing)
        w = max(-p.w_max, min(p.w_max, p.k_w * alpha))
        v = p.v_max * max(0.2, 1.0 - abs(alpha) / 1.2)
        return v, w, False
    rx, ry, d_min = repulsion_vector(ranges, angle_min, angle_increment, p)

    if front_blocked(ranges, angle_min, angle_increment, p):
        # infundat: nu inainta; pivoteaza spre partea cu mai mult spatiu
        # (semnul componentei laterale a repulsiei arata incotro e liber)
        w = p.w_max if ry >= 0 else -p.w_max
        return 0.0, w, True

    # directia dorita = suma campurilor
    dx, dy = ax + rx, ay + ry
    desired = math.atan2(dy, dx)            # in cadrul robotului (0 = inainte)
    alpha = _wrap(desired)

    w = max(-p.w_max, min(p.w_max, p.k_w * alpha))
    # viteza: redu cand directia e laterala SI cand obstacolul e aproape
    turn_factor = max(0.2, 1.0 - abs(alpha) / 1.2)
    if math.isinf(d_min):
        prox_factor = 1.0
    else:
        # 1.0 la d_safe sau mai departe, scade liniar spre 0.3 la d_crit
        prox_factor = max(0.3, min(1.0, (d_min - p.d_crit)
                                   / max(1e-3, p.d_safe - p.d_crit)))
    v = p.v_max * turn_factor * prox_factor
    return v, w, False
