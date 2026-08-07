#!/usr/bin/env python3
"""test_nodes_fara_politica.py -- nodurile NU au voie sa contina politica.

Promisiunea 'nodul e subtire' e usor de facut si usor de incalcat: e de ajuns ca cineva sa
adauge un 'if L > 0.15: foloseste zenoh' ca sa aiba experimentul doua creiere si sa nu se
mai poata spune care a produs un rezultat. Testul asta o verifica mecanic, pe arborele
sintactic, si pica daca:
  1. apare, ca literal, numele vreunui transport cunoscut de tabela de politica;
  2. exista o comparatie cu un literal ZECIMAL (tiparul unui prag: 'L > 0.15', 'marja < 12.0');
  3. exista nume de constante care miros a politica (PRAG_, MARJA_, THRESHOLD_).
Numerele intregi sunt permise (indici, adancimi de coada, numar de cai), fiindca pragurile
de politica din C2/C3 sunt zecimale, iar interzicerea lor ar face codul ilizibil degeaba.

Rulare: python3 test/test_nodes_fara_politica.py
"""
import ast
import os
import sys

AICI = os.path.dirname(os.path.abspath(__file__))
PACHET = os.path.join(os.path.dirname(AICI), "c3_gateway")
NODES = os.path.join(PACHET, "nodes")
AGENT = os.path.join(PACHET, "agent")
sys.path.insert(0, os.path.join(PACHET, "core"))

from policy import Politica                                        # noqa: E402

PREFIXE_INTERZISE = ("PRAG_", "MARJA_", "THRESHOLD_", "HISTEREZIS")


def _fisiere(director):
    if not os.path.isdir(director):
        return []
    return [os.path.join(director, f) for f in sorted(os.listdir(director))
            if f.endswith(".py")]


def verifica(cale, transporturi):
    """Lista de probleme gasite in fisierul dat (goala = curat)."""
    probleme = []
    arbore = ast.parse(open(cale).read(), filename=os.path.basename(cale))
    for nod in ast.walk(arbore):
        # 1. numele transporturilor, ca literal
        if isinstance(nod, ast.Constant) and isinstance(nod.value, str):
            if nod.value in transporturi:
                probleme.append("linia %d: numele transportului '%s' scris in cod"
                                % (nod.lineno, nod.value))
        # 2. comparatii cu literali zecimali = praguri deghizate
        if isinstance(nod, ast.Compare):
            for parte in [nod.left] + list(nod.comparators):
                if (isinstance(parte, ast.Constant) and isinstance(parte.value, float)):
                    probleme.append("linia %d: comparatie cu pragul zecimal %r"
                                    % (nod.lineno, parte.value))
        # 3. constante cu nume de politica
        if isinstance(nod, ast.Assign):
            for tinta in nod.targets:
                if isinstance(tinta, ast.Name) and tinta.id.startswith(PREFIXE_INTERZISE):
                    probleme.append("linia %d: constanta de politica '%s'"
                                    % (nod.lineno, tinta.id))
    return probleme


def main(argv):
    transporturi = Politica.din_fisier().transporturi()
    fisiere = _fisiere(NODES) + _fisiere(AGENT)
    assert fisiere, "nu am gasit fisiere in nodes/ si agent/"
    total = 0
    for f in fisiere:
        probleme = verifica(f, transporturi)
        total += len(probleme)
        stare = "OK" if not probleme else "PICAT"
        print("  %-28s %s" % (os.path.basename(f), stare))
        for p in probleme:
            print("      %s" % p)
    assert total == 0, "%d urme de politica in noduri" % total

    # controlul negativ: verificatorul TREBUIE sa prinda o strecurare. Fara asta, un 'OK'
    # de mai sus n-ar dovedi decat ca functia nu se plange niciodata.
    import tempfile
    rau = os.path.join(tempfile.mkdtemp(), "rau.py")
    with open(rau, "w") as f:
        f.write("PRAG_PLECARE = 12.0\n"
                "def alege(L):\n"
                "    if L > 0.15:\n"
                "        return 'zenoh'\n"
                "    return 'cyclonedds'\n")
    gasite = verifica(rau, transporturi)
    assert len(gasite) >= 4, gasite          # 2 nume, 1 prag zecimal, 1 constanta
    assert any("zenoh" in g for g in gasite) and any("0.15" in g for g in gasite), gasite
    print("  control negativ: %d urme prinse intr-un fisier care incalca regula" % len(gasite))
    print("\nNODURILE SUNT CURATE: %d fisiere, nicio urma de politica." % len(fisiere))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
