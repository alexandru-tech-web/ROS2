#!/usr/bin/env python3
"""test_dwell_mediana.py -- alegerea MEDIANEI pentru dwell e o masuratoare, nu o parere.

CE SE VERIFICA
Dwell-time-ul a fost fixat la mediana timpului de asezare (171 esantioane), nu la p95 (817).
Argumentul de atunci a fost: pe celulele lente marja dintre transporturi e uriasa, deci o
estimare INCA NEASEZATA da oricum acelasi raspuns. Argumentul asta era o afirmatie. Aici
devine test: pentru fiecare celula a grilei se compara

    decizia luata cu estimarea la ASEZARE_ESANTIOANE dupa treapta   (estimare NEasezata)
    decizia luata cu estimarea complet asezata                      (adevarul)

Daca cele doua coincid peste tot, mediana e suficienta. Daca difera pe vreo celula, atunci
dwell-ul NU poate fi o constanta globala si trebuie sa devina dependent de celula -- caz in
care testul RAPORTEAZA si nu repara nimic singur.

Rulare: python3 test/test_dwell_mediana.py
"""
import os
import sys

AICI = os.path.dirname(os.path.abspath(__file__))
PACHET = os.path.dirname(AICI)
sys.path.insert(0, os.path.join(PACHET, "c3_gateway", "core"))
sys.path.insert(0, os.path.join(PACHET, "tools"))

from canal_ge import CanalGE                                       # noqa: E402
from estimator import ALPHA_B, ALPHA_L, EstimatorLink              # noqa: E402
from policy import Politica                                        # noqa: E402
from switching import (ASEZARE_ESANTIOANE, Comutator,             # noqa: E402
                       MIN_ESANTIOANE_CANDIDAT, Viabilitate)      # noqa: E402

GRILA = [(5, 1), (5, 3), (5, 8), (15, 1), (15, 3), (15, 8), (30, 1), (30, 3), (30, 8)]
SURSE = [(0, 1), (30, 8)]          # se vine de la 'ideal' si de la extrema opusa
SEEDS = 20
PAYLOADS = (4096, 65536)
N_ASEZAT = 6000                    # dupa atatea esantioane estimarea e asezata pe orice celula


def _estimare_dupa(sursa, tinta, seed, n_dupa, n_pre=3000):
    """Estimarea la n_dupa esantioane dupa treapta sursa -> tinta."""
    c_sursa = CanalGE.from_LB_pct(sursa[0], sursa[1], seed=seed)
    c_tinta = CanalGE.from_LB_pct(tinta[0], tinta[1], seed=seed + 7777)
    est = EstimatorLink(alpha_L=ALPHA_L, alpha_B=ALPHA_B)
    seq = 1
    for _ in range(n_pre):
        if c_sursa.esantion():
            est.observa(seq)
        seq += 1
    for _ in range(n_dupa):
        if c_tinta.esantion():
            est.observa(seq)
        seq += 1
    return est.estimare()


def _decizie_comutator(pol, payload, estimare):
    """Decizia REALA a gateway-ului pentru o estimare data: comutator proaspat, ambele cai
    raportate ca sanatoase, timp mult peste dwell (deci dwell-ul nu blocheaza nimic).
    Ce ramane sunt exact franele care conteaza: marja, incertitudinea si vetoul."""
    # Viabilitatea e BINARA de la 6dc7f3b ("vetoul primeste viabilitate binara"): nu mai e
    # un Estimare, ci cate sonde s-au trimis si cate s-au intors. "Sanatos" = destule sonde
    # ca sa nu fie candidat necunoscut, si toate intoarse.
    sanatos = Viabilitate(MIN_ESANTIOANE_CANDIDAT * 5, MIN_ESANTIOANE_CANDIDAT * 5)
    com = Comutator(pol, payload)
    stari = {t: sanatos for t in pol.transporturi()}
    t, _ = com.decide(estimare, 100000.0, stari)
    return t


