#!/usr/bin/env python3
"""test_burst_channel.py -- valideaza integrarea rafalelor (rf_interference.BurstProcess) in
LinkState.drops() din netem_core: la ACEEASI pierdere medie, rafalele dau outage-uri mai lungi
decat pierderea memoryless -- exact ce conteaza pentru store-and-forward / bucla de control.
Ruleaza din sar_swarm/: python3 test_burst_channel.py"""
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "sar_plugins"))
import netem_core
import rf_interference as rf


def mean_run(drops):
    """Lungimea medie a secventelor de pierderi consecutive."""
    runs, cur = [], 0
    for d in drops:
        if d:
            cur += 1
        elif cur:
            runs.append(cur)
            cur = 0
    if cur:
        runs.append(cur)
    return (sum(runs) / len(runs)) if runs else 0.0


def main():
    N = 100000
    rng = random.Random(0)

    Lm = netem_core.LinkState(loss=0.3)            # memoryless la 0.3
    dm = [Lm.drops(rng) for _ in range(N)]
    lm = sum(dm) / N

    Lb = netem_core.LinkState(loss=0.3)            # rafale (gilbert) la ACEEASI medie
    Lb.burst = rf.BurstProcess.from_steady(0.3, 8.0, seed=1)
    db = [Lb.drops(rng) for _ in range(N)]
    lb = sum(db) / N

    assert abs(lm - 0.3) < 0.01, "memoryless ~ 0.3 (%.3f)" % lm
    assert abs(lb - 0.3) < 0.02, "burst la aceeasi medie ~ 0.3 (%.3f)" % lb
    rm, rb = mean_run(dm), mean_run(db)
    assert rb > 2 * rm, "rafalele dau outage mai lung (%.2f vs memoryless %.2f)" % (rb, rm)

    Ld = netem_core.LinkState(loss=0.0)            # default neschimbat: fara burst, loss=0
    assert Ld.burst is None and Ld.drops(random.Random(0)) is False, "default memoryless intact"

    print("OK test_burst_channel: la aceeasi medie 0.3, outage burst=%.2f > memoryless=%.2f (%.1fx)"
          % (rb, rm, rb / rm))


if __name__ == "__main__":
    main()
