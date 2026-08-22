#!/usr/bin/env python3
"""test_supervizor.py -- stratul electric contra REALITATII modelului.

supervizor_core.py se testeaza singur pe numere alese. Aici se verifica lucrurile pe
care numai robotul real le poate infirma:

  1. limitele se CITESC din URDF si sunt cele asteptate;
  2. pragul de sezut din nod COINCIDE cu proprietatea din xacro. Valoarea nu poate fi
     citita din URDF-ul generat (acela poarta doar postura activa), deci exista in
     doua locuri. In loc de o a doua copie tacuta, aici e o asertie care pica daca se
     despart;
  3. pragurile electrice incap in limitele mecanice ale ROBOTULUI ASTA, nu ale unuia
     inventat pentru test;
  4. postura de pornire nu declanseaza -- pe datele reale, nu pe cele din selftest.

Rulare: python3 test/test_supervizor.py
"""
import math
import os
import subprocess
import sys
import tempfile

AICI = os.path.dirname(os.path.abspath(__file__))
PACHET = os.path.dirname(AICI)
sys.path.insert(0, os.path.join(PACHET, "scripts"))
XACRO_SRC = os.path.join(PACHET, "urdf", "rehab_exo.urdf.xacro")

import supervizor_core as sc                                       # noqa: E402
from supervizor_electric import (ARTICULATII, limite_din_urdf,     # noqa: E402
                                 limite_sezut)


