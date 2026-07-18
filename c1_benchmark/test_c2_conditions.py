#!/usr/bin/env python3
"""test_c2_conditions.py -- selftest PUR PYTHON pentru conditiile C2 (fara ROS,
fara retea). Reconstruieste comanda netem pentru FIECARE conditie noua prin
ramura 'gilbert' EXISTENTA din bench_core.netem_cmd si verifica:
  1. (p, r) stocate == tabelul din c2_planning/CALIBRARE_GE_C2.md;
  2. comanda netem la formatul EXACT de afisare (netem_cmd, %.3f);
  3. rata medie implicita L=p/(p+r) si lungimea rafalei B=1/r == tinta grilei.
Rulare: python3 test_c2_conditions.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bench_core import CONDITIONS, netem_cmd

IFACE = "IFACE"

# Tabelul de referinta, transcris din c2_planning/CALIBRARE_GE_C2.md:
#   name -> (p, r, L_target, B_target)
# bern_L: Bernoulli via gemodel r=1-p (B_target ~ 1/(1-L), aprox 1). B tinta = None
#   (nu se verifica exact; se verifica L). ge_L_B: r=1/B, p=L/(B*(1-L)).
REF = {
    "bern_5":  (0.05,     0.95,     0.05, None),
    "bern_15": (0.15,     0.85,     0.15, None),
    "bern_30": (0.30,     0.70,     0.30, None),
    "ge_5_3":  (0.017544, 0.333333, 0.05, 3),
    "ge_5_8":  (0.006579, 0.125,    0.05, 8),
    "ge_15_3": (0.058824, 0.333333, 0.15, 3),
    "ge_15_8": (0.022059, 0.125,    0.15, 8),
    "ge_30_3": (0.142857, 0.333333, 0.30, 3),
    "ge_30_8": (0.053571, 0.125,    0.30, 8),
}


def expected_cmd(p, r):
    """Comanda asteptata, la formatul de afisare al ramurii gilbert (%.3f)."""
    return ("tc qdisc replace dev %s root netem delay 0ms 0ms "
            "loss gemodel %.3f%% %.3f%% 100%% 0%%" % (IFACE, 100 * p, 100 * r))


def run():
    by_name = {c["name"]: c for c in CONDITIONS}
    checks = 0
    fails = []
    for name, (p, r, L_t, B_t) in REF.items():
        if name not in by_name:
            fails.append("%s: LIPSA din CONDITIONS" % name); continue
        c = by_name[name]
        # 1. (p, r) stocate == referinta
        if c.get("p") != p or c.get("r") != r:
            fails.append("%s: (p,r)=(%s,%s) != ref (%s,%s)"
                         % (name, c.get("p"), c.get("r"), p, r))
        # 2. comanda netem la formatul exact
        got = netem_cmd(IFACE, c)
        exp = expected_cmd(p, r)
        if got != exp:
            fails.append("%s: cmd\n    got: %s\n    exp: %s" % (name, got, exp))
        # 3. L si B implicite == tinta
        L = p / (p + r)
        if abs(L - L_t) > 0.003:            # 0.3 pp toleranta pe rata medie
            fails.append("%s: L=%.4f != tinta %.2f" % (name, L, L_t))
        if B_t is not None:
            B = 1.0 / r
            if abs(B - B_t) > 0.01:
                fails.append("%s: B=%.3f != tinta %d" % (name, B, B_t))
        checks += 1
    # 4. bench_core NU a fost stricat: gilbert_* / lat200_* raman
    for must in ("ideal", "gilbert_20", "lat200_jit50", "lat200_l15"):
        if must not in by_name:
            fails.append("REGRES: %s a disparut din CONDITIONS" % must)
    # 5. B=1 corect ELIMINAT (nu exista ge_*_1)
    if any(n.startswith("ge_") and n.endswith("_1") for n in by_name):
        fails.append("B=1 ar fi trebuit eliminat, dar exista o ge_*_1")

    if fails:
        print("FAIL (%d/%d conditii verificate):" % (checks, len(REF)))
        for f in fails:
            print("  - " + f)
        return 1
    print("SELFTEST C2 OK: %d conditii verificate (p,r + comanda netem + L,B)." % checks)
    print("Comenzi reconstruite (format campanie netem_cmd, %.3f):")
    for name in REF:
        print("  %-8s %s" % (name, netem_cmd(IFACE, by_name[name])))
    return 0


if __name__ == "__main__":
    sys.exit(run())
