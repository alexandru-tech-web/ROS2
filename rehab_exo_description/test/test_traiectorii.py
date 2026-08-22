#!/usr/bin/env python3
"""test_traiectorii.py -- reconversia B0 -> B-prim: forma pastrata, absolutul schimbat.

CE SE DOVEDESTE
La 22 aug traiectoriile au trecut din conventia B0 (zero anatomic) in B-prim (zero
mecanic, D1). Tratamentul NU e acelasi pentru toate articulatiile, si asta se
verifica, nu se declara:

  genunchi, glezna -- TRANSPORT prin maparea dovedita, care la ele e IDENTITATEA.
                      Valorile raman numeric aceleasi si cad toate in ferestrele
                      B-prim. Invariant: egalitate stricta cu versiunea B0.

  sold             -- RE-DERIVARE PE FRACTIE. Transportul (minus 90 de grade) ar
                      duce toate valorile in [-82, -35], adica in afara ferestrei
                      B-prim [0, 90]. S-a pastrat deci FRACTIA din cursa disponibila
                      DEASUPRA REPAUSULUI: intervalul vechi [repaus_vechi, 90] s-a
                      mapat pe cel nou [0, 90]. Asta pastreaza forma exercitiului
                      (cat de sus urca, ca fractie din cat poate urca) si schimba
                      deliberat unghiul absolut.

CELE DOUA INVARIANTE SE TESTEAZA SEPARAT, ca la M1: daca ar fi verificate impreuna,
un test care trece n-ar mai spune care din cele doua proprietati tine.

ANCORA re-derivarii e LITERALUL folosit in traiectorii (0.6147 rad), nu
radians(35.22). Difera cu 4.4e-6 rad, iar cu ancora gresita repausul s-ar mapa la
-7e-6 rad, adica un pic SUB limita: o iesire din fereastra produsa de rotunjire, nu
de model. Detaliul e scris fiindca a fost o decizie, nu o intamplare.

Rulare: python3 test/test_traiectorii.py
"""
import importlib.machinery
import importlib.util
import math
import os
import sys

AICI = os.path.dirname(os.path.abspath(__file__))
PACHET = os.path.dirname(AICI)

VECHI_REPAUS = 0.6147                 # literalul din traiectoriile B0
VECHI_MAX = math.radians(90.0)
NOU_MIN, NOU_MAX = 0.0, math.radians(90.0)
PRAG = 1e-9

# Pragul pe FORMA e mai larg decat cel pe transport, si motivul e o inconsecventa
# care exista DEJA in B0, nu una introdusa de reconversie: POSTURA_INITIALA se
# calcula din grade (radians(35.22) = 0.6147044) in timp ce traiectoriile purtau
# literalul rotunjit 0.6147. Cele doua difera cu 4.4e-6 rad, adica 0.00025 grade,
# ceea ce da o abatere de fractie de circa 4.6e-6. Pragul e pus imediat peste ea, ca
# sa nu ascunda nimic mai mare: daca abaterea creste, testul pica.
PRAG_FORMA = 1e-5
PASI = 40                             # esantioane pe exercitiu


def incarca(cale, nume):
    """Incarcare pe cale explicita: fisierul din attic are o extensie tocmai ca sa nu
    poata fi importat din greseala ca modul activ."""
    inc = importlib.machinery.SourceFileLoader(nume, cale)
    sp = importlib.util.spec_from_loader(nume, inc)
    m = importlib.util.module_from_spec(sp)
    inc.exec_module(m)
    return m


def fractie_veche(q):
    return (q - VECHI_REPAUS) / (VECHI_MAX - VECHI_REPAUS)


def fractie_noua(q):
    return (q - NOU_MIN) / (NOU_MAX - NOU_MIN)