def _urdf(*arg):
    f = tempfile.NamedTemporaryFile(suffix=".urdf", delete=False)
    f.close()
    p = subprocess.run(["xacro", XACRO_SRC] + list(arg) + ["-o", f.name],
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError("xacro a picat: %s" % p.stderr[:400])
    return f.name


def _proprietate_xacro(nume):
    """Citeste o <xacro:property> din sursa. Deliberat naiv: daca formatul se
    schimba, testul PICA in loc sa ghiceasca."""
    import re
    s = open(XACRO_SRC).read()
    m = re.search(r'<xacro:property\s+name="%s"\s+value="([^"]+)"' % nume, s)
    if not m:
        raise AssertionError("nu gasesc proprietatea '%s' in xacro" % nume)
    return float(m.group(1))


def main(argv):
    n = [0]

    def ok(c, m):
        if not c:
            print("ESEC: %s" % m)
            raise SystemExit(1)
        n[0] += 1

    lim = limite_din_urdf(_urdf())

    # 1. toate cele sase articulatii, cu limite finite
    ok(len(lim) == 6, "trebuie 6 articulatii, am %d" % len(lim))
    for j, (lo, hi) in lim.items():
        ok(hi > lo, "%s: limita superioara trebuie sa fie peste cea inferioara" % j)
    ok(abs(lim["left_hip_joint"][1] - math.radians(90.0)) < 1e-4,
       "soldul trebuie sa aiba maxim 90 de grade")
    ok(abs(lim["left_knee_joint"][1] - math.radians(140.0)) < 1e-4,
       "genunchiul trebuie sa aiba maxim 140 de grade")

    # 2. ASERTIA CARE TINE LOC DE A DOUA COPIE
    # AMBELE capete acum: la flip-ul de conventie banda de sezut a capatat si un
    # maxim propriu. Asertia a prins deja o despartire reala pe 22 aug, cand xacro
    # trecuse pe valorile transportate si nodul ramasese pe cele vechi.
    for nume, implicit_nod in (("sold_sezut_min_deg", 0.0),
                               ("sold_sezut_max_deg", 25.0)):
        din_xacro = _proprietate_xacro(nume)
        ok(abs(din_xacro - implicit_nod) < 1e-9,
           "%s s-a despartit: xacro spune %.3f, nodul %.3f. Se schimba AMBELE sau "
           "niciunul." % (nume, din_xacro, implicit_nod))

    # 3. sezutul atinge DOAR soldurile
    lim_s = limite_sezut(lim, math.radians(_proprietate_xacro("sold_sezut_min_deg")),
                         math.radians(_proprietate_xacro("sold_sezut_max_deg")))
    for j in lim:
        if j.endswith("_hip_joint"):
            ok(lim_s[j] != lim[j], "%s: sezutul trebuie sa schimbe fereastra" % j)
            ok(lim_s[j][1] < lim[j][1],
               "%s: sezutul trebuie sa REDUCA fereastra, nu doar sa o mute -- e "
               "chiar ce spune documentul despre inelul de oprire" % j)
            ok(lim_s[j][0] >= lim[j][0],
               "%s: capatul de jos se PASTREAZA (submultime, nu deplasare)" % j)
        else:
            ok(lim_s[j] == lim[j], "%s NU are voie sa se schimbe la sezut" % j)

    # 4. pragurile electrice incap in limitele mecanice ALE ACESTUI robot, in ambele
    # posturi, la marja implicita
    for eticheta, L in (("culcat", lim), ("sezut", lim_s)):
        P = sc.praguri_electrice(L)
        for j, (lo, hi) in P.items():
            # D2: marje PER CAPAT. Jos pragul coincide cu limita mecanica (repausul
            # nu e zona interzisa), sus e strict inauntru.
            ok(abs(lo - L[j][0]) < 1e-12,
               "%s/%s: jos pragul trebuie sa coincida cu limita mecanica" % (eticheta, j))
            ok(hi < L[j][1],
               "%s/%s: sus pragul trebuie sa fie strict inauntru" % (eticheta, j))
            ok(hi - lo >= 2 * sc.BANDA_ARMARE_RAD,
               "%s/%s: fereastra prea ingusta pentru banda de armare" % (eticheta, j))

    # 5. POSTURA DE PORNIRE, pe date reale: articulatiile apar la 0.0, iar soldul si
    # genunchiul au minimul mecanic tot 0.0 -- deci pornirea E pe margine. Nimic nu
    # are voie sa declanseze, si asta e chiar motivul pentru care exista armarea.
    ok(abs(lim["left_hip_joint"][0]) < 1e-9,
       "premisa testului: minimul soldului e 0.0 (daca se schimba, revizuieste)")
    s = sc.Supervizor(sc.praguri_electrice(lim))
    boot = {j: 0.0 for j in ARTICULATII}
    for _ in range(100):
        ok(not s.pas(boot), "pornirea la 0.0 NU are voie sa declanseze")
    ok(s.stare["left_hip_joint"] == sc.NEARMAT, "soldul ramane nearmat la pornire")

    # 6. POSTURA_INITIALA E CHIAR PE MARGINE, si asta e acum situatia normala, nu un
    # caz limita. De la re-ancorarea din 22 aug soldul sta la 0, adica exact capatul
    # de jos al benzii, deci SUB pragul electric. Un supervizor fara armare ar
    # declansa la fiecare asezare a pacientului.
    # Se cere deci: zero declansari, si soldul NEARMAT PRIN PROIECTARE -- nu "armat",
    # cum cerea versiunea de dinainte, cand postura era la 35.22 grade.
    import exercise_core as ec
    lim_sez = limite_sezut(lim, math.radians(_proprietate_xacro("sold_sezut_min_deg")),
                           math.radians(_proprietate_xacro("sold_sezut_max_deg")))
    for lim_post, et in ((lim, "culcat"), (lim_sez, "sezut")):
        s2 = sc.Supervizor(sc.praguri_electrice(lim_post))
        for _ in range(50):
            ok(not s2.pas(ec.POSTURA_INITIALA),
               "%s: POSTURA_INITIALA nu are voie sa declanseze, niciodata" % et)
        for j in ("left_hip_joint", "right_hip_joint"):
            ok(s2.stare[j] == sc.NEARMAT,
               "%s: %s ar trebui NEARMAT la postura initiala (e chiar pe capat, iar "
               "banda de armare cere sa se intre mai adanc)" % (et, j))
        for j in ("left_knee_joint", "right_knee_joint"):
            ok(s2.stare[j] == sc.ARMAT,
               "%s: genunchiul la 90 de grade e bine inauntru, deci SE armeaza" % et)
    # ... iar dupa ce soldul intra in zona sigura, se armeaza si poate declansa
    s3 = sc.Supervizor(sc.praguri_electrice(lim))
    s3.pas(dict(ec.POSTURA_INITIALA, left_hip_joint=math.radians(30.0),
                right_hip_joint=math.radians(30.0)))
    ok(s3.stare["left_hip_joint"] == sc.ARMAT,
       "dupa ce intra la 30 de grade soldul trebuie sa se armeze")
    ok(len(s3.pas(dict(ec.POSTURA_INITIALA, left_hip_joint=math.radians(88.0),
                       right_hip_joint=math.radians(88.0)))) == 2,
       "odata armat, soldul trebuie sa poata declansa")

    print("test_supervizor: %d verificari OK (limite din URDF, pragul de sezut "
          "sincron cu xacro, pornire pe margine)." % n[0])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
