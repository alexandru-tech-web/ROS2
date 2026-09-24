#!/usr/bin/python3
"""
exercise_core.py -- Nucleul procesului de control al celor 6 servomotoare
(2 sold + 2 genunchi + 2 glezna), FARA dependinte ROS.  [v2: sesiuni]

Straturi: program -> traiectorie cosinus (viteza zero la capete) ->
siguranta (clamp + validare viteza) -> Player.sample(t).

REPERTORIU v2 -- 12 exercitii atomice + 4 SESIUNI pe grupe:
  glezna:   ankle_pump, ankle_alternating, ankle_holds
  genunchi: knee_extension, knee_alternating, knee_pulses
  sold:     hip_raise, hip_alternating, hip_hold
  combinat: alternating_march, full_extension, leg_wave
  SESIUNI:  ankle_session, knee_session, hip_session, combined_session
            (inlantuiri de exercitii; fiecare exercitiu incepe si se
             termina in postura neutra, deci cusatura e continua)

Siguranta specifica gleznei: exercitiile de glezna ridica intai usor
gambele (genunchi +0.30 rad) inainte de plantarflexie, astfel incat
varful pantofului sa nu coboare sub nivelul podelei -- verificat prin
FK pe punctele varf/calcai ale placii de picior.

Conventia de semn (identica cu URDF v2):
  CONVENTIE: ZERO ANATOMIC (M1, decizia B din registrul de pe 18 aug).
  hip   +  = FLEXIE (coapsa spre piept)   [0.0000 .. 1.5708] rad = 0..90 grade
  knee  +  = FLEXIE (calcaiul spre sezut) [0.0000 .. 2.4435] rad = 0..140 grade
  ankle +  = DORSIFLEXIE (varf sus)      [-0.6109 .. 0.6109] rad = -35..+35 grade
  ATENTIE la genunchi: semnul S-A INVERSAT (in conventia veche + era extensie).

  CONVERSIA TRAIECTORIILOR nu e uniforma, si asta trebuie stiut:
    genunchi, glezna -- offset (si inversare la genunchi): unghiul FIZIC e IDENTIC
      cu cel din conventia veche. Echivalenta e dovedita punct cu punct.
    sold -- RE-DERIVAT, nu convertit. Cursa veche, exprimata anatomic, era
      64.22 .. 130.11 grade: sold permanent flectat, pana peste flexia umana
      normala. Nicio fereastra de 90 de grade (cursa documentata, Tabel 3.1) nu o
      contine. Vechile limite erau placeholdere fara sursa (GAP 4), deci documentul
      are prioritate. Punctele pastreaza FRACTIA din cursa disponibila, adica forma
      si intentia exercitiului, NU unghiul fizic absolut.
  Conventia veche e in attic/exercise_core.py.vechi.

NOTA MEDICALA: valorile sunt de DEMONSTRATIE, nu prescriptii clinice.
"""

import math

JOINT_NAMES = [
    "left_hip_joint", "left_knee_joint", "left_ankle_joint",
    "right_hip_joint", "right_knee_joint", "right_ankle_joint",
]

# VERSIUNEA DE CONVENTIE in care sunt scrise traiectoriile din acest fisier.
# Modelul poarta a lui in URDF (conventie_versiune). Cat timp cele doua difera,
# exercise_controller REFUZA sa ruleze: o traiectorie scrisa in alta conventie ar
# duce robotul in alt loc decat scrie pe ea, si ar face-o linistit.
# B0 = zero anatomic (M1). B1 = zero mecanic al dispozitivului (D1, 22 aug).
# Traiectoriile de mai jos sunt inca in B0; se reconvertesc la punctul 7.
CONVENTIE_TRAIECTORII = "B1"

# Cod de esec DISTINCT, ca un refuz de conventie sa nu poata fi confundat cu altceva.
COD_CONVENTIE = 7

