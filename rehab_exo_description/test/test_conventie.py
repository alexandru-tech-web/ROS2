#!/usr/bin/env python3
"""test_conventie.py -- echivalenta conventiilor B si B-prim, DOVEDITA prin FK.

CE SE DOVEDESTE, SI DE CE ASA
Decizia D1 a schimbat zeroul articular: din zero anatomic (B) in zero mecanic al
dispozitivului (B-prim). O schimbare de conventie e o schimbare de ETICHETE, nu de
masina: acelasi unghi fizic trebuie sa se poata numi in ambele. Aici se DERIVA
maparea intre ele si se dovedeste ca e corecta, in loc sa fie citita din comentarii.

INVARIANTUL ALES: DIRECTIA segmentelor in lume, plus unghiul relativ la glezna.

De ce nu pozitia: lungimile segmentelor s-au schimbat DELIBERAT la aceeasi revizie
(din literali inventati in cote derivate din antropometrie). Comparand pozitii,
testul ar amesteca doua schimbari si n-ar dovedi nimic despre conventie.

De ce nu matricea de rotatie a cadrelor: prima versiune a acestui test facea exact
asta si PICA, dar din motivul gresit. Odata cu conventia s-a schimbat si axa LOCALA
pe care se intinde fiecare segment: gamba mergea pe -Z local si merge acum pe +X.
Doua cadre pot descrie acelasi segment fizic si sa aiba rotatii diferite. Comparatia
era intre mere si pere, iar reziduul de 45 de grade pe care il raporta nu insemna
nimic.

Directia unui segment IN LUME e insa aceeasi marime fizica in orice conventie, si se
citeste din date, nu din presupuneri: e originea articulatiei-copil, rotita in cadrul
parintelui. La glezna, unde nu exista articulatie-copil, se compara UNGHIUL RELATIV
dintre cadrul tapei si cel al gambei, care e chiar unghiul de glezna.

MAPAREA DERIVATA: sold_nou = sold_vechi ; 90 grade. Genunchi si glezna neschimbate.
Nu e postulata: se cauta numeric, apoi se verifica pe toata grila.

Rulare: python3 test/test_conventie.py
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
XACRO_NOU = os.path.join(PACHET, "urdf", "rehab_exo.urdf.xacro")
XACRO_VECHI = os.path.join(PACHET, "attic", "rehab_exo.xacro.conventieB")

# Pragul e o DISTANTA adimensionala, nu un unghi, si asta e deliberat. Prima
# versiune masura unghiuri cu acos si se lovea de un plafon de 2.1e-08: acos e prost
# conditionat langa argumentul 1, adica exact acolo unde raspunsul e "identic", si
# eroarea lui creste ca radacina din epsilon. Slabirea pragului ar fi ascuns metrica
# proasta. Se folosesc in schimb distante de coarda (pentru vectori unitari) si norma
# Frobenius (pentru rotatii), care sunt bine conditionate la zero si dau ~1e-16.
PRAG_DISTANTA = 1e-12
SEGMENTE = ("thigh", "shank", "foot")
PARTI = ("left", "right")


def _urdf(sursa, *arg):
    f = tempfile.NamedTemporaryFile(suffix=".urdf", delete=False)
    f.close()
    p = subprocess.run(["xacro", sursa] + list(arg) + ["-o", f.name],
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError("xacro a picat pe %s:\n%s" % (sursa, p.stderr[:400]))
    return f.name


def _rpy2R(r):
    x, y, z = r
    cx, sx, cy, sy, cz, sz = (math.cos(x), math.sin(x), math.cos(y),
                              math.sin(y), math.cos(z), math.sin(z))
    return np.array([[cz * cy, cz * sy * sx - sz * cx, cz * sy * cx + sz * sx],
                     [sz * cy, sz * sy * sx + cz * cx, sz * sy * cx - cz * sx],
                     [-sy, cy * sx, cy * cx]])


def _incarca(cale):
    r = ET.parse(cale).getroot()
    J = []
    for j in r.findall("joint"):
        o, ax = j.find("origin"), j.find("axis")
        J.append(dict(
            name=j.get("name"), typ=j.get("type"),
            par=j.find("parent").get("link"), chi=j.find("child").get("link"),
            xyz=np.array([float(v) for v in (o.get("xyz", "0 0 0")).split()])
            if o is not None else np.zeros(3),
            rpy=[float(v) for v in (o.get("rpy", "0 0 0")).split()]
            if o is not None else [0.0, 0.0, 0.0],
            axis=np.array([float(v) for v in ax.get("xyz").split()])
            if ax is not None else np.array([0.0, 0.0, 1.0])))
    return J


def _fk(J, q):
    T = {"world": (np.zeros(3), np.eye(3))}
    for _ in range(6):
        for j in J:
            if j["par"] in T and j["chi"] not in T:
                p, R = T[j["par"]]
                Rj = R @ _rpy2R(j["rpy"])
                pj = p + R @ j["xyz"]
                v = q.get(j["name"], 0.0)
                if j["typ"] == "revolute":
                    a = j["axis"] / np.linalg.norm(j["axis"])
                    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
                    Rj = Rj @ (np.eye(3) + math.sin(v) * K + (1 - math.cos(v)) * K @ K)
                elif j["typ"] == "prismatic":
                    pj = pj + Rj @ (j["axis"] * v)
                T[j["chi"]] = (pj, Rj)
    return T


def _unghi_intre(Ra, Rb):
    """Unghiul rotatiei care duce Ra in Rb. Zero = orientari identice."""
    c = (np.trace(Ra.T @ Rb) - 1.0) / 2.0
    return math.acos(max(-1.0, min(1.0, c)))


def _directie(J, T, nume_joint):
    """Directia IN LUME a segmentului care pleaca din articulatia-parinte spre
    `nume_joint`. Se ia din date: originea acelei articulatii, rotita in cadrul
    parintelui ei. Independenta de lungime si de axa locala aleasa."""
    j = next(x for x in J if x["name"] == nume_joint)
    R = T[j["par"]][1]
    v = R @ j["xyz"]
    nrm = np.linalg.norm(v)
    return v / nrm if nrm > 1e-12 else None


def _abatere(J_v, J_n, q_vechi, mapare):
    """Cea mai mare abatere fizica intre cele doua conventii, in radiani."""
    q_nou = {k: mapare(k, v) for k, v in q_vechi.items()}
    Tv, Tn = _fk(J_v, q_vechi), _fk(J_n, q_nou)
    m = 0.0
    for p in PARTI:
        # coapsa si gamba: directia segmentului in lume
        for jt in ("%s_thigh_ext_joint" % p, "%s_shank_ext_joint" % p):
            dv, dn = _directie(J_v, Tv, jt), _directie(J_n, Tn, jt)
            if dv is None or dn is None:
                continue
            m = max(m, float(np.linalg.norm(dv - dn)))
        # glezna: rotatia RELATIVA talpa fata de gamba. Aceeasi marime fizica in
        # ambele conventii, comparata prin norma Frobenius a diferentei.
        rv = Tv["%s_shank" % p][1].T @ Tv["%s_foot" % p][1]
        rn = Tn["%s_shank" % p][1].T @ Tn["%s_foot" % p][1]
        m = max(m, float(np.linalg.norm(rv - rn)))
    return m


def _grila():
    """Configuratii de test: capete, mijloc si valori intermediare, pe cele trei
    articulatii, oglindite pe ambele picioare."""
    d2r = math.pi / 180.0
    solduri = [0.0, 20.0, 45.0, 70.0, 90.0]
    genunchi = [0.0, 30.0, 90.0, 140.0]
    glezne = [-35.0, 0.0, 35.0]
    out = []
    for s in solduri:
        for g in genunchi:
            for a in glezne:
                q = {}
                for p in PARTI:
                    q["%s_hip_joint" % p] = s * d2r
                    q["%s_knee_joint" % p] = g * d2r
                    q["%s_ankle_joint" % p] = a * d2r
                out.append(q)
    return out


def main(argv):
    n = [0]

    def ok(c, m):
        if not c:
            print("ESEC: %s" % m)
            raise SystemExit(1)
        n[0] += 1

    ctrl = os.path.join(PACHET, "config", "controllers.yaml")
    J_v = _incarca(_urdf(XACRO_VECHI, "controllers:=%s" % ctrl))
    J_n = _incarca(_urdf(XACRO_NOU, "controllers:=%s" % ctrl))

    # --- 1. MAPAREA SE DERIVA, nu se postuleaza. Se cauta offsetul de sold care
    # anuleaza abaterea de orientare, pe o configuratie de proba.
    proba = {"%s_hip_joint" % p: 0.7 for p in PARTI}
    proba.update({"%s_knee_joint" % p: 0.5 for p in PARTI})
    candidati = [(-180 + 5 * k) * math.pi / 180.0 for k in range(73)]
    scoruri = [(_abatere(J_v, J_n,
                         proba, lambda k, v, o=o: v + o if "hip" in k else v), o)
               for o in candidati]
    best, offset = min(scoruri)
    ok(best < PRAG_DISTANTA,
       "nicio deplasare de sold nu aliniaza conventiile; cea mai buna da %.3e" % best)
    grade = math.degrees(offset)
    ok(abs(grade + 90.0) < 1e-6,
       "maparea derivata e %+.3f grade la sold; se asteptau -90" % grade)
    print("  maparea DERIVATA din FK: sold_nou = sold_vechi %+.1f grade" % grade)

    def mapare(k, v):
        return v + offset if "hip" in k else v

    # --- 2. INVARIANTUL, pe toata grila x 2 picioare
    grila = _grila()
    maxim = 0.0
    for q in grila:
        maxim = max(maxim, _abatere(J_v, J_n, q, mapare))
    ok(maxim < PRAG_DISTANTA,
       "abatere maxima %.3e (distanta), peste pragul %.1e" % (maxim, PRAG_DISTANTA))
    n[0] += len(grila)
    print("  invariant: %d configuratii x %d picioare x %d segmente, abatere maxima %.2e"
          % (len(grila), len(PARTI), len(SEGMENTE), maxim))

    # --- 3. CONTROALE NEGATIVE. Fiecare mapare gresita trebuie sa produca o abatere
    # de ordinul unui unghi articular, nu una mica. Fara ele, testul 2 ar putea trece
    # si daca FK-ul ar fi degenerat.
    rele = [
        ("semn inversat la sold", lambda k, v: v - offset if "hip" in k else v),
        ("mapare aplicata si la genunchi", lambda k, v: v + offset),
        ("mapare aplicata la glezna", lambda k, v:
            v + offset if ("hip" in k or "ankle" in k) else v),
        ("fara mapare", lambda k, v: v),
    ]
    for eticheta, m in rele:
        e = max(_abatere(J_v, J_n, q, m) for q in grila[:12])
        ok(e > 0.5, "'%s' ar trebui sa strice geometria, dar da doar %.3e"
           % (eticheta, e))
        print("  control negativ '%s': abatere %.3f" % (eticheta, e))

    # --- 4. SEMANTICA NOULUI ZERO, verificata direct pe geometrie: la sold zero
    # coapsa e ORIZONTALA, iar la unghi pozitiv se RIDICA. Asta e chiar continutul
    # deciziei D1 si nu are voie sa depinda de comentarii.
    T0 = _fk(J_n, {})
    p_sold = T0["left_thigh"][0]
    p_gen = T0["left_shank"][0]
    ok(abs(p_gen[2] - p_sold[2]) < 1e-9,
       "la sold zero coapsa nu e orizontala: genunchiul e cu %.4f m fata de sold"
       % (p_gen[2] - p_sold[2]))
    ok(p_gen[0] > p_sold[0], "la sold zero coapsa trebuie sa arate INAINTE")
    T1 = _fk(J_n, {"left_hip_joint": 0.3})
    ok(T1["left_shank"][0][2] > p_gen[2],
       "unghi de sold POZITIV trebuie sa RIDICE genunchiul")
    n[0] += 1

    # --- 5. La genunchi zero gamba continua coapsa; flexia pozitiva o coboara.
    ok(abs(T0["left_foot"][0][2] - p_sold[2]) < 1e-9,
       "la genunchi zero gamba nu continua coapsa")
    T2 = _fk(J_n, {"left_knee_joint": 0.3})
    ok(T2["left_foot"][0][2] < T0["left_foot"][0][2],
       "flexia POZITIVA de genunchi trebuie sa COBOARE glezna")
    n[0] += 1

    print("test_conventie: %d verificari OK (mapare derivata, invariant pe grila, "
          "4 controale negative, semantica zeroului)." % n[0])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
