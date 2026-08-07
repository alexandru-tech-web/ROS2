#!/usr/bin/env python3
"""switching.py -- masina de stare care decide CAND se comuta transportul.
NUCLEU PUR: nu importa rclpy, socket sau os.environ.

Politica (policy.py) spune ce transport e mai bun INTR-UN PUNCT. Modulul asta decide daca
merita sa te MISTI acolo. Sunt intrebari diferite: prima e despre date, a doua despre cost.

TREI FRANE, fiecare cu alt rol:

1. DWELL-TIME MINIM -- derivat, nu ales
   Costul masurat de re-stabilire (FAPTE_C3.md, sectiunea d): 0.429 s mediana pe
   cyclonedds, 0.428 s pe zenoh, 5 repetitii fiecare, cu abonatul deja pornit. Se ia
   plafonul superior, 0.43 s.
   Regula de amortizare: nu vrem sa cheltuim pe re-stabilire mai mult de 10% din timpul
   petrecut pe un transport. De aici
       DWELL_MIN_S = FACTOR_AMORTIZARE * COST_RESTABILIRE_S = 10 * 0.43 = 4.3 s
   Factorul 10 e alegerea de proiectare (echivalent: acceptam pana la 10% timp mort);
   0.43 s e MASURATOARE. Daca se schimba masuratoarea, se schimba si dwell-time-ul, fara
   sa umble nimeni la o constanta magica.

2. HISTEREZIS ASIMETRIC -- doua praguri, nu unul
   Pragurile sunt asimetrice pentru ca RISCURILE sunt asimetrice. Transportul implicit din
   tabela e cel care castiga majoritatea celulelor masurate; a pleca de la el pe o dovada
   slaba poate costa pachete nelivrate, in timp ce a te intoarce la el costa cel mult ceva
   optimalitate. Deci:
       PRAG_PLECARE   = 12 pp  (ca sa parasesti implicitul, ai nevoie de dovada tare)
       PRAG_INTOARCERE = 5 pp  (ca sa revii la implicit, e destul o dovada slaba)
   Unitatea e puncte procentuale de livrare efectiva, aceeasi ca marja din tabela C2.

3. POARTA DE INCERTITUDINE -- marja trebuie sa bata bara de eroare
   O marja de 1.7 pp (cat are celula 64 KB / L=15 / B=1 din tabela reala) nu inseamna nimic
   daca sigma estimarii lui L e 4 pp. Se cere
       marja >= K_SIGMA * sigma_L,  K_SIGMA = 2
   adica marja sa depaseasca ~2 abateri standard. Fara asta, gateway-ul comuta pe zgomot
   exact in celulele in care cele doua transporturi sunt practic egale.
   In plus, daca estimarea lui B nu e stabila (vezi estimator.py), nu se comuta deloc:
   politica e indexata si pe B, deci un B nedemn de incredere face raspunsul nedemn.
"""
import sys

COST_RESTABILIRE_S = 0.43       # MASURAT: FAPTE_C3.md (d), plafonul celor doua mediane
FACTOR_AMORTIZARE = 10.0        # ALES: acceptam cel mult ~10% timp mort din re-stabiliri
DWELL_MIN_S = FACTOR_AMORTIZARE * COST_RESTABILIRE_S     # 4.3 s

PRAG_PLECARE_PP = 12.0
PRAG_INTOARCERE_PP = 5.0
K_SIGMA = 2.0


class Comutator(object):
    """Masina de stare. decide(estimare, acum) -> (transport, motiv).
    Nu are ceas propriu: timpul vine din afara, ca sa fie testabila determinist."""

    def __init__(self, politica, payload, transport_initial=None,
                 dwell_min_s=DWELL_MIN_S, prag_plecare=PRAG_PLECARE_PP,
                 prag_intoarcere=PRAG_INTOARCERE_PP, k_sigma=K_SIGMA):
        self.politica = politica
        self.payload = int(payload)
        self.implicit = politica.implicit
        self.transport = transport_initial or politica.implicit
        self.dwell_min_s = float(dwell_min_s)
        self.prag_plecare = float(prag_plecare)
        self.prag_intoarcere = float(prag_intoarcere)
        self.k_sigma = float(k_sigma)
        self.t_ultima_comutare = None
        self.n_comutari = 0

    def _prag(self, candidat):
        """Asimetria: spre implicit e ieftin, dinspre implicit e scump."""
        return self.prag_intoarcere if candidat == self.implicit else self.prag_plecare

    def decide(self, estimare, acum):
        """estimare: obiect cu .L (fractie), .B, .sigma_L, .stable. acum: secunde."""
        d = self.politica.decide(estimare.L * 100.0, estimare.B, self.payload)
        candidat = d.transport

        if candidat == self.transport:
            return self.transport, "stabil (deja pe %s)" % self.transport

        if not estimare.stable:
            return self.transport, "estimare instabila (B nedemn de incredere)"

        prag = self._prag(candidat)
        if d.marja < prag:
            return self.transport, ("marja %.1f pp sub pragul de %.1f pp (%s)"
                                    % (d.marja, prag,
                                       "intoarcere" if candidat == self.implicit
                                       else "plecare"))

        nevoie = self.k_sigma * estimare.sigma_L * 100.0
        if d.marja < nevoie:
            return self.transport, ("marja %.1f pp sub incertitudine (%.1f x sigma = %.1f pp)"
                                    % (d.marja, self.k_sigma, nevoie))

        if (self.t_ultima_comutare is not None
                and acum - self.t_ultima_comutare < self.dwell_min_s):
            return self.transport, ("dwell: %.2f s din %.2f s"
                                    % (acum - self.t_ultima_comutare, self.dwell_min_s))

        self.transport = candidat
        self.t_ultima_comutare = acum
        self.n_comutari += 1
        return self.transport, ("comutat pe %s (marja %.1f pp, sursa %s)"
                                % (candidat, d.marja, d.sursa))


