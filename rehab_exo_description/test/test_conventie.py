#!/usr/bin/env python3
"""test_conventie.py -- schimbarea de conventie NU a schimbat robotul.

M1 muta zeroul articular de la conventia mostenita ('zero = SEZUT') la zeroul
ANATOMIC (decizia B din registru, 18 aug). O schimbare de conventie e, prin
definitie, o REETICHETARE: acelasi unghi fizic primeste alt numar. Daca pe drum
se schimba si geometria, twin-ul devine alt robot fara ca nimeni sa observe --
exact ce s-a intamplat la Valul 1 cu semnul aplicat pe <axis>, prins doar de
invariantul numeric.

DOVADA e cinematica, nu textuala: pentru fiecare punct de test, se calculeaza
pozitia si orientarea talpii in descrierea VECHE (attic/rehab_exo.urdf.livrat, la
unghiul vechi) si in cea NOUA (la unghiul convertit). Trebuie sa coincida.

MAPAREA (derivata din geometrie, nu presupusa):
    sold_nou     = sold_vechi + 90 grade
    genunchi_nou = 90 grade - genunchi_vechi      (INVERSARE DE SEMN)
    glezna_noua  = glezna_veche
Justificare: la q=0 in conventia veche coapsa arata spre +X (orizontal) iar gamba
spre -Z (vertical in jos) -- postura sezut. Trunchiul e pe +Z. Deci coapsa la zero
anatomic (colineara cu trunchiul) arata spre -Z, la 90 grade de +X. La genunchi,
cinematica directa arata ca unghiul vechi CRESTEA spre extensie (gamba se rotea de
la -Z spre +X), deci in conventia anatomica, unde pozitivul e flexia, semnul se
inverseaza.
"""
import math
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

AICI = os.path.dirname(os.path.abspath(__file__))
PACHET = os.path.dirname(AICI)
XACRO_NOU = os.path.join(PACHET, "urdf", "rehab_exo.urdf.xacro")
URDF_VECHI = os.path.join(PACHET, "attic", "rehab_exo.urdf.livrat")
TOL = 1e-9          # toleranta pe pozitie [m] si pe elementele matricei de rotatie

LANT = ["{s}_hip_joint", "{s}_thigh_ext_joint", "{s}_knee_joint",
        "{s}_shank_ext_joint", "{s}_ankle_joint"]
_V = [0]


def ok(cond, mesaj):
    assert cond, mesaj
    _V[0] += 1


# ------------------------------------------------------------------ cinematica
def _rot(ax, th):
    x, y, z = ax
    c, s, C = math.cos(th), math.sin(th), 1 - math.cos(th)
    return [[c + x * x * C, x * y * C - z * s, x * z * C + y * s],
            [y * x * C + z * s, c + y * y * C, y * z * C - x * s],
            [z * x * C - y * s, z * y * C + x * s, c + z * z * C]]


def _rpy(r, p, y):
    return _mul(_mul(_rot((0, 0, 1), y), _rot((0, 1, 0), p)), _rot((1, 0, 0), r))


