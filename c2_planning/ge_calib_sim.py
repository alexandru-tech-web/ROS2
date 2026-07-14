#!/usr/bin/env python3
"""ge_calib_sim.py -- calibrare Gilbert-Elliott (Simple Gilbert) pentru C2.

PLANIFICARE, PYTHON PUR, FARA RETEA. Nu ruleaza tc/netem. Deriva parametrii
(p, r) ai modelului Simple Gilbert netem 'loss gemodel' pentru o grila de
(rata medie L, lungime medie rafala B), valideaza prin Monte Carlo lantul
Markov cu 2 stari, si auditeaza conditiile gilbert_*/loss_*_burst din
c1_benchmark/bench_core.py (READ-ONLY -- valorile transcrise verbatim aici).

Model (man tc-netem, 'loss gemodel'): stari good/bad; p = P(good->bad),
r = P(bad->good); 1-h = pierdere in bad, 1-k = pierdere in good. Simple
Gilbert = 1-h=1 (pierzi mereu in bad), 1-k=0 (nu pierzi in good).
Deci pierderea unui pachet <=> stare bad.

Formule (stationar): pi_bad = p/(p+r); L = pi_bad; B = 1/r.
Inversare:           r = 1/B ; p = L / (B*(1-L)).

ONESTITATE (lectia jitter uniform din C1): man page-ul descrie modelul, NU
garanteaza ce implementeaza kernelul. Numerele de aici valideaza ARITMETICA
modelului si a inversarii (Monte Carlo pe lantul Markov teoretic), nu ce va
produce netem real. Distributia REALIZATA se confirma la campanie din
log-urile de pachete, nu din documentatie si nici din aceasta simulare.
"""
import random
import statistics


# ------------------------- nucleu pur -------------------------
def pr_from_LB(L, B):
    """(rata medie L in [0,1), lungime medie rafala B>=1) -> (p, r) Simple Gilbert."""
    r = 1.0 / B
    p = L / (B * (1.0 - L))
    return p, r


def stationary_L(p, r):
    """Rata medie stationara pi_bad = p/(p+r)."""
    return p / (p + r)


def gemodel_cmd(p, r, iface="<IFACE>"):
    """Comanda netem EXACTA (Simple Gilbert: 1-h=100%, 1-k=0%). Text, NErulata."""
    return ("tc qdisc replace dev %s root netem "
            "loss gemodel %.4f%% %.4f%% 100%% 0%%" % (iface, 100 * p, 100 * r))


def bernoulli_cmd(L, iface="<IFACE>"):
    """Perechea Bernoulli (memoryless) la aceeasi rata medie L. Text, NErulata."""
    return "tc qdisc replace dev %s root netem loss %.4f%%" % (iface, 100 * L)


def simulate(p, r, n=10**6, seed=12345):
    """Monte Carlo lantul Markov 2-stari, n pachete. Simple Gilbert: pierdere
    <=> stare bad. Pierderea e decisa de starea CURENTA, apoi se tranzitioneaza.
    Intoarce rata realizata + statistici lungime rafala (rafala = run de pierderi
    consecutive = run de stari bad consecutive)."""
    rnd = random.Random(seed).random
    bad = False                      # start in good
    lost = 0
    bursts = []
    run = 0
    for _ in range(n):
        if bad:
            lost += 1
            run += 1
            if rnd() < r:            # bad -> good
                bad = False
        else:
            if run:
                bursts.append(run)
                run = 0
            if rnd() < p:            # good -> bad
                bad = True
    if run:
        bursts.append(run)
    L_real = lost / n
    if bursts:
        bs = sorted(bursts)
        b_mean = statistics.fmean(bs)
        b_p95 = bs[min(len(bs) - 1, int(round(0.95 * (len(bs) - 1))))]
    else:
        b_mean = b_p95 = 0.0
    return {"L_real": L_real, "burst_mean": b_mean, "burst_p95": b_p95,
            "n_bursts": len(bursts)}


# grila de calibrare ceruta: L x B
GRID_L = [0.05, 0.15, 0.30]
GRID_B = [1, 3, 8]                    # 1 = control ~Bernoulli

