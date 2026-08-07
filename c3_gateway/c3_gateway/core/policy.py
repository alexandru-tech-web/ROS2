#!/usr/bin/env python3
"""policy.py -- politica de selectie a transportului, ca TABELA pe (L, B, payload).
NUCLEU PUR: nu importa rclpy, socket sau os.environ.

DE CE TABELA SI NU O REGULA SCALARA
O regula de forma 'daca L > x atunci cyclonedds' presupune ca ordinea transporturilor
depinde de o singura marime. Datele C2 spun altceva: la 4 KB cyclonedds castiga peste tot,
dar la 64 KB, L=15%, B=1 castiga zenoh. Un prag scalar nu poate exprima asta. Cheia e deci
(L, B, payload), iar raspunsul se citeste dintr-o tabela DERIVATA din masuratori
(tools/derive_policy.py), nu scrisa de mana.

CELULE NEACOPERITE
Grila C2 are gauri (nu s-au rulat toate combinatiile la 64 KB). Pentru un punct care nu cade
pe grila se ia VECINUL CEL MAI APROPIAT, iar raspunsul e marcat covered=False, ca cel care
il consuma sa stie ca extrapoleaza. Daca nici vecinul nu e aproape (peste DIST_MAX), se
intoarce implicitul CONSERVATOR din tabela, cu covered=False si marja 0 -- adica 'nu stiu,
ramai pe ce e sigur', nu o preferinta inventata.

DISTANTA intre celule: L normalizat la intervalul grilei (0..30 pp) si B pe scara
LOGARITMICA (grila e 1, 3, 8 -- geometrica, nu liniara), plus o penalizare mare pentru
payload diferit, fiindca inversiunea de la 64 KB arata ca payload-ul nu e o dimensiune
peste care se poate interpola.
"""
import json
import math
import os
import sys

AICI = os.path.dirname(os.path.abspath(__file__))
TABELA_IMPLICITA = os.path.join(AICI, "policy_table.json")

L_SCARA = 30.0          # intervalul grilei C2 pe L (procente)
B_SCARA = 3.0           # log2(8) - log2(1): intervalul grilei pe B, in octave
PEN_PAYLOAD = 10.0      # payload diferit = practic alt regim, nu vecin
DIST_MAX = 0.5          # peste atat, vecinul nu mai e un argument


class Decizie(object):
    """Raspunsul politicii intr-un punct. Poarta si provenienta, ca sa se poata raspunde
    la 'de ce zici asta?' fara sa deschizi codul."""

    __slots__ = ("transport", "marja", "covered", "sursa", "conditie", "distanta")

    def __init__(self, transport, marja, covered, sursa, conditie=None, distanta=0.0):
        self.transport = transport
        self.marja = marja
        self.covered = covered
        self.sursa = sursa
        self.conditie = conditie
        self.distanta = distanta

    def __repr__(self):
        return ("Decizie(%s, marja=%.2f, covered=%s, sursa=%s, cond=%s, d=%.3f)"
                % (self.transport, self.marja, self.covered, self.sursa, self.conditie,
                   self.distanta))


class Politica(object):
    def __init__(self, tabela):
        if tabela.get("schema") != "c3_policy_table/1":
            raise ValueError("schema necunoscuta: %r" % (tabela.get("schema"),))
        if not tabela.get("celule"):
            raise ValueError("tabela fara celule -- regenereaza cu tools/derive_policy.py")
        self.tabela = tabela
        self.celule = tabela["celule"]
        self.implicit = tabela.get("default_transport", "cyclonedds")

    @classmethod
    def din_fisier(cls, cale=None):
        cale = cale or TABELA_IMPLICITA
        with open(cale) as f:
            return cls(json.load(f))

    def _distanta(self, celula, L_pct, B, payload):
        dL = (celula["L"] - L_pct) / L_SCARA
        dB = (math.log(max(celula["B"], 1.0), 2) - math.log(max(B, 1.0), 2)) / B_SCARA
        dP = 0.0 if celula["payload"] == payload else PEN_PAYLOAD
        return math.sqrt(dL * dL + dB * dB) + dP

    def decide(self, L_pct, B, payload):
        """(L in PROCENTE, B in pachete, payload in octeti) -> Decizie."""
        cel_mai_bun, dist_min = None, float("inf")
        for c in self.celule:
            d = self._distanta(c, L_pct, B, payload)
            if d < dist_min:
                cel_mai_bun, dist_min = c, d
        exact = dist_min < 1e-9
        if dist_min > DIST_MAX:
            # nimic destul de aproape: raspunsul cinstit e implicitul conservator, cu
            # marja 0 -- adica 'nu am dovezi aici', nu 'am ales eu asa'
            return Decizie(self.implicit, 0.0, False,
                           self.tabela.get("default_motiv", "implicit"), None, dist_min)
        return Decizie(cel_mai_bun["transport"], cel_mai_bun["marja"], exact,
                       cel_mai_bun["sursa"], cel_mai_bun.get("conditie"), dist_min)

    def payloaduri(self):
        return sorted({c["payload"] for c in self.celule})

    def transporturi(self):
        """Transporturile despre care tabela stie ceva. Nodurile isi valideaza cablajul
        fata de lista asta, ca sa nu poata inventa o cale care nu are acoperire in date."""
        t = {c["transport"] for c in self.celule}
        t.add(self.implicit)
        return t