LIMITS = {
    "hip":   (0.00000, 1.57080),   # 0..90 grade anatomic [PDF Tabel 3.1]
    "knee":  (0.00000, 2.44346),   # 0..140 grade anatomic [PDF Tabel 3.1]
    "ankle": (-0.61087, 0.61087),  # -35..+35 grade [PDF Tabel 3.1, split GAP 4]
}

# POSTURA INITIALA, RE-ANCORATA FIZIC pe 22 aug 2026 (conventia B-prim, D1).
#
# Nu mai e o fractie mostenita, ci POZITIA DE ASEZARE a pacientului, descrisa direct:
#   sold 0      coapsa pe sezut, orizontala. In B-prim zero CHIAR E repausul.
#   genunchi 90 gamba atarna vertical, talpa pe suport.
#   glezna 0    talpa perpendiculara pe gamba.
#
# Ce a fost inainte, si de ce a murit: la M1 soldul primise 35.22 grade, pastrand
# fractia 0.3913 din cursa veche. Fractia era o mostenire aritmetica, nu o postura:
# 35.22 nu descria nimic fizic, si in conventia noua ar fi insemnat coapsa ridicata
# la 35 de grade deasupra orizontalei, adica pacientul asezat cu genunchii in sus.
#
# Cele trei conditii sunt VERIFICATE, nu presupuse, in test/test_postura.py:
# apartenenta la banda de sezut, invariantul podelei, si FK-ul care arata gamba
# verticala.
import math as _math
POSTURA_INITIALA_DEG = {"hip": 0.0, "knee": 90.0, "ankle": 0.0}
POSTURA_INITIALA = {
    j: _math.radians(POSTURA_INITIALA_DEG[
        "hip" if "hip" in j else ("knee" if "knee" in j else "ankle")])
    for j in JOINT_NAMES}
VEL_MAX = 2.0   # rad/s -- limita servomotorului din URDF


def limit_of(joint_name: str):
    for k, lim in LIMITS.items():
        if k in joint_name:
            return lim
    raise ValueError(f"articulatie necunoscuta: {joint_name}")


def clamp(joint_name: str, value: float) -> float:
    lo, hi = limit_of(joint_name)
    return max(lo, min(hi, value))


def cosine_blend(a: float, b: float, s: float) -> float:
    """Interpolare cosinus: viteza zero la capete; v_max = (b-a)*pi/(2*T)."""
    s = max(0.0, min(1.0, s))
    return a + (b - a) * (1.0 - math.cos(math.pi * s)) / 2.0


class Program:
    """Lista de segmente (durata_s, tinte_partiale). Tintele nespecificate
    isi pastreaza pozitia. Valideaza la constructie viteza de varf."""

    def __init__(self, name: str, segments, reps: int = 1, q_init=None):
        self.name = name
        self.reps = max(1, int(reps))
        self.timeline = []     # (t_start, t_end, q_start{6}, q_end{6})
        q = dict(POSTURA_INITIALA)
        if q_init:
            for j, v in q_init.items():
                if j in q:
                    q[j] = clamp(j, float(v))
        t = 0.0
        for _ in range(self.reps):
            for dur, targets in segments:
                q_end = dict(q)
                for j, v in targets.items():
                    q_end[j] = clamp(j, float(v))
                for j in JOINT_NAMES:
                    dq = abs(q_end[j] - q[j])
                    if dq > 1e-9:
                        v_peak = dq * math.pi / (2.0 * dur)
                        if v_peak > VEL_MAX:
                            raise ValueError(
                                f"{name}: segment {dur}s cere {v_peak:.2f} rad/s "
                                f"pe {j} > limita {VEL_MAX}")
                self.timeline.append((t, t + dur, dict(q), q_end))
                q = q_end
                t += dur
        self.total_time = t
        self.q_final = q


class Player:
    def __init__(self, program: Program):
        self.p = program

    def sample(self, t: float):
        if t <= 0.0:
            _, _, q0, _ = self.p.timeline[0]
            return dict(q0), False
        if t >= self.p.total_time:
            return dict(self.p.q_final), True
        for t0, t1, q0, q1 in self.p.timeline:
            if t0 <= t < t1:
                s = (t - t0) / (t1 - t0)
                return {j: cosine_blend(q0[j], q1[j], s) for j in JOINT_NAMES}, False
        return dict(self.p.q_final), True


