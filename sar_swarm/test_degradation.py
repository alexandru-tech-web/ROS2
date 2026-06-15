#!/usr/bin/env python3
"""test_degradation.py -- validare: degradarea retelei produce un GRADIENT
masurabil pe metricile de misiune.

Ruleaza SIL-ul pe o scara de scenarii (de la nominal la sever) si verifica,
cu repetitii pe seed-uri diferite, ca metricile se inrautatesc MONOTON cu
severitatea -- adica reziliența e cuantificabila, nu zgomot. Daca acest test
trece, ai dovada ca experimentul "vede" degradarea (raspunde la intrebarea:
injectarea defectelor chiar conteaza pentru rezultate?).

Verifica trei lucruri:
  1. goodput (livrate/oferite) SCADE cu severitatea pierderii;
  2. latenta e2e a telemetriei CRESTE cu severitatea;
  3. partitia produce timp in fallback > 0 (izolare reala), baseline = 0.

Ruleaza cu N repetitii pe seed-uri diferite si raporteaza media +/- abatere,
plus un verdict GO/NO-GO. Nu cere ROS (doar SIL pur).

  python3 test_degradation.py                 # 3 repetitii (rapid)
  python3 test_degradation.py --reps 5         # mai robust
"""
import argparse
import json
import os
import statistics
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCEN_DIR = os.path.join(HERE, "scenarios")


def run_sil(scenario, seed, out_dir):
    """Ruleaza sil_run.py pe un scenariu cu un seed dat; intoarce summary dict.
    Seed-ul se paseaza prin variabila de mediu SIL_SEED (sil_run o citeste daca
    e setata; altfel foloseste seed-ul intern). Tolerant: daca sil_run nu
    accepta seed, repetitiile vor fi identice (test inca valid pe medii)."""
    env = dict(os.environ, SIL_SEED=str(seed))
    path = os.path.join(SCEN_DIR, f"{scenario}.yaml")
    res = subprocess.run([sys.executable, os.path.join(HERE, "sil_run.py"),
                          path, "--out", out_dir],
                         capture_output=True, text=True, env=env)
    if res.returncode != 0:
        raise RuntimeError(f"sil_run esuat pe {scenario}:\n{res.stderr[-500:]}")
    txt = res.stdout
    return json.loads(txt[txt.index("{"):])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--out", default="/tmp/degr_results")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    # scara de severitate (de la nominal la sever) pentru pierdere
    loss_ladder = ["baseline", "loss_30", "loss_70"]
    # scenariile de izolare (pentru testul de fallback)
    partition = "partition_2v2"

    print(f"== validarea gradientului de degradare ({a.reps} repetitii) ==\n")

    # colecteaza metrici pe scara de pierdere
    data = {s: {"goodput": [], "e2e_p95": [], "coverage": []}
            for s in loss_ladder}
    for s in loss_ladder:
        for rep in range(a.reps):
            summ = run_sil(s, seed=11 + rep, out_dir=a.out)
            data[s]["goodput"].append(summ["goodput_gcs"])
            data[s]["e2e_p95"].append(summ["e2e_telemetry_p95_ms"])
            data[s]["coverage"].append(summ["coverage_final"])

    def med(xs):
        return statistics.mean(xs)

    def sd(xs):
        return statistics.pstdev(xs) if len(xs) > 1 else 0.0

    print("scenariu       goodput          e2e_p95 [ms]      coverage")
    for s in loss_ladder:
        g, e, c = data[s]["goodput"], data[s]["e2e_p95"], data[s]["coverage"]
        print(f"  {s:12s} {med(g):.3f}+/-{sd(g):.3f}   "
              f"{med(e):7.1f}+/-{sd(e):5.1f}   {med(c):.3f}+/-{sd(c):.3f}")

    # verdictele
    n_ok = [0]

    def check(name, cond, detail=""):
        print(("[ok]   " if cond else "[FAIL] ") + name + ("  " + detail if detail else ""))
        n_ok[0] += bool(cond)

    print("\n== verdicte ==")
    gp = [med(data[s]["goodput"]) for s in loss_ladder]
    e2 = [med(data[s]["e2e_p95"]) for s in loss_ladder]

    check("goodput scade monoton cu pierderea (baseline > loss_30 > loss_70)",
          gp[0] > gp[1] > gp[2],
          f"{gp[0]:.2f} > {gp[1]:.2f} > {gp[2]:.2f}")
    check("e2e p95 creste monoton cu pierderea",
          e2[0] < e2[1] < e2[2],
          f"{e2[0]:.0f} < {e2[1]:.0f} < {e2[2]:.0f} ms")
    check("degradarea goodput baseline->loss_70 e substantiala (>30%)",
          (gp[0] - gp[2]) / gp[0] > 0.30,
          f"scadere {100*(gp[0]-gp[2])/gp[0]:.0f}%")

    # testul de fallback: partitia izoleaza efectiv drone
    fb_part, fb_base = [], []
    for rep in range(a.reps):
        fb_part.append(run_sil(partition, seed=11 + rep,
                               out_dir=a.out)["fallback_drone_s"])
        fb_base.append(run_sil("baseline", seed=11 + rep,
                               out_dir=a.out)["fallback_drone_s"])
    check("partitia produce timp in fallback > 0 (izolare reala)",
          med(fb_part) > 0, f"{med(fb_part):.0f} drona*s")
    check("baseline NU produce fallback (retea nominala)",
          med(fb_base) == 0, f"{med(fb_base):.0f} drona*s")

    print(f"\n=== {n_ok[0]}/5 verdicte trecute ===")
    if n_ok[0] == 5:
        print("VERDICT: GO -- degradarea produce gradient masurabil; "
              "experimentul raspunde la injectarea defectelor.")
    else:
        print("VERDICT: verifica liniile [FAIL] -- gradientul nu e clar.")
    return 0 if n_ok[0] == 5 else 1


if __name__ == "__main__":
    sys.exit(main())