# PAS 4 -- transcris VERBATIM din c1_benchmark/bench_core.py CONDITIONS (linii 30-37),
# READ-ONLY. gilbert_* = 'loss gemodel' (p, r dati direct). loss_*_burst = model
# corelat deprecat 'loss p% r%' (corr), NU gemodel -> formulele GE NU se aplica la B.
BENCH_GILBERT = [   # (nume, p, r) -- bench_core.py:35-37
    ("gilbert_20", 0.0500, 0.2000),
    ("gilbert_25", 0.0667, 0.2000),
    ("gilbert_30", 0.0857, 0.2000),
]
BENCH_BURST = [     # (nume, loss, corr) -- bench_core.py:30-32
    ("loss_20_burst", 0.20, 0.50),
    ("loss_25_burst", 0.25, 0.50),
    ("loss_30_burst", 0.30, 0.50),
]


def _selftest():
    """Verifica inversarea formulelor + coerenta simularii (toleranta larga)."""
    ok = 0
    # 1. pr_from_LB inverseaza corect: stationary_L(p,r)==L, 1/r==B
    for L in GRID_L:
        for B in GRID_B:
            p, r = pr_from_LB(L, B)
            assert abs(stationary_L(p, r) - L) < 1e-12, (L, B)
            assert abs(1.0 / r - B) < 1e-12, (L, B)
            ok += 1
    # 2. gilbert_* din bench_core inverseaza catre L/B rezonabile
    for name, p, r in BENCH_GILBERT:
        L = stationary_L(p, r); B = 1.0 / r
        assert 0.19 < L < 0.31 and abs(B - 5.0) < 1e-9, (name, L, B)
        ok += 1
    # 3. Monte Carlo scurt: rata realizata aproape de tinta
    p, r = pr_from_LB(0.15, 3)
    s = simulate(p, r, n=200000, seed=7)
    assert abs(s["L_real"] - 0.15) < 0.01, s
    ok += 1
    print("SELFTEST OK (%d verificari)" % ok)


def main():
    print("=" * 74)
    print("GRILA DE CALIBRARE (Simple Gilbert: 1-h=100%, 1-k=0%)")
    print("formule: r=1/B ; p=L/(B*(1-L)) ; validare Monte Carlo 10^6 pachete")
    print("=" * 74)
    hdr = ("L%", "B", "p%", "r%", "L_real%", "B_real", "B_p95", "|dL|pp")
    print("%-4s %-3s %-9s %-8s %-8s %-7s %-6s %-7s" % hdr)
    for L in GRID_L:
        for B in GRID_B:
            p, r = pr_from_LB(L, B)
            s = simulate(p, r, n=10**6)
            print("%-4.0f %-3d %-9.4f %-8.4f %-8.3f %-7.3f %-6d %-7.3f" % (
                100 * L, B, 100 * p, 100 * r, 100 * s["L_real"],
                s["burst_mean"], s["burst_p95"],
                abs(100 * s["L_real"] - 100 * L)))
    print()
    print("COMENZI netem EXACTE (text, NErulate) + perechea Bernoulli:")
    for L in GRID_L:
        print("  -- L=%.0f%% --  Bernoulli: %s" % (100 * L, bernoulli_cmd(L)))
        for B in GRID_B:
            p, r = pr_from_LB(L, B)
            tag = " (control ~Bernoulli)" if B == 1 else ""
            print("     B=%d%s: %s" % (B, tag, gemodel_cmd(p, r)))
    print()
    print("=" * 74)
    print("PAS 4 -- AUDIT conditii existente in bench_core.py (READ-ONLY)")
    print("=" * 74)
    print("gilbert_* (loss gemodel, p/r verbatim) -> L,B implicite + simulare:")
    for name, p, r in BENCH_GILBERT:
        L = stationary_L(p, r); B = 1.0 / r
        s = simulate(p, r, n=10**6)
        print("  %-11s p=%.4f r=%.4f -> L=%.2f%% B=%.2f | real L=%.3f%% B=%.3f" % (
            name, p, r, 100 * L, B, 100 * s["L_real"], s["burst_mean"]))
    print("loss_*_burst (model CORELAT deprecat 'loss p%% r%%', NU gemodel):")
    for name, loss, corr in BENCH_BURST:
        print("  %-13s loss=%.0f%% corr=%.0f%% -> L=%.0f%%; B NEDEFINIT prin GE "
              "(alt model)" % (name, 100 * loss, 100 * corr, 100 * loss))


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        _selftest()
    else:
        main()