def _mul(A, B):
    return [[sum(A[i][k] * B[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def _app(A, v):
    return [sum(A[i][k] * v[k] for k in range(3)) for i in range(3)]


def fk(urdf, q, side="left"):
    """Pozitia si orientarea TALPII, pornind din seat_link."""
    J = {j.get("name"): j for j in ET.parse(urdf).getroot().findall("joint")}
    R = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
    p = [0.0, 0.0, 0.0]
    for sablon in LANT:
        n = sablon.format(s=side)
        j = J[n]
        o = j.find("origin")
        oxyz = [float(v) for v in (o.get("xyz") if o is not None else "0 0 0").split()]
        orpy = [float(v) for v in ((o.get("rpy") if o is not None else None) or "0 0 0").split()]
        p = [p[i] + _app(R, oxyz)[i] for i in range(3)]
        R = _mul(R, _rpy(*orpy))
        ax = j.find("axis")
        a = [float(v) for v in ax.get("xyz").split()] if ax is not None else [0, 0, 1]
        val = q.get(n, 0.0)
        if j.get("type") == "revolute":
            R = _mul(R, _rot(a, val))
        else:
            p = [p[i] + _app(R, [a[k] * val for k in range(3)])[i] for i in range(3)]
    return p, R


# ------------------------------------------------------------------- maparea
def converteste(q_vechi, side="left"):
    """Unghiuri vechi -> unghiuri noi. Singurul loc unde traieste maparea."""
    h, k, a = ("%s_hip_joint" % side, "%s_knee_joint" % side, "%s_ankle_joint" % side)
    out = dict(q_vechi)
    out[h] = q_vechi.get(h, 0.0) + math.pi / 2.0
    out[k] = math.pi / 2.0 - q_vechi.get(k, 0.0)
    out[a] = q_vechi.get(a, 0.0)
    return out


def genereaza(*argumente):
    f = tempfile.NamedTemporaryFile(suffix=".urdf", delete=False)
    f.close()
    p = subprocess.run(["xacro", XACRO_NOU] + list(argumente) + ["-o", f.name],
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError("xacro a picat:\n%s" % p.stderr[:400])
    return f.name


def main(argv=None):
    print("== echivalenta fizica veche <-> noua conventie ==")
    nou = genereaza()

    # grila de puncte: capetele si mijlocul curselor VECHI, plus prismaticele
    puncte = []
    for h in (-0.45, -0.2, 0.0, 0.35, 0.7):
        for k in (0.0, 0.5, 1.0, 1.75):
            for a in (-0.6, 0.0, 0.6):
                puncte.append({"left_hip_joint": h, "left_knee_joint": k,
                               "left_ankle_joint": a})
    # cu prismaticele la capete, ca sa nu treaca doar pe configuratia retrasa
    for pr in (0.0, 0.08):
        puncte.append({"left_hip_joint": 0.3, "left_knee_joint": 0.9,
                       "left_ankle_joint": -0.2,
                       "left_thigh_ext_joint": pr, "left_shank_ext_joint": pr})

    d_max_p, d_max_R = 0.0, 0.0
    for q in puncte:
        for side in ("left", "right"):
            qv = {k.replace("left_", side + "_"): v for k, v in q.items()}
            qn = converteste(qv, side)
            pv, Rv = fk(URDF_VECHI, qv, side)
            pn, Rn = fk(nou, qn, side)
            d_max_p = max(d_max_p, max(abs(pv[i] - pn[i]) for i in range(3)))
            d_max_R = max(d_max_R, max(abs(Rv[i][j] - Rn[i][j])
                                       for i in range(3) for j in range(3)))
            ok(all(abs(pv[i] - pn[i]) < TOL for i in range(3)),
               "pozitia talpii difera la %s: %s vs %s" % (qv, pv, pn))
            ok(all(abs(Rv[i][j] - Rn[i][j]) < TOL for i in range(3) for j in range(3)),
               "orientarea talpii difera la %s" % qv)
    print("   %d puncte x 2 picioare; abatere maxima: pozitie %.2e m, rotatie %.2e"
          % (len(puncte), d_max_p, d_max_R))

    # CONTROL NEGATIV: o mapare GRESITA trebuie sa PICE. Fara asta, testul ar trece
    # si daca fk() ar intoarce mereu aceeasi valoare.
    q = {"left_hip_joint": 0.3, "left_knee_joint": 0.9, "left_ankle_joint": -0.2}
    gresit = dict(converteste(q))
    gresit["left_knee_joint"] = math.pi / 2.0 + q["left_knee_joint"]   # semn neinversat
    pv, _ = fk(URDF_VECHI, q, "left")
    pg, _ = fk(nou, gresit, "left")
    ok(max(abs(pv[i] - pg[i]) for i in range(3)) > 1e-3,
       "controlul negativ NU a picat: o mapare gresita da acelasi rezultat")
    print("   control negativ: maparea fara inversare de semn da o abatere de %.3f m"
          % max(abs(pv[i] - pg[i]) for i in range(3)))

    # CURSELE noi sunt cele DOCUMENTATE [PDF Tabel 3.1]
    r = ET.parse(nou).getroot()
    lim = {j.get("name"): j.find("limit") for j in r.findall("joint")
           if j.find("limit") is not None}
    for n, doc in (("left_hip_joint", 90.0), ("left_knee_joint", 140.0),
                   ("left_ankle_joint", 70.0)):
        l = lim[n]
        cursa = math.degrees(float(l.get("upper")) - float(l.get("lower")))
        ok(abs(cursa - doc) < 1e-6,
           "%s: cursa %.2f grade, documentat %.0f [PDF Tabel 3.1]" % (n, cursa, doc))
        print("   %-18s %7.2f .. %7.2f grade  (cursa %.0f, documentata)"
              % (n, math.degrees(float(l.get("lower"))),
                 math.degrees(float(l.get("upper"))), cursa))

    # POSTURA: sezut restrange soldul, si NUMAI soldul
    sez = ET.parse(genereaza("postura:=sezut")).getroot()
    ls = {j.get("name"): j.find("limit") for j in sez.findall("joint")
          if j.find("limit") is not None}
    ok(float(ls["left_hip_joint"].get("lower")) > float(lim["left_hip_joint"].get("lower")),
       "postura sezut trebuie sa RIDICE limita inferioara a soldului")
    for n in ("left_knee_joint", "left_ankle_joint"):
        ok(ls[n].get("lower") == lim[n].get("lower")
           and ls[n].get("upper") == lim[n].get("upper"),
           "postura NU are voie sa atinga %s" % n)
    print("   postura sezut: sold %.1f..%.1f grade (culcat: %.1f..%.1f); restul neatins"
          % (math.degrees(float(ls["left_hip_joint"].get("lower"))),
             math.degrees(float(ls["left_hip_joint"].get("upper"))),
             math.degrees(float(lim["left_hip_joint"].get("lower"))),
             math.degrees(float(lim["left_hip_joint"].get("upper")))))

    print("SELFTEST conventie OK (%d verificari)." % _V[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())