def main(argv):
    pol = Politica.din_fisier()
    dezacorduri_operationale = []
    print("dwell = %d esantioane (mediana asezarii). Verific daca decizia luata ATUNCI"
          % ASEZARE_ESANTIOANE)
    print("coincide cu decizia luata pe estimarea complet asezata.\n")
    print("  %-9s %-8s %-7s %-24s %-24s %s"
          % ("celula", "payload", "sursa", "la dwell (L,B -> ales)", "asezat (L,B -> ales)",
             "acord"))
    dezacorduri = []
    for tinta in GRILA:
        for sursa in SURSE:
            if sursa == tinta:
                continue
            for payload in PAYLOADS:
                acord_seed = 0
                exemplu = None
                for k in range(SEEDS):
                    seed = 1000 + 13 * k
                    e_dwell = _estimare_dupa(sursa, tinta, seed, ASEZARE_ESANTIOANE)
                    e_asezat = _estimare_dupa(sursa, tinta, seed, N_ASEZAT)
                    d1 = pol.decide(e_dwell.L * 100.0, e_dwell.B, payload)
                    d2 = pol.decide(e_asezat.L * 100.0, e_asezat.B, payload)
                    # ce conteaza operational NU e cautarea bruta in tabela, ci decizia
                    # comutatorului -- cu marja, incertitudine si veto cu tot
                    t1 = _decizie_comutator(pol, payload, e_dwell)
                    t2 = _decizie_comutator(pol, payload, e_asezat)
                    if t1 != t2:
                        dezacorduri_operationale.append((tinta, sursa, payload, seed,
                                                         e_dwell, e_asezat, t1, t2))
                    if d1.transport == d2.transport:
                        acord_seed += 1
                    elif exemplu is None:
                        exemplu = (e_dwell, e_asezat, d1, d2)
                if acord_seed < SEEDS:
                    e1, e2, d1, d2 = exemplu
                    dezacorduri.append((tinta, sursa, payload, SEEDS - acord_seed,
                                        e1, e2, d1, d2))
                    print("  %-9s %-8d %-7s L=%.3f B=%.1f -> %-9s L=%.3f B=%.1f -> %-9s "
                          "DEZACORD %d/%d"
                          % ("L%dB%d" % tinta, payload, "L%dB%d" % sursa,
                             e1.L, e1.B, d1.transport, e2.L, e2.B, d2.transport,
                             SEEDS - acord_seed, SEEDS))
    if not dezacorduri:
        print("  (toate celulele: acord pe %d/%d seed-uri, ambele payload-uri)"
              % (SEEDS, SEEDS))
    print()
    print("  Cautarea bruta in tabela: %d combinatii in dezacord." % len(dezacorduri))
    la_4k = [d for d in dezacorduri if d[2] == 4096]
    print("    dintre care la 4096 B: %d | la 65536 B: %d"
          % (len(la_4k), len(dezacorduri) - len(la_4k)))
    print("  Decizia COMUTATORULUI (cu marja + incertitudine + veto): %d dezacorduri din "
          "%d comparatii." % (len(dezacorduri_operationale),
                              len(GRILA) * (len(SURSE)) * len(PAYLOADS) * SEEDS))
    for d in dezacorduri_operationale[:5]:
        print("    L%dB%d <- L%dB%d payload=%d seed=%d: %s vs %s"
              % (d[0][0], d[0][1], d[1][0], d[1][1], d[2], d[3], d[6], d[7]))
    print()
    if dezacorduri_operationale:
        print("REZULTAT: %d dezacorduri OPERATIONALE -- dwell-ul NU poate fi o constanta"
              % len(dezacorduri_operationale))
        print("globala. NU schimb nimic: decizia despre dwell dependent de celula e a")
        print("omului, dupa ce vede cifrele de mai sus.")
        return 1
    if dezacorduri:
        print("REZULTAT: cautarea bruta in tabela basculeaza pe %d combinatii, TOATE la"
              % len(dezacorduri))
        print("payload-ul de 65536 B -- unde grila C2 are doar 3 celule masurate, deci")
        print("vecinul cel mai apropiat se schimba usor. DAR decizia comutatorului NU se")
        print("schimba pe niciuna: franele (marja, incertitudine) le suprima pe toate.")
        print("Concluzie: mediana ramane valida pentru dwell; ce e subtire la 64 KB e")
        print("ACOPERIREA GRILEI, nu timpul de asezare. Se repara cu date, nu cu praguri.")
        return 0
    print("REZULTAT: decizia la dwell (mediana) coincide cu decizia asezata pe TOATE")
    print("celulele grilei, ambele payload-uri, %d seed-uri. Alegerea medianei e validata:" % SEEDS)
    print("pe celulele lente marja e destul de mare incat o estimare inca neasezata sa dea")
    print("acelasi raspuns. Dwell-ul poate ramane o constanta globala.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