def _selftest():
    from estimator import Estimare
    from policy import Politica, _tabela_sintetica

    def est(L, B=8.0, sigma=0.005, stable=True):
        return Estimare(L, B, sigma, 1000, 50, stable)

    pol = Politica(_tabela_sintetica())

    # 1. dwell-time-ul e DERIVAT din masuratoare, nu scris de mana
    assert abs(DWELL_MIN_S - 4.3) < 1e-9, DWELL_MIN_S
    assert DWELL_MIN_S == FACTOR_AMORTIZARE * COST_RESTABILIRE_S

    # 2. pe payload 64 KB, la (L=15, B=1), tabela zice zenoh -- dar marja e 1.7 pp,
    # sub pragul de plecare: NU se comuta. Exact celula pentru care exista pragurile.
    c = Comutator(pol, 65536)
    t, motiv = c.decide(est(0.15, 1.0), 100.0)
    assert t == "cyclonedds" and c.n_comutari == 0, (t, motiv)
    assert "sub pragul" in motiv, motiv

    # 3. marja mare, estimare stabila -> se comuta (si se cere payload-ul potrivit)
    pol2 = Politica({
        "schema": "c3_policy_table/1", "default_transport": "cyclonedds",
        "default_motiv": "sintetic",
        "celule": [{"L": 15.0, "B": 8.0, "payload": 4096, "transport": "zenoh",
                    "marja": 40.0, "covered": True, "sursa": "t.md"}]})
    c = Comutator(pol2, 4096)
    t, motiv = c.decide(est(0.15), 10.0)
    assert t == "zenoh" and c.n_comutari == 1, (t, motiv)
    assert "comutat" in motiv, motiv

    # 4. DWELL: imediat dupa o comutare, alta comutare e refuzata
    c.transport = "cyclonedds"                 # simulam ca politica vrea inapoi
    t, motiv = c.decide(est(0.15), 10.5)       # 0.5 s < 4.3 s
    assert t == "cyclonedds" and "dwell" in motiv, (t, motiv)
    t, motiv = c.decide(est(0.15), 10.0 + DWELL_MIN_S + 0.01)
    assert t == "zenoh" and c.n_comutari == 2, (t, motiv)

    # 5. POARTA DE INCERTITUDINE: aceeasi marja, dar sigma mare -> nu se comuta
    c = Comutator(pol2, 4096)
    t, motiv = c.decide(est(0.15, sigma=0.30), 10.0)     # 2*30 pp = 60 pp > marja 40
    assert t == "cyclonedds" and "incertitudine" in motiv, (t, motiv)

    # 6. ESTIMARE INSTABILA: nu se comuta, oricat de mare ar fi marja
    c = Comutator(pol2, 4096)
    t, motiv = c.decide(est(0.15, stable=False), 10.0)
    assert t == "cyclonedds" and "instabila" in motiv, (t, motiv)

    # 7. ASIMETRIA pragurilor: plecarea de la implicit cere mai mult decat intoarcerea.
    # Marja de 8 pp: nu ajunge sa pleci, dar ajunge sa te intorci.
    pol8 = Politica({
        "schema": "c3_policy_table/1", "default_transport": "cyclonedds",
        "default_motiv": "sintetic",
        "celule": [{"L": 15.0, "B": 8.0, "payload": 4096, "transport": "zenoh",
                    "marja": 8.0, "covered": True, "sursa": "t.md"},
                   {"L": 30.0, "B": 8.0, "payload": 4096, "transport": "cyclonedds",
                    "marja": 8.0, "covered": True, "sursa": "t.md"}]})
    c = Comutator(pol8, 4096)
    t, _ = c.decide(est(0.15), 10.0)
    assert t == "cyclonedds", "8 pp nu ar trebui sa ajunga pentru PLECARE"
    c.transport = "zenoh"                       # acum suntem in afara implicitului
    t, motiv = c.decide(est(0.30), 100.0)
    assert t == "cyclonedds" and "comutat" in motiv, ("8 pp ar trebui sa ajunga pentru "
                                                      "INTOARCERE", motiv)
    print("SELFTEST switching OK (dwell derivat, histerezis asimetric, poarta de "
          "incertitudine).")


def main(argv):
    if argv and argv[0] == "--selftest":
        _selftest()
        return 0
    print(__doc__.strip())
    print("\nCOST_RESTABILIRE_S = %.3f (masurat)  x  FACTOR_AMORTIZARE = %.0f"
          "  ->  DWELL_MIN_S = %.2f s" % (COST_RESTABILIRE_S, FACTOR_AMORTIZARE,
                                          DWELL_MIN_S))
    print("PRAG_PLECARE = %.1f pp | PRAG_INTOARCERE = %.1f pp | K_SIGMA = %.1f"
          % (PRAG_PLECARE_PP, PRAG_INTOARCERE_PP, K_SIGMA))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
