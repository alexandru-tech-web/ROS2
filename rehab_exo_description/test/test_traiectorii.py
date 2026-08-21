#!/usr/bin/env python3
"""test_traiectorii.py -- traiectoriile convertite fac ce trebuie.

DOUA INVARIANTE DIFERITE, si diferenta conteaza:
  genunchi + glezna -- unghiul FIZIC ramane identic (reetichetare pura);
  sold              -- unghiul fizic SE SCHIMBA deliberat; se pastreaza FRACTIA din
                       cursa disponibila. Motiv masurat: cursa veche a soldului,
                       exprimata anatomic, e 64.22..130.11 grade (permanent flectat,
                       peste flexia umana normala) si nu incape in cei 90 de grade
                       documentati [PDF Tabel 3.1]. Limitele vechi erau placeholdere
                       fara sursa (GAP 4); documentul are prioritate.

Conversia de conventie (M1) a atins 36 de valori de unghi din exercise_core.py si
6 pozitii de repaus din patient_demo.yaml. O conversie facuta cu mana ar fi trecut
neobservata daca ar fi ratat una singura: exercitiul ar arata plauzibil si ar duce
piciorul in alta parte.

DOVADA: pentru FIECARE punct al FIECAREI traiectorii, unghiul din nucleul NOU trebuie
sa fie exact conversia unghiului din nucleul VECHI (attic/exercise_core.py.vechi).
Se compara toate cele 6 articulatii, la toti timpii, pentru toate exercitiile
inregistrate -- nu un esantion.
"""
import importlib.machinery
import importlib.util
import math
import os
import sys

AICI = os.path.dirname(os.path.abspath(__file__))
PACHET = os.path.dirname(AICI)
TOL = 1e-4          # valorile convertite sunt scrise cu 4 zecimale in sursa

_V = [0]


def ok(cond, mesaj):
    assert cond, mesaj
    _V[0] += 1


def incarca(cale, nume):
    """Incarcare pe cale explicita: fisierul din attic are extensia '.vechi' tocmai ca
    sa nu poata fi importat din greseala ca modul activ, deci importlib nu il recunoaste
    singur si are nevoie de SourceFileLoader."""
    incarcator = importlib.machinery.SourceFileLoader(nume, cale)
    sp = importlib.util.spec_from_loader(nume, incarcator)
    m = importlib.util.module_from_spec(sp)
    incarcator.exec_module(m)
    return m


VECHI = {"hip": (-0.45, 0.70), "knee": (0.00, 1.75), "ankle": (-0.60, 0.60)}
NOU = {"hip": (0.0, math.radians(90)), "knee": (0.0, math.radians(140)),
       "ankle": (math.radians(-35), math.radians(35))}


def familie(joint):
    return "hip" if "hip" in joint else ("knee" if "knee" in joint else "ankle")


def converteste(joint, val):
    """Maparea, si NU e uniforma. Genunchi si glezna: unghi FIZIC identic (offset, cu
    inversare la genunchi). Sold: RE-DERIVAT pe fractia din cursa -- cursa veche,
    exprimata anatomic, era 64.22..130.11 grade si nu incape in cei 90 documentati."""
    k = familie(joint)
    if k == "knee":
        return math.pi / 2.0 - val
    if k == "ankle":
        return val
    lo_v, hi_v = VECHI["hip"]
    lo_n, hi_n = NOU["hip"]
    return lo_n + (val - lo_v) / (hi_v - lo_v) * (hi_n - lo_n)


def fractie(joint, val, tabel):
    lo, hi = tabel[familie(joint)]
    return (val - lo) / (hi - lo)


