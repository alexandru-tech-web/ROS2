#!/usr/bin/env python3
"""test_repaus_pe_limita.py -- REGRESIE NUMITA: repausul nu are voie sa cada PE limita.

MECANISMUL, dovedit pe 22 aug 2026 prin A/B cu o singura variabila:

  Soldul se odihneste exact PE limita lui inferioara (0 grade), acolo unde gravitatia
  il impinge cand coapsa e orizontala. Constrangerea de limita din solverul de fizica
  tine articulatia, iar comanda de viteza a lui gz_ros2_control nu o poate elibera:
  JTC raporteaza reference 1.346379, feedback -9.1e-14, error 1.346379, pe o interfata
  pe care o detine singur. Comanda pleaca si nu ajunge in fizica.

  Genunchiul NU pateste asta fiindca aceeasi gravitatie il impinge DINSPRE limita lui,
  spre flexie.

DOVADA (o variabila, restul identic):
  limita inferioara a soldului = 0 grade   -> comanda 1.3464 rad, soldul ramane 0.0000
  limita inferioara a soldului = -3 grade  -> aceeasi comanda, soldul ajunge 1.3464

REGULA pe care o aserteaza testul: pozitia de repaus a fiecarei articulatii actionate
trebuie sa fie STRICT in interiorul limitelor ei, cu o rezerva declarata. Nu e o
subtilitate de simulator: pe un dispozitiv real, o masina care se odihneste pe propriul
opritor mecanic isi macina opritorul si nu are unde sa se duca la pornire.

Rulare: python3 test/test_repaus_pe_limita.py
"""
import math
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

AICI = os.path.dirname(os.path.abspath(__file__))
PACHET = os.path.dirname(AICI)
sys.path.insert(0, os.path.join(PACHET, "scripts"))

import exercise_core as ec                                        # noqa: E402

# Rezerva ceruta intre repaus si limita. 2 grade: mai mult decat orice zgomot de
# solver (masurat 9e-14) si mai putin decat banda de armare a supervizorului, ca sa
# nu interactioneze cu ea.
REZERVA_RAD = math.radians(2.0)
ARTICULATII = ("hip", "knee", "ankle")
PARTI = ("left", "right")


def _urdf(*arg):
    f = tempfile.NamedTemporaryFile(suffix=".urdf", delete=False)
    f.close()
    p = subprocess.run(["xacro", os.path.join(PACHET, "urdf", "rehab_exo.urdf.xacro")]
                       + list(arg) + ["-o", f.name], capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError("xacro a picat: %s" % p.stderr[:300])
    return f.name


def limite(cale):
    r = ET.parse(cale).getroot()
    out = {}
    for j in r.findall("joint"):
        li = j.find("limit")
        if li is not None and j.get("type") == "revolute":
            out[j.get("name")] = (float(li.get("lower")), float(li.get("upper")))
    return out


def main(argv):
    n = [0]
    rele = []

    def ok(c, m):
        if not c:
            print("ESEC: %s" % m)
            raise SystemExit(1)
        n[0] += 1

    ctrl = "controllers:=%s" % os.path.join(PACHET, "config", "controllers.yaml")
    for postura in ("culcat", "sezut"):
        lim = limite(_urdf("postura:=%s" % postura, ctrl))
        for p in PARTI:
            for a in ARTICULATII:
                j = "%s_%s_joint" % (p, a)
                if j not in lim:
                    continue
                lo, hi = lim[j]
                v = ec.POSTURA_INITIALA[j]
                jos, sus = v - lo, hi - v
                if jos < REZERVA_RAD or sus < REZERVA_RAD:
                    rele.append((postura, j, math.degrees(v), math.degrees(lo),
                                 math.degrees(hi), math.degrees(min(jos, sus))))
                n[0] += 1

    if rele:
        print("  ARTICULATII CU REPAUSUL PE LIMITA (rezerva ceruta %.1f grade):"
              % math.degrees(REZERVA_RAD))
        print("  %-8s %-20s %8s %8s %8s %9s" %
              ("postura", "articulatie", "repaus", "min", "max", "rezerva"))
        for postura, j, v, lo, hi, rez in rele:
            print("  %-8s %-20s %8.2f %8.2f %8.2f %9.2f" % (postura, j, v, lo, hi, rez))
        print()
        print("ESEC: %d articulatii se odihnesc pe limita. Vezi antetul acestui fisier "
              "pentru mecanism si dovada." % len(rele))
        return 1

    print("test_repaus_pe_limita: %d verificari OK (nicio articulatie nu se odihneste "
          "pe limita, in nicio postura)." % n[0])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
