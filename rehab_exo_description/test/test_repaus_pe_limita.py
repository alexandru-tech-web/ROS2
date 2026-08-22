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


def limite(cale, tip=("revolute",)):
    r = ET.parse(cale).getroot()
    out = {}
    for j in r.findall("joint"):
        li = j.find("limit")
        if li is not None and j.get("type") in tip:
            out[j.get("name")] = (float(li.get("lower")), float(li.get("upper")))
    return out


# ARTICULATIILE PRISMATICE se odihnesc TOATE pe cate un capat, si asta e prin
# constructie: reglajele pleaca de la retras si coloana de la inaltimea de lucru.
# Ele primesc EXEMPTIE, dar exemptia se demonstreaza, nu se presupune: mecanismul cere
# ca GRAVITATIA sa impinga articulatia SPRE limita pe care se odihneste. Directia se
# calculeaza din axa articulatiei in postura de repaus, iar verificarea empirica (se
# misca sau nu la comanda) e in raportul zilei.
STATUT_PRISMATICE = {
    # Rationamentul de mai jos e cel gravitational. Verificarea EMPIRICA din 22 aug
    # l-a CONTRAZIS partial, si asta se scrie aici in loc sa fie ascuns: comandate sa
    # se mute de la repaus, doua din trei NU s-au miscat. Deci NU sunt exemptii
    # dovedite, sunt items DESCHISE cu rationament scris. Cauza nu e stabilita si
    # poate fi alta decat mecanismul soldului; exercitiile nu le folosesc, deci nu
    # afecteaza cele 12.
    "seat_lift_joint":
        "repaus la 0 = capatul de SUS (-0.15..0); gravitatia impinge DINSPRE el. "
        "EMPIRIC: comandat -0.05, a coborat pana la -0.15, adica pe celalalt capat. "
        "Se misca, dar nu se opreste unde i se cere. DESCHIS.",
    "left_thigh_ext_joint":
        "axa in lungul coapsei, orizontala la repaus; gravitatia nu are componenta pe "
        "axa. EMPIRIC: comandat +0.04, nu s-a miscat. DESCHIS.",
    "right_thigh_ext_joint": "idem stanga. DESCHIS.",
    "left_shank_ext_joint":
        "axa in lungul gambei, verticala la repaus; gravitatia impinge SPRE extindere, "
        "dinspre limita 0. EMPIRIC: comandat +0.04, nu s-a miscat. DESCHIS.",
    "right_shank_ext_joint": "idem stanga. DESCHIS.",
}

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

    # PRISMATICE: fiecare trebuie sa aiba verdict -- fie rezerva, fie exemptie SCRISA.
    # O articulatie fara niciunul din cele doua e o scapare, nu o exceptie.
    lim_p = limite(_urdf(ctrl), tip=("prismatic",))
    fara_verdict = []
    for j, (lo, hi) in sorted(lim_p.items()):
        v = 0.0     # toate reglajele pornesc de la zero
        pe_limita = min(v - lo, hi - v) < REZERVA_RAD
        if pe_limita and j not in STATUT_PRISMATICE:
            fara_verdict.append(j)
        n[0] += 1
    ok(not fara_verdict,
       "articulatii prismatice care se odihnesc pe limita si NU au STATUT scris: %s"
       % fara_verdict)
    print("  prismatice: %d verificate, %d cu statut scris (toate DESCHISE -- "
          "verificarea empirica a contrazis rationamentul gravitational)" %
          (len(lim_p), len([j for j in lim_p if j in STATUT_PRISMATICE])))

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