def main(argv=None):
    nou = incarca(os.path.join(PACHET, "scripts", "exercise_core.py"), "ec_nou")
    vechi = incarca(os.path.join(PACHET, "attic", "exercise_core.py.vechi"), "ec_vechi")

    nume = sorted(set(getattr(nou, "EXERCISES", {})) & set(getattr(vechi, "EXERCISES", {})))
    ok(len(nume) >= 8, "prea putine exercitii comparate: %d" % len(nume))
    print("== echivalenta traiectoriilor: %d exercitii ==" % len(nume))

    total_puncte = 0
    d_max = 0.0
    for ex in nume:
        tv = vechi.EXERCISES[ex]().timeline
        tn = nou.EXERCISES[ex]().timeline
        ok(len(tv) == len(tn), "%s: %d segmente vechi vs %d noi" % (ex, len(tv), len(tn)))
        for i, (sv, sn) in enumerate(zip(tv, tn)):
            ok(abs(sv[0] - sn[0]) < 1e-9 and abs(sv[1] - sn[1]) < 1e-9,
               "%s[%d]: timpii s-au schimbat (%s vs %s)" % (ex, i, sv[:2], sn[:2]))
            for capat in (2, 3):        # q_start si q_end
                qv, qn = sv[capat], sn[capat]
                ok(sorted(qv) == sorted(qn),
                   "%s[%d]: alt set de articulatii" % (ex, i))
                for j in qv:
                    asteptat = converteste(j, qv[j])
                    d = abs(asteptat - qn[j])
                    d_max = max(d_max, d)
                    ok(d < TOL, "%s[%d].%s: vechi %.4f -> asteptat %.4f, gasit %.4f"
                       % (ex, i, j, qv[j], asteptat, qn[j]))
                    total_puncte += 1
    print("   %d valori de unghi comparate; abatere maxima %.2e rad" % (total_puncte, d_max))
    print("   genunchi si glezna: unghi FIZIC identic; sold: aceeasi FRACTIE din cursa")
    ok(total_puncte > 100, "prea putine valori comparate: %d" % total_puncte)

    # CONTROL NEGATIV: daca maparea ar fi identitatea, testul TREBUIE sa pice.
    # Fara asta, un nucleu nou identic cu cel vechi ar trece drept convertit.
    gresite = 0
    for ex in nume:
        tv = vechi.EXERCISES[ex]().timeline
        tn = nou.EXERCISES[ex]().timeline
        for sv, sn in zip(tv, tn):
            for capat in (2, 3):
                for j in sv[capat]:
                    if ("hip" in j or "knee" in j) \
                            and abs(sv[capat][j] - sn[capat][j]) < TOL \
                            and abs(converteste(j, sv[capat][j]) - sv[capat][j]) > TOL:
                        gresite += 1
    ok(gresite == 0, "%d valori de sold/genunchi au ramas NECONVERTITE" % gresite)
    print("   control negativ: 0 valori de sold/genunchi ramase neconvertite")

    # LIMITELE din nucleu = cursele documentate
    for cheie, doc in (("hip", 90.0), ("knee", 140.0), ("ankle", 70.0)):
        lo, hi = nou.LIMITS[cheie]
        ok(abs(math.degrees(hi - lo) - doc) < 0.01,
           "%s: cursa %.2f, documentat %.0f" % (cheie, math.degrees(hi - lo), doc))
    print("   limitele nucleului: sold 90, genunchi 140, glezna 70 grade (documentate)")

    # toate punctele sunt IN limitele noi (o conversie corecta nu iese din cursa)
    afara = []
    for ex in nume:
        tn = nou.EXERCISES[ex]().timeline
        for i, sn in enumerate(tn):
            for j, v in list(sn[2].items()) + list(sn[3].items()):
                cheie = "hip" if "hip" in j else ("knee" if "knee" in j else "ankle")
                lo, hi = nou.LIMITS[cheie]
                if not (lo - 1e-6 <= v <= hi + 1e-6):
                    afara.append("%s[%d].%s = %.4f nu e in [%.4f, %.4f]" % (ex, i, j, v, lo, hi))
    ok(not afara, "puncte in afara limitelor dupa conversie:\n    " + "\n    ".join(afara[:6]))
    print("   toate punctele convertite sunt in cursele noi")

    print("SELFTEST traiectorii OK (%d verificari)." % _V[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())