def _tabela_sintetica():
    """Tabela mica, folosita in selfteste, ca ele sa nu depinda de datele reale."""
    return {
        "schema": "c3_policy_table/1",
        "default_transport": "cyclonedds",
        "default_motiv": "sintetic",
        "celule": [
            {"L": 0.0, "B": 1.0, "payload": 4096, "transport": "cyclonedds",
             "marja": 0.0, "covered": True, "sursa": "t.md", "conditie": "ideal"},
            {"L": 15.0, "B": 8.0, "payload": 4096, "transport": "cyclonedds",
             "marja": 89.6, "covered": True, "sursa": "t.md", "conditie": "ge_15_8"},
            {"L": 15.0, "B": 1.0, "payload": 65536, "transport": "zenoh",
             "marja": 1.7, "covered": True, "sursa": "t64.md", "conditie": "bern_15"},
        ],
    }


def _selftest():
    p = Politica(_tabela_sintetica())

    # 1. potrivire EXACTA pe o celula din grila -> covered=True si provenienta pastrata
    d = p.decide(15.0, 8.0, 4096)
    assert d.transport == "cyclonedds" and d.covered is True, d
    assert abs(d.marja - 89.6) < 1e-9 and d.sursa == "t.md" and d.conditie == "ge_15_8", d

    # 2. inversiunea de la 64 KB e RESPECTATA: acelasi (L,B), alt payload, alt castigator.
    # Asta e chiar motivul pentru care politica e tabela si nu prag scalar.
    assert p.decide(15.0, 1.0, 65536).transport == "zenoh"
    assert p.decide(15.0, 1.0, 4096).transport == "cyclonedds"

    # 3. celula NEACOPERITA: vecinul cel mai apropiat, dar marcat ca extrapolare
    d = p.decide(14.0, 7.0, 4096)
    assert d.transport == "cyclonedds" and d.covered is False, d
    assert 0 < d.distanta < DIST_MAX, d

    # 4. prea departe de orice celula -> implicit conservator, marja 0 (nu o preferinta)
    d = p.decide(15.0, 8.0, 999)          # payload necunoscut = alt regim
    assert d.covered is False and d.marja == 0.0, d
    assert d.transport == "cyclonedds", d

    # 5. distanta: B e pe scara logaritmica (grila e geometrica), nu liniara.
    # De la B=3: pana la 1 e o octava si jumatate, pana la 8 tot cam atat; distanta pe B
    # trebuie sa fie comparabila, spre deosebire de o metrica liniara unde 8 ar fi mult
    # mai departe decat 1.
    c15_8 = {"L": 15.0, "B": 8.0, "payload": 4096}
    c15_1 = {"L": 15.0, "B": 1.0, "payload": 4096}
    d8 = p._distanta(c15_8, 15.0, 3.0, 4096)
    d1 = p._distanta(c15_1, 15.0, 3.0, 4096)
    assert abs(d8 - d1) < 0.15, (d8, d1)

    # 6. tabela invalida e RESPINSA, nu acceptata tacut
    for rea in ({"schema": "altceva", "celule": [1]}, {"schema": "c3_policy_table/1"}):
        try:
            Politica(rea)
            raise AssertionError("tabela invalida acceptata: %r" % (rea,))
        except ValueError:
            pass

    # 7. tabela REALA (generata din C2) se incarca si raspunde pe grila ei
    if os.path.isfile(TABELA_IMPLICITA):
        reala = Politica.din_fisier()
        assert reala.payloaduri() == [4096, 65536], reala.payloaduri()
        assert reala.transporturi() == {"cyclonedds", "zenoh"}, reala.transporturi()
        d = reala.decide(15.0, 8.0, 4096)
        assert d.covered is True and d.transport in ("cyclonedds", "zenoh"), d
        assert d.sursa.endswith(".md"), d
        assert len(reala.tabela["surse"]) == 2, reala.tabela["surse"]
    print("SELFTEST policy OK (tabela pe (L,B,payload), vecin, implicit conservator).")


def main(argv):
    if argv and argv[0] == "--selftest":
        _selftest()
        return 0
    p = Politica.din_fisier()
    print("tabela: %d celule | implicit: %s" % (len(p.celule), p.implicit))
    print("%s" % p.tabela.get("default_motiv", ""))
    for c in p.celule:
        print("  L=%-4g B=%-3g payload=%-6d -> %-11s marja=%6.2f  (%s, %s)"
              % (c["L"], c["B"], c["payload"], c["transport"], c["marja"],
                 c.get("conditie"), c["sursa"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