def main(argv=None):
    n = [0]

    def ok(c, m):
        if not c:
            print("ESEC: %s" % m)
            raise SystemExit(1)
        n[0] += 1

    nou = incarca(os.path.join(PACHET, "scripts", "exercise_core.py"), "ec_nou")
    vechi = incarca(os.path.join(PACHET, "attic", "exercise_core.py.conventieB0"),
                    "ec_b0")

    ok(nou.CONVENTIE_TRAIECTORII == "B1",
       "traiectoriile active trebuie sa fie in B1, sunt in %s"
       % nou.CONVENTIE_TRAIECTORII)
    ok(vechi.CONVENTIE_TRAIECTORII == "B0",
       "snapshotul din attic trebuie sa fie in B0")

    nume = sorted(set(nou.EXERCISES) & set(vechi.EXERCISES))
    ok(len(nume) >= 8, "prea putine exercitii comparate: %d" % len(nume))
    print("  %d exercitii, %d esantioane fiecare" % (len(nume), PASI))

    total, sold_pts, kg_pts = 0, 0, 0
    max_abatere_forma, max_abatere_kg = 0.0, 0.0
    max_delta_sold = 0.0

    for ex in nume:
        pn = nou.EXERCISES[ex](q_init=dict(nou.POSTURA_INITIALA))
        pv = vechi.EXERCISES[ex](q_init=dict(vechi.POSTURA_INITIALA))
        pln, plv = nou.Player(pn), vechi.Player(pv)
        ok(abs(pn.total_time - pv.total_time) < PRAG,
           "%s: durata s-a schimbat (%.3f vs %.3f)" % (ex, pn.total_time, pv.total_time))
        for k in range(PASI):
            t = pn.total_time * k / (PASI - 1.0)
            qn, _ = pln.sample(t)
            qv, _ = plv.sample(t)
            for j in nou.JOINT_NAMES:
                total += 1
                if "hip" in j:
                    # INVARIANT 1: FORMA. Fractia din cursa disponibila deasupra
                    # repausului trebuie sa fie aceeasi in ambele conventii.
                    fv, fn = fractie_veche(qv[j]), fractie_noua(qn[j])
                    max_abatere_forma = max(max_abatere_forma, abs(fv - fn))
                    ok(abs(fv - fn) < PRAG_FORMA,
                       "%s t=%.2f %s: fractia NU s-a pastrat (%.6f vs %.6f)"
                       % (ex, t, j, fv, fn))
                    max_delta_sold = max(max_delta_sold, abs(qn[j] - qv[j]))
                    # ... si nimic nu a fost taiat: totul e in fereastra B-prim
                    ok(NOU_MIN - 1e-9 <= qn[j] <= NOU_MAX + 1e-9,
                       "%s t=%.2f %s: %.4f in afara ferestrei B-prim -- CLAMP"
                       % (ex, t, j, qn[j]))
                    sold_pts += 1
                else:
                    # INVARIANT 2: TRANSPORT IDENTIC la genunchi si glezna.
                    max_abatere_kg = max(max_abatere_kg, abs(qn[j] - qv[j]))
                    ok(abs(qn[j] - qv[j]) < PRAG,
                       "%s t=%.2f %s: transportul trebuie sa fie identitatea, dar "
                       "difera cu %.3e" % (ex, t, j, abs(qn[j] - qv[j])))
                    kg_pts += 1

    print("  sold     : %d puncte, forma pastrata la %.2e; deplasare absoluta "
          "maxima %.4f rad (%.2f grade)"
          % (sold_pts, max_abatere_forma, max_delta_sold, math.degrees(max_delta_sold)))
    print("  gen+glez : %d puncte, transport identic la %.2e" % (kg_pts, max_abatere_kg))

    # INVARIANTUL 2 ARE NEVOIE DE DINTI: absolutul soldului chiar TREBUIE sa se fi
    # schimbat. Daca ar fi ramas identic, "forma pastrata" ar fi trecut trivial si
    # n-ar dovedi ca s-a facut vreo re-derivare.
    ok(max_abatere_forma < PRAG_FORMA,
       "abaterea de forma (%.2e) a crescut peste reziduul de rotunjire cunoscut; "
       "nu mai e explicabila prin literalul 0.6147" % max_abatere_forma)
    ok(max_delta_sold > math.radians(5.0),
       "unghiul absolut al soldului ar trebui sa se fi schimbat deliberat, dar "
       "deplasarea maxima e doar %.4f rad" % max_delta_sold)

    # CONTROL NEGATIV: o fractie calculata gresit (pe fereastra intreaga, nu pe cea
    # deasupra repausului) trebuie sa NU treaca -- altfel testul ar accepta si
    # tratamentul gresit.
    gresit = max(abs(qv[j] / VECHI_MAX - fractie_noua(qn[j]))
                 for j in nou.JOINT_NAMES if "hip" in j)
    ok(gresit > 1e-3,
       "fractia calculata pe fereastra intreaga ar trebui sa difere vizibil de cea "
       "corecta, dar difera cu %.3e" % gresit)

    print("test_traiectorii: %d verificari OK (forma pastrata la sold, transport "
          "identic la genunchi si glezna, 0 clamp-uri)." % n[0])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
