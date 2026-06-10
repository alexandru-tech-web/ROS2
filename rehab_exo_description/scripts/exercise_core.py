#!/usr/bin/env python3
"""
exercise_core.py — Nucleul procesului de control al celor 6 servomotoare
(2 sold + 2 genunchi + 2 glezna), FARA dependinte ROS.  [v2: sesiuni]

Straturi: program -> traiectorie cosinus (viteza zero la capete) ->
siguranta (clamp + validare viteza) -> Player.sample(t).

REPERTORIU v2 — 12 exercitii atomice + 4 SESIUNI pe grupe:
  glezna:   ankle_pump, ankle_alternating, ankle_holds
  genunchi: knee_extension, knee_alternating, knee_pulses
  sold:     hip_raise, hip_alternating, hip_hold
  combinat: alternating_march, full_extension, leg_wave
  SESIUNI:  ankle_session, knee_session, hip_session, combined_session
            (inlantuiri de exercitii; fiecare exercitiu incepe si se
             termina in postura neutra, deci cusatura e continua)

Siguranta specifica gleznei: exercitiile de glezna ridica intai usor
gambele (genunchi +0.30 rad) inainte de plantarflexie, astfel incat
varful pantofului sa nu coboare sub nivelul podelei — verificat prin
FK pe punctele varf/calcai ale placii de picior.

Conventia de semn (identica cu URDF v2):
  hip   +  = ridica coapsa            [-0.45 .. +0.70] rad
  knee  +  = extensie (gamba in fata) [ 0.00 .. +1.75] rad
  ankle +  = dorsiflexie (varf sus)   [-0.60 .. +0.60] rad

NOTA MEDICALA: valorile sunt de DEMONSTRATIE, nu prescriptii clinice.
"""

import math

JOINT_NAMES = [
    "left_hip_joint", "left_knee_joint", "left_ankle_joint",
    "right_hip_joint", "right_knee_joint", "right_ankle_joint",
]

LIMITS = {
    "hip":   (-0.45, 0.70),
    "knee":  (0.00, 1.75),
    "ankle": (-0.60, 0.60),
}
VEL_MAX = 2.0   # rad/s — limita servomotorului din URDF


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

    def __init__(self, name: str, segments, reps: int = 1):
        self.name = name
        self.reps = max(1, int(reps))
        self.timeline = []     # (t_start, t_end, q_start{6}, q_end{6})
        q = {j: 0.0 for j in JOINT_NAMES}
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

def _both(d):
    out = {}
    for k, v in d.items():
        out[f"left_{k}_joint"] = v
        out[f"right_{k}_joint"] = v
    return out


# ---------- GLEZNA (cu ridicare prealabila a gambelor: knee 0.30) ----------
_LIFT = [(1.4, _both({"knee": 0.30}))]
_LOWER = [(1.4, _both({"knee": 0.00})), (0.5, {})]

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
        (2.5, _both({"knee": 1.40, "ankle": 0.20})),
        (1.5, {}),
        (2.5, _both({"knee": 0.00, "ankle": 0.00})),
        (1.0, {}),
    ]
    return rep * reps

def _full_knee_alternating(reps=2):
    rep = [
        (2.0, {"left_knee_joint": 1.40, "left_ankle_joint": 0.20}),
        (1.0, {}),
        (2.0, {"left_knee_joint": 0.00, "left_ankle_joint": 0.00}),
        (2.0, {"right_knee_joint": 1.40, "right_ankle_joint": 0.20}),
        (1.0, {}),
        (2.0, {"right_knee_joint": 0.00, "right_ankle_joint": 0.00}),
        (0.5, {}),
    ]
    return rep * reps

def _full_knee_pulses(reps=2):
    """Extensie la 1.0 rad, apoi pulsuri scurte 1.0 <-> 1.4 (intarire)."""
    pulse = [(0.8, _both({"knee": 1.40})), (0.8, _both({"knee": 1.00}))]
    rep = ([(2.0, _both({"knee": 1.00, "ankle": 0.15}))]
           + pulse * 3
           + [(2.0, _both({"knee": 0.00, "ankle": 0.00})), (0.5, {})])
    return rep * reps


# ---------- SOLD ----------
def _full_hip_raise(reps=3):
    rep = [
        (2.0, _both({"hip": 0.50})),
        (1.5, {}),
        (2.0, _both({"hip": 0.00})),
        (1.0, {}),
    ]
    return rep * reps

def _full_hip_alternating(reps=2):
    rep = [
        (1.8, {"left_hip_joint": 0.55}),
        (0.8, {}),
        (1.8, {"left_hip_joint": 0.00}),
        (1.8, {"right_hip_joint": 0.55}),
        (0.8, {}),
        (1.8, {"right_hip_joint": 0.00}),
        (0.4, {}),
    ]
    return rep * reps

def _full_hip_hold(reps=2):
    rep = [
        (2.2, _both({"hip": 0.60})),
        (4.0, {}),                          # mentinere izometrica
        (2.2, _both({"hip": 0.00})),
        (0.6, {}),
    ]
    return rep * reps


# ---------- COMBINATE ----------
def _full_alternating_march(reps=3):
    rep = [
        (1.6, {"left_hip_joint": 0.45, "left_knee_joint": 0.35}),
        (1.6, {"left_hip_joint": 0.0, "left_knee_joint": 0.0}),
        (1.6, {"right_hip_joint": 0.45, "right_knee_joint": 0.35}),
        (1.6, {"right_hip_joint": 0.0, "right_knee_joint": 0.0}),
    ]
    return rep * reps

def _full_full_extension(reps=2):
    rep = [
        (3.0, _both({"hip": 0.25, "knee": 1.50, "ankle": 0.15})),
        (2.5, {}),
        (3.0, _both({"hip": 0.00, "knee": 0.00, "ankle": 0.00})),
        (1.0, {}),
    ]
    return rep * reps

def _full_leg_wave(reps=2):
    """Val coordonat: sold -> genunchi -> glezna, apoi derulare inversa."""
    rep = [
        (1.8, _both({"hip": 0.35})),
        (1.8, _both({"knee": 1.20})),
        (1.2, _both({"ankle": 0.30})),
        (1.5, {}),
        (1.2, _both({"ankle": 0.00})),
        (1.8, _both({"knee": 0.00})),
        (1.8, _both({"hip": 0.00})),
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
    def builder(reps=default_reps):
        prog = Program(name, _FULL[name](int(reps)), 1)
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


def build(name: str, reps: int) -> Program:
    """Construieste un exercitiu atomic SAU o sesiune intreaga.
    Pentru sesiuni, `reps` = de cate ori se repeta intreaga sesiune."""
    if name in EXERCISES:
        return EXERCISES[name](reps)
    if name in SESSIONS:
        segs = []
        for ex, r in SESSIONS[name]:
            segs += _FULL[ex](r)
        prog = Program(name, segs, max(1, int(reps)))
        prog.reps = max(1, int(reps))
        return prog
    raise ValueError(
        f"necunoscut: {name}. Exercitii: {sorted(EXERCISES)}. "
        f"Sesiuni: {sorted(SESSIONS)}")
