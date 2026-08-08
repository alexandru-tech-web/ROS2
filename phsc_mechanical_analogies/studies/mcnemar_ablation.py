#!/usr/bin/env python3
"""
mcnemar_ablation.py
Test statistic pereche pentru afirmatia centrala a ablatiei:
'predictia naiva (u=0) este mai rea decat lipsa compensarii'.

De ce McNemar si nu chi-patrat: incercarile sunt PERECHI -- aceeasi stare
initiala, aceiasi parametri fizici, acelasi zgomot pe latenta sunt date
ambelor conditii. Un test pentru esantioane independente ar ignora exact
informatia care da putere comparatiei si ar fi conservator inutil.

McNemar se uita doar la perechile DISCORDANTE:
  b = incercari unde 'none' e stabil dar 'naive' cade
  c = incercari unde 'naive' e stabil dar 'none' cade
Sub ipoteza nula (cele doua conditii sunt la fel de bune), b si c provin
dintr-o binomiala(b+c, 0.5). Folosim varianta EXACTA (binomiala), nu
aproximarea chi-patrat, pentru ca numerele sunt mici.

Se ruleaza doar pe valorile de tau unde exista separare (50, 60, 70 ms);
in rest ambele conditii sunt 100% sau 0% si nu exista perechi discordante.
"""

import sys
from pathlib import Path

import numpy as np
from scipy.stats import binomtest

# monte_carlo_stability.py sta alaturi; il gasim indiferent de directorul
# din care e lansat scriptul.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from monte_carlo_stability import run_trial, draw_params    # noqa: E402

TAUS = [0.05, 0.06, 0.07]
N = 50

print("=" * 76)
print(f"McNEMAR EXACT -- 'naiv' vs 'fara compensare', N={N} incercari perechi")
print("=" * 76)
print(f"{'tau':>7} | {'ambele':>7} {'doar none':>10} {'doar naiv':>10} "
      f"{'niciunul':>9} | {'p (o coada)':>12}")
print("-" * 76)

for tau in TAUS:
    a = b = c = d = 0     # a=ambele ok, b=doar none ok, c=doar naiv ok, d=niciunul
    for k in range(N):
        p = draw_params(np.random.default_rng(10_000 + k))
        _, ok_none = run_trial('none', tau, seed=20_000 + k, **p)
        _, ok_naive = run_trial('naive', tau, seed=20_000 + k, **p)
        if ok_none and ok_naive:
            a += 1
        elif ok_none and not ok_naive:
            b += 1
        elif ok_naive and not ok_none:
            c += 1
        else:
            d += 1

    n_disc = b + c
    if n_disc == 0:
        pv = 1.0
        note = "(fara perechi discordante)"
    else:
        # ipoteza alternativa: naiv e MAI RAU, deci b > c
        pv = binomtest(b, n_disc, 0.5, alternative='greater').pvalue
        note = ""
    print(f"{tau*1000:6.0f}m | {a:>7} {b:>10} {c:>10} {d:>9} | "
          f"{pv:>12.2e} {note}")

print("-" * 76)
print("b = doar 'none' stabil (naivul a stricat)")
print("c = doar 'naiv' stabil (naivul a ajutat)")
print("Ipoteza alternativa testata: b > c, adica predictia naiva strica")
print("mai des decat ajuta. p mic => afirmatia se sustine statistic.")
print("=" * 76)