# ============================================================
# Segmente complete per exercitiu: _FULL[nume](reps) -> lista de segmente
# (include prolog/epilog acolo unde e nevoie; incepe si se termina la zero)
# ============================================================

def verdict_conventie(a_modelului, a_traiectoriilor=None):
    """Se pot rula traiectoriile pe modelul asta? NUCLEU PUR.

    Intoarce (permis, motiv). Un "nu stiu" NU e un "da": daca modelul nu declara
    nicio versiune, refuzul e tot refuz. Altfel gardianul ar fi ocolit exact de
    modelele vechi, adica de cele pentru care a fost facut."""
    mea = CONVENTIE_TRAIECTORII if a_traiectoriilor is None else a_traiectoriilor
    if not a_modelului:
        return (False, "modelul nu declara nicio versiune de conventie; traiectoriile "
                       "sunt scrise in %s. Refuz: nu pot verifica pe ce le rulez." % mea)
    if a_modelului != mea:
        return (False, "NEPOTRIVIRE DE CONVENTIE: modelul e in %s, traiectoriile in "
                       "%s. Refuz sa rulez. Unghiurile ar fi interpretate altfel decat "
                       "au fost scrise, si robotul s-ar misca in alta parte fara sa se "
                       "planga nimeni. Vezi DECIZII.md, D1."
                       % (a_modelului, mea))
    return (True, "conventie confirmata: model si traiectorii in %s" % mea)


def _both(d):
    out = {}
    for k, v in d.items():
        out[f"left_{k}_joint"] = v
        out[f"right_{k}_joint"] = v
    return out


# ---------- GLEZNA (cu ridicare prealabila a gambelor: knee 0.30) ----------
_LIFT = [(1.4, _both({"knee": 1.2708}))]
_LOWER = [(1.4, _both({"knee": 1.5708})), (0.5, {})]

def _full_ankle_pump(reps=3):
    rep = [
        (1.0, _both({"ankle": 0.45})),
        (1.8, _both({"ankle": -0.45})),
        (1.0, _both({"ankle": 0.00})),
        (0.4, {}),
    ]
    return _LIFT + rep * reps + _LOWER

def _full_ankle_alternating(reps=3):
    rep = [
        (1.5, {"left_ankle_joint": 0.45, "right_ankle_joint": -0.45}),
        (1.5, {"left_ankle_joint": -0.45, "right_ankle_joint": 0.45}),
        (1.2, _both({"ankle": 0.00})),
        (0.4, {}),
    ]
    return _LIFT + rep * reps + _LOWER

def _full_ankle_holds(reps=2):
    rep = [
        (1.5, _both({"ankle": 0.50})),
        (2.5, {}),                          # mentinere dorsiflexie
        (2.0, _both({"ankle": -0.50})),
        (2.5, {}),                          # mentinere plantarflexie
        (1.5, _both({"ankle": 0.00})),
        (0.5, {}),
    ]
    return _LIFT + rep * reps + _LOWER


# ---------- GENUNCHI ----------
def _full_knee_extension(reps=3):
    rep = [
        (2.5, _both({"knee": 0.1708, "ankle": 0.20})),
        (1.5, {}),
        (2.5, _both({"knee": 1.5708, "ankle": 0.00})),
        (1.0, {}),
    ]
    return rep * reps

def _full_knee_alternating(reps=2):
    rep = [
        (2.0, {"left_knee_joint": 0.1708, "left_ankle_joint": 0.20}),
        (1.0, {}),
        (2.0, {"left_knee_joint": 1.5708, "left_ankle_joint": 0.00}),
        (2.0, {"right_knee_joint": 0.1708, "right_ankle_joint": 0.20}),
        (1.0, {}),
        (2.0, {"right_knee_joint": 1.5708, "right_ankle_joint": 0.00}),
        (0.5, {}),
    ]
    return rep * reps

