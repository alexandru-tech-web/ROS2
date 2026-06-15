#!/usr/bin/env python3
"""run_sil_campaign.py -- orchestrator de campanie SIL (pur Python, fara ROS).

Ruleaza intreaga baterie de scenarii x N repetitii (seed-uri diferite), aduna
metricile in tabele si genereaza figurile de comparatie -- totul dintr-o
comanda, reproducibil pe orice masina. Util pentru: regenerarea rapida a
tuturor rezultatelor cand un recenzor cere o verificare, sau cand schimbi un
parametru si vrei sa vezi efectul pe toate scenariile.

Spre deosebire de mission_experiment.sh (campania ROS reala, lenta, pe masina
de masura), aceasta e versiunea de SIMULARE: secunde, nu ore; nu cere RMW,
Gazebo sau retea -- doar valideaza ca metricile raspund la degradare si produce
figurile pentru articol / teza.

Pasi:
  1. ruleaza sil_run.py pe fiecare scenariu x reps (cu SIL_SEED diferit);
  2. aduna summary.json -> tabel CSV cu toate metricile;
  3. figuri: degradarea metricilor pe scenarii (e2e, goodput, coverage, ...);
  4. ruleaza test_degradation.py (validarea gradientului) ca verdict final.

  python3 run_sil_campaign.py                  # 3 repetitii, toate scenariile
  python3 run_sil_campaign.py --reps 5
  python3 run_sil_campaign.py --scenarios baseline loss_30 loss_70
"""
import argparse
import json
import os
import statistics
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCEN_DIR = os.path.join(HERE, "scenarios")

ALL_SCENARIOS = ["baseline", "loss_30", "loss_70", "gcs_delay_spike",
                 "partition_2v2", "drone_isolation"]

# metrici de interes din summary.json (cheie -> eticheta, "mai mic e mai bine?")
METRICS = [
    ("coverage_final", "acoperire finala", False),
    ("victims_found", "victime gasite", False),
    ("mission_time_s", "timp misiune [s]", True),
    ("e2e_telemetry_p95_ms", "latenta e2e p95 [ms]", True),
    ("goodput_gcs", "goodput", False),
    ("disconnected_total_s", "timp deconectat [s]", True),
    ("fallback_drone_s", "fallback [drona*s]", True),
]


def run_one(scenario, seed, out_dir):
    env = dict(os.environ, SIL_SEED=str(seed))
    path = os.path.join(SCEN_DIR, f"{scenario}.yaml")
    if not os.path.exists(path):
        path = scenario
    res = subprocess.run([sys.executable, os.path.join(HERE, "sil_run.py"),
                          path, "--out", out_dir],
                         capture_output=True, text=True, env=env)
    if res.returncode != 0:
        print(f"  [!] {scenario} seed {seed} esuat:\n{res.stderr[-300:]}")
        return None
    txt = res.stdout
    try:
        return json.loads(txt[txt.index("{"):])
    except (ValueError, json.JSONDecodeError):
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--scenarios", nargs="*", default=None)
    ap.add_argument("--out", default=os.path.expanduser("~/sil_campaign"))
    ap.add_argument("--seed0", type=int, default=11)
    a = ap.parse_args()

    scenarios = a.scenarios or ALL_SCENARIOS
    os.makedirs(a.out, exist_ok=True)
    print(f"== campanie SIL: {len(scenarios)} scenarii x {a.reps} repetitii "
          f"= {len(scenarios) * a.reps} rulari ==")
    print(f"   iesire: {a.out}\n")

    # 1. ruleaza tot
    data = {s: [] for s in scenarios}
    for s in scenarios:
        for rep in range(a.reps):
            summ = run_one(s, a.seed0 + rep, a.out)
            if summ:
                data[s].append(summ)
        n = len(data[s])
        print(f"  {s:18s} {n}/{a.reps} rulari OK")

    # 2. tabel agregat
    csv_path = os.path.join(a.out, "campaign_summary.csv")
    keys = [k for k, _, _ in METRICS]
    with open(csv_path, "w") as f:
        f.write("scenario," + ",".join(f"{k}_mean,{k}_sd" for k in keys) + "\n")
        for s in scenarios:
            runs = data[s]
            cells = []
            for k in keys:
                vals = [r[k] for r in runs if r.get(k) is not None]
                if vals:
                    m = statistics.mean(vals)
                    sd = statistics.pstdev(vals) if len(vals) > 1 else 0.0
                    cells.append(f"{m:.3f},{sd:.3f}")
                else:
                    cells.append(",")
            f.write(f"{s}," + ",".join(cells) + "\n")
    print(f"\n[ok] {csv_path}")

    # 3. tabel in consola
    print("\n== mediile pe scenariu ==")
    hdr = "scenariu          " + "".join(f"{lbl[:13]:>15s}"
                                         for _, lbl, _ in METRICS)
    print(hdr)
    for s in scenarios:
        runs = data[s]
        line = f"  {s:16s}"
        for k, _, _ in METRICS:
            vals = [r[k] for r in runs if r.get(k) is not None]
            line += f"{statistics.mean(vals):>15.2f}" if vals else f"{'-':>15s}"
        print(line)

    # 4. figuri (daca matplotlib e disponibil)
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        _figures(data, scenarios, a.out, plt)
        print(f"\n[ok] figuri in {a.out}")
    except ImportError:
        print("\n[info] matplotlib lipseste; sar figurile")

    # 5. validarea gradientului (verdict final)
    print("\n== validarea gradientului (test_degradation) ==")
    td = os.path.join(HERE, "test_degradation.py")
    if os.path.exists(td):
        r = subprocess.run([sys.executable, td, "--reps", str(a.reps)],
                           capture_output=True, text=True)
        # afisez doar verdictele
        for line in r.stdout.splitlines():
            if line.startswith(("[ok]", "[FAIL]", "VERDICT", "===")):
                print("  " + line)
    else:
        print("  [info] test_degradation.py negasit")

    print(f"\n[gata] campanie completa in {a.out}")


def _figures(data, scenarios, out, plt):
    """Bare cu media +/- sd pe scenarii, pentru metricile cheie."""
    metr_fig = [("e2e_telemetry_p95_ms", "latenta e2e p95 [ms]", "#c0392b"),
                ("goodput_gcs", "goodput (livrate/oferite)", "#2E8B57"),
                ("coverage_final", "acoperire finala", "#2E73CC"),
                ("fallback_drone_s", "timp in fallback [drona*s]", "#d8702e")]
    fig, axs = plt.subplots(2, 2, figsize=(13, 8))
    for ax, (key, lbl, col) in zip(axs.flat, metr_fig):
        xs, ys, es = [], [], []
        for s in scenarios:
            vals = [r[key] for r in data[s] if r.get(key) is not None]
            if vals:
                xs.append(s)
                ys.append(statistics.mean(vals))
                es.append(statistics.pstdev(vals) if len(vals) > 1 else 0.0)
        ax.bar(range(len(xs)), ys, yerr=es, color=col, alpha=0.85,
               capsize=4)
        ax.set_xticks(range(len(xs)))
        ax.set_xticklabels(xs, rotation=30, ha="right", fontsize=8)
        ax.set_title(lbl)
        ax.grid(axis="y", alpha=0.3)
    fig.suptitle("Campanie SIL: metricile de misiune pe scenarii de degradare "
                 "(media +/- abatere pe repetitii)", fontsize=12)
    fig.tight_layout()
    fig.savefig(os.path.join(out, "campaign_metrics.png"), dpi=140)
    plt.close(fig)


if __name__ == "__main__":
    main()
