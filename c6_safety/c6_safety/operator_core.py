#!/usr/bin/env python3
"""operator_core.py -- operatorul uman, simulat. ORB la pericol.

ERATA v0.2 (17.09): react=False e SCENARIUL DE BAZA -- filtrul decide, operatorul
nu vede nimic si cere P spre tinta la nesfarsit. Pretul sigurantei cu un operator
orb (B, T_G) e chiar motivatia C5, deci NU se ascunde.

react=True e un SUB-BLOC (factor F7): un om care observa ca NU INAINTEAZA si da
din volan. Declansare pe PROGRES (D1, 17.09), nu pe viteza:
    progres < PROGRES_MIN = 0.10 m in fereastra T_REACT = 2.0 s, cu v_op > 0.2
apoi viraj 45 grade spre partea cu h mai mare, timp de DURATA_REACT = 2 s, apoi
P; re-armare dupa T_REARM = 1 s. Motiv (S2.1 erata): cu W filtrul iese din blocaj
tarandu-se la v ~ 0.01 in rafale sub 1 s, iar un prag pe viteza continua nu se
arma niciodata (n_reactii = 0). Progresul pe fereastra prinde si tararea.

Operatorul are STARE (cronometre), deci e o clasa. op_cmd() ramane pentru
compatibilitate si e echivalent cu Operator(react=False).
"""
import math

T_REACT = 2.0        # s, fereastra de progres; D1 (17.09)
PROGRES_MIN = 0.10   # m, sub atat in fereastra = blocaj
UNGHI_REACT = math.radians(45.0)
DURATA_REACT = 2.0   # s
T_REARM = 1.0        # s
V_BLOCAT = 0.05      # m/s, caiet sec. 8
V_OP_ACTIV = 0.2     # m/s, caiet sec. 8


def raportor_activ(t, t_pauza, durata):
    """Raporteaza GCS-ul pericolul la momentul t? Predicat PUR, folosit si de nod si de core.

    Fereastra de tacere e [t_pauza, t_pauza + durata). t_pauza < 0 sau durata <= 0 inseamna FARA pauza,
    deci comportamentul de dinainte, bit cu bit. E scris o singura data si importat de amandoua partile
    tocmai ca simularea offline si rularea ROS sa nu poata diverge pe definitia ferestrei.
    """
    if t_pauza is None or t_pauza < 0.0 or durata is None or durata <= 0.0:
        return True
    return not (t_pauza <= t < t_pauza + durata)


def _eroare_unghi(tinta, theta):
    return math.atan2(math.sin(tinta - theta), math.cos(tinta - theta))


def _partea_cu_h_mai_mare(state, params, dir_goal):
    """+1 = stanga, -1 = dreapta: partea care lasa h mai mare dupa un pas ipotetic."""
    ox, oy = params.obst
    best = None
    for semn in (+1, -1):
        th = dir_goal + semn * UNGHI_REACT
        s = params.v_max * params.dt
        cx = state.x + (s + params.l) * math.cos(th)
        cy = state.y + (s + params.l) * math.sin(th)
        h = math.hypot(cx - ox, cy - oy)
        if best is None or h > best[0]:
            best = (h, semn)
    return best[1]


def _p_spre_goal(state, params):
    gx, gy = params.goal
    dx, dy = gx - state.x, gy - state.y
    return math.hypot(dx, dy), math.atan2(dy, dx)


class Operator(object):
    def __init__(self, params, react=False):
        self.p = params
        self.react = react
        self.istoric = []         # (t, x, y) pe ultimele T_REACT secunde
        self.t_viraj = None       # de cand vireaza
        self.semn = 0
        self.t_rearm = -1.0       # cand poate reactiona din nou
        self.n_reactii = 0

    def cmd(self, state, t):
        p = self.p
        dist, dir_goal = _p_spre_goal(state, p)
        v = max(0.0, min(p.v_max, p.k_v * dist))
        tinta = dir_goal

        if self.react:
            # in viraj?
            if self.t_viraj is not None:
                if t - self.t_viraj < DURATA_REACT:
                    tinta = dir_goal + self.semn * UNGHI_REACT
                else:
                    self.t_viraj = None
                    self.t_rearm = t + T_REARM
            else:
                self.istoric.append((t, state.x, state.y))
                self.istoric = [e for e in self.istoric if t - e[0] <= T_REACT]
                fereastra_plina = (t - self.istoric[0][0]) >= T_REACT - 1e-9
                if fereastra_plina and v > V_OP_ACTIV and t >= self.t_rearm:
                    t0, x0, y0 = self.istoric[0]
                    progres = math.hypot(state.x - x0, state.y - y0)
                    if progres < PROGRES_MIN:
                        self.semn = _partea_cu_h_mai_mare(state, p, dir_goal)
                        self.t_viraj = t
                        self.istoric = []
                        self.n_reactii += 1
                        tinta = dir_goal + self.semn * UNGHI_REACT

        err = _eroare_unghi(tinta, state.theta)
        w = max(-p.omega_max, min(p.omega_max, p.k_w * err))
        return v, w


def op_cmd(state, params, t=None, react=False):
    """Compatibilitate: fara stare, deci DOAR react=False are sens aici."""
    return Operator(params, react=False).cmd(state, t or 0.0)