def _full_knee_pulses(reps=2):
    """Extensie la 1.0 rad, apoi pulsuri scurte 1.0 <-> 1.4 (intarire)."""
    pulse = [(0.8, _both({"knee": 0.1708})), (0.8, _both({"knee": 0.5708}))]
    rep = ([(2.0, _both({"knee": 0.5708, "ankle": 0.15}))]
           + pulse * 3
           + [(2.0, _both({"knee": 1.5708, "ankle": 0.00})), (0.5, {})])
    return rep * reps


# ---------- SOLD ----------
def _full_hip_raise(reps=3):
    rep = [
        (2.0, _both({"hip": 1.121955})),
        (1.5, {}),
        (2.0, _both({"hip": 0.000000})),
        (1.0, {}),
    ]
    return rep * reps

def _full_hip_alternating(reps=2):
    rep = [
        (1.8, {"left_hip_joint": 1.234167}),
        (0.8, {}),
        (1.8, {"left_hip_joint": 0.000000}),
        (1.8, {"right_hip_joint": 1.234167}),
        (0.8, {}),
        (1.8, {"right_hip_joint": 0.000000}),
        (0.4, {}),
    ]
    return rep * reps

def _full_hip_hold(reps=2):
    rep = [
        (2.2, _both({"hip": 1.346379})),
        (4.0, {}),                          # mentinere izometrica
        (2.2, _both({"hip": 0.000000})),
        (0.6, {}),
    ]
    return rep * reps


# ---------- COMBINATE ----------
def _full_alternating_march(reps=3):
    rep = [
        (1.6, {"left_hip_joint": 1.009743, "left_knee_joint": 1.2208}),
        (1.6, {"left_hip_joint": 0.000000, "left_knee_joint": 1.5708}),
        (1.6, {"right_hip_joint": 1.009743, "right_knee_joint": 1.2208}),
        (1.6, {"right_hip_joint": 0.000000, "right_knee_joint": 1.5708}),
    ]
    return rep * reps

def _full_full_extension(reps=2):
    rep = [
        (3.0, _both({"hip": 0.560895, "knee": 0.0708, "ankle": 0.15})),
        (2.5, {}),
        (3.0, _both({"hip": 0.000000, "knee": 1.5708, "ankle": 0.00})),
        (1.0, {}),
    ]
    return rep * reps

def _full_leg_wave(reps=2):
    """Val coordonat: sold -> genunchi -> glezna, apoi derulare inversa."""
    rep = [
        (1.8, _both({"hip": 0.785319})),
        (1.8, _both({"knee": 0.3708})),
        (1.2, _both({"ankle": 0.30})),
        (1.5, {}),
        (1.2, _both({"ankle": 0.00})),
        (1.8, _both({"knee": 1.5708})),
        (1.8, _both({"hip": 0.000000})),
        (0.5, {}),
    ]
    return rep * reps


_FULL = {
    "ankle_pump": _full_ankle_pump,
    "ankle_alternating": _full_ankle_alternating,
    "ankle_holds": _full_ankle_holds,
    "knee_extension": _full_knee_extension,
    "knee_alternating": _full_knee_alternating,
    "knee_pulses": _full_knee_pulses,
    "hip_raise": _full_hip_raise,
    "hip_alternating": _full_hip_alternating,
    "hip_hold": _full_hip_hold,
    "alternating_march": _full_alternating_march,
    "full_extension": _full_full_extension,
    "leg_wave": _full_leg_wave,
}

# SESIUNI: inlantuiri (exercitiu, repetari) pe grupe de articulatii
SESSIONS = {
    "ankle_session":    [("ankle_pump", 3), ("ankle_alternating", 3), ("ankle_holds", 2)],
    "knee_session":     [("knee_extension", 2), ("knee_alternating", 2), ("knee_pulses", 2)],
    "hip_session":      [("hip_raise", 2), ("hip_alternating", 2), ("hip_hold", 2)],
    "combined_session": [("leg_wave", 2), ("alternating_march", 3), ("full_extension", 2)],
}


