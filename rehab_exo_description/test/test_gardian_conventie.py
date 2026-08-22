#!/usr/bin/env python3
"""test_gardian_conventie.py -- traiectoriile vechi trebuie sa fie REFUZATE.

DE CE
Flip-ul de conventie (D1) a schimbat intelesul unghiurilor de sold. Traiectoriile din
exercise_core sunt inca scrise in conventia veche si se reconvertesc abia la punctul
7. Pana atunci pericolul nu e ca ceva sa CADA, ci ca totul sa mearga: un exercitiu
rulat in conventia gresita nu da nicio eroare, misca robotul cu 90 de grade in alta
parte si arata perfect normal pe ecran.

De aceea modelul isi poarta versiunea in URDF (`conventie_versiune`), fisierul de
traiectorii pe a lui, iar controlerul refuza cand difera. Aici se verifica lantul
intreg: ca versiunea CHIAR ajunge in URDF-ul generat, si ca verdictul o respinge.

Rulare: python3 test/test_gardian_conventie.py
"""
import os
import re
import subprocess
import sys
import tempfile

AICI = os.path.dirname(os.path.abspath(__file__))
PACHET = os.path.dirname(AICI)
sys.path.insert(0, os.path.join(PACHET, "scripts"))

import exercise_core as ec                                        # noqa: E402


def main(argv):
    n = [0]

    def ok(c, m):
        if not c:
            print("ESEC: %s" % m)
            raise SystemExit(1)
        n[0] += 1

    # 1. Versiunea ajunge CHIAR in URDF-ul generat. Fara asta, gardianul ar avea
    # dreptate degeaba: n-ar avea ce citi.
    f = tempfile.NamedTemporaryFile(suffix=".urdf", delete=False)
    f.close()
    p = subprocess.run(["xacro", os.path.join(PACHET, "urdf", "rehab_exo.urdf.xacro"),
                        "controllers:=%s" % os.path.join(PACHET, "config",
                                                         "controllers.yaml"),
                        "-o", f.name], capture_output=True, text=True)
    ok(p.returncode == 0, "xacro a picat: %s" % p.stderr[:200])
    text = open(f.name).read()
    m = re.search(r'conventie_versiune"\s*>\s*([^<\s]+)\s*<', text)
    ok(m is not None, "URDF-ul generat nu poarta conventie_versiune")
    a_modelului = m.group(1)
    ok(a_modelului == "B1", "modelul declara '%s', se astepta B1" % a_modelului)

    # 2. AFIRMATIA CENTRALA, INVERSATA DELIBERAT pe 22 aug dupa reconversie.
    # Cat timp traiectoriile erau in B0 iar modelul in B1, aici se cerea REFUZ, si
    # asta era rostul gardianului. Odata reconvertite (P2.3), versiunile coincid si
    # se cere ACCEPTARE. Inversarea e vizibila in fisier, nu tacuta; daca reapare un
    # refuz, inseamna ca ceva a ramas in urma la o reconversie viitoare.
    ok(ec.CONVENTIE_TRAIECTORII == a_modelului,
       "dupa reconversie, traiectoriile (%s) trebuie sa fie in aceeasi conventie ca "
       "modelul (%s)" % (ec.CONVENTIE_TRAIECTORII, a_modelului))
    permis, motiv = ec.verdict_conventie(a_modelului)
    ok(permis, "cu versiunile potrivite, gardianul trebuie sa PERMITA rularea")
    ok("confirmata" in motiv, "acceptarea trebuie sa se vada ca acceptare")

    # 3. CONTROL NEGATIV: gardianul mai are dinti. O versiune diferita trebuie
    # REFUZATA, cu ambele nume in mesaj. Fara asta, testul 2 ar trece si daca
    # gardianul ar fi fost scos din functiune.
    permis2, motiv2 = ec.verdict_conventie("B0")
    ok(not permis2, "un model ramas in B0 trebuie REFUZAT")
    ok("NEPOTRIVIRE" in motiv2, "refuzul trebuie sa spuna ca e o nepotrivire")
    ok("B0" in motiv2 and ec.CONVENTIE_TRAIECTORII in motiv2,
       "mesajul trebuie sa numeasca AMBELE versiuni, altfel nu se poate depana")

    # 4. "Nu stiu" nu e "da". Un model care nu declara nimic e exact cazul vechi,
    # adica exact cel pentru care exista gardianul.
    for lipsa in (None, "", "   "):
        permis3, motiv3 = ec.verdict_conventie(lipsa)
        ok(not permis3, "model fara versiune (%r) trebuie REFUZAT" % lipsa)
    ok("nu pot verifica" in ec.verdict_conventie(None)[1],
       "refuzul pe lipsa trebuie sa spuna ca nu s-a putut verifica, nu ca difera")

    # 5. Codul de esec e distinct de celelalte din pachet, ca un refuz de conventie
    # sa nu poata fi confundat cu o nepotrivire de RMW sau cu o eroare de argparse.
    ok(ec.COD_CONVENTIE not in (0, 2, 3, 4, 5, 6),
       "codul de conventie (%d) se ciocneste cu un cod deja folosit" % ec.COD_CONVENTIE)

    print("test_gardian_conventie: %d verificari OK (versiunea ajunge in URDF, "
          "vechiul e refuzat, potrivirea e acceptata, lipsa e refuz)." % n[0])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
