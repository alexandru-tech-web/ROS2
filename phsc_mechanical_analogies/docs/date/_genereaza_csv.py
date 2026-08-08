#!/usr/bin/env python3
"""
_genereaza_csv.py
Transforma iesirile brute ale simularilor in CSV, pentru a putea fi
incarcate direct intr-un tabel de articol sau intr-un notebook.

NU recalculeaza nimic: parseaza fisierele .txt produse de
monte_carlo_stability.py si mcnemar_ablation.py. Daca refaci simularile,
ruleaza si scriptul asta ca sa regenerezi CSV-urile.

Rulare:  python3 _genereaza_csv.py
"""

import csv
import re
from pathlib import Path

BAZA = Path(__file__).resolve().parent


def monte_carlo():
    src = BAZA / 'monte_carlo' / 'monte_carlo_iesire_bruta_N50.txt'
    dst = BAZA / 'monte_carlo' / 'praguri_stabilitate_N50.csv'
    # linii de forma:
    #   tau=   50 ms | none:  100% [0.93,1.00] | naive:   76% [0.63,0.86] | ...
    rx = re.compile(
        r'tau=\s*(\d+)\s*ms\s*\|'
        r'\s*none:\s*(\d+)%\s*\[([\d.]+),([\d.]+)\]\s*\|'
        r'\s*naive:\s*(\d+)%\s*\[([\d.]+),([\d.]+)\]\s*\|'
        r'\s*smith:\s*(\d+)%\s*\[([\d.]+),([\d.]+)\]')
    randuri = []
    for linie in src.read_text().splitlines():
        m = rx.search(linie)
        if not m:
            continue
        g = m.groups()
        tau = int(g[0])
        for i, cond in enumerate(('fara_compensare', 'naiv_u0', 'smith_buffer')):
            p, lo, hi = g[1 + 3 * i], g[2 + 3 * i], g[3 + 3 * i]
            randuri.append({
                'tau_ms': tau,
                'conditie': cond,
                'p_stabil': float(p) / 100.0,
                'wilson_95_jos': float(lo),
                'wilson_95_sus': float(hi),
                'n_incercari': 50,
            })
    with dst.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(randuri[0].keys()))
        w.writeheader()
        w.writerows(randuri)
    return dst, len(randuri)


def mcnemar():
    src = BAZA / 'mcnemar' / 'mcnemar_iesire_bruta_N50.txt'
    dst = BAZA / 'mcnemar' / 'mcnemar_perechi_N50.csv'
    #     50m |      38         12          0         0 |     2.44e-04
    rx = re.compile(r'^\s*(\d+)m\s*\|\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*\|\s*([\deE.+-]+)')
    randuri = []
    for linie in src.read_text().splitlines():
        m = rx.match(linie)
        if not m:
            continue
        tau, a, b, c, d, p = m.groups()
        randuri.append({
            'tau_ms': int(tau),
            'ambele_stabile': int(a),
            'doar_fara_compensare_b': int(b),
            'doar_naiv_c': int(c),
            'niciunul': int(d),
            'p_o_coada': float(p),
            'n_incercari': 50,
        })
    with dst.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(randuri[0].keys()))
        w.writeheader()
        w.writerows(randuri)
    return dst, len(randuri)


def benchmark():
    src = BAZA / 'benchmark' / 'benchmark_iesire_bruta.txt'
    dst = BAZA / 'benchmark' / 'timp_solve_mpc.csv'
    if not src.exists():
        return None, 0
    #   N=20: mediana=  530.9 ms  min= 477.7  max=  542.7  ->   1.9 Hz  [LENT]
    rx = re.compile(r'N=\s*(\d+):\s*mediana=\s*([\d.]+)\s*ms\s*'
                    r'min=\s*([\d.]+)\s*max=\s*([\d.]+)\s*->\s*([\d.]+)\s*Hz')
    randuri = []
    for linie in src.read_text().splitlines():
        m = rx.search(linie)
        if not m:
            continue
        N, med, mn, mx, hz = m.groups()
        randuri.append({
            'orizont_N': int(N),
            'mediana_ms': float(med),
            'min_ms': float(mn),
            'max_ms': float(mx),
            'rata_hz': float(hz),
            'buget_20hz_ms': 50.0,
            'incape_in_buget': float(med) < 50.0,
        })
    if not randuri:
        return None, 0
    with dst.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(randuri[0].keys()))
        w.writeheader()
        w.writerows(randuri)
    return dst, len(randuri)


if __name__ == '__main__':
    for fn in (monte_carlo, mcnemar, benchmark):
        cale, n = fn()
        if cale:
            print(f"  {cale.name}: {n} randuri")
        else:
            print(f"  {fn.__name__}: sursa lipseste, sarit")
