#!/usr/bin/env python3
"""channel.py -- canal Gilbert-Elliott DETERMINIST, pentru teste. NUCLEU PUR: nu importa
rclpy, socket sau os.environ.

Modelul e cel din C2 (Simple Gilbert, 1-h=1 / 1-k=0): doua stari, G (livreaza intotdeauna)
si B (pierde intotdeauna). p = P(G->B), r = P(B->G). Deci:
    L = p/(p+r)          rata medie de pierdere (probabilitatea stationara a starii B)
    B = 1/r              lungimea medie a unei rafale de pierderi (sederea in starea B)
Inversele, folosite ca sa reproducem exact celulele grilei C2:
    r = 1/B              p = L*r/(1-L)
Aceleasi formule ca in CALIBRARE_GE_C2.md, deci un canal construit cu from_LB(15, 8) e
celula ge_15_8 din campanie.

Determinismul e obligatoriu: un test care esueaza o data la zece rulari nu e un test.
Se foloseste random.Random(seed) (Mersenne Twister, stabil intre versiunile de Python),
NU modulul random global, ca doua canale sa nu se influenteze.
"""
import random
import sys


class CanalGE(object):
    """Generator de pierderi Gilbert-Elliott. Starea initiala e G, deci primele esantioane
    sunt livrate; asta e intentionat (o sesiune reala incepe cu linkul functional)."""

    def __init__(self, p, r, seed=0):
        if not (0.0 < r <= 1.0):
            raise ValueError("r trebuie in (0, 1]: %r" % (r,))
        if not (0.0 <= p <= 1.0):
            raise ValueError("p trebuie in [0, 1]: %r" % (p,))
        self.p = float(p)
        self.r = float(r)
        self._rng = random.Random(seed)
        self._in_bad = False

    @classmethod
    def from_LB_pct(cls, L_pct, B, seed=0):
        """Ca from_LB, dar L in PROCENTE -- forma in care e scrisa grila C2 (ge_15_8)."""
        return cls.from_LB(float(L_pct) / 100.0, B, seed)

    @classmethod
    def from_LB(cls, L, B, seed=0):
        """Canalul celulei (L, B) din grila C2. L e o FRACTIE in [0,1).
        NU exista conversie automata din procente: un API care ghiceste unitatea dupa
        marimea numarului transforma 0.5%% in 50%% fara sa spuna nimic (m-a prins deja o
        data, in propriul selftest). Pentru procente exista from_LB_pct."""
        L = float(L)
        if not (0.0 <= L < 1.0):
            raise ValueError("L trebuie sa fie o fractie in [0,1); pentru procente "
                             "foloseste from_LB_pct: %r" % (L,))
        B = float(B)
        if B < 1.0:
            raise ValueError("B trebuie >= 1: %r" % (B,))
        r = 1.0 / B
        p = L * r / (1.0 - L) if L > 0 else 0.0
        return cls(p, r, seed)

    def esantion(self):
        """Un esantion: True = livrat, False = pierdut. Tranzitia se face DUPA ce se
        decide soarta esantionului curent (starea descrie esantionul, nu urmatorul)."""
        livrat = not self._in_bad
        if self._in_bad:
            if self._rng.random() < self.r:
                self._in_bad = False
        else:
            if self._rng.random() < self.p:
                self._in_bad = True
        return livrat

    def secvente(self, n, seq0=1):
        """Numerele de secventa LIVRATE dintr-un flux de n esantioane numerotate de la
        seq0. Exact ce vede un receptor real: golurile sunt pierderile."""
        return [seq0 + i for i in range(n) if self.esantion()]


def masoara(canal, n):
    """Statisticile EMPIRICE ale unui canal (pentru validarea generatorului insusi):
    (L_empiric, B_empiric, numar_rafale). B_empiric = media lungimilor rafalelor."""
    pierdute = 0
    rafale, curenta = [], 0
    for _ in range(n):
        if canal.esantion():
            if curenta:
                rafale.append(curenta)
                curenta = 0
        else:
            pierdute += 1
            curenta += 1
    if curenta:
        rafale.append(curenta)
    L = pierdute / float(n) if n else 0.0
    B = sum(rafale) / float(len(rafale)) if rafale else 0.0
    return L, B, len(rafale)


def _selftest():
    # 1. inversele L,B <-> p,r sunt exacte pe celulele grilei C2
    for L, B, p_ast, r_ast in ((5, 3, 0.017544, 0.333333), (15, 8, 0.022059, 0.125),
                               (30, 3, 0.142857, 0.333333)):
        c = CanalGE.from_LB_pct(L, B)
        assert abs(c.r - r_ast) < 1e-6, (L, B, c.r)
        assert abs(c.p - p_ast) < 1e-6, (L, B, c.p)

    # 2. canalul REPRODUCE celulele grilei C2: L si B empirice cad pe tinta.
    # Toleranta NU e o cifra rotunda aleasa din ochi, ci 4 erori standard teoretice --
    # altfel testul ori trece pe langa o eroare reala, ori pica pe zgomot la celulele
    # cu putine rafale. Lungimea rafalei e geometrica(r): medie 1/r, abatere sqrt(1-r)/r.
    # Pentru L, esantioanele sunt CORELATE, deci varianta mediei creste cu (1+rho)/(1-rho),
    # rho = 1-p-r (autocorelatia la pas 1 a lantului cu doua stari).
    import math
    N = 300000
    for L, B in ((5, 1), (5, 3), (5, 8), (15, 1), (15, 3), (15, 8),
                 (30, 1), (30, 3), (30, 8)):
        c = CanalGE.from_LB_pct(L, B, seed=1234)
        Le, Be, nr = masoara(c, N)
        Lt = L / 100.0
        rho = max(0.0, 1.0 - c.p - c.r)
        se_L = math.sqrt(Lt * (1 - Lt) / N * (1 + rho) / (1 - rho))
        se_B = (math.sqrt(1 - c.r) / c.r) / math.sqrt(nr)
        # '<=' + epsilon: la B=1 (r=1) rafala are lungime DETERMINIST 1, deci
        # se_B=0 si singura valoare acceptabila e exact 1
        assert abs(Le - Lt) <= 4 * se_L + 1e-9, (L, B, Le, 4 * se_L)
        assert abs(Be - B) <= 4 * se_B + 1e-9, (L, B, Be, 4 * se_B)
        assert nr > 100, (L, B, nr)

    # 3. determinism: acelasi seed -> aceeasi secventa; alt seed -> alta
    a = CanalGE.from_LB_pct(15, 8, seed=7).secvente(500)
    b = CanalGE.from_LB_pct(15, 8, seed=7).secvente(500)
    d = CanalGE.from_LB_pct(15, 8, seed=8).secvente(500)
    assert a == b, "canal nedeterminist la acelasi seed"
    assert a != d, "seed-uri diferite dau aceeasi secventa"

    # 4. cazuri limita
    assert CanalGE.from_LB_pct(0, 1, seed=1).secvente(100) == list(range(1, 101))  # fara pierderi
    assert CanalGE.from_LB(0.15, 8).p == CanalGE.from_LB_pct(15, 8).p          # fractie == procent
    for rea in ((0.15, 0.5), (-1, 3), (15, 3)):
        try:
            CanalGE.from_LB(*rea)
            raise AssertionError("parametru invalid acceptat: %r" % (rea,))
        except ValueError:
            pass
    print("SELFTEST channel OK (canal GE determinist, 9 celule C2 reproduse).")


def main(argv):
    if argv and argv[0] == "--selftest":
        _selftest()
        return 0
    print(__doc__.strip())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