def _make_builder(name, default_reps):
    def builder(reps=default_reps, q_init=None):
        prog = Program(name, _FULL[name](int(reps)), 1, q_init=q_init)
        prog.reps = int(reps)
        return prog
    return builder

_DEFAULT_REPS = {
    "ankle_pump": 3, "ankle_alternating": 3, "ankle_holds": 2,
    "knee_extension": 3, "knee_alternating": 2, "knee_pulses": 2,
    "hip_raise": 3, "hip_alternating": 2, "hip_hold": 2,
    "alternating_march": 3, "full_extension": 2, "leg_wave": 2,
}

EXERCISES = {n: _make_builder(n, d) for n, d in _DEFAULT_REPS.items()}


def build(name: str, reps: int, q_init=None) -> Program:
    """Construieste un exercitiu atomic, o sesiune SAU `neutral` (revenire
    lina la postura sezut din pozitia curenta -- folosit ca STOP).
    q_init = pozitia curenta a articulatiilor: traiectoria porneste de
    acolo (comutare live fara salt). Pentru sesiuni, `reps` repeta sesiunea."""
    if name == "neutral":
        # TINTA E POSTURA_INITIALA, nu zero pe toate articulatiile. Pana pe 22 aug
        # `neutral` ducea robotul la tot-zero, adica la piciorul complet INTINS -- nu
        # la postura de asezare a pacientului, care e chiar ce promite docstringul de
        # mai sus. Demo-ul porneste cu `neutral`, deci fiecare sesiune incepea in
        # extensie completa. Bugul e vizibil in conventia B-prim, unde zero pe genunchi
        # NU mai inseamna postura de lucru; in conventia veche coincideau.
        prog = Program("neutral",
                       [(2.0, dict(POSTURA_INITIALA)), (0.5, {})],
                       1, q_init=q_init)
        prog.reps = 1
        return prog
    if name in EXERCISES:
        return EXERCISES[name](reps, q_init=q_init)
    if name in SESSIONS:
        segs = []
        for ex, r in SESSIONS[name]:
            segs += _FULL[ex](r)
        prog = Program(name, segs, max(1, int(reps)), q_init=q_init)
        prog.reps = max(1, int(reps))
        return prog
    raise ValueError(
        f"necunoscut: {name}. Exercitii: {sorted(EXERCISES)}. "
        f"Sesiuni: {sorted(SESSIONS)}")


# ============================================================
# v3: AXELE DE AJUSTARE (prismatice) -- scaun + segmente telescopice
# ============================================================
ADJUST_JOINT_NAMES = [
    "seat_lift_joint",
    "left_thigh_ext_joint", "right_thigh_ext_joint",
    "left_shank_ext_joint", "right_shank_ext_joint",
]
ADJUST_LIMITS = {
    "seat_lift_joint": (0.0, 0.15),
    "left_thigh_ext_joint": (0.0, 0.08), "right_thigh_ext_joint": (0.0, 0.08),
    "left_shank_ext_joint": (0.0, 0.08), "right_shank_ext_joint": (0.0, 0.08),
}
ADJUST_VEL = 0.03   # m/s -- viteza de ajustare (axe lente, de reglaj)

# Regula de cuplare (garda la sol, demonstrata prin FK): extensia gambei
# coboara glezna, deci e permisa doar daca scaunul e ridicat suficient:
#     shank_ext <= seat_lift + SHANK_EXT_MARGIN
SHANK_EXT_MARGIN = 0.03


def clamp_adjust(targets: dict) -> dict:
    """Taie tintele de ajustare la limite SI impune regula de cuplare.
    Returneaza dict complet (toate cele 5 axe) cu valori sigure."""
    out = {}
    for j in ADJUST_JOINT_NAMES:
        lo, hi = ADJUST_LIMITS[j]
        out[j] = max(lo, min(hi, float(targets.get(j, 0.0))))
    cap = out["seat_lift_joint"] + SHANK_EXT_MARGIN
    for j in ("left_shank_ext_joint", "right_shank_ext_joint"):
        out[j] = min(out[j], cap)
    return out
