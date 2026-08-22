#!/usr/bin/env python3
"""test_postura.py -- POSTURA_INITIALA, verificata pe cele trei conditii.

Valoarea propusa (sold 0, genunchi 90, glezna 0) e pozitia fizica de asezare a
pacientului. Nu se ia pe incredere: daca vreuna din cele trei conditii pica, atunci
ori postura, ori banda de sezut, ori geometria e gresita, si testul trebuie sa spuna
CARE -- nu sa netezeasca.

  (i)   e in interiorul benzii de sezut re-justificate la P2.1;
  (ii)  invariantul podelei trece in ea si pe tot drumul spre ea;
  (iii) FK-ul arata gamba VERTICALA, adica postura chiar e ce spune ca e.

Se verifica in plus RAMPA de la aparitie: robotul apare cu toate articulatiile la 0,
iar drumul pana la POSTURA_INITIALA trebuie sa fie legal in FIECARE punct, nu doar la
capete. O rampa care iese din limite la mijloc ar fi invizibila intr-un test care se
uita doar la destinatie.

Rulare: python3 test/test_postura.py
"""
import math
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

import numpy as np

AICI = os.path.dirname(os.path.abspath(__file__))
PACHET = os.path.dirname(AICI)
sys.path.insert(0, os.path.join(PACHET, "scripts"))
sys.path.insert(0, AICI)

import exercise_core as ec                                          # noqa: E402
import geometrie_core as gc                                         # noqa: E402
from test_podea import _fk, _model, _puncte_critice, _urdf          # noqa: E402

PARTI = ("left", "right")


def main(argv):
    n = [0]

    def ok(c, m):
        if not c:
            print("ESEC: %s" % m)
            raise SystemExit(1)
        n[0] += 1

    ctrl = "controllers:=%s" % os.path.join(PACHET, "config", "controllers.yaml")
    J, lim = _model(_urdf(ctrl))
    J_s, lim_s = _model(_urdf("postura:=sezut", ctrl))
    c = gc.cote()
    P = ec.POSTURA_INITIALA_DEG
    print("  POSTURA_INITIALA: sold %.2f, genunchi %.2f, glezna %.2f grade"
          % (P["hip"], P["knee"], P["ankle"]))

    # --- (i) IN BANDA DE SEZUT. Daca pica, una din cele doua e gresita si NU se
    # netezeste: se raporteaza contradictia.
    for art, cheie in (("hip", "hip"), ("knee", "knee"), ("ankle", "ankle")):
        v = math.radians(P[cheie])
        lo, hi = lim_s["left_%s_joint" % art]
        ok(lo - 1e-12 <= v <= hi + 1e-12,
           "CONTRADICTIE: POSTURA_INITIALA are %s la %.2f grade, in afara benzii de "
           "sezut %.2f..%.2f. Ori postura, ori banda e gresita; nu le impac aici."
           % (art, P[cheie], math.degrees(lo), math.degrees(hi)))
    print("  (i)  in banda de sezut: sold %.2f..%.2f grade, valoarea %.2f -- OK"
          % (math.degrees(lim_s["left_hip_joint"][0]),
             math.degrees(lim_s["left_hip_joint"][1]), P["hip"]))

    # --- (ii) INVARIANTUL PODELEI, in postura SI pe tot drumul spre ea.
    def q_la(f):
        """Rampa liniara de la aparitie (toate zero) la POSTURA_INITIALA."""
        o = {}
        for p in PARTI:
            for art in ("hip", "knee", "ankle"):
                o["%s_%s_joint" % (p, art)] = f * math.radians(P[art])
        return o

    z_min, unde = 1e9, None
    PASI = 51
    for k in range(PASI):
        for nume, z in _puncte_critice(_fk(J, q_la(k / (PASI - 1.0))), c):
            if z < z_min:
                z_min, unde = z, "%s la fractia %.2f" % (nume, k / (PASI - 1.0))
    ok(z_min >= c["margine_podea"],
       "pe rampa spre POSTURA_INITIALA un punct coboara la %.4f m (%s), sub marginea "
       "de %.3f" % (z_min, unde, c["margine_podea"]))
    print("  (ii) rampa in %d pasi: cel mai jos punct %+.4f m (%s) -- OK"
          % (PASI, z_min, unde))

    # --- rampa e si LEGALA in fiecare punct, nu doar la capete
    for k in range(PASI):
        q = q_la(k / (PASI - 1.0))
        for j, v in q.items():
            lo, hi = lim[j]
            ok(lo - 1e-9 <= v <= hi + 1e-9,
               "rampa iese din limite la fractia %.2f: %s la %.4f, permis %.4f..%.4f"
               % (k / (PASI - 1.0), j, v, lo, hi))

    # --- (iii) FK: gamba chiar e VERTICALA. Dovada numerica, nu o afirmatie.
    T = _fk(J, q_la(1.0))
    for p in PARTI:
        genunchi = T["%s_shank" % p][0]
        glezna = T["%s_foot" % p][0]
        d = glezna - genunchi
        ok(abs(d[0]) < 1e-9 and abs(d[1]) < 1e-9,
           "%s: gamba nu e verticala, are componente orizontale (%.2e, %.2e)"
           % (p, d[0], d[1]))
        ok(d[2] < 0, "%s: gamba trebuie sa coboare, nu sa urce" % p)
        sold = T["%s_thigh" % p][0]
        ok(abs(genunchi[2] - sold[2]) < 1e-9,
           "%s: coapsa nu e orizontala la sold zero" % p)
    d = T["left_foot"][0] - T["left_shank"][0]
    print("  (iii) gamba: componente orizontale %.1e / %.1e, verticala %+.4f m -- OK"
          % (d[0], d[1], d[2]))

    print("test_postura: %d verificari OK (in banda, rampa legala si deasupra "
          "podelei, gamba verticala dovedita prin FK)." % n[0])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
